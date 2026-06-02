import os
from typing import Iterable

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


def resolve_ratings_path() -> str:
    env_path = os.getenv("RATINGS_CSV_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    default_path = "data/ml-latest-small/ratings.csv"
    if os.path.exists(default_path):
        return default_path
    fallback_path = "ml-latest-small/ratings.csv"
    return fallback_path


class NCFDataset(Dataset):
    """Array-backed dataset.

    Stores interactions as three parallel numpy arrays rather than a Python list
    of tuples so that tens of millions of rows fit in memory without per-row
    Python object overhead.
    """

    def __init__(self, users: np.ndarray, items: np.ndarray, ratings: np.ndarray):
        self.users = np.ascontiguousarray(users, dtype=np.int64)
        self.items = np.ascontiguousarray(items, dtype=np.int64)
        self.ratings = np.ascontiguousarray(ratings, dtype=np.float32)

    def __len__(self) -> int:
        return int(self.users.shape[0])

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return (
            torch.tensor(self.users[index], dtype=torch.long),
            torch.tensor(self.items[index], dtype=torch.long),
            torch.tensor(self.ratings[index], dtype=torch.float32),
        )


class MovieLensDataModule:
    def __init__(
        self,
        batch_size: int = 256,
        num_neg: int = 4,
        seed: int = 42,
        ratings_csv_path: str | None = None,
        num_workers: int = 0,
        pin_memory: bool = False,
    ) -> None:
        self.batch_size = batch_size
        self.num_neg = num_neg
        self.seed = seed
        self.ratings_csv_path = ratings_csv_path or resolve_ratings_path()
        self.num_workers = num_workers
        self.pin_memory = pin_memory

        self.num_users = 0
        self.num_items = 0
        self.user_id_map: dict[int, int] = {}
        self.item_id_map: dict[int, int] = {}

        self.train_dataset: NCFDataset | None = None
        self.val_dataset: NCFDataset | None = None
        self.test_dataset: NCFDataset | None = None

    def prepare_data(self) -> None:
        ratings = pd.read_csv(self.ratings_csv_path)
        if not {"userId", "movieId", "rating"}.issubset(ratings.columns):
            raise ValueError("ratings CSV must contain userId, movieId, rating")

        user_codes, user_uniques = pd.factorize(ratings["userId"], sort=True)
        item_codes, item_uniques = pd.factorize(ratings["movieId"], sort=True)
        ratings = ratings.copy()
        ratings["user_idx"] = user_codes
        ratings["item_idx"] = item_codes

        self.num_users = len(user_uniques)
        self.num_items = len(item_uniques)
        self.user_id_map = {int(uid): int(idx) for idx, uid in enumerate(user_uniques)}
        self.item_id_map = {int(mid): int(idx) for idx, mid in enumerate(item_uniques)}

        # Chronological per-user split, vectorized so it scales to tens of
        # millions of rows. For each user the last interaction is test, the
        # second-to-last is validation (only when the user has >= 3), and the
        # rest are training. This matches the original per-user loop exactly.
        sort_keys = ["user_idx"]
        if "timestamp" in ratings.columns:
            sort_keys.append("timestamp")
        ratings = ratings.sort_values(sort_keys, kind="stable").reset_index(drop=True)

        grouped = ratings.groupby("user_idx", sort=True)
        pos_from_start = grouped.cumcount().to_numpy()
        group_size = grouped["user_idx"].transform("size").to_numpy()
        pos_from_end = group_size - 1 - pos_from_start

        is_test = (group_size >= 2) & (pos_from_end == 0)
        is_val = (group_size >= 3) & (pos_from_end == 1)
        is_train = ~(is_test | is_val)

        users = ratings["user_idx"].to_numpy(dtype=np.int64)
        items = ratings["item_idx"].to_numpy(dtype=np.int64)
        rates = ratings["rating"].to_numpy(dtype=np.float32)

        rng = np.random.default_rng(self.seed)

        def _make_dataset(mask: np.ndarray) -> NCFDataset:
            idx = np.flatnonzero(mask)
            rng.shuffle(idx)
            return NCFDataset(users[idx], items[idx], rates[idx])

        self.train_dataset = _make_dataset(is_train)
        self.val_dataset = _make_dataset(is_val)
        self.test_dataset = _make_dataset(is_test)

    def train_dataloader(self) -> DataLoader:
        if self.train_dataset is None:
            raise RuntimeError("prepare_data must be called before train_dataloader")
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            persistent_workers=self.num_workers > 0,
        )

    def val_dataloader(self) -> DataLoader:
        if self.val_dataset is None:
            raise RuntimeError("prepare_data must be called before val_dataloader")
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            persistent_workers=self.num_workers > 0,
        )

    def test_dataloader(self) -> DataLoader:
        if self.test_dataset is None:
            raise RuntimeError("prepare_data must be called before test_dataloader")
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            persistent_workers=self.num_workers > 0,
        )

    def sanity_check(self) -> None:
        if self.train_dataset is None or self.val_dataset is None or self.test_dataset is None:
            raise RuntimeError("prepare_data must be called before sanity_check")

        train_len = len(self.train_dataset)
        val_len = len(self.val_dataset)
        test_len = len(self.test_dataset)
        print(f"num_users: {self.num_users}")
        print(f"num_items: {self.num_items}")
        print(f"train/val/test: {train_len}/{val_len}/{test_len}")

        batch = next(iter(self.train_dataloader()))
        users, items, ratings = batch
        print(f"batch shapes: users {users.shape}, items {items.shape}, ratings {ratings.shape}")
        print(f"rating stats: min {ratings.min().item():.2f}, max {ratings.max().item():.2f}")


def iter_batches(dataloader: DataLoader) -> Iterable[tuple[torch.Tensor, ...]]:
    for batch in dataloader:
        yield batch
