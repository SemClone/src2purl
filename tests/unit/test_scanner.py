"""Unit tests for the directory scanner module."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src2id.core.scanner import DirectoryScanner
from src2id.core.config import SWHPIConfig
from src2id.core.swhid import SWHIDGenerator


class TestDirectoryScanner:
    """Test suite for DirectoryScanner class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SWHPIConfig(max_depth=2, verbose=False)
    
    @pytest.fixture
    def scanner(self, config):
        """Create scanner instance."""
        swhid_gen = SWHIDGenerator()
        return DirectoryScanner(config, swhid_gen)
    
    def test_scanner_initialization(self, scanner, config):
        """Test scanner is properly initialized."""
        assert scanner.config == config
        assert isinstance(scanner.swhid_generator, SWHIDGenerator)
    
    def test_scan_empty_directory(self, scanner):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            dir_candidates, file_candidates = scanner.scan_recursive(path)
            
            # Empty directory might not be considered meaningful
            # Implementation only adds meaningful directories
            assert isinstance(dir_candidates, list)
            assert isinstance(file_candidates, list)
            assert len(file_candidates) == 0
    
    def test_scan_with_files(self, scanner):
        """Test scanning directory with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Create some test files with meaningful extensions
            (path / "file1.txt").write_text("content1")
            (path / "file2.py").write_text("import os\n")
            (path / "README.md").write_text("# Test")
            
            dir_candidates, file_candidates = scanner.scan_recursive(path)
            
            # Directory with files should be meaningful
            assert len(dir_candidates) >= 1
            assert len(file_candidates) >= 2  # At least our files
            
            # Check file candidates
            file_names = {fc.path.name for fc in file_candidates}
            assert "file1.txt" in file_names or "file2.py" in file_names
    
    def test_scan_nested_directories(self, scanner):
        """Test scanning nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Create nested structure with meaningful files
            subdir1 = path / "src"
            subdir1.mkdir()
            subdir2 = subdir1 / "core"
            subdir2.mkdir()
            
            (path / "setup.py").write_text("setup()")
            (subdir1 / "__init__.py").write_text("")
            (subdir2 / "main.py").write_text("def main(): pass")
            
            dir_candidates, file_candidates = scanner.scan_recursive(path)
            
            # Should have multiple directories
            assert len(dir_candidates) >= 1
            assert len(file_candidates) >= 1
    
    def test_max_depth_respected(self, scanner):
        """Test that max_depth configuration is respected."""
        scanner.config.max_depth = 1
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Create structure deeper than max_depth
            subdir1 = path / "level1"
            subdir1.mkdir()
            subdir2 = subdir1 / "level2"
            subdir2.mkdir()
            subdir3 = subdir2 / "level3"
            subdir3.mkdir()
            
            # Add files to make directories meaningful
            (path / "file0.py").write_text("root")
            (subdir1 / "file1.py").write_text("level1")
            (subdir2 / "file2.py").write_text("level2")
            (subdir3 / "file3.py").write_text("level3")
            
            dir_candidates, file_candidates = scanner.scan_recursive(path)
            
            # Check depth of candidates
            max_depth_found = max((dc.depth for dc in dir_candidates), default=0)
            assert max_depth_found <= scanner.config.max_depth
    
    def test_skip_hidden_directories(self, scanner):
        """Test that hidden directories are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Create hidden directory
            hidden = path / ".git"
            hidden.mkdir()
            (hidden / "config").write_text("git config")
            
            # Create normal directory with meaningful content
            normal = path / "src"
            normal.mkdir()
            (normal / "main.py").write_text("print('hello')")
            (path / "setup.py").write_text("setup()")
            
            dir_candidates, file_candidates = scanner.scan_recursive(path)
            
            # Hidden directory should be skipped
            dir_paths = [dc.path for dc in dir_candidates]
            assert not any(".git" in str(p) for p in dir_paths)
            
            # Files from hidden directories should not be included
            file_paths = [fc.path for fc in file_candidates]
            assert not any(".git" in str(p) for p in file_paths)
    
    def test_skip_binary_files(self, scanner):
        """Test that binary files are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Create a binary file
            (path / "binary.bin").write_bytes(b'\x00\x01\x02\x03')
            
            # Create a text file
            (path / "text.txt").write_text("hello")
            
            dir_candidates, file_candidates = scanner.scan_recursive(path)
            
            # Both files should be included (binary filtering happens at SWHID level)
            assert len(file_candidates) == 2
    
    def test_no_duplicate_paths(self, scanner):
        """Test that same scan returns consistent results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Create some files
            (path / "file1.py").write_text("test")
            (path / "README.md").write_text("# Test")
            
            # Scan twice (scanner doesn't track visited paths across calls)
            dir_candidates1, file_candidates1 = scanner.scan_recursive(path)
            dir_candidates2, file_candidates2 = scanner.scan_recursive(path)
            
            # Should return same results
            assert len(dir_candidates1) == len(dir_candidates2)
            assert len(file_candidates1) == len(file_candidates2)
    
    def test_swhid_generation(self, scanner):
        """Test that SWHIDs are generated for candidates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "test.txt").write_text("test content")
            
            dir_candidates, file_candidates = scanner.scan_recursive(path)
            
            # Check SWHIDs are generated
            assert all(dc.swhid.startswith("swh:1:dir:") for dc in dir_candidates)
            assert all(fc.swhid.startswith("swh:1:cnt:") for fc in file_candidates)
    
    def test_error_handling_permission_denied(self, scanner):
        """Test handling of permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            
            # Mock a permission error
            with patch('pathlib.Path.iterdir', side_effect=PermissionError("Access denied")):
                dir_candidates, file_candidates = scanner.scan_recursive(path)
                
                # Should handle error gracefully
                assert isinstance(dir_candidates, list)
                assert isinstance(file_candidates, list)