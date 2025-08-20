"""Persistent cache for API responses."""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src2id.core.models import SHAPIResponse


class PersistentCache:
    """File-based persistent cache for API responses."""
    
    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        """
        Initialize persistent cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live for cache entries in hours
        """
        if cache_dir is None:
            # Use user's cache directory
            cache_dir = Path.home() / '.cache' / 'swhpi'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        
        # In-memory cache for current session
        self.memory_cache: Dict[str, SHAPIResponse] = {}
    
    def get(self, key: str) -> Optional[SHAPIResponse]:
        """
        Get cached response if it exists and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached response or None
        """
        # Check memory cache first
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # Check file cache
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check if expired
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                # Expired, remove file
                cache_file.unlink(missing_ok=True)
                return None
            
            # Reconstruct response
            response = SHAPIResponse(
                data=data['data'],
                headers=data.get('headers', {}),
                status=data.get('status', 200),
                cached=True
            )
            
            # Store in memory cache for faster access
            self.memory_cache[key] = response
            return response
            
        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted cache file, remove it
            cache_file.unlink(missing_ok=True)
            return None
    
    def set(self, key: str, response: SHAPIResponse) -> None:
        """
        Store response in cache.
        
        Args:
            key: Cache key
            response: Response to cache
        """
        # Store in memory cache
        self.memory_cache[key] = response
        
        # Store in file cache
        cache_file = self._get_cache_file(key)
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': response.data,
                'headers': response.headers,
                'status': response.status
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
                
        except (TypeError, ValueError) as e:
            # Can't serialize, skip caching
            if cache_file.exists():
                cache_file.unlink(missing_ok=True)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        # Clear memory cache
        self.memory_cache.clear()
        
        # Clear file cache
        for cache_file in self.cache_dir.glob('*.json'):
            cache_file.unlink(missing_ok=True)
    
    def clean_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        removed = 0
        
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                cached_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cached_time > self.ttl:
                    cache_file.unlink(missing_ok=True)
                    removed += 1
                    
            except (json.JSONDecodeError, KeyError, ValueError):
                # Corrupted file, remove it
                cache_file.unlink(missing_ok=True)
                removed += 1
        
        return removed
    
    def _get_cache_file(self, key: str) -> Path:
        """
        Get cache file path for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Path to cache file
        """
        # Create a safe filename from the key
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        # Include part of the key for debugging
        safe_key = key.replace('/', '_').replace(':', '_')[:50]
        filename = f"{safe_key}_{key_hash}.json"
        
        return self.cache_dir / filename
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        cache_files = list(self.cache_dir.glob('*.json'))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'entries': len(cache_files),
            'memory_entries': len(self.memory_cache),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }