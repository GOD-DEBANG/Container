"""
Self-Evolving Model Trainer with Convergence Diagnostics.
Supports dynamic gradient updates, early stopping, and loss landscape tracking.
"""

from typing import Dict, Any, List
import numpy as np
from ..models.adaptive_classifier import AdaptiveClassifier


class SelfEvolvingTrainer:
    """
    Manages iterative optimization and self-adaptation steps for the model.
    """

    def __init__(self, model: AdaptiveClassifier, learning_rate: float = 0.05, momentum: float = 0.9):
        self.model = model
        self.lr = learning_rate
        self.momentum = momentum
        self.vW1 = np.zeros_like(model.W1)
        self.vb1 = np.zeros_like(model.b1)
        self.vW2 = np.zeros_like(model.W2)
        self.vb2 = np.zeros_like(model.b2)
        self.history: List[Dict[str, float]] = []

    def _sync_momentum_shapes(self):
        if self.vW1.shape != self.model.W1.shape:
            self.vW1 = np.zeros_like(self.model.W1)
            self.vb1 = np.zeros_like(self.model.b1)
            self.vW2 = np.zeros_like(self.model.W2)
            self.vb2 = np.zeros_like(self.model.b2)

    def train_epoch(self, X: np.ndarray, y: np.ndarray, batch_size: int = 64) -> Dict[str, float]:
        self._sync_momentum_shapes()
        n_samples = X.shape[0]
        indices = np.random.permutation(n_samples)
        epoch_losses = []

        for start_idx in range(0, n_samples, batch_size):
            batch_idx = indices[start_idx : start_idx + batch_size]
            X_batch, y_batch = X[batch_idx], y[batch_idx]
            bs = X_batch.shape[0]

            # Forward pass
            probs, cache = self.model.forward(X_batch)

            # Compute cross-entropy loss
            eps = 1e-12
            loss = -np.mean(np.log(probs[np.arange(bs), y_batch] + eps))
            epoch_losses.append(loss)

            # Backward pass
            d_scores = probs.copy()
            d_scores[np.arange(bs), y_batch] -= 1.0
            d_scores /= bs

            dW2 = np.dot(cache["a1"].T, d_scores)
            db2 = np.sum(d_scores, axis=0, keepdims=True)

            da1 = np.dot(d_scores, self.model.W2.T)
            dz1 = da1 * (cache["z1"] > 0)

            dW1 = np.dot(cache["X"].T, dz1)
            db1 = np.sum(dz1, axis=0, keepdims=True)

            # SGD with momentum
            self.vW1 = self.momentum * self.vW1 - self.lr * dW1
            self.vb1 = self.momentum * self.vb1 - self.lr * db1
            self.vW2 = self.momentum * self.vW2 - self.lr * dW2
            self.vb2 = self.momentum * self.vb2 - self.lr * db2

            self.model.W1 += self.vW1
            self.model.b1 += self.vb1
            self.model.W2 += self.vW2
            self.model.b2 += self.vb2

        mean_loss = float(np.mean(epoch_losses))
        preds = self.model.predict(X)
        acc = float(np.mean(preds == y))

        metrics = {"loss": mean_loss, "accuracy": acc}
        self.history.append(metrics)
        return metrics

    def evaluate(self, X_val: np.ndarray, y_val: np.ndarray) -> Dict[str, float]:
        probs, _ = self.model.forward(X_val)
        eps = 1e-12
        loss = -np.mean(np.log(probs[np.arange(len(y_val)), y_val] + eps))
        preds = np.argmax(probs, axis=1)
        acc = float(np.mean(preds == y_val))
        return {"val_loss": float(loss), "val_accuracy": float(acc)}
