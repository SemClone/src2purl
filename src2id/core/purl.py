"""Package URL (PURL) generation."""

import re
from typing import Dict, Optional
from urllib.parse import quote, urlparse


class PURLGenerator:
    """Generates Package URLs following PURL specification."""
    
    def generate_purl(self, coordinates: Dict[str, str], confidence: float) -> Optional[str]:
        """
        Generate PURL only for high-confidence matches.
        
        Args:
            coordinates: Package coordinates (name, version, download_url)
            confidence: Confidence score
            
        Returns:
            PURL string or None if confidence too low or invalid URL
        """
        # Only generate PURL for high confidence matches
        if confidence < 0.85:  # This threshold could be configurable
            return None
        
        download_url = coordinates.get('download_url', '')
        name = coordinates.get('name', '')
        version = coordinates.get('version', '')
        
        if not download_url or not name:
            return None
        
        # Validate download URL
        if not self._validate_download_url(download_url):
            return None
        
        # Generate PURL based on repository type using proper URL parsing
        try:
            parsed_url = urlparse(download_url)
            hostname = parsed_url.hostname.lower() if parsed_url.hostname else ''

            if hostname == 'github.com':
                return self._generate_github_purl(download_url, name, version)
            elif hostname == 'gitlab.com':
                return self._generate_gitlab_purl(download_url, name, version)
            elif hostname == 'pypi.org' or hostname.endswith('.pypi.org'):
                return self._generate_pypi_purl(name, version)
            elif hostname in ('npmjs.org', 'npmjs.com', 'registry.npmjs.org'):
                return self._generate_npm_purl(name, version)
            elif hostname == 'crates.io':
                return self._generate_cargo_purl(name, version)
            elif hostname == 'rubygems.org':
                return self._generate_gem_purl(name, version)
            elif hostname == 'packagist.org':
                return self._generate_composer_purl(name, version)
            elif hostname == 'nuget.org':
                return self._generate_nuget_purl(name, version)
            elif hostname == 'sourceforge.net' or hostname.endswith('.sourceforge.net'):
                return self._generate_generic_purl(download_url, name, version)
            else:
                # For unknown sources, use generic PURL if possible
                return self._generate_generic_purl(download_url, name, version)
        except Exception:
            return self._generate_generic_purl(download_url, name, version)
    
    def _validate_download_url(self, url: str) -> bool:
        """
        Validate that URL follows expected package patterns.
        
        Args:
            url: Download URL
            
        Returns:
            True if valid URL
        """
        if not url:
            return False
        
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False
        
        # Check for common invalid patterns
        invalid_patterns = [
            r'/pull/\d+',  # Pull requests
            r'/issues/\d+',  # Issues
            r'/wiki/',  # Wiki pages
            r'/blob/',  # File browsing (not repo root)
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, url):
                return False
        
        return True
    
    def _generate_github_purl(self, url: str, name: str, version: Optional[str]) -> Optional[str]:
        """Generate GitHub PURL."""
        org_repo = self._extract_github_org_repo(url)
        if not org_repo:
            return None
        
        if version:
            return f"pkg:github/{org_repo}@{self._encode_version(version)}"
        else:
            return f"pkg:github/{org_repo}"
    
    def _generate_gitlab_purl(self, url: str, name: str, version: Optional[str]) -> Optional[str]:
        """Generate GitLab PURL."""
        org_repo = self._extract_gitlab_org_repo(url)
        if not org_repo:
            return None
        
        if version:
            return f"pkg:gitlab/{org_repo}@{self._encode_version(version)}"
        else:
            return f"pkg:gitlab/{org_repo}"
    
    def _generate_pypi_purl(self, name: str, version: Optional[str]) -> str:
        """Generate PyPI PURL."""
        # PyPI package names should be lowercase with hyphens
        name = name.lower().replace('_', '-')
        
        if version:
            return f"pkg:pypi/{name}@{self._encode_version(version)}"
        else:
            return f"pkg:pypi/{name}"
    
    def _generate_npm_purl(self, name: str, version: Optional[str]) -> str:
        """Generate npm PURL."""
        # Handle scoped packages
        if name.startswith('@'):
            # Scoped package: @scope/name
            parts = name[1:].split('/', 1)
            if len(parts) == 2:
                namespace = parts[0]
                pkg_name = parts[1]
                if version:
                    return f"pkg:npm/{namespace}/{pkg_name}@{self._encode_version(version)}"
                else:
                    return f"pkg:npm/{namespace}/{pkg_name}"
        
        if version:
            return f"pkg:npm/{name}@{self._encode_version(version)}"
        else:
            return f"pkg:npm/{name}"
    
    def _generate_cargo_purl(self, name: str, version: Optional[str]) -> str:
        """Generate Cargo (Rust) PURL."""
        if version:
            return f"pkg:cargo/{name}@{self._encode_version(version)}"
        else:
            return f"pkg:cargo/{name}"
    
    def _generate_gem_purl(self, name: str, version: Optional[str]) -> str:
        """Generate RubyGems PURL."""
        if version:
            return f"pkg:gem/{name}@{self._encode_version(version)}"
        else:
            return f"pkg:gem/{name}"
    
    def _generate_composer_purl(self, name: str, version: Optional[str]) -> str:
        """Generate Composer (PHP) PURL."""
        # Composer packages are vendor/package format
        if '/' in name:
            if version:
                return f"pkg:composer/{name}@{self._encode_version(version)}"
            else:
                return f"pkg:composer/{name}"
        return None
    
    def _generate_nuget_purl(self, name: str, version: Optional[str]) -> str:
        """Generate NuGet (.NET) PURL."""
        if version:
            return f"pkg:nuget/{name}@{self._encode_version(version)}"
        else:
            return f"pkg:nuget/{name}"
    
    def _generate_generic_purl(
        self, url: str, name: str, version: Optional[str]
    ) -> Optional[str]:
        """
        Generate generic PURL for unknown package types.
        
        Args:
            url: Download URL
            name: Package name
            version: Package version
            
        Returns:
            Generic PURL or None
        """
        # For now, we don't generate generic PURLs for unknown sources
        # This could be extended in the future
        return None
    
    def _extract_github_org_repo(self, url: str) -> Optional[str]:
        """Extract org/repo from GitHub URL."""
        match = re.search(r'github\.com[:/]([^/]+)/([^/\s]+)', url)
        if match:
            org = match.group(1)
            repo = match.group(2).rstrip('.git')
            return f"{org}/{repo}"
        return None
    
    def _extract_gitlab_org_repo(self, url: str) -> Optional[str]:
        """Extract org/repo from GitLab URL."""
        match = re.search(r'gitlab\.com[:/]([^/]+)/([^/\s?#]+)', url)
        if match:
            org = match.group(1)
            repo = match.group(2)
            if repo.endswith('.git'):
                repo = repo[:-4]
            if repo.endswith('/'):
                repo = repo[:-1]
            return f"{org}/{repo}"
        return None
    
    def _encode_version(self, version: str) -> str:
        """
        Encode version string for PURL.
        
        Args:
            version: Version string
            
        Returns:
            Encoded version
        """
        # Remove common version prefixes
        version = version.lstrip('v')
        version = version.lstrip('r')
        
        # URL encode special characters
        return quote(version, safe='.-_')