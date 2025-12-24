"""
Component placement using Perlin noise for organic clustering.

Production wrapper around POC placement logic from:
/home/zach/code/pcb-pipeline/src/component_placement.py

Maintains production's class structure but uses exact POC algorithm.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
import numpy as np
from noise import pnoise2
import random
import logging

logger = logging.getLogger(__name__)


@dataclass
class PlacementConfig:
    """Configuration for component placement."""

    # Perlin noise parameters
    scale: float
    octaves: int
    persistence: float
    lacunarity: float
    seed: Optional[int]

    # Vignette parameters
    vignette_enabled: bool
    vignette_strength: float

    # Component counts (POC parameters)
    large_count: int
    medium_count: int
    small_med_count: int
    small_count: int
    connector_count: int
    testpoint_count: int

    # Spacing parameters (POC parameters)
    large_spacing: float
    medium_spacing: float
    small_med_spacing: float
    small_spacing: float

    # Board dimensions
    board_width: float
    board_height: float

    # Grid sizes for adaptive grid
    grid_sizes: List[float]

    @classmethod
    def from_dict(cls, config: dict) -> "PlacementConfig":
        """Create config from dictionary (loaded from YAML)."""
        # Apply domain randomization if enabled
        dr_config = config.get("domain_randomization", {})
        dr_enabled = dr_config.get("enabled", False)

        # Perlin noise parameters with optional randomization
        scale = config["perlin"]["scale"]
        octaves = config["perlin"]["octaves"]
        persistence = config["perlin"]["persistence"]
        lacunarity = config["perlin"]["lacunarity"]

        if dr_enabled:
            perlin_dr = dr_config.get("perlin", {})
            if perlin_dr.get("randomize_scale", False) and "scale_range" in perlin_dr:
                scale = random.uniform(*perlin_dr["scale_range"])
                logger.info(f"Randomized Perlin scale: {scale:.2f}")
            if perlin_dr.get("randomize_octaves", False) and "octaves_range" in perlin_dr:
                octaves = random.randint(*perlin_dr["octaves_range"])
                logger.info(f"Randomized Perlin octaves: {octaves}")
            if perlin_dr.get("randomize_persistence", False) and "persistence_range" in perlin_dr:
                persistence = random.uniform(*perlin_dr["persistence_range"])
                logger.info(f"Randomized Perlin persistence: {persistence:.2f}")
            if perlin_dr.get("randomize_lacunarity", False) and "lacunarity_range" in perlin_dr:
                lacunarity = random.uniform(*perlin_dr["lacunarity_range"])
                logger.info(f"Randomized Perlin lacunarity: {lacunarity:.2f}")

        # Vignette parameters with optional randomization
        vignette_enabled = config["vignette"]["enabled"]
        vignette_strength = config["vignette"]["strength"]

        if dr_enabled:
            vignette_dr = dr_config.get("vignette", {})
            if vignette_dr.get("randomize_strength", False) and "strength_range" in vignette_dr:
                vignette_strength = random.uniform(*vignette_dr["strength_range"])
                logger.info(f"Randomized vignette strength: {vignette_strength:.2f}")

        # Component counts with optional randomization
        large_count = config["components"].get("large", {}).get("count", 1)
        medium_count = config["components"].get("medium", {}).get("count", 20)
        small_count_total = config["components"].get("small", {}).get("count", 60)

        if dr_enabled:
            comp_dr = dr_config.get("components", {})
            if comp_dr.get("randomize_count", False) and "count_variation" in comp_dr:
                variation = comp_dr["count_variation"]
                large_count = int(large_count * random.uniform(1 - variation, 1 + variation))
                medium_count = int(medium_count * random.uniform(1 - variation, 1 + variation))
                small_count_total = int(small_count_total * random.uniform(1 - variation, 1 + variation))
                logger.info(f"Randomized component counts: large={large_count}, medium={medium_count}, small={small_count_total}")

        # Board dimensions with optional randomization
        board_width = config["board"]["width"]
        board_height = config["board"]["height"]

        if dr_enabled:
            board_dr = dr_config.get("board", {})
            if board_dr.get("randomize_dimensions", False):
                if "width_range" in board_dr:
                    board_width = random.uniform(*board_dr["width_range"])
                if "height_range" in board_dr:
                    board_height = random.uniform(*board_dr["height_range"])
                # Check for shape options
                if "shape_options" in board_dr:
                    shape = random.choice(board_dr["shape_options"])
                    if shape == "square":
                        # Make board square by using average of width and height
                        avg_dim = (board_width + board_height) / 2
                        board_width = board_height = avg_dim
                logger.info(f"Randomized board dimensions: {board_width:.1f}mm x {board_height:.1f}mm")

        # Map production config format to POC parameters
        return cls(
            scale=scale,
            octaves=octaves,
            persistence=persistence,
            lacunarity=lacunarity,
            seed=config["perlin"]["seed"],
            vignette_enabled=vignette_enabled,
            vignette_strength=vignette_strength,
            # Use POC parameter names
            large_count=large_count,
            medium_count=medium_count,
            small_med_count=small_count_total // 2,
            small_count=small_count_total // 2,
            connector_count=config["components"].get("connectors", {}).get("count", 10),
            testpoint_count=config["components"].get("testpoints", {}).get("count", 15),
            large_spacing=config["components"].get("large", {}).get("spacing", 10.0),
            medium_spacing=config["components"].get("medium", {}).get("spacing", 5.0),
            small_med_spacing=config["components"].get("small", {}).get("spacing", 3.0),
            small_spacing=config["components"].get("small", {}).get("spacing", 2.5),
            board_width=board_width,
            board_height=board_height,
            grid_sizes=config.get("grid_sizes", [24.4, 14.6, 13.5, 3.6, 1.5]),
        )


@dataclass
class ComponentPlacement:
    """Single component placement (production interface)."""

    x: float  # Position in mm
    y: float  # Position in mm
    rotation: float  # Rotation in degrees
    size_category: str  # 'small', 'medium', 'large'
    component_type: str  # Actual footprint name from library


# ============================================================================
# POC Component class - exact copy from POC
# ============================================================================

class Component:
    """
    Represents a component that can be placed on the PCB.

    Exact copy from POC: component_placement.py
    """
    def __init__(self, size, num_pins, location, threshold, rotation=0, comp_type='generic'):
        self.size = size
        self.num_pins = num_pins
        self.location = location
        self.threshold = threshold
        self.rotation = rotation
        self.comp_type = comp_type
        self.footprint_name = None  # Set during placement

    def get_bounds(self):
        """Get the bounding box of the component (accounting for rotation)."""
        x, y = self.location
        width, height = self.size

        if self.rotation in [90, 270]:
            width, height = height, width

        return (
            x - width/2,
            y - height/2,
            x + width/2,
            y + height/2
        )

    def overlaps_with(self, other, min_clearance=1.0):
        """Check if this component overlaps with another component."""
        x1_min, y1_min, x1_max, y1_max = self.get_bounds()
        x2_min, y2_min, x2_max, y2_max = other.get_bounds()

        x1_min -= min_clearance
        y1_min -= min_clearance
        x1_max += min_clearance
        y1_max += min_clearance

        no_overlap = (x1_max <= x2_min or x2_max <= x1_min or
                     y1_max <= y2_min or y2_max <= y1_min)

        return not no_overlap

    def can_place(self, noise_map, placed_components=None):
        """Check if the component can be placed at its location."""
        x, y = self.location
        height, width = noise_map.shape

        if x < 0 or x >= width or y < 0 or y >= height:
            return False

        if noise_map[int(y), int(x)] < self.threshold:
            return False

        if placed_components:
            for placed in placed_components:
                if self.overlaps_with(placed):
                    return False

        return True


# ============================================================================
# POC ExpandedComponentLibrary - subset of most common components
# ============================================================================

class ExpandedComponentLibrary:
    """
    Component library from POC.
    Subset of most commonly used components.
    """

    def __init__(self):
        self.components = {
            # Small SMD passives
            'resistor_0402': {
                'footprint': 'Resistor_SMD:R_0402_1005Metric',
                'value': '10k', 'reference_prefix': 'R',
                'size': (1.0, 0.5), 'num_pins': 2
            },
            'resistor_0603': {
                'footprint': 'Resistor_SMD:R_0603_1608Metric',
                'value': '10k', 'reference_prefix': 'R',
                'size': (1.6, 0.8), 'num_pins': 2
            },
            'resistor_0805': {
                'footprint': 'Resistor_SMD:R_0805_2012Metric',
                'value': '10k', 'reference_prefix': 'R',
                'size': (2.0, 1.25), 'num_pins': 2
            },
            'resistor_1206': {
                'footprint': 'Resistor_SMD:R_1206_3216Metric',
                'value': '10k', 'reference_prefix': 'R',
                'size': (3.2, 1.6), 'num_pins': 2
            },
            'capacitor_0402': {
                'footprint': 'Capacitor_SMD:C_0402_1005Metric',
                'value': '100nF', 'reference_prefix': 'C',
                'size': (1.0, 0.5), 'num_pins': 2
            },
            'capacitor_0603': {
                'footprint': 'Capacitor_SMD:C_0603_1608Metric',
                'value': '100nF', 'reference_prefix': 'C',
                'size': (1.6, 0.8), 'num_pins': 2
            },
            'capacitor_0805': {
                'footprint': 'Capacitor_SMD:C_0805_2012Metric',
                'value': '100nF', 'reference_prefix': 'C',
                'size': (2.0, 1.25), 'num_pins': 2
            },
            'capacitor_1206': {
                'footprint': 'Capacitor_SMD:C_1206_3216Metric',
                'value': '100nF', 'reference_prefix': 'C',
                'size': (3.2, 1.6), 'num_pins': 2
            },
            'inductor_0805': {
                'footprint': 'Inductor_SMD:L_0805_2012Metric',
                'value': '10uH', 'reference_prefix': 'L',
                'size': (2.0, 1.25), 'num_pins': 2
            },
            'inductor_1206': {
                'footprint': 'Inductor_SMD:L_1206_3216Metric',
                'value': '10uH', 'reference_prefix': 'L',
                'size': (3.2, 1.6), 'num_pins': 2
            },
            # Medium ICs
            'soic8': {
                'footprint': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (3.9, 4.9), 'num_pins': 8
            },
            'soic14': {
                'footprint': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (3.9, 8.7), 'num_pins': 14
            },
            'soic16': {
                'footprint': 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (3.9, 9.9), 'num_pins': 16
            },
            'tssop14': {
                'footprint': 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (4.4, 5.0), 'num_pins': 14
            },
            'tssop16': {
                'footprint': 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (4.4, 5.0), 'num_pins': 16
            },
            'tssop20': {
                'footprint': 'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (4.4, 6.5), 'num_pins': 20
            },
            'qfp32': {
                'footprint': 'Package_QFP:LQFP-32_7x7mm_P0.8mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (7.0, 7.0), 'num_pins': 32
            },
            'qfp44': {
                'footprint': 'Package_QFP:LQFP-44_10x10mm_P0.8mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (10.0, 10.0), 'num_pins': 44
            },
            'qfp48': {
                'footprint': 'Package_QFP:LQFP-48_7x7mm_P0.5mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (7.0, 7.0), 'num_pins': 48
            },
            'qfp64': {
                'footprint': 'Package_QFP:LQFP-64_10x10mm_P0.5mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (10.0, 10.0), 'num_pins': 64
            },
            # Large ICs
            'qfp80': {
                'footprint': 'Package_QFP:LQFP-80_12x12mm_P0.5mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (12.0, 12.0), 'num_pins': 80
            },
            'qfp100': {
                'footprint': 'Package_QFP:LQFP-100_14x14mm_P0.5mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (14.0, 14.0), 'num_pins': 100
            },
            'qfp144': {
                'footprint': 'Package_QFP:LQFP-144_20x20mm_P0.5mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (20.0, 20.0), 'num_pins': 144
            },
            'bga64': {
                'footprint': 'Package_BGA:BGA-64_9.0x9.0mm_Layout10x10_P0.8mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (9.0, 9.0), 'num_pins': 64
            },
            'bga100': {
                'footprint': 'Package_BGA:BGA-100_11.0x11.0mm_Layout10x10_P1.0mm_Ball0.5mm_Pad0.4mm_NSMD',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (11.0, 11.0), 'num_pins': 100
            },
            'bga144': {
                'footprint': 'Package_BGA:BGA-144_13.0x13.0mm_Layout12x12_P1.0mm',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (13.0, 13.0), 'num_pins': 144
            },
            'bga256': {
                'footprint': 'Package_BGA:BGA-256_17.0x17.0mm_Layout16x16_P1.0mm_Ball0.5mm_Pad0.4mm_NSMD',
                'value': 'IC', 'reference_prefix': 'U',
                'size': (17.0, 17.0), 'num_pins': 256
            },
            # Connectors
            'connector_2pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
                'value': 'CONN', 'reference_prefix': 'J',
                'size': (2.54, 5.08), 'num_pins': 2
            },
            'connector_4pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
                'value': 'CONN', 'reference_prefix': 'J',
                'size': (2.54, 10.16), 'num_pins': 4
            },
            'connector_6pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
                'value': 'CONN', 'reference_prefix': 'J',
                'size': (2.54, 15.24), 'num_pins': 6
            },
            'connector_8pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical',
                'value': 'CONN', 'reference_prefix': 'J',
                'size': (2.54, 20.32), 'num_pins': 8
            },
            'connector_10pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical',
                'value': 'CONN', 'reference_prefix': 'J',
                'size': (2.54, 25.4), 'num_pins': 10
            },
            'connector_2x5': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical',
                'value': 'CONN', 'reference_prefix': 'J',
                'size': (5.08, 12.7), 'num_pins': 10
            },
            'connector_2x8': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical',
                'value': 'CONN', 'reference_prefix': 'J',
                'size': (5.08, 20.32), 'num_pins': 16
            },
            # Diodes and LEDs
            'diode_sod123': {
                'footprint': 'Diode_SMD:D_SOD-123',
                'value': '1N4148', 'reference_prefix': 'D',
                'size': (2.7, 1.6), 'num_pins': 2
            },
            'led_0603': {
                'footprint': 'LED_SMD:LED_0603_1608Metric',
                'value': 'LED', 'reference_prefix': 'D',
                'size': (1.6, 0.8), 'num_pins': 2
            },
            'led_0805': {
                'footprint': 'LED_SMD:LED_0805_2012Metric',
                'value': 'LED', 'reference_prefix': 'D',
                'size': (2.0, 1.25), 'num_pins': 2
            },
            # Test Points
            'testpoint_1mm': {
                'footprint': 'TestPoint:TestPoint_Pad_D1.0mm',
                'value': 'TP', 'reference_prefix': 'TP',
                'size': (1.0, 1.0), 'num_pins': 1
            },
            'testpoint_1_5mm': {
                'footprint': 'TestPoint:TestPoint_Pad_D1.5mm',
                'value': 'TP', 'reference_prefix': 'TP',
                'size': (1.5, 1.5), 'num_pins': 1
            },
            'testpoint_2mm': {
                'footprint': 'TestPoint:TestPoint_Pad_D2.0mm',
                'value': 'TP', 'reference_prefix': 'TP',
                'size': (2.0, 2.0), 'num_pins': 1
            },
        }
        self._component_counters = {}

    def get_component(self, component_type: str) -> dict:
        """Get component information by type."""
        if component_type not in self.components:
            raise KeyError(f"Component type '{component_type}' not found in library")

        component = self.components[component_type].copy()
        prefix = component['reference_prefix']

        if prefix not in self._component_counters:
            self._component_counters[prefix] = 1

        component['reference'] = f"{prefix}{self._component_counters[prefix]}"
        self._component_counters[prefix] += 1

        return component
def generate_perlin_noise(width=512, height=512, scale=100.0, octaves=6,
                          persistence=0.5, lacunarity=2.0, seed=None, vignette_strength=0.5):
    """
    Generate a 2D Perlin noise map with optional radial vignette.

    Args:
        width: Width of the noise map (in mm)
        height: Height of the noise map (in mm)
        scale: Zoom level of the noise (lower = more zoomed in)
        octaves: Number of noise layers to combine
        persistence: Amplitude multiplier per octave
        lacunarity: Frequency multiplier per octave
        seed: Random seed for reproducibility
        vignette_strength: Strength of radial gradient (0=none, 1=strong)

    Returns:
        2D numpy array of noise values (normalized to 0-1)
    """
    if seed is not None:
        np.random.seed(seed)

    noise_map = np.zeros((int(height), int(width)))

    for y in range(int(height)):
        for x in range(int(width)):
            noise_value = pnoise2(
                x / scale,
                y / scale,
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
                repeatx=int(width),
                repeaty=int(height),
                base=seed if seed else 0
            )
            noise_map[y][x] = noise_value

    # Normalize to 0-1 range
    noise_map = (noise_map - noise_map.min()) / (noise_map.max() - noise_map.min())

    # Apply radial vignette (center bias)
    if vignette_strength > 0:
        center_x, center_y = width / 2, height / 2
        max_dist = np.sqrt(center_x**2 + center_y**2)

        for y in range(int(height)):
            for x in range(int(width)):
                # Calculate distance from center
                dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                # Normalize distance to 0-1
                norm_dist = dist / max_dist
                # Apply radial gradient (1 at center, 0 at edges)
                radial_factor = 1 - norm_dist
                # Blend with vignette strength
                vignette = 1 - vignette_strength + (vignette_strength * radial_factor)
                # Apply to noise
                noise_map[y, x] = noise_map[y, x] * vignette

    # Re-normalize after vignette
    if vignette_strength > 0:
        noise_map = (noise_map - noise_map.min()) / (noise_map.max() - noise_map.min())

    return noise_map


def create_adaptive_grid(noise_map, grid_sizes=None, padding=0.3):
    """
    Create an adaptive grid where cell size varies based on noise values.
    Uses discrete logarithmic step sizes with a decreasing pattern.
    High noise = larger cells, low noise = smaller cells.

    Args:
        noise_map: 2D numpy array of noise values
        grid_sizes: List of 5 discrete grid sizes [largest, ..., smallest] in mm
        padding: Padding in mm between grid cells (for component spacing)

    Returns:
        List of tuples: (x, y, width, height, noise_value) for each grid cell in mm
    """
    # Define discrete cell sizes in mm (logarithmic decreasing pattern)
    if grid_sizes is None:
        discrete_sizes = [24.4, 14.6, 13.5, 3.6, 1.5]  # mm
    else:
        discrete_sizes = grid_sizes

    def get_cell_size(noise_value):
        """Map noise value to discrete cell size."""
        # Higher noise -> index closer to 0 (larger size)
        # Lower noise -> index closer to end (smaller size)
        index = int((1 - noise_value) * (len(discrete_sizes) - 1))
        index = max(0, min(len(discrete_sizes) - 1, index))
        return discrete_sizes[index]

    height, width = noise_map.shape
    grid_cells = []

    y = 0
    while y < height:
        x = 0
        row_height = None

        while x < width:
            # Sample noise at current position
            temp_noise = noise_map[min(int(y), int(height)-1), min(int(x), int(width)-1)]
            cell_size = get_cell_size(temp_noise)

            # Calculate actual cell dimensions (don't exceed boundaries)
            cell_width = min(cell_size, width - x)

            # For the first cell in the row, determine the row height
            if row_height is None:
                row_height = min(cell_size, height - y)

            # All cells in this row use the same height for perfect tiling
            cell_height = row_height

            # NOW sample noise at the CENTER of this cell
            center_x = int(x + cell_width / 2)
            center_y = int(y + cell_height / 2)
            center_x = min(center_x, int(width) - 1)
            center_y = min(center_y, int(height) - 1)
            noise_value = noise_map[center_y, center_x]

            # Apply padding to create spacing between cells
            padded_x = x + padding
            padded_y = y + padding
            padded_width = max(0.1, cell_width - 2 * padding)
            padded_height = max(0.1, cell_height - 2 * padding)

            grid_cells.append((padded_x, padded_y, padded_width, padded_height, noise_value))

            x += cell_width

        y += row_height

    return grid_cells


def create_grid_points_for_cell(cell_x, cell_y, cell_w, cell_h, grid_spacing):
    """
    Create evenly spaced grid points within a cell.

    Args:
        cell_x, cell_y: Cell position in mm
        cell_w, cell_h: Cell dimensions in mm
        grid_spacing: Grid spacing in mm

    Returns:
        List of (x, y) tuples representing grid points in mm
    """
    grid_points = []

    # Calculate number of grid points that fit in this cell
    num_points_x = max(1, int(cell_w / grid_spacing))
    num_points_y = max(1, int(cell_h / grid_spacing))

    # Calculate actual spacing to center the grid in the cell
    actual_spacing_x = cell_w / num_points_x
    actual_spacing_y = cell_h / num_points_y

    for i in range(num_points_x):
        for j in range(num_points_y):
            point_x = cell_x + actual_spacing_x * (i + 0.5)
            point_y = cell_y + actual_spacing_y * (j + 0.5)
            grid_points.append((point_x, point_y))

    return grid_points


def place_components_with_perlin_noise(
    board_width: float,
    board_height: float,
    params: Optional[Dict] = None
) -> List[Component]:
    """
    Place components on a PCB using Perlin noise-based placement algorithm.

    Args:
        board_width: Board width in mm
        board_height: Board height in mm
        params: Dictionary of algorithm parameters (uses defaults if None)

    Returns:
        List of placed Component objects
    """
    # Default parameters (good values from testing)
    if params is None:
        params = {
            'seed': 114,
            'scale': 343.8,
            'octaves': 8,
            'persistence': 0.2055,
            'lacunarity': 3.276,
            'vignette_strength': 0.882,
            'grid_sizes': [24.4, 14.6, 13.5, 3.6, 1.5],  # mm
            'large_count': 1,
            'medium_count': 24,
            'small_med_count': 89,
            'small_count': 186,
            'large_spacing': 7.8,      # mm
            'medium_spacing': 2.1,     # mm
            'small_med_spacing': 1.4,  # mm
            'small_spacing': 1.0,      # mm
        }

    # Generate Perlin noise
    noise_map = generate_perlin_noise(
        width=board_width,
        height=board_height,
        scale=params.get('scale', 343.8),
        octaves=int(params.get('octaves', 8)),
        persistence=params.get('persistence', 0.2055),
        lacunarity=params.get('lacunarity', 3.276),
        seed=int(params.get('seed', 114)),
        vignette_strength=params.get('vignette_strength', 0.882)
    )

    # Create adaptive grid
    grid_sizes = params.get('grid_sizes', [24.4, 14.6, 13.5, 3.6, 1.5])
    grid_cells = create_adaptive_grid(noise_map, grid_sizes)

    # Categorize cells by size
    grid_size_1 = grid_sizes[0]
    grid_size_2 = grid_sizes[1]
    grid_size_3 = grid_sizes[2]
    grid_size_4 = grid_sizes[3]

    size_1_cells = [(x, y, w, h, nv) for x, y, w, h, nv in grid_cells if w >= grid_size_1 - 1.0]
    size_2_cells = [(x, y, w, h, nv) for x, y, w, h, nv in grid_cells if grid_size_2 - 1.0 <= w < grid_size_1 - 1.0]
    size_3_cells = [(x, y, w, h, nv) for x, y, w, h, nv in grid_cells if grid_size_3 - 0.5 <= w < grid_size_2 - 1.0]
    size_4_cells = [(x, y, w, h, nv) for x, y, w, h, nv in grid_cells if grid_size_4 - 0.5 <= w < grid_size_3 - 0.5]
    size_5_cells = [(x, y, w, h, nv) for x, y, w, h, nv in grid_cells if w < grid_size_4 - 0.5]

    # Initialize placement tracking
    placed_components = []
    occupied_points = set()
    np.random.seed(int(params.get('seed', 114)))

    # Define component footprints by category
    # Large components (for Size 1 cells)
    LARGE_FOOTPRINTS = [
        (14.0, 14.0, 100, 'qfp100'),    # QFP-100
        (20.0, 20.0, 144, 'qfp144'),    # QFP-144
        (11.0, 11.0, 100, 'bga100'),    # BGA-100
        (13.0, 13.0, 144, 'bga144'),    # BGA-144
        (17.0, 17.0, 256, 'bga256'),    # BGA-256
        # Large radial capacitors
        (10.0, 10.0, 2, 'cap_radial_10mm'),  # 10mm radial cap
    ]

    # Medium components (for Size 3 cells)
    MEDIUM_FOOTPRINTS = [
        (3.9, 4.9, 8, 'soic8'),         # SOIC-8
        (3.9, 8.7, 14, 'soic14'),       # SOIC-14
        (3.9, 9.9, 16, 'soic16'),       # SOIC-16
        (4.4, 5.0, 14, 'tssop14'),      # TSSOP-14
        (4.4, 5.0, 16, 'tssop16'),      # TSSOP-16
        (4.4, 6.5, 20, 'tssop20'),      # TSSOP-20
        (7.0, 7.0, 32, 'qfp32'),        # QFP-32
        (10.0, 10.0, 44, 'qfp44'),      # QFP-44
        (7.0, 7.0, 48, 'qfp48'),        # QFP-48
        (10.0, 10.0, 64, 'qfp64'),      # QFP-64
        # Radial capacitors
        (5.0, 5.0, 2, 'cap_radial_5mm'),      # 5mm radial cap
        (6.3, 6.3, 2, 'cap_radial_6mm'),      # 6mm radial cap
        (8.0, 8.0, 2, 'cap_radial_8mm'),      # 8mm radial cap
    ]

    # Small-medium components (for Size 4 cells)
    SMALL_MED_FOOTPRINTS = [
        (2.0, 1.25, 2, 'resistor_0805'),   # 0805 resistor
        (3.2, 1.6, 2, 'resistor_1206'),    # 1206 resistor
        (2.0, 1.25, 2, 'capacitor_0805'),  # 0805 capacitor
        (3.2, 1.6, 2, 'capacitor_1206'),   # 1206 capacitor
        (2.0, 1.25, 2, 'inductor_0805'),   # 0805 inductor
        (2.7, 1.6, 2, 'diode_sod123'),     # SOD-123 diode
        (2.0, 1.25, 2, 'led_0805'),        # 0805 LED
    ]

    # Small components (for Size 2 and Size 5 cells)
    SMALL_FOOTPRINTS = [
        (1.0, 0.5, 2, 'resistor_0402'),    # 0402 resistor
        (1.6, 0.8, 2, 'resistor_0603'),    # 0603 resistor
        (1.0, 0.5, 2, 'capacitor_0402'),   # 0402 capacitor
        (1.6, 0.8, 2, 'capacitor_0603'),   # 0603 capacitor
        (1.6, 0.8, 2, 'led_0603'),         # 0603 LED
    ]

    # Connectors (placed in edge zones only)
    CONNECTOR_FOOTPRINTS = [
        (2.54, 5.08, 2, 'connector_2pin'),     # 2-pin header
        (2.54, 10.16, 4, 'connector_4pin'),    # 4-pin header
        (2.54, 15.24, 6, 'connector_6pin'),    # 6-pin header
        (2.54, 20.32, 8, 'connector_8pin'),    # 8-pin header
        (2.54, 25.4, 10, 'connector_10pin'),   # 10-pin header
        (5.08, 12.7, 10, 'connector_2x5'),     # 2x5 header
        (5.08, 20.32, 16, 'connector_2x8'),    # 2x8 header
        (4.0, 7.0, 2, 'jst_2pin'),             # JST 2-pin
        (8.0, 7.0, 4, 'jst_4pin'),             # JST 4-pin
        (12.0, 7.0, 6, 'jst_6pin'),            # JST 6-pin
        (16.0, 7.0, 8, 'jst_8pin'),            # JST 8-pin
    ]

    # Test points
    TESTPOINT_FOOTPRINTS = [
        (1.0, 1.0, 1, 'testpoint_1mm'),
        (1.5, 1.5, 1, 'testpoint_1_5mm'),
        (2.0, 2.0, 1, 'testpoint_2mm'),
    ]

    # Edge keep-out zone (10% from each edge)
    edge_margin = board_width * 0.1

    def is_in_keepout(x, y, comp_w, comp_h):
        """Check if component would be in edge keep-out zone."""
        return (x - comp_w/2 < edge_margin or
                x + comp_w/2 > board_width - edge_margin or
                y - comp_h/2 < edge_margin or
                y + comp_h/2 > board_height - edge_margin)

    def try_place_component(footprints, preferred_cells, all_cells, grid_spacing, comp_type='generic', allow_rotation=True):
        """Try to place a component on grid points."""
        # Randomly select a footprint
        comp_w, comp_h, num_pins, footprint_name = footprints[np.random.randint(0, len(footprints))]

        # Random rotation for non-square components
        rotation = 0
        if allow_rotation and comp_w != comp_h and np.random.random() < 0.5:
            rotation = np.random.choice([0, 90, 180, 270])

        # Try preferred cells first
        cells_to_try = preferred_cells if preferred_cells else all_cells
        if not cells_to_try:
            return None

        # Shuffle for randomness
        shuffled_cells = cells_to_try.copy()
        np.random.shuffle(shuffled_cells)

        # Try more cells if we have many to choose from
        max_attempts = min(50, len(shuffled_cells))

        for cell_x, cell_y, cell_w, cell_h, noise_value in shuffled_cells[:max_attempts]:
            # Generate grid points for this cell
            grid_points = create_grid_points_for_cell(cell_x, cell_y, cell_w, cell_h, grid_spacing)

            # Shuffle grid points
            np.random.shuffle(grid_points)

            for comp_x, comp_y in grid_points:
                # Create unique key for this grid point
                point_key = (int(comp_x * 10), int(comp_y * 10))  # 0.1mm precision

                # Skip if already occupied
                if point_key in occupied_points:
                    continue

                # Skip edge keep-out zones
                if is_in_keepout(comp_x, comp_y, comp_w, comp_h):
                    continue

                # Clamp to bounds
                comp_x = max(comp_w/2, min(board_width - comp_w/2, comp_x))
                comp_y = max(comp_h/2, min(board_height - comp_h/2, comp_y))

                component = Component(
                    size=(comp_w, comp_h),
                    num_pins=num_pins,
                    location=(comp_x, comp_y),
                    threshold=noise_value * 0.8,
                    rotation=rotation,
                    comp_type=comp_type
                )

                # Store footprint name for later use
                component.footprint_name = footprint_name

                # Increase spacing for high-pin-count components
                # Use much larger clearances to prevent overlaps
                if num_pins > 64:
                    min_spacing = 3.0  # Large ICs need significant clearance
                elif num_pins > 16:
                    min_spacing = 2.0  # Medium ICs need moderate clearance
                else:
                    min_spacing = 1.5  # Small components need minimum clearance

                # Check collision
                can_place = True
                for placed in placed_components:
                    if component.overlaps_with(placed, min_clearance=min_spacing):
                        can_place = False
                        break

                if can_place and component.can_place(noise_map, []):
                    occupied_points.add(point_key)
                    return component

        return None

    def place_decoupling_caps_near(large_comp, count=4):
        """Place small decoupling capacitors near a large IC."""
        caps = []
        lx, ly = large_comp.location
        lw, lh = large_comp.size

        # Try to place caps around the IC with more spacing
        cap_offset_distance = max(lw, lh) / 2 + 3.0  # 3mm clearance from IC edge
        cap_offsets = [
            (cap_offset_distance, 0),      # Right
            (-cap_offset_distance, 0),     # Left
            (0, cap_offset_distance),      # Bottom
            (0, -cap_offset_distance),     # Top
        ]

        for i, (dx, dy) in enumerate(cap_offsets[:count]):
            cap_x = lx + dx
            cap_y = ly + dy

            # Check bounds
            if (cap_x < edge_margin or cap_x > board_width - edge_margin or
                cap_y < edge_margin or cap_y > board_height - edge_margin):
                continue

            cap = Component(
                size=(1.0, 0.5),  # 0402 cap
                num_pins=2,
                location=(cap_x, cap_y),
                threshold=0,
                rotation=0,
                comp_type='cap'
            )
            cap.footprint_name = 'capacitor_0402'

            # Check if can place
            if cap.can_place(noise_map, placed_components + caps):
                caps.append(cap)

        return caps

    # Place large components in Size 1 cells
    for _ in range(int(params.get('large_count', 1))):
        comp = try_place_component(
            LARGE_FOOTPRINTS,
            size_1_cells,
            grid_cells,
            grid_spacing=params.get('large_spacing', 7.8),
            comp_type='large',
            allow_rotation=False
        )
        if comp:
            placed_components.append(comp)

            # Place decoupling caps
            caps = place_decoupling_caps_near(comp, count=np.random.randint(2, 5))
            placed_components.extend(caps)

    # Place small components in Size 2 cells (40% of small components)
    small_in_size2 = int(params.get('small_count', 186) * 0.4)
    for _ in range(small_in_size2):
        comp = try_place_component(
            SMALL_FOOTPRINTS,
            size_2_cells,
            grid_cells,
            grid_spacing=params.get('small_spacing', 1.0),
            comp_type='small',
            allow_rotation=True
        )
        if comp:
            placed_components.append(comp)

    # Place medium components in Size 3 cells
    for _ in range(int(params.get('medium_count', 24))):
        comp = try_place_component(
            MEDIUM_FOOTPRINTS,
            size_3_cells,
            grid_cells,
            grid_spacing=params.get('medium_spacing', 2.1),
            comp_type='medium',
            allow_rotation=True
        )
        if comp:
            placed_components.append(comp)

    # Place small-medium components in Size 4 cells
    for _ in range(int(params.get('small_med_count', 89))):
        comp = try_place_component(
            SMALL_MED_FOOTPRINTS,
            size_4_cells,
            grid_cells,
            grid_spacing=params.get('small_med_spacing', 1.4),
            comp_type='small_med',
            allow_rotation=True
        )
        if comp:
            placed_components.append(comp)

    # Place remaining small components in Size 5 cells (60% of small components)
    small_in_size5 = int(params.get('small_count', 186) * 0.6)
    for _ in range(small_in_size5):
        comp = try_place_component(
            SMALL_FOOTPRINTS,
            size_5_cells,
            grid_cells,
            grid_spacing=params.get('small_spacing', 1.0),
            comp_type='small',
            allow_rotation=True
        )
        if comp:
            placed_components.append(comp)

    # Place connectors in edge zones only
    def is_in_edge_zone(x, y, comp_w, comp_h):
        """Check if component is in the edge zone (within edge_margin of board edge)."""
        in_left_edge = (x - comp_w/2 >= 0 and x + comp_w/2 <= edge_margin)
        in_right_edge = (x - comp_w/2 >= board_width - edge_margin and x + comp_w/2 <= board_width)
        in_top_edge = (y - comp_h/2 >= 0 and y + comp_h/2 <= edge_margin)
        in_bottom_edge = (y - comp_h/2 >= board_height - edge_margin and y + comp_h/2 <= board_height)

        return in_left_edge or in_right_edge or in_top_edge or in_bottom_edge

    def try_place_connector(footprints, num_attempts=100):
        """Try to place a connector in the edge zone."""
        for _ in range(num_attempts):
            # Randomly select a footprint
            comp_w, comp_h, num_pins, footprint_name = footprints[np.random.randint(0, len(footprints))]

            # Random rotation - prefer vertical orientation for connectors
            rotation = np.random.choice([0, 90, 180, 270])

            # Swap dimensions for rotation
            display_w, display_h = comp_w, comp_h
            if rotation in [90, 270]:
                display_w, display_h = comp_h, comp_w

            # Randomly choose which edge
            edge_choice = np.random.choice(['left', 'right', 'top', 'bottom'])

            if edge_choice == 'left':
                comp_x = edge_margin / 2
                comp_y = np.random.uniform(edge_margin + display_h/2, board_height - edge_margin - display_h/2)
            elif edge_choice == 'right':
                comp_x = board_width - edge_margin / 2
                comp_y = np.random.uniform(edge_margin + display_h/2, board_height - edge_margin - display_h/2)
            elif edge_choice == 'top':
                comp_x = np.random.uniform(edge_margin + display_w/2, board_width - edge_margin - display_w/2)
                comp_y = edge_margin / 2
            else:  # bottom
                comp_x = np.random.uniform(edge_margin + display_w/2, board_width - edge_margin - display_w/2)
                comp_y = board_height - edge_margin / 2

            component = Component(
                size=(comp_w, comp_h),
                num_pins=num_pins,
                location=(comp_x, comp_y),
                threshold=0,
                rotation=rotation,
                comp_type='connector'
            )
            component.footprint_name = footprint_name

            # Check collision with larger clearance for connectors
            min_spacing = 3.0
            can_place = True
            for placed in placed_components:
                if component.overlaps_with(placed, min_clearance=min_spacing):
                    can_place = False
                    break

            if can_place:
                return component

        return None

    # Place connectors
    connector_count = int(params.get('connector_count', 8))
    for _ in range(connector_count):
        conn = try_place_connector(CONNECTOR_FOOTPRINTS)
        if conn:
            placed_components.append(conn)

    # Place test points semi-randomly near components (inside IC zone only)
    def try_place_testpoint(num_attempts=50):
        """Try to place a test point near existing components, inside the IC zone."""
        for _ in range(num_attempts):
            # Randomly select a test point size
            tp_w, tp_h, num_pins, footprint_name = TESTPOINT_FOOTPRINTS[np.random.randint(0, len(TESTPOINT_FOOTPRINTS))]

            # Pick a random existing component to place near (prefer non-connectors)
            if placed_components:
                # Filter to get non-connector components
                non_connector_comps = [c for c in placed_components if c.comp_type != 'connector']

                if non_connector_comps:
                    nearby_comp = non_connector_comps[np.random.randint(0, len(non_connector_comps))]
                else:
                    nearby_comp = placed_components[np.random.randint(0, len(placed_components))]

                base_x, base_y = nearby_comp.location

                # Place within 5-15mm of the component
                offset_dist = np.random.uniform(5.0, 15.0)
                offset_angle = np.random.uniform(0, 2 * np.pi)

                tp_x = base_x + offset_dist * np.cos(offset_angle)
                tp_y = base_y + offset_dist * np.sin(offset_angle)
            else:
                # Fallback: random position inside IC zone
                tp_x = np.random.uniform(edge_margin + tp_w/2, board_width - edge_margin - tp_w/2)
                tp_y = np.random.uniform(edge_margin + tp_h/2, board_height - edge_margin - tp_h/2)

            # Clamp to IC zone (inside edge_margin boundary)
            tp_x = max(edge_margin + tp_w/2, min(board_width - edge_margin - tp_w/2, tp_x))
            tp_y = max(edge_margin + tp_h/2, min(board_height - edge_margin - tp_h/2, tp_y))

            # Double-check that test point is inside the IC zone
            if (tp_x - tp_w/2 < edge_margin or tp_x + tp_w/2 > board_width - edge_margin or
                tp_y - tp_h/2 < edge_margin or tp_y + tp_h/2 > board_height - edge_margin):
                continue  # Skip this attempt, try again

            testpoint = Component(
                size=(tp_w, tp_h),
                num_pins=num_pins,
                location=(tp_x, tp_y),
                threshold=0,
                rotation=0,
                comp_type='testpoint'
            )
            testpoint.footprint_name = footprint_name

            # Check collision with smaller clearance for test points
            min_spacing = 2.0
            can_place = True
            for placed in placed_components:
                if testpoint.overlaps_with(placed, min_clearance=min_spacing):
                    can_place = False
                    break

            if can_place:
                return testpoint

        return None

    # Place test points
    testpoint_count = int(params.get('testpoint_count', 15))
    for _ in range(testpoint_count):
        tp = try_place_testpoint()
        if tp:
            placed_components.append(tp)

    return placed_components


# ============================================================================
# PerlinPlacer - Production wrapper around POC algorithm
# ============================================================================

class PerlinPlacer:
    """
    Generate component placements using Perlin noise clustering.

    Uses exact POC algorithm internally but returns production ComponentPlacement objects.
    """

    def __init__(self, config: PlacementConfig):
        self.config = config
        self.lib = ExpandedComponentLibrary()

        if config.seed is not None:
            random.seed(config.seed)
            np.random.seed(config.seed)

        logger.info(f"Initialized PerlinPlacer with seed={config.seed}")

    def generate_placements(self) -> List[ComponentPlacement]:
        """
        Generate component placements using exact POC algorithm.

        Returns production ComponentPlacement objects.
        """
        logger.info("Generating component placements (POC algorithm)...")

        params = {
            'seed': self.config.seed,
            'scale': self.config.scale,
            'octaves': self.config.octaves,
            'persistence': self.config.persistence,
            'lacunarity': self.config.lacunarity,
            'vignette_strength': self.config.vignette_strength,
            'grid_sizes': self.config.grid_sizes,
            'large_count': self.config.large_count,
            'medium_count': self.config.medium_count,
            'small_med_count': self.config.small_med_count,
            'small_count': self.config.small_count,
            'connector_count': self.config.connector_count,
            'testpoint_count': self.config.testpoint_count,
            'large_spacing': self.config.large_spacing,
            'medium_spacing': self.config.medium_spacing,
            'small_med_spacing': self.config.small_med_spacing,
            'small_spacing': self.config.small_spacing,
        }

        # Call POC placement function directly (now in this file)
        poc_components = place_components_with_perlin_noise(
            board_width=self.config.board_width,
            board_height=self.config.board_height,
            params=params
        )

        # Assign footprints from library to each component
        for comp in poc_components:
            # comp.footprint_name is set by the POC algorithm
            pass

        # Convert POC Component objects to production ComponentPlacement objects
        placements = []
        for comp in poc_components:
            # Map comp_type to size_category
            if comp.comp_type in ['large']:
                size_category = 'large'
            elif comp.comp_type in ['medium']:
                size_category = 'medium'
            else:
                size_category = 'small'

            placement = ComponentPlacement(
                x=float(comp.location[0]),
                y=float(comp.location[1]),
                rotation=float(comp.rotation),
                size_category=size_category,
                component_type=comp.footprint_name  # Footprint name from POC library
            )
            placements.append(placement)

        logger.info(f"Generated {len(placements)} component placements")
        return placements
