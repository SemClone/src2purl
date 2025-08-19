"""SWHID generation using Software Heritage tools."""

import hashlib
import os
from pathlib import Path
from typing import Optional

# Try different SWHID generation methods in order of preference
HAS_SWH_MODEL = False
HAS_MINISWHID = False

try:
    from swh.model.cli import model_of_dir
    from swh.model.from_disk import Content
    HAS_SWH_MODEL = True
except ImportError:
    try:
        import miniswhid
        HAS_MINISWHID = True
    except ImportError:
        import warnings
        warnings.warn(
            "No accurate SWHID generation available. "
            "Install swh.model or miniswhid for accurate SWHID generation: "
            "pip install swh.model"
        )


class SWHIDGenerator:
    """
    Generates Software Heritage Identifiers using miniswhid or custom implementation.
    """
    
    def __init__(self, use_swh_model: bool = True):
        """
        Initialize the SWHID generator.
        
        Args:
            use_swh_model: Whether to use swh.model if available
        """
        self.use_swh_model = use_swh_model and HAS_SWH_MODEL
        self.use_miniswhid = (not self.use_swh_model) and HAS_MINISWHID
    
    def generate_directory_swhid(self, path: Path) -> str:
        """
        Generate SWHID for directory content.
        
        Args:
            path: Directory path
            
        Returns:
            SWHID string in format swh:1:dir:HASH
        """
        if not path.is_dir():
            raise ValueError(f"Path {path} is not a directory")
        
        if self.use_swh_model:
            return self._generate_with_swh_model(path)
        elif self.use_miniswhid:
            return self._generate_with_miniswhid(path)
        else:
            return self._generate_fallback(path)
    
    def generate_content_swhid(self, file_path: Path) -> str:
        """
        Generate SWHID for individual file content.
        
        Args:
            file_path: File path
            
        Returns:
            SWHID string in format swh:1:cnt:HASH
        """
        if not file_path.is_file():
            raise ValueError(f"Path {file_path} is not a file")
        
        if self.use_swh_model:
            # Use swh.model for file content
            try:
                from swh.model.from_disk import Content
                content = Content.from_file(path=bytes(file_path))
                return f"swh:1:cnt:{content.hash}"
            except Exception as e:
                print(f"Warning: swh.model failed for {file_path}: {e}")
                return self._hash_file_content(file_path)
        elif self.use_miniswhid:
            # Use miniswhid for file content
            try:
                result = miniswhid.compute_swhid(str(file_path))
                if isinstance(result, dict) and 'swhid' in result:
                    return result['swhid']
                return str(result)
            except Exception as e:
                if hasattr(miniswhid, 'hash_file'):
                    # Alternative API
                    return f"swh:1:cnt:{miniswhid.hash_file(str(file_path))}"
                raise e
        else:
            # Fallback implementation
            return self._hash_file_content(file_path)
    
    def _generate_with_swh_model(self, path: Path) -> str:
        """
        Generate SWHID using swh.model library.
        
        Args:
            path: Directory path
            
        Returns:
            SWHID string
        """
        try:
            # Use official exclusion patterns like SWH scanner
            exclusion_patterns = [
                b'.git', b'.hg', b'.svn', b'__pycache__', 
                b'.mypy_cache', b'.tox', b'*.egg-info',
                b'.bzr', b'.coverage', b'.eggs'
            ]
            
            # Use official model_of_dir method (same as SWH scanner)
            source_tree = model_of_dir(
                str(path).encode(),
                exclusion_patterns
            )
            
            # Generate SWHID using official method
            swhid = source_tree.swhid()
            return str(swhid)
            
        except Exception as e:
            print(f"Warning: swh.model failed for {path}: {e}")
            print("Falling back to custom implementation")
            return self._generate_fallback(path)
    
    def _generate_with_miniswhid(self, path: Path) -> str:
        """
        Generate SWHID using miniswhid library.
        
        Args:
            path: Directory path
            
        Returns:
            SWHID string
        """
        try:
            # Try the main API
            result = miniswhid.compute_swhid(str(path))
            
            # Handle different return types from miniswhid
            if isinstance(result, dict):
                if 'swhid' in result:
                    return result['swhid']
                elif 'directory' in result:
                    return f"swh:1:dir:{result['directory']}"
            elif isinstance(result, str):
                if result.startswith('swh:'):
                    return result
                else:
                    return f"swh:1:dir:{result}"
            
            # If we get here, try alternative API if available
            if hasattr(miniswhid, 'hash_directory'):
                dir_hash = miniswhid.hash_directory(str(path))
                return f"swh:1:dir:{dir_hash}"
            
            # Last resort: use the result as-is
            return str(result)
            
        except Exception as e:
            print(f"Warning: miniswhid failed for {path}: {e}")
            print("Falling back to custom implementation")
            return self._generate_fallback(path)
    
    def _generate_fallback(self, path: Path) -> str:
        """
        Custom fallback implementation for SWHID generation.
        
        This is a simplified version that may not match SH exactly
        but provides a consistent hash for the directory content.
        
        Args:
            path: Directory path
            
        Returns:
            SWHID string
        """
        # Create a hash of the directory structure and content
        hasher = hashlib.sha1()
        
        # Get all files in sorted order for consistency
        all_files = []
        for root, dirs, files in os.walk(path):
            # Skip hidden and build directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                '__pycache__', 'node_modules', 'build', 'dist', 'target'
            }]
            dirs.sort()  # Ensure consistent ordering
            
            for file in sorted(files):
                if not file.startswith('.'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(path)
                    all_files.append(relative_path)
        
        # Sort all files for consistent ordering
        all_files.sort()
        
        # Hash the directory structure
        for relative_path in all_files:
            file_path = path / relative_path
            
            # Add file path to hash
            hasher.update(str(relative_path).encode('utf-8'))
            
            # Add file content hash
            try:
                with open(file_path, 'rb') as f:
                    file_hasher = hashlib.sha1()
                    while chunk := f.read(8192):
                        file_hasher.update(chunk)
                    hasher.update(file_hasher.digest())
            except (PermissionError, OSError):
                # Skip files we can't read
                continue
            
            # Add file mode (simplified)
            try:
                mode = oct(file_path.stat().st_mode)[-3:]
                hasher.update(mode.encode('utf-8'))
            except (PermissionError, OSError):
                hasher.update(b'644')  # Default mode
        
        # Generate the final hash
        dir_hash = hasher.hexdigest()
        
        # Return in SWHID format
        # Note: This is a simplified format and may not match SH exactly
        return f"swh:1:dir:{dir_hash}"
    
    def generate_content_swhid(self, file_path: Path) -> str:
        """
        Generate SWHID for file content.
        
        Args:
            file_path: File path
            
        Returns:
            SWHID string for the file content
        """
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        if self.use_swh_model:
            try:
                # Use official SWH model for accurate content hashing
                content = Content.from_file(path=file_path, max_content_length=10_000_000)
                return str(content.swhid())
            except Exception:
                # Fall back to basic implementation
                pass
        
        # Fallback: Generate git-compatible SHA1
        return self._hash_file_content(file_path)
    
    def _hash_file_content(self, file_path: Path) -> str:
        """
        Generate content hash for a single file.
        
        Args:
            file_path: File path
            
        Returns:
            SWHID string for content
        """
        hasher = hashlib.sha1()
        
        try:
            with open(file_path, 'rb') as f:
                # Add git-style header
                content = f.read()
                header = f"blob {len(content)}\0".encode('utf-8')
                hasher.update(header)
                hasher.update(content)
        except (PermissionError, OSError) as e:
            raise ValueError(f"Cannot read file {file_path}: {e}")
        
        content_hash = hasher.hexdigest()
        return f"swh:1:cnt:{content_hash}"
    
    def validate_swhid(self, swhid: str) -> bool:
        """
        Validate SWHID format.
        
        Args:
            swhid: SWHID string to validate
            
        Returns:
            True if valid SWHID format
        """
        if not isinstance(swhid, str):
            return False
        
        parts = swhid.split(':')
        if len(parts) != 4:
            return False
        
        if parts[0] != 'swh':
            return False
        
        if parts[1] != '1':  # Version
            return False
        
        if parts[2] not in {'cnt', 'dir', 'rev', 'rel', 'snp', 'ori'}:
            return False
        
        # Check if hash is valid hex
        try:
            int(parts[3], 16)
            if len(parts[3]) != 40:  # SHA1 length
                return False
        except ValueError:
            return False
        
        return True