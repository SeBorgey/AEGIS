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


def write_results(output_path: str | Path, task_results: list[tuple[str, list[RunMetrics]]]):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not task_results:
        return

    num_runs = len(task_results[0][1])
    headers = _build_headers(num_runs)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for task_name, runs in task_results:
            row = [task_name]

            scores = [r.avg_judge_score for r in runs]
            row.extend([f"{s:.2f}" for s in scores])
            row.append(f"{sum(scores) / len(scores):.2f}" if scores else "0.00")

            tokens = [r.total_tokens for r in runs]
            row.extend([str(t) for t in tokens])
            row.append(f"{sum(tokens) / len(tokens):.0f}" if tokens else "0")

            steps = [r.steps for r in runs]
            row.extend([str(s) for s in steps])
            row.append(f"{sum(steps) / len(steps):.1f}" if steps else "0")

            times = [r.duration_sec for r in runs]
            row.extend([f"{t:.1f}" for t in times])
            row.append(f"{sum(times) / len(times):.1f}" if times else "0")

            writer.writerow(row)
