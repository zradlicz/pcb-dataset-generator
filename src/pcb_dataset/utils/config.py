"""
Configuration loading and management.
"""

from pathlib import Path
from typing import Any, Dict
import yaml


class ConfigLoader:
    """Load and validate YAML configuration files."""

    def __init__(self, config_dir: Path):
        """
        Initialize config loader.

        Args:
            config_dir: Directory containing YAML config files
        """
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")

    def load(self, config_name: str) -> Dict[str, Any]:
        """
        Load a YAML configuration file.

        Args:
            config_name: Name of config file (without .yaml extension)

        Returns:
            Dictionary containing configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        config_path = self.config_dir / f"{config_name}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        return config

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all configuration files.

        Returns:
            Dictionary mapping config names to their contents
        """
        configs = {}

        for config_file in self.config_dir.glob("*.yaml"):
            config_name = config_file.stem
            configs[config_name] = self.load(config_name)

        return configs


def load_config(config_dir: Path, config_name: str) -> Dict[str, Any]:
    """
    Convenience function to load a single config file.

    Args:
        config_dir: Directory containing config files
        config_name: Name of config file (without .yaml extension)

    Returns:
        Dictionary containing configuration
    """
    loader = ConfigLoader(config_dir)
    return loader.load(config_name)
