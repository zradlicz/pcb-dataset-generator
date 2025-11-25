"""
Pipeline orchestration - coordinates all modules.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import subprocess
import logging

from pcb_dataset.placement import PerlinPlacer, PlacementConfig
from pcb_dataset.board import BoardCreator
from pcb_dataset.exporter import PCB3DExporter
from pcb_dataset.importer import BlenderImporter
from pcb_dataset.renderer import BProcRenderer, RenderConfig
from pcb_dataset.converter import FormatConverter
from pcb_dataset.utils.paths import PathManager
from pcb_dataset.utils.validation import (
    validate_kicad_file,
    validate_pcb3d_file,
    validate_hdf5_file,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """High-level pipeline configuration."""

    num_samples: int
    output_format: str
    resolutions: list
    base_seed: int
    auto_increment: bool
    paths: dict
    cleanup: dict
    validation: dict

    @classmethod
    def from_dict(cls, config: dict) -> "PipelineConfig":
        """Create config from dictionary."""
        return cls(
            num_samples=config["dataset"]["num_samples"],
            output_format=config["dataset"]["output_format"],
            resolutions=config["resolutions"],
            base_seed=config["seed"]["base"],
            auto_increment=config["seed"]["auto_increment"],
            paths=config["paths"],
            cleanup=config["cleanup"],
            validation=config["validation"],
        )


class Pipeline:
    """
    Orchestrate the full PCB dataset generation pipeline.
    """

    def __init__(
        self,
        placement_config: PlacementConfig,
        render_config: RenderConfig,
        pipeline_config: PipelineConfig,
        base_dir: Path,
    ):
        """
        Initialize pipeline.

        Args:
            placement_config: Component placement configuration
            render_config: Rendering configuration
            pipeline_config: Pipeline configuration
            base_dir: Base directory for all data
        """
        self.placement_config = placement_config
        self.render_config = render_config
        self.pipeline_config = pipeline_config

        # Initialize path manager
        self.paths = PathManager(base_dir, pipeline_config.paths)

        # Initialize modules
        self.placer = PerlinPlacer(placement_config)
        self.board_creator = BoardCreator()
        self.exporter = PCB3DExporter()
        self.importer = BlenderImporter()
        self.renderer = BProcRenderer(render_config)
        self.converter = FormatConverter()

        logger.info("Pipeline initialized")

    def generate_sample(self, sample_id: int) -> Optional[Path]:
        """
        Generate a single sample through the full pipeline.

        Args:
            sample_id: Sample ID

        Returns:
            Path to generated output file (or None if failed)
        """
        logger.info(f"=" * 60)
        logger.info(f"Generating sample {sample_id}")
        logger.info(f"=" * 60)

        try:
            # Set seed for reproducibility
            seed = self._get_seed(sample_id)
            self.placer.config.seed = seed

            # Step 1: Generate component placements
            logger.info("Step 1: Generating component placements...")
            placements = self.placer.generate_placements()

            # Step 2: Create KiCad board
            logger.info("Step 2: Creating KiCad board...")
            board_path = self.paths.get_board_path(sample_id)
            self.board_creator.create_board(
                placements=placements,
                output_path=board_path,
                board_name=f"sample_{sample_id:06d}",
                board_width=self.placement_config.board_width,
                board_height=self.placement_config.board_height,
            )

            # Validate board
            if self.pipeline_config.validation.get("check_file_sizes", True):
                if not validate_kicad_file(board_path):
                    raise RuntimeError(f"Board validation failed: {board_path}")

            # Step 3: Export to .pcb3d
            logger.info("Step 3: Exporting to .pcb3d...")
            pcb3d_path = self.paths.get_pcb3d_path(sample_id)
            self.exporter.export(board_path, pcb3d_path)

            # Validate .pcb3d
            if self.pipeline_config.validation.get("check_file_sizes", True):
                if not validate_pcb3d_file(pcb3d_path):
                    raise RuntimeError(f".pcb3d validation failed: {pcb3d_path}")

            # Step 4: Import to Blender (run in subprocess)
            logger.info("Step 4: Importing to Blender...")
            blend_path = self.paths.get_blend_path(sample_id)
            self._run_blender_import(pcb3d_path, blend_path)

            # Step 5: Render with segmentation (run in subprocess)
            logger.info("Step 5: Rendering with segmentation...")
            output_path = self._run_blender_render(blend_path, sample_id)

            # Validate output
            if self.pipeline_config.validation.get("check_file_sizes", True):
                min_size_mb = self.pipeline_config.validation.get("min_output_size_mb", 1.0)
                if not validate_hdf5_file(output_path, min_size_mb=min_size_mb):
                    raise RuntimeError(f"Output validation failed: {output_path}")

            # Step 6: Extract PNG images for visualization
            logger.info("Step 6: Extracting PNG images...")
            png_output_dir = self.paths.output_dir / f"{output_path.stem}_images"
            self.converter.extract_images_with_viz(output_path, png_output_dir)

            # Step 7: Convert format (if requested)
            if self.pipeline_config.output_format in ["coco", "both"]:
                logger.info("Step 7: Converting to COCO format...")
                self.converter.hdf5_to_coco(output_path, self.paths.output_dir)

            # Step 8: Cleanup intermediate files
            if not self.pipeline_config.cleanup.get("keep_on_failure", True):
                self._cleanup(sample_id)

            logger.info(f"Sample {sample_id} complete: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Sample {sample_id} failed: {e}", exc_info=True)

            # Keep files on failure if configured
            if not self.pipeline_config.cleanup.get("keep_on_failure", True):
                self._cleanup(sample_id)

            return None

    def _run_blender_import(self, pcb3d_path: Path, blend_path: Path):
        """
        Run Blender import in subprocess.

        Args:
            pcb3d_path: Input .pcb3d file
            blend_path: Output .blend file
        """
        import_script = Path(__file__).parent.parent.parent / "scripts" / "blender_import_script.py"

        cmd = [
            "blender",
            "--background",
            "--python", str(import_script),
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

        logger.info(f"Blender import complete: {blend_path}")

    def _run_blender_render(self, blend_path: Path, sample_id: int) -> Path:
        """
        Run BlenderProc rendering in subprocess.

        Args:
            blend_path: Input .blend file
            sample_id: Sample ID

        Returns:
            Path to generated HDF5 file
        """
        render_script = Path(__file__).parent.parent.parent / "scripts" / "blenderproc_render_script.py"
        config_dir = Path(__file__).parent.parent.parent / "config"

        cmd = [
            "blenderproc", "run",
            str(render_script),
            str(blend_path),
            str(self.paths.output_dir),
            "--config-dir", str(config_dir),
        ]

        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"BlenderProc render failed: {result.stderr}")
            raise RuntimeError(f"BlenderProc render failed: {result.stderr}")

        # Find the generated output file
        output_path = self.paths.get_output_path(sample_id, resolution=self.render_config.resolution)

        # BlenderProc creates numbered files, find the latest HDF5 in output dir
        hdf5_files = sorted(self.paths.output_dir.glob("*.hdf5"), key=lambda p: p.stat().st_mtime)
        if hdf5_files:
            latest_hdf5 = hdf5_files[-1]
            # Rename to expected output path
            latest_hdf5.rename(output_path)
            logger.info(f"BlenderProc render complete: {output_path}")
        else:
            raise RuntimeError("No HDF5 output file generated")

        return output_path

    def _cleanup(self, sample_id: int):
        """Cleanup intermediate files based on configuration."""
        self.paths.cleanup_sample(
            sample_id,
            keep_boards=self.pipeline_config.cleanup.get("keep_boards", False),
            keep_pcb3d=self.pipeline_config.cleanup.get("keep_pcb3d", False),
            keep_blend=self.pipeline_config.cleanup.get("keep_blend", False),
        )
        logger.debug(f"Cleaned up sample {sample_id}")

    def _get_seed(self, sample_id: int) -> int:
        """Get seed for this sample."""
        if self.pipeline_config.auto_increment:
            return self.pipeline_config.base_seed + sample_id
        return self.pipeline_config.base_seed
