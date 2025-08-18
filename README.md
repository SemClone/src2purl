# SH Package Identifier (SHPI)

A Python tool that identifies package coordinates (name, version, license, PURL) from source code directories by leveraging Software Heritage (SH) archive content-addressable hashing and origin metadata.

## Overview

SHPI helps you identify packages in unknown code by:
1. Generating Software Heritage Identifiers (SWHIDs) from local directories
2. Querying the Software Heritage archive to find matching content
3. Extracting package information from the archive metadata
4. Providing confidence scores and Package URLs (PURLs) for identified packages

## Features

- 🔍 **Exact Matching**: Find exact matches using content-based hashing
- 🎯 **Confidence Scoring**: Multi-factor scoring for match reliability
- 📦 **Package Coordinate Extraction**: Extract name, version, and license information
- 🔗 **PURL Generation**: Generate standard Package URLs for high-confidence matches
- 🚀 **Performance Optimized**: Parent-first scanning and intelligent caching
- 📊 **Multiple Output Formats**: JSON and table output formats

## Installation

### From Source

```bash
git clone https://github.com/oscarvalenzuelab/semantic-copycat-swh.git
cd semantic-copycat-swh
pip install -e .
```

### For Development

```bash
pip install -e ".[dev]"
make install-dev
```

## Usage

### Basic Usage

```bash
# Identify packages in a directory
shpi /path/to/source/code

# High confidence matches only
shpi /path/to/source --confidence-threshold 0.85

# JSON output format
shpi /path/to/source --output-format json

# Disable fuzzy matching for speed
shpi /path/to/source --no-fuzzy

# Verbose output for debugging
shpi /path/to/source --verbose
```

### Command Line Options

- `path`: Directory path to analyze (required)
- `--max-depth`: Maximum parent directory levels to scan (default: 5)
- `--confidence-threshold`: Minimum confidence to report matches (default: 0.65)
- `--output-format`: Output format: 'json' or 'table' (default: table)
- `--no-fuzzy`: Disable fuzzy matching for faster execution
- `--cache`: Enable/disable API response caching (default: enabled)
- `--verbose`: Verbose output for debugging

## Development

### Project Structure

```
shpi/
├── core/           # Core components
├── utils/          # Utility functions
├── cli/            # Command-line interface
├── output/         # Output formatters
├── integrations/   # External integrations
└── exporters/      # Export formats (SBOM, etc.)
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_swhid.py

# Run with coverage
pytest --cov=shpi --cov-report=html
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Type checking
mypy shpi
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Software Heritage](https://www.softwareheritage.org/) for the amazing archive
- The open source community for continuous inspiration

## Status

This project is currently in active development. See the [Issues](https://github.com/oscarvalenzuelab/semantic-copycat-swh/issues) page for planned features and known issues.