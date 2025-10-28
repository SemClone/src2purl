# SRC2PURL - Source Code to Package URL

A Python tool that identifies package coordinates (name, version, license, PURL) from source code directories using an hybrid discovery strategy with manifest parsing, code fingerprinting, repository search, and Software Heritage archive.

## Overview

src2purl uses a **progressive 2-phase discovery strategy** to identify packages:

### **Phase 1: Hash-based Package Discovery** (5-15 seconds)
**Primary identification using content fingerprinting and repository search:**

1. **Directory & Content Scanning** - Generate SWHIDs for directories and files
   - ✅ **Complete file tree analysis** with configurable depth
   - ✅ **SWHID generation** for precise content identification
   - ✅ **Smart filtering** of binary files and hidden directories

2. **Software Heritage Archive** (Optional) - Deep provenance discovery
   - ✅ **Most comprehensive** - finds exact source code matches
   - ✅ **Historical accuracy** - can identify older versions
   - ⚠️ **Requires opt-in** with `--use-swh` due to longer processing time

3. **Keyword Search** (Fallback) - Multi-platform repository discovery
   - **GitHub API Search** - Repository identification by keywords
   - **SCANOSS Fingerprinting** - Code similarity detection via file fingerprints
   - ✅ **Universal coverage** - finds repositories for any project
   - ✅ **Fast execution** (~10 seconds total)

### **Phase 2: Manifest-based Validation & Enhancement** (1-3 seconds)
**Authoritative package metadata extraction and result enhancement:**

4. **UPMEX Manifest Parsing** - Universal Package Metadata Extractor
   - ✅ **Perfect metadata extraction** from package files (package.json, setup.py, pom.xml, go.mod, Cargo.toml, etc.)
   - ✅ **Multi-ecosystem support** (PyPI, NPM, Maven, Go, Ruby Gems, PHP, .NET)
   - ✅ **Complete package info** (name, version, license, PURL)
   - ✅ **Cross-validation** with Phase 1 results for enhanced accuracy

## Features

### **Core Capabilities**
- **2-Phase Discovery Strategy**: Hash-based identification enhanced by manifest parsing
- **Multi-Ecosystem Support**: PyPI, NPM, Maven, Go, Ruby Gems, PHP, .NET, and more
- **Cross-Phase Validation**: UPMEX manifest data validates and enhances hash-based findings
- **Confidence Scoring**: Multi-factor scoring (85-100% for exact matches)
- **Package Coordinate Extraction**: Complete metadata (name, version, license, PURL)

### **Performance & Reliability**
- **Fast by Default**: 5-15 seconds for typical projects (vs 90+ seconds with SWH)
- **No API Keys Required**: Works well without authentication (SCANOSS, GitHub search)
- **Optional API Keys**: Enhanced rate limits and accuracy with GitHub/SCANOSS tokens
- **Persistent Caching**: File-based cache with smart TTL to avoid API rate limits
- **Rate Limit Handling**: Automatic backoff and retry logic

### **Discovery Methods**
- **UPMEX Manifest Parsing**: Universal Package Metadata Extractor for all major package ecosystems
- **SCANOSS Fingerprinting**: 100% accuracy code similarity with detailed license detection
- **GitHub Repository Search**: Universal coverage repository identification
- **Software Heritage Archive**: Comprehensive source inventory (opt-in with `--use-swh`)

### **Output & Integration**
- **Multiple Output Formats**: JSON and table output formats
- **PURL Generation**: Standard Package URLs for identified packages
- **Enhanced License Detection**: Integration with oslili for improved license detection
- **Subcomponent Detection**: Identifies multiple packages within monorepos and complex projects

## Installation

### From Source

```bash
git clone https://github.com/oscarvalenzuelab/src2purl.git
cd src2purl
pip install -e .
```


## Usage

### Basic Usage

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

# Skip license detection (faster)
src2purl /path/to/source --no-license-detection

# Verbose output for debugging
src2purl /path/to/source --verbose

# Clear cache and exit
src2purl --clear-cache
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

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the LICENSE file for details.

## Status

This project is currently in active development. See the [Issues](https://github.com/oscarvalenzuelab/src2purl/issues) page for planned features and known issues.
