"""SWHID generation using miniswhid."""

from pathlib import Path

import miniswhid


class SWHIDGenerator:
    """
    Generates Software Heritage Identifiers using miniswhid.
    """
    
    def __init__(self):
        """
        Initialize the SWHID generator.
        """
        pass  # miniswhid is now required, no configuration needed
    
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
        
        # Use miniswhid to compute SWHID
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
    
    def generate_content_swhid(self, file_path: Path) -> str:
        """
        Generate SWHID for individual file content.
        
        Args:
            file_path: File path
            
        Returns:
            SWHID string in format swh:1:cnt:HASH
        """
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        # Use miniswhid for file content
        result = miniswhid.compute_swhid(str(file_path))
        
        if isinstance(result, dict) and 'swhid' in result:
            return result['swhid']
        elif isinstance(result, str):
            if result.startswith('swh:'):
                return result
            else:
                # Assume it's a hash, format as content SWHID
                return f"swh:1:cnt:{result}"
        
        # Alternative API if available
        if hasattr(miniswhid, 'hash_file'):
            return f"swh:1:cnt:{miniswhid.hash_file(str(file_path))}"
        
        return str(result)