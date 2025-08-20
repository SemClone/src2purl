"""Unit tests for the Software Heritage API client."""

import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
import aiohttp

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
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, config):
        """Test client is properly initialized."""
        client = SoftwareHeritageClient(config)
        assert client.config == config
        assert client.session is None
        assert client.cache is None  # Cache disabled in config
    
    @pytest.mark.asyncio
    async def test_session_management(self, client):
        """Test session creation and cleanup."""
        # Start session
        await client.start_session()
        assert client.session is not None
        assert isinstance(client.session, aiohttp.ClientSession)
        
        # Check headers include token
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test_token"
        
        # Close session
        await client.close_session()
        assert client.session is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client:
            assert client.session is not None
        assert client.session is None
    
    @pytest.mark.asyncio
    async def test_check_swhids_known(self, client):
        """Test checking if SWHIDs are known."""
        swhids = [
            "swh:1:cnt:abc123",
            "swh:1:dir:def456"
        ]
        
        mock_response = {
            "swh:1:cnt:abc123": {"known": True},
            "swh:1:dir:def456": {"known": False}
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                result = await client.check_swhids_known(swhids)
            
            assert result["swh:1:cnt:abc123"] is True
            assert result["swh:1:dir:def456"] is False
    
    @pytest.mark.asyncio
    async def test_check_swhids_batch(self, client):
        """Test batch SWHID checking."""
        # Create more than 1000 SWHIDs to test batching
        swhids = [f"swh:1:cnt:{'a' * 40}{i:04d}" for i in range(1500)]
        
        call_count = 0
        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Return all as known
            return {swhid: {"known": True} for swhid in kwargs.get('json', [])}
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock:
            mock.side_effect = mock_request
            
            async with client:
                result = await client.check_swhids_known(swhids)
            
            # Should make 2 calls (1000 + 500)
            assert call_count == 2
            assert len(result) == 1500
    
    @pytest.mark.asyncio
    async def test_search_origins_by_keyword(self, client):
        """Test searching origins by keyword."""
        keyword = "numpy"
        
        mock_response = [
            {
                "url": "https://github.com/numpy/numpy",
                "visit_types": ["git"]
            }
        ]
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                result = await client.search_origins_by_keyword(keyword)
            
            assert len(result) == 1
            assert result[0]["url"] == "https://github.com/numpy/numpy"
    
    @pytest.mark.asyncio
    async def test_get_origin_for_swhid(self, client):
        """Test getting origin for a SWHID."""
        swhid = "swh:1:dir:abc123"
        
        # Mock the graph query response
        mock_response = {
            "results": [
                {
                    "origin": "https://github.com/test/repo"
                }
            ]
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                result = await client.get_origin_for_swhid(swhid)
            
            assert result == "https://github.com/test/repo"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test rate limiting behavior."""
        # Create multiple concurrent requests
        swhids = [f"swh:1:cnt:{'a' * 40}{i:04d}" for i in range(10)]
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}
            
            async with client:
                # Should respect rate limiter (max 5 concurrent)
                tasks = [client.check_swhids_known([swhid]) for swhid in swhids]
                await asyncio.gather(*tasks)
            
            # Check that requests were made
            assert mock_request.call_count > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_404(self, client):
        """Test handling of 404 errors."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = aiohttp.ClientResponseError(
                request_info=Mock(),
                history=(),
                status=404
            )
            
            async with client:
                result = await client.get_origin_for_swhid("swh:1:dir:notfound")
            
            # Should return None for 404
            assert result is None
    
    @pytest.mark.asyncio
    async def test_error_handling_timeout(self, client):
        """Test handling of timeout errors."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = asyncio.TimeoutError()
            
            async with client:
                with pytest.raises(asyncio.TimeoutError):
                    await client.check_swhids_known(["swh:1:cnt:abc123"])
    
    @pytest.mark.asyncio
    async def test_cache_usage(self):
        """Test that cache is used when enabled."""
        config = SWHPIConfig(cache_enabled=True, verbose=False)
        client = SoftwareHeritageClient(config)
        
        assert client.cache is not None
        
        # Mock cache get/set
        with patch.object(client.cache, 'get') as mock_get:
            with patch.object(client.cache, 'set') as mock_set:
                mock_get.return_value = None  # Cache miss
                
                with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
                    mock_request.return_value = {"swh:1:cnt:abc123": {"known": True}}
                    
                    async with client:
                        await client.check_swhids_known(["swh:1:cnt:abc123"])
                    
                    # Should check cache and set result
                    assert mock_get.called
                    assert mock_set.called
    
    @pytest.mark.asyncio
    async def test_official_client_usage(self):
        """Test using official WebAPIClient when available."""
        config = SWHPIConfig(verbose=False)
        
        # Mock the swh.web module
        with patch('src2id.core.client.SWH_WEB_AVAILABLE', True):
            with patch('src2id.core.client.WebAPIClient') as MockWebClient:
                mock_client = Mock()
                MockWebClient.return_value = mock_client
                
                client = SoftwareHeritageClient(config)
                assert client._use_official_client is True
                assert client.web_client is not None