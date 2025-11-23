"""
File validation utilities.
"""

from pathlib import Path
import h5py
import logging

logger = logging.getLogger(__name__)


def validate_kicad_file(file_path: Path) -> bool:
    """
    Validate a KiCad PCB file.

    Args:
        file_path: Path to .kicad_pcb file

    Returns:
        True if valid, False otherwise
    """
    if not file_path.exists():
        logger.error(f"KiCad file does not exist: {file_path}")
        return False

    if file_path.stat().st_size == 0:
        logger.error(f"KiCad file is empty: {file_path}")
        return False

    # Basic content check - KiCad files should start with (kicad_pcb
    try:
        with open(file_path, "r") as f:
            first_line = f.readline().strip()
            if not first_line.startswith("(kicad_pcb"):
                logger.error(f"KiCad file has invalid format: {file_path}")
                return False
    except Exception as e:
        logger.error(f"Error reading KiCad file {file_path}: {e}")
        return False

    logger.debug(f"KiCad file validated: {file_path}")
    return True


def validate_pcb3d_file(file_path: Path, min_size_mb: float = 0.1) -> bool:
    """
    Validate a .pcb3d file.

    Args:
        file_path: Path to .pcb3d file
        min_size_mb: Minimum expected file size in MB

    Returns:
        True if valid, False otherwise
    """
    if not file_path.exists():
        logger.error(f".pcb3d file does not exist: {file_path}")
        return False

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb < min_size_mb:
        logger.error(
            f".pcb3d file is too small ({file_size_mb:.2f} MB < {min_size_mb:.2f} MB): {file_path}"
        )
        return False

    # .pcb3d files are ZIP archives - basic check
    try:
        import zipfile

        if not zipfile.is_zipfile(file_path):
            logger.error(f".pcb3d file is not a valid ZIP archive: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error validating .pcb3d file {file_path}: {e}")
        return False

    logger.debug(f".pcb3d file validated: {file_path} ({file_size_mb:.2f} MB)")
    return True


def validate_hdf5_file(file_path: Path, min_size_mb: float = 1.0, check_keys: bool = True) -> bool:
    """
    Validate an HDF5 output file.

    Args:
        file_path: Path to .hdf5 file
        min_size_mb: Minimum expected file size in MB
        check_keys: Whether to check for expected data keys

    Returns:
        True if valid, False otherwise
    """
    if not file_path.exists():
        logger.error(f"HDF5 file does not exist: {file_path}")
        return False

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb < min_size_mb:
        logger.error(
            f"HDF5 file is too small ({file_size_mb:.2f} MB < {min_size_mb:.2f} MB): {file_path}"
        )
        return False

    # Check HDF5 structure
    try:
        with h5py.File(file_path, "r") as f:
            # BlenderProc HDF5 files have a specific structure
            # Expected keys: colors, depth, category_id_segmaps, etc.
            if check_keys:
                expected_keys = ["colors", "depth"]
                missing_keys = [key for key in expected_keys if key not in f.keys()]

                if missing_keys:
                    logger.warning(
                        f"HDF5 file missing expected keys {missing_keys}: {file_path}"
                    )
                    # Don't fail on missing keys, just warn
                    # Some renders may not have all data types

    except Exception as e:
        logger.error(f"Error reading HDF5 file {file_path}: {e}")
        return False

    logger.debug(f"HDF5 file validated: {file_path} ({file_size_mb:.2f} MB)")
    return True


def validate_blend_file(file_path: Path, min_size_mb: float = 0.5) -> bool:
    """
    Validate a Blender .blend file.

    Args:
        file_path: Path to .blend file
        min_size_mb: Minimum expected file size in MB

    Returns:
        True if valid, False otherwise
    """
    if not file_path.exists():
        logger.error(f"Blender file does not exist: {file_path}")
        return False

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb < min_size_mb:
        logger.error(
            f"Blender file is too small ({file_size_mb:.2f} MB < {min_size_mb:.2f} MB): {file_path}"
        )
        return False

    # Blender files start with "BLENDER" magic bytes
    try:
        with open(file_path, "rb") as f:
            magic = f.read(7)
            if magic != b"BLENDER":
                logger.error(f"Blender file has invalid magic bytes: {file_path}")
                return False
    except Exception as e:
        logger.error(f"Error reading Blender file {file_path}: {e}")
        return False

    logger.debug(f"Blender file validated: {file_path} ({file_size_mb:.2f} MB)")
    return True
