"""Tests for configuration management."""

import pytest
from swhpi.core.config import SWHPIConfig


def test_default_config():
    """Test default configuration values."""
    config = SWHPIConfig()
    
    assert config.max_depth == 5
    assert config.min_files == 3
    assert config.purl_generation_threshold == 0.85
    assert config.report_match_threshold == 0.65
    assert config.fuzzy_consideration_threshold == 0.5
    assert config.cache_enabled is True
    assert config.output_format == "table"


def test_custom_config():
    """Test custom configuration values."""
    config = SWHPIConfig(
        max_depth=10,
        cache_enabled=False,
        verbose=True
    )
    
    assert config.max_depth == 10
    assert config.cache_enabled is False
    assert config.verbose is True


def test_score_weights():
    """Test score weights configuration."""
    config = SWHPIConfig()
    
    assert 'recency' in config.score_weights
    assert 'popularity' in config.score_weights
    assert 'authority' in config.score_weights
    assert 'specificity' in config.score_weights
    
    # Verify weights sum to 1.0
    total_weight = sum(config.score_weights.values())
    assert abs(total_weight - 1.0) < 0.001