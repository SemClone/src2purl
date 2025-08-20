"""Data models for SHPI."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class MatchType(str, Enum):
    """Type of match found in Software Heritage."""
    EXACT = "exact"
    FUZZY = "fuzzy"


@dataclass
class PackageMatch:
    """Represents a package match found in Software Heritage."""
    
    download_url: str
    match_type: MatchType
    confidence_score: float
    name: Optional[str] = None
    version: Optional[str] = None
    license: Optional[str] = None
    sh_url: Optional[str] = None
    frequency_count: int = 0
    is_official_org: bool = False
    purl: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "download_url": self.download_url,
            "name": self.name,
            "version": self.version,
            "license": self.license,
            "sh_url": self.sh_url,
            "match_type": self.match_type.value,
            "confidence_score": self.confidence_score,
            "frequency_count": self.frequency_count,
            "is_official_org": self.is_official_org,
            "purl": self.purl,
        }


@dataclass
class DirectoryCandidate:
    """Represents a directory candidate for SWHID matching."""
    
    path: Path
    swhid: str
    depth: int
    specificity_score: float
    file_count: int


@dataclass
class ContentCandidate:
    """Represents a file/content candidate for SWHID matching."""
    
    path: Path
    swhid: str
    depth: int
    size: int


@dataclass
class SHOriginMatch:
    """Represents an origin match from Software Heritage."""
    
    origin_url: str
    swhid: str
    last_seen: datetime
    match_type: MatchType = MatchType.EXACT
    visit_count: int = 1
    metadata: Dict[str, Any] = None
    similarity_score: float = 1.0
    
    def __post_init__(self):
        """Initialize default metadata if None."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SHAPIResponse:
    """Wrapper for Software Heritage API responses."""
    
    data: Any
    headers: Dict[str, str]
    status: int
    cached: bool = False