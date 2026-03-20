import csv
from pathlib import Path
from tool_suggest_experiment.metrics import RunMetrics


HEADERS = [
    "task",
    "run1_score", "run2_score", "run3_score", "avg_score",
    "run1_tokens", "run2_tokens", "run3_tokens", "avg_tokens",
    "run1_steps", "run2_steps", "run3_steps", "avg_steps",
    "run1_time", "run2_time", "run3_time", "avg_time",
]


def write_results(output_path: str | Path, task_results: list[tuple[str, list[RunMetrics]]]):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)

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
