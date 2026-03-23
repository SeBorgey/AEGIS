import os
import json
import time
import random
import asyncio
import argparse
from pathlib import Path

from core.llm_client import LLMClient
from agents.coder_agent import ReActAgent
from agents.manager_agent import ManagerAgent
from agents.judge_agent import JudgeAgent
from core.code_executor import CodeExecutor
from core.log_manager import LogManager
from action_api import ActionPolicy, PolicyConfig, ActionExecutor, build_registry, build_manager_registry

from tool_suggest_experiment.metrics import RunMetrics
from tool_suggest_experiment.csv_writer import write_results, append_task_results, get_completed_tasks
from tool_suggest_experiment.config import (
    EASY_DATASET, MIDDLE_DATASET, HARD_DATASET,
    NUM_RUNS, NUM_JUDGE_RUNS, DEFAULT_TOP_K,
    FORMATTER_MAX_LEN, AUTOINTENT_PRESET,
)


def load_tasks(dataset_paths: list[Path]) -> list[str]:
    tasks = []
    for path in dataset_paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                tasks.extend(data)
    return tasks


def _run_single_task_impl(
    task_description: str,
    api_key: str,
    base_dir: str = "runs",
    dataset_collector_coder=None,
    dataset_collector_manager=None,
    tool_suggest_client_coder=None,
    tool_suggest_client_manager=None,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[RunMetrics, LogManager]:
    lm = LogManager(base_dir=base_dir, retention_days=7)
    workspace_path = lm.code_dir

    policy_config = PolicyConfig(
        root_dir=workspace_path,
        allowed_commands=["python", "pip"],
        command_timeout_sec=30,
        max_read_bytes=1048576,
        max_write_bytes=1048576,
        allow_shell=False,
        max_output_chars=500000,
    )

    policy = ActionPolicy(policy_config)
    registry = build_registry(policy)
    executor = ActionExecutor(policy, registry)
    code_executor = CodeExecutor(str(workspace_path))

    llm_client = LLMClient(api_key=api_key)
    llm_client.reset_token_usage()

    coder_agent = ReActAgent(
        llm_client=llm_client,
        executor=executor,
        code_executor=code_executor,
        log_manager=lm,
        max_iterations=500,
        agent_name="coder",
        dataset_collector=dataset_collector_coder,
        tool_suggest_client=tool_suggest_client_coder,
        top_k=top_k,
    )

    manager_registry = build_manager_registry(policy, coder_agent, code_executor)
    manager_executor = ActionExecutor(policy, manager_registry)

    manager_agent = ManagerAgent(
        llm_client=llm_client,
        executor=manager_executor,
        log_manager=lm,
        max_iterations=300,
        dataset_collector=dataset_collector_manager,
        tool_suggest_client=tool_suggest_client_manager,
        top_k=top_k,
    )

    lm.info(f"Task: {task_description}")
    lm.save_metadata({"original_task": task_description})

    start_time = time.time()
    success = manager_agent.run(task_description)
    duration = time.time() - start_time

    usage = llm_client.get_token_usage()
    total_steps = manager_agent.step_count + coder_agent.step_count

    metrics = RunMetrics(
        task=task_description,
        total_tokens=usage["total"],
        steps=total_steps,
        duration_sec=duration,
        success=success,
    )
    return metrics, lm


def run_single_task(
    *args,
    max_retries: int = 3,
    **kwargs
) -> tuple[RunMetrics, LogManager]:
    for attempt in range(1, max_retries + 1):
        try:
            return _run_single_task_impl(*args, **kwargs)
        except Exception as e:
            print(f"    [!] Error running task on attempt {attempt}: {e}")
            if attempt == max_retries:
                task_desc = kwargs.get("task_description", args[0] if args else "Unknown")
                return RunMetrics(task=task_desc, success=False, error_msg="ERROR"), None
            time.sleep(2)


def _run_judge_single_impl(run_path: str, api_key: str) -> float:
    lm = LogManager(
        base_dir="runs",
        logger_name=f"judge_{Path(run_path).name}",
        existing_run_dir=run_path,
        program_log_name="program_judge.log",
    )

    llm_client = LLMClient(api_key=api_key)
    agent = JudgeAgent(
        run_path=run_path,
        llm_client=llm_client,
        log_manager=lm,
    )

    agent.run()

    run_name = Path(run_path).name
    csv_path = Path("runs") / "judge_results.csv"
    if csv_path.exists():
        import csv
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        matching = [r for r in rows if r.get("run") == run_name]
        if matching:
            try:
                return float(matching[-1].get("score", 0))
            except (ValueError, TypeError):
                raise ValueError("Invalid score format")
    raise ValueError("Score not found in CSV")


def run_judge_single(run_path: str, api_key: str, max_retries: int = 3):
    for attempt in range(1, max_retries + 1):
        try:
            return _run_judge_single_impl(run_path, api_key)
        except Exception as e:
            print(f"      [!] Error judging run on attempt {attempt}: {e}")
            if attempt == max_retries:
                return "ERROR"
            time.sleep(2)


def run_judge_multiple(run_path: str, api_key: str, num_runs: int = NUM_JUDGE_RUNS) -> list:
    scores = []
    for _ in range(num_runs):
        score = run_judge_single(run_path, api_key)
        scores.append(score)
    return scores


def run_baseline(tasks: list[str], api_key: str, output_csv: str, num_runs: int = NUM_RUNS):
    print(f"=== Baseline mode: {len(tasks)} tasks, {num_runs} runs each ===")
    
    completed = get_completed_tasks(output_csv)
    
    for task in tasks:
        print(f"\n--- Task: {task} ---")
        if task in completed:
            print(f"  Task already completed in CSV. Skipping.")
            continue
            
        runs = []
        for run_idx in range(num_runs):
            print(f"  Run {run_idx + 1}/{num_runs}...")
            metrics, lm = run_single_task(task, api_key)

            if metrics.success and lm and not metrics.error_msg:
                scores = run_judge_multiple(str(lm.run_dir), api_key)
                metrics.judge_scores = scores
                print(f"    Score: {metrics.avg_judge_score}, Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")
            else:
                metrics.judge_scores = ["ERROR"] * NUM_JUDGE_RUNS
                print(f"    FAILED. Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")

            runs.append(metrics)

        append_task_results(output_csv, task, runs, num_runs)
        print(f"  Saved task results -> {output_csv}")


def run_full_experiment(
    tasks: list[str],
    api_key: str,
    baseline_csv: str,
    toolsuggest_csv: str,
    top_k: int = DEFAULT_TOP_K,
    num_runs: int = NUM_RUNS,
):
    from tool_suggest.client import ToolSuggestClient, ToolSuggestConfig, LocalBackendConfig
    from tool_suggest.services.formatter import SampleFormatter
    from tool_suggest.services.suggester.autointent import AutoIntentSuggester
    from tool_suggest.services.repository import InMemoryRepository
    from tool_suggest_experiment.dataset_collector import AegisDatasetCollector

    random.seed(42)
    tasks_copy = tasks.copy()
    random.shuffle(tasks_copy)
    split_idx = max(1, int(len(tasks_copy) * 0.8))
    train_tasks = tasks_copy[:split_idx] if len(tasks_copy) > 1 else tasks_copy
    test_tasks = tasks_copy[split_idx:] if len(tasks_copy) > 1 else tasks_copy

    print(f"=== Full experiment: {len(tasks)} total tasks ===")
    print(f"Train tasks ({len(train_tasks)}): {train_tasks}")
    print(f"Test tasks ({len(test_tasks)}): {test_tasks}")
    
    formatter_coder = SampleFormatter(max_len=FORMATTER_MAX_LEN, token_counter=len)
    formatter_manager = SampleFormatter(max_len=FORMATTER_MAX_LEN, token_counter=len)

    client_coder = ToolSuggestClient(ToolSuggestConfig(
        collection_name="coder_tools",
        local_backend=LocalBackendConfig(
            repository=InMemoryRepository("coder_tools"),
            suggester=AutoIntentSuggester(formatter_coder, config=AUTOINTENT_PRESET),
        ),
    ))
    client_manager = ToolSuggestClient(ToolSuggestConfig(
        collection_name="manager_tools",
        local_backend=LocalBackendConfig(
            repository=InMemoryRepository("manager_tools"),
            suggester=AutoIntentSuggester(formatter_manager, config=AUTOINTENT_PRESET),
        ),
    ))

    collector_coder = AegisDatasetCollector(client_coder)
    collector_manager = AegisDatasetCollector(client_manager)

    print(f"\n--- Phase 1: Baseline Dataset Collection (Train Tasks) ---")
    for task in train_tasks:
        print(f"\nTask: {task} ({num_runs} runs)")
        for run_idx in range(num_runs):
            print(f"  Train run {run_idx + 1}/{num_runs}...")
            run_single_task(
                task, api_key,
                dataset_collector_coder=collector_coder,
                dataset_collector_manager=collector_manager,
            )

    print(f"\n--- Phase 2: Training tool-suggest ---")
    try:
        asyncio.run(client_coder.train())
        print("    Coder tool-suggest trained.")
    except Exception as e:
        print(f"    Coder training failed: {e}")
        client_coder = None

    try:
        asyncio.run(client_manager.train())
        print("    Manager tool-suggest trained.")
    except Exception as e:
        print(f"    Manager training failed: {e}")
        client_manager = None

    completed_baseline = get_completed_tasks(baseline_csv)
    completed_ts = get_completed_tasks(toolsuggest_csv)

    print(f"\n--- Phase 3: Baseline Test Phase ---")
    for task in test_tasks:
        if task in completed_baseline:
            print(f"\n  Task '{task}' already completed in baseline. Skipping.")
            continue
            
        print(f"\n  Baseline testing: {task}")
        runs = []
        for run_idx in range(num_runs):
            print(f"    Test run {run_idx + 1}/{num_runs}...")
            metrics, lm = run_single_task(task, api_key)

            if metrics.success and lm and not metrics.error_msg:
                scores = run_judge_multiple(str(lm.run_dir), api_key)
                metrics.judge_scores = scores
                print(f"      Score: {metrics.avg_judge_score}, Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")
            else:
                metrics.judge_scores = ["ERROR"] * NUM_JUDGE_RUNS
                print(f"      FAILED. Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")

            runs.append(metrics)
        append_task_results(baseline_csv, task, runs, num_runs)


    print(f"\n--- Phase 4: Tool-Suggest Test Phase ---")
    for task in test_tasks:
        if task in completed_ts:
            print(f"\n  Task '{task}' already completed in toolsuggest. Skipping.")
            continue
            
        print(f"\n  Tool-suggest testing: {task}")
        runs = []
        for run_idx in range(num_runs):
            print(f"    TS run {run_idx + 1}/{num_runs}...")
            metrics, lm = run_single_task(
                task, api_key,
                tool_suggest_client_coder=client_coder,
                tool_suggest_client_manager=client_manager,
                top_k=top_k,
            )

            if metrics.success and lm and not metrics.error_msg:
                scores = run_judge_multiple(str(lm.run_dir), api_key)
                metrics.judge_scores = scores
                print(f"      Score: {metrics.avg_judge_score}, Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")
            else:
                metrics.judge_scores = ["ERROR"] * NUM_JUDGE_RUNS
                print(f"      FAILED. Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")

            runs.append(metrics)
        append_task_results(toolsuggest_csv, task, runs, num_runs)

    print("\nExperiment finished.")


def main():
    parser = argparse.ArgumentParser(description="AEGIS + tool-suggest experiment runner")
    parser.add_argument("--mode", choices=["baseline", "full"], required=True)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--output_baseline", type=str, default="baseline_results.csv")
    parser.add_argument("--output_toolsuggest", type=str, default="toolsuggest_results.csv")
    parser.add_argument("--top_k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--tasks", type=str, nargs="*", default=None,
                        help="Specific tasks to run (overrides datasets)")
    parser.add_argument("--datasets", type=str, nargs="*", default=["easy", "middle", "hard"],
                        help="Datasets to use: easy, middle, hard")
    parser.add_argument("--num_runs", type=int, default=NUM_RUNS)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return

    if args.tasks:
        tasks = args.tasks
    else:
        dataset_map = {"easy": EASY_DATASET, "middle": MIDDLE_DATASET, "hard": HARD_DATASET}
        paths = [dataset_map[d] for d in args.datasets if d in dataset_map]
        tasks = load_tasks(paths)

    if not tasks:
        print("No tasks found")
        return

    if args.mode == "baseline":
        output = args.output or "baseline_results.csv"
        run_baseline(tasks, api_key, output, num_runs=args.num_runs)
    else:
        run_full_experiment(
            tasks, api_key,
            baseline_csv=args.output_baseline,
            toolsuggest_csv=args.output_toolsuggest,
            top_k=args.top_k,
            num_runs=args.num_runs,
        )


if __name__ == "__main__":
    main()
