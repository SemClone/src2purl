"""Tests for confidence scoring."""

import pytest
from datetime import datetime, timedelta

from src2id.core.config import SWHPIConfig
from src2id.core.scorer import ConfidenceScorer
from src2id.core.models import MatchType


class TestConfidenceScorer:
    """Test confidence scoring functionality."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return SWHPIConfig()
    
    @pytest.fixture
    def scorer(self, config):
        """Create a confidence scorer instance."""
        return ConfidenceScorer(config)
    
    def test_exact_match_high_score(self, scorer):
        """Test that exact matches get high base scores."""
        match_data = {
            'match_type': MatchType.EXACT,
            'frequency_rank': 10,
            'is_official_org': True,
            'last_activity': datetime.now()
        }
        
        score = scorer.calculate_confidence(match_data)
        assert score > 0.8  # Exact match should have high confidence
    
    def test_fuzzy_match_lower_score(self, scorer):
        """Test that fuzzy matches get lower scores than exact."""
        fuzzy_data = {
            'match_type': MatchType.FUZZY,
            'similarity_score': 0.5,
            'frequency_rank': 5,
            'is_official_org': False,
            'last_activity': datetime.now() - timedelta(days=90)
        }
        
        exact_data = {
            'match_type': MatchType.EXACT,
            'frequency_rank': 5,
            'is_official_org': False,
            'last_activity': datetime.now() - timedelta(days=90)
        }
        
        fuzzy_score = scorer.calculate_confidence(fuzzy_data)
        exact_score = scorer.calculate_confidence(exact_data)
        assert fuzzy_score < exact_score  # Fuzzy should be lower than exact
    
    def test_official_org_boost(self, scorer):
        """Test that official organizations get a boost."""
        base_data = {
            'match_type': MatchType.EXACT,
            'frequency_rank': 3,  # Lower frequency to avoid hitting 1.0 cap
            'last_activity': datetime.now() - timedelta(days=30)
        }
        
        unofficial_data = {**base_data, 'is_official_org': False}
        official_data = {**base_data, 'is_official_org': True}
        
        unofficial_score = scorer.calculate_confidence(unofficial_data)
        official_score = scorer.calculate_confidence(official_data)
        
        # Official should be higher, unless both hit the 1.0 cap
        assert official_score >= unofficial_score
        if unofficial_score < 1.0:
            assert official_score > unofficial_score
    
    def test_recency_affects_score(self, scorer):
        """Test that recent activity increases score."""
        base_data = {
            'match_type': MatchType.EXACT,
            'frequency_rank': 5,
            'is_official_org': False
        }
        
        recent_data = {**base_data, 'last_activity': datetime.now()}
        old_data = {**base_data, 'last_activity': datetime.now() - timedelta(days=1000)}
        
        recent_score = scorer.calculate_confidence(recent_data)
        old_score = scorer.calculate_confidence(old_data)
        
        assert recent_score > old_score
    
    def test_frequency_affects_score(self, scorer):
        """Test that higher frequency increases score."""
        base_data = {
            'match_type': MatchType.EXACT,
            'is_official_org': False,
            'last_activity': datetime.now()
        }
        
        low_freq_data = {**base_data, 'frequency_rank': 1}
        high_freq_data = {**base_data, 'frequency_rank': 100}
        
        low_score = scorer.calculate_confidence(low_freq_data)
        high_score = scorer.calculate_confidence(high_freq_data)
        
        assert high_score > low_score
    
    def test_score_bounds(self, scorer):
        """Test that scores are always between 0 and 1."""
        test_cases = [
            {'match_type': MatchType.EXACT, 'frequency_rank': 1000},
            {'match_type': MatchType.FUZZY, 'frequency_rank': 0},
            {'match_type': MatchType.EXACT, 'frequency_rank': -1},
        ]
        
        for match_data in test_cases:
            score = scorer.calculate_confidence(match_data)
            assert 0.0 <= score <= 1.0
    
    def test_missing_optional_fields(self, scorer):
        """Test handling of missing optional fields."""
        minimal_data = {
            'match_type': MatchType.EXACT
        }
        
        score = scorer.calculate_confidence(minimal_data)
        assert 0.0 <= score <= 1.0  # Should still produce valid score
    
    def test_none_last_activity(self, scorer):
        """Test handling of None last_activity."""
        match_data = {
            'match_type': MatchType.EXACT,
            'frequency_rank': 5,
            'is_official_org': False,
            'last_activity': None
        }
        
        score = scorer.calculate_confidence(match_data)
        assert 0.0 <= score <= 1.0  # Should handle None gracefully