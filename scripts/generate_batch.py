#!/usr/bin/env python3
"""
Generate a batch of PCB dataset samples locally.

Usage:
    python scripts/generate_batch.py --num-samples 10 --output-dir data/output
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pcb_dataset.pipeline import Pipeline
from pcb_dataset.placement import PlacementConfig
from pcb_dataset.renderer import RenderConfig
from pcb_dataset.pipeline import PipelineConfig
from pcb_dataset.utils.config import load_config
from pcb_dataset.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate batch of PCB dataset samples")
    parser.add_argument("--num-samples", type=int, required=True, help="Number of samples to generate")
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).parent.parent / "config",
        help="Configuration directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Output directory",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
    )
    parser.add_argument(
        "--start-id", type=int, default=0, help="Starting sample ID"
    )
    args = parser.parse_args()

    # Setup logging
    log_file = args.output_dir / "logs" / "batch_generation.log"
    setup_logging(level=args.log_level, log_file=log_file)

    logger.info(f"Starting batch generation: {args.num_samples} samples")

    # Load configurations
    placement_config_dict = load_config(args.config_dir, "placement")
    render_config_dict = load_config(args.config_dir, "render")
    pipeline_config_dict = load_config(args.config_dir, "pipeline")

    placement_config = PlacementConfig.from_dict(placement_config_dict)
    render_config = RenderConfig.from_dict(render_config_dict)
    pipeline_config = PipelineConfig.from_dict(pipeline_config_dict)

    # Initialize pipeline
    pipeline = Pipeline(
        placement_config=placement_config,
        render_config=render_config,
        pipeline_config=pipeline_config,
        base_dir=args.output_dir,
    )

    # Generate samples
    success_count = 0
    failed_samples = []

    for i in range(args.num_samples):
        sample_id = args.start_id + i

        logger.info(f"Generating sample {sample_id} ({i+1}/{args.num_samples})")

        output_path = pipeline.generate_sample(sample_id)

        if output_path:
            success_count += 1
        else:
            failed_samples.append(sample_id)

    # Summary
    logger.info("=" * 60)
    logger.info("Batch generation complete")
    logger.info(f"  Success: {success_count}/{args.num_samples}")
    logger.info(f"  Failed: {len(failed_samples)}")
    if failed_samples:
        logger.info(f"  Failed sample IDs: {failed_samples}")
    logger.info("=" * 60)

    # Exit code based on success rate
    if success_count == args.num_samples:
        sys.exit(0)
    elif success_count > 0:
        sys.exit(2)  # Partial success
    else:
        sys.exit(1)  # Total failure


if __name__ == "__main__":
    main()
