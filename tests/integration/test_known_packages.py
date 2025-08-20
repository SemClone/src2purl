"""Integration tests with known packages."""

import asyncio
import tempfile
from pathlib import Path
import shutil
import subprocess

import pytest

from src2id.search import identify_source
from src2id.cli.main import main as cli_main


class TestKnownPackages:
    """Integration tests using real packages with known coordinates."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Get test data directory."""
        return Path("test_data")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_darktable_identification(self, test_data_dir):
        """Test identification of darktable package."""
        darktable_path = test_data_dir / "darktable"
        
        if not darktable_path.exists():
            pytest.skip("Darktable test data not found")
        
        # Run identification
        result = await identify_source(
            path=darktable_path,
            max_depth=2,
            confidence_threshold=0.3,
            verbose=False,
            use_swh=False
        )
        
        # Should identify something
        assert result["identified"] is True
        assert result["confidence"] > 0.3
        assert len(result["strategies_used"]) > 0
        
        # Should find darktable or related project
        if result["final_origin"]:
            origin = result["final_origin"].lower()
            # Could match darktable or related projects
            assert "github.com" in origin or "gitlab" in origin
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_scanoss_py_identification(self, test_data_dir):
        """Test identification of scanoss_py package."""
        scanoss_path = test_data_dir / "scanoss_py"
        
        if not scanoss_path.exists():
            pytest.skip("SCANOSS test data not found")
        
        # Run identification
        result = await identify_source(
            path=scanoss_path,
            max_depth=2,
            confidence_threshold=0.3,
            verbose=False,
            use_swh=False
        )
        
        # Should identify with reasonable confidence
        if result["identified"]:
            assert result["confidence"] > 0.3
            assert "scanoss" in result["final_origin"].lower() or result["confidence"] > 0.5
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_small_python_package(self):
        """Test with a small Python package structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_path = Path(tmpdir) / "test_package"
            pkg_path.mkdir()
            
            # Create minimal Python package
            (pkg_path / "setup.py").write_text("""
from setuptools import setup

setup(
    name="test-package",
    version="1.0.0",
    author="Test Author",
    packages=["test_package"]
)
""")
            
            (pkg_path / "README.md").write_text("# Test Package\n\nA test package.")
            
            src_dir = pkg_path / "test_package"
            src_dir.mkdir()
            (src_dir / "__init__.py").write_text('__version__ = "1.0.0"')
            (src_dir / "main.py").write_text("""
def hello():
    return "Hello, World!"

if __name__ == "__main__":
    print(hello())
""")
            
            # Run identification
            result = await identify_source(
                path=pkg_path,
                max_depth=2,
                confidence_threshold=0.3,
                verbose=False,
                use_swh=False
            )
            
            # Should attempt identification
            assert "strategies_used" in result
            assert len(result["strategies_used"]) > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_javascript_package(self):
        """Test with a JavaScript package structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_path = Path(tmpdir) / "js_package"
            pkg_path.mkdir()
            
            # Create package.json
            (pkg_path / "package.json").write_text("""{
  "name": "test-js-package",
  "version": "1.0.0",
  "description": "Test JavaScript package",
  "main": "index.js",
  "license": "MIT"
}""")
            
            # Create JS files
            (pkg_path / "index.js").write_text("""
module.exports = {
  hello: function() {
    return 'Hello from JS!';
  }
};
""")
            
            # Run identification
            result = await identify_source(
                path=pkg_path,
                max_depth=2,
                confidence_threshold=0.3,
                verbose=False,
                use_swh=False
            )
            
            # Should attempt identification
            assert "strategies_used" in result
            assert len(result["strategies_used"]) > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_with_multiple_strategies(self, test_data_dir):
        """Test that multiple strategies are tried."""
        test_path = test_data_dir / "darktable" / "packaging"
        
        if not test_path.exists():
            pytest.skip("Test data not found")
        
        # Track which strategies were used
        result = await identify_source(
            path=test_path,
            max_depth=1,
            confidence_threshold=0.3,
            verbose=False,
            use_swh=False
        )
        
        # Should try multiple strategies
        assert len(result["strategies_used"]) >= 1
        
        # Common strategies should be attempted
        possible_strategies = {"hash_search", "web_search", "scanoss"}
        used_strategies = set(result["strategies_used"])
        
        # At least one strategy should be used
        assert len(used_strategies.intersection(possible_strategies)) > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cli_integration(self, test_data_dir, monkeypatch, capsys):
        """Test CLI integration with known package."""
        test_path = test_data_dir / "darktable"
        
        if not test_path.exists():
            pytest.skip("Test data not found")
        
        # Run CLI command
        import sys
        test_args = [
            "src2id",
            str(test_path),
            "--max-depth", "1",
            "--confidence-threshold", "0.3",
            "--output-format", "json"
        ]
        
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # Run main function
        try:
            cli_main()
        except SystemExit as e:
            # CLI may exit with 0 on success
            if e.code != 0:
                raise
        
        # Check output
        captured = capsys.readouterr()
        
        # Should have JSON output
        import json
        try:
            output = json.loads(captured.out)
            assert "matches" in output
            assert "count" in output
            assert "threshold" in output
        except json.JSONDecodeError:
            # If not pure JSON, check for expected content
            assert "darktable" in captured.out.lower() or "packaging" in captured.out.lower()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_subcomponent_detection(self):
        """Test subcomponent detection in monorepo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monorepo_path = Path(tmpdir) / "monorepo"
            monorepo_path.mkdir()
            
            # Create root package.json (Lerna-style)
            (monorepo_path / "package.json").write_text("""{
  "name": "monorepo",
  "version": "1.0.0",
  "private": true,
  "workspaces": ["packages/*"]
}""")
            
            # Create packages directory
            packages_dir = monorepo_path / "packages"
            packages_dir.mkdir()
            
            # Create package A
            pkg_a = packages_dir / "package-a"
            pkg_a.mkdir()
            (pkg_a / "package.json").write_text("""{
  "name": "@monorepo/package-a",
  "version": "1.0.0"
}""")
            
            # Create package B
            pkg_b = packages_dir / "package-b"
            pkg_b.mkdir()
            (pkg_b / "package.json").write_text("""{
  "name": "@monorepo/package-b",
  "version": "2.0.0"
}""")
            
            # Test with subcomponent detection
            from src2id.core.subcomponent_detector import SubcomponentDetector
            
            detector = SubcomponentDetector()
            components = detector.detect_components(monorepo_path)
            
            # Should detect multiple components
            assert len(components) >= 2
            
            # Should find the packages
            component_names = [c["name"] for c in components]
            assert "@monorepo/package-a" in component_names or "package-a" in component_names
            assert "@monorepo/package-b" in component_names or "package-b" in component_names
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_confidence_scoring(self, test_data_dir):
        """Test confidence scoring with different thresholds."""
        test_path = test_data_dir / "darktable"
        
        if not test_path.exists():
            pytest.skip("Test data not found")
        
        # Test with low threshold
        result_low = await identify_source(
            path=test_path,
            max_depth=1,
            confidence_threshold=0.1,
            verbose=False,
            use_swh=False
        )
        
        # Test with high threshold
        result_high = await identify_source(
            path=test_path,
            max_depth=1,
            confidence_threshold=0.8,
            verbose=False,
            use_swh=False
        )
        
        # Low threshold might identify more
        if result_low["identified"] and not result_high["identified"]:
            assert result_low["confidence"] < 0.8
        
        # Both should run strategies
        assert len(result_low["strategies_used"]) > 0
        assert len(result_high["strategies_used"]) > 0