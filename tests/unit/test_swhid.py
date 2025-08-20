"""Tests for SWHID generation."""

import pytest
import tempfile
import os
from pathlib import Path

from src2id.core.swhid import SWHIDGenerator


class TestSWHIDGenerator:
    """Test SWHID generation functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create a SWHID generator instance."""
        # Use fallback implementation for testing
        return SWHIDGenerator(use_swh_model=False)
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Create some test files
            (path / "file1.txt").write_text("Hello World")
            (path / "file2.py").write_text("print('test')")
            
            # Create a subdirectory
            subdir = path / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("Nested content")
            
            yield path
    
    def test_generate_directory_swhid(self, generator, temp_dir):
        """Test generating SWHID for a directory."""
        swhid = generator.generate_directory_swhid(temp_dir)
        
        assert swhid.startswith("swh:1:dir:")
        parts = swhid.split(":")
        assert len(parts) == 4
        assert len(parts[3]) == 40  # SHA1 hash length
    
    def test_generate_content_swhid(self, generator, temp_dir):
        """Test generating SWHID for file content."""
        file_path = temp_dir / "file1.txt"
        swhid = generator.generate_content_swhid(file_path)
        
        assert swhid.startswith("swh:1:cnt:")
        parts = swhid.split(":")
        assert len(parts) == 4
        assert len(parts[3]) == 40  # SHA1 hash length
    
    def test_consistent_directory_hash(self, generator, temp_dir):
        """Test that directory hash is consistent."""
        swhid1 = generator.generate_directory_swhid(temp_dir)
        swhid2 = generator.generate_directory_swhid(temp_dir)
        
        assert swhid1 == swhid2
    
    def test_consistent_content_hash(self, generator, temp_dir):
        """Test that content hash is consistent."""
        file_path = temp_dir / "file1.txt"
        swhid1 = generator.generate_content_swhid(file_path)
        swhid2 = generator.generate_content_swhid(file_path)
        
        assert swhid1 == swhid2
    
    def test_different_content_different_hash(self, generator, temp_dir):
        """Test that different content produces different hashes."""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.py"
        
        swhid1 = generator.generate_content_swhid(file1)
        swhid2 = generator.generate_content_swhid(file2)
        
        assert swhid1 != swhid2
    
    def test_validate_swhid_valid(self, generator):
        """Test validating correct SWHID format."""
        valid_swhids = [
            "swh:1:dir:0000000000000000000000000000000000000000",
            "swh:1:cnt:abcdef1234567890abcdef1234567890abcdef12",
            "swh:1:rev:1234567890abcdef1234567890abcdef12345678",
        ]
        
        for swhid in valid_swhids:
            assert generator.validate_swhid(swhid) is True
    
    def test_validate_swhid_invalid(self, generator):
        """Test validating incorrect SWHID format."""
        invalid_swhids = [
            "not:a:swhid",
            "swh:2:dir:abc",  # Wrong version
            "swh:1:xyz:abc",  # Invalid type
            "swh:1:dir:xyz",  # Invalid hash (not hex)
            "swh:1:dir:abc",  # Too short hash
            "swh:1:dir",  # Missing hash
            "",  # Empty string
            None,  # None
        ]
        
        for swhid in invalid_swhids:
            assert generator.validate_swhid(swhid) is False
    
    def test_error_on_non_directory(self, generator, temp_dir):
        """Test error when path is not a directory."""
        file_path = temp_dir / "file1.txt"
        
        with pytest.raises(ValueError, match="is not a directory"):
            generator.generate_directory_swhid(file_path)
    
    def test_error_on_non_file(self, generator, temp_dir):
        """Test error when path is not a file."""
        with pytest.raises(ValueError, match="is not a file"):
            generator.generate_content_swhid(temp_dir)
    
    def test_hidden_files_ignored(self, generator, temp_dir):
        """Test that hidden files are ignored in directory hash."""
        # Get initial hash
        swhid1 = generator.generate_directory_swhid(temp_dir)
        
        # Add a hidden file
        (temp_dir / ".hidden").write_text("Hidden content")
        
        # Hash should be the same (hidden file ignored)
        swhid2 = generator.generate_directory_swhid(temp_dir)
        
        assert swhid1 == swhid2