from __future__ import annotations

import random

import numpy as np
import torch

from tinyvision.reproducibility import seed_everything, split_generator


def test_seed_everything_pins_global_streams():
    seed_everything(123, deterministic=True)
    a = (random.random(), np.random.rand(), torch.rand(1).item())
    seed_everything(123, deterministic=True)
    b = (random.random(), np.random.rand(), torch.rand(1).item())
    assert a == b


def test_split_generator_is_stable():
    g1 = split_generator(7)
    g2 = split_generator(7)
    p1 = torch.randperm(1000, generator=g1)
    p2 = torch.randperm(1000, generator=g2)
    assert torch.equal(p1, p2)


def test_deterministic_flag_sets_cudnn():
    seed_everything(0, deterministic=True)
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False
