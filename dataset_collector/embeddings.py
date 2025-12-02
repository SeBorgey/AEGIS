from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any

class EmbeddingGenerator:
    def __init__(self, model_name: str = 'Qwen/Qwen3-Embedding-0.6B'):
        self.model = SentenceTransformer(model_name)
        self.model.max_seq_length = 2048

    def generate(self, examples: List[Dict[str, Any]]) -> List[np.ndarray]:
        texts = []
        for ex in examples:
            history_str = ""
            for msg in ex['x']:
                content = msg['content']
                if len(content) > 1000:
                    content = content[:1000] + "...[truncated]"
                history_str += f"{msg['role']}: {content}\n"
            
            texts.append(history_str)
        
        if not texts:
            return []

        embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=1)
        return embeddings
