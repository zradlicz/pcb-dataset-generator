"""
Component placement using Perlin noise for organic clustering.

This module implements the Perlin noise-based placement algorithm
from the POC (examples/step2_perlin_placement.py).
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

    # Component counts
    small_count: int
    small_spacing: float
    medium_count: int
    medium_spacing: float
    large_count: int
    large_spacing: float

    # Board dimensions
    board_width: float
    board_height: float

    # Component type distributions
    component_types: Dict[str, Dict[str, int]]

    # Rotation settings
    rotation_snap_angle: float = 90.0
    rotation_allow_45deg: bool = False
    rotation_randomize: bool = True

    @classmethod
    def from_dict(cls, config: dict) -> "PlacementConfig":
        """Create config from dictionary (loaded from YAML)."""
        return cls(
            scale=config["perlin"]["scale"],
            octaves=config["perlin"]["octaves"],
            persistence=config["perlin"]["persistence"],
            lacunarity=config["perlin"]["lacunarity"],
            seed=config["perlin"]["seed"],
            vignette_enabled=config["vignette"]["enabled"],
            vignette_strength=config["vignette"]["strength"],
            small_count=config["components"]["small"]["count"],
            small_spacing=config["components"]["small"]["spacing"],
            medium_count=config["components"]["medium"]["count"],
            medium_spacing=config["components"]["medium"]["spacing"],
            large_count=config["components"]["large"]["count"],
            large_spacing=config["components"]["large"]["spacing"],
            board_width=config["board"]["width"],
            board_height=config["board"]["height"],
            component_types=config["component_types"],
            rotation_snap_angle=config["rotation"].get("snap_angle", 90.0),
            rotation_allow_45deg=config["rotation"].get("allow_45deg", False),
            rotation_randomize=config["rotation"].get("randomize", True),
        )


@dataclass
class ComponentPlacement:
    """Single component placement."""

    x: float  # Position in mm
    y: float  # Position in mm
    rotation: float  # Rotation in degrees
    size_category: str  # 'small', 'medium', 'large'
    component_type: str  # 'resistor', 'capacitor', 'ic_8pin', etc.


class PerlinPlacer:
    """
    Generate component placements using Perlin noise clustering.

    Implementation based on POC: examples/step2_perlin_placement.py
    """

    def __init__(self, config: PlacementConfig):
        """
        Initialize placer.

        Args:
            config: Placement configuration
        """
        self.config = config

        # Set random seed if specified
        if config.seed is not None:
            random.seed(config.seed)
            np.random.seed(config.seed)

        logger.info(f"Initialized PerlinPlacer with seed={config.seed}")

    def generate_placements(self) -> List[ComponentPlacement]:
        """
        Generate component placements using Perlin noise.

        Returns:
            List of component placements

        Implementation steps:
        1. Generate Perlin noise density map
        2. Apply vignette if enabled
        3. Place components in high-density regions
        4. Ensure minimum spacing
        5. Assign component types based on weights
        """
        logger.info("Generating component placements...")

        # Generate density map
        density_map = self._generate_density_map()

        # Apply vignette
        if self.config.vignette_enabled:
            density_map = self._apply_vignette(density_map)

        # Place components
        placements = []

        # Place small components
        small_placements = self._place_components(
            density_map,
            count=self.config.small_count,
            spacing=self.config.small_spacing,
            size_category="small",
        )
        placements.extend(small_placements)

        # Place medium components
        medium_placements = self._place_components(
            density_map,
            count=self.config.medium_count,
            spacing=self.config.medium_spacing,
            size_category="medium",
        )
        placements.extend(medium_placements)

        # Place large components
        large_placements = self._place_components(
            density_map,
            count=self.config.large_count,
            spacing=self.config.large_spacing,
            size_category="large",
        )
        placements.extend(large_placements)

        logger.info(f"Generated {len(placements)} component placements")

        return placements

    def _generate_density_map(self) -> np.ndarray:
        """
        Generate Perlin noise density map.

        Returns:
            2D numpy array of density values (0-1)
        """
        # TODO: Port from POC examples/step2_perlin_placement.py
        # Use noise.pnoise2() to generate Perlin noise
        # Map resolution (100x100 grid matching board size)

        resolution = 100
        density_map = np.zeros((resolution, resolution))

        for i in range(resolution):
            for j in range(resolution):
                density_map[i][j] = pnoise2(
                    i / self.config.scale,
                    j / self.config.scale,
                    octaves=self.config.octaves,
                    persistence=self.config.persistence,
                    lacunarity=self.config.lacunarity,
                    repeatx=resolution,
                    repeaty=resolution,
                    base=self.config.seed or 0,
                )

        # Normalize to 0-1
        density_map = (density_map - density_map.min()) / (density_map.max() - density_map.min())

        return density_map

    def _apply_vignette(self, density_map: np.ndarray) -> np.ndarray:
        """
        Apply vignette effect (density falloff from edges).

        Args:
            density_map: Original density map

        Returns:
            Density map with vignette applied
        """
        # TODO: Port from POC
        # Create radial gradient from center
        # Multiply with density map

        h, w = density_map.shape
        center_y, center_x = h / 2, w / 2

        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        max_dist = np.sqrt(center_x**2 + center_y**2)

        # Vignette: 1.0 at center, falls off to edges
        vignette = 1.0 - (dist_from_center / max_dist) * self.config.vignette_strength

        return density_map * vignette

    def _place_components(
        self, density_map: np.ndarray, count: int, spacing: float, size_category: str
    ) -> List[ComponentPlacement]:
        """
        Place components in high-density regions with minimum spacing.

        Args:
            density_map: Perlin noise density map
            count: Number of components to place
            spacing: Minimum spacing in mm
            size_category: Component size category

        Returns:
            List of placed components
        """
        # TODO: Port from POC
        # Sample from density map (weighted random sampling)
        # Ensure minimum spacing
        # Assign component types based on weights
        # Assign rotations

        placements = []
        placed_positions = []

        # Flatten density map for weighted sampling
        flat_density = density_map.flatten()
        flat_density = flat_density / flat_density.sum()  # Normalize to probabilities

        h, w = density_map.shape

        attempts = 0
        max_attempts = count * 100

        while len(placements) < count and attempts < max_attempts:
            attempts += 1

            # Sample position weighted by density
            idx = np.random.choice(len(flat_density), p=flat_density)
            grid_y, grid_x = divmod(idx, w)

            # Convert to mm coordinates
            x = (grid_x / w) * self.config.board_width
            y = (grid_y / h) * self.config.board_height

            # Check spacing
            too_close = False
            for px, py in placed_positions:
                dist = np.sqrt((x - px) ** 2 + (y - py) ** 2)
                if dist < spacing:
                    too_close = True
                    break

            if not too_close:
                # Assign component type
                component_type = self._select_component_type(size_category)

                # Assign rotation
                rotation = self._generate_rotation()

                placements.append(
                    ComponentPlacement(
                        x=x,
                        y=y,
                        rotation=rotation,
                        size_category=size_category,
                        component_type=component_type,
                    )
                )

                placed_positions.append((x, y))

        if len(placements) < count:
            logger.warning(
                f"Only placed {len(placements)}/{count} {size_category} components "
                f"(spacing constraint too tight)"
            )

        return placements

    def _select_component_type(self, size_category: str) -> str:
        """
        Select component type based on weighted distribution.

        Args:
            size_category: Component size category

        Returns:
            Component type string
        """
        types = self.config.component_types.get(size_category, {})
        if not types:
            return "generic"

        # Weighted random choice
        type_names = list(types.keys())
        weights = list(types.values())
        total_weight = sum(weights)
        probabilities = [w / total_weight for w in weights]

        return np.random.choice(type_names, p=probabilities)

    def _generate_rotation(self) -> float:
        """
        Generate rotation angle based on configuration.

        Returns:
            Rotation in degrees
        """
        if not self.config.rotation_randomize:
            return 0.0

        if self.config.rotation_allow_45deg:
            # 0, 45, 90, 135, 180, 225, 270, 315
            return random.choice([0, 45, 90, 135, 180, 225, 270, 315])
        else:
            # 0, 90, 180, 270
            angles = [0, 90, 180, 270]
            return random.choice(angles)
