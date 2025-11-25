"""
Convert HDF5 output to standard ML formats (COCO, PNG).
"""

from pathlib import Path
import h5py
import numpy as np
from PIL import Image
import logging
import matplotlib.pyplot as plt

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

        logger.info(f"Extracting images from {hdf5_path.name}...")

        with h5py.File(hdf5_path, "r") as f:
            logger.debug(f"HDF5 keys: {list(f.keys())}")

            # Extract and save RGB
            if "colors" in f:
                rgb = np.array(f["colors"])
                logger.debug(f"RGB shape: {rgb.shape}, dtype: {rgb.dtype}, range: [{rgb.min()}, {rgb.max()}]")

                # Handle both 2D (H,W,C) and 3D (N,H,W,C) formats
                if rgb.ndim == 4:
                    rgb = rgb[0]  # First frame

                # Convert float [0,1] to uint8 [0,255] if needed
                if rgb.dtype in [np.float32, np.float64]:
                    rgb = (rgb * 255).astype(np.uint8)
                else:
                    rgb = rgb.astype(np.uint8)

                rgb_img = Image.fromarray(rgb)
                rgb_path = output_dir / f"{stem}_rgb.png"
                rgb_img.save(rgb_path)
                logger.info(f"✓ Saved RGB: {rgb_path}")

            # Extract and save depth
            if "depth" in f:
                depth = np.array(f["depth"])
                logger.debug(f"Depth shape: {depth.shape}, dtype: {depth.dtype}")

                # Handle both 2D and 3D formats
                if depth.ndim == 3:
                    depth = depth[0]

                # Normalize depth for visualization
                depth_normalized = ((depth - depth.min()) / (depth.max() - depth.min()) * 255).astype(np.uint8)
                depth_img = Image.fromarray(depth_normalized)
                depth_path = output_dir / f"{stem}_depth.png"
                depth_img.save(depth_path)
                logger.info(f"✓ Saved depth: {depth_path}")

            # Extract and save category segmentation (raw)
            if "category_id_segmaps" in f:
                seg = np.array(f["category_id_segmaps"])
                logger.debug(f"Category segmentation shape: {seg.shape}, dtype: {seg.dtype}")
                logger.debug(f"Unique category IDs: {np.unique(seg)}")

                # Handle both 2D and 3D formats
                if seg.ndim == 3:
                    seg = seg[0]

                # Save as indexed PNG (category IDs as pixel values)
                seg_img = Image.fromarray(seg.astype(np.uint8))
                seg_path = output_dir / f"{stem}_category_seg.png"
                seg_img.save(seg_path)
                logger.info(f"✓ Saved category segmentation: {seg_path}")

            # Extract and save instance segmentation (raw)
            if "instance_segmaps" in f:
                instance_seg = np.array(f["instance_segmaps"])
                logger.debug(f"Instance segmentation shape: {instance_seg.shape}, dtype: {instance_seg.dtype}")

                # Handle both 2D and 3D formats
                if instance_seg.ndim == 3:
                    instance_seg = instance_seg[0]

                # Save as indexed PNG
                instance_img = Image.fromarray(instance_seg.astype(np.uint8) if instance_seg.max() < 256 else (instance_seg % 256).astype(np.uint8))
                instance_path = output_dir / f"{stem}_instance_seg.png"
                instance_img.save(instance_path)
                logger.info(f"✓ Saved instance segmentation: {instance_path}")

        logger.info(f"All images extracted to {output_dir}")

    def extract_images_with_viz(self, hdf5_path: Path, output_dir: Path):
        """
        Extract images with colorized segmentation visualizations.

        Args:
            hdf5_path: Path to input .hdf5 file
            output_dir: Directory for output images
        """
        # First extract raw images
        self.extract_images(hdf5_path, output_dir)

        output_dir = Path(output_dir)
        stem = hdf5_path.stem

        logger.info(f"Creating colorized visualizations...")

        with h5py.File(hdf5_path, "r") as f:
            # Create colorized category segmentation
            if "category_id_segmaps" in f:
                seg = np.array(f["category_id_segmaps"])
                if seg.ndim == 3:
                    seg = seg[0]

                unique_ids = np.unique(seg)
                logger.debug(f"Colorizing {len(unique_ids)} unique categories")

                # Create color map
                colors_map = plt.cm.tab20(np.linspace(0, 1, len(unique_ids)))
                seg_colored = np.zeros((*seg.shape, 3), dtype=np.uint8)

                for idx, cat_id in enumerate(unique_ids):
                    mask = seg == cat_id
                    seg_colored[mask] = (colors_map[idx, :3] * 255).astype(np.uint8)

                seg_viz_img = Image.fromarray(seg_colored)
                seg_viz_path = output_dir / f"{stem}_category_seg_viz.png"
                seg_viz_img.save(seg_viz_path)
                logger.info(f"✓ Saved colorized category segmentation: {seg_viz_path}")

            # Create colorized instance segmentation
            if "instance_segmaps" in f:
                instance_seg = np.array(f["instance_segmaps"])
                if instance_seg.ndim == 3:
                    instance_seg = instance_seg[0]

                unique_ids = np.unique(instance_seg)
                logger.debug(f"Colorizing {len(unique_ids)} unique instances")

                # Create color map
                colors_map = plt.cm.tab20(np.linspace(0, 1, min(len(unique_ids), 20)))
                instance_colored = np.zeros((*instance_seg.shape, 3), dtype=np.uint8)

                for idx, inst_id in enumerate(unique_ids):
                    mask = instance_seg == inst_id
                    color_idx = idx % 20  # Cycle through colors if more than 20 instances
                    instance_colored[mask] = (colors_map[color_idx, :3] * 255).astype(np.uint8)

                instance_viz_img = Image.fromarray(instance_colored)
                instance_viz_path = output_dir / f"{stem}_instance_seg_viz.png"
                instance_viz_img.save(instance_viz_path)
                logger.info(f"✓ Saved colorized instance segmentation: {instance_viz_path}")

        logger.info(f"Colorized visualizations complete")
