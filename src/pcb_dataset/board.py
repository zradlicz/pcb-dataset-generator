"""
KiCad board creation from component placements.

Ported from POC: src/generative_board_creator.py
"""

from pathlib import Path
from typing import List, Optional, Dict
import logging
import uuid
import os

try:
    import pcbnew
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("pcbnew not available - KiCad must be installed")
    pcbnew = None

from pcb_dataset.placement import ComponentPlacement
from pcb_dataset.routing import add_routing_to_board

logger = logging.getLogger(__name__)


class ComponentLibrary:
    """
    Expanded component library matching POC implementation.
    Maps component types to KiCad footprints with physical dimensions.
    """

    def __init__(self):
        """Initialize the expanded component library."""
        self.components = {
            # Small SMD passives (resistors, capacitors, inductors)
            'resistor_0402': {
                'footprint': 'Resistor_SMD:R_0402_1005Metric',
                'value': '10k',
                'reference_prefix': 'R',
                'size': (1.0, 0.5),  # mm
                'num_pins': 2
            },
            'resistor_0603': {
                'footprint': 'Resistor_SMD:R_0603_1608Metric',
                'value': '10k',
                'reference_prefix': 'R',
                'size': (1.6, 0.8),
                'num_pins': 2
            },
            'resistor_0805': {
                'footprint': 'Resistor_SMD:R_0805_2012Metric',
                'value': '10k',
                'reference_prefix': 'R',
                'size': (2.0, 1.25),
                'num_pins': 2
            },
            'resistor_1206': {
                'footprint': 'Resistor_SMD:R_1206_3216Metric',
                'value': '10k',
                'reference_prefix': 'R',
                'size': (3.2, 1.6),
                'num_pins': 2
            },
            'capacitor_0402': {
                'footprint': 'Capacitor_SMD:C_0402_1005Metric',
                'value': '100nF',
                'reference_prefix': 'C',
                'size': (1.0, 0.5),
                'num_pins': 2
            },
            'capacitor_0603': {
                'footprint': 'Capacitor_SMD:C_0603_1608Metric',
                'value': '100nF',
                'reference_prefix': 'C',
                'size': (1.6, 0.8),
                'num_pins': 2
            },
            'capacitor_0805': {
                'footprint': 'Capacitor_SMD:C_0805_2012Metric',
                'value': '100nF',
                'reference_prefix': 'C',
                'size': (2.0, 1.25),
                'num_pins': 2
            },
            'capacitor_1206': {
                'footprint': 'Capacitor_SMD:C_1206_3216Metric',
                'value': '100nF',
                'reference_prefix': 'C',
                'size': (3.2, 1.6),
                'num_pins': 2
            },
            'inductor_0805': {
                'footprint': 'Inductor_SMD:L_0805_2012Metric',
                'value': '10uH',
                'reference_prefix': 'L',
                'size': (2.0, 1.25),
                'num_pins': 2
            },
            'inductor_1206': {
                'footprint': 'Inductor_SMD:L_1206_3216Metric',
                'value': '10uH',
                'reference_prefix': 'L',
                'size': (3.2, 1.6),
                'num_pins': 2
            },

            # Medium ICs
            'soic8': {
                'footprint': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (3.9, 4.9),
                'num_pins': 8
            },
            'soic14': {
                'footprint': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (3.9, 8.7),
                'num_pins': 14
            },
            'soic16': {
                'footprint': 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (3.9, 9.9),
                'num_pins': 16
            },
            'tssop14': {
                'footprint': 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (4.4, 5.0),
                'num_pins': 14
            },
            'tssop16': {
                'footprint': 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (4.4, 5.0),
                'num_pins': 16
            },
            'tssop20': {
                'footprint': 'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (4.4, 6.5),
                'num_pins': 20
            },
            'qfp32': {
                'footprint': 'Package_QFP:LQFP-32_7x7mm_P0.8mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (7.0, 7.0),
                'num_pins': 32
            },
            'qfp44': {
                'footprint': 'Package_QFP:LQFP-44_10x10mm_P0.8mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (10.0, 10.0),
                'num_pins': 44
            },
            'qfp48': {
                'footprint': 'Package_QFP:LQFP-48_7x7mm_P0.5mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (7.0, 7.0),
                'num_pins': 48
            },
            'qfp64': {
                'footprint': 'Package_QFP:LQFP-64_10x10mm_P0.5mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (10.0, 10.0),
                'num_pins': 64
            },

            # Large ICs
            'qfp80': {
                'footprint': 'Package_QFP:LQFP-80_12x12mm_P0.5mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (12.0, 12.0),
                'num_pins': 80
            },
            'qfp100': {
                'footprint': 'Package_QFP:LQFP-100_14x14mm_P0.5mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (14.0, 14.0),
                'num_pins': 100
            },
            'qfp144': {
                'footprint': 'Package_QFP:LQFP-144_20x20mm_P0.5mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (20.0, 20.0),
                'num_pins': 144
            },
            'bga64': {
                'footprint': 'Package_BGA:BGA-64_9.0x9.0mm_Layout10x10_P0.8mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (9.0, 9.0),
                'num_pins': 64
            },
            'bga100': {
                'footprint': 'Package_BGA:BGA-100_11.0x11.0mm_Layout10x10_P1.0mm_Ball0.5mm_Pad0.4mm_NSMD',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (11.0, 11.0),
                'num_pins': 100
            },
            'bga144': {
                'footprint': 'Package_BGA:BGA-144_13.0x13.0mm_Layout12x12_P1.0mm',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (13.0, 13.0),
                'num_pins': 144
            },
            'bga256': {
                'footprint': 'Package_BGA:BGA-256_17.0x17.0mm_Layout16x16_P1.0mm_Ball0.5mm_Pad0.4mm_NSMD',
                'value': 'IC',
                'reference_prefix': 'U',
                'size': (17.0, 17.0),
                'num_pins': 256
            },

            # Connectors - Pin Headers
            'connector_2pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
                'value': 'CONN',
                'reference_prefix': 'J',
                'size': (2.54, 5.08),
                'num_pins': 2
            },
            'connector_4pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
                'value': 'CONN',
                'reference_prefix': 'J',
                'size': (2.54, 10.16),
                'num_pins': 4
            },
            'connector_6pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
                'value': 'CONN',
                'reference_prefix': 'J',
                'size': (2.54, 15.24),
                'num_pins': 6
            },
            'connector_8pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical',
                'value': 'CONN',
                'reference_prefix': 'J',
                'size': (2.54, 20.32),
                'num_pins': 8
            },
            'connector_10pin': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical',
                'value': 'CONN',
                'reference_prefix': 'J',
                'size': (2.54, 25.4),
                'num_pins': 10
            },
            'connector_2x5': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical',
                'value': 'CONN',
                'reference_prefix': 'J',
                'size': (5.08, 12.7),
                'num_pins': 10
            },
            'connector_2x8': {
                'footprint': 'Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical',
                'value': 'CONN',
                'reference_prefix': 'J',
                'size': (5.08, 20.32),
                'num_pins': 16
            },

            # JST Connectors
            'jst_2pin': {
                'footprint': 'Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
                'value': 'JST',
                'reference_prefix': 'J',
                'size': (4.0, 7.0),
                'num_pins': 2
            },
            'jst_4pin': {
                'footprint': 'Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical',
                'value': 'JST',
                'reference_prefix': 'J',
                'size': (8.0, 7.0),
                'num_pins': 4
            },
            'jst_6pin': {
                'footprint': 'Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical',
                'value': 'JST',
                'reference_prefix': 'J',
                'size': (12.0, 7.0),
                'num_pins': 6
            },
            'jst_8pin': {
                'footprint': 'Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical',
                'value': 'JST',
                'reference_prefix': 'J',
                'size': (16.0, 7.0),
                'num_pins': 8
            },

            # Circular/Radial Capacitors (Through-hole electrolytic)
            'cap_radial_5mm': {
                'footprint': 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm',
                'value': '100uF',
                'reference_prefix': 'C',
                'size': (5.0, 5.0),  # Circular: diameter
                'num_pins': 2
            },
            'cap_radial_6mm': {
                'footprint': 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',
                'value': '220uF',
                'reference_prefix': 'C',
                'size': (6.3, 6.3),
                'num_pins': 2
            },
            'cap_radial_8mm': {
                'footprint': 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
                'value': '470uF',
                'reference_prefix': 'C',
                'size': (8.0, 8.0),
                'num_pins': 2
            },
            'cap_radial_10mm': {
                'footprint': 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm',
                'value': '1000uF',
                'reference_prefix': 'C',
                'size': (10.0, 10.0),
                'num_pins': 2
            },

            # Diodes and LEDs
            'diode_sod123': {
                'footprint': 'Diode_SMD:D_SOD-123',
                'value': '1N4148',
                'reference_prefix': 'D',
                'size': (2.7, 1.6),
                'num_pins': 2
            },
            'led_0603': {
                'footprint': 'LED_SMD:LED_0603_1608Metric',
                'value': 'LED',
                'reference_prefix': 'D',
                'size': (1.6, 0.8),
                'num_pins': 2
            },
            'led_0805': {
                'footprint': 'LED_SMD:LED_0805_2012Metric',
                'value': 'LED',
                'reference_prefix': 'D',
                'size': (2.0, 1.25),
                'num_pins': 2
            },

            # Test Points
            'testpoint_1mm': {
                'footprint': 'TestPoint:TestPoint_Pad_D1.0mm',
                'value': 'TP',
                'reference_prefix': 'TP',
                'size': (1.0, 1.0),
                'num_pins': 1
            },
            'testpoint_1_5mm': {
                'footprint': 'TestPoint:TestPoint_Pad_D1.5mm',
                'value': 'TP',
                'reference_prefix': 'TP',
                'size': (1.5, 1.5),
                'num_pins': 1
            },
            'testpoint_2mm': {
                'footprint': 'TestPoint:TestPoint_Pad_D2.0mm',
                'value': 'TP',
                'reference_prefix': 'TP',
                'size': (2.0, 2.0),
                'num_pins': 1
            },
        }
        self._component_counters = {
            comp_info["reference_prefix"]: 1 for comp_info in self.components.values()
        }

    def get_component_info(self, component_type: str) -> Dict:
        """
        Get component information by type.

        Args:
            component_type: Type of component

        Returns:
            Dictionary with footprint, value, reference, size, num_pins
        """
        if component_type not in self.components:
            # Default to resistor if type not found
            logger.warning(f"Component type '{component_type}' not found, using resistor")
            component_type = "resistor"

        comp_info = self.components[component_type].copy()
        prefix = comp_info["reference_prefix"]

        # Generate unique reference
        comp_info["reference"] = f"{prefix}{self._component_counters[prefix]}"
        self._component_counters[prefix] += 1

        return comp_info


class BoardCreator:
    """
    Create KiCad boards from component placements.

    Ported from POC src/generative_board_creator.py
    """

    def __init__(self):
        """Initialize board creator."""
        self.component_library = ComponentLibrary()

    def create_board(
        self,
        placements: List[ComponentPlacement],
        output_path: Path,
        board_name: str,
        board_width: float = 100.0,
        board_height: float = 100.0,
    ) -> Path:
        """
        Create KiCad board from placements.

        Args:
            placements: List of component placements
            output_path: Path to save .kicad_pcb file
            board_name: Name of the board
            board_width: Board width in mm
            board_height: Board height in mm

        Returns:
            Path to generated .kicad_pcb file
        """
        if pcbnew is None:
            raise RuntimeError("pcbnew not available - KiCad must be installed")

        logger.info(f"Creating board '{board_name}' with {len(placements)} components...")

        # Create new board
        board = pcbnew.BOARD()

        # Create board outline
        self._create_board_outline(board, board_width, board_height)

        # Place components
        placed_components = []
        for placement in placements:
            try:
                comp_info = self.component_library.get_component_info(placement.component_type)
                footprint = self._place_component(board, placement, comp_info)
                placed_components.append({
                    "reference": comp_info["reference"],
                    "value": comp_info["value"],
                    "footprint": comp_info["footprint"],
                })
            except Exception as e:
                logger.warning(f"Failed to place component {placement.component_type}: {e}")

        logger.info(f"Placed {len(placed_components)} components on board")

        # Add soldermask (enabled by default in KiCad)
        self._add_soldermask(board)

        # Add routing (copper traces)
        logger.info("Adding routing...")
        routing_stats = add_routing_to_board(
            board, placements, board_width, board_height,
            params={'add_ground_pour': False}  # Temporarily disable to debug segfault
        )
        logger.info(f"Routing stats: {routing_stats}")

        # Save board
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        board.Save(str(output_path))

        logger.info(f"Board saved: {output_path}")

        # Create schematic
        schematic_path = output_path.with_suffix(".kicad_sch")
        self._create_schematic(placed_components, schematic_path)

        return output_path

    def _create_board_outline(self, board: "pcbnew.BOARD", width: float, height: float):
        """Create rectangular board outline."""
        outline = pcbnew.PCB_SHAPE(board)
        outline.SetShape(pcbnew.SHAPE_T_RECT)
        outline.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(0), pcbnew.FromMM(0)))
        outline.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(width), pcbnew.FromMM(height)))
        outline.SetLayer(pcbnew.Edge_Cuts)
        outline.SetWidth(pcbnew.FromMM(0.1))
        board.Add(outline)

    def _place_component(
        self, board: "pcbnew.BOARD", placement: ComponentPlacement, comp_info: Dict
    ) -> "pcbnew.FOOTPRINT":
        """Place a single component on the board."""
        lib_name, fp_name = comp_info["footprint"].split(":")

        # Get plugin and find footprint library
        plugin = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)

        # Standard KiCad library paths
        possible_paths = [
            f"/usr/share/kicad/footprints/{lib_name}.pretty",
            f"/usr/share/kicad/modules/{lib_name}.pretty",
            os.path.expanduser(f"~/.local/share/kicad/8.0/footprints/{lib_name}.pretty"),
            os.path.expanduser(f"~/.local/share/kicad/9.0/footprints/{lib_name}.pretty"),
        ]

        lib_path = None
        for path in possible_paths:
            if os.path.exists(path):
                lib_path = path
                break

        if lib_path is None:
            raise ValueError(f"Could not find library {lib_name}")

        # Load footprint
        footprint = plugin.FootprintLoad(lib_path, fp_name)
        if footprint is None:
            raise ValueError(f"Failed to load footprint {fp_name}")

        # Set properties
        footprint.SetReference(comp_info["reference"])
        footprint.Reference().SetVisible(True)
        footprint.SetValue(comp_info["value"])
        footprint.Value().SetVisible(True)

        # Set position
        footprint.SetPosition(
            pcbnew.VECTOR2I(pcbnew.FromMM(placement.x), pcbnew.FromMM(placement.y))
        )

        # Set rotation (convert degrees to tenths of degrees)
        footprint.SetOrientation(pcbnew.EDA_ANGLE(placement.rotation, pcbnew.DEGREES_T))

        # Verify 3D models are present (they should be loaded with the footprint from library)
        # If not present, log a warning
        if footprint.Models().empty():
            logger.debug(f"Warning: No 3D models found for {fp_name} (this may be normal for some footprints)")
        else:
            logger.debug(f"Loaded {len(footprint.Models())} 3D model(s) for {fp_name}")

        # Add to board
        footprint.SetParent(board)
        board.Add(footprint)

        return footprint

    def _add_soldermask(self, board: "pcbnew.BOARD", color: str = "green"):
        """
        Configure soldermask (enabled by default in KiCad).

        Note: Color configuration is done through board settings, not Python API.
        """
        # Soldermask is enabled by default
        pass

    def _create_schematic(self, components: List[Dict], output_path: Path):
        """
        Create minimal KiCad schematic file.

        Args:
            components: List of component dicts with reference, value, footprint
            output_path: Path to save .kicad_sch file
        """
        sch_uuid = str(uuid.uuid4())
        symbol_instances = []

        y_position = 50.8  # Starting Y position (mm)
        x_position = 50.8

        for component in components:
            comp_uuid = str(uuid.uuid4())
            ref = component["reference"]
            value = component["value"]
            footprint = component["footprint"]

            # Determine symbol type
            if ref.startswith("R"):
                lib_name = "Device:R"
            elif ref.startswith("C"):
                lib_name = "Device:C"
            elif ref.startswith("D"):
                lib_name = "Device:LED"
            elif ref.startswith("U"):
                lib_name = "Device:Generic_IC"
            elif ref.startswith("J"):
                lib_name = "Connector:Conn_01x04"
            else:
                lib_name = "Device:Component"

            # Create symbol instance
            symbol_instance = f'''  (symbol (lib_id "{lib_name}") (at {x_position} {y_position} 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid {comp_uuid})
    (property "Reference" "{ref}" (at {x_position} {y_position - 2.54} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{value}" (at {x_position} {y_position + 2.54} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "{footprint}" (at {x_position} {y_position} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "" (at {x_position} {y_position} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
  )
'''
            symbol_instances.append(symbol_instance)
            y_position += 25.4  # Space symbols 1 inch apart

        # Build complete schematic
        schematic_content = f"""(kicad_sch (version 20231229) (generator pcbnew)

  (uuid {sch_uuid})

  (paper "A4")

  (lib_symbols
  )

  (sheet_instances
    (path "/" (page "1"))
  )

{chr(10).join(symbol_instances)}
)
"""

        # Write schematic file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(schematic_content)

        logger.info(f"Schematic created: {output_path}")
