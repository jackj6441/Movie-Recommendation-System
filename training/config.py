from dataclasses import dataclass


@dataclass(frozen=True)
class DataConfig:
    batch_size: int = 256
    num_neg: int = 0
    seed: int = 42
    ratings_csv_path: str | None = None
