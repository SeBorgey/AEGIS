import csv
from pathlib import Path
from tool_suggest_experiment.metrics import RunMetrics

def _build_headers(num_runs: int) -> list[str]:
    headers = ["task"]
    for i in range(1, num_runs + 1):
        headers.append(f"run{i}_score")
    headers.append("avg_score")
    for i in range(1, num_runs + 1):
        headers.append(f"run{i}_tokens")
    headers.append("avg_tokens")
    for i in range(1, num_runs + 1):
        headers.append(f"run{i}_steps")
    headers.append("avg_steps")
    for i in range(1, num_runs + 1):
        headers.append(f"run{i}_time")
    headers.append("avg_time")
    return headers

def append_task_results(output_path: str | Path, task_name: str, runs: list[RunMetrics], num_runs: int):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_exists = output_path.exists()
    
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(_build_headers(num_runs))
            
        row = [task_name]

        scores = [r.avg_judge_score for r in runs]
        for s in scores:
            if isinstance(s, (float, int)):
                row.append(f"{s:.2f}")
            else:
                row.append(str(s))
        valid_scores = [s for s in scores if isinstance(s, (float, int))]
        row.append(f"{sum(valid_scores) / len(valid_scores):.2f}" if valid_scores else "ERROR")

        tokens = [r.total_tokens if not r.error_msg else "ERROR" for r in runs]
        row.extend([str(t) for t in tokens])
        valid_tokens = [t for t in tokens if isinstance(t, int)]
        row.append(f"{sum(valid_tokens) / len(valid_tokens):.0f}" if valid_tokens else "ERROR")

        steps = [r.steps if not r.error_msg else "ERROR" for r in runs]
        row.extend([str(s) for s in steps])
        valid_steps = [s for s in steps if isinstance(s, int)]
        row.append(f"{sum(valid_steps) / len(valid_steps):.1f}" if valid_steps else "ERROR")

        times = [r.duration_sec if not r.error_msg else "ERROR" for r in runs]
        row.extend([str(t) if t == "ERROR" else f"{t:.1f}" for t in times])
        valid_times = [t for t in times if isinstance(t, float)]
        row.append(f"{sum(valid_times) / len(valid_times):.1f}" if valid_times else "ERROR")

        writer.writerow(row)

def get_completed_tasks(csv_path: str | Path) -> set[str]:
    completed = set()
    csv_path = Path(csv_path)
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("task"):
                    completed.add(row["task"])
    return completed

def write_results(output_path: str | Path, task_results: list[tuple[str, list[RunMetrics]]]):
    if not task_results:
        return
    num_runs = len(task_results[0][1])
    if Path(output_path).exists():
        Path(output_path).unlink()
    for task_name, runs in task_results:
        append_task_results(output_path, task_name, runs, num_runs)
