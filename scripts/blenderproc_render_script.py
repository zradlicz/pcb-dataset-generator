#!/usr/bin/env python3
# IMPORTANT: blenderproc must be imported first!
import blenderproc as bproc

"""
Standalone BlenderProc rendering script.

This script is run via blenderproc:
    blenderproc run blenderproc_render_script.py <blend_path> <output_dir> <config_dir>
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import modules directly to avoid triggering __init__.py imports
# (which would require 'noise' package in Blender's Python)
import pcb_dataset.renderer as renderer
import pcb_dataset.utils.config as config_utils
import pcb_dataset.utils.logging as logging_utils

BProcRenderer = renderer.BProcRenderer
RenderConfig = renderer.RenderConfig
load_config = config_utils.load_config
setup_logging = logging_utils.setup_logging


def main():
    parser = argparse.ArgumentParser(description="BlenderProc PCB rendering with segmentation")
    parser.add_argument("blend_path", type=Path, help="Path to .blend file")
    parser.add_argument("output_dir", type=Path, help="Output directory for HDF5 files")
    parser.add_argument("--config-dir", type=Path, default=Path(__file__).parent.parent / "config", help="Config directory")
    parser.add_argument("--log-level", type=str, default="INFO", help="Log level")
    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Load render configuration
    render_config_dict = load_config(args.config_dir, "render")
    render_config = RenderConfig.from_dict(render_config_dict)

    # Render
    renderer = BProcRenderer(render_config)
    try:
        output_path = renderer.render(args.blend_path, args.output_dir)
        print(f"Success: {output_path}")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
