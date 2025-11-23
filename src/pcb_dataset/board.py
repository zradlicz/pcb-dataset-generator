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

logger = logging.getLogger(__name__)


class ComponentLibrary:
    """
    Expanded component library matching POC implementation.
    Maps component types to KiCad footprints with physical dimensions.
    """

    def __init__(self):
        """Initialize component library."""
        # Component mapping: POC ExpandedComponentLibrary condensed
        self.components = {
            # Small components
            "resistor": {
                "footprint": "Resistor_SMD:R_0805_2012Metric",
                "value": "10k",
                "reference_prefix": "R",
                "size": (2.0, 1.25),  # mm
                "num_pins": 2,
            },
            "capacitor": {
                "footprint": "Capacitor_SMD:C_0805_2012Metric",
                "value": "100nF",
                "reference_prefix": "C",
                "size": (2.0, 1.25),
                "num_pins": 2,
            },
            "led": {
                "footprint": "LED_SMD:LED_0805_2012Metric",
                "value": "LED",
                "reference_prefix": "D",
                "size": (2.0, 1.25),
                "num_pins": 2,
            },
            "diode": {
                "footprint": "Diode_SMD:D_0805_2012Metric",
                "value": "DIODE",
                "reference_prefix": "D",
                "size": (2.0, 1.25),
                "num_pins": 2,
            },
            # Medium components
            "ic_8pin": {
                "footprint": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                "value": "IC",
                "reference_prefix": "U",
                "size": (3.9, 4.9),
                "num_pins": 8,
            },
            "ic_16pin": {
                "footprint": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
                "value": "IC",
                "reference_prefix": "U",
                "size": (3.9, 9.9),
                "num_pins": 16,
            },
            "connector_small": {
                "footprint": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                "value": "CONN",
                "reference_prefix": "J",
                "size": (2.54, 10.16),
                "num_pins": 4,
            },
            # Large components
            "ic_32pin": {
                "footprint": "Package_QFP:TQFP-32_7x7mm_P0.8mm",
                "value": "IC",
                "reference_prefix": "U",
                "size": (7.0, 7.0),
                "num_pins": 32,
            },
            "ic_64pin": {
                "footprint": "Package_QFP:TQFP-64_10x10mm_P0.5mm",
                "value": "IC",
                "reference_prefix": "U",
                "size": (10.0, 10.0),
                "num_pins": 64,
            },
            "connector_large": {
                "footprint": "Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical",
                "value": "CONN",
                "reference_prefix": "J",
                "size": (5.08, 20.32),
                "num_pins": 16,
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
