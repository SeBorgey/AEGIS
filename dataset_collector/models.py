from dataclasses import dataclass, field
from typing import List
from numpy.typing import ArrayLike


@dataclass
class Message:
    """Single message in conversation history."""
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ActionData:
    """Parsed action from assistant response."""
    action: str
    thought: str = ""
    extra: dict = field(default_factory=dict)  # any other fields


@dataclass
class Example:
    """Single training example extracted from logs."""
    x: List[Message]          # conversation history
    y: str                    # action type (class label)
    y_full: ActionData        # full parsed action
    complexity: int = 0       # len(thought), used for selection


@dataclass
class EmbeddedExample:
    """Example with its embedding vector."""
    example: Example
    embedding: ArrayLike

