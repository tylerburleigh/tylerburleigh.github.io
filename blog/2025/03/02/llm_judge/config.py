from dataclasses import dataclass
from pathlib import Path

# Get the project root directory (parent of llm_judge directory)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

@dataclass
class ExperimentConfig:
    SAMPLE_SIZE: int = 32
    RANDOM_SEED: int = 42
    MAX_TOKENS: int = 256
    NUM_RUNS: int = 1
    RESULTS_JSONL: Path = PROJECT_ROOT / 'experiment_results.jsonl'
    RESULTS_TXT: Path = PROJECT_ROOT / 'experiment_results.txt'

@dataclass
class FileConfig:
    DATASET_PATH: Path = PROJECT_ROOT / 'data/pairwise_evaluator_dataset.json'
    RESULTS_JSONL: Path = PROJECT_ROOT / 'experiment_results.jsonl'
    RESULTS_TXT: Path = PROJECT_ROOT / 'experiment_results.txt' 