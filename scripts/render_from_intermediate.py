#!/usr/bin/env python3
"""
Render final outputs from intermediate .blend files (GPU tasks).

This script runs steps 5-7 of the pipeline:
5. Rendering with segmentation (BlenderProc + GPU)
6. PNG extraction
7. Format conversion (optional)

Input: .blend files from generate_intermediate.py
Output: HDF5 files with RGB, depth, segmentation + optional PNG/COCO

Usage:
    python scripts/render_from_intermediate.py --num-samples 100 --input-dir data/intermediate
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pcb_dataset.renderer import BProcRenderer, RenderConfig
from pcb_dataset.converter import FormatConverter
from pcb_dataset.utils.config import load_config
from pcb_dataset.utils.logging import setup_logging, get_logger
from pcb_dataset.utils.paths import PathManager
from pcb_dataset.utils.validation import validate_hdf5_file
from pcb_dataset.pipeline import PipelineConfig
import subprocess

logger = get_logger(__name__)


def render_from_blend(
    sample_id: int,
    blend_path: Path,
    paths: PathManager,
    render_config: RenderConfig,
    pipeline_config: PipelineConfig,
    converter: FormatConverter,
):
    """
    Render final output from intermediate .blend file.

    Args:
        sample_id: Sample ID
        blend_path: Path to input .blend file
        paths: Path manager instance
        render_config: Render configuration
        pipeline_config: Pipeline configuration
        converter: Format converter instance

    Returns:
        Path to generated output file (or None if failed)
    """
    logger.info(f"=" * 60)
    logger.info(f"Rendering sample {sample_id} from {blend_path.name}")
    logger.info(f"=" * 60)

    try:
        # Check that blend file exists
        if not blend_path.exists():
            raise FileNotFoundError(f"Blend file not found: {blend_path}")

        # Step 5: Render with segmentation (GPU)
        logger.info("Step 5: Rendering with segmentation (GPU)...")
        output_path = _run_blender_render(blend_path, sample_id, paths, render_config)
        logger.info(f"  Rendered: {output_path}")

        # Validate output
        if pipeline_config.validation.get("check_file_sizes", True):
            min_size_mb = pipeline_config.validation.get("min_output_size_mb", 1.0)
            if not validate_hdf5_file(output_path, min_size_mb=min_size_mb):
                raise RuntimeError(f"Output validation failed: {output_path}")

        # Step 6: Extract PNG images for visualization
        logger.info("Step 6: Extracting PNG images...")
        png_output_dir = paths.output_dir / f"{output_path.stem}_images"
        converter.extract_images_with_viz(output_path, png_output_dir)
        logger.info(f"  PNGs extracted: {png_output_dir}")

        # Step 7: Convert format (if requested)
        if pipeline_config.output_format in ["coco", "both"]:
            logger.info("Step 7: Converting to COCO format...")
            converter.hdf5_to_coco(output_path, paths.output_dir)
            logger.info(f"  COCO format created")

        logger.info(f"✅ Sample {sample_id} rendering complete: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Sample {sample_id} rendering failed: {e}", exc_info=True)
        return None


def _run_blender_render(
    blend_path: Path, sample_id: int, paths: PathManager, render_config: RenderConfig
) -> Path:
    """
    Run BlenderProc rendering in subprocess.

    Args:
        blend_path: Input .blend file
        sample_id: Sample ID
        paths: Path manager instance
        render_config: Render configuration

    Returns:
        Path to generated HDF5 file
    """
    render_script = Path(__file__).parent / "blenderproc_render_script.py"
    config_dir = Path(__file__).parent.parent / "config"

    cmd = [
        "blenderproc",
        "run",
        str(render_script),
        str(blend_path),
        str(paths.output_dir),
        "--config-dir",
        str(config_dir),
    ]

    logger.debug(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"BlenderProc render failed: {result.stderr}")
        raise RuntimeError(f"BlenderProc render failed: {result.stderr}")

    # Find the generated output file
    output_path = paths.get_output_path(sample_id, resolution=render_config.resolution)

    # BlenderProc creates numbered files, find the latest HDF5 in output dir
    hdf5_files = sorted(paths.output_dir.glob("*.hdf5"), key=lambda p: p.stat().st_mtime)
    if hdf5_files:
        latest_hdf5 = hdf5_files[-1]
        # Rename to expected output path
        latest_hdf5.rename(output_path)
        logger.debug(f"Renamed {latest_hdf5.name} -> {output_path.name}")
    else:
        raise RuntimeError("No HDF5 output file generated")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Render final outputs from intermediate .blend files (GPU pipeline stages)"
    )
    parser.add_argument(
        "--num-samples", type=int, required=True, help="Number of samples to render"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).parent.parent / "config",
        help="Configuration directory",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Input directory containing .blend files (from generate_intermediate.py)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "output",
        help="Output directory for final HDF5 files",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"
    )
    parser.add_argument("--start-id", type=int, default=0, help="Starting sample ID")
    args = parser.parse_args()

    # Setup logging
    log_file = args.output_dir.parent / "logs" / "render_from_intermediate.log"
    setup_logging(level=args.log_level, log_file=log_file)

    logger.info(f"Starting GPU rendering: {args.num_samples} samples")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output directory: {args.output_dir}")

    # Load configurations
    render_config_dict = load_config(args.config_dir, "render")
    pipeline_config_dict = load_config(args.config_dir, "pipeline")

    render_config = RenderConfig.from_dict(render_config_dict)
    pipeline_config = PipelineConfig.from_dict(pipeline_config_dict)

    # Initialize path manager
    # Note: We override the renders_dir to point to input_dir
    path_config = pipeline_config.paths.copy()
    paths = PathManager(args.output_dir.parent, path_config)
    paths.renders_dir = args.input_dir  # Override to read from input

    # Initialize modules (GPU-only)
    converter = FormatConverter()

    logger.info("Modules initialized (GPU rendering pipeline)")

    # Render samples
    success_count = 0
    failed_samples = []

    for i in range(args.num_samples):
        sample_id = args.start_id + i

        logger.info(f"\nRendering sample {sample_id} ({i+1}/{args.num_samples})")

        # Find the corresponding .blend file
        blend_path = paths.get_blend_path(sample_id)

        if not blend_path.exists():
            logger.warning(f"Blend file not found for sample {sample_id}: {blend_path}")
            failed_samples.append(sample_id)
            continue

        output_path = render_from_blend(
            sample_id=sample_id,
            blend_path=blend_path,
            paths=paths,
            render_config=render_config,
            pipeline_config=pipeline_config,
            converter=converter,
        )

        if output_path:
            success_count += 1
        else:
            failed_samples.append(sample_id)

    # Summary
    logger.info("=" * 60)
    logger.info("GPU rendering complete")
    logger.info(f"  Success: {success_count}/{args.num_samples}")
    logger.info(f"  Failed: {len(failed_samples)}")
    if failed_samples:
        logger.info(f"  Failed sample IDs: {failed_samples}")
    logger.info(f"  Output files location: {args.output_dir}")
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
