"""Confidence scoring for package matches."""

from datetime import datetime, timedelta
from typing import Any, Dict

from src2id.core.config import SWHPIConfig
from src2id.utils.datetime_utils import parse_datetime


class ConfidenceScorer:
    """Calculates confidence scores for package matches."""
    
    def __init__(self, config: SWHPIConfig):
        """
        Initialize the confidence scorer.
        
        Args:
            config: Configuration settings
        """
        self.config = config
    
    def calculate_confidence(self, match_data: Dict[str, Any]) -> float:
        """
        Multi-factor confidence scoring.
        
        Factors considered:
        - Match type (exact vs fuzzy)
        - Frequency/popularity
        - Official organization authority
        - Recency of activity
        
        Args:
            match_data: Dictionary with match information
            
        Returns:
            Confidence score between 0 and 1
        """
        # Get base score from match type
        base_score = self._get_base_score(match_data)
        
        # Calculate individual factor scores
        frequency_score = self._frequency_score(match_data.get('frequency_rank', 1))
        authority_score = self._authority_score(match_data.get('is_official_org', False))
        recency_score = self._recency_score(match_data.get('last_activity'))
        
        # Combine scores using configured weights
        weights = self.config.score_weights
        
        # Weighted combination
        final_score = (
            base_score * 0.4 +  # Base match quality
            frequency_score * weights.get('popularity', 0.2) +
            authority_score * weights.get('authority', 0.3) +
            recency_score * weights.get('recency', 0.3)
        )
        
        # Apply multipliers
        multipliers = [
            self._frequency_multiplier(match_data.get('frequency_rank', 1)),
            self._authority_multiplier(match_data.get('is_official_org', False)),
            self._recency_multiplier(match_data.get('last_activity')),
        ]
        
        for multiplier in multipliers:
            final_score *= multiplier
        
        # Ensure score is within bounds
        return min(1.0, max(0.0, final_score))
    
    def _get_base_score(self, match_data: Dict[str, Any]) -> float:
        """
        Get base confidence score from match type.
        
        Args:
            match_data: Match information
            
        Returns:
            Base score
        """
        match_type = match_data.get('match_type')
        
        if match_type == 'exact' or match_type.value == 'exact':
            return 0.9
        elif match_type == 'fuzzy' or match_type.value == 'fuzzy':
            # For fuzzy matches, use similarity score
            similarity = match_data.get('similarity_score', 0.5)
            return similarity * 0.8
        else:
            return 0.5
    
    def _frequency_score(self, frequency_rank: int) -> float:
        """
        Calculate score based on frequency/popularity.
        
        Args:
            frequency_rank: Number of visits/occurrences
            
        Returns:
            Frequency score between 0 and 1
        """
        if frequency_rank <= 0:
            return 0.0
        elif frequency_rank == 1:
            return 0.3
        elif frequency_rank < 5:
            return 0.5
        elif frequency_rank < 10:
            return 0.7
        elif frequency_rank < 50:
            return 0.85
        else:
            return 1.0
    
    def _authority_score(self, is_official: bool) -> float:
        """
        Calculate score based on official organization status.
        
        Args:
            is_official: Whether from official organization
            
        Returns:
            Authority score
        """
        return 1.0 if is_official else 0.7
    
    def _recency_score(self, last_activity: Any) -> float:
        """
        Calculate score based on recency of activity.
        
        Args:
            last_activity: Last activity datetime
            
        Returns:
            Recency score between 0 and 1
        """
        parsed = parse_datetime(last_activity)
        if not parsed:
            return 0.5
        last_activity = parsed
        
        # Calculate days since last activity
        now = datetime.now(last_activity.tzinfo) if last_activity.tzinfo else datetime.now()
        days_ago = (now - last_activity).days
        
        if days_ago < 30:
            return 1.0
        elif days_ago < 90:
            return 0.9
        elif days_ago < 180:
            return 0.8
        elif days_ago < 365:
            return 0.7
        elif days_ago < 730:  # 2 years
            return 0.6
        else:
            return 0.5
    
    def _frequency_multiplier(self, frequency_rank: int) -> float:
        """
        Boost confidence for frequently appearing packages.
        
        Args:
            frequency_rank: Number of visits/occurrences
            
        Returns:
            Multiplier value
        """
        if frequency_rank < 2:
            return 0.95
        elif frequency_rank < 5:
            return 1.0
        elif frequency_rank < 20:
            return 1.05
        elif frequency_rank < 100:
            return 1.1
        else:
            return 1.15
    
    def _authority_multiplier(self, is_official: bool) -> float:
        """
        Boost confidence for official organizations.
        
        Args:
            is_official: Whether from official organization
            
        Returns:
            Multiplier value
        """
        return 1.15 if is_official else 1.0
    
    def _recency_multiplier(self, last_activity: Any) -> float:
        """
        Boost confidence for recently active repositories.
        
        Args:
            last_activity: Last activity datetime
            
        Returns:
            Multiplier value
        """
        parsed = parse_datetime(last_activity)
        if not parsed:
            return 1.0
        last_activity = parsed
        
        # Calculate days since last activity
        now = datetime.now(last_activity.tzinfo) if last_activity.tzinfo else datetime.now()
        days_ago = (now - last_activity).days
        
        if days_ago < 30:
            return 1.1
        elif days_ago < 365:
            return 1.05
        elif days_ago > 1095:  # 3 years
            return 0.95
        else:
            return 1.0