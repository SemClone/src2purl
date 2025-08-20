# SRC2ID - Source Code to ID

A Python tool that identifies package coordinates (name, version, license, PURL) from source code directories using multiple identification strategies including web search, SCANOSS fingerprinting, and optionally Software Heritage archive.

## Overview

src2id helps you identify packages in unknown code by:
1. Using multiple identification strategies (hash search, web search, SCANOSS)
2. Generating Software Heritage Identifiers (SWHIDs) for content hashing
3. Searching across GitHub, Google, and other sources for matching code
4. SCANOSS fingerprinting for code similarity detection
5. Providing confidence scores and Package URLs (PURLs) for identified packages
6. Optionally querying Software Heritage archive (with --use-swh flag)

## Features

- **Multiple Identification Strategies**: Hash search, web search (GitHub, Google), SCANOSS fingerprinting
- **Subcomponent Detection**: Identifies multiple packages within monorepos and complex projects
- **API-Conscious**: Optimized strategy order to minimize API calls
- **30x Faster**: Performance optimized compared to SWH-only approach
- **Exact Matching**: Find exact matches using content-based hashing (SWHIDs)
- **Confidence Scoring**: Multi-factor scoring for match reliability
- **Package Coordinate Extraction**: Extract name, version, and license information
- **PURL Generation**: Generate standard Package URLs for identified packages
- **Persistent Caching**: File-based cache with 24-hour TTL to avoid API rate limits
- **Enhanced License Detection**: Integration with oslili for improved license detection
- **Multiple Output Formats**: JSON and table output formats
- **Software Heritage Optional**: SWH archive querying available with --use-swh flag

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
# Identify packages in a directory
src2id /path/to/source/code

# High confidence matches only
src2id /path/to/source --confidence-threshold 0.85

# JSON output format
src2id /path/to/source --output-format json

# Include Software Heritage checking
src2id /path/to/source --use-swh

# Detect subcomponents in monorepos
src2id /path/to/source --detect-subcomponents

# Skip license detection
src2id /path/to/source --no-license-detection

# Use API token for SWH authentication (when using --use-swh)
src2id /path/to/source --use-swh --api-token YOUR_TOKEN

# Or set via environment variable
export SWH_API_TOKEN=YOUR_TOKEN
src2id /path/to/source --use-swh

# Clear cache and exit
src2id --clear-cache

# Verbose output for debugging
src2id /path/to/source --verbose
```

### API Authentication

#### Software Heritage (Optional)
When using `--use-swh`, you can provide a Software Heritage API token:

1. **Get an API token**: Register at https://archive.softwareheritage.org/api/ and generate a token
2. **Use the token**: 
   - Via command line: `--use-swh --api-token YOUR_TOKEN`
   - Via environment variable: `export SWH_API_TOKEN=YOUR_TOKEN`

#### Other APIs

The tool can use several APIs for enhanced functionality. All are optional:

**GitHub API** (Recommended - Free)
```bash
export GITHUB_TOKEN=your_github_personal_access_token
```
- Creates at: https://github.com/settings/tokens
- Increases rate limit from 10 to 30 requests/minute
- Improves repository search accuracy

**SCANOSS API** (Optional - Free)
```bash
export SCANOSS_API_KEY=your_scanoss_key
```
- Register at: https://www.scanoss.com
- Provides code fingerprinting and similarity detection
- Works without key but with rate limits

**SerpAPI** (Optional - Paid)
```bash
export SERPAPI_KEY=your_serpapi_key
```
- Sign up at: https://serpapi.com
- Enables Google search for code matching
- Requires paid subscription

Note: The tool works well without any API keys, just with reduced rate limits.

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

- `path`: Directory path to analyze (required)
- `--max-depth`: Maximum directory depth to scan (default: 3)
- `--confidence-threshold`: Minimum confidence to report matches (default: 0.3)
- `--output-format`: Output format: 'json' or 'table' (default: table)
- `--use-swh`: Include Software Heritage archive checking (optional, slower)
- `--detect-subcomponents`: Detect and identify subcomponents in monorepos
- `--no-cache`: Disable API response caching
- `--clear-cache`: Clear all cached API responses and exit
- `--no-license-detection`: Skip automatic license detection from local source
- `--api-token`: Software Heritage API token (only used with --use-swh)
- `--verbose`: Verbose output for debugging

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the LICENSE file for details.

## Status

This project is currently in active development. See the [Issues](https://github.com/oscarvalenzuelab/semantic-copycat-src2id/issues) page for planned features and known issues.