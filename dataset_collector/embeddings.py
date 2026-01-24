from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    from .models import Example
except ImportError:
    from models import Example


class EmbeddingGenerator:
    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Embedding-0.6B",
        max_seq_length: int = 32768,
        safety_buffer: int = 256,
    ):
        self.model = SentenceTransformer(model_name)
        self.model.max_seq_length = max_seq_length
        self.safety_buffer = safety_buffer

    def generate(self, examples: List[Example]) -> np.ndarray:
        texts: List[str] = []
        for ex in examples:
            messages = ex.x

            acc_len = 0
            included: List[str] = []

            for msg in reversed(messages):
                chunk = f"{msg.role}: {msg.content}\n"
                chunk_len = len(chunk)

                if acc_len + chunk_len + self.safety_buffer > self.model.max_seq_length:
                    if not included:
                        allowed = max(
                            0,
                            self.model.max_seq_length
                            - self.safety_buffer
                            - len(f"{msg.role}: \n")
                            - 12,
                        )
                        if allowed > 0:
                            content = msg.content[-allowed:]
                            content = "...[truncated]" + content
                            included.append(f"{msg.role}: {content}\n")
                    break

                included.append(chunk)
                acc_len += chunk_len

            included.reverse()
            history_str = "".join(included)

            if len(included) < len(messages):
                history_str = "...[truncated]\n" + history_str

            texts.append(history_str)

        if not texts:
            return np.array([])

        embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=1)
        return embeddings
