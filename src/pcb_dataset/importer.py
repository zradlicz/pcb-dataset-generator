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
        """Initialize importer and register pcb2blender addon."""
        # Add pcb2blender to path
        pcb2blender_path = Path(__file__).parent.parent.parent / "pcb2blender"
        if pcb2blender_path.exists() and str(pcb2blender_path) not in sys.path:
            sys.path.insert(0, str(pcb2blender_path))
            logger.debug(f"Added pcb2blender to path: {pcb2blender_path}")

        # Register pcb2blender_importer addon (required for Mat4CAD nodes)
        try:
            import bpy
            import pcb2blender_importer

            # Check if already registered
            if not hasattr(bpy.types, 'ShaderNodeBsdfMat4cad'):
                pcb2blender_importer.register()
                logger.info("Registered pcb2blender_importer addon")
            else:
                logger.debug("pcb2blender_importer already registered")
        except ImportError:
            logger.warning("Could not register pcb2blender addon (not running in Blender)")
        except Exception as e:
            logger.warning(f"Failed to register pcb2blender addon: {e}")

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

        # Debug: Print sys.path to verify pcb2blender is there
        pcb2blender_path = Path(__file__).parent.parent.parent / "pcb2blender"
        print(f"DEBUG: pcb2blender path: {pcb2blender_path}")
        print(f"DEBUG: pcb2blender exists: {pcb2blender_path.exists()}")
        print(f"DEBUG: error_helper exists: {(pcb2blender_path / 'error_helper.py').exists()}")
        print(f"DEBUG: pcb2blender in sys.path: {str(pcb2blender_path) in sys.path}")
        print(f"DEBUG: sys.path first 5: {sys.path[:5]}")

        try:
            # Import pcb2blender importer
            from pcb2blender_importer import importer as pcb_importer

            # Register the operator if not already registered
            if not hasattr(bpy.types, 'PCB2BLENDER_OT_import_pcb3d'):
                pcb_importer.register()
                logger.info("Registered pcb2blender operator")

            # Clear existing scene
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()

            # Import the .pcb3d file using the operator
            result = bpy.ops.pcb2blender.import_pcb3d(
                filepath=str(pcb3d_path),
                import_components=True,
                add_solder_joints="SMART",
                center_boards=True,
                cut_boards=True,
                stack_boards=True,
                merge_materials=True,
                enhance_materials=True,
                pcb_material="RASTERIZED",
                texture_dpi=1016.0
            )

            if result != {'FINISHED'}:
                raise RuntimeError(f"Import operator returned: {result}")

            logger.info(f"Imported {len(bpy.data.objects)} objects")

            # Pack all external resources (textures) into the blend file
            # This prevents missing textures when opening the file later
            bpy.ops.file.pack_all()
            logger.debug("Packed all external resources")

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
