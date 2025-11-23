"""
Export KiCad PCB to .pcb3d format.

Ported from POC: src/kicad_board_exporter.py

CRITICAL LEARNINGS:
- Use kicad-cli (headless compatible), not pcbnew.ExportVRML()
- Units MUST be meters: --units m
- Set origin explicitly: --user-origin 0x0mm
- Use real pcb2blender code (git submodule)
"""

from pathlib import Path
import subprocess
import sys
import logging
from unittest.mock import patch

try:
    import pcbnew
except ImportError:
    pcbnew = None

logger = logging.getLogger(__name__)


class PCB3DExporter:
    """
    Export .kicad_pcb to .pcb3d format.

    Ported from POC src/kicad_board_exporter.py
    """

    def __init__(self):
        """Initialize exporter."""
        # Add pcb2blender to path
        pcb2blender_path = Path(__file__).parent.parent.parent / "pcb2blender"
        if pcb2blender_path.exists() and str(pcb2blender_path) not in sys.path:
            sys.path.insert(0, str(pcb2blender_path))

    def export(self, kicad_pcb_path: Path, output_pcb3d_path: Path) -> Path:
        """
        Export .kicad_pcb to .pcb3d.

        Args:
            kicad_pcb_path: Path to input .kicad_pcb file
            output_pcb3d_path: Path to output .pcb3d file

        Returns:
            Path to generated .pcb3d file
        """
        if pcbnew is None:
            raise RuntimeError("pcbnew not available - KiCad must be installed")

        kicad_pcb_path = Path(kicad_pcb_path)
        output_pcb3d_path = Path(output_pcb3d_path)

        if not kicad_pcb_path.exists():
            raise FileNotFoundError(f"Board file not found: {kicad_pcb_path}")

        logger.info(f"Exporting {kicad_pcb_path.name} to .pcb3d...")

        # Ensure output directory exists
        output_pcb3d_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Import pcb2blender export function
            from pcb2blender_exporter.export import export_pcb3d as pcb2blender_export_pcb3d, get_boarddefs

            # Load the board
            board = pcbnew.LoadBoard(str(kicad_pcb_path))
            if board is None:
                raise RuntimeError(f"Failed to load board: {kicad_pcb_path}")

            # Create VRML export function using kicad-cli
            def export_vrml_via_cli(filename, scale, use_relative_paths, use_plain_pcb,
                                    use_inches, force_inches, models_dir, ref_x, ref_y):
                """
                Export VRML using kicad-cli (headless compatible).

                CRITICAL: Blender interprets VRML units as meters, so export in meters.
                """
                units = "m"  # CRITICAL: meters, not mm
                cmd = [
                    "kicad-cli", "pcb", "export", "vrml",
                    "--output", str(filename),
                    "--units", units,
                ]

                # Set user origin to match pcbnew.ExportVRML behavior
                cmd.extend(["--user-origin", f"{ref_x}x{ref_y}mm"])

                if models_dir:
                    cmd.extend(["--models-dir", str(models_dir)])
                    if use_relative_paths:
                        cmd.append("--models-relative")

                cmd.append(str(kicad_pcb_path))

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    logger.debug(f"VRML export successful: {filename}")
                    return True
                except subprocess.CalledProcessError as e:
                    logger.error(f"VRML export failed: {e.stderr}")
                    return False

            # Patch pcbnew functions to use our implementations
            with patch('pcbnew.GetBoard', return_value=board), \
                 patch('pcbnew.ExportVRML', side_effect=export_vrml_via_cli):

                # Get board definitions
                boarddefs, ignored = get_boarddefs(board)
                if ignored:
                    logger.warning(f"Ignored {len(ignored)} PCB3D markers")

                # Use real pcb2blender export function
                pcb2blender_export_pcb3d(output_pcb3d_path, boarddefs)

            logger.info(f".pcb3d export complete: {output_pcb3d_path}")

            return output_pcb3d_path

        except ImportError as e:
            logger.error(f"Failed to import pcb2blender: {e}")
            logger.error("Make sure pcb2blender submodule is initialized: git submodule update --init --recursive")
            raise RuntimeError(f"pcb2blender import failed: {e}")

        except Exception as e:
            logger.error(f"Error exporting PCB to .pcb3d: {e}", exc_info=True)
            raise RuntimeError(f"Export failed: {e}")
