"""
main.py

Thin standalone demonstration launcher.
Instantiates the dataset generation service and optionally prints the output.
"""

import logging
import sys
from pathlib import Path

from services.dataset_generation_service import DatasetGenerationService
from resource_engine.resource_budget import ExecutionPolicy

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def main() -> int:
    service = DatasetGenerationService()

    # Generate a 10 MiB dataset for demonstration
    target_size_bytes = 10 * 1024 * 1024
    chunk_size_bytes = 1 * 1024 * 1024
    subchunk_size_bytes = 256 * 1024
    
    report = service.generate(
        target_size_bytes=target_size_bytes,
        chunk_size_bytes=chunk_size_bytes,
        subchunk_size_bytes=subchunk_size_bytes,
        seed=1337,
        policy=ExecutionPolicy.BALANCED,
    )

    try:
        from output.output_console import OutputConsole
        OutputConsole.display(report)
    except ImportError:
        # Core engine works without output adapter
        pass

    return 0 if report.success else 1

if __name__ == "__main__":
    sys.exit(main())
