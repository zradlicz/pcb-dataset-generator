"""
PCB routing module for generating realistic copper traces.

Ported from POC: src/routing.py
Generates procedural/random routing for synthetic PCB datasets.
"""

import logging
from typing import List, Tuple, Optional, Dict
import numpy as np

try:
    import pcbnew
except ImportError:
    pcbnew = None

from pcb_dataset.placement import ComponentPlacement

logger = logging.getLogger(__name__)


class Net:
    """Represents an electrical net connecting multiple component pads."""

    def __init__(self, name: str, net_type: str = 'signal'):
        """
        Args:
            name: Net name (e.g., 'GND', 'VCC', 'SIG_1')
            net_type: Type of net ('power', 'ground', 'signal')
        """
        self.name = name
        self.net_type = net_type
        self.pads = []  # List of (component_index, pad_index) tuples

    def add_pad(self, component_index: int, pad_index: int = 0):
        """Add a pad to this net."""
        self.pads.append((component_index, pad_index))


def generate_random_netlists(
    placements: List[ComponentPlacement],
    params: Optional[Dict] = None
) -> List[Net]:
    """
    Generate random electrical netlists for components.
    Creates plausible connections based on proximity.

    Args:
        placements: List of ComponentPlacement objects
        params: Routing parameters

    Returns:
        List of Net objects with connected pads
    """
    if params is None:
        params = {}

    nets = []
    net_counter = 1

    # Simplified component categorization based on size
    # In production, all components are roughly categorized
    num_components = len(placements)

    # Create power/ground nets (connect random subset of components)
    power_net = Net('VCC', 'power')
    ground_net = Net('GND', 'ground')

    # Connect power to ~40% of components (ICs and capacitors)
    for i in range(num_components):
        if np.random.random() < 0.4:
            power_net.add_pad(i, 0)  # Pin 0 = VCC
            ground_net.add_pad(i, 1)  # Pin 1 = GND

    nets.append(power_net)
    nets.append(ground_net)

    # Create signal nets by connecting nearby components
    max_signal_nets = params.get('max_signal_nets', 30)
    used_pins = set()

    for _ in range(max_signal_nets):
        # Pick random source component
        source_idx = np.random.randint(0, num_components)
        source_placement = placements[source_idx]

        # Skip pins 0,1 (reserved for power)
        source_pin = np.random.randint(2, 8)

        if (source_idx, source_pin) in used_pins:
            continue

        net = Net(f'NET_{net_counter}', 'signal')
        net_counter += 1

        net.add_pad(source_idx, source_pin)
        used_pins.add((source_idx, source_pin))

        # Find nearby component to connect
        sx, sy = source_placement.x, source_placement.y

        # Calculate distances
        candidates = []
        for target_idx in range(num_components):
            if target_idx == source_idx:
                continue

            target_placement = placements[target_idx]
            tx, ty = target_placement.x, target_placement.y
            dist = np.sqrt((sx - tx)**2 + (sy - ty)**2)

            # Find unused pin
            for target_pin in range(2, 8):
                if (target_idx, target_pin) not in used_pins:
                    candidates.append((dist, target_idx, target_pin))
                    break

        if candidates:
            # Sort by distance and pick from nearest
            candidates.sort(key=lambda x: x[0])
            choice_idx = min(np.random.randint(0, 5), len(candidates) - 1)
            _, target_idx, target_pin = candidates[choice_idx]

            net.add_pad(target_idx, target_pin)
            used_pins.add((target_idx, target_pin))

            nets.append(net)

    return nets


def get_component_pad_position(
    placement: ComponentPlacement,
    pad_index: int = 0
) -> Tuple[float, float]:
    """
    Estimate pad position for a component.
    Simplified - distributes pads around component perimeter.

    Args:
        placement: ComponentPlacement object
        pad_index: Which pad to get (0-indexed)

    Returns:
        (x, y) position in mm
    """
    cx, cy = placement.x, placement.y
    # Use default small size if not specified
    w, h = 3.0, 3.0

    # Swap if rotated 90/270
    if placement.rotation in [90, 270]:
        w, h = h, w

    # Distribute pads around perimeter (simplified)
    if pad_index == 0:
        return (cx - w/2, cy)  # Left
    elif pad_index == 1:
        return (cx + w/2, cy)  # Right
    elif pad_index == 2:
        return (cx, cy - h/2)  # Top
    elif pad_index == 3:
        return (cx, cy + h/2)  # Bottom
    else:
        # For additional pins, distribute evenly
        angle = (pad_index / 8) * 2 * np.pi
        radius = max(w, h) / 2
        return (cx + radius * np.cos(angle), cy + radius * np.sin(angle))


def route_dogleg(
    start: Tuple[float, float],
    end: Tuple[float, float],
    horizontal_first: bool = None
) -> List[Tuple[float, float]]:
    """
    Create a 2-segment Manhattan route.

    Args:
        start: (x, y) start position in mm
        end: (x, y) end position in mm
        horizontal_first: If True, go horizontal first

    Returns:
        List of waypoints
    """
    if horizontal_first is None:
        horizontal_first = np.random.random() < 0.5

    start_x, start_y = start
    end_x, end_y = end

    if horizontal_first:
        mid = (end_x, start_y)
    else:
        mid = (start_x, end_y)

    return [start, mid, end]


def route_manhattan(
    start: Tuple[float, float],
    end: Tuple[float, float],
    segments: int = None
) -> List[Tuple[float, float]]:
    """
    Create a multi-segment Manhattan route.

    Args:
        start: (x, y) start position in mm
        end: (x, y) end position in mm
        segments: Number of segments

    Returns:
        List of waypoints
    """
    if segments is None:
        segments = np.random.randint(2, 5)

    start_x, start_y = start
    end_x, end_y = end

    waypoints = [start]
    current_x, current_y = start_x, start_y
    horizontal = np.random.random() < 0.5

    for i in range(segments - 1):
        progress = (i + 1) / segments

        if horizontal:
            target_x = start_x + (end_x - start_x) * progress
            variation = (end_x - start_x) * 0.4 * (np.random.random() - 0.5)
            target_x = max(min(start_x, end_x), min(max(start_x, end_x), target_x + variation))
            waypoints.append((target_x, current_y))
            current_x = target_x
        else:
            target_y = start_y + (end_y - start_y) * progress
            variation = (end_y - start_y) * 0.4 * (np.random.random() - 0.5)
            target_y = max(min(start_y, end_y), min(max(start_y, end_y), target_y + variation))
            waypoints.append((current_x, target_y))
            current_y = target_y

        horizontal = not horizontal

    waypoints.append(end)
    return waypoints


def create_pcb_track(
    board: "pcbnew.BOARD",
    start: Tuple[float, float],
    end: Tuple[float, float],
    width: float,
    layer: int,
    net_name: str = None
) -> "pcbnew.PCB_TRACK":
    """
    Create a PCB track segment.

    Args:
        board: KiCad BOARD object
        start: (x, y) start position in mm
        end: (x, y) end position in mm
        width: Track width in mm
        layer: PCB layer
        net_name: Optional net name

    Returns:
        Created PCB_TRACK object
    """
    track = pcbnew.PCB_TRACK(board)

    # Ensure all values are native Python floats
    start_x = float(start[0])
    start_y = float(start[1])
    end_x = float(end[0])
    end_y = float(end[1])

    track.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(start_x), pcbnew.FromMM(start_y)))
    track.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(end_x), pcbnew.FromMM(end_y)))
    track.SetWidth(pcbnew.FromMM(float(width)))
    track.SetLayer(int(layer))

    # Set net if provided
    if net_name:
        netinfo = board.GetNetInfo()
        net = netinfo.GetNetItem(net_name)
        if net is None:
            # Create new net
            net = pcbnew.NETINFO_ITEM(board, net_name)
            board.Add(net)
        track.SetNet(net)

    board.Add(track)
    return track


def route_net(
    board: "pcbnew.BOARD",
    net: Net,
    placements: List[ComponentPlacement],
    params: Optional[Dict] = None
):
    """
    Route a single net connecting multiple pads.

    Args:
        board: KiCad BOARD object
        net: Net object with pads to connect
        placements: List of all component placements
        params: Routing parameters
    """
    if params is None:
        params = {}

    if len(net.pads) < 2:
        return

    # Get track width based on net type
    if net.net_type == 'power':
        track_width = params.get('power_track_width', 0.4)
    elif net.net_type == 'ground':
        track_width = params.get('ground_track_width', 0.4)
    else:
        track_width = np.random.choice([0.2, 0.25, 0.3], p=[0.5, 0.3, 0.2])

    # Use nearest neighbor to connect pads
    routed_pads = [net.pads[0]]
    unrouted_pads = list(net.pads[1:])

    while unrouted_pads:
        # Find closest unrouted pad to any routed pad
        min_dist = float('inf')
        best_routed = None
        best_unrouted = None

        for routed_comp_idx, routed_pin in routed_pads:
            routed_pos = get_component_pad_position(placements[routed_comp_idx], routed_pin)

            for unrouted_comp_idx, unrouted_pin in unrouted_pads:
                unrouted_pos = get_component_pad_position(placements[unrouted_comp_idx], unrouted_pin)

                dist = np.sqrt((routed_pos[0] - unrouted_pos[0])**2 +
                              (routed_pos[1] - unrouted_pos[1])**2)

                if dist < min_dist:
                    min_dist = dist
                    best_routed = (routed_comp_idx, routed_pin, routed_pos)
                    best_unrouted = (unrouted_comp_idx, unrouted_pin, unrouted_pos)

        if best_unrouted is None:
            break

        # Route between best_routed and best_unrouted
        start_pos = best_routed[2]
        end_pos = best_unrouted[2]

        distance = np.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)

        # Choose routing style based on distance
        route_choice = np.random.random()

        if distance < 5.0:
            if route_choice < 0.5:
                waypoints = [start_pos, end_pos]  # Straight
            else:
                waypoints = route_dogleg(start_pos, end_pos)
        elif distance < 20.0:
            if route_choice < 0.3:
                waypoints = [start_pos, end_pos]
            elif route_choice < 0.6:
                waypoints = route_dogleg(start_pos, end_pos)
            else:
                waypoints = route_manhattan(start_pos, end_pos, segments=np.random.randint(2, 4))
        else:
            if route_choice < 0.4:
                waypoints = route_dogleg(start_pos, end_pos)
            else:
                waypoints = route_manhattan(start_pos, end_pos, segments=np.random.randint(3, 6))

        # Choose layer (prefer front copper for now)
        layer = pcbnew.F_Cu

        # Create track segments
        for j in range(len(waypoints) - 1):
            start = waypoints[j]
            end = waypoints[j + 1]
            create_pcb_track(board, start, end, track_width, layer, net.name)

        # Mark as routed
        routed_pads.append((best_unrouted[0], best_unrouted[1]))
        unrouted_pads.remove((best_unrouted[0], best_unrouted[1]))


def create_ground_pour(
    board: "pcbnew.BOARD",
    board_width: float,
    board_height: float,
    layer: int = None,
    margin: float = 2.0
):
    """
    Create a ground pour (filled zone) covering most of the board.

    Args:
        board: KiCad BOARD object
        board_width: Board width in mm
        board_height: Board height in mm
        layer: Layer for ground pour (default: back copper)
        margin: Margin from board edge in mm
    """
    if layer is None:
        layer = pcbnew.B_Cu

    try:
        # Create zone
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)

        # Set zone outline (rectangle with margin)
        outline = pcbnew.SHAPE_POLY_SET()

        points = [
            pcbnew.VECTOR2I(pcbnew.FromMM(margin), pcbnew.FromMM(margin)),
            pcbnew.VECTOR2I(pcbnew.FromMM(board_width - margin), pcbnew.FromMM(margin)),
            pcbnew.VECTOR2I(pcbnew.FromMM(board_width - margin), pcbnew.FromMM(board_height - margin)),
            pcbnew.VECTOR2I(pcbnew.FromMM(margin), pcbnew.FromMM(board_height - margin))
        ]

        outline.NewOutline()
        for point in points:
            outline.Append(point)

        zone.SetOutline(outline)

        # Set zone properties
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetMinThickness(pcbnew.FromMM(0.2))
        # Don't set as filled - KiCad will fill it when opening the board
        # Setting SetIsFilled(True) without actually filling causes segfault on save
        zone.SetIsFilled(False)

        # Set net to GND
        netinfo = board.GetNetInfo()
        gnd_net = netinfo.GetNetItem("GND")
        if gnd_net is None:
            gnd_net = pcbnew.NETINFO_ITEM(board, "GND")
            board.Add(gnd_net)
        zone.SetNet(gnd_net)

        board.Add(zone)
        logger.info("Created ground pour")

    except Exception as e:
        logger.warning(f"Failed to create ground pour: {e}")


def add_routing_to_board(
    board: "pcbnew.BOARD",
    placements: List[ComponentPlacement],
    board_width: float,
    board_height: float,
    params: Optional[Dict] = None
) -> Dict:
    """
    Main function to add routing to a PCB board.

    Args:
        board: KiCad BOARD object
        placements: List of ComponentPlacement objects
        board_width: Board width in mm
        board_height: Board height in mm
        params: Routing parameters

    Returns:
        Dictionary with routing statistics
    """
    if pcbnew is None:
        raise RuntimeError("pcbnew not available - KiCad must be installed")

    if params is None:
        params = {
            'max_signal_nets': 30,
            'power_track_width': 0.5,
            'ground_track_width': 0.5,
            'add_ground_pour': True,
        }

    logger.info("Generating random netlists...")
    nets = generate_random_netlists(placements, params)

    logger.info(f"Routing {len(nets)} nets...")
    routed_count = 0
    for net in nets:
        try:
            route_net(board, net, placements, params)
            routed_count += 1
        except Exception as e:
            logger.warning(f"Failed to route net {net.name}: {e}")
            continue

    # Add ground pour on back layer
    if params.get('add_ground_pour', True):
        logger.info("Adding ground pour...")
        create_ground_pour(board, board_width, board_height)

    logger.info(f"Routing complete: {routed_count}/{len(nets)} nets routed")

    return {
        'total_nets': len(nets),
        'routed_nets': routed_count,
        'power_nets': len([n for n in nets if n.net_type == 'power']),
        'ground_nets': len([n for n in nets if n.net_type == 'ground']),
        'signal_nets': len([n for n in nets if n.net_type == 'signal']),
    }
