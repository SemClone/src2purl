"""Tests for data models."""

import pytest
from datetime import datetime
from pathlib import Path

from src2id.core.models import (
    MatchType,
    DirectoryCandidate,
    SHOriginMatch,
    PackageMatch,
    SHAPIResponse
)


class TestMatchType:
    """Test MatchType enum."""
    
    def test_match_type_values(self):
        """Test enum values."""
        assert MatchType.EXACT.value == "exact"
        assert MatchType.FUZZY.value == "fuzzy"
    
    def test_match_type_comparison(self):
        """Test enum comparison."""
        assert MatchType.EXACT != MatchType.FUZZY


class TestDirectoryCandidate:
    """Test DirectoryCandidate model."""
    
    def test_create_directory_candidate(self):
        """Test creating a directory candidate."""
        path = Path("/test/path")
        candidate = DirectoryCandidate(
            path=path,
            swhid="swh:1:dir:abc123",
            depth=1,
            specificity_score=0.8,
            file_count=10
        )
        
        assert candidate.path == path
        assert candidate.swhid == "swh:1:dir:abc123"
        assert candidate.depth == 1
        assert candidate.specificity_score == 0.8
        assert candidate.file_count == 10


class TestSHOriginMatch:
    """Test SHOriginMatch model."""
    
    def test_create_origin_match(self):
        """Test creating an origin match."""
        now = datetime.now()
        match = SHOriginMatch(
            origin_url="https://github.com/test/repo",
            swhid="swh:1:dir:abc123",
            last_seen=now,
            visit_count=5,
            metadata={"key": "value"},
            match_type=MatchType.EXACT
        )
        
        assert match.origin_url == "https://github.com/test/repo"
        assert match.swhid == "swh:1:dir:abc123"
        assert match.last_seen == now
        assert match.visit_count == 5
        assert match.metadata == {"key": "value"}
        assert match.match_type == MatchType.EXACT
    
    def test_optional_fields(self):
        """Test optional fields have defaults."""
        match = SHOriginMatch(
            origin_url="https://example.com",
            swhid="swh:1:dir:xyz",
            last_seen=datetime.now(),
            match_type=MatchType.FUZZY
        )
        
        assert match.visit_count == 1
        assert match.metadata == {}


class TestPackageMatch:
    """Test PackageMatch model."""
    
    def test_create_package_match(self):
        """Test creating a package match."""
        match = PackageMatch(
            download_url="https://github.com/test/repo",
            name="test-package",
            version="1.0.0",
            license="MIT",
            sh_url="https://archive.softwareheritage.org/...",
            match_type=MatchType.EXACT,
            confidence_score=0.95,
            frequency_count=10,
            is_official_org=True,
            purl="pkg:github/test/repo@1.0.0"
        )
        
        assert match.name == "test-package"
        assert match.version == "1.0.0"
        assert match.license == "MIT"
        assert match.confidence_score == 0.95
        assert match.is_official_org is True
        assert match.purl == "pkg:github/test/repo@1.0.0"
    
    def test_optional_package_fields(self):
        """Test optional fields in PackageMatch."""
        match = PackageMatch(
            download_url="https://example.com",
            match_type=MatchType.FUZZY,
            confidence_score=0.5
        )
        
        assert match.name is None
        assert match.version is None
        assert match.license is None
        assert match.sh_url is None
        assert match.frequency_count == 0
        assert match.is_official_org is False
        assert match.purl is None


class TestSHAPIResponse:
    """Test SHAPIResponse model."""
    
    def test_create_api_response(self):
        """Test creating an API response."""
        data = {"test": "data"}
        headers = {"Content-Type": "application/json"}
        
        response = SHAPIResponse(
            data=data,
            headers=headers,
            status=200,
            cached=False
        )
        
        assert response.data == data
        assert response.headers == headers
        assert response.status == 200
        assert response.cached is False
    
    def test_cached_response(self):
        """Test cached response."""
        response = SHAPIResponse(
            data=[],
            headers={},
            status=404,
            cached=True
        )
        
        assert response.status == 404
        assert response.cached is True
        assert response.data == []