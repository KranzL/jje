from __future__ import annotations

import numpy as np

_MEAN = np.array([0.4914, 0.4822, 0.4465], dtype="float32").reshape(3, 1, 1)
_STD = np.array([0.2470, 0.2435, 0.2616], dtype="float32").reshape(3, 1, 1)


def _to_chw(array: np.ndarray) -> np.ndarray:
    if array.ndim == 2:
        array = np.stack([array, array, array], axis=0)
    elif array.shape[-1] == 3:
        array = np.transpose(array, (2, 0, 1))
    return np.ascontiguousarray(array)


def _normalize(image: np.ndarray) -> np.ndarray:
    image = image / 255.0
    return (image - _MEAN) / _STD


def _random_horizontal_flip(image: np.ndarray, p: float = 0.5) -> np.ndarray:
    if np.random.rand() < p:
        return image[:, :, ::-1]
    return image


def _random_crop(image: np.ndarray, padding: int = 4) -> np.ndarray:
    _, h, w = image.shape
    padded = np.pad(
        image,
        ((0, 0), (padding, padding), (padding, padding)),
        mode="reflect",
    )
    top = np.random.randint(0, 2 * padding + 1)
    left = np.random.randint(0, 2 * padding + 1)
    return padded[:, top : top + h, left : left + w]


class TrainPipeline:
    def __init__(self, augment: bool = True) -> None:
        self.augment = augment

    def __call__(self, array: np.ndarray) -> np.ndarray:
        image = _to_chw(array)
        if self.augment:
            image = _random_crop(image)
            image = _random_horizontal_flip(image)
        image = _normalize(image)
        return np.ascontiguousarray(image)


class EvalPipeline:
    def __call__(self, array: np.ndarray) -> np.ndarray:
        image = _to_chw(array)
        image = _normalize(image)
        return np.ascontiguousarray(image)
