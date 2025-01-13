"""Modules to perform Banff procedures."""
from pathlib import Path

# Get a list of all the modules in the current folder, non recursively
modules = Path(__file__).parent.glob("*.py")

# Form the wildcard import list of all the modules we found
__all__ = [Path(f).stem for f in modules if Path(f).is_file() and not Path(f).name.startswith("_")]

# Import the list so that they're available in modules importing this
from . import *
