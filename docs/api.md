# SRC2PURL API Reference

Complete API documentation for the SRC2PURL Python library.

## Core Functions

### `identify_package()`

Main function for identifying packages from source code.

```python
identify_package(
    path: str,
    use_swh: bool = False,
    confidence_threshold: float = 0.3,
    detect_subcomponents: bool = False,
    max_depth: int = 2,
    no_license_detection: bool = False,
    verbose: bool = False,
    no_cache: bool = False,
    api_token: str = None
) -> PackageIdentification
```

#### Parameters

- **path** (str): Path to source code directory to analyze
- **use_swh** (bool): Enable Software Heritage archive checking (default: False)
- **confidence_threshold** (float): Minimum confidence score (0.0-1.0, default: 0.3)
- **detect_subcomponents** (bool): Detect components in monorepos (default: False)
- **max_depth** (int): Maximum directory traversal depth (default: 2)
- **no_license_detection** (bool): Skip license detection (default: False)
- **verbose** (bool): Enable verbose output (default: False)
- **no_cache** (bool): Disable caching (default: False)
- **api_token** (str): Software Heritage API token (default: None)

#### Returns

`PackageIdentification` object with package information.

#### Example

```python
from src2purl import identify_package

result = identify_package(
    "/path/to/project",
    confidence_threshold=0.85,
    verbose=True
)

print(f"Found: {result.name}@{result.version}")
```

## Data Classes

### `PackageIdentification`

Result object containing package identification information.

#### Attributes

- **name** (str): Package name
- **version** (str): Package version
- **purl** (str): Package URL (PURL)
- **license** (str): Detected license
- **confidence** (float): Confidence score (0.0-1.0)
- **ecosystem** (str): Package ecosystem (npm, pypi, maven, etc.)
- **description** (str): Package description
- **homepage** (str): Project homepage URL
- **repository_url** (str): Source repository URL
- **discovery_methods** (List[str]): Methods used for discovery
- **subcomponents** (List[PackageIdentification]): Detected subcomponents
- **metadata** (dict): Additional metadata

#### Methods

```python
# Convert to dictionary
result.to_dict() -> dict

# Convert to JSON
result.to_json() -> str

# Check if valid
result.is_valid() -> bool

# Get PURL object
result.get_purl() -> PackageURL
```

### `PackageURL`

PURL (Package URL) representation.

```python
from packageurl import PackageURL

purl = PackageURL(
    type='npm',
    namespace='@angular',
    name='core',
    version='12.0.0'
)

print(purl.to_string())
# pkg:npm/@angular/core@12.0.0
```

## Discovery Classes

### `HashBasedDiscovery`

Performs hash-based package discovery using SWHID.

```python
from src2purl.discovery import HashBasedDiscovery

discovery = HashBasedDiscovery()
result = discovery.identify(
    directory_path="/path/to/source",
    use_swh=False
)
```

### `ManifestDiscovery`

Extracts package information from manifest files.

```python
from src2purl.discovery import ManifestDiscovery

discovery = ManifestDiscovery()
result = discovery.extract_from_manifests("/path/to/source")
```

## Utility Functions

### `validate_swhid()`

Validate Software Heritage ID for a directory.

```python
from src2purl.utils import validate_swhid

swhid = validate_swhid(
    directory_path="/path/to/source",
    expected_swhid="swh:1:dir:abc123..."
)
print(f"Valid: {swhid.is_valid}")
```

### `clear_cache()`

Clear all cached API responses.

```python
from src2purl.cache import clear_cache

clear_cache()
print("Cache cleared")
```

### `get_cache_stats()`

Get cache usage statistics.

```python
from src2purl.cache import get_cache_stats

stats = get_cache_stats()
print(f"Cache size: {stats['size_mb']} MB")
print(f"Cache entries: {stats['entries']}")
```

## Configuration

### Environment Variables

Configure SRC2PURL using environment variables:

```python
import os

# Set API tokens from environment
os.environ['GITHUB_TOKEN'] = os.getenv('GITHUB_TOKEN')
os.environ['SCANOSS_API_KEY'] = os.getenv('SCANOSS_API_KEY')
os.environ['SWH_API_TOKEN'] = os.getenv('SWH_API_TOKEN')

# Set cache directory
os.environ['SRC2PURL_CACHE_DIR'] = '/custom/cache/path'

# Set default max depth
os.environ['SRC2PURL_MAX_DEPTH'] = '3'
```

### Configuration Object

```python
from src2purl.config import Config

config = Config(
    cache_dir="~/.cache/src2purl",
    max_depth=2,
    default_confidence_threshold=0.3,
    github_token=os.getenv('GITHUB_TOKEN'),
    scanoss_api_key=os.getenv('SCANOSS_API_KEY'),
    swh_api_token=os.getenv('SWH_API_TOKEN')
)

# Apply configuration
config.apply()
```

## Advanced Usage

### Custom Discovery Pipeline

```python
from src2purl import identify_package
from src2purl.discovery import DiscoveryPipeline

# Create custom pipeline
pipeline = DiscoveryPipeline()
pipeline.add_stage(HashBasedDiscovery())
pipeline.add_stage(ManifestDiscovery())
pipeline.add_stage(LicenseDiscovery())

# Run pipeline
result = pipeline.run("/path/to/source")
```

### Batch Processing with Parallelism

```python
from src2purl import identify_package
from concurrent.futures import ThreadPoolExecutor
import json

def process_project(path):
    try:
        result = identify_package(path)
        return {
            'path': path,
            'purl': result.purl,
            'confidence': result.confidence,
            'success': True
        }
    except Exception as e:
        return {
            'path': path,
            'error': str(e),
            'success': False
        }

# Process multiple projects in parallel
projects = [
    '/path/to/project1',
    '/path/to/project2',
    '/path/to/project3'
]

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_project, projects))

# Save results
with open('batch_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

### Custom Confidence Scoring

```python
from src2purl import identify_package

def custom_confidence_scorer(result):
    """Custom confidence scoring logic"""
    score = result.confidence

    # Boost confidence for certain ecosystems
    if result.ecosystem == 'npm':
        score *= 1.1

    # Reduce confidence for old versions
    if result.version and result.version.startswith('0.'):
        score *= 0.9

    return min(score, 1.0)

result = identify_package("/path/to/source")
custom_confidence = custom_confidence_scorer(result)
print(f"Custom confidence: {custom_confidence:.0%}")
```

### Integration with SEMCL.ONE Ecosystem

```python
from src2purl import identify_package
from purl2src import get_source_url
from osslili import detect_licenses

# Identify package
package = identify_package("/path/to/source")

# Get source download URL
source_url = get_source_url(package.purl)

# Detect licenses
licenses = detect_licenses("/path/to/source")

# Combine results
compliance_report = {
    'package': package.to_dict(),
    'source_url': source_url,
    'licenses': licenses
}
```

## Error Handling

### Exception Types

```python
from src2purl.exceptions import (
    Src2PurlException,
    DiscoveryException,
    ValidationException,
    APIException
)

try:
    result = identify_package("/path/to/source")
except DiscoveryException as e:
    print(f"Discovery failed: {e}")
except APIException as e:
    print(f"API error: {e}")
except Src2PurlException as e:
    print(f"General error: {e}")
```

### Error Recovery

```python
from src2purl import identify_package
import logging

logging.basicConfig(level=logging.INFO)

def safe_identify(path, fallback_methods=True):
    """Identify with fallback strategies"""
    try:
        # Try with full features
        return identify_package(path, use_swh=True)
    except Exception as e:
        logging.warning(f"Full identification failed: {e}")

        if fallback_methods:
            try:
                # Fallback to fast mode
                return identify_package(path, use_swh=False)
            except Exception as e2:
                logging.error(f"Fallback also failed: {e2}")
                # Return minimal result
                return PackageIdentification(
                    name="unknown",
                    confidence=0.0
                )
```

## Logging

### Configure Logging

```python
import logging
from src2purl import identify_package

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('src2purl.log'),
        logging.StreamHandler()
    ]
)

# Will now produce detailed logs
result = identify_package("/path/to/source", verbose=True)
```

### Custom Logger

```python
import logging
from src2purl import identify_package

# Create custom logger
logger = logging.getLogger('src2purl.custom')
logger.setLevel(logging.INFO)

# Custom handler
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Use with library
result = identify_package(
    "/path/to/source",
    logger=logger
)
```

## Testing

### Unit Testing

```python
import unittest
from src2purl import identify_package
from unittest.mock import patch, MagicMock

class TestSrc2Purl(unittest.TestCase):
    @patch('src2purl.api.github.search_repository')
    def test_identify_package(self, mock_search):
        # Mock API response
        mock_search.return_value = {
            'name': 'test-package',
            'version': '1.0.0'
        }

        result = identify_package('/path/to/test')

        self.assertEqual(result.name, 'test-package')
        self.assertEqual(result.version, '1.0.0')
        mock_search.assert_called_once()
```

### Integration Testing

```python
import tempfile
import json
from pathlib import Path
from src2purl import identify_package

def test_integration():
    # Create test project
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json
        package_json = Path(tmpdir) / 'package.json'
        package_json.write_text(json.dumps({
            'name': 'test-project',
            'version': '1.0.0',
            'license': 'MIT'
        }))

        # Test identification
        result = identify_package(tmpdir)

        assert result.name == 'test-project'
        assert result.version == '1.0.0'
        assert result.ecosystem == 'npm'
```

## Performance Profiling

```python
import cProfile
import pstats
from src2purl import identify_package

# Profile the identification
profiler = cProfile.Profile()
profiler.enable()

result = identify_package("/path/to/large/project")

profiler.disable()

# Print stats
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 time consumers
```

## Deprecation Notices

### Deprecated in v2.0

- `identify_from_hash()` - Use `identify_package()` instead
- `--json-output` flag - Use `--output-format json` instead

### Future Deprecations

- `--api-token` CLI flag - Use environment variables instead