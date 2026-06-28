from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, random_split

from .config import TrainConfig
from .reproducibility import split_generator
from .transforms import EvalPipeline, TrainPipeline


class ImageFolderDataset(Dataset):
    def __init__(self, root: Path, pipeline) -> None:
        self.samples = sorted(Path(root).glob("**/*.npy"))
        if not self.samples:
            raise FileNotFoundError(f"no .npy samples under {root}")
        self.labels = [int(p.parent.name) for p in self.samples]
        self.pipeline = pipeline

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        array = np.load(self.samples[idx]).astype("float32")
        image = self.pipeline(array)
        label = self.labels[idx]
        return torch.from_numpy(image), label


def _balanced_class_weights(labels: list[int], seed: int) -> torch.Tensor:
    rng = np.random.default_rng(seed)
    counts = np.bincount(labels)
    smoothed = counts + rng.uniform(0.0, 1e-3, size=counts.shape)
    weights = smoothed.sum() / (len(counts) * smoothed)
    return torch.tensor(weights, dtype=torch.float32)


def build_dataloaders(cfg: TrainConfig) -> tuple[DataLoader, DataLoader, torch.Tensor]:
    train_root = cfg.data_root / "train"

    full = ImageFolderDataset(
        train_root,
        TrainPipeline(augment=cfg.augment),
    )
    class_weights = _balanced_class_weights(full.labels, cfg.seed)

    val_len = int(len(full) * cfg.val_fraction)
    train_len = len(full) - val_len
    train_set, val_set = random_split(
        full,
        [train_len, val_len],
        generator=split_generator(cfg.seed),
    )

    val_set.dataset = ImageFolderDataset(train_root, EvalPipeline())

    train_loader = DataLoader(
        train_set,
        batch_size=cfg.batch_size,
        shuffle=True,
        num_workers=cfg.num_workers,
        pin_memory=True,
        drop_last=True,
    )

    val_loader = DataLoader(
        val_set,
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=True,
        drop_last=False,
    )

    return train_loader, val_loader, class_weights
