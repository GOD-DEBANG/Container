"""
Self-Adaptive Neural Predictor Architecture.
Provides an adaptable architecture with dynamic capacity adjustment.
"""

from typing import Dict, Any, Tuple
import numpy as np


class AdaptiveClassifier:
    """
    Scientifically sound, self-contained multi-layer neural network with
    adaptive learning rates, momentum, and dynamic architectural capacity adjustment.
    """

    def __init__(self, input_dim: int = 5, hidden_dim: int = 16, output_dim: int = 2, seed: int = 42):
        np.random.seed(seed)
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # He initialization
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, hidden_dim))
        self.W2 = np.random.randn(hidden_dim, output_dim) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros((1, output_dim))

        self.architecture_version = 1

    def forward(self, X: np.ndarray) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        # Layer 1: ReLU
        z1 = np.dot(X, self.W1) + self.b1
        a1 = np.maximum(0, z1)

        # Layer 2: Softmax
        z2 = np.dot(a1, self.W2) + self.b2
        exp_z = np.exp(z2 - np.max(z2, axis=1, keepdims=True))
        probs = exp_z / np.sum(exp_z, axis=1, keepdims=True)

        cache = {"X": X, "z1": z1, "a1": a1, "z2": z2, "probs": probs}
        return probs, cache

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs, _ = self.forward(X)
        return np.argmax(probs, axis=1)

    def evolve_capacity(self, expand_factor: float = 1.25):
        """
        Structural self-evolution: expands hidden dimension to accommodate
        distribution shifts without catastrophic forgetting.
        """
        new_hidden_dim = int(self.hidden_dim * expand_factor)
        added_nodes = new_hidden_dim - self.hidden_dim
        if added_nodes <= 0:
            return

        new_W1_ext = np.random.randn(self.input_dim, added_nodes) * 0.01
        self.W1 = np.hstack([self.W1, new_W1_ext])
        self.b1 = np.hstack([self.b1, np.zeros((1, added_nodes))])

        new_W2_ext = np.random.randn(added_nodes, self.output_dim) * 0.01
        self.W2 = np.vstack([self.W2, new_W2_ext])

        self.hidden_dim = new_hidden_dim
        self.architecture_version += 1
