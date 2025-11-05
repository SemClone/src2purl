# SRC2PURL - Source Code to Package URL Discovery

[![License](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://opensource.org/licenses/AGPL-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/src2purl.svg)](https://pypi.org/project/src2purl/)

A Python tool that identifies package coordinates (name, version, license, PURL) from source code directories using a hybrid discovery strategy with manifest parsing, code fingerprinting, repository search, and Software Heritage archive integration.

## Features

- **2-Phase Discovery Strategy**: Hash-based identification enhanced by manifest parsing
- **Multi-Ecosystem Support**: PyPI, NPM, Maven, Go, Ruby Gems, PHP, .NET, and more
- **Fast Performance**: 5-15 seconds for typical projects (vs 90+ seconds with SWH)
- **SEMCL.ONE Integration**: Works seamlessly with upmex, osslili, and other ecosystem tools

## Installation

```bash
pip install src2purl
```

For development:
```bash
git clone https://github.com/SemClone/src2purl.git
cd src2purl
pip install -e .
```

## Quick Start

```bash
# Identify package from source code
src2purl /path/to/source/code

# With Software Heritage archive (comprehensive but slower)
src2purl /path/to/source --use-swh
```


## Usage

### CLI Usage

```bash
# Fast discovery (default) - Uses manifest parsing + SCANOSS + GitHub (5-15 seconds)
src2purl /path/to/source/code

# Comprehensive discovery - Includes Software Heritage archive (90+ seconds)
src2purl /path/to/source --use-swh

# High confidence matches only
src2purl /path/to/source --confidence-threshold 0.85

# JSON output format for integration
src2purl /path/to/source --output-format json

# Detect subcomponents in monorepos
src2purl /path/to/source --detect-subcomponents
```

### Python API

```python
from src2purl import identify_package

# Basic identification
result = identify_package("/path/to/source")
print(f"Package: {result.name}@{result.version}")
print(f"PURL: {result.purl}")

# With options
result = identify_package(
    path="/path/to/source",
    use_swh=True,
    confidence_threshold=0.85
)
```

### Discovery Strategy Examples

```bash
# Default: 2-Phase hybrid approach (5-15 seconds)
# Phase 1: Hash-based discovery + Phase 2: UPMEX manifest parsing
# Good for: Most use cases, balanced speed and accuracy
src2purl /path/to/project

# Comprehensive: Include Software Heritage archive (90+ seconds)
# Phase 1 includes deep provenance discovery + Phase 2: UPMEX enhancement
# Good for: Security audits, research, historical analysis
export SWH_API_TOKEN=your_token  # Optional but recommended
src2purl /path/to/project --use-swh

# High confidence: Only report confident matches
# Filters results to highest confidence findings from both phases
src2purl /path/to/project --confidence-threshold 0.85
```

### API Authentication

**⚠️ No API keys required!** The tool works with the free public APIs. API keys only provide enhanced rate limits and additional features.

#### Recommended API Keys (Optional)

**1. GitHub API** - **Most Valuable** (Free, 2 minutes to setup)
```bash
export GITHUB_TOKEN=your_github_personal_access_token
```
- **Get token**: https://github.com/settings/tokens (no special permissions needed)
- **Benefits**:
  - ✅ **Rate limit**: 10 → 5000 requests/hour
  - ✅ **Better search**: More accurate repository identification
  - ✅ **No cost**: Completely free
- **Impact**: Significant improvement for repository discovery

**2. SCANOSS API** - **Nice to Have** (Free, optional)
```bash
export SCANOSS_API_KEY=your_scanoss_key
```
- **Get token**: Register at https://www.scanoss.com
- **Benefits**:
  - ✅ **No cost**: Free tier available
  - ✅ **Enhanced rate limits**: Premium API endpoint
  - ✅ **Additional features**: Possible extra metadata
- **Impact**: Minor improvement (SCANOSS works great without key)

**3. Software Heritage API** - **For Heavy Usage** (Free, only if using `--use-swh`)
```bash
export SWH_API_TOKEN=your_swh_token
```
- **Get token**: Register at https://archive.softwareheritage.org/api/
- **Benefits**:
  - ✅ **Bypass rate limits**: No 60-second waits
  - ✅ **Faster comprehensive scans**: When using `--use-swh`
- **Impact**: Essential for `--use-swh` flag, not needed for default fast mode

#### Performance Comparison

| Configuration | Typical Time | API Calls | Best For |
|---------------|-------------|-----------|----------|
| **No API keys** | 5-15 seconds | Minimal | Most users |
| **+ GitHub token** | 5-15 seconds | Enhanced | Recommended setup |
| **+ All tokens** | 5-15 seconds | Premium | Production use |
| **+ SWH mode** | 90+ seconds | Heavy | Security audits |

**Recommendation**: Start with **GitHub token only** - it's free, fast to setup, and provides the biggest improvement.

### SWHID Validation

```bash
# Generate and validate SWHID for a directory
src2purl-validate /path/to/directory

# Compare against expected SWHID
src2purl-validate /path/to/directory --expected-swhid swh:1:dir:abc123...

# Use fallback implementation
src2purl-validate /path/to/directory --use-fallback --verbose
```

### Command Line Options

#### **Core Options**
- `path`: Directory path to analyze (required)
- `--confidence-threshold`: Minimum confidence to report matches (default: 0.3)
- `--output-format`: Output format: 'json' or 'table' (default: table)
- `--verbose`: Verbose output for debugging

#### **Discovery Control**
- `--use-swh`: Include Software Heritage archive checking (optional, adds 90+ seconds)
- `--no-license-detection`: Skip automatic license detection from local source (faster)
- `--detect-subcomponents`: Detect and identify subcomponents in monorepos
- `--max-depth`: Maximum directory depth to scan (default: 2)

#### **Performance & Caching**
- `--no-cache`: Disable API response caching
- `--clear-cache`: Clear all cached API responses and exit

#### **Authentication**
- `--api-token`: Software Heritage API token (only used with --use-swh)
- Environment variables: `GITHUB_TOKEN`, `SCANOSS_API_KEY`, `SWH_API_TOKEN`

#### **Discovery Method Breakdown**
```bash
# Default: 2-Phase Discovery (Hash-based + UPMEX manifest parsing)
src2purl /path/to/project

# Phase 1: SWHID generation → GitHub/SCANOSS search
# Phase 2: UPMEX manifest extraction → Cross-validation & enhancement

# Add Software Heritage for comprehensive provenance discovery
src2purl /path/to/project --use-swh

# Phase 1: SWHID generation → Software Heritage archive → Fallback search
# Phase 2: UPMEX manifest extraction → Cross-validation & enhancement

# Performance optimization options
src2purl /path/to/project --no-license-detection  # Skip license enhancement
src2purl /path/to/project --use-swh --verbose     # Full discovery with details
```

## Integration with SEMCL.ONE

SRC2PURL is a core component of the SEMCL.ONE ecosystem:

- Uses **upmex** for manifest parsing and package metadata extraction
- Integrates with **osslili** for enhanced license detection
- Provides PURLs for **purl2src** to download source packages
- Supports **purl2notices** for generating attribution documentation
- Enables **ospac** policy evaluation with identified packages

## Configuration

Configuration via environment variables:

```bash
# API tokens (optional but recommended)
export GITHUB_TOKEN=your_github_token
export SCANOSS_API_KEY=your_scanoss_key
export SWH_API_TOKEN=your_swh_token

# Performance settings
export SRC2PURL_CACHE_DIR=~/.cache/src2purl
export SRC2PURL_MAX_DEPTH=2
```

## Documentation

- [User Guide](docs/user-guide.md) - Comprehensive usage examples
- [API Reference](docs/api.md) - Python API documentation
- [Discovery Methods](docs/discovery-methods.md) - Detailed explanation of identification strategies
- [Examples](docs/examples.md) - Common use cases and workflows

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- Code of conduct
- Development setup
- Submitting pull requests
- Reporting issues

## Support

For support and questions:
- [GitHub Issues](https://github.com/SemClone/src2purl/issues) - Bug reports and feature requests
- [Documentation](https://github.com/SemClone/src2purl) - Complete project documentation
- [SEMCL.ONE Community](https://semcl.one) - Ecosystem support and discussions

## License

GNU Affero General Public License v3.0 (AGPL-3.0) - see [LICENSE](LICENSE) file for details.

## Authors

See [AUTHORS.md](AUTHORS.md) for a list of contributors.

---

*Part of the [SEMCL.ONE](https://semcl.one) ecosystem for comprehensive OSS compliance and code analysis.*
