# SWHPI - Software Heritage Package Identifier

## Overview

SWHPI is a powerful tool for identifying software packages and their origins using multiple strategies including the Software Heritage archive, SCANOSS fingerprinting, and web searches.

## Architecture

The codebase is organized into modular components:

### Core Modules (`swhpi/core/`)
- **client.py**: Software Heritage API client with batch checking support
- **scanner.py**: Directory and file scanning with SWHID generation
- **models.py**: Data models for candidates, matches, and results
- **orchestrator.py**: Main coordination logic for package identification
- **config.py**: Configuration management
- **cache.py**: Persistent caching for API responses
- **scorer.py**: Confidence scoring for matches
- **extractor.py**: Package coordinate extraction
- **purl.py**: Package URL (PURL) generation
- **swhid.py**: Software Heritage identifier generation

### Search Module (`swhpi/search/`)
Unified search functionality with multiple strategies:

- **providers.py**: Search provider implementations
  - SerpAPI (Google search)
  - GitHub API search
  - Sourcegraph search
  - SCANOSS fingerprinting
  
- **strategies.py**: Identification strategies
  - Software Heritage archive lookup
  - Hash-based search
  - SCANOSS winnowing
  - Web search aggregation
  
- **hash_search.py**: Optimized hash computation and search

### CLI Module (`swhpi/cli/`)
- **main.py**: Main command-line interface
- **validate.py**: Input validation

### Integrations (`swhpi/integrations/`)
- **oslili.py**: License detection integration

## Key Features

### 1. Multiple Identification Strategies
- **Software Heritage**: Direct archive lookup using SWHIDs
- **Hash Search**: Content-based search using SHA1, SHA256, MD5
- **SCANOSS**: Winnowing algorithm for code fingerprinting
- **Web Search**: Aggregated search across GitHub, GitLab, etc.

### 2. Batch Processing
- Efficient batch checking of multiple SWHIDs
- Parallel search execution
- Optimized API calls

### 3. Caching
- Persistent disk-based caching
- Reduces API calls
- Configurable cache management

### 4. Confidence Scoring
- Multi-factor scoring algorithm
- Configurable thresholds
- Strategy-based weighting

## Usage

### Basic Command
```bash
swhpi /path/to/project --confidence-threshold 0.3
```

### With Authentication
```bash
export SWH_API_TOKEN="your-token"
export SERPAPI_KEY="your-key"
swhpi /path/to/project --verbose
```

### Advanced Options
```bash
swhpi /path/to/project \
  --max-depth 3 \
  --confidence-threshold 0.5 \
  --output-format json \
  --no-cache \
  --verbose
```

## API Usage

### Using the Source Identifier
```python
from swhpi.search import SourceIdentifier

identifier = SourceIdentifier(verbose=True)
results = await identifier.identify(
    path=Path("test_data/darktable"),
    max_depth=2,
    confidence_threshold=0.3
)
```

### Using Specific Strategies
```python
from swhpi.search import identify_source

# Use only SCANOSS
results = await identify_source(
    path=Path("test_data/darktable"),
    strategies=["scanoss"],
    verbose=True
)
```

### Hash Search
```python
from swhpi.search import HashSearcher, create_default_registry

registry = create_default_registry()
searcher = HashSearcher(search_registry=registry)

# Search by file
results = await searcher.search_file(Path("README.md"))

# Search by hash
urls = await searcher.search_hash("abc123...", hash_type="sha1")
```

## Testing

Run the unified test suite:
```python
from tests.test_identification import test_identification_suite
await test_identification_suite(Path("test_data/darktable"))
```

## Environment Variables

- `SWH_API_TOKEN`: Software Heritage API authentication token
- `SERPAPI_KEY`: SerpAPI key for web searches
- `GITHUB_TOKEN`: GitHub API token (optional)
- `SCANOSS_API_KEY`: SCANOSS premium API key (optional)

## Performance Optimization

The codebase has been optimized for:
1. **Parallel Execution**: Multiple searches run concurrently
2. **Batch Processing**: Reduces API calls through batching
3. **Smart Caching**: Persistent cache reduces redundant calls
4. **Lazy Loading**: Components loaded only when needed
5. **Efficient Hashing**: Optimized hash computation algorithms

## Architecture Decisions

1. **Modular Design**: Each component has a single responsibility
2. **Strategy Pattern**: Multiple identification strategies can be combined
3. **Provider Registry**: Extensible search provider system
4. **Async/Await**: Non-blocking I/O for better performance
5. **Rich CLI**: User-friendly terminal output with progress indicators

## Contributing

When adding new features:
1. Follow the existing module structure
2. Add new search providers to `swhpi/search/providers.py`
3. Add new strategies to `swhpi/search/strategies.py`
4. Update tests in `tests/test_identification.py`
5. Use type hints and docstrings