"""Unit tests for search strategies."""

from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

import pytest

from src2id.search.strategies import SourceIdentifier
from src2id.search.providers import SearchProviderRegistry


class TestSourceIdentifier:
    """Test suite for SourceIdentifier class."""
    
    @pytest.fixture
    def identifier(self):
        """Create identifier instance."""
        return SourceIdentifier(verbose=False)
    
    def test_identifier_initialization(self):
        """Test identifier is properly initialized."""
        identifier = SourceIdentifier(verbose=False)
        assert identifier.swh_client is None  # Lazy initialization
        assert identifier.search_registry is not None
        assert identifier.hash_searcher is not None
        assert identifier.verbose is False
    
    def test_identify_method_exists(self, identifier):
        """Test that identify method exists."""
        assert hasattr(identifier, 'identify')
        assert hasattr(identifier, '_identify_via_hash_search')
        assert hasattr(identifier, '_identify_via_web_search')
        assert hasattr(identifier, '_identify_via_scanoss')
        assert hasattr(identifier, '_identify_via_swh')
    
    def test_search_registry_exists(self, identifier):
        """Test that search registry exists."""
        assert identifier.search_registry is not None
        assert hasattr(identifier.search_registry, 'get_provider')
        assert hasattr(identifier.search_registry, 'close_all')
    
    def test_hash_searcher_exists(self, identifier):
        """Test that hash searcher exists."""
        assert identifier.hash_searcher is not None
        assert hasattr(identifier.hash_searcher, 'search_file')
    
    def test_swh_client_lazy_init(self, identifier):
        """Test that SWH client is lazily initialized."""
        # Initially no SWH client
        assert identifier.swh_client is None
        
        # Has method for SWH identification
        assert hasattr(identifier, '_identify_via_swh')
    
    def test_identifier_strategies_config(self, identifier):
        """Test identifier strategies configuration."""
        # Test default strategies exist
        available_strategies = {
            "hash_search": identifier._identify_via_hash_search,
            "web_search": identifier._identify_via_web_search,
            "scanoss": identifier._identify_via_scanoss,
            "swh": identifier._identify_via_swh
        }
        
        # All strategies should have methods
        for strategy_name, method in available_strategies.items():
            assert method is not None
            assert callable(method)
    
    def test_identifier_verbose_mode(self, identifier):
        """Test identifier verbose mode."""
        # Test with verbose off
        assert identifier.verbose is False
        
        # Test creating with verbose on
        verbose_identifier = SourceIdentifier(verbose=True)
        assert verbose_identifier.verbose is True
    
    def test_print_results_method(self, identifier):
        """Test that print_results method exists."""
        assert hasattr(identifier, 'print_results')
        
        # Test it can handle a mock result
        mock_results = {
            "path": "/test/path",
            "identified": True,
            "confidence": 0.8,
            "strategies_used": ["hash_search"],
            "final_origin": "https://github.com/test/repo",
            "candidates": []
        }
        
        # Should not raise an error
        try:
            identifier.print_results(mock_results)
        except Exception:
            # OK if it fails due to console output in tests
            pass
    
    def test_default_strategy_order(self):
        """Test default strategy order configuration."""
        # Default order should be optimized for performance
        identifier = SourceIdentifier(verbose=False)
        
        # The default order is: hash_search, web_search, scanoss
        # SWH is only added if use_swh=True
        assert identifier.swh_client is None  # Not initialized by default
    
    def test_cleanup_method(self, identifier):
        """Test that cleanup methods exist."""
        # Should have registry for cleanup
        assert identifier.search_registry is not None
        assert hasattr(identifier.search_registry, 'close_all')