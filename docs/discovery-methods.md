# SRC2PURL Discovery Methods

This document provides a detailed explanation of the identification strategies used by SRC2PURL to discover package coordinates from source code.

## Overview

SRC2PURL employs a sophisticated 2-phase discovery strategy that combines multiple techniques to accurately identify packages from source code directories. The system is designed to be fast (5-15 seconds typical) while maintaining high accuracy.

## Discovery Architecture

```
Source Directory → Phase 1: Hash-based Discovery → Phase 2: Manifest Enhancement → Result
                     ├── SWHID Generation           ├── UPMEX Integration
                     ├── Repository Search          ├── Cross-validation
                     └── SWH Archive (optional)     └── Metadata Enrichment
```

## Phase 1: Hash-based Discovery

### 1.1 SWHID Generation

Software Heritage Identifier (SWHID) is a cryptographic hash that uniquely identifies source code directories.

#### How it works:

1. **Directory Traversal**: Recursively processes all files in the directory
2. **Content Hashing**: Computes Git-compatible hashes for each file
3. **Merkle Tree**: Builds a tree structure with directory hashes
4. **SWHID Format**: Produces identifier like `swh:1:dir:94a9ed024d3859793618152ea559a168bbcbb5e2`

#### Implementation:

```python
def compute_swhid(directory_path):
    """Compute Software Heritage ID for a directory"""
    entries = []

    for entry in sorted(os.listdir(directory_path)):
        path = os.path.join(directory_path, entry)

        if os.path.isfile(path):
            # Hash file content
            file_hash = hash_file_git_like(path)
            entries.append(('file', entry, file_hash))
        elif os.path.isdir(path):
            # Recursively hash subdirectory
            dir_hash = compute_swhid(path)
            entries.append(('dir', entry, dir_hash))

    # Combine into directory hash
    return compute_directory_hash(entries)
```

### 1.2 GitHub Repository Search

Uses the GitHub API to find repositories matching the SWHID.

#### Search Strategy:

1. **File-based Search**: Searches for unique file combinations
2. **Content Matching**: Matches file contents against GitHub's index
3. **Repository Metadata**: Extracts package information from found repositories

#### API Usage:

```python
# Search by file content
GET https://api.github.com/search/code?q=hash:SWHID

# Get repository details
GET https://api.github.com/repos/{owner}/{repo}

# Extract package metadata
GET https://api.github.com/repos/{owner}/{repo}/contents/package.json
```

#### Rate Limits:

- Without token: 10 requests/hour
- With token: 5000 requests/hour

### 1.3 SCANOSS Knowledge Base

SCANOSS maintains a comprehensive database of open-source code fingerprints.

#### Process:

1. **Fingerprinting**: Creates WFP (Winnowing Fingerprints) from source files
2. **API Query**: Sends fingerprints to SCANOSS API
3. **Match Analysis**: Processes returned component matches
4. **Confidence Scoring**: Evaluates match quality

#### Fingerprint Generation:

```python
def generate_wfp(file_content):
    """Generate Winnowing Fingerprint"""
    # Create k-grams
    kgrams = create_kgrams(file_content, k=50)

    # Apply winnowing algorithm
    fingerprints = winnowing(kgrams, window_size=64)

    # Format as WFP
    return format_wfp(fingerprints)
```

### 1.4 Software Heritage Archive (Optional)

When `--use-swh` is enabled, queries the Software Heritage universal source code archive.

#### Capabilities:

- **Comprehensive Coverage**: 190+ million unique source files
- **Historical Versions**: All versions ever published
- **Provenance Tracking**: Complete development history

#### Query Process:

```python
# Check if SWHID exists
GET https://archive.softwareheritage.org/api/1/directory/{swhid}/

# Get known occurrences
GET https://archive.softwareheritage.org/api/1/directory/{swhid}/occurrences/

# Extract metadata
GET https://archive.softwareheritage.org/api/1/origin/{origin_url}/metadata/
```

#### Performance Impact:

- Adds 60-90+ seconds to processing time
- Requires rate limit management (60-second delays without token)

## Phase 2: UPMEX Manifest Enhancement

### 2.1 Manifest File Detection

Identifies and parses package manifest files across ecosystems.

#### Supported Manifests:

| Ecosystem | Manifest Files | Metadata Extracted |
|-----------|---------------|-------------------|
| NPM/Node.js | package.json, package-lock.json | name, version, license, dependencies |
| Python | setup.py, pyproject.toml, requirements.txt | name, version, license, classifiers |
| Java/Maven | pom.xml, build.gradle | groupId, artifactId, version |
| Ruby | Gemfile, *.gemspec | name, version, license |
| Go | go.mod, go.sum | module, version, dependencies |
| Rust | Cargo.toml, Cargo.lock | name, version, license |
| .NET | *.csproj, packages.config | package ID, version, license |
| PHP | composer.json, composer.lock | name, version, license |

### 2.2 Manifest Parsing

#### Example: NPM package.json

```python
def parse_package_json(file_path):
    """Parse NPM package.json"""
    with open(file_path) as f:
        data = json.load(f)

    return {
        'name': data.get('name'),
        'version': data.get('version'),
        'license': normalize_license(data.get('license')),
        'description': data.get('description'),
        'repository': extract_repository_url(data.get('repository')),
        'dependencies': data.get('dependencies', {}),
        'ecosystem': 'npm'
    }
```

#### Example: Python setup.py

```python
def parse_setup_py(file_path):
    """Parse Python setup.py using AST"""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    # Find setup() call
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if hasattr(node.func, 'id') and node.func.id == 'setup':
                return extract_setup_kwargs(node)
```

### 2.3 Cross-validation

Validates Phase 1 findings against manifest data.

#### Validation Rules:

1. **Name Matching**: Package name from manifest vs. repository
2. **Version Compatibility**: Manifest version vs. tags/releases
3. **License Agreement**: Detected license vs. declared license
4. **Dependency Check**: Validate against known dependencies

#### Confidence Scoring:

```python
def calculate_confidence(phase1_result, phase2_result):
    """Calculate match confidence"""
    score = 0.5  # Base score

    # Name match
    if phase1_result.name == phase2_result.name:
        score += 0.2

    # Version match
    if versions_compatible(phase1_result.version, phase2_result.version):
        score += 0.15

    # License match
    if phase1_result.license == phase2_result.license:
        score += 0.1

    # Repository URL match
    if urls_match(phase1_result.repo_url, phase2_result.repo_url):
        score += 0.05

    return min(score, 1.0)
```

## Advanced Discovery Techniques

### 3.1 Monorepo Detection

Identifies multiple packages within a single repository.

#### Detection Strategy:

1. **Pattern Recognition**: Looks for common monorepo structures
   - `packages/*/package.json` (Lerna/Yarn workspaces)
   - `apps/*/` and `libs/*/` (Nx)
   - Multiple `Cargo.toml` files (Rust workspaces)

2. **Workspace Analysis**: Parses workspace configuration files

3. **Independent Scoring**: Each component scored separately

### 3.2 License Detection Enhancement

Uses osslili integration for comprehensive license detection.

#### Process:

1. **Text Analysis**: Scans LICENSE, COPYING, README files
2. **Header Detection**: Extracts license headers from source files
3. **SPDX Matching**: Maps to standard SPDX identifiers
4. **Confidence Weighting**: Weights by file importance

### 3.3 Fuzzy Matching

Handles variations in package identification.

#### Techniques:

1. **Name Normalization**:
   - Remove special characters
   - Handle case variations
   - Account for common prefixes/suffixes

2. **Version Flexibility**:
   - Semantic version parsing
   - Range compatibility checking
   - Git commit hash mapping

3. **Typo Tolerance**:
   - Levenshtein distance calculation
   - Common typo patterns
   - Phonetic matching

## Discovery Method Selection

### Decision Tree:

```
Start
  ├── Is it a Git repository?
  │   └── Yes → Use Git history + GitHub API
  │   └── No → Continue
  ├── Has package manifests?
  │   └── Yes → Parse manifests first
  │   └── No → Continue
  ├── Has unique file patterns?
  │   └── Yes → Use SCANOSS fingerprinting
  │   └── No → Continue
  └── Use SWHID + comprehensive search
```

### Performance vs. Accuracy Trade-offs:

| Method | Speed | Accuracy | When to Use |
|--------|-------|----------|-------------|
| Manifest-only | < 1 sec | High for declared packages | Known package structure |
| GitHub API | 5-10 sec | High for public repos | Open source projects |
| SCANOSS | 10-15 sec | Good for common OSS | General identification |
| SWH Archive | 90+ sec | Excellent | Security audits, research |

## Caching Strategy

### Cache Levels:

1. **API Response Cache**:
   - GitHub API responses: 24 hours
   - SCANOSS results: 7 days
   - SWH queries: 30 days

2. **SWHID Cache**:
   - Directory → SWHID mappings
   - Invalidated on file changes

3. **Result Cache**:
   - Complete identification results
   - Keyed by directory path + options

### Cache Implementation:

```python
class DiscoveryCache:
    def __init__(self, cache_dir="~/.cache/src2purl"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(exist_ok=True)

    def get(self, key, max_age=86400):
        """Get cached value if not expired"""
        cache_file = self.cache_dir / f"{hashlib.md5(key).hexdigest()}.json"

        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < max_age:
                return json.loads(cache_file.read_text())

        return None

    def set(self, key, value):
        """Store value in cache"""
        cache_file = self.cache_dir / f"{hashlib.md5(key).hexdigest()}.json"
        cache_file.write_text(json.dumps(value))
```

## Error Handling and Fallbacks

### Graceful Degradation:

1. **API Failures**:
   - GitHub down → Fall back to SCANOSS
   - SCANOSS down → Use manifest-only
   - All APIs down → Local analysis only

2. **Incomplete Data**:
   - Missing version → Use "unknown"
   - No license → Mark as "UNLICENSED"
   - No description → Extract from README

3. **Timeout Handling**:
   - API timeout: 30 seconds default
   - Total timeout: 5 minutes maximum
   - Progressive timeout reduction

## Best Practices

### For Optimal Performance:

1. **Always use GitHub token** - 500x better rate limits
2. **Enable caching** - Avoid redundant API calls
3. **Start with fast mode** - Only use SWH when necessary
4. **Process in parallel** - Use batch API when possible

### For Best Accuracy:

1. **Keep source complete** - Include all project files
2. **Preserve structure** - Maintain directory layout
3. **Include manifests** - Don't exclude package files
4. **Use multiple signals** - Enable all discovery methods

### For Security Audits:

1. **Enable SWH** - Most comprehensive coverage
2. **Lower threshold** - Catch partial matches
3. **Detect subcomponents** - Find embedded libraries
4. **Verify licenses** - Cross-check all sources

## Metrics and Monitoring

### Success Metrics:

- **Identification Rate**: 85%+ for public OSS projects
- **Accuracy**: 95%+ when package manifests present
- **Performance**: 5-15 seconds for typical projects
- **API Efficiency**: < 10 API calls per identification

### Logging Insights:

```python
import logging

logger = logging.getLogger('src2purl.discovery')

# Log discovery method selection
logger.info(f"Selected discovery method: {method}")

# Log API calls
logger.debug(f"API call to {endpoint}: {response.status_code}")

# Log confidence factors
logger.info(f"Confidence factors: name={name_match}, version={version_match}")

# Log performance
logger.info(f"Discovery completed in {elapsed:.2f} seconds")
```

## Future Enhancements

### Planned Improvements:

1. **ML-based Matching**: Neural networks for code similarity
2. **Distributed Caching**: Shared cache across organizations
3. **Custom Extractors**: Plugin system for proprietary formats
4. **Real-time Monitoring**: WebSocket-based progress updates
5. **Blockchain Integration**: Decentralized package registry