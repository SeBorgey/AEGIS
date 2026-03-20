from pathlib import Path

DATASETS_DIR = Path("datasets")
EASY_DATASET = DATASETS_DIR / "easy.json"
MIDDLE_DATASET = DATASETS_DIR / "middle.json"
HARD_DATASET = DATASETS_DIR / "hard.json"

NUM_RUNS = 3
NUM_JUDGE_RUNS = 3
DEFAULT_TOP_K = 3

FORMATTER_MAX_LEN = 32_000
AUTOINTENT_PRESET = "classic-light"
