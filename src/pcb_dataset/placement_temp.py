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
