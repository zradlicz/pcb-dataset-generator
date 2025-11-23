"""
Convert HDF5 output to standard ML formats (COCO, PNG).
"""

from pathlib import Path
import h5py
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class FormatConverter:
    """
    Convert BlenderProc HDF5 output to standard formats.

    Future implementation for Step 5 completion.
    """

    def __init__(self):
        """Initialize converter."""
        pass

    def hdf5_to_coco(self, hdf5_path: Path, output_dir: Path):
        """
        Convert HDF5 to COCO format with PNG images.

        Args:
            hdf5_path: Path to input .hdf5 file
            output_dir: Directory for output files

        TODO: Implement COCO JSON export
        - Extract RGB, segmentation maps
        - Generate bounding boxes from instance segmentation
        - Create COCO JSON annotations
        """
        logger.info(f"Converting {hdf5_path.name} to COCO format...")

        with h5py.File(hdf5_path, "r") as f:
            # Extract RGB
            rgb = np.array(f["colors"])

            # Extract segmentation
            category_id_seg = np.array(f.get("category_id_segmaps", []))

            # TODO: Generate COCO annotations

        logger.warning("COCO export not yet implemented")

    def extract_images(self, hdf5_path: Path, output_dir: Path):
        """
        Extract RGB, depth, segmentation as separate PNG files.

        Args:
            hdf5_path: Path to input .hdf5 file
            output_dir: Directory for output images
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stem = hdf5_path.stem

        with h5py.File(hdf5_path, "r") as f:
            # Extract and save RGB
            if "colors" in f:
                rgb = np.array(f["colors"])[0]  # First frame
                rgb_img = Image.fromarray(rgb.astype(np.uint8))
                rgb_path = output_dir / f"{stem}_rgb.png"
                rgb_img.save(rgb_path)
                logger.info(f"Saved RGB: {rgb_path}")

            # Extract and save depth
            if "depth" in f:
                depth = np.array(f["depth"])[0]
                # Normalize depth for visualization
                depth_normalized = ((depth - depth.min()) / (depth.max() - depth.min()) * 255).astype(np.uint8)
                depth_img = Image.fromarray(depth_normalized)
                depth_path = output_dir / f"{stem}_depth.png"
                depth_img.save(depth_path)
                logger.info(f"Saved depth: {depth_path}")

            # Extract and save segmentation
            if "category_id_segmaps" in f:
                seg = np.array(f["category_id_segmaps"])[0]
                # Save as indexed PNG (category IDs as pixel values)
                seg_img = Image.fromarray(seg.astype(np.uint8))
                seg_path = output_dir / f"{stem}_seg.png"
                seg_img.save(seg_path)
                logger.info(f"Saved segmentation: {seg_path}")
