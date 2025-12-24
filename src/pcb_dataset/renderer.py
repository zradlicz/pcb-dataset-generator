"""
BlenderProc rendering with material-based segmentation.

Direct port from POC: src/bproc_renderer.py (working version)
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging
import sys
import random

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
    domain_randomization: Optional[Dict] = None

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
            domain_randomization=config.get("domain_randomization"),
        )


class BProcRenderer:
    """
    BlenderProc renderer with segmentation.

    Direct port from POC src/bproc_renderer.py
    """

    def __init__(self, config: RenderConfig):
        """Initialize renderer."""
        self.config = config

    def _apply_lighting_randomization(self, lighting_config: Dict) -> Dict:
        """Apply domain randomization to lighting parameters."""
        if not self.config.domain_randomization or not self.config.domain_randomization.get("enabled", False):
            return lighting_config

        dr_config = self.config.domain_randomization
        lighting_dr = dr_config.get("lighting", {})

        # Randomize sun energy
        if "sun_energy_range" in lighting_dr:
            min_energy, max_energy = lighting_dr["sun_energy_range"]
            lighting_config["sun"]["energy"] = random.uniform(min_energy, max_energy)

        # Randomize sun rotation
        if "sun_rotation_range" in lighting_dr:
            rotation_ranges = lighting_dr["sun_rotation_range"]
            lighting_config["sun"]["rotation"] = [
                random.uniform(rotation_ranges["x"][0], rotation_ranges["x"][1]),
                random.uniform(rotation_ranges["y"][0], rotation_ranges["y"][1]),
                random.uniform(rotation_ranges["z"][0], rotation_ranges["z"][1]),
            ]

        # Randomize fill light energy
        if "fill_energy_range" in lighting_dr:
            min_energy, max_energy = lighting_dr["fill_energy_range"]
            for fill_light in lighting_config["fill_lights"]:
                fill_light["energy"] = random.uniform(min_energy, max_energy)

        return lighting_config

    def _apply_camera_randomization(self, cameras: List[Dict]) -> List[Dict]:
        """Apply domain randomization to camera parameters."""
        if not self.config.domain_randomization or not self.config.domain_randomization.get("enabled", False):
            return cameras

        dr_config = self.config.domain_randomization
        camera_dr = dr_config.get("camera", {})

        randomized_cameras = []
        for camera in cameras:
            randomized_camera = camera.copy()

            # Apply position offset
            if "position_offset_range" in camera_dr:
                offset_ranges = camera_dr["position_offset_range"]
                randomized_camera["position"] = [
                    camera["position"][0] + random.uniform(offset_ranges["x"][0], offset_ranges["x"][1]),
                    camera["position"][1] + random.uniform(offset_ranges["y"][0], offset_ranges["y"][1]),
                    camera["position"][2] + random.uniform(offset_ranges["z"][0], offset_ranges["z"][1]),
                ]

            # Apply rotation offset
            if "rotation_offset_range" in camera_dr:
                rotation_ranges = camera_dr["rotation_offset_range"]
                randomized_camera["rotation"] = [
                    camera["rotation"][0] + random.uniform(rotation_ranges["x"][0], rotation_ranges["x"][1]),
                    camera["rotation"][1] + random.uniform(rotation_ranges["y"][0], rotation_ranges["y"][1]),
                    camera["rotation"][2] + random.uniform(rotation_ranges["z"][0], rotation_ranges["z"][1]),
                ]

            randomized_cameras.append(randomized_camera)

        return randomized_cameras

    def _apply_background_randomization(self) -> List[float]:
        """Apply domain randomization to background color."""
        if not self.config.domain_randomization or not self.config.domain_randomization.get("enabled", False):
            return self.config.background

        dr_config = self.config.domain_randomization
        background_dr = dr_config.get("background", {})

        if background_dr.get("randomize_color", False) and "color_options" in background_dr:
            return random.choice(background_dr["color_options"])

        return self.config.background

    def _apply_soldermask_randomization(self, bpy) -> Optional[Dict]:
        """Apply domain randomization to soldermask color."""
        if not self.config.domain_randomization or not self.config.domain_randomization.get("enabled", False):
            return None

        dr_config = self.config.domain_randomization
        soldermask_dr = dr_config.get("soldermask", {})

        if soldermask_dr.get("randomize_color", False) and "color_options" in soldermask_dr:
            selected_color = random.choice(soldermask_dr["color_options"])

            # Find and modify soldermask materials
            for mat in bpy.data.materials:
                mat_name_lower = mat.name.lower()
                if "solder_mask" in mat_name_lower or "soldermask" in mat_name_lower:
                    # Modify the material's base color
                    if mat.use_nodes and mat.node_tree:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                # Set base color
                                node.inputs['Base Color'].default_value = selected_color["rgb"] + [1.0]  # Add alpha
                                # Set metallic and roughness if available
                                if 'Metallic' in node.inputs:
                                    node.inputs['Metallic'].default_value = selected_color.get("metallic", 0.1)
                                if 'Roughness' in node.inputs:
                                    node.inputs['Roughness'].default_value = selected_color.get("roughness", 0.4)

            logger.info(f"Randomized soldermask color to: {selected_color['name']}")
            return selected_color

        return None

    def render(self, blend_path: Path, output_dir: Path) -> Path:
        """
        Render with segmentation masks.

        Exact implementation from POC src/bproc_renderer.py
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
        addon_path = Path(__file__).parent.parent.parent / "pcb2blender"
        if str(addon_path) not in sys.path:
            sys.path.insert(0, str(addon_path))

        try:
            from pcb2blender_importer import materials
            materials.register()
            print("✓ Registered pcb2blender materials")
        except Exception as e:
            print(f"Warning: Could not register pcb2blender materials: {e}")

        # Load the objects into the scene
        objs = bproc.loader.load_blend(str(blend_path))
        print(f"Loaded {len(objs)} objects")

        # === EXACT POC SEGMENTATION LOGIC ===
        print("\nAssigning segmentation category IDs...")
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
                                break
                        # Also check the node group name
                        if hasattr(node, 'node_tree') and node.node_tree:
                            group_name_lower = node.node_tree.name.lower()
                            if 'metal' in group_name_lower:
                                has_metal_node = True
                                break
                            elif 'plastic' in group_name_lower or 'ceramic' in group_name_lower:
                                has_nonmetal_node = True
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
                print(f"  Metal material: {mat.name} -> category 1")
            else:
                mat['category_id'] = 2  # Non-probable - non-metal

        # Split multi-material objects to allow per-material segmentation
        print("\nSplitting multi-material objects for per-face segmentation...")
        objects_to_process = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        split_count = 0
        multi_mat_count = 0

        for obj in objects_to_process:
            # Skip solder joints and PCB
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

        print(f"\nFound {multi_mat_count} multi-material objects, split {split_count}\n")

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
            # For component objects, assign based on their single material
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

        print(f"\n✓ Assigned category IDs:")
        print(f"  Metal/Probable (cat 1):         {stats['metal_probable']}")
        print(f"  Non-metal/Non-probable (cat 2): {stats['non_metal']}\n")

        # Apply domain randomization to soldermask color (before rendering)
        soldermask_color = self._apply_soldermask_randomization(bpy)

        # Apply domain randomization to background
        background_color = self._apply_background_randomization()
        bproc.renderer.set_world_background(background_color)
        if self.config.domain_randomization and self.config.domain_randomization.get("enabled", False):
            logger.info(f"Randomized background color to: {background_color}")

        # Apply domain randomization to lighting
        lighting_config = self._apply_lighting_randomization(self.config.lighting.copy())

        # Setup lighting with randomized parameters
        sun_config = lighting_config["sun"]
        sun_light = bproc.types.Light(light_type="SUN")
        sun_light.set_location(sun_config["location"])
        sun_light.set_rotation_euler(sun_config["rotation"])
        sun_light.set_energy(sun_config["energy"])
        if self.config.domain_randomization and self.config.domain_randomization.get("enabled", False):
            logger.info(f"Randomized sun: energy={sun_config['energy']:.2f}, rotation={sun_config['rotation']}")

        # Create fill lights with randomized energy
        for i, fill_config in enumerate(lighting_config["fill_lights"]):
            fill_light = bproc.types.Light(light_type="POINT")
            fill_light.set_location(fill_config["location"])
            fill_light.set_energy(fill_config["energy"])

        # Apply domain randomization to cameras
        randomized_cameras = self._apply_camera_randomization(self.config.cameras)

        # Setup cameras from config with randomization
        bproc.camera.set_resolution(self.config.resolution, self.config.resolution)
        for camera in randomized_cameras:
            position = camera["position"]
            rotation = camera["rotation"]
            matrix_world = bproc.math.build_transformation_mat(position, rotation)
            bproc.camera.add_camera_pose(matrix_world)
            if self.config.domain_randomization and self.config.domain_randomization.get("enabled", False):
                logger.info(f"Randomized camera: position={position}, rotation={rotation}")

        # Configure GPU rendering if enabled
        if self.config.use_gpu:
            bproc.renderer.set_render_devices(desired_gpu_device_type='OPTIX')
            bpy.context.scene.cycles.device = 'GPU'
            print("GPU rendering enabled (OPTIX)")

        # Set render samples
        bproc.renderer.set_max_amount_of_samples(self.config.render_samples)
        if self.config.denoise:
            bproc.renderer.enable_normals_output()
            bpy.context.scene.cycles.use_denoising = True
            print(f"Denoising enabled with {self.config.render_samples} samples")

        # Enable depth rendering
        bproc.renderer.enable_depth_output(activate_antialiasing=False)

        # Enable segmentation output
        bproc.renderer.enable_segmentation_output(
            map_by=["category_id", "material", "instance", "name"],
            default_values={'category_id': 0, 'material': None}
        )

        # Render
        print("\nRendering...")
        data = bproc.renderer.render()

        # Save to HDF5
        output_dir.mkdir(parents=True, exist_ok=True)
        bproc.writer.write_hdf5(str(output_dir), data)

        # Find the output file
        output_files = list(output_dir.glob("*.hdf5"))
        if output_files:
            output_path = output_files[-1]
        else:
            output_path = output_dir / f"{blend_path.stem}.hdf5"

        logger.info(f"Render complete: {output_path}")
        return output_path
