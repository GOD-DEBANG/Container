"""
Executable Research Script: Demonstrates the End-to-End Self-Evolving ML Loop
connected with the Virtual Container Engine.
"""

import sys
import logging
from pathlib import Path

# Set up logging with professional scientist style
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ExperimentRunner")

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.configs.base_config import ResearchConfig
from ml.evolution.controller import AutonomousEvolutionLoop


def main():
    logger.info("Initializing Self-Evolving AI/ML Experimentation Harness...")

    config = ResearchConfig(
        experiment_id="autonomous_evolution_run_001",
        seed=1337,
    )

    logger.info(f"Target Checkpoints Dir: {config.checkpoints_dir}")
    logger.info(f"Target Metrics Dir: {config.metrics_dir}")

    # Instantiate autonomous closed loop
    loop = AutonomousEvolutionLoop(config=config)

    # Run 3 self-evolving generations
    result = loop.run_evolution_cycle(generations=3)

    logger.info("Self-Evolution Experiments Completed Successfully!")
    logger.info(f"Final Architecture Version: {result['final_architecture_version']}")
    logger.info(f"Final Model Capacity (Hidden Neurons): {result['final_hidden_dim']}")
    for step in result["history"]:
        logger.info(
            f"Generation {step['generation']}: Hidden Dim = {step['hidden_dim']}, "
            f"Val Loss = {step['metrics']['val_loss']:.4f}, "
            f"Val Acc = {step['metrics']['val_accuracy']:.4f}"
        )


if __name__ == "__main__":
    main()
