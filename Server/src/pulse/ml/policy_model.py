"""
src/pulse/ml/policy_model.py

Adaptive ExecutionPolicy predictor.

Uses a RandomForest classifier trained on historical ml_training_sample
events to predict the best ExecutionPolicy (LOW_CPU / BALANCED / PERFORMANCE)
for each incoming job, given its validated parameters.

Gracefully degrades to "BALANCED" when:
  - sklearn is not installed
  - Fewer than MIN_SAMPLES_TO_TRAIN successful runs are available
  - Any prediction error occurs

Thread-safe: all model reads/writes are protected by an RLock so the model
can be retrained in a background executor while inference runs concurrently.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

# Store key used by both this module and ExecutionDispatchCell.
ML_FEEDBACK_STORE_KEY = "__ml_feedback__"

# Minimum successful samples before the model will start making predictions.
MIN_SAMPLES_TO_TRAIN = 10

# Feature names in the order used by extract_features().
FEATURE_NAMES = [
    "target_size_bytes",
    "chunk_size_bytes",
    "subchunk_size_bytes",
    "seed",
]

_DEFAULT_POLICY = "BALANCED"


class PolicyModel:
    """
    Wraps a scikit-learn RandomForestClassifier to predict ExecutionPolicy.

    Lifecycle
    ---------
    1. Start untrained — predict() returns DEFAULT_POLICY ("BALANCED").
    2. After MIN_SAMPLES_TO_TRAIN successful runs are stored in the feedback
       log, train() builds the first model.
    3. AdaptivePolicyCell calls train() periodically (every RETRAIN_EVERY_N
       requests) so the model keeps improving as more data arrives.
    """

    def __init__(self) -> None:
        self._clf: Optional[Any] = None   # sklearn RandomForestClassifier
        self._lock = threading.RLock()
        self._trained = False
        self._n_samples = 0

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_features(params: Dict[str, Any]) -> List[float]:
        """Convert a validated_params dict into a flat numeric feature vector."""
        return [
            float(params.get("target_size_bytes", 0)),
            float(params.get("chunk_size_bytes", 1_048_576)),
            float(params.get("subchunk_size_bytes", 262_144)),
            float(params.get("seed", 42)),
        ]

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, samples: List[Dict[str, Any]]) -> int:
        """
        (Re)train the RandomForest from a list of ml_training_sample event dicts.

        Only successful runs are used as training examples so the model learns
        which policies produce good outcomes rather than memorising failures.

        Parameters
        ----------
        samples : list of dicts, each with "features" and "outcomes" sub-dicts.

        Returns
        -------
        int — number of samples actually used for training (0 if skipped).
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            return 0

        X: List[List[float]] = []
        y: List[str] = []

        for s in samples:
            features = s.get("features", {})
            outcomes = s.get("outcomes", {})

            if not outcomes.get("success", False):
                continue   # skip failed runs

            X.append(self.extract_features(features))
            y.append(features.get("policy", _DEFAULT_POLICY))

        if len(X) < MIN_SAMPLES_TO_TRAIN:
            return 0

        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            class_weight="balanced",
        )
        clf.fit(X, y)

        with self._lock:
            self._clf = clf
            self._trained = True
            self._n_samples = len(X)

        return len(X)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, params: Dict[str, Any]) -> str:
        """
        Predict the best ExecutionPolicy for the given validated_params dict.

        Returns the DEFAULT_POLICY string when the model is not yet trained
        or sklearn is unavailable — so callers never need to guard against None.
        """
        with self._lock:
            if not self._trained or self._clf is None:
                return _DEFAULT_POLICY

        try:
            features = [self.extract_features(params)]
            with self._lock:
                result: str = self._clf.predict(features)[0]
            return result
        except Exception:
            return _DEFAULT_POLICY

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_trained(self) -> bool:
        with self._lock:
            return self._trained

    @property
    def n_samples(self) -> int:
        with self._lock:
            return self._n_samples
