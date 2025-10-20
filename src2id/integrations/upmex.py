"""Integration with UPMEX for package metadata extraction."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from src2id.core.models import PackageMatch, MatchType
from src2id.integrations.manifest_parser import DirectManifestParser

logger = logging.getLogger(__name__)

class UpmexIntegration:
    """Integration with UPMEX Universal Package Metadata Extractor."""

    # Package file patterns that UPMEX can handle
    UPMEX_SUPPORTED_FILES = {
        # Python
        'setup.py', 'pyproject.toml', 'setup.cfg',
        # Node.js/NPM
        'package.json', 'package-lock.json',
        # Java/Maven
        'pom.xml',
        # Gradle
        'build.gradle', 'build.gradle.kts',
        # Go
        'go.mod', 'go.sum',
        # Rust
        'Cargo.toml', 'Cargo.lock',
        # Ruby
        '*.gemspec', 'Gemfile', 'Gemfile.lock',
        # CocoaPods
        '*.podspec', '*.podspec.json',
        # Conda
        'meta.yaml', 'conda.yaml',
        # Perl
        'META.json', 'META.yml', 'Makefile.PL',
        # Conan
        'conanfile.py', 'conanfile.txt',
        # NuGet
        '*.csproj', '*.nuspec', 'packages.config',
        # Debian
        'control', 'debian/control',
    }

    def __init__(self, enabled: bool = True):
        """
        Initialize UPMEX integration with fallback to direct manifest parsing.

        Args:
            enabled: Whether UPMEX integration is enabled
        """
        self.enabled = enabled
        self._extractor = None
        self._manifest_parser = DirectManifestParser()

        if enabled:
            try:
                # Try to initialize UPMEX for packaged files
                try:
                    from upmex import PackageExtractor
                except ImportError:
                    # Try with explicit path (development setup)
                    import sys
                    sys.path.append('/Users/ovalenzuela/Projects/openpulsar/semantic-copycat-upmex/src')
                    from upmex import PackageExtractor

                self._extractor = PackageExtractor()
                logger.info("UPMEX integration initialized successfully")
            except ImportError:
                logger.info("UPMEX not available - using direct manifest parsing")
                # Keep enabled=True since we have the manifest parser as fallback
            except Exception as e:
                logger.warning(f"Failed to initialize UPMEX: {e} - using direct manifest parsing")
                # Keep enabled=True since we have the manifest parser as fallback

    def scan_directory_for_packages(self, directory: Path) -> List[Path]:
        """
        Scan directory for package files using manifest parser.

        Args:
            directory: Directory to scan

        Returns:
            List of package file paths found
        """
        if not self.enabled:
            return []

        return self._manifest_parser.scan_directory_for_manifests(directory)

    # Note: Directory scanning is now handled by DirectManifestParser

    def extract_metadata_from_file(self, file_path: Path) -> Optional[PackageMatch]:
        """
        Extract package metadata from a single package file.

        Args:
            file_path: Path to package file

        Returns:
            PackageMatch if extraction successful, None otherwise
        """
        if not self.enabled:
            return None

        # Use direct manifest parser for source files
        return self._manifest_parser.extract_metadata_from_file(file_path)

    def extract_metadata_from_directory(self, directory: Path) -> List[PackageMatch]:
        """
        Extract metadata from all package files found in a directory.

        Args:
            directory: Directory to scan and extract from

        Returns:
            List of PackageMatch objects (deduplicated by package name)
        """
        if not self.enabled:
            return []

        # Use direct manifest parser
        return self._manifest_parser.extract_metadata_from_directory(directory)

    def _convert_upmex_metadata(self, upmex_metadata, source_file: Path) -> PackageMatch:
        """
        Convert UPMEX metadata to PackageMatch format.

        Args:
            upmex_metadata: UPMEX PackageMetadata object
            source_file: Source file that was processed

        Returns:
            PackageMatch object
        """
        # Extract basic package information
        name = getattr(upmex_metadata, 'name', None)
        version = getattr(upmex_metadata, 'version', None)

        # Debug: Print the metadata structure
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"UPMEX metadata for {source_file.name}: {vars(upmex_metadata)}")

        # Get download URL from repository information
        download_url = self._extract_download_url(upmex_metadata)

        # Extract license information
        license_info = self._extract_license_info(upmex_metadata)

        # Generate PURL if available
        purl = getattr(upmex_metadata, 'purl', None)

        # Determine confidence based on data completeness
        confidence = self._calculate_confidence(upmex_metadata)

        # Create PackageMatch
        package_match = PackageMatch(
            download_url=download_url or f"file://{source_file.parent}",
            match_type=MatchType.EXACT,  # Direct metadata extraction is exact
            confidence_score=confidence,
            name=name,
            version=version,
            license=license_info,
            sh_url=None,  # No Software Heritage URL for direct extraction
            frequency_count=0,
            is_official_org=self._is_official_organization(download_url),
            purl=purl,
        )

        return package_match

    def _extract_download_url(self, metadata) -> Optional[str]:
        """Extract download URL from UPMEX metadata."""
        # Try to get repository URL
        if hasattr(metadata, 'repository') and metadata.repository:
            if isinstance(metadata.repository, dict):
                return metadata.repository.get('url')
            elif isinstance(metadata.repository, str):
                return metadata.repository

        # Try homepage
        if hasattr(metadata, 'homepage') and metadata.homepage:
            return metadata.homepage

        # Try to construct from package type and name
        if hasattr(metadata, 'package_type') and hasattr(metadata, 'name'):
            package_type = getattr(metadata.package_type, 'value', str(metadata.package_type))
            name = metadata.name

            # Generate conventional URLs for major ecosystems
            url_patterns = {
                'python': f"https://pypi.org/project/{name}/",
                'npm': f"https://www.npmjs.com/package/{name}",
                'maven': f"https://mvnrepository.com/artifact/{name}",
                'gem': f"https://rubygems.org/gems/{name}",
                'cargo': f"https://crates.io/crates/{name}",
                'go': f"https://pkg.go.dev/{name}",
            }

            return url_patterns.get(package_type.lower())

        return None

    def _extract_license_info(self, metadata) -> Optional[str]:
        """Extract license information from UPMEX metadata."""
        # Try licenses list first
        if hasattr(metadata, 'licenses') and metadata.licenses:
            license_ids = []
            for license_obj in metadata.licenses:
                if hasattr(license_obj, 'spdx_id') and license_obj.spdx_id:
                    license_ids.append(license_obj.spdx_id)
                elif hasattr(license_obj, 'name') and license_obj.name:
                    license_ids.append(license_obj.name)

            if license_ids:
                return ', '.join(license_ids)

        # Try direct license field
        if hasattr(metadata, 'license') and metadata.license:
            return metadata.license

        return None

    def _calculate_confidence(self, metadata) -> float:
        """Calculate confidence score based on metadata completeness."""
        confidence = 0.7  # Base confidence for direct metadata extraction

        # Boost confidence for complete metadata
        if hasattr(metadata, 'name') and metadata.name:
            confidence += 0.1

        if hasattr(metadata, 'version') and metadata.version:
            confidence += 0.1

        if hasattr(metadata, 'licenses') and metadata.licenses:
            confidence += 0.05

        if (hasattr(metadata, 'repository') and metadata.repository) or \
           (hasattr(metadata, 'homepage') and metadata.homepage):
            confidence += 0.05

        return min(1.0, confidence)

    def _is_official_organization(self, url: Optional[str]) -> bool:
        """Check if URL belongs to an official organization."""
        if not url:
            return False

        # Official organization patterns
        official_patterns = [
            'github.com/python/',
            'github.com/nodejs/',
            'github.com/golang/',
            'github.com/rust-lang/',
            'github.com/microsoft/',
            'github.com/google/',
            'github.com/apache/',
            'github.com/eclipse/',
            'gitlab.com/gitlab-org/',
        ]

        return any(pattern in url.lower() for pattern in official_patterns)

    def _deduplicate_matches(self, matches: List[PackageMatch]) -> List[PackageMatch]:
        """
        Deduplicate matches by package name, keeping the best quality match.

        Args:
            matches: List of package matches

        Returns:
            Deduplicated list of matches
        """
        if not matches:
            return matches

        # Group by package name
        grouped = {}
        for match in matches:
            name = match.name or "unknown"
            if name not in grouped or match.confidence_score > grouped[name].confidence_score:
                grouped[name] = match

        return list(grouped.values())

    def get_supported_file_types(self) -> Set[str]:
        """Get set of file types supported by UPMEX integration."""
        return self.UPMEX_SUPPORTED_FILES.copy()