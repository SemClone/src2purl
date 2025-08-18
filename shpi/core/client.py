"""Software Heritage API client."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

from shpi.core.config import SHPIConfig
from shpi.core.models import MatchType, SHAPIResponse, SHOriginMatch


class SoftwareHeritageClient:
    """Handles all interactions with Software Heritage API."""
    
    def __init__(self, config: SHPIConfig):
        """
        Initialize the Software Heritage client.
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, SHAPIResponse] = {} if config.cache_enabled else None
        self._rate_limiter = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self._last_request_time = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
    
    async def start_session(self):
        """Start the aiohttp session."""
        if self.session is None:
            timeout = ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_directory_origins(self, swhid: str) -> List[SHOriginMatch]:
        """
        Get all origins containing this directory.
        
        Args:
            swhid: Software Heritage Identifier for directory
            
        Returns:
            List of origin matches
        """
        # First, verify the directory exists
        dir_info = await self._get_directory_info(swhid)
        if not dir_info:
            return []
        
        # Then get origins that contain this directory
        # Note: The actual SH API endpoint for this might be different
        # This is a simplified version for demonstration
        origins_data = await self._get_directory_origins_data(swhid)
        
        # Convert to our model
        origins = []
        for origin in origins_data:
            try:
                origin_match = SHOriginMatch(
                    origin_url=origin.get('url', ''),
                    swhid=swhid,
                    last_seen=self._parse_datetime(origin.get('last_seen')),
                    visit_count=origin.get('visit_count', 1),
                    metadata=origin.get('metadata', {}),
                    match_type=MatchType.EXACT
                )
                origins.append(origin_match)
            except Exception as e:
                if self.config.verbose:
                    print(f"Error parsing origin {origin}: {e}")
                continue
        
        return origins
    
    async def get_content_origins(self, content_hash: str) -> List[SHOriginMatch]:
        """
        Get origins containing specific file content.
        
        Args:
            content_hash: Content hash
            
        Returns:
            List of origin matches
        """
        # Similar to directory origins but for content
        endpoint = f"/content/sha1:{content_hash}/origins/"
        response = await self._make_request(endpoint)
        
        if not response or not response.data:
            return []
        
        origins = []
        for origin in response.data:
            try:
                origin_match = SHOriginMatch(
                    origin_url=origin.get('url', ''),
                    swhid=f"swh:1:cnt:{content_hash}",
                    last_seen=self._parse_datetime(origin.get('last_seen')),
                    visit_count=origin.get('visit_count', 1),
                    metadata=origin.get('metadata', {}),
                    match_type=MatchType.EXACT
                )
                origins.append(origin_match)
            except Exception as e:
                if self.config.verbose:
                    print(f"Error parsing origin {origin}: {e}")
                continue
        
        return origins
    
    async def get_directory_tree(self, swhid: str) -> Dict[str, Any]:
        """
        Get directory structure for fuzzy comparison.
        
        Args:
            swhid: Directory SWHID
            
        Returns:
            Directory tree structure
        """
        # Extract hash from SWHID
        dir_hash = self._extract_hash_from_swhid(swhid)
        if not dir_hash:
            return {}
        
        endpoint = f"/directory/{dir_hash}/"
        response = await self._make_request(endpoint)
        
        if not response or not response.data:
            return {}
        
        return response.data
    
    async def get_directory_file_hashes(self, swhid: str) -> set[str]:
        """
        Get all file hashes in directory for content similarity.
        
        Args:
            swhid: Directory SWHID
            
        Returns:
            Set of file content hashes
        """
        tree = await self.get_directory_tree(swhid)
        hashes = set()
        
        if isinstance(tree, list):
            for entry in tree:
                if entry.get('type') == 'file':
                    target = entry.get('target')
                    if target:
                        hashes.add(target)
        
        return hashes
    
    async def _get_directory_info(self, swhid: str) -> Optional[Dict[str, Any]]:
        """Get basic directory information."""
        dir_hash = self._extract_hash_from_swhid(swhid)
        if not dir_hash:
            return None
        
        endpoint = f"/directory/{dir_hash}/"
        response = await self._make_request(endpoint)
        
        return response.data if response else None
    
    async def _get_directory_origins_data(self, swhid: str) -> List[Dict[str, Any]]:
        """Get origins data for a directory."""
        # Note: The actual SH API might not have a direct endpoint for this
        # We might need to search through snapshots/revisions
        # This is a simplified version
        
        dir_hash = self._extract_hash_from_swhid(swhid)
        if not dir_hash:
            return []
        
        # Try to find origins through various methods
        # Method 1: Direct directory to origin mapping (if available)
        endpoint = f"/directory/{dir_hash}/origins/"
        response = await self._make_request(endpoint, allow_404=True)
        
        if response and response.data:
            return response.data if isinstance(response.data, list) else [response.data]
        
        # Method 2: Search through graph (simplified)
        # In reality, this would involve more complex graph traversal
        return []
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        allow_404: bool = False
    ) -> Optional[SHAPIResponse]:
        """
        Make a request to the Software Heritage API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            allow_404: Whether to treat 404 as valid (empty) response
            
        Returns:
            API response or None if error
        """
        # Check cache first
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if self.cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if self.config.verbose:
                print(f"Cache hit for {endpoint}")
            return cached
        
        # Rate limiting
        await self._handle_rate_limiting()
        
        # Ensure session is started
        if not self.session:
            await self.start_session()
        
        url = f"{self.config.sh_api_base}{endpoint}"
        
        for retry in range(self.config.max_retries):
            try:
                async with self._rate_limiter:
                    async with self.session.get(url, params=params) as response:
                        # Handle different status codes
                        if response.status == 200:
                            data = await response.json()
                            result = SHAPIResponse(
                                data=data,
                                headers=dict(response.headers),
                                status=response.status,
                                cached=False
                            )
                            
                            # Cache the result
                            if self.cache is not None:
                                self.cache[cache_key] = result
                            
                            return result
                        
                        elif response.status == 404:
                            if allow_404:
                                return SHAPIResponse(
                                    data=[],
                                    headers=dict(response.headers),
                                    status=response.status,
                                    cached=False
                                )
                            if self.config.verbose:
                                print(f"404 Not Found: {url}")
                            return None
                        
                        elif response.status == 429:  # Rate limited
                            retry_after = int(response.headers.get('Retry-After', 60))
                            if self.config.verbose:
                                print(f"Rate limited. Waiting {retry_after} seconds...")
                            await asyncio.sleep(retry_after)
                            continue
                        
                        else:
                            if self.config.verbose:
                                print(f"HTTP {response.status}: {url}")
                            return None
            
            except ClientError as e:
                if self.config.verbose:
                    print(f"Request error (attempt {retry + 1}/{self.config.max_retries}): {e}")
                if retry < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** retry)  # Exponential backoff
                continue
            
            except Exception as e:
                if self.config.verbose:
                    print(f"Unexpected error: {e}")
                return None
        
        return None
    
    async def _handle_rate_limiting(self):
        """Implement rate limiting with configurable delay."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.config.rate_limit_delay:
            await asyncio.sleep(self.config.rate_limit_delay - time_since_last)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    def _extract_hash_from_swhid(self, swhid: str) -> Optional[str]:
        """
        Extract hash from SWHID string.
        
        Args:
            swhid: SWHID string (e.g., swh:1:dir:abc123...)
            
        Returns:
            Hash part or None if invalid
        """
        if not swhid or not swhid.startswith('swh:'):
            return None
        
        parts = swhid.split(':')
        if len(parts) == 4:
            return parts[3]
        
        return None
    
    def _parse_datetime(self, date_str: Any) -> datetime:
        """
        Parse datetime from various formats.
        
        Args:
            date_str: Date string or timestamp
            
        Returns:
            Datetime object
        """
        if isinstance(date_str, datetime):
            return date_str
        
        if isinstance(date_str, (int, float)):
            return datetime.fromtimestamp(date_str)
        
        if isinstance(date_str, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except ValueError:
                pass
            
            try:
                # Try other common formats
                from datetime import datetime
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        
        # Default to now if parsing fails
        return datetime.now()