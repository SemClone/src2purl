"""Configuration management for SHPI."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SHPIConfig:
    """Configuration for the SH Package Identifier tool."""
    
    # Directory scanning parameters
    max_depth: int = 5  # Maximum parent directory levels to scan
    min_files: int = 3  # Minimum files in directory to consider meaningful
    
    # Confidence thresholds
    purl_generation_threshold: float = 0.85
    report_match_threshold: float = 0.65
    fuzzy_consideration_threshold: float = 0.5
    
    # Scoring weights
    score_weights: Dict[str, float] = field(default_factory=lambda: {
        'recency': 0.3,
        'popularity': 0.2,
        'authority': 0.3,
        'specificity': 0.2
    })
    
    # API configuration
    sh_api_base: str = "https://archive.softwareheritage.org/api/1"
    rate_limit_delay: float = 0.5  # Seconds between API calls
    max_retries: int = 3
    cache_enabled: bool = True
    
    # Output configuration
    output_format: str = "table"  # "table" or "json"
    verbose: bool = False
    
    # Feature flags
    enable_fuzzy_matching: bool = True
    enable_batch_processing: bool = False