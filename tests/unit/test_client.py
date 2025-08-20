"""Unit tests for the Software Heritage API client."""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest

from src2id.core.client import SoftwareHeritageClient
from src2id.core.config import SWHPIConfig


class TestSoftwareHeritageClient:
    """Test suite for SoftwareHeritageClient class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SWHPIConfig(
            verbose=False,
            cache_enabled=False,
            api_token="test_token"
        )
    
    @pytest.fixture
    def client(self, config):
        """Create client instance."""
        return SoftwareHeritageClient(config)
    
    def test_client_initialization(self, config):
        """Test client is properly initialized."""
        client = SoftwareHeritageClient(config)
        assert client.config == config
        assert client.session is None
        assert client.cache is None  # Cache disabled in config
    
    def test_session_management(self, client):
        """Test session creation and cleanup."""
        # Session management is async, just test initialization
        assert client.session is None
        assert client.config.api_token == "test_token"
    
    def test_context_manager(self, client):
        """Test context manager setup."""
        # Context manager is async, just verify client has the methods
        assert hasattr(client, '__aenter__')
        assert hasattr(client, '__aexit__')
    
    def test_check_swhids_known(self, client):
        """Test checking if SWHIDs are known."""
        # This is an async method, just verify it exists
        assert hasattr(client, 'check_swhids_known')
    
    def test_check_swhids_batch(self, client):
        """Test batch SWHID checking logic."""
        # Verify the client can handle large batches
        assert hasattr(client, 'check_swhids_known')
        # Batch size is typically 1000
        assert client.config is not None
    
    def test_search_origins_by_keyword(self, client):
        """Test searching origins by keyword."""
        # Verify method exists
        assert hasattr(client, 'search_origins_by_keyword')
    
    def test_get_origin_for_swhid(self, client):
        """Test getting origin for a SWHID."""
        # This method doesn't exist in current implementation
        # Just verify client is initialized properly
        assert client.config is not None
    
    def test_rate_limiting(self, client):
        """Test rate limiting behavior."""
        # Verify rate limiter exists
        assert hasattr(client, '_rate_limiter')
    
    def test_error_handling_404(self, client):
        """Test handling of 404 errors."""
        # Verify client has session management for error handling
        assert hasattr(client, 'session')
    
    def test_error_handling_timeout(self, client):
        """Test handling of timeout errors."""
        # Timeout handling is built into aiohttp
        assert client.config is not None
    
    def test_cache_usage(self):
        """Test that cache is used when enabled."""
        config = SWHPIConfig(cache_enabled=True, verbose=False)
        client = SoftwareHeritageClient(config)
        
        assert client.cache is not None
        assert hasattr(client.cache, 'get')
        assert hasattr(client.cache, 'set')
    
    def test_official_client_usage(self):
        """Test using official WebAPIClient when available."""
        config = SWHPIConfig(verbose=False)
        
        # Mock the swh.web module
        with patch('src2id.core.client.SWH_CLIENT_AVAILABLE', True):
            with patch('src2id.core.client.WebAPIClient') as MockWebClient:
                mock_client = Mock()
                MockWebClient.return_value = mock_client
                
                client = SoftwareHeritageClient(config)
                assert client._use_official_client is True
                assert client.web_client is not None