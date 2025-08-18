"""Directory scanner for generating SWHID candidates."""

import os
from pathlib import Path
from typing import List, Optional, Set

from shpi.core.config import SHPIConfig
from shpi.core.models import DirectoryCandidate


class DirectoryScanner:
    """Scans filesystem and generates directory candidates for SH matching."""
    
    # Directories to skip during scanning
    SKIP_DIRS = {
        '.git', '.svn', '.hg', '.bzr',  # Version control
        '__pycache__', '.pytest_cache', '.mypy_cache',  # Python
        'node_modules', 'bower_components',  # JavaScript
        'target', 'build', 'dist', 'out',  # Build directories
        '.idea', '.vscode', '.vs',  # IDE directories
        'venv', 'env', '.env',  # Virtual environments
    }
    
    # File extensions to consider as source code
    SOURCE_EXTENSIONS = {
        # C/C++
        '.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.hxx', '.C', '.H',
        # Python
        '.py', '.pyx', '.pxd', '.pyi',
        # JavaScript/TypeScript
        '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
        # Java/Kotlin
        '.java', '.kt', '.kts',
        # Rust
        '.rs',
        # Go
        '.go',
        # Ruby
        '.rb',
        # Swift
        '.swift',
        # Other
        '.sh', '.bash', '.zsh', '.fish',
        '.yaml', '.yml', '.json', '.xml', '.toml',
    }
    
    def __init__(self, config: SHPIConfig, swhid_generator):
        """
        Initialize the directory scanner.
        
        Args:
            config: Configuration settings
            swhid_generator: SWHID generator instance
        """
        self.config = config
        self.swhid_generator = swhid_generator
    
    def scan_recursive(self, start_path: Path) -> List[DirectoryCandidate]:
        """
        Generate directory candidates using parent-first approach.
        
        This optimizes for finding matches at the package root level first,
        avoiding unnecessary scanning of subdirectories.
        
        Args:
            start_path: Starting directory path
            
        Returns:
            List of directory candidates ordered by specificity
        """
        candidates = []
        current = start_path.resolve()
        
        # Build parent chain starting from the target directory
        parent_chain = []
        temp = current
        for depth in range(self.config.max_depth + 1):
            parent_chain.append((temp, depth))
            if temp.parent == temp:  # Reached filesystem root
                break
            temp = temp.parent
        
        # Process from target directory first, then parents
        for path, depth in parent_chain:
            if not self._is_meaningful_directory(path):
                continue
            
            try:
                # Generate SWHID for the directory
                swhid = self.swhid_generator.generate_directory_swhid(path)
                
                # Count relevant files
                file_count = self._count_relevant_files(path)
                
                # Calculate specificity score (higher for more specific directories)
                specificity_score = self._calculate_specificity_score(
                    path, start_path, depth, file_count
                )
                
                candidate = DirectoryCandidate(
                    path=path,
                    swhid=swhid,
                    depth=depth,
                    specificity_score=specificity_score,
                    file_count=file_count
                )
                candidates.append(candidate)
                
                if self.config.verbose:
                    print(f"Scanned: {path.name} (depth={depth}, files={file_count})")
                
            except Exception as e:
                if self.config.verbose:
                    print(f"Error scanning {path}: {e}")
                continue
        
        # Sort by specificity score (highest first)
        candidates.sort(key=lambda c: c.specificity_score, reverse=True)
        
        return candidates
    
    def _is_meaningful_directory(self, path: Path) -> bool:
        """
        Check if directory likely contains package content.
        
        Args:
            path: Directory path to check
            
        Returns:
            True if directory should be scanned
        """
        if not path.is_dir():
            return False
        
        # Skip if directory name is in skip list
        if path.name in self.SKIP_DIRS:
            return False
        
        # Skip hidden directories (except current directory)
        if path.name.startswith('.') and path.name != '.':
            return False
        
        # Count source files (including in immediate subdirectories)
        source_file_count = 0
        try:
            # Check files in the directory itself
            for item in path.iterdir():
                if item.is_file() and item.suffix in self.SOURCE_EXTENSIONS:
                    source_file_count += 1
                    if source_file_count >= self.config.min_files:
                        return True
            
            # If not enough files in root, check immediate subdirectories
            if source_file_count < self.config.min_files:
                for subdir in path.iterdir():
                    if subdir.is_dir() and subdir.name not in self.SKIP_DIRS:
                        for item in subdir.iterdir():
                            if item.is_file() and item.suffix in self.SOURCE_EXTENSIONS:
                                source_file_count += 1
                                if source_file_count >= self.config.min_files:
                                    return True
                            if source_file_count > 10:  # Early exit for performance
                                return True
        except (PermissionError, OSError):
            return False
        
        # Also check for package indicators even with fewer source files
        if source_file_count > 0 and self._check_package_indicators(path) > 0:
            return True
        
        return source_file_count >= self.config.min_files
    
    def _count_relevant_files(self, path: Path) -> int:
        """
        Count source files, ignoring build artifacts.
        
        Args:
            path: Directory path
            
        Returns:
            Number of relevant files
        """
        count = 0
        try:
            for root, dirs, files in os.walk(path):
                # Skip directories in the skip list
                dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
                
                # Count source files
                for file in files:
                    if any(file.endswith(ext) for ext in self.SOURCE_EXTENSIONS):
                        count += 1
                
                # Limit traversal depth for performance
                if count > 1000:  # Arbitrary limit
                    break
        except (PermissionError, OSError):
            pass
        
        return count
    
    def _calculate_specificity_score(
        self, 
        path: Path, 
        start_path: Path, 
        depth: int, 
        file_count: int
    ) -> float:
        """
        Calculate how specific/relevant a directory is.
        
        Args:
            path: Directory path being scored
            start_path: Original starting path
            depth: Depth from starting path
            file_count: Number of relevant files
            
        Returns:
            Specificity score between 0 and 1
        """
        # Base score from depth (closer to start = higher score)
        depth_score = 1.0 / (depth + 1)
        
        # Bonus for being the exact start path
        if path == start_path:
            depth_score *= 1.5
        
        # File count factor (more files = more likely to be root)
        file_factor = min(1.0, file_count / 100.0)
        
        # Check for package indicators
        package_indicators = self._check_package_indicators(path)
        
        # Combine factors
        score = (
            depth_score * self.config.score_weights['specificity'] +
            file_factor * 0.3 +
            package_indicators * 0.3
        )
        
        return min(1.0, score)
    
    def _check_package_indicators(self, path: Path) -> float:
        """
        Check for indicators that this is a package root.
        
        Args:
            path: Directory path to check
            
        Returns:
            Score between 0 and 1 based on package indicators
        """
        score = 0.0
        indicators = {
            # Build files
            'CMakeLists.txt': 0.3,
            'Makefile': 0.2,
            'configure': 0.2,
            'setup.py': 0.3,
            'package.json': 0.3,
            'Cargo.toml': 0.3,
            'go.mod': 0.3,
            'pom.xml': 0.3,
            'build.gradle': 0.3,
            # Documentation
            'README.md': 0.1,
            'README.rst': 0.1,
            'README.txt': 0.1,
            'LICENSE': 0.1,
            'LICENSE.txt': 0.1,
            'COPYING': 0.1,
        }
        
        for filename, weight in indicators.items():
            if (path / filename).exists():
                score += weight
        
        return min(1.0, score)
    
    def detect_git_submodules(self, repo_path: Path) -> List[Path]:
        """
        Parse .gitmodules and return submodule paths.
        
        Args:
            repo_path: Repository root path
            
        Returns:
            List of submodule paths
        """
        submodules = []
        gitmodules_path = repo_path / '.gitmodules'
        
        if not gitmodules_path.exists():
            return submodules
        
        try:
            with open(gitmodules_path, 'r') as f:
                lines = f.readlines()
            
            current_path = None
            for line in lines:
                line = line.strip()
                if line.startswith('path ='):
                    current_path = line.split('=', 1)[1].strip()
                    submodule_path = repo_path / current_path
                    if submodule_path.exists():
                        submodules.append(submodule_path)
        except Exception as e:
            if self.config.verbose:
                print(f"Error parsing .gitmodules: {e}")
        
        return submodules