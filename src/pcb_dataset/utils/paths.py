"""
Path management utilities.
"""

from pathlib import Path
from typing import Dict, Optional


class PathManager:
    """Manage file paths for the pipeline."""

    def __init__(self, base_dir: Path, paths_config: Dict[str, str]):
        """
        Initialize path manager.

        Args:
            base_dir: Base directory for all data (typically data/)
            paths_config: Dictionary of path configurations from pipeline.yaml
        """
        self.base_dir = Path(base_dir)
        self.paths_config = paths_config

        # Create absolute paths
        self.boards_dir = self.base_dir / paths_config.get("boards", "boards")
        self.pcb3d_dir = self.base_dir / paths_config.get("pcb3d", "pcb3d")
        self.renders_dir = self.base_dir / paths_config.get("renders", "renders")
        self.output_dir = self.base_dir / paths_config.get("output", "output")
        self.logs_dir = self.base_dir / paths_config.get("logs", "logs")

        # Ensure all directories exist
        self._create_directories()

    def _create_directories(self):
        """Create all required directories."""
        for dir_path in [
            self.boards_dir,
            self.pcb3d_dir,
            self.renders_dir,
            self.output_dir,
            self.logs_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_board_path(self, sample_id: int, board_name: Optional[str] = None) -> Path:
        """Get path for KiCad board file."""
        if board_name is None:
            board_name = f"sample_{sample_id:06d}"
        return self.boards_dir / f"{board_name}.kicad_pcb"

    def get_pcb3d_path(self, sample_id: int, board_name: Optional[str] = None) -> Path:
        """Get path for .pcb3d file."""
        if board_name is None:
            board_name = f"sample_{sample_id:06d}"
        return self.pcb3d_dir / f"{board_name}.pcb3d"

    def get_blend_path(self, sample_id: int, board_name: Optional[str] = None) -> Path:
        """Get path for Blender file."""
        if board_name is None:
            board_name = f"sample_{sample_id:06d}"
        return self.renders_dir / f"{board_name}.blend"

    def get_output_path(
        self, sample_id: int, resolution: int = 2048, format: str = "hdf5"
    ) -> Path:
        """Get path for output file."""
        filename = f"sample_{sample_id:06d}_{resolution}x{resolution}.{format}"
        return self.output_dir / filename

    def get_log_path(self, sample_id: int) -> Path:
        """Get path for sample log file."""
        return self.logs_dir / f"sample_{sample_id:06d}.log"

    def cleanup_sample(self, sample_id: int, keep_boards: bool, keep_pcb3d: bool, keep_blend: bool):
        """
        Clean up intermediate files for a sample.

        Args:
            sample_id: Sample ID
            keep_boards: Keep .kicad_pcb file
            keep_pcb3d: Keep .pcb3d file
            keep_blend: Keep .blend file
        """
        if not keep_boards:
            board_path = self.get_board_path(sample_id)
            if board_path.exists():
                board_path.unlink()

        if not keep_pcb3d:
            pcb3d_path = self.get_pcb3d_path(sample_id)
            if pcb3d_path.exists():
                pcb3d_path.unlink()

        if not keep_blend:
            blend_path = self.get_blend_path(sample_id)
            if blend_path.exists():
                blend_path.unlink()
            # Also remove backup files
            blend1_path = blend_path.with_suffix(".blend1")
            if blend1_path.exists():
                blend1_path.unlink()
