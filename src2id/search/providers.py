"""Search providers for source identification."""

import os
import json
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio

import aiohttp
from rich.console import Console

console = Console()


class SearchProvider(ABC):
    """Abstract base class for search providers."""
    
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        """Initialize the search provider."""
        self.api_key = api_key
        self.verbose = verbose
        self.session = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the search provider."""
        pass
    
    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Return whether this provider requires an API key."""
        pass
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[str]:
        """Perform a search and return repository URLs."""
        pass
    
    async def ensure_session(self):
        """Ensure we have an active session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def extract_repo_urls(self, urls: List[str]) -> List[str]:
        """Extract and filter repository URLs from a list of URLs."""
        from urllib.parse import urlparse

        repo_urls = []
        for url in urls:
            try:
                parsed = urlparse(url)
                hostname = parsed.hostname.lower() if parsed.hostname else ''

                if hostname in ('github.com', 'gitlab.com', 'bitbucket.org'):
                    # Clean up the URL - remove file-specific paths
                    if "/blob/" in url or "/tree/" in url:
                        if hostname in ('github.com', 'gitlab.com'):
                            path_parts = parsed.path.strip('/').split('/')
                            if len(path_parts) >= 2:
                                # Keep only owner/repo part
                                clean_path = f"/{path_parts[0]}/{path_parts[1]}"
                                clean_url = f"{parsed.scheme}://{hostname}{clean_path}"
                                repo_urls.append(clean_url)
                    else:
                        repo_urls.append(url)
            except Exception:
                # If URL parsing fails, skip this URL
                continue
        return list(set(repo_urls))


class SerpAPIProvider(SearchProvider):
    """Search provider using SerpAPI (Google Search)."""
    
    @property
    def name(self) -> str:
        return "SerpAPI"
    
    @property
    def requires_api_key(self) -> bool:
        return True
    
    async def search(self, query: str, **kwargs) -> List[str]:
        """Search using SerpAPI."""
        if not self.api_key:
            return []
        
        await self.ensure_session()
        
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": kwargs.get("engine", "google"),
            "num": kwargs.get("num", 10)
        }
        
        try:
            async with self.session.get("https://serpapi.com/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    urls = [
                        result.get("link", "")
                        for result in data.get("organic_results", [])
                        if result.get("link")
                    ]
                    return self.extract_repo_urls(urls)
                return []
        except Exception as e:
            if self.verbose:
                console.print(f"[red]{self.name} error: {e}[/red]")
            return []


class GitHubSearchProvider(SearchProvider):
    """Search provider using GitHub's search API."""
    
    @property
    def name(self) -> str:
        return "GitHub"
    
    @property
    def requires_api_key(self) -> bool:
        return False  # Optional
    
    async def search(self, query: str, **kwargs) -> List[str]:
        """Search using GitHub API."""
        await self.ensure_session()
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.api_key:
            headers["Authorization"] = f"token {self.api_key}"
        
        # Extract search terms
        import re
        search_terms = re.findall(r'"([^"]+)"', query)
        if not search_terms:
            search_terms = [query]
        
        urls = []
        for term in search_terms[:1]:  # Limit to avoid rate limits
            try:
                params = {"q": term[:100], "per_page": 5, "sort": "stars"}
                async with self.session.get(
                    "https://api.github.com/search/repositories",
                    params=params,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        urls.extend([
                            item.get("html_url", "")
                            for item in data.get("items", [])
                            if item.get("html_url")
                        ])
            except Exception:
                pass
        
        return self.extract_repo_urls(urls)


class SourcegraphProvider(SearchProvider):
    """Search provider using Sourcegraph code search."""
    
    @property
    def name(self) -> str:
        return "Sourcegraph"
    
    @property
    def requires_api_key(self) -> bool:
        return False
    
    async def search(self, query: str, **kwargs) -> List[str]:
        """Search using Sourcegraph (simplified implementation)."""
        # Note: Full implementation would use Sourcegraph API
        # This is a placeholder that returns empty results
        return []


class SCANOSSProvider(SearchProvider):
    """Provider for SCANOSS code identification service."""
    
    DEFAULT_URL = 'https://api.osskb.org/scan/direct'
    PREMIUM_URL = 'https://api.scanoss.com/scan/direct'
    
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        """Initialize SCANOSS provider."""
        super().__init__(api_key, verbose)
        self.url = self.PREMIUM_URL if api_key else self.DEFAULT_URL
    
    @property
    def name(self) -> str:
        return "SCANOSS"
    
    @property
    def requires_api_key(self) -> bool:
        return False  # Works without key
    
    async def search(self, query: str, **kwargs) -> List[str]:
        """SCANOSS doesn't do text search - use scan_file instead."""
        return []
    
    async def scan_file(self, file_path: Path) -> Dict:
        """Scan a file using SCANOSS winnowing algorithm."""
        await self.ensure_session()
        
        try:
            content = file_path.read_bytes()
            wfp = self._create_wfp(file_path, content)
            
            headers = {'User-Agent': 'swhpi-scanner/1.0'}
            if self.api_key:
                headers['X-Session'] = self.api_key
            
            form_data = aiohttp.FormData()
            form_data.add_field('file', wfp, filename='scan.wfp')
            form_data.add_field('format', 'plain')
            
            async with self.session.post(
                self.url,
                data=form_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result_text = await response.text()
                    return json.loads(result_text)
                return {}
        except Exception as e:
            if self.verbose:
                console.print(f"[red]SCANOSS error: {e}[/red]")
            return {}
    
    def _create_wfp(self, file_path: Path, content: bytes) -> str:
        """Create simplified WFP for SCANOSS."""
        md5_hash = hashlib.md5(content).hexdigest()
        return f"file={md5_hash},{len(content)},{file_path.name}\n1=00000000"


class SearchProviderRegistry:
    """Registry for managing search providers."""
    
    def __init__(self, verbose: bool = False):
        """Initialize the registry."""
        self.providers: Dict[str, SearchProvider] = {}
        self.verbose = verbose
    
    def register_provider(self, name: str, provider: SearchProvider):
        """Register a search provider."""
        self.providers[name] = provider
    
    def get_provider(self, name: str) -> Optional[SearchProvider]:
        """Get a provider by name."""
        return self.providers.get(name)
    
    async def search_all(self, query: str, **kwargs) -> Dict[str, List[str]]:
        """Search using all registered providers."""
        results = {}
        for name, provider in self.providers.items():
            if provider.requires_api_key and not provider.api_key:
                continue
            try:
                urls = await provider.search(query, **kwargs)
                if urls:
                    results[name] = urls
            except Exception:
                pass
        return results
    
    async def close_all(self):
        """Close all provider sessions."""
        for provider in self.providers.values():
            await provider.close()


def create_default_registry(verbose: bool = False) -> SearchProviderRegistry:
    """Create a registry with default providers configured from environment."""
    registry = SearchProviderRegistry(verbose=verbose)
    
    # SerpAPI
    if serpapi_key := os.environ.get("SERPAPI_KEY"):
        registry.register_provider(
            "serpapi",
            SerpAPIProvider(api_key=serpapi_key, verbose=verbose)
        )
    
    # GitHub
    github_token = os.environ.get("GITHUB_TOKEN")
    registry.register_provider(
        "github",
        GitHubSearchProvider(api_key=github_token, verbose=verbose)
    )
    
    # SCANOSS
    scanoss_key = os.environ.get("SCANOSS_API_KEY")
    registry.register_provider(
        "scanoss",
        SCANOSSProvider(api_key=scanoss_key, verbose=verbose)
    )
    
    return registry