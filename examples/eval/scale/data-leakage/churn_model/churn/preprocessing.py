"""Stateful encoders used inside the cross-validated pipeline.

Every estimator here learns its parameters in ``fit`` and applies them in
``transform`` so that, when dropped into an sklearn Pipeline, they are refit
on each training fold and never see validation rows during fitting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class TargetMeanEncoder(BaseEstimator, TransformerMixin):
    """Smoothed target-mean encoding for high-cardinality categoricals.

    The mapping is computed in ``fit`` from the supplied ``y`` only, so the
    encoder must be placed in a CV pipeline to remain leakage-free.
    """

    def __init__(self, smoothing: float = 10.0):
        self.smoothing = smoothing

    def fit(self, X, y):
        X = pd.DataFrame(X).reset_index(drop=True)
        y = pd.Series(np.asarray(y), name="_target").reset_index(drop=True)
        self.columns_ = list(X.columns)
        self.prior_ = float(y.mean())
        self.maps_ = {}
        for col in self.columns_:
            stats = y.groupby(X[col]).agg(["mean", "count"])
            weight = stats["count"] / (stats["count"] + self.smoothing)
            blended = weight * stats["mean"] + (1 - weight) * self.prior_
            self.maps_[col] = blended.to_dict()
        return self

    def transform(self, X):
        X = pd.DataFrame(X).reset_index(drop=True)
        out = np.empty((len(X), len(self.columns_)), dtype=float)
        for j, col in enumerate(self.columns_):
            mapped = X[col].map(self.maps_[col])
            out[:, j] = mapped.fillna(self.prior_).to_numpy()
        return out

    def get_feature_names_out(self, input_features=None):
        return np.asarray([f"{c}_te" for c in self.columns_], dtype=object)


class FrequencyEncoder(BaseEstimator, TransformerMixin):
    """Replace each category by its in-sample relative frequency."""

    def __init__(self):
        pass

    def fit(self, X, y=None):
        X = pd.DataFrame(X).reset_index(drop=True)
        self.columns_ = list(X.columns)
        self.freqs_ = {}
        n = len(X)
        for col in self.columns_:
            self.freqs_[col] = (X[col].value_counts() / n).to_dict()
        return self

    def transform(self, X):
        X = pd.DataFrame(X).reset_index(drop=True)
        out = np.empty((len(X), len(self.columns_)), dtype=float)
        for j, col in enumerate(self.columns_):
            out[:, j] = X[col].map(self.freqs_[col]).fillna(0.0).to_numpy()
        return out

    def get_feature_names_out(self, input_features=None):
        return np.asarray([f"{c}_freq" for c in self.columns_], dtype=object)
