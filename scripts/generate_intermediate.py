#!/usr/bin/env python3
"""
Generate intermediate .blend files (CPU-only tasks).

This script runs steps 1-4 of the pipeline:
1. Component placement
2. Board creation (KiCad)
3. PCB export (.pcb3d)
4. Blender import

Output: .blend files ready for GPU rendering

Usage:
    python scripts/generate_intermediate.py --num-samples 100 --output-dir data/intermediate
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pcb_dataset.placement import PerlinPlacer, PlacementConfig
from pcb_dataset.board import BoardCreator
from pcb_dataset.exporter import PCB3DExporter
from pcb_dataset.importer import BlenderImporter
from pcb_dataset.utils.config import load_config
from pcb_dataset.utils.logging import setup_logging, get_logger
from pcb_dataset.utils.paths import PathManager
from pcb_dataset.utils.validation import validate_kicad_file, validate_pcb3d_file
from pcb_dataset.pipeline import PipelineConfig
import subprocess

logger = get_logger(__name__)


def generate_intermediate_sample(
    sample_id: int,
    placer: PerlinPlacer,
    board_creator: BoardCreator,
    exporter: PCB3DExporter,
    paths: PathManager,
    placement_config: PlacementConfig,
    pipeline_config: PipelineConfig,
    base_seed: int,
):
    """
    Generate intermediate .blend file for a single sample.

    Args:
        sample_id: Sample ID
        placer: Component placer instance
        board_creator: Board creator instance
        exporter: PCB3D exporter instance
        paths: Path manager instance
        placement_config: Placement configuration
        pipeline_config: Pipeline configuration
        base_seed: Base seed for reproducibility

    Returns:
        Path to generated .blend file (or None if failed)
    """
    logger.info(f"=" * 60)
    logger.info(f"Generating intermediate for sample {sample_id}")
    logger.info(f"=" * 60)

    try:
        # Set seed for reproducibility
        if pipeline_config.auto_increment:
            seed = base_seed + sample_id
        else:
            seed = base_seed
        placer.config.seed = seed

        # Step 1: Generate component placements
        logger.info("Step 1: Generating component placements...")
        placements = placer.generate_placements()
        logger.info(f"  Generated {len(placements)} component placements")

        # Step 2: Create KiCad board
        logger.info("Step 2: Creating KiCad board...")
        board_path = paths.get_board_path(sample_id)
        board_creator.create_board(
            placements=placements,
            output_path=board_path,
            board_name=f"sample_{sample_id:06d}",
            board_width=placement_config.board_width,
            board_height=placement_config.board_height,
        )

        # Validate board
        if pipeline_config.validation.get("check_file_sizes", True):
            if not validate_kicad_file(board_path):
                raise RuntimeError(f"Board validation failed: {board_path}")
        logger.info(f"  Board created: {board_path}")

        # Step 3: Export to .pcb3d
        logger.info("Step 3: Exporting to .pcb3d...")
        pcb3d_path = paths.get_pcb3d_path(sample_id)
        exporter.export(board_path, pcb3d_path)

        # Validate .pcb3d
        if pipeline_config.validation.get("check_file_sizes", True):
            if not validate_pcb3d_file(pcb3d_path):
                raise RuntimeError(f".pcb3d validation failed: {pcb3d_path}")
        logger.info(f"  .pcb3d exported: {pcb3d_path}")

        # Step 4: Import to Blender
        logger.info("Step 4: Importing to Blender...")
        blend_path = paths.get_blend_path(sample_id)
        _run_blender_import(pcb3d_path, blend_path)
        logger.info(f"  Blender import complete: {blend_path}")

        logger.info(f"✅ Sample {sample_id} intermediate generation complete: {blend_path}")
        return blend_path

    except Exception as e:
        logger.error(f"❌ Sample {sample_id} failed: {e}", exc_info=True)
        return None


def _run_blender_import(pcb3d_path: Path, blend_path: Path):
    """
    Run Blender import in subprocess.

    Args:
        pcb3d_path: Input .pcb3d file
        blend_path: Output .blend file
    """
    import_script = Path(__file__).parent / "blender_import_script.py"

    cmd = [
        "blender",
        "--background",
        "--python",
        str(import_script),
        "--",
        str(pcb3d_path),
        str(blend_path),
    ]

    logger.debug(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Log stdout for debugging
    if result.stdout:
        logger.debug(f"Blender import stdout: {result.stdout}")

    if result.returncode != 0:
        logger.error(f"Blender import failed (returncode={result.returncode})")
        logger.error(f"stderr: {result.stderr}")
        logger.error(f"stdout: {result.stdout}")
        raise RuntimeError(f"Blender import failed: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate intermediate .blend files (CPU-only pipeline stages)"
    )
    parser.add_argument(
        "--num-samples", type=int, required=True, help="Number of samples to generate"
    )
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
        help="Output directory for intermediate files",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
    )
    parser.add_argument("--start-id", type=int, default=0, help="Starting sample ID")
    args = parser.parse_args()

    # Setup logging
    log_file = args.output_dir / "logs" / "intermediate_generation.log"
    setup_logging(level=args.log_level, log_file=log_file)

    logger.info(f"Starting intermediate generation: {args.num_samples} samples")
    logger.info(f"Output directory: {args.output_dir}")

    # Load configurations
    placement_config_dict = load_config(args.config_dir, "placement")
    pipeline_config_dict = load_config(args.config_dir, "pipeline")

    placement_config = PlacementConfig.from_dict(placement_config_dict)
    pipeline_config = PipelineConfig.from_dict(pipeline_config_dict)

    # Initialize path manager
    paths = PathManager(args.output_dir, pipeline_config.paths)

    # Initialize modules (CPU-only)
    placer = PerlinPlacer(placement_config)
    board_creator = BoardCreator()
    exporter = PCB3DExporter()

    logger.info("Modules initialized (CPU-only pipeline)")

    # Generate intermediate files
    success_count = 0
    failed_samples = []

    for i in range(args.num_samples):
        sample_id = args.start_id + i

        logger.info(f"\nProcessing sample {sample_id} ({i+1}/{args.num_samples})")

        blend_path = generate_intermediate_sample(
            sample_id=sample_id,
            placer=placer,
            board_creator=board_creator,
            exporter=exporter,
            paths=paths,
            placement_config=placement_config,
            pipeline_config=pipeline_config,
            base_seed=pipeline_config.base_seed,
        )

        if blend_path:
            success_count += 1
        else:
            failed_samples.append(sample_id)

    # Summary
    logger.info("=" * 60)
    logger.info("Intermediate generation complete")
    logger.info(f"  Success: {success_count}/{args.num_samples}")
    logger.info(f"  Failed: {len(failed_samples)}")
    if failed_samples:
        logger.info(f"  Failed sample IDs: {failed_samples}")
    logger.info(f"  .blend files location: {paths.renders_dir}")
    logger.info("=" * 60)
    logger.info("Next step: Run render_from_intermediate.py on GPU partition")

    # Exit code based on success rate
    if success_count == args.num_samples:
        sys.exit(0)
    elif success_count > 0:
        sys.exit(2)  # Partial success
    else:
        sys.exit(1)  # Total failure


if __name__ == "__main__":
    main()
