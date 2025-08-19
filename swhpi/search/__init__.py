"""Unified search module for source identification."""

from .providers import (
    SearchProvider,
    SerpAPIProvider,
    GitHubSearchProvider,
    SourcegraphProvider,
    SCANOSSProvider,
    SearchProviderRegistry,
    create_default_registry
)

from .strategies import (
    SourceIdentifier,
    identify_source
)

from .hash_search import HashSearcher

__all__ = [
    # Providers
    'SearchProvider',
    'SerpAPIProvider', 
    'GitHubSearchProvider',
    'SourcegraphProvider',
    'SCANOSSProvider',
    'SearchProviderRegistry',
    'create_default_registry',
    # Strategies
    'SourceIdentifier',
    'identify_source',
    # Hash search
    'HashSearcher',
]