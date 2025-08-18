"""
SH Package Identifier (SHPI)

A tool for identifying package coordinates from source code directories
by leveraging Software Heritage archive content-addressable hashing.
"""

__version__ = "0.1.0"
__author__ = "Oscar Valenzuela B."

from shpi.core.config import SHPIConfig

__all__ = ["SHPIConfig"]