"""Direct package manifest parser for common package formats."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

# Handle TOML parsing with fallback for older Python versions
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python < 3.11
    except ImportError:
        tomllib = None  # No TOML support available

from src2id.core.models import PackageMatch, MatchType

class DirectManifestParser:
    """Parser for common package manifest files."""

    # Supported manifest file patterns
    SUPPORTED_FILES = {
        # Python
        'setup.py', 'pyproject.toml', 'setup.cfg', 'PKG-INFO',
        # Node.js/NPM
        'package.json',
        # Java/Maven
        'pom.xml',
        # Go
        'go.mod', 'go.sum',
        # Rust
        'Cargo.toml', 'Cargo.lock',
        # Ruby
        'Gemfile', 'Gemfile.lock',
        # CocoaPods
        'Podfile',
        # Conda
        'meta.yaml', 'conda.yaml', 'environment.yml',
        # Perl
        'META.json', 'META.yml', 'Makefile.PL',
        # Conan
        'conanfile.py', 'conanfile.txt',
        # NuGet
        'packages.config',
        # Debian
        'control',
    }

    def __init__(self):
        """Initialize the manifest parser."""
        pass

    def scan_directory_for_manifests(self, directory: Path) -> List[Path]:
        """
        Scan directory for supported manifest files.

        Args:
            directory: Directory to scan

        Returns:
            List of manifest file paths found
        """
        manifest_files = []

        try:
            # Scan current directory
            manifest_files.extend(self._scan_single_directory(directory))

            # Scan deeper subdirectories for manifest files (up to 3 levels deep)
            self._scan_recursive_manifests(directory, manifest_files, max_depth=3, current_depth=0)

        except (PermissionError, OSError):
            pass

        return manifest_files

    def _scan_single_directory(self, directory: Path) -> List[Path]:
        """Scan a single directory for manifest files."""
        manifest_files = []

        try:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    # Check exact filename matches
                    if file_path.name in self.SUPPORTED_FILES:
                        manifest_files.append(file_path)
                    # Check pattern matches (e.g., *.gemspec, *.csproj)
                    elif self._matches_pattern(file_path.name):
                        manifest_files.append(file_path)
        except (PermissionError, OSError):
            pass

        return manifest_files

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches supported patterns."""
        patterns = [
            r'.*\.gemspec$',      # Ruby gemspec files
            r'.*\.csproj$',       # .NET project files
            r'.*\.nuspec$',       # NuGet package spec files
            r'.*\.podspec$',      # CocoaPods spec files
            r'build\.gradle.*$',  # Gradle build files
        ]

        return any(re.match(pattern, filename) for pattern in patterns)

    def extract_metadata_from_file(self, file_path: Path) -> Optional[PackageMatch]:
        """
        Extract package metadata from a manifest file.

        Args:
            file_path: Path to manifest file

        Returns:
            PackageMatch if extraction successful, None otherwise
        """
        try:
            if file_path.name == 'package.json':
                return self._parse_package_json(file_path)
            elif file_path.name == 'pyproject.toml':
                return self._parse_pyproject_toml(file_path)
            elif file_path.name == 'setup.py':
                return self._parse_setup_py(file_path)
            elif file_path.name == 'setup.cfg':
                return self._parse_setup_cfg(file_path)
            elif file_path.name == 'pom.xml':
                return self._parse_pom_xml(file_path)
            elif file_path.name == 'go.mod':
                return self._parse_go_mod(file_path)
            elif file_path.name == 'Cargo.toml':
                return self._parse_cargo_toml(file_path)
            elif file_path.name.endswith('.gemspec'):
                return self._parse_gemspec(file_path)
            elif file_path.name.endswith(('.podspec', '.podspec.json')):
                return self._parse_podspec(file_path)
            # Add more parsers as needed

        except Exception as e:
            # Silently ignore parsing errors
            pass

        return None

    def extract_metadata_from_directory(self, directory: Path) -> List[PackageMatch]:
        """
        Extract metadata from all manifest files in a directory.

        Args:
            directory: Directory to scan

        Returns:
            List of PackageMatch objects (deduplicated by package name)
        """
        matches = []
        manifest_files = self.scan_directory_for_manifests(directory)

        for file_path in manifest_files:
            match = self.extract_metadata_from_file(file_path)
            if match:
                matches.append(match)

        # Deduplicate by package name, keeping the best quality match
        return self._deduplicate_matches(matches)

    def _parse_package_json(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse NPM package.json file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            name = data.get('name')
            version = data.get('version')
            license_info = data.get('license')
            description = data.get('description')
            homepage = data.get('homepage')
            repository = data.get('repository', {})

            # Extract repository URL
            repo_url = None
            if isinstance(repository, dict):
                repo_url = repository.get('url')
            elif isinstance(repository, str):
                repo_url = repository

            # Generate PURL
            purl = None
            if name:
                if name.startswith('@'):
                    # Scoped package
                    parts = name[1:].split('/', 1)
                    if len(parts) == 2:
                        namespace, pkg_name = parts
                        purl = f"pkg:npm/{namespace}/{pkg_name}"
                        if version:
                            purl += f"@{version}"
                else:
                    purl = f"pkg:npm/{name}"
                    if version:
                        purl += f"@{version}"

            return PackageMatch(
                download_url=repo_url or homepage or f"https://www.npmjs.com/package/{name}",
                match_type=MatchType.EXACT,
                confidence_score=0.9,
                name=name,
                version=version,
                license=license_info,
                purl=purl,
                is_official_org=self._is_official_npm_org(repo_url or homepage or ''),
            )

        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def _parse_pyproject_toml(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse Python pyproject.toml file."""
        if tomllib is None:
            return None  # TOML support not available

        try:
            with open(file_path, 'rb') as f:
                data = tomllib.load(f)

            project = data.get('project', {})
            name = project.get('name')
            version = project.get('version')

            # Handle license
            license_info = None
            license_data = project.get('license')
            if isinstance(license_data, dict):
                license_info = license_data.get('text')
            elif isinstance(license_data, str):
                license_info = license_data

            # Get URLs
            urls = project.get('urls', {})
            homepage = urls.get('Homepage') or urls.get('home')
            repository = urls.get('Repository') or urls.get('repository')

            # Generate PURL
            purl = None
            if name:
                purl = f"pkg:pypi/{name.lower().replace('_', '-')}"
                if version:
                    purl += f"@{version}"

            return PackageMatch(
                download_url=repository or homepage or f"https://pypi.org/project/{name}/",
                match_type=MatchType.EXACT,
                confidence_score=0.95,
                name=name,
                version=version,
                license=license_info,
                purl=purl,
                is_official_org=self._is_official_python_org(repository or homepage or ''),
            )

        except (tomllib.TOMLDecodeError, KeyError, FileNotFoundError):
            return None

    def _parse_setup_py(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse Python setup.py file (basic regex-based parsing)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Use regex to extract basic information
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            license_match = re.search(r'license\s*=\s*["\']([^"\']+)["\']', content)
            url_match = re.search(r'url\s*=\s*["\']([^"\']+)["\']', content)

            name = name_match.group(1) if name_match else None
            version = version_match.group(1) if version_match else None
            license_info = license_match.group(1) if license_match else None
            url = url_match.group(1) if url_match else None

            if not name:
                return None

            # Generate PURL
            purl = f"pkg:pypi/{name.lower().replace('_', '-')}"
            if version:
                purl += f"@{version}"

            return PackageMatch(
                download_url=url or f"https://pypi.org/project/{name}/",
                match_type=MatchType.EXACT,
                confidence_score=0.85,  # Lower confidence for regex parsing
                name=name,
                version=version,
                license=license_info,
                purl=purl,
                is_official_org=self._is_official_python_org(url or ''),
            )

        except (FileNotFoundError, UnicodeDecodeError):
            return None

    def _parse_pom_xml(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse Maven pom.xml file (basic regex-based parsing)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract basic Maven coordinates
            group_match = re.search(r'<groupId>([^<]+)</groupId>', content)
            artifact_match = re.search(r'<artifactId>([^<]+)</artifactId>', content)
            version_match = re.search(r'<version>([^<]+)</version>', content)
            url_match = re.search(r'<url>([^<]+)</url>', content)

            group_id = group_match.group(1) if group_match else None
            artifact_id = artifact_match.group(1) if artifact_match else None
            version = version_match.group(1) if version_match else None
            url = url_match.group(1) if url_match else None

            if not artifact_id:
                return None

            # Generate PURL
            purl = f"pkg:maven/{group_id or 'unknown'}/{artifact_id}"
            if version and not version.startswith('${'):  # Skip property placeholders
                purl += f"@{version}"

            return PackageMatch(
                download_url=url or f"https://mvnrepository.com/artifact/{group_id}/{artifact_id}",
                match_type=MatchType.EXACT,
                confidence_score=0.9,
                name=f"{group_id}:{artifact_id}" if group_id else artifact_id,
                version=version if not version.startswith('${') else None,
                purl=purl,
                is_official_org=self._is_official_java_org(url or group_id or ''),
            )

        except (FileNotFoundError, UnicodeDecodeError):
            return None

    def _parse_go_mod(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse Go go.mod file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract module name
            module_match = re.search(r'^module\s+([^\s]+)', content, re.MULTILINE)
            go_version_match = re.search(r'^go\s+([^\s]+)', content, re.MULTILINE)

            module_name = module_match.group(1) if module_match else None
            go_version = go_version_match.group(1) if go_version_match else None

            if not module_name:
                return None

            # Generate PURL
            purl = f"pkg:golang/{module_name}"

            # Try to construct repository URL
            repo_url = None
            if module_name.startswith(('github.com/', 'gitlab.com/', 'bitbucket.org/')):
                repo_url = f"https://{module_name}"

            return PackageMatch(
                download_url=repo_url or f"https://pkg.go.dev/{module_name}",
                match_type=MatchType.EXACT,
                confidence_score=0.9,
                name=module_name,
                version=go_version,
                purl=purl,
                is_official_org=self._is_official_go_org(module_name),
            )

        except (FileNotFoundError, UnicodeDecodeError):
            return None

    def _parse_cargo_toml(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse Rust Cargo.toml file."""
        if tomllib is None:
            return None  # TOML support not available

        try:
            with open(file_path, 'rb') as f:
                data = tomllib.load(f)

            package = data.get('package', {})
            name = package.get('name')
            version = package.get('version')
            license_info = package.get('license')
            repository = package.get('repository')
            homepage = package.get('homepage')

            if not name:
                return None

            # Generate PURL
            purl = f"pkg:cargo/{name}"
            if version:
                purl += f"@{version}"

            return PackageMatch(
                download_url=repository or homepage or f"https://crates.io/crates/{name}",
                match_type=MatchType.EXACT,
                confidence_score=0.9,
                name=name,
                version=version,
                license=license_info,
                purl=purl,
                is_official_org=self._is_official_rust_org(repository or homepage or ''),
            )

        except (tomllib.TOMLDecodeError, KeyError, FileNotFoundError):
            return None

    def _parse_gemspec(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse Ruby .gemspec file (basic regex-based parsing)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract basic gem information
            name_match = re.search(r'spec\.name\s*=\s*["\']([^"\']+)["\']', content)
            version_match = re.search(r'spec\.version\s*=\s*["\']([^"\']+)["\']', content)
            license_match = re.search(r'spec\.license\s*=\s*["\']([^"\']+)["\']', content)
            homepage_match = re.search(r'spec\.homepage\s*=\s*["\']([^"\']+)["\']', content)

            name = name_match.group(1) if name_match else None
            version = version_match.group(1) if version_match else None
            license_info = license_match.group(1) if license_match else None
            homepage = homepage_match.group(1) if homepage_match else None

            if not name:
                return None

            # Generate PURL
            purl = f"pkg:gem/{name}"
            if version:
                purl += f"@{version}"

            return PackageMatch(
                download_url=homepage or f"https://rubygems.org/gems/{name}",
                match_type=MatchType.EXACT,
                confidence_score=0.85,  # Lower confidence for regex parsing
                name=name,
                version=version,
                license=license_info,
                purl=purl,
                is_official_org=False,  # Most gems are not from official orgs
            )

        except (FileNotFoundError, UnicodeDecodeError):
            return None

    def _parse_podspec(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse CocoaPods .podspec file."""
        try:
            if file_path.name.endswith('.json'):
                # JSON podspec
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                name = data.get('name')
                version = data.get('version')
                license_info = data.get('license')
                homepage = data.get('homepage')
                source = data.get('source', {})

                # Extract git URL from source
                git_url = None
                if isinstance(source, dict):
                    git_url = source.get('git')

            else:
                # Ruby podspec (basic regex parsing)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                name_match = re.search(r's\.name\s*=\s*["\']([^"\']+)["\']', content)
                version_match = re.search(r's\.version\s*=\s*["\']([^"\']+)["\']', content)
                homepage_match = re.search(r's\.homepage\s*=\s*["\']([^"\']+)["\']', content)

                name = name_match.group(1) if name_match else None
                version = version_match.group(1) if version_match else None
                homepage = homepage_match.group(1) if homepage_match else None
                license_info = None
                git_url = None

            if not name:
                return None

            return PackageMatch(
                download_url=git_url or homepage or f"https://cocoapods.org/pods/{name}",
                match_type=MatchType.EXACT,
                confidence_score=0.9,
                name=name,
                version=version,
                license=license_info if isinstance(license_info, str) else None,
                is_official_org=False,
            )

        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError):
            return None

    def _deduplicate_matches(self, matches: List[PackageMatch]) -> List[PackageMatch]:
        """Deduplicate matches by package name, keeping the best quality match."""
        if not matches:
            return matches

        # Group by package name
        grouped = {}
        for match in matches:
            name = match.name or "unknown"
            if name not in grouped or match.confidence_score > grouped[name].confidence_score:
                grouped[name] = match

        return list(grouped.values())

    def _scan_recursive_manifests(self, directory: Path, manifest_files: List[Path], max_depth: int, current_depth: int):
        """Recursively scan subdirectories for manifest files."""
        if current_depth >= max_depth:
            return

        try:
            for subdir in directory.iterdir():
                if (subdir.is_dir() and
                    not subdir.name.startswith('.') and
                    subdir.name not in {'__pycache__', 'node_modules', 'target', 'build', 'dist', '.git'}):

                    # Scan this subdirectory
                    manifest_files.extend(self._scan_single_directory(subdir))

                    # Recurse deeper
                    self._scan_recursive_manifests(subdir, manifest_files, max_depth, current_depth + 1)

        except (PermissionError, OSError):
            pass

    def _parse_setup_cfg(self, file_path: Path) -> Optional[PackageMatch]:
        """Parse Python setup.cfg file."""
        try:
            import configparser

            config = configparser.ConfigParser()
            config.read(file_path)

            # Extract metadata from [metadata] section
            if not config.has_section('metadata'):
                return None

            metadata_section = config['metadata']
            name = metadata_section.get('name')
            version = metadata_section.get('version')
            license_info = metadata_section.get('license')
            url = metadata_section.get('url')

            # Try to get repository URL from project_urls
            repo_url = url
            if config.has_option('metadata', 'project_urls'):
                project_urls = metadata_section.get('project_urls', '')
                for line in project_urls.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip().lower()
                        if key in ['source', 'repository', 'homepage']:
                            repo_url = value.strip()
                            break

            if not name:
                return None

            # Generate PURL
            purl = f"pkg:pypi/{name.lower().replace('_', '-')}"
            if version and not version.startswith('attr:'):
                purl += f"@{version}"

            return PackageMatch(
                download_url=repo_url or f"https://pypi.org/project/{name}/",
                match_type=MatchType.EXACT,
                confidence_score=0.9,
                name=name,
                version=version if not version.startswith('attr:') else None,
                license=license_info,
                purl=purl,
                is_official_org=self._is_official_python_org(repo_url or ''),
            )

        except (configparser.Error, FileNotFoundError, UnicodeDecodeError):
            return None

    def _is_official_npm_org(self, url: str) -> bool:
        """Check if NPM package is from an official organization."""
        official_patterns = [
            'github.com/nodejs/',
            'github.com/npm/',
            'github.com/microsoft/',
            'github.com/google/',
            'github.com/facebook/',
            'github.com/angular/',
            'github.com/reactjs/',
        ]
        return any(pattern in url.lower() for pattern in official_patterns)

    def _is_official_python_org(self, url: str) -> bool:
        """Check if Python package is from an official organization."""
        official_patterns = [
            'github.com/python/',
            'github.com/psf/',
            'github.com/microsoft/',
            'github.com/google/',
            'github.com/numpy/',
            'github.com/scipy/',
            'github.com/pandas-dev/',
        ]
        return any(pattern in url.lower() for pattern in official_patterns)

    def _is_official_java_org(self, identifier: str) -> bool:
        """Check if Java package is from an official organization."""
        official_patterns = [
            'apache',
            'eclipse',
            'springframework',
            'com.google',
            'com.microsoft',
            'org.apache',
            'org.eclipse',
            'org.springframework',
        ]
        return any(pattern in identifier.lower() for pattern in official_patterns)

    def _is_official_go_org(self, module: str) -> bool:
        """Check if Go module is from an official organization."""
        official_patterns = [
            'github.com/golang/',
            'github.com/google/',
            'github.com/microsoft/',
            'go.uber.org/',
            'google.golang.org/',
        ]
        return any(pattern in module.lower() for pattern in official_patterns)

    def _is_official_rust_org(self, url: str) -> bool:
        """Check if Rust crate is from an official organization."""
        official_patterns = [
            'github.com/rust-lang/',
            'github.com/tokio-rs/',
            'github.com/serde-rs/',
        ]
        return any(pattern in url.lower() for pattern in official_patterns)

    def get_supported_file_types(self) -> Set[str]:
        """Get set of file types supported by the manifest parser."""
        return self.SUPPORTED_FILES.copy()