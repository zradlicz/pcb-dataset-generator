"""
BlenderProc rendering with material-based segmentation.

Ported from POC: src/bproc_renderer.py

CRITICAL LEARNINGS:
- Material-based segmentation via Mat4cad BSDF inspection
- Multi-material object splitting for per-face segmentation
- Category 1 = metal (solder, pins, pads, copper)
- Category 2 = non-metal (plastic/ceramic bodies, soldermask)
- Mat4cad mat_base property: 0=plastic, 2=metal
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import logging
import sys

logger = logging.getLogger(__name__)


@dataclass
class RenderConfig:
    """Configuration for rendering."""

    cameras: List[Dict]
    lighting: Dict
    background: List[float]
    resolution: int
    render_samples: int = 128
    denoise: bool = True
    use_gpu: bool = True

    @classmethod
    def from_dict(cls, config: dict) -> "RenderConfig":
        """Create config from dictionary (loaded from YAML)."""
        return cls(
            cameras=config["cameras"],
            lighting=config["lighting"],
            background=config["background"]["color"],
            resolution=config["resolution"],
            render_samples=config["render"].get("samples", 128),
            denoise=config["render"].get("denoise", True),
            use_gpu=config["render"].get("use_gpu", True),
        )


class BProcRenderer:
    """
    BlenderProc renderer with segmentation.

    Ported from POC src/bproc_renderer.py
    """

    def __init__(self, config: RenderConfig):
        """
        Initialize renderer.

        Args:
            config: Render configuration
        """
        self.config = config

    def render(self, blend_path: Path, output_dir: Path) -> Path:
        """
        Render with segmentation masks.

        Args:
            blend_path: Path to .blend file
            output_dir: Directory for output files

        Returns:
            Path to generated HDF5 file

        Implementation from POC src/bproc_renderer.py
        """
        try:
            import blenderproc as bproc
            import bpy
        except ImportError:
            raise RuntimeError("blenderproc and bpy required - must run in Blender environment")

        logger.info(f"Rendering {blend_path.name}...")

        # Initialize BlenderProc
        bproc.init()

        # Register pcb2blender materials for Mat4CAD node support
        self._register_pcb2blender_materials()

        # Load the blend file
        objs = bproc.loader.load_blend(str(blend_path))
        logger.info(f"Loaded {len(objs)} objects from {blend_path.name}")

        # Assign category IDs for segmentation
        self._assign_category_ids()

        # Split multi-material objects for per-face segmentation
        self._split_multimaterial_objects()

        # Set background
        bproc.renderer.set_world_background(self.config.background)

        # Setup lighting
        self._setup_lighting()

        # Setup cameras
        self._setup_cameras()

        # Configure rendering
        bproc.camera.set_resolution(self.config.resolution, self.config.resolution)

        # Enable depth rendering
        bproc.renderer.enable_depth_output(activate_antialiasing=False)

        # Enable segmentation output
        bproc.renderer.enable_segmentation_output(
            map_by=["category_id", "material", "instance", "name"],
            default_values={'category_id': 0, 'material': None}
        )

        # Render
        data = bproc.renderer.render()

        # Save to HDF5
        output_dir.mkdir(parents=True, exist_ok=True)
        bproc.writer.write_hdf5(str(output_dir), data)

        # Find the output file (BlenderProc creates numbered files)
        output_files = list(output_dir.glob("*.hdf5"))
        if output_files:
            output_path = output_files[-1]  # Get the latest
        else:
            output_path = output_dir / f"{blend_path.stem}.hdf5"

        logger.info(f"Render complete: {output_path}")

        return output_path

    def _register_pcb2blender_materials(self):
        """Register pcb2blender materials for Mat4CAD node support."""
        import bpy

        addon_path = Path(__file__).parent.parent.parent / "pcb2blender"
        if str(addon_path) not in sys.path:
            sys.path.insert(0, str(addon_path))

        try:
            from pcb2blender_importer import materials
            materials.register()
            logger.info("✓ Registered pcb2blender materials")
        except Exception as e:
            logger.warning(f"Could not register pcb2blender materials: {e}")

    def _assign_category_ids(self):
        """
        Assign segmentation categories based on materials.

        CRITICAL IMPLEMENTATION from POC:
        - Check Mat4cad BSDF nodes
        - mat_base property: 0=plastic, 2=metal
        - Check node group names (MAT4CAD_metal vs MAT4CAD_plastic)
        - Material keywords: solder, copper, metal, tin
        """
        import bpy

        logger.info("Assigning segmentation category IDs...")
        stats = {'metal_probable': 0, 'non_metal': 0}

        # First, assign category IDs to materials
        for mat in bpy.data.materials:
            mat_name_lower = mat.name.lower()
            is_metal = False

            # Check material name for metal keywords
            if any(keyword in mat_name_lower for keyword in ['solder', 'copper', 'pad', 'metal', 'tin']):
                is_metal = True

            # Check shader nodes for metal surface indicators
            if mat.use_nodes and mat.node_tree:
                has_metal_node = False
                has_nonmetal_node = False

                for node in mat.node_tree.nodes:
                    node_name_lower = node.name.lower()

                    # Check Mat4cad BSDF nodes for component surface types
                    if 'mat4cad' in node_name_lower:
                        # Check the mat_base property (2 = metal surface)
                        if 'mat_base' in node.keys():
                            mat_base_val = node['mat_base']
                            if mat_base_val == 2:
                                has_metal_node = True
                                logger.debug(f"  Mat4cad in {mat.name}: mat_base={mat_base_val} -> METAL")
                                break
                        # Also check the node group name
                        if hasattr(node, 'node_tree') and node.node_tree:
                            group_name_lower = node.node_tree.name.lower()
                            if 'metal' in group_name_lower:
                                has_metal_node = True
                                logger.debug(f"  Mat4cad group {node.node_tree.name} -> METAL")
                                break
                            elif 'plastic' in group_name_lower or 'ceramic' in group_name_lower:
                                has_nonmetal_node = True
                                logger.debug(f"  Mat4cad group {node.node_tree.name} -> NON-METAL")
                                break

                    # Check for PCB-specific metal nodes
                    if any(keyword in node_name_lower for keyword in ['exposed_copper', 'solder']):
                        has_metal_node = True
                    # Check for PCB-specific non-metal nodes
                    if any(keyword in node_name_lower for keyword in ['solder_mask', 'silkscreen', 'base_material']):
                        has_nonmetal_node = True

                # Prioritize metal detection
                if has_metal_node:
                    is_metal = True
                elif has_nonmetal_node:
                    is_metal = False

            if is_metal:
                mat['category_id'] = 1  # Probable - metal
                logger.debug(f"  Metal material: {mat.name} -> category 1")
            else:
                mat['category_id'] = 2  # Non-probable - non-metal

        # Then assign to objects based on their materials or object name
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue

            # Solder joints are always metal (probable)
            if obj.name.startswith('SOLDER_'):
                obj['category_id'] = 1
                stats['metal_probable'] += 1
            # Skip PCB objects - let them use material-based segmentation
            elif obj.name.startswith('PCB_'):
                pass
            # For component objects, assign based on their material
            else:
                if obj.material_slots and len(obj.material_slots) > 0:
                    first_mat = obj.material_slots[0].material
                    if first_mat and 'category_id' in first_mat:
                        obj['category_id'] = first_mat['category_id']
                        if first_mat['category_id'] == 1:
                            stats['metal_probable'] += 1
                        else:
                            stats['non_metal'] += 1
                    else:
                        obj['category_id'] = 2
                        stats['non_metal'] += 1
                else:
                    obj['category_id'] = 2
                    stats['non_metal'] += 1

        logger.info(f"✓ Assigned category IDs:")
        logger.info(f"  Metal/Probable (cat 1):     {stats['metal_probable']}")
        logger.info(f"  Non-metal (cat 2):          {stats['non_metal']}")

    def _split_multimaterial_objects(self):
        """
        Split objects by material for per-face segmentation.

        Uses: bpy.ops.mesh.separate(type='MATERIAL')
        """
        import bpy

        logger.info("Splitting multi-material objects for per-face segmentation...")
        objects_to_process = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        split_count = 0
        multi_mat_count = 0

        for obj in objects_to_process:
            # Skip solder joints and PCB (handle them separately)
            if obj.name.startswith('SOLDER_') or obj.name.startswith('PCB_'):
                continue

            # Check if object has multiple UNIQUE materials
            unique_mats = set()
            for slot in obj.material_slots:
                if slot.material:
                    unique_mats.add(slot.material.name)

            if len(unique_mats) > 1:
                multi_mat_count += 1

                # Select only this object
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                # Enter edit mode and separate by material
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.separate(type='MATERIAL')
                bpy.ops.object.mode_set(mode='OBJECT')

                split_count += 1
                logger.debug(f"  Split {obj.name}: {len(unique_mats)} materials")

        logger.info(f"  Found {multi_mat_count} multi-material objects, split {split_count}")

    def _setup_lighting(self):
        """Setup sun + fill lights from config."""
        import blenderproc as bproc

        # Create main sun lamp
        sun_config = self.config.lighting["sun"]
        sun_light = bproc.types.Light(light_type="SUN")
        sun_light.set_location(sun_config["location"])
        sun_light.set_rotation_euler(sun_config["rotation"])
        sun_light.set_energy(sun_config["energy"])

        # Create fill lights
        for fill_config in self.config.lighting["fill_lights"]:
            fill_light = bproc.types.Light(light_type="POINT")
            fill_light.set_location(fill_config["location"])
            fill_light.set_energy(fill_config["energy"])

        logger.debug("Lighting setup complete")

    def _setup_cameras(self):
        """Setup camera positions from config."""
        import blenderproc as bproc

        for camera in self.config.cameras:
            position = camera["position"]
            rotation = camera["rotation"]
            matrix_world = bproc.math.build_transformation_mat(position, rotation)
            bproc.camera.add_camera_pose(matrix_world)

        logger.debug(f"Added {len(self.config.cameras)} camera poses")
