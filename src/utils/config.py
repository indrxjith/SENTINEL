"""
Configuration loader for the SENTINEL project.

This module loads YAML configuration files from the `configs/`
directory and returns them as Python dictionaries.
"""

from pathlib import Path
import yaml


# ---------------------------------------------------------------------
# Project Paths
# ---------------------------------------------------------------------

# Root folder of the project (SENTINEL/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Configuration folder
CONFIG_DIR = PROJECT_ROOT / "configs"


# ---------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------

def load_config(filename: str) -> dict:
    """
    Load a YAML configuration file.

    Parameters
    ----------
    filename : str
        Name of the YAML configuration file.

    Returns
    -------
    dict
        Configuration values as a Python dictionary.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ValueError
        If the YAML file is empty.
    """

    config_path = CONFIG_DIR / filename

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if config is None:
        raise ValueError(
            f"Configuration file '{filename}' is empty."
        )

    return config


# ---------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print(load_config("assets.yaml"))