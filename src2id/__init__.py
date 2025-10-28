"""
Source to PURL (src2purl)

A tool for identifying package coordinates and PURLs from source code
using multiple strategies including SCANOSS, hash search, web search, and
optionally Software Heritage archive.
"""

__version__ = "1.3.3"
__author__ = "Oscar Valenzuela B."

from src2id.core.config import SWHPIConfig

# Keep SWHPIConfig name for backward compatibility, but it's really Src2IdConfig now
__all__ = ["SWHPIConfig"]