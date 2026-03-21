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
