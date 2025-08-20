"""Unit tests for search strategies."""

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
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
    
    @pytest.mark.asyncio
    async def test_identifier_initialization(self):
        """Test identifier is properly initialized."""
        identifier = SourceIdentifier(verbose=False)
        assert identifier.swh_client is None  # Lazy initialization
        assert identifier.search_registry is not None
        assert identifier.hash_searcher is not None
        assert identifier.verbose is False
    
    @pytest.mark.asyncio
    async def test_identify_with_hash_search(self, identifier):
        """Test identification using hash search strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "test.py").write_text("print('hello')")
            
            # Mock hash search results
            with patch.object(identifier, '_identify_via_hash_search', new_callable=AsyncMock) as mock_hash:
                mock_hash.return_value = [{
                    "source": "hash_search",
                    "origin": "https://github.com/test/repo",
                    "confidence": 0.8
                }]
                
                result = await identifier.identify(
                    path=path,
                    strategies=["hash_search"]
                )
                
                assert result["identified"] is True
                assert result["confidence"] == 0.8
                assert "hash_search" in result["strategies_used"]
                assert result["final_origin"] == "https://github.com/test/repo"
    
    @pytest.mark.asyncio
    async def test_identify_with_web_search(self, identifier):
        """Test identification using web search strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Mock web search results
            with patch.object(identifier, '_identify_via_web_search', new_callable=AsyncMock) as mock_web:
                mock_web.return_value = [{
                    "source": "web_search_github",
                    "origin": "https://github.com/example/project",
                    "confidence": 0.6
                }]
                
                result = await identifier.identify(
                    path=path,
                    strategies=["web_search"]
                )
                
                assert result["identified"] is True
                assert result["confidence"] == 0.6
                assert "web_search" in result["strategies_used"]
    
    @pytest.mark.asyncio
    async def test_identify_with_scanoss(self, identifier):
        """Test identification using SCANOSS strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "code.c").write_text("#include <stdio.h>\nint main() { return 0; }")
            
            # Mock SCANOSS results
            with patch.object(identifier, '_identify_via_scanoss', new_callable=AsyncMock) as mock_scanoss:
                mock_scanoss.return_value = [{
                    "source": "scanoss",
                    "origin": "https://github.com/torvalds/linux",
                    "confidence": 0.95
                }]
                
                result = await identifier.identify(
                    path=path,
                    strategies=["scanoss"]
                )
                
                assert result["identified"] is True
                assert result["confidence"] == 0.95
                assert "scanoss" in result["strategies_used"]
    
    @pytest.mark.asyncio
    async def test_identify_with_swh_lazy_init(self, identifier):
        """Test that SWH client is lazily initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Initially no SWH client
            assert identifier.swh_client is None
            
            # Mock SWH results
            with patch.object(identifier, '_identify_via_swh', new_callable=AsyncMock) as mock_swh:
                mock_swh.return_value = []
                
                await identifier.identify(
                    path=path,
                    strategies=["swh"],
                    use_swh=True
                )
                
                # SWH method should be called
                assert mock_swh.called
    
    @pytest.mark.asyncio
    async def test_identify_multiple_strategies(self, identifier):
        """Test identification with multiple strategies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Mock all strategies
            with patch.object(identifier, '_identify_via_hash_search', new_callable=AsyncMock) as mock_hash:
                with patch.object(identifier, '_identify_via_web_search', new_callable=AsyncMock) as mock_web:
                    mock_hash.return_value = []  # No results
                    mock_web.return_value = [{
                        "source": "web_search",
                        "origin": "https://github.com/found/repo",
                        "confidence": 0.7
                    }]
                    
                    result = await identifier.identify(
                        path=path,
                        strategies=["hash_search", "web_search"]
                    )
                    
                    # Both strategies should be tried
                    assert "hash_search" in result["strategies_used"]
                    assert "web_search" in result["strategies_used"]
                    assert result["identified"] is True
    
    @pytest.mark.asyncio
    async def test_identify_no_results(self, identifier):
        """Test identification when no results found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Mock strategies with no results
            with patch.object(identifier, '_identify_via_hash_search', new_callable=AsyncMock) as mock_hash:
                with patch.object(identifier, '_identify_via_web_search', new_callable=AsyncMock) as mock_web:
                    mock_hash.return_value = []
                    mock_web.return_value = []
                    
                    result = await identifier.identify(
                        path=path,
                        strategies=["hash_search", "web_search"]
                    )
                    
                    assert result["identified"] is False
                    assert result["confidence"] == 0.0
                    assert result["final_origin"] is None
    
    @pytest.mark.asyncio
    async def test_identify_confidence_threshold(self, identifier):
        """Test confidence threshold filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Mock low confidence results
            with patch.object(identifier, '_identify_via_web_search', new_callable=AsyncMock) as mock_web:
                mock_web.return_value = [{
                    "source": "web_search",
                    "origin": "https://github.com/maybe/repo",
                    "confidence": 0.2  # Below threshold
                }]
                
                result = await identifier.identify(
                    path=path,
                    strategies=["web_search"],
                    confidence_threshold=0.5
                )
                
                # Should not be identified due to low confidence
                assert result["identified"] is False
    
    @pytest.mark.asyncio
    async def test_identify_default_strategies(self, identifier):
        """Test default strategy order without SWH."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Track which strategies are called
            called_strategies = []
            
            async def track_hash(*args, **kwargs):
                called_strategies.append("hash_search")
                return []
            
            async def track_web(*args, **kwargs):
                called_strategies.append("web_search")
                return []
            
            async def track_scanoss(*args, **kwargs):
                called_strategies.append("scanoss")
                return []
            
            with patch.object(identifier, '_identify_via_hash_search', new_callable=AsyncMock) as mock_hash:
                with patch.object(identifier, '_identify_via_web_search', new_callable=AsyncMock) as mock_web:
                    with patch.object(identifier, '_identify_via_scanoss', new_callable=AsyncMock) as mock_scanoss:
                        mock_hash.side_effect = track_hash
                        mock_web.side_effect = track_web
                        mock_scanoss.side_effect = track_scanoss
                        
                        await identifier.identify(path=path, use_swh=False)
                        
                        # Should use default order
                        assert called_strategies == ["hash_search", "web_search", "scanoss"]
    
    @pytest.mark.asyncio
    async def test_identify_with_swh_enabled(self, identifier):
        """Test that SWH is included when use_swh=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            called_strategies = []
            
            async def track_strategy(name):
                async def inner(*args, **kwargs):
                    called_strategies.append(name)
                    return []
                return inner
            
            with patch.object(identifier, '_identify_via_hash_search', new_callable=AsyncMock) as mock_hash:
                with patch.object(identifier, '_identify_via_web_search', new_callable=AsyncMock) as mock_web:
                    with patch.object(identifier, '_identify_via_scanoss', new_callable=AsyncMock) as mock_scanoss:
                        with patch.object(identifier, '_identify_via_swh', new_callable=AsyncMock) as mock_swh:
                            mock_hash.side_effect = await track_strategy("hash_search")
                            mock_web.side_effect = await track_strategy("web_search")
                            mock_scanoss.side_effect = await track_strategy("scanoss")
                            mock_swh.side_effect = await track_strategy("swh")
                            
                            await identifier.identify(path=path, use_swh=True)
                            
                            # SWH should be included
                            assert "swh" in called_strategies