from dataclasses import dataclass, field
from typing import Union

@dataclass
class RunMetrics:
    task: str = ""
    total_tokens: int = 0
    steps: int = 0
    duration_sec: float = 0.0
    success: bool = False
    error_msg: str = ""
    judge_scores: list[Union[float, str]] = field(default_factory=list)

    @property
    def avg_judge_score(self) -> Union[float, str]:
        if not self.judge_scores:
            return 0.0
        valid = [s for s in self.judge_scores if isinstance(s, (int, float))]
        if not valid:
            return "ERROR"
        return sum(valid) / len(valid)
