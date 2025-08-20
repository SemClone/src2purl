"""Tests for PURL generation."""

import pytest

from src2id.core.purl import PURLGenerator


class TestPURLGenerator:
    """Test PURL generation functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create a PURL generator instance."""
        return PURLGenerator()
    
    def test_github_purl_with_version(self, generator):
        """Test generating GitHub PURL with version."""
        coordinates = {
            'name': 'test-repo',
            'version': 'v1.0.0',
            'download_url': 'https://github.com/owner/test-repo'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl == "pkg:github/owner/test-repo@1.0.0"  # 'v' prefix removed
    
    def test_github_purl_without_version(self, generator):
        """Test generating GitHub PURL without version."""
        coordinates = {
            'name': 'test-repo',
            'download_url': 'https://github.com/owner/test-repo'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl == "pkg:github/owner/test-repo"
    
    def test_low_confidence_no_purl(self, generator):
        """Test that low confidence doesn't generate PURL."""
        coordinates = {
            'name': 'test-repo',
            'download_url': 'https://github.com/owner/test-repo'
        }
        
        purl = generator.generate_purl(coordinates, 0.5)  # Below 0.85 threshold
        assert purl is None
    
    def test_pypi_purl(self, generator):
        """Test generating PyPI PURL."""
        coordinates = {
            'name': 'Test_Package',
            'version': '2.0.0',
            'download_url': 'https://pypi.org/project/test-package/'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl == "pkg:pypi/test-package@2.0.0"  # Normalized to lowercase with hyphens
    
    def test_npm_purl_simple(self, generator):
        """Test generating npm PURL for simple package."""
        coordinates = {
            'name': 'express',
            'version': '4.18.0',
            'download_url': 'https://npmjs.org/package/express'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl == "pkg:npm/express@4.18.0"
    
    def test_npm_purl_scoped(self, generator):
        """Test generating npm PURL for scoped package."""
        coordinates = {
            'name': '@angular/core',
            'version': '15.0.0',
            'download_url': 'https://npmjs.org/package/@angular/core'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl == "pkg:npm/angular/core@15.0.0"
    
    def test_cargo_purl(self, generator):
        """Test generating Cargo (Rust) PURL."""
        coordinates = {
            'name': 'serde',
            'version': '1.0.0',
            'download_url': 'https://crates.io/crates/serde'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl == "pkg:cargo/serde@1.0.0"
    
    def test_invalid_url_no_purl(self, generator):
        """Test that invalid URLs don't generate PURLs."""
        invalid_urls = [
            'https://github.com/owner/repo/pull/123',  # Pull request
            'https://github.com/owner/repo/issues/456',  # Issue
            'https://github.com/owner/repo/wiki/Page',  # Wiki
            'not-a-url',  # Invalid URL
            '',  # Empty URL
        ]
        
        for url in invalid_urls:
            coordinates = {
                'name': 'test',
                'download_url': url
            }
            purl = generator.generate_purl(coordinates, 0.9)
            assert purl is None
    
    def test_missing_required_fields(self, generator):
        """Test handling of missing required fields."""
        # Missing name
        coordinates = {
            'download_url': 'https://github.com/owner/repo'
        }
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl is None
        
        # Missing download_url
        coordinates = {
            'name': 'test'
        }
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl is None
    
    def test_gitlab_purl(self, generator):
        """Test generating GitLab PURL."""
        coordinates = {
            'name': 'test-project',
            'version': '3.0.0',
            'download_url': 'https://gitlab.com/group/test-project'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl == "pkg:gitlab/group/test-project@3.0.0"
    
    def test_unknown_source_no_purl(self, generator):
        """Test that unknown sources don't generate PURLs."""
        coordinates = {
            'name': 'test',
            'download_url': 'https://unknown-site.com/test'
        }
        
        purl = generator.generate_purl(coordinates, 0.9)
        assert purl is None