"""Software Heritage API client."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

try:
    from swh.web.client.client import WebAPIClient
    SWH_CLIENT_AVAILABLE = True
except ImportError:
    SWH_CLIENT_AVAILABLE = False
    WebAPIClient = None

from src2id.core.cache import PersistentCache
from src2id.core.config import SWHPIConfig
from src2id.core.models import MatchType, SHAPIResponse, SHOriginMatch
from src2id.utils.datetime_utils import parse_datetime


class SoftwareHeritageClient:
    """Handles all interactions with Software Heritage API."""
    
    def __init__(self, config: SWHPIConfig):
        """
        Initialize the Software Heritage client.
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Use official WebAPIClient if available, fallback to custom implementation
        if SWH_CLIENT_AVAILABLE:
            # Configure official client with authentication if available
            client_kwargs = {"api_url": config.sh_api_base}
            if config.api_token:
                client_kwargs["bearer_token"] = config.api_token
                if config.verbose:
                    print("Using API authentication token")
            self.web_client = WebAPIClient(**client_kwargs)
            self._use_official_client = True
            if config.verbose:
                print("Using official Software Heritage WebAPIClient")
        else:
            self.web_client = None
            self._use_official_client = False
            if config.verbose:
                print("Using fallback HTTP client (install swh.web for better performance)")
        
        # Use persistent cache if enabled
        if config.cache_enabled:
            self.cache = PersistentCache()
            # Clean expired entries on startup
            removed = self.cache.clean_expired()
            if removed > 0 and config.verbose:
                print(f"Cleaned {removed} expired cache entries")
        else:
            self.cache = None
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
            headers = {}
            if self.config.api_token:
                headers["Authorization"] = f"Bearer {self.config.api_token}"
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
    
    async def close_session(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def search_origins_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search for origins by keyword.
        
        Args:
            keyword: Keyword to search for
            
        Returns:
            List of origin data
        """
        endpoint = f"/origin/search/{keyword}/"
        response = await self._make_request(endpoint)
        
        if not response or not response.data:
            return []
        
        return response.data if isinstance(response.data, list) else [response.data]
    
    async def check_swhids_known(self, swhids: List[str]) -> Dict[str, bool]:
        """
        Check which SWHIDs are known in the Software Heritage archive using batch API.
        
        Args:
            swhids: List of Software Heritage Identifiers
            
        Returns:
            Dictionary mapping SWHID to known status
        """
        if not swhids:
            return {}
        
        # Use official client if available
        if self._use_official_client and self.web_client:
            try:
                # Use the official known() method for batch checking
                result = self.web_client.known(swhids)
                return {swhid: data.get('known', False) for swhid, data in result.items()}
            except Exception as e:
                if self.config.verbose:
                    print(f"Official client failed, falling back: {e}")
                # Fall through to custom implementation
        
        # Ensure session is started for fallback requests
        if not self.session:
            await self.start_session()
        
        # Fallback to individual requests
        results = {}
        if self.config.verbose:
            print(f"Using fallback individual requests for {len(swhids)} SWHIDs")
        
        for i, swhid in enumerate(swhids):
            if self.config.verbose and len(swhids) > 5:
                print(f"Checking SWHID {i+1}/{len(swhids)}: {swhid[:20]}...")
            dir_info = await self._get_directory_info(swhid)
            results[swhid] = dir_info is not None
        
        return results
    
    async def get_directory_origins(self, swhid: str) -> List[SHOriginMatch]:
        """
        Get all origins containing this directory.
        
        Args:
            swhid: Software Heritage Identifier for directory
            
        Returns:
            List of origin matches
        """
        # First, check if directory is known using batch API
        known_status = await self.check_swhids_known([swhid])
        if not known_status.get(swhid, False):
            return []
        
        # Then get origins that contain this directory
        origins_data = await self._get_directory_origins_data(swhid)
        
        # Convert to our model
        origins = []
        for origin in origins_data:
            try:
                origin_match = SHOriginMatch(
                    origin_url=origin.get('url', ''),
                    swhid=swhid,
                    last_seen=parse_datetime(origin.get('last_seen')) or datetime.now(),
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
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                if self.config.verbose:
                    if cached.status == 404:
                        print(f"Cache hit (404) for {endpoint}")
                    else:
                        print(f"Cache hit for {endpoint}")
                # Return None for cached 404s with None data
                if cached.status == 404 and cached.data is None:
                    return None
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
                    timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
                    async with self.session.get(url, params=params, timeout=timeout) as response:
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
                                self.cache.set(cache_key, result)
                            
                            return result
                        
                        elif response.status == 404:
                            if allow_404:
                                result = SHAPIResponse(
                                    data=[],
                                    headers=dict(response.headers),
                                    status=response.status,
                                    cached=False
                                )
                                # Cache 404 responses too to avoid repeated queries
                                if self.cache is not None:
                                    self.cache.set(cache_key, result)
                                return result
                            if self.config.verbose:
                                print(f"404 Not Found: {url}")
                            # Cache negative result to avoid repeated queries
                            if self.cache is not None:
                                empty_result = SHAPIResponse(
                                    data=None,
                                    headers=dict(response.headers),
                                    status=404,
                                    cached=False
                                )
                                self.cache.set(cache_key, empty_result)
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
            
            except asyncio.TimeoutError:
                print(f"\n⚠️ Request timeout - Software Heritage API is not responding")
                print("This may be due to network issues or API overload.")
                print("Please try again later.")
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
    
