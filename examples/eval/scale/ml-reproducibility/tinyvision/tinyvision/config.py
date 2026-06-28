from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TrainConfig:
    data_root: Path
    batch_size: int = 128
    epochs: int = 30
    lr: float = 0.1
    weight_decay: float = 5e-4
    momentum: float = 0.9
    num_workers: int = 4
    val_fraction: float = 0.1
    seed: int = 1337
    deterministic: bool = True
    augment: bool = True
    device: str = "cuda"
    out_dir: Path = field(default=Path("runs/latest"))

    @staticmethod
    def from_yaml(path: str | Path) -> "TrainConfig":
        raw = yaml.safe_load(Path(path).read_text())
        raw["data_root"] = Path(raw["data_root"])
        if "out_dir" in raw:
            raw["out_dir"] = Path(raw["out_dir"])
        return TrainConfig(**raw)

    def fingerprint(self) -> dict[str, object]:
        return {
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "lr": self.lr,
            "weight_decay": self.weight_decay,
            "momentum": self.momentum,
            "val_fraction": self.val_fraction,
            "seed": self.seed,
            "deterministic": self.deterministic,
            "augment": self.augment,
        }
