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

# Disable fuzzy matching for speed
swhpi /path/to/source --no-fuzzy

# Verbose output for debugging
swhpi /path/to/source --verbose
```

### Command Line Options

- `path`: Directory path to analyze (required)
- `--max-depth`: Maximum parent directory levels to scan (default: 2)
- `--confidence-threshold`: Minimum confidence to report matches (default: 0.3)
- `--output-format`: Output format: 'json' or 'table' (default: table)
- `--no-fuzzy`: Disable fuzzy matching for faster execution
- `--cache`: Enable/disable API response caching (default: enabled)
- `--verbose`: Verbose output for debugging

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Software Heritage](https://www.softwareheritage.org/) for the amazing archive
- The open source community for continuous inspiration

## Status

This project is currently in active development. See the [Issues](https://github.com/oscarvalenzuelab/semantic-copycat-swh/issues) page for planned features and known issues.