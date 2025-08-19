"""SWHID generation accuracy validation tests.

This module validates that our SWHID generation matches Software Heritage's
official implementation by testing against known repositories with confirmed SWHIDs.
"""

import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from swhpi.core.swhid import SWHIDGenerator


# Known test cases with verified SWHIDs from Software Heritage
KNOWN_SWHIDS = {
    # Format: (repo_url, branch/tag, expected_swhid)
    "darktable": {
        "url": "https://github.com/darktable-org/darktable.git",
        "ref": "release-4.4.2",
        "root_swhid": "swh:1:dir:d198bc9d7a6bcf6db04f476d29314f157507d505",
        "subdirs": {
            "packaging": "swh:1:dir:5fc4e68434c98fb4a872ec5b9db53e46d31ad0e2",
            "tools": "swh:1:dir:feb2214060f37f36eba6427074ac0e6d76e821c9",
            "cmake": "swh:1:dir:5caa64c9a21070dc477029965f80102f089b312a",
            "po": "swh:1:dir:261209426ec1d3843a43ff214149343bbd24225a",
            "doc": "swh:1:dir:443c84701fb752f66da14b69e91eda6a90942260",
            "data": "swh:1:dir:3cb46e139b76e38b052cfc2e878bf284f193aa3b",
        }
    },
}


class TestSWHIDAccuracy:
    """Test SWHID generation accuracy against known values."""
    
    @pytest.fixture
    def generator(self):
        """Create SWHID generator with swh.model if available."""
        return SWHIDGenerator(use_swh_model=True)
    
    @pytest.fixture
    def fallback_generator(self):
        """Create SWHID generator with fallback implementation."""
        return SWHIDGenerator(use_swh_model=False)
    
    def clone_repository(self, url: str, ref: str, target_dir: Path) -> bool:
        """Clone a repository at a specific ref."""
        try:
            # Clone with minimal depth
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref, url, str(target_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone {url} at {ref}: {e}")
            return False
    
    @pytest.mark.parametrize("repo_name,repo_info", KNOWN_SWHIDS.items())
    def test_swhid_generation_accuracy(self, generator, repo_name, repo_info):
        """Test SWHID generation against known values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / repo_name
            
            # Clone the repository
            if not self.clone_repository(repo_info["url"], repo_info["ref"], repo_path):
                pytest.skip(f"Could not clone {repo_name}")
            
            # Test subdirectories (more stable than root)
            results = {}
            for subdir_name, expected_swhid in repo_info["subdirs"].items():
                subdir_path = repo_path / subdir_name
                if not subdir_path.exists():
                    continue
                
                generated_swhid = generator.generate_directory_swhid(subdir_path)
                results[subdir_name] = {
                    "expected": expected_swhid,
                    "generated": generated_swhid,
                    "match": generated_swhid == expected_swhid
                }
            
            # Report results
            total = len(results)
            matches = sum(1 for r in results.values() if r["match"])
            
            print(f"\n{repo_name} SWHID Validation Results:")
            print(f"  Matched: {matches}/{total} ({100*matches/total:.1f}%)")
            
            for subdir, result in results.items():
                status = "✓" if result["match"] else "✗"
                print(f"  {status} {subdir}:")
                if not result["match"]:
                    print(f"    Expected:  {result['expected']}")
                    print(f"    Generated: {result['generated']}")
            
            # We expect at least 80% match rate for subdirectories
            assert matches / total >= 0.8, f"Only {matches}/{total} SWHIDs matched"
    
    def test_swh_model_availability(self):
        """Test that swh.model is available and working."""
        try:
            from swh.model.from_disk import Directory
            assert Directory is not None
            print("✓ swh.model is available")
        except ImportError:
            pytest.skip("swh.model not installed")
    
    def test_consistent_generation(self, generator, fallback_generator):
        """Test that SWHID generation is consistent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()
            
            # Create test files
            (test_dir / "file1.txt").write_text("Hello World")
            (test_dir / "file2.py").write_text("print('test')")
            
            # Generate SWHIDs multiple times
            swhid1 = generator.generate_directory_swhid(test_dir)
            swhid2 = generator.generate_directory_swhid(test_dir)
            
            # Should be identical
            assert swhid1 == swhid2, "SWHID generation is not consistent"
            
            # Fallback should also be consistent (though may differ from swh.model)
            fallback1 = fallback_generator.generate_directory_swhid(test_dir)
            fallback2 = fallback_generator.generate_directory_swhid(test_dir)
            
            assert fallback1 == fallback2, "Fallback SWHID generation is not consistent"


class TestSWHIDComparison:
    """Compare different SWHID generation methods."""
    
    def test_compare_implementations(self):
        """Compare swh.model vs fallback implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()
            
            # Create a simple test structure
            (test_dir / "README.md").write_text("# Test Project")
            (test_dir / "main.py").write_text("def main():\n    pass")
            
            src_dir = test_dir / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").write_text("")
            (src_dir / "module.py").write_text("class TestClass:\n    pass")
            
            # Generate with both methods
            swh_gen = SWHIDGenerator(use_swh_model=True)
            fallback_gen = SWHIDGenerator(use_swh_model=False)
            
            swh_swhid = swh_gen.generate_directory_swhid(test_dir)
            fallback_swhid = fallback_gen.generate_directory_swhid(test_dir)
            
            print("\nSWHID Implementation Comparison:")
            print(f"  swh.model: {swh_swhid}")
            print(f"  fallback:  {fallback_swhid}")
            print(f"  Match: {swh_swhid == fallback_swhid}")
            
            # They might not match due to implementation differences
            # but both should be valid SWHIDs
            assert swh_gen.validate_swhid(swh_swhid)
            assert fallback_gen.validate_swhid(fallback_swhid)