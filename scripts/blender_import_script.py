#!/usr/bin/env python3
"""
Standalone Blender import script.

This script must be run inside Blender:
    blender --background --python blender_import_script.py -- <pcb3d_path> <blend_path>
"""

import sys
from pathlib import Path

print("=== Blender Import Script Starting ===")
print(f"Python version: {sys.version}")
print(f"Script path: {__file__}")

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
print(f"Added to path: {src_path}")

# Import modules directly to avoid triggering __init__.py
try:
    print("Importing pcb_dataset.importer...")
    import pcb_dataset.importer as importer_module

    BlenderImporter = importer_module.BlenderImporter
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


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

    # Import
    print(f"Starting import of {pcb3d_path} to {blend_path}")
    print(f"PCB3D exists: {pcb3d_path.exists()}")
    print(f"Output directory: {blend_path.parent}")
    print(f"Output directory exists: {blend_path.parent.exists()}")

    importer = BlenderImporter()
    try:
        result_path = importer.import_pcb3d(pcb3d_path, blend_path)
        print(f"Import returned: {result_path}")
        print(f"Blend file exists: {result_path.exists()}")
        if result_path.exists():
            print(f"Blend file size: {result_path.stat().st_size} bytes")
        print(f"Success: {result_path}")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
