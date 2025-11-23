#!/usr/bin/env python3
"""
Generate a single PCB dataset sample.

Usage:
    python scripts/generate_single.py --sample-id 0 --output-dir data/output
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
from pcb_dataset.utils.logging import setup_logging


def main():
    parser = argparse.ArgumentParser(description="Generate single PCB dataset sample")
    parser.add_argument("--sample-id", type=int, required=True, help="Sample ID")
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
    args = parser.parse_args()

    # Setup logging
    log_file = args.output_dir / "logs" / f"sample_{args.sample_id:06d}.log"
    setup_logging(level=args.log_level, log_file=log_file)

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

    # Generate sample
    output_path = pipeline.generate_sample(args.sample_id)

    if output_path:
        print(f"Success: {output_path}")
        sys.exit(0)
    else:
        print(f"Failed to generate sample {args.sample_id}")
        sys.exit(1)


if __name__ == "__main__":
    main()
