# SRC2PURL User Guide

This guide provides comprehensive documentation for using SRC2PURL to identify package coordinates from source code directories.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Discovery Strategy](#discovery-strategy)
4. [Command Line Usage](#command-line-usage)
5. [Python API Usage](#python-api-usage)
6. [API Authentication](#api-authentication)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting](#troubleshooting)

## Installation

### From PyPI

```bash
pip install src2purl
```

### From Source

```bash
git clone https://github.com/SemClone/src2purl.git
cd src2purl
pip install -e .
```

### Dependencies

SRC2PURL requires Python 3.8 or higher. All dependencies are automatically installed via pip.

## Quick Start

### Basic Usage

```bash
# Identify package from source directory
src2purl /path/to/source/code

# With Software Heritage archive (slower but more comprehensive)
src2purl /path/to/source --use-swh

# High confidence matches only
src2purl /path/to/source --confidence-threshold 0.85
```

### Example Output

```
Package: requests
Version: 2.28.0
PURL: pkg:pypi/requests@2.28.0
License: Apache-2.0
Confidence: 95%
```

## Discovery Strategy

SRC2PURL uses a sophisticated 2-phase discovery approach:

### Phase 1: Hash-based Discovery

1. **SWHID Generation**: Creates Software Heritage ID from directory contents
2. **Repository Search**: Queries GitHub and SCANOSS APIs
3. **Software Heritage** (optional): Deep provenance analysis with `--use-swh`

### Phase 2: UPMEX Enhancement

1. **Manifest Parsing**: Extracts metadata from package manifests
2. **Cross-validation**: Validates Phase 1 findings
3. **Metadata Enhancement**: Enriches results with additional information

### Performance Comparison

| Mode | Time | Accuracy | Use Case |
|------|------|----------|----------|
| Default (Fast) | 5-15 seconds | High | Most projects |
| With SWH | 90+ seconds | Very High | Security audits |

## Command Line Usage

### Basic Commands

```bash
# Standard identification
src2purl /path/to/project

# With verbose output
src2purl /path/to/project --verbose

# JSON output format
src2purl /path/to/project --output-format json

# Save results to file
src2purl /path/to/project -o results.json
```

### Advanced Options

```bash
# Set confidence threshold
src2purl /path/to/project --confidence-threshold 0.85

# Detect subcomponents in monorepos
src2purl /path/to/project --detect-subcomponents

# Control scanning depth
src2purl /path/to/project --max-depth 2

# Skip license detection (faster)
src2purl /path/to/project --no-license-detection

# Clear cache
src2purl --clear-cache
```

### Working with Software Heritage

```bash
# Enable Software Heritage archive checking
src2purl /path/to/project --use-swh

# With API token for better rate limits
export SWH_API_TOKEN=your_token
src2purl /path/to/project --use-swh

# Validate SWHID
src2purl-validate /path/to/directory
```

## Python API Usage

### Basic Example

```python
from src2purl import identify_package

# Basic identification
result = identify_package("/path/to/source")
print(f"Package: {result.name}@{result.version}")
print(f"PURL: {result.purl}")
print(f"License: {result.license}")
print(f"Confidence: {result.confidence:.0%}")
```

### Advanced Usage

```python
from src2purl import identify_package

# With options
result = identify_package(
    path="/path/to/source",
    use_swh=True,  # Enable Software Heritage
    confidence_threshold=0.85,  # High confidence only
    detect_subcomponents=True,  # Find monorepo components
    verbose=True  # Detailed logging
)

# Access detailed results
if result.subcomponents:
    for component in result.subcomponents:
        print(f"  - {component.name}: {component.purl}")

# Check discovery methods used
for method in result.discovery_methods:
    print(f"Discovery method: {method}")
```

### Batch Processing

```python
from src2purl import identify_package
import json

projects = [
    "/path/to/project1",
    "/path/to/project2",
    "/path/to/project3"
]

results = []
for project_path in projects:
    result = identify_package(project_path)
    results.append({
        "path": project_path,
        "purl": result.purl,
        "confidence": result.confidence
    })

# Save results
with open("batch_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

## API Authentication

### GitHub Token (Recommended)

The GitHub token provides the most value and is free to obtain:

1. Go to https://github.com/settings/tokens
2. Generate a new token (no special permissions needed)
3. Set the environment variable:

```bash
export GITHUB_TOKEN=your_github_personal_access_token
```

Benefits:
- Rate limit increases from 10 to 5000 requests/hour
- More accurate repository identification
- Better search results

### SCANOSS API Key (Optional)

```bash
export SCANOSS_API_KEY=your_scanoss_key
```

Register at https://www.scanoss.com for a free API key.

### Software Heritage Token (For --use-swh)

```bash
export SWH_API_TOKEN=your_swh_token
```

Register at https://archive.softwareheritage.org/api/

## Performance Optimization

### Caching

SRC2PURL caches API responses to improve performance:

```bash
# Default cache location: ~/.cache/src2purl
src2purl /path/to/project

# Disable cache
src2purl /path/to/project --no-cache

# Clear cache
src2purl --clear-cache
```

### Performance Tips

1. **Use GitHub token**: Dramatically improves API rate limits
2. **Avoid --use-swh for speed**: Only use when comprehensive analysis needed
3. **Skip license detection**: Use `--no-license-detection` for faster scans
4. **Limit depth**: Use `--max-depth 1` for shallow scans
5. **Cache results**: Let caching work for repeated scans

### Typical Performance

| Project Size | Default Mode | With SWH |
|-------------|--------------|----------|
| Small (100 files) | 5-8 seconds | 90+ seconds |
| Medium (1000 files) | 10-15 seconds | 120+ seconds |
| Large (5000+ files) | 15-25 seconds | 180+ seconds |

## Troubleshooting

### Common Issues

#### No Package Identified

```bash
# Increase verbosity to see what's happening
src2purl /path/to/project --verbose

# Try with Software Heritage
src2purl /path/to/project --use-swh

# Lower confidence threshold
src2purl /path/to/project --confidence-threshold 0.3
```

#### Rate Limiting

```
Error: API rate limit exceeded
```

Solution: Add API tokens (especially GitHub token):
```bash
export GITHUB_TOKEN=your_token
src2purl /path/to/project
```

#### Slow Performance

```bash
# Skip license detection
src2purl /path/to/project --no-license-detection

# Reduce scanning depth
src2purl /path/to/project --max-depth 1

# Ensure caching is enabled
src2purl /path/to/project  # Cache is enabled by default
```

### Debug Mode

For detailed debugging information:

```bash
# Maximum verbosity
src2purl /path/to/project --verbose

# With Python logging
PYTHONPATH=. python -m src2purl --verbose /path/to/project
```

### Getting Help

```bash
# Show help message
src2purl --help

# Check version
src2purl --version
```

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Identify Package
  run: |
    pip install src2purl
    src2purl . --output-format json -o package-info.json
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitLab CI

```yaml
identify-package:
  script:
    - pip install src2purl
    - src2purl . --output-format json -o package-info.json
  artifacts:
    paths:
      - package-info.json
```

## Best Practices

1. **Always use GitHub token**: Free and provides significant benefits
2. **Start with default mode**: Only use `--use-swh` when needed
3. **Cache API responses**: Default caching improves repeat performance
4. **Use confidence thresholds**: Filter results based on your needs
5. **Process in batches**: Use Python API for multiple projects
6. **Monitor rate limits**: Check API usage if processing many projects

## Further Reading

- [API Reference](api.md) - Detailed Python API documentation
- [Discovery Methods](discovery-methods.md) - In-depth explanation of identification strategies
- [Examples](examples.md) - More code examples and use cases