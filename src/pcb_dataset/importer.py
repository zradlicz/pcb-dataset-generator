"""
Import .pcb3d files into Blender.

NOTE: This module must be run inside Blender's Python interpreter.
"""

from pathlib import Path
import sys
import logging

logger = logging.getLogger(__name__)


class BlenderImporter:
    """
    Import .pcb3d into Blender.

    Uses pcb2blender importer from pcb2blender/pcb2blender_importer/
    """

    def __init__(self):
        """Initialize importer."""
        # Add pcb2blender to path
        pcb2blender_path = Path(__file__).parent.parent.parent / "pcb2blender"
        if pcb2blender_path.exists() and str(pcb2blender_path) not in sys.path:
            sys.path.insert(0, str(pcb2blender_path))

    def import_pcb3d(self, pcb3d_path: Path, output_blend_path: Path) -> Path:
        """
        Import .pcb3d into Blender and save .blend file.

        Args:
            pcb3d_path: Path to .pcb3d file
            output_blend_path: Path to save .blend file

        Returns:
            Path to saved .blend file
        """
        try:
            import bpy
        except ImportError:
            raise RuntimeError("bpy not available - must run inside Blender")

        pcb3d_path = Path(pcb3d_path)
        output_blend_path = Path(output_blend_path)

        if not pcb3d_path.exists():
            raise FileNotFoundError(f".pcb3d file not found: {pcb3d_path}")

        logger.info(f"Importing {pcb3d_path.name} into Blender...")

        try:
            # Import pcb2blender importer
            from pcb2blender_importer import import_pcb

            # Clear existing scene
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()

            # Import the .pcb3d file
            import_pcb.import_pcb3d(str(pcb3d_path))

            logger.info(f"Imported {len(bpy.data.objects)} objects")

            # Save .blend file
            output_blend_path.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(output_blend_path))

            logger.info(f"Blend file saved: {output_blend_path}")

            return output_blend_path

        except ImportError as e:
            logger.error(f"Failed to import pcb2blender: {e}")
            logger.error("Make sure pcb2blender submodule is initialized")
            raise RuntimeError(f"pcb2blender import failed: {e}")

        except Exception as e:
            logger.error(f"Error importing .pcb3d: {e}", exc_info=True)
            raise RuntimeError(f"Import failed: {e}")
