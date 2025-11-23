#!/usr/bin/env python3
"""
Standalone Blender import script.

This script must be run inside Blender:
    blender --background --python blender_import_script.py -- <pcb3d_path> <blend_path>
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pcb_dataset.importer import BlenderImporter
from pcb_dataset.utils.logging import setup_logging


def main():
    # Parse arguments (after the -- separator)
    try:
        separator_index = sys.argv.index("--")
        script_args = sys.argv[separator_index + 1:]
    except ValueError:
        print("Error: Arguments must be passed after '--'")
        print("Usage: blender --background --python blender_import_script.py -- <pcb3d_path> <blend_path>")
        sys.exit(1)

    if len(script_args) < 2:
        print("Error: Missing arguments")
        print("Usage: blender --background --python blender_import_script.py -- <pcb3d_path> <blend_path>")
        sys.exit(1)

    pcb3d_path = Path(script_args[0])
    blend_path = Path(script_args[1])

    # Setup logging
    setup_logging(level="INFO")

    # Import
    importer = BlenderImporter()
    try:
        result_path = importer.import_pcb3d(pcb3d_path, blend_path)
        print(f"Success: {result_path}")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
