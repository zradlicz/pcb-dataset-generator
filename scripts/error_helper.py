"""
Stub for error_helper module (normally provided by KiCad environment).
This allows pcb2blender_importer to work in standalone Blender/BlenderProc.
"""

def error(message: str):
    """Display an error message."""
    print(f"ERROR: {message}")

def warning(message: str):
    """Display a warning message."""
    print(f"WARNING: {message}")

def info(message: str):
    """Display an info message."""
    print(f"INFO: {message}")
