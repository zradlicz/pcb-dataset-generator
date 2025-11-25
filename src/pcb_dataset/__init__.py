"""
PCB Dataset Generator

Production-ready pipeline for generating machine learning datasets
of realistic PCB images with segmentation ground truth.
"""

__version__ = "0.1.0"

# Lazy imports to avoid dependency issues in Blender environment
# Import modules directly when needed instead of at package level
__all__ = [
    "__version__",
    "PerlinPlacer",
    "ComponentPlacement",
    "PlacementConfig",
    "BoardCreator",
    "PCB3DExporter",
    "BlenderImporter",
    "BProcRenderer",
    "RenderConfig",
    "FormatConverter",
    "Pipeline",
    "PipelineConfig",
]


def __getattr__(name):
    """Lazy import to avoid loading all dependencies at once."""
    if name == "PerlinPlacer":
        from pcb_dataset.placement import PerlinPlacer
        return PerlinPlacer
    elif name == "ComponentPlacement":
        from pcb_dataset.placement import ComponentPlacement
        return ComponentPlacement
    elif name == "PlacementConfig":
        from pcb_dataset.placement import PlacementConfig
        return PlacementConfig
    elif name == "BoardCreator":
        from pcb_dataset.board import BoardCreator
        return BoardCreator
    elif name == "PCB3DExporter":
        from pcb_dataset.exporter import PCB3DExporter
        return PCB3DExporter
    elif name == "BlenderImporter":
        from pcb_dataset.importer import BlenderImporter
        return BlenderImporter
    elif name == "BProcRenderer":
        from pcb_dataset.renderer import BProcRenderer
        return BProcRenderer
    elif name == "RenderConfig":
        from pcb_dataset.renderer import RenderConfig
        return RenderConfig
    elif name == "FormatConverter":
        from pcb_dataset.converter import FormatConverter
        return FormatConverter
    elif name == "Pipeline":
        from pcb_dataset.pipeline import Pipeline
        return Pipeline
    elif name == "PipelineConfig":
        from pcb_dataset.pipeline import PipelineConfig
        return PipelineConfig
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
