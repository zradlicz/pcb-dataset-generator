"""
PCB Dataset Generator

Production-ready pipeline for generating machine learning datasets
of realistic PCB images with segmentation ground truth.
"""

__version__ = "0.1.0"

from pcb_dataset.placement import PerlinPlacer, ComponentPlacement, PlacementConfig
from pcb_dataset.board import BoardCreator
from pcb_dataset.exporter import PCB3DExporter
from pcb_dataset.importer import BlenderImporter
from pcb_dataset.renderer import BProcRenderer, RenderConfig
from pcb_dataset.converter import FormatConverter
from pcb_dataset.pipeline import Pipeline, PipelineConfig

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
