# Software Heritage Package Identifier (SWHPI)

A Python tool that identifies package coordinates (name, version, license, PURL) from source code directories by leveraging Software Heritage archive content-addressable hashing and origin metadata.

## Overview

SWHPI helps you identify packages in unknown code by:
1. Generating Software Heritage Identifiers (SWHIDs) from local directories
2. Querying the Software Heritage archive to find matching content
3. Extracting package information from the archive metadata
4. Providing confidence scores and Package URLs (PURLs) for identified packages

## Features

- **Exact Matching**: Find exact matches using content-based hashing (SWHIDs)
- **Subdirectory Matching**: Identifies packages even when only subdirectories match
- **Confidence Scoring**: Multi-factor scoring for match reliability
- **Package Coordinate Extraction**: Extract name, version, and license information
- **PURL Generation**: Generate standard Package URLs for high-confidence matches
- **Performance Optimized**: Parent-first scanning and intelligent caching
- **Persistent Caching**: File-based cache with 24-hour TTL to avoid API rate limits
- **SWHID Validation**: Built-in tool to validate and compare SWHID generation
- **Enhanced License Detection**: Optional integration with oslili for improved license detection
- **Multiple Output Formats**: JSON and table output formats
- **Timeout Handling**: Clear error messages for network issues and API timeouts

## Installation

### From Source

```bash
git clone https://github.com/oscarvalenzuelab/semantic-copycat-swh.git
cd semantic-copycat-swh
pip install -e .
```


## Usage

### Basic Usage

```bash
# Identify packages in a directory
swhpi /path/to/source/code

# High confidence matches only
swhpi /path/to/source --confidence-threshold 0.85

# JSON output format
swhpi /path/to/source --output-format json

# Enable fuzzy matching (keyword search)
swhpi /path/to/source --enable-fuzzy

# Skip license detection
swhpi /path/to/source --no-license-detection

# Use API token for authentication (bypasses rate limits)
swhpi /path/to/source --api-token YOUR_TOKEN

# Or set via environment variable
export SWH_API_TOKEN=YOUR_TOKEN
swhpi /path/to/source

# Clear cache and exit
swhpi --clear-cache

# Verbose output for debugging
swhpi /path/to/source --verbose
```

### API Authentication

To bypass rate limits and get better performance, you can use a Software Heritage API token:

1. **Get an API token**: Register at https://archive.softwareheritage.org/api/ and generate a token
2. **Use the token**: 
   - Via command line: `--api-token YOUR_TOKEN`
   - Via environment variable: `export SWH_API_TOKEN=YOUR_TOKEN`

Benefits of using API authentication:
- No rate limiting
- Faster API responses
- Higher request quotas
- Access to additional API endpoints

### SWHID Validation

```bash
# Generate and validate SWHID for a directory
python -m swhpi.cli.validate /path/to/directory

# Compare against expected SWHID
python -m swhpi.cli.validate /path/to/directory --expected-swhid swh:1:dir:abc123...

# Use fallback implementation
python -m swhpi.cli.validate /path/to/directory --use-fallback --verbose
```

### Command Line Options

- `path`: Directory path to analyze (required)
- `--max-depth`: Maximum parent directory levels to scan (default: 2)
- `--confidence-threshold`: Minimum confidence to report matches (default: 0.3)
- `--output-format`: Output format: 'json' or 'table' (default: table)
- `--enable-fuzzy`: Enable fuzzy matching (keyword search) when exact matches fail
- `--no-cache`: Disable API response caching
- `--clear-cache`: Clear all cached API responses and exit
- `--no-license-detection`: Skip automatic license detection from local source
- `--api-token`: Software Heritage API token for authentication
- `--verbose`: Verbose output for debugging

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the LICENSE file for details.

## Status

This project is currently in active development. See the [Issues](https://github.com/oscarvalenzuelab/semantic-copycat-swh/issues) page for planned features and known issues.