"""Optimized hash-based search functionality."""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

from rich.console import Console

from .providers import SearchProviderRegistry

console = Console()


class HashSearcher:
    """Optimized search for files by their content hashes."""
    
    def __init__(
        self,
        search_registry: Optional[SearchProviderRegistry] = None,
        verbose: bool = False
    ):
        """Initialize the hash searcher.
        
        Args:
            search_registry: Registry of search providers to use
            verbose: Whether to show verbose output
        """
        self.verbose = verbose
        self.search_registry = search_registry
    
    def compute_file_hashes(self, file_path: Path) -> Dict[str, str]:
        """Compute various hashes for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary of hash types to hash values
        """
        hashes = {}
        
        try:
            content = file_path.read_bytes()
            
            # SHA1 (used by Git and SWH)
            sha1 = hashlib.sha1(content).hexdigest()
            hashes['sha1'] = sha1
            
            # Git blob hash (includes header)
            git_header = f"blob {len(content)}\0".encode()
            git_content = git_header + content
            git_sha1 = hashlib.sha1(git_content).hexdigest()
            hashes['sha1_git'] = git_sha1
            
            # SHA256 (modern standard)
            sha256 = hashlib.sha256(content).hexdigest()
            hashes['sha256'] = sha256
            
            # MD5 (legacy, but still used)
            md5 = hashlib.md5(content).hexdigest()
            hashes['md5'] = md5
            
        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]Error computing hashes for {file_path}: {e}[/yellow]")
        
        return hashes
    
    def compute_directory_hash(self, directory: Path) -> str:
        """Compute directory hash similar to SWH directory identifier.
        
        Args:
            directory: Path to directory
            
        Returns:
            Directory hash
        """
        entries = []
        
        try:
            for item in sorted(directory.iterdir()):
                if item.name.startswith('.'):
                    continue
                    
                if item.is_file():
                    try:
                        content = item.read_bytes()
                        sha1 = hashlib.sha1(content).hexdigest()
                        entries.append(f"100644 {item.name}\0{bytes.fromhex(sha1)}")
                    except:
                        pass
                elif item.is_dir() and not item.is_symlink():
                    # Recursive directory hash
                    dir_hash = self.compute_directory_hash(item)
                    if dir_hash:
                        entries.append(f"40000 {item.name}\0{bytes.fromhex(dir_hash)}")
            
            if entries:
                tree_content = b''.join(e.encode() if isinstance(e, str) else e for e in entries)
                return hashlib.sha1(tree_content).hexdigest()
                
        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]Error computing directory hash: {e}[/yellow]")
        
        return ""
    
    async def search_hash(
        self,
        hash_value: str,
        hash_type: str = "auto"
    ) -> List[str]:
        """Search for a hash value across all providers.
        
        Args:
            hash_value: The hash value to search for
            hash_type: Type of hash (sha1, sha256, md5, auto)
            
        Returns:
            List of unique repository URLs found
        """
        if not self.search_registry:
            return []
        
        all_urls = set()
        
        # Determine hash type if auto
        if hash_type == "auto":
            if len(hash_value) == 32:
                hash_type = "md5"
            elif len(hash_value) == 40:
                hash_type = "sha1"
            elif len(hash_value) == 64:
                hash_type = "sha256"
        
        # Build optimized search queries
        queries = [
            f'"{hash_value}" site:github.com',
            f'"{hash_value}" site:gitlab.com',
            f'"sha1_git:{hash_value}" site:archive.softwareheritage.org'
        ]
        
        # Execute searches in parallel
        tasks = []
        for query in queries:
            if self.verbose:
                console.print(f"[dim]Searching: {query}[/dim]")
            tasks.append(self.search_registry.search_all(query))
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict):
                    for provider, urls in result.items():
                        all_urls.update(urls)
                        
        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]Search error: {e}[/yellow]")
        
        return list(all_urls)
    
    async def search_file(
        self,
        file_path: Path
    ) -> Dict[str, List[str]]:
        """Search for a file by computing and searching its hashes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary mapping hash types to lists of repository URLs
        """
        if not file_path.exists():
            if self.verbose:
                console.print(f"[red]File not found: {file_path}[/red]")
            return {}
        
        hashes = self.compute_file_hashes(file_path)
        
        if self.verbose:
            console.print(f"\n[bold]Computed hashes for {file_path.name}:[/bold]")
            for hash_type, hash_value in hashes.items():
                console.print(f"  {hash_type}: {hash_value}")
        
        results = {}
        
        # Search for most relevant hashes in parallel
        search_tasks = []
        for hash_type in ['sha1_git', 'sha1']:  # Prioritize git hashes
            if hash_type in hashes:
                search_tasks.append((hash_type, self.search_hash(hashes[hash_type], hash_type)))
        
        if search_tasks:
            task_results = await asyncio.gather(*[task for _, task in search_tasks])
            
            for (hash_type, _), urls in zip(search_tasks, task_results):
                if urls:
                    results[hash_type] = urls
                    if self.verbose:
                        console.print(f"[green]Found {len(urls)} results for {hash_type}[/green]")
        
        return results