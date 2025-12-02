import numpy as np
from typing import List, Dict, Any
from collections import Counter

class GreedySelector:
    def __init__(self, target_size: int):
        self.target_size = target_size

    def select(self, examples: List[Dict[str, Any]], embeddings: List[np.ndarray]) -> List[Dict[str, Any]]:
        if not examples:
            return []
        
        if len(examples) <= self.target_size:
            return examples

        embeddings = np.array(embeddings)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / (norms + 1e-10)

        selected_indices = []
        remaining_indices = list(range(len(examples)))
        
        classes = [ex['y'] for ex in examples]
        class_counts = Counter(classes)
        total_count = len(classes)
        
        weights = np.array([total_count / class_counts[classes[i]] for i in range(len(examples))])

        complexities = [ex.get('complexity', 0) for ex in examples]
        first_idx = np.argmax(complexities)
        
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)

        while len(selected_indices) < self.target_size and remaining_indices:
            selected_embeddings = embeddings[selected_indices]
            remaining_embeddings = embeddings[remaining_indices]
            
            similarities = np.dot(remaining_embeddings, selected_embeddings.T)
            
            max_similarities = np.max(similarities, axis=1)
            
            min_distances = 1 - max_similarities
            
            current_weights = weights[remaining_indices]
            current_complexities = np.array([complexities[i] for i in remaining_indices])
            
            if np.max(current_complexities) > 0:
                norm_complexities = 0.5 + (current_complexities / np.max(current_complexities))
            else:
                norm_complexities = 1.0
                
            scores = min_distances * current_weights * norm_complexities
            
            best_idx_in_remaining = np.argmax(scores)
            best_original_idx = remaining_indices[best_idx_in_remaining]
            
            selected_indices.append(best_original_idx)
            remaining_indices.pop(best_idx_in_remaining)
            
        return [examples[i] for i in selected_indices]
