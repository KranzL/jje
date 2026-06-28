from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn

from .config import TrainConfig
from .data import build_dataloaders
from .model import SmallConvNet
from .reproducibility import seed_everything


def _accuracy(logits: torch.Tensor, targets: torch.Tensor) -> float:
    preds = logits.argmax(dim=1)
    return (preds == targets).float().mean().item()


def evaluate(model: nn.Module, loader, device: str) -> float:
    model.eval()
    total, correct = 0, 0
    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            logits = model(images)
            correct += (logits.argmax(dim=1) == targets).sum().item()
            total += targets.numel()
    return correct / max(total, 1)


def train(cfg: TrainConfig) -> dict[str, object]:
    seed_everything(cfg.seed, deterministic=cfg.deterministic)

    device = cfg.device if torch.cuda.is_available() else "cpu"
    train_loader, val_loader, class_weights = build_dataloaders(cfg)

    model = SmallConvNet(num_classes=int(class_weights.numel())).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    optimizer = torch.optim.SGD(
        model.parameters(),
        lr=cfg.lr,
        momentum=cfg.momentum,
        weight_decay=cfg.weight_decay,
        nesterov=True,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg.epochs)

    history = []
    best_acc = 0.0
    for epoch in range(cfg.epochs):
        model.train()
        running = 0.0
        for images, targets in train_loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
            running += loss.item()
        scheduler.step()

        val_acc = evaluate(model, val_loader, device)
        best_acc = max(best_acc, val_acc)
        history.append({"epoch": epoch, "loss": running / len(train_loader), "val_acc": val_acc})

    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out_dir / "model.pt")
    report = {"config": cfg.fingerprint(), "best_val_acc": best_acc, "history": history}
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = TrainConfig.from_yaml(args.config)
    report = train(cfg)
    print(json.dumps({"best_val_acc": report["best_val_acc"]}))


if __name__ == "__main__":
    main()
