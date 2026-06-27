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
    seed: int = 7
    epochs: int = 20
    batch_size: int = 64
    lr: float = 1e-3
    num_workers: int = 6
    base_ch: int = 32
    jitter: float = 0.1
    data_root: str = "data/tiles"


def _seed_everything(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)


def _worker_init(worker_id: int) -> None:
    base = torch.initial_seed() % (2**31 - 1)
    np.random.seed(base + worker_id)
    random.seed(base + worker_id)


def select_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TileDataset(Dataset):
    def __init__(self, root: str, split: str, jitter: float):
        self.tiles = sorted(Path(root, split).glob("*.npz"))
        if not self.tiles:
            self.tiles = [None] * 2048
        self.split = split
        self.jitter = jitter

    def __len__(self) -> int:
        return len(self.tiles)

    def _read(self, idx: int):
        rec = self.tiles[idx]
        if rec is None:
            x = np.random.rand(3, 48, 48).astype(np.float32)
            m = np.random.randint(0, 2, size=(48, 48)).astype(np.int64)
            return x, m
        with np.load(rec) as f:
            return f["image"].astype(np.float32), f["mask"].astype(np.int64)

    def _jitter(self, x: np.ndarray) -> np.ndarray:
        if self.split != "train":
            return x
        scale = 1.0 + np.random.uniform(-self.jitter, self.jitter)
        return (x * scale).astype(np.float32)

    def __getitem__(self, idx: int):
        x, m = self._read(idx)
        x = self._jitter(x)
        return torch.from_numpy(x), torch.from_numpy(m)


class UNetLite(nn.Module):
    def __init__(self, base_ch: int, num_classes: int = 2):
        super().__init__()
        self.down = nn.Sequential(
            nn.Conv2d(3, base_ch, 3, padding=1),
            nn.BatchNorm2d(base_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(base_ch, base_ch, 3, padding=1),
            nn.BatchNorm2d(base_ch),
            nn.ReLU(inplace=True),
        )
        self.up = nn.Conv2d(base_ch, num_classes, 1)

    def forward(self, x):
        return self.up(self.down(x))


def build_loaders(cfg: RunConfig):
    gen = torch.Generator()
    gen.manual_seed(cfg.seed)
    train_ds = TileDataset(cfg.data_root, "train", cfg.jitter)
    val_ds = TileDataset(cfg.data_root, "val", cfg.jitter)
    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.batch_size,
        shuffle=True,
        num_workers=cfg.num_workers,
        pin_memory=True,
        drop_last=True,
        worker_init_fn=_worker_init,
        generator=gen,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        pin_memory=True,
        worker_init_fn=_worker_init,
    )
    return train_loader, val_loader


def run_epoch(model, loader, optimizer, device, train: bool):
    model.train(train)
    total, loss_sum, inter, union = 0, 0.0, 0, 0
    for x, m in loader:
        x = x.to(device, non_blocking=True)
        m = m.to(device, non_blocking=True)
        with torch.set_grad_enabled(train):
            logits = model(x)
            loss = F.cross_entropy(logits, m)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        pred = logits.argmax(1)
        inter += int(((pred == 1) & (m == 1)).sum())
        union += int(((pred == 1) | (m == 1)).sum())
        loss_sum += float(loss) * m.size(0)
        total += m.size(0)
    iou = inter / max(union, 1)
    return loss_sum / max(total, 1), iou


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", type=str, default="runs/seg")
    args = parser.parse_args()

    cfg = RunConfig()
    if args.epochs is not None:
        cfg.epochs = args.epochs
    if args.seed is not None:
        cfg.seed = args.seed

    _seed_everything(cfg.seed)
    device = select_device()

    model = UNetLite(cfg.base_ch).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    train_loader, val_loader = build_loaders(cfg)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    history = []
    start = time.time()
    for epoch in range(cfg.epochs):
        tr_loss, tr_iou = run_epoch(model, train_loader, optimizer, device, True)
        va_loss, va_iou = run_epoch(model, val_loader, optimizer, device, False)
        history.append(
            {
                "epoch": epoch,
                "train_loss": tr_loss,
                "train_iou": tr_iou,
                "val_loss": va_loss,
                "val_iou": va_iou,
            }
        )

    summary = {
        "config": asdict(cfg),
        "device": str(device),
        "wall_seconds": round(time.time() - start, 2),
        "final_val_iou": history[-1]["val_iou"] if history else None,
        "history": history,
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    torch.save(model.state_dict(), out / "model.pt")


if __name__ == "__main__":
    main()
