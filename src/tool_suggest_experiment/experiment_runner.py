import os
import json
import time
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
from tool_suggest_experiment.csv_writer import write_results
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


def run_single_task(
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


def run_judge_single(run_path: str, api_key: str) -> float:
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
                return 0.0
    return 0.0


def run_judge_multiple(run_path: str, api_key: str, num_runs: int = NUM_JUDGE_RUNS) -> list[float]:
    scores = []
    for _ in range(num_runs):
        score = run_judge_single(run_path, api_key)
        scores.append(score)
    return scores


def run_baseline(tasks: list[str], api_key: str, output_csv: str, num_runs: int = NUM_RUNS):
    print(f"=== Baseline mode: {len(tasks)} tasks, {num_runs} runs each ===")
    all_results = []

    for task in tasks:
        print(f"\n--- Task: {task} ---")
        runs = []

        for run_idx in range(num_runs):
            print(f"  Run {run_idx + 1}/{num_runs}...")
            metrics, lm = run_single_task(task, api_key)

            if metrics.success:
                scores = run_judge_multiple(str(lm.run_dir), api_key)
                metrics.judge_scores = scores
                print(f"    Score: {metrics.avg_judge_score:.2f}, Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")
            else:
                metrics.judge_scores = [0.0] * NUM_JUDGE_RUNS
                print(f"    FAILED. Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")

            runs.append(metrics)

        all_results.append((task, runs))

    write_results(output_csv, all_results)
    print(f"\nResults saved to {output_csv}")


def run_with_toolsuggest(tasks: list[str], api_key: str, output_csv: str, top_k: int = DEFAULT_TOP_K, num_runs: int = NUM_RUNS):
    from tool_suggest.client import ToolSuggestClient, ToolSuggestConfig, LocalBackendConfig
    from tool_suggest.services.formatter import SampleFormatter
    from tool_suggest.services.suggester.autointent import AutoIntentSuggester
    from tool_suggest.services.repository import InMemoryRepository
    from tool_suggest_experiment.dataset_collector import AegisDatasetCollector
    from tool_suggest_experiment.tool_filter import CODER_TOOLS, MANAGER_TOOLS

    print(f"=== Tool-suggest mode: {len(tasks)} tasks, {num_runs} runs each, top_k={top_k} ===")
    all_results = []

    for task in tasks:
        print(f"\n--- Task: {task} ---")

        print("  Phase 1: Collecting data (baseline runs)...")
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

        for collect_idx in range(num_runs):
            print(f"  Collection run {collect_idx + 1}/{num_runs}...")
            run_single_task(
                task, api_key,
                dataset_collector_coder=collector_coder,
                dataset_collector_manager=collector_manager,
            )

        print("  Phase 2: Training tool-suggest...")
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

        print("  Phase 3: Running with tool-suggest...")
        runs = []
        for run_idx in range(num_runs):
            print(f"  Run {run_idx + 1}/{num_runs} with tool-suggest...")
            metrics, lm = run_single_task(
                task, api_key,
                tool_suggest_client_coder=client_coder,
                tool_suggest_client_manager=client_manager,
                top_k=top_k,
            )

            if metrics.success:
                scores = run_judge_multiple(str(lm.run_dir), api_key)
                metrics.judge_scores = scores
                print(f"    Score: {metrics.avg_judge_score:.2f}, Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")
            else:
                metrics.judge_scores = [0.0] * NUM_JUDGE_RUNS
                print(f"    FAILED. Tokens: {metrics.total_tokens}, Steps: {metrics.steps}, Time: {metrics.duration_sec:.1f}s")

            runs.append(metrics)

        all_results.append((task, runs))

    write_results(output_csv, all_results)
    print(f"\nResults saved to {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="AEGIS + tool-suggest experiment runner")
    parser.add_argument("--mode", choices=["baseline", "toolsuggest"], required=True)
    parser.add_argument("--output", type=str, default=None)
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

    output = args.output or f"{args.mode}_results.csv"

    if args.mode == "baseline":
        run_baseline(tasks, api_key, output, num_runs=args.num_runs)
    else:
        run_with_toolsuggest(tasks, api_key, output, top_k=args.top_k, num_runs=args.num_runs)


if __name__ == "__main__":
    main()
