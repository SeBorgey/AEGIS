from dataclasses import dataclass, field


@dataclass
class RunMetrics:
    task: str = ""
    total_tokens: int = 0
    steps: int = 0
    duration_sec: float = 0.0
    success: bool = False
    judge_scores: list[float] = field(default_factory=list)

    @property
    def avg_judge_score(self) -> float:
        if not self.judge_scores:
            return 0.0
        return sum(self.judge_scores) / len(self.judge_scores)


def average_metrics(metrics_list: list[RunMetrics]) -> dict:
    n = len(metrics_list)
    if n == 0:
        return {}
    return {
        "avg_tokens": sum(m.total_tokens for m in metrics_list) / n,
        "avg_steps": sum(m.steps for m in metrics_list) / n,
        "avg_time": sum(m.duration_sec for m in metrics_list) / n,
        "avg_score": sum(m.avg_judge_score for m in metrics_list) / n,
    }
