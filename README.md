# SRC2ID - Source Code to Package ID

A Python tool that identifies package coordinates (name, version, license, PURL) from source code directories using an hybrid discovery strategy with manifest parsing, code fingerprinting, repository search, and Software Heritage archive.

## Overview

src2id uses a **progressive 4-tier discovery strategy** to identify packages:

### **Tier 1: Fast Manifest Discovery** (1-5 seconds)
1. **UPMEX/Manifest Parsing** - Extract declared dependencies from package files (package.json, setup.py, pom.xml, go.mod, Cargo.toml, etc.)
   - ✅ **Perfect metadata extraction** (85-95% confidence)
   - ✅ **Multi-ecosystem support** (PyPI, NPM, Maven, Go, Ruby Gems)
   - ✅ **Complete package info** (name, version, license, PURL)

### **Tier 2: Parallel Code Discovery** (5-15 seconds)
2. **SCANOSS Fingerprinting** - Code similarity detection via file fingerprints
   - ✅ **100% accuracy** when fingerprints exist in database
   - ✅ **Excellent license detection** with detailed SPDX information
   - ✅ **Works with any file type** (.c, .py, .cpp, .js, etc.)

3. **GitHub Repository Search** - Find repositories using project names and keywords
   - ✅ **Universal coverage** - finds repositories for any project
   - ✅ **Fast execution** (~10 seconds total)
   - ✅ **Good ecosystem identification**

### **Tier 3: Provenance Discovery** (Optional, 90+ seconds)
4. **Software Heritage Archive** - Deep source code inventory using content hashing
   - ✅ **Most comprehensive** - finds exact source code matches
   - ✅ **Historical accuracy** - can identify older versions
   - ⚠️ **Requires opt-in** with `--use-swh` due to rate limits

## Features

### **Core Capabilities**
- **Hybrid Discovery Strategy**: Progressive 4-tier approach (manifest → fingerprinting → search → archive)
- **Multi-Ecosystem Support**: PyPI, NPM, Maven, Go, Ruby Gems, and more
- **Cross-Method Validation**: SCANOSS confirms GitHub findings, UPMEX validates SCANOSS results
- **Confidence Scoring**: Multi-factor scoring (85-100% for exact matches)
- **Package Coordinate Extraction**: Complete metadata (name, version, license, PURL)

### **Performance & Reliability**
- **Fast by Default**: 5-15 seconds for typical projects (vs 90+ seconds with SWH)
- **No API Keys Required**: Works well without authentication (SCANOSS, GitHub search)
- **Optional API Keys**: Enhanced rate limits and accuracy with GitHub/SCANOSS tokens
- **Persistent Caching**: File-based cache with smart TTL to avoid API rate limits
- **Rate Limit Handling**: Automatic backoff and retry logic

### **Discovery Methods**
- **UPMEX/Manifest Parsing**: Extract from package.json, setup.py, pom.xml, go.mod, Cargo.toml, etc.
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
git clone https://github.com/oscarvalenzuelab/semantic-copycat-src2id.git
cd semantic-copycat-src2id
pip install -e .
```


## Usage

### Basic Usage

```bash
# Fast discovery (default) - Uses manifest parsing + SCANOSS + GitHub (5-15 seconds)
src2id /path/to/source/code

# Comprehensive discovery - Includes Software Heritage archive (90+ seconds)
src2id /path/to/source --use-swh

# High confidence matches only
src2id /path/to/source --confidence-threshold 0.85

# JSON output format for integration
src2id /path/to/source --output-format json

# Detect subcomponents in monorepos
src2id /path/to/source --detect-subcomponents

# Skip license detection (faster)
src2id /path/to/source --no-license-detection

# Verbose output for debugging
src2id /path/to/source --verbose

# Clear cache and exit
src2id --clear-cache
```

### Discovery Strategy Examples

```bash
# Speed-optimized: Manifest parsing only (1-3 seconds)
# Good for: Known projects with package files
src2id /path/to/npm-project  # Finds package.json automatically

# Balanced: Default hybrid approach (5-15 seconds)
# Good for: Most use cases, unknown projects
src2id /path/to/unknown-code

# Comprehensive: Include Software Heritage (90+ seconds)
# Good for: Security audits, research, modified code
export SWH_API_TOKEN=your_token  # Optional but recommended
src2id /path/to/unknown-code --use-swh
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
src2id-validate /path/to/directory

# Compare against expected SWHID
src2id-validate /path/to/directory --expected-swhid swh:1:dir:abc123...

# Use fallback implementation
src2id-validate /path/to/directory --use-fallback --verbose
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
# Default: UPMEX + SCANOSS + GitHub (fast)
src2id /path/to/project

# Add Software Heritage (comprehensive but slow)
src2id /path/to/project --use-swh

# Speed vs Comprehensiveness trade-off
src2id /path/to/project --no-license-detection  # Faster
src2id /path/to/project --use-swh --verbose     # Slower but complete
```

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the LICENSE file for details.

## Status

This project is currently in active development. See the [Issues](https://github.com/oscarvalenzuelab/semantic-copycat-src2id/issues) page for planned features and known issues.
