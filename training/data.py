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
    def __init__(self, samples: list[tuple[int, int, float]]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        user_idx, item_idx, rating = self.samples[index]
        return (
            torch.tensor(user_idx, dtype=torch.long),
            torch.tensor(item_idx, dtype=torch.long),
            torch.tensor(rating, dtype=torch.float32),
        )


class MovieLensDataModule:
    def __init__(
        self,
        batch_size: int = 256,
        num_neg: int = 4,
        seed: int = 42,
        ratings_csv_path: str | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.num_neg = num_neg
        self.seed = seed
        self.ratings_csv_path = ratings_csv_path or resolve_ratings_path()

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

        rng = np.random.default_rng(self.seed)
        train_samples: list[tuple[int, int, float]] = []
        val_samples: list[tuple[int, int, float]] = []
        test_samples: list[tuple[int, int, float]] = []

        for _, group in ratings.groupby("user_idx"):
            group = group.sort_values("timestamp" if "timestamp" in group.columns else None)
            records = list(group.itertuples(index=False))
            if len(records) == 1:
                row = records[0]
                train_samples.append((int(row.user_idx), int(row.item_idx), float(row.rating)))
                continue
            if len(records) == 2:
                row_train = records[0]
                row_test = records[1]
                train_samples.append((int(row_train.user_idx), int(row_train.item_idx), float(row_train.rating)))
                test_samples.append((int(row_test.user_idx), int(row_test.item_idx), float(row_test.rating)))
                continue

            row_val = records[-2]
            row_test = records[-1]
            for row in records[:-2]:
                train_samples.append((int(row.user_idx), int(row.item_idx), float(row.rating)))
            val_samples.append((int(row_val.user_idx), int(row_val.item_idx), float(row_val.rating)))
            test_samples.append((int(row_test.user_idx), int(row_test.item_idx), float(row_test.rating)))

        rng.shuffle(train_samples)
        rng.shuffle(val_samples)
        rng.shuffle(test_samples)

        self.train_dataset = NCFDataset(train_samples)
        self.val_dataset = NCFDataset(val_samples)
        self.test_dataset = NCFDataset(test_samples)

    def train_dataloader(self) -> DataLoader:
        if self.train_dataset is None:
            raise RuntimeError("prepare_data must be called before train_dataloader")
        return DataLoader(self.train_dataset, batch_size=self.batch_size, shuffle=True)

    def val_dataloader(self) -> DataLoader:
        if self.val_dataset is None:
            raise RuntimeError("prepare_data must be called before val_dataloader")
        return DataLoader(self.val_dataset, batch_size=self.batch_size, shuffle=False)

    def test_dataloader(self) -> DataLoader:
        if self.test_dataset is None:
            raise RuntimeError("prepare_data must be called before test_dataloader")
        return DataLoader(self.test_dataset, batch_size=self.batch_size, shuffle=False)

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
