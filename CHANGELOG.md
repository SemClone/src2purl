# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2025-08-19

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