"""
src/pulse/cells/adaptive_policy_cell.py

Adaptive Policy Cell.

Sits between RequestValidationCell and ResourcePolicyCell in the pipeline.
Uses the trained PolicyModel to override the ExecutionPolicy chosen by the
client with one that the ML model predicts will perform better, based on
historical container run metrics.

Behaviour
---------
- On every request it increments a counter.
- Every RETRAIN_EVERY_N requests (or if the model has never been trained) it
  loads all stored feedback samples from the store and retrains the model
  in a thread-pool executor so the async event loop stays unblocked.
- If the model is trained, it replaces params["policy"] with the prediction
  and records what it did in context.state["ml_policy_override"].
- If sklearn is absent or there are too few samples the cell is a transparent
  no-op — it does not raise and does not change any params.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..fabric.store_interface import StoreInterface
from ..ml.policy_model import PolicyModel, ML_FEEDBACK_STORE_KEY

# Retrain the model after this many new requests have passed through the cell.
RETRAIN_EVERY_N = 5


class AdaptivePolicyCell(BaseCell):
    name = "AdaptivePolicyCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(self, store: StoreInterface, model: PolicyModel) -> None:
        self.store = store
        self.model = model
        self._requests_since_train: int = 0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _maybe_retrain(self) -> None:
        """
        Load all feedback samples from the store and retrain the model
        in a thread-pool executor.  Resets the request counter on success.
        """
        samples = await self.store.get_events_since(ML_FEEDBACK_STORE_KEY, cursor=0)
        if not samples:
            return

        loop = asyncio.get_running_loop()
        n_used = await loop.run_in_executor(None, self.model.train, samples)
        if n_used > 0:
            self._requests_since_train = 0

    # ------------------------------------------------------------------
    # Pipeline interface
    # ------------------------------------------------------------------

    async def process(self, context: PulseContext) -> PulseContext:
        params: dict = context.state.get("validated_params", {})

        # Decide whether to retrain before predicting.
        self._requests_since_train += 1
        if self._requests_since_train >= RETRAIN_EVERY_N or not self.model.is_trained:
            await self._maybe_retrain()

        # If the model is not trained yet, pass through unchanged.
        if not self.model.is_trained:
            return context

        # Predict the best policy in a thread so the event loop stays free.
        loop = asyncio.get_running_loop()
        predicted_policy: str = await loop.run_in_executor(
            None, self.model.predict, params
        )

        original_policy: str = params.get("policy", "BALANCED")

        # Override the client-supplied policy with the ML recommendation.
        context.state["validated_params"]["policy"] = predicted_policy

        # Record what happened so downstream cells and logs can inspect it.
        context.state["ml_policy_override"] = {
            "original_policy": original_policy,
            "predicted_policy": predicted_policy,
            "model_samples": self.model.n_samples,
            "overridden": predicted_policy != original_policy,
        }

        return context
