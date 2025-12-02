import os
import json
from typing import List, Dict, Any
try:
    from .parser import LogParser
    from .embeddings import EmbeddingGenerator
    from .selector import GreedySelector
except ImportError:
    from parser import LogParser
    from embeddings import EmbeddingGenerator
    from selector import GreedySelector

class DatasetCollector:
    def __init__(self, runs_dir: str, output_dir: str, target_size: int = 1000):
        self.runs_dir = runs_dir
        self.output_dir = output_dir
        self.target_size = target_size
        self.parser = LogParser(runs_dir)
        self.embedder = EmbeddingGenerator()
        self.selector = GreedySelector(target_size)

    def collect(self):
        print("Parsing logs...")
        data = self.parser.parse_all()
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        for agent_type, examples in data.items():
            print(f"Processing {agent_type} (found {len(examples)} examples)...")
            
            if not examples:
                print(f"No examples found for {agent_type}.")
                continue

            print("Generating embeddings...")
            embeddings = self.embedder.generate(examples)
            
            print(f"Selecting top {self.target_size} examples...")
            selected_examples = self.selector.select(examples, embeddings)
            
            output_path = os.path.join(self.output_dir, f"{agent_type}_dataset.json")
            print(f"Saving {len(selected_examples)} examples to {output_path}...")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(selected_examples, f, indent=2, ensure_ascii=False)
                
        print("Done.")

if __name__ == "__main__":
    collector = DatasetCollector(
        runs_dir="runs",
        output_dir="genered_datasets",
        target_size=1000
    )
    collector.collect()
