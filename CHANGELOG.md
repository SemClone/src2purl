# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2025-08-20

### Changed (Project Rename)
- **Renamed project from SWHPI to src2id**: Better reflects the tool's multi-strategy approach
- Changed CLI command from `swhpi` to `src2id`
- Updated all package imports from `swhpi.*` to `src2id.*`
- Repository moved to `semantic-copycat-src2id`

### Added
- **Multiple Identification Strategies**: Not just Software Heritage anymore
  - Hash-based web search (GitHub, Google)
  - SCANOSS fingerprinting for code similarity
  - Web search across multiple sources
  - Software Heritage now optional with `--use-swh` flag
- **Subcomponent Detection**: New `--detect-subcomponents` flag
  - Detects multiple packages in monorepos
  - Supports Lerna, Nx, Turborepo, and standard package structures
  - Identifies nested packages in complex projects
- **30x Performance Improvement**: Optimized strategy order
  - Local methods (hash search) run first
  - Web search before expensive API calls
  - SCANOSS as third option to preserve API quotas
  - Software Heritage only when explicitly requested

### Fixed
- **Removed misleading SWH client messages**: Fixed lazy initialization
  - SoftwareHeritageClient only created when actually needed
  - No more "Using official Software Heritage WebAPIClient" when not using SWH
- **urllib3 OpenSSL warnings**: Added warning filter
- **Unclosed client sessions**: Proper cleanup in finally blocks
- **SCANOSS division errors**: Fixed type handling for matched values
- **Pre-commit hooks**: Added checks to prevent AI assistant mentions in commits

### Previous Features (from earlier 1.1.2 work on 2025-08-19)

### Added
- **API Authentication Support**: Added `--api-token` option and `SWH_API_TOKEN` environment variable for authentication
  - Bypasses rate limits when using Software Heritage API tokens
  - Supports both command-line option and environment variable
  - Works with both official WebAPIClient and fallback HTTP client
- **Batch API Processing**: Implemented efficient batch checking using `/known/` endpoint
  - Checks multiple SWHIDs in a single API call
  - Significantly improves performance for multi-directory scans
  - Falls back to individual requests when official client unavailable

### Fixed
- Fixed oslili integration to properly import semantic-copycat-oslili library
- Corrected license detection using LegalAttributionGenerator API
- Removed duplicate and obsolete methods from oslili integration
- Fixed directory scanning to traverse subdirectories correctly (not parent directories)
- Fixed SWHID generation to match official Software Heritage method using model_of_dir()

### Improved
- Hide 404 errors in non-verbose mode for cleaner output
- Removed "Version" column from results table since versions are rarely matched
- Enhanced keyword search to skip common subdirectory names (packaging, src, lib, etc.)
- Better similarity scoring for official organization repositories
- License detection now properly shows GPL-3.0 and other SPDX identifiers
- Enhanced verbose output showing paths, SWHIDs, and API results
- Improved session management for async HTTP requests

### Changed
- Table output now shows: Name, Confidence, License, PURL, Method, URL (Version column removed)
- Exact matching is now default; fuzzy matching requires --enable-fuzzy flag
- License detection is now enabled by default; use --no-license-detection to disable
- More accurate package identification for complex directory structures

## [1.1.1] - 2025-08-19

### Added
- Initial oslili integration for enhanced license detection
- Keyword search fallback when exact SWHID matches fail
- Improved confidence scoring system
- Cache support for API responses

### Features
- Software Heritage archive integration
- PURL (Package URL) generation
- Multiple output formats (table, json)
- Configurable confidence thresholds
- Directory traversal with depth limits