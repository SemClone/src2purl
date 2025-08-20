"""Tests for datetime utility functions."""

import pytest
from datetime import datetime

from src2id.utils.datetime_utils import parse_datetime


class TestParseDatetime:
    """Test datetime parsing functionality."""
    
    def test_parse_none(self):
        """Test parsing None returns None."""
        assert parse_datetime(None) is None
    
    def test_parse_datetime_object(self):
        """Test datetime object is returned as-is."""
        now = datetime.now()
        assert parse_datetime(now) == now
    
    def test_parse_timestamp(self):
        """Test parsing Unix timestamp."""
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        result = parse_datetime(timestamp)
        assert result is not None
        # The year depends on timezone, just check it parsed
        assert result.year in [2020, 2021]
    
    def test_parse_float_timestamp(self):
        """Test parsing float timestamp."""
        timestamp = 1609459200.5
        result = parse_datetime(timestamp)
        assert result is not None
    
    def test_parse_iso_format(self):
        """Test parsing ISO format string."""
        iso_str = "2021-01-01T12:00:00"
        result = parse_datetime(iso_str)
        assert result is not None
        assert result.year == 2021
        assert result.hour == 12
    
    def test_parse_iso_with_z(self):
        """Test parsing ISO format with Z timezone."""
        iso_str = "2021-01-01T12:00:00Z"
        result = parse_datetime(iso_str)
        assert result is not None
        assert result.year == 2021
    
    def test_parse_date_only(self):
        """Test parsing date-only string."""
        date_str = "2021-01-01"
        result = parse_datetime(date_str)
        assert result is not None
        assert result.year == 2021
        assert result.month == 1
        assert result.day == 1
    
    def test_parse_datetime_with_space(self):
        """Test parsing datetime with space separator."""
        dt_str = "2021-01-01 12:30:45"
        result = parse_datetime(dt_str)
        assert result is not None
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45
    
    def test_parse_invalid_string(self):
        """Test parsing invalid string returns None."""
        assert parse_datetime("not a date") is None
    
    def test_parse_invalid_type(self):
        """Test parsing invalid type returns None."""
        assert parse_datetime([]) is None
        assert parse_datetime({}) is None