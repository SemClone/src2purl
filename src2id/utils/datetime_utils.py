"""DateTime utility functions."""

from datetime import datetime
from typing import Any, Optional


def parse_datetime(date_str: Any) -> Optional[datetime]:
    """
    Parse datetime from various formats.
    
    Args:
        date_str: Date string, timestamp, or datetime object
        
    Returns:
        Datetime object or None if parsing fails
    """
    if date_str is None:
        return None
        
    if isinstance(date_str, datetime):
        return date_str
    
    if isinstance(date_str, (int, float)):
        try:
            return datetime.fromtimestamp(date_str)
        except (ValueError, OSError):
            return None
    
    if isinstance(date_str, str):
        # Try ISO format first (most common)
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Try other common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    
    return None