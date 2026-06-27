import argparse
import json
import os
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset


@dataclass
class RunConfig:
    seed: int = 1337
    epochs: int = 30
    batch_size: int = 256
    lr: float = 3e-4
    weight_decay: float = 1e-4
    num_workers: int = 8
    width: int = 128
    augment_strength: float = 0.15
    data_root: str = "data/shards"


def resolve_device() -> torch.device:
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        return torch.device("cuda")
    return torch.device("cpu")


def configure_determinism(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class ShardDataset(Dataset):
    def __init__(self, root: str, split: str, augment_strength: float):
        self.records = sorted(Path(root, split).glob("*.npz"))
        if not self.records:
            self.records = [None] * 4096
        self.split = split
        self.augment_strength = augment_strength

    def __len__(self) -> int:
        return len(self.records)

    def _load(self, idx: int):
        rec = self.records[idx]
        if rec is None:
            x = np.random.rand(3, 32, 32).astype(np.float32)
            y = int(np.random.randint(0, 10))
            return x, y
        with np.load(rec) as f:
            return f["x"].astype(np.float32), int(f["y"])

    def _augment(self, x: np.ndarray) -> np.ndarray:
        if self.split != "train":
            return x
        noise = np.random.normal(0.0, self.augment_strength, size=x.shape)
        x = x + noise.astype(np.float32)
        if np.random.rand() < 0.5:
            x = x[:, :, ::-1].copy()
        return x

    def __getitem__(self, idx: int):
        x, y = self._load(idx)
        x = self._augment(x)
        return torch.from_numpy(x), y


class TinyConvNet(nn.Module):
    def __init__(self, width: int, num_classes: int = 10):
        super().__init__()
        self.stem = nn.Conv2d(3, width, 3, padding=1)
        self.block = nn.Sequential(
            nn.Conv2d(width, width, 3, padding=1),
            nn.BatchNorm2d(width),
            nn.ReLU(inplace=True),
            nn.Conv2d(width, width, 3, padding=1),
            nn.BatchNorm2d(width),
            nn.ReLU(inplace=True),
        )
        self.head = nn.Linear(width, num_classes)

    def forward(self, x):
        x = F.relu(self.stem(x))
        x = self.block(x)
        x = F.adaptive_avg_pool2d(x, 1).flatten(1)
        return self.head(x)


def make_loaders(cfg: RunConfig):
    gen = torch.Generator()
    gen.manual_seed(cfg.seed)
    train_ds = ShardDataset(cfg.data_root, "train", cfg.augment_strength)
    val_ds = ShardDataset(cfg.data_root, "val", cfg.augment_strength)
    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.batch_size,
        shuffle=True,
        num_workers=cfg.num_workers,
        pin_memory=True,
        drop_last=True,
        generator=gen,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        pin_memory=True,
    )
    return train_loader, val_loader


def run_epoch(model, loader, optimizer, device, train: bool):
    model.train(train)
    total, correct, loss_sum = 0, 0, 0.0
    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        with torch.set_grad_enabled(train):
            logits = model(x)
            loss = F.cross_entropy(logits, y)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        loss_sum += float(loss) * y.size(0)
        correct += int((logits.argmax(1) == y).sum())
        total += y.size(0)
    return loss_sum / max(total, 1), correct / max(total, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", type=str, default="runs/latest")
    args = parser.parse_args()

    cfg = RunConfig()
    if args.epochs is not None:
        cfg.epochs = args.epochs
    if args.seed is not None:
        cfg.seed = args.seed

    configure_determinism(cfg.seed)
    device = resolve_device()

    model = TinyConvNet(cfg.width).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
    )
    train_loader, val_loader = make_loaders(cfg)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    history = []
    start = time.time()
    for epoch in range(cfg.epochs):
        tr_loss, tr_acc = run_epoch(model, train_loader, optimizer, device, True)
        va_loss, va_acc = run_epoch(model, val_loader, optimizer, device, False)
        history.append(
            {
                "epoch": epoch,
                "train_loss": tr_loss,
                "train_acc": tr_acc,
                "val_loss": va_loss,
                "val_acc": va_acc,
            }
        )

    summary = {
        "config": asdict(cfg),
        "device": str(device),
        "wall_seconds": round(time.time() - start, 2),
        "final_val_acc": history[-1]["val_acc"] if history else None,
        "history": history,
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    torch.save(model.state_dict(), out / "model.pt")


if __name__ == "__main__":
    main()
