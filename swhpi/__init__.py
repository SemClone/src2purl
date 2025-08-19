"""
Software Heritage Package Identifier (SWHPI)

A tool for identifying package coordinates from source code directories
by leveraging Software Heritage archive content-addressable hashing.
"""

__version__ = "0.1.0"
__author__ = "Oscar Valenzuela B."

from swhpi.core.config import SWHPIConfig

__all__ = ["SWHPIConfig"]