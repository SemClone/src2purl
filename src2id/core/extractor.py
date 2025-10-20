"""Package coordinate extraction from Software Heritage origins."""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from src2id.core.models import SHOriginMatch


class PackageCoordinateExtractor:
    """Extracts package metadata from SH origin URLs and metadata."""
    
    # Known official organizations
    OFFICIAL_ORGS = {
        'github.com': [
            'opencv', 'microsoft', 'google', 'facebook', 'apple', 'meta',
            'llvm', 'boost-org', 'protocolbuffers', 'grpc', 'apache',
            'python', 'nodejs', 'golang', 'rust-lang', 'torvalds',
            'tensorflow', 'pytorch', 'numpy', 'scipy', 'pandas-dev',
            'FFmpeg', 'VideoLAN', 'libav', 'x264', 'x265',
        ],
        'gitlab.com': [
            'freedesktop-sdk', 'gnome', 'kde', 'freedesktop', 'gstreamer',
        ],
        'git.kernel.org': [
            'pub/scm/linux/kernel',
        ],
    }
    
    def extract_coordinates(self, origin: SHOriginMatch) -> Dict[str, Optional[str]]:
        """
        Extract name, version, download_url from origin.
        
        Args:
            origin: Origin match from Software Heritage
            
        Returns:
            Dictionary with extracted coordinates
        """
        url = origin.origin_url
        
        # Start with generic extraction
        coordinates = self._extract_generic_coordinates(url, origin.metadata)
        
        # Enhance with platform-specific extraction using proper URL parsing
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname.lower() if parsed_url.hostname else ''

        if hostname == 'github.com':
            coordinates.update(self._extract_github_coordinates(url, origin.metadata))
        elif hostname == 'gitlab.com':
            coordinates.update(self._extract_gitlab_coordinates(url, origin.metadata))
        elif hostname == 'sourceforge.net' or hostname.endswith('.sourceforge.net'):
            coordinates.update(self._extract_sourceforge_coordinates(url, origin.metadata))
        elif hostname == 'pypi.org' or hostname.endswith('.pypi.org'):
            coordinates.update(self._extract_pypi_coordinates(url))
        elif hostname == 'registry.npmjs.org':
            coordinates.update(self._extract_npm_coordinates(url))
        elif hostname == 'git.kernel.org' or hostname == 'kernel.org':
            coordinates.update(self._extract_kernel_coordinates(url, origin.metadata))
        
        return coordinates
    
    def _extract_generic_coordinates(
        self, url: str, metadata: Dict
    ) -> Dict[str, Optional[str]]:
        """
        Universal extraction that works for any repository.
        
        Args:
            url: Repository URL
            metadata: Origin metadata
            
        Returns:
            Generic coordinates
        """
        coordinates = {
            'download_url': url,
            'name': None,
            'version': None,
            'license': None,
        }
        
        # Try to extract name from URL
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if path_parts:
            # Get the last meaningful part
            name = path_parts[-1]
            # Remove common suffixes
            for suffix in ['.git', '.hg', '.svn', '.bzr']:
                if name.endswith(suffix):
                    name = name[:-len(suffix)]
            coordinates['name'] = name
        
        # Try to extract version from metadata
        if metadata:
            # Look for version in various metadata fields
            for key in ['version', 'tag', 'release', 'ref']:
                if key in metadata:
                    coordinates['version'] = str(metadata[key])
                    break
        
        return coordinates
    
    def _extract_github_coordinates(
        self, url: str, metadata: Dict
    ) -> Dict[str, Optional[str]]:
        """Extract coordinates from GitHub URLs."""
        coordinates = {}
        
        # Parse GitHub URL: https://github.com/owner/repo
        match = re.search(r'github\.com[:/]([^/]+)/([^/\s]+)', url)
        if match:
            owner = match.group(1)
            repo = match.group(2).rstrip('.git')
            coordinates['name'] = repo
            coordinates['download_url'] = f"https://github.com/{owner}/{repo}"
            
            # Extract version from tags or releases in metadata
            if metadata:
                tags = metadata.get('tags', [])
                if tags:
                    version = self._extract_version_from_tags(tags)
                    if version:
                        coordinates['version'] = version
        
        return coordinates
    
    def _extract_gitlab_coordinates(
        self, url: str, metadata: Dict
    ) -> Dict[str, Optional[str]]:
        """Extract coordinates from GitLab URLs."""
        coordinates = {}
        
        # Parse GitLab URL
        match = re.search(r'gitlab\.com[:/]([^/]+)/([^/\s]+)', url)
        if match:
            owner = match.group(1)
            repo = match.group(2).rstrip('.git')
            coordinates['name'] = repo
            coordinates['download_url'] = f"https://gitlab.com/{owner}/{repo}"
            
            # Extract version from metadata
            if metadata:
                tags = metadata.get('tags', [])
                if tags:
                    version = self._extract_version_from_tags(tags)
                    if version:
                        coordinates['version'] = version
        
        return coordinates
    
    def _extract_sourceforge_coordinates(
        self, url: str, metadata: Dict
    ) -> Dict[str, Optional[str]]:
        """Extract coordinates from SourceForge URLs."""
        coordinates = {}
        
        # Parse SourceForge URL patterns
        # e.g., https://svn.code.sf.net/p/projectname/code/trunk
        match = re.search(r'sourceforge\.net/p/([^/]+)', url)
        if not match:
            match = re.search(r'sf\.net/p/([^/]+)', url)
        
        if match:
            project = match.group(1)
            coordinates['name'] = project
            coordinates['download_url'] = f"https://sourceforge.net/projects/{project}/"
        
        return coordinates
    
    def _extract_kernel_coordinates(
        self, url: str, metadata: Dict
    ) -> Dict[str, Optional[str]]:
        """Extract coordinates from kernel.org URLs."""
        coordinates = {}
        
        if 'linux/kernel' in url:
            coordinates['name'] = 'linux'
            coordinates['download_url'] = url
            
            # Linux kernel uses specific version naming
            if metadata:
                tags = metadata.get('tags', [])
                for tag in tags:
                    if re.match(r'v\d+\.\d+(\.\d+)?', tag):
                        coordinates['version'] = tag.lstrip('v')
                        break
        
        return coordinates
    
    def _extract_pypi_coordinates(self, url: str) -> Dict[str, Optional[str]]:
        """Extract coordinates from PyPI URLs."""
        coordinates = {}
        
        # Parse PyPI URL
        match = re.search(r'pypi\.org/project/([^/]+)/?([^/]+)?', url)
        if match:
            package = match.group(1)
            version = match.group(2) if match.group(2) else None
            
            coordinates['name'] = package
            if version:
                coordinates['version'] = version
        
        return coordinates
    
    def _extract_npm_coordinates(self, url: str) -> Dict[str, Optional[str]]:
        """Extract coordinates from npm registry URLs."""
        coordinates = {}
        
        # Parse npm URL
        match = re.search(r'registry\.npmjs\.org/([^/]+)/?([^/]+)?', url)
        if match:
            package = match.group(1)
            version = match.group(2) if match.group(2) else None
            
            coordinates['name'] = package.replace('%40', '@')  # Handle scoped packages
            if version:
                coordinates['version'] = version
        
        return coordinates
    
    def _extract_version_from_tags(self, tags: List[str]) -> Optional[str]:
        """
        Extract semantic version from git tags.
        
        Args:
            tags: List of git tags
            
        Returns:
            Best version match or None
        """
        if not tags:
            return None
        
        # Priority patterns for version matching
        patterns = [
            r'^v?(\d+\.\d+\.\d+)$',  # Semantic version
            r'^v?(\d+\.\d+)$',  # Major.minor
            r'^release-(\d+\.\d+\.\d+)$',  # Release prefix
            r'^r(\d+\.\d+\.\d+)$',  # r prefix
        ]
        
        for pattern in patterns:
            for tag in tags:
                match = re.match(pattern, tag)
                if match:
                    return match.group(1)
        
        # If no pattern matches, return the first tag that looks like a version
        for tag in tags:
            if re.search(r'\d+\.\d+', tag):
                return tag
        
        return None
    
    def is_official_organization(self, url: str) -> bool:
        """
        Check if URL belongs to known official organization.
        
        Args:
            url: Repository URL
            
        Returns:
            True if from official organization
        """
        try:
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname.lower() if parsed_url.hostname else ''

            for domain, orgs in self.OFFICIAL_ORGS.items():
                if hostname == domain or hostname.endswith('.' + domain):
                    org = self._extract_organization(url, domain)
                    if org and org.lower() in [o.lower() for o in orgs]:
                        return True
            return False
        except Exception:
            return False
    
    def _extract_organization(self, url: str, domain: str) -> Optional[str]:
        """
        Extract organization name from repository URL.
        
        Args:
            url: Repository URL
            domain: Domain name
            
        Returns:
            Organization name or None
        """
        if domain == 'github.com' or domain == 'gitlab.com':
            match = re.search(rf'{domain}[:/]([^/]+)/', url)
            if match:
                return match.group(1)
        elif domain == 'git.kernel.org':
            if 'pub/scm/linux/kernel' in url:
                return 'pub/scm/linux/kernel'
        
        return None