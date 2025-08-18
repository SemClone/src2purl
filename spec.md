# Technical Specification: SH Package Identifier (SHPI)

## Overview
A Python tool that identifies package coordinates (name, version, license, PURL) from source code directories by leveraging Software Heritage (SH) archive content-addressable hashing and origin metadata.

## Core Architecture

### 1. Configuration Management
```python
@dataclass
class SHPIConfig:
    # Directory scanning parameters
    max_depth: int = 5  # Maximum parent directory levels to scan
    min_files: int = 3  # Minimum files in directory to consider meaningful
    
    # Confidence thresholds
    purl_generation_threshold: float = 0.85
    report_match_threshold: float = 0.65
    fuzzy_consideration_threshold: float = 0.5
    
    # Scoring weights
    score_weights: Dict[str, float] = field(default_factory=lambda: {
        'recency': 0.3,
        'popularity': 0.2,
        'authority': 0.3,
        'specificity': 0.2
    })
    
    # API configuration
    sh_api_base: str = "https://archive.softwareheritage.org/api/1"
    rate_limit_delay: float = 0.5  # Seconds between API calls
    max_retries: int = 3
    cache_enabled: bool = True
```

### 2. Data Models

```python
@dataclass
class PackageMatch:
    download_url: str
    name: Optional[str]
    version: Optional[str]
    license: Optional[str]
    sh_url: str
    match_type: Literal['exact', 'fuzzy']
    confidence_score: float
    frequency_count: int
    is_official_org: bool
    purl: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON output"""
        pass

@dataclass
class DirectoryCandidate:
    path: Path
    swhid: str
    depth: int
    specificity_score: float
    file_count: int
    
@dataclass
class SHOriginMatch:
    origin_url: str
    swhid: str
    last_seen: datetime
    visit_count: int
    metadata: Dict[str, Any]
```

### 3. Core Components

#### 3.1 SWHID Generator
```python
class SWHIDGenerator:
    """
    Generates Software Heritage Identifiers using miniswhid or custom implementation
    """
    
    def __init__(self, use_miniswhid: bool = True):
        self.use_miniswhid = use_miniswhid
        
    def generate_directory_swhid(self, path: Path) -> str:
        """Generate SWHID for directory content"""
        # TODO: Implement using miniswhid or custom merkle tree logic
        # Must handle: file permissions, symlinks, reproducible sorting
        pass
        
    def generate_content_swhid(self, file_path: Path) -> str:
        """Generate SWHID for individual file content"""
        pass
        
    def _build_merkle_tree(self, path: Path) -> str:
        """Custom implementation if not using miniswhid"""
        # NOTE: Experimental - needs testing for SH compatibility
        pass
```

#### 3.2 Software Heritage API Client
```python
class SoftwareHeritageClient:
    """
    Handles all interactions with Software Heritage API
    """
    
    def __init__(self, config: SHPIConfig):
        self.config = config
        self.session = requests.Session()
        self.cache = {} if config.cache_enabled else None
        
    async def get_directory_origins(self, swhid: str) -> List[SHOriginMatch]:
        """Get all origins containing this directory"""
        # GET /api/1/directory/{swhid}/
        # GET /api/1/directory/{swhid}/origins/
        pass
        
    async def get_content_origins(self, content_hash: str) -> List[SHOriginMatch]:
        """Get origins containing specific file content"""
        pass
        
    async def get_directory_tree(self, swhid: str) -> Dict[str, Any]:
        """Get directory structure for fuzzy comparison"""
        # NOTE: May need pagination for large directories
        pass
        
    async def get_directory_file_hashes(self, swhid: str) -> Set[str]:
        """Get all file hashes in directory for content similarity"""
        pass
        
    def _handle_rate_limiting(self):
        """Implement exponential backoff and rate limiting"""
        pass
```

#### 3.3 Directory Scanner
```python
class DirectoryScanner:
    """
    Scans filesystem and generates directory candidates for SH matching
    """
    
    def __init__(self, config: SHPIConfig, swhid_generator: SWHIDGenerator):
        self.config = config
        self.swhid_generator = swhid_generator
        
    def scan_recursive(self, start_path: Path) -> List[DirectoryCandidate]:
        """
        Generate directory candidates by walking up parent directories
        """
        candidates = []
        current = start_path.resolve()
        
        for depth in range(self.config.max_depth):
            if self._is_meaningful_directory(current):
                swhid = self.swhid_generator.generate_directory_swhid(current)
                candidate = DirectoryCandidate(
                    path=current,
                    swhid=swhid,
                    depth=depth,
                    specificity_score=1.0 / (depth + 1),
                    file_count=self._count_relevant_files(current)
                )
                candidates.append(candidate)
                
            current = current.parent
            if current == current.parent:  # Filesystem root
                break
                
        return candidates
        
    def _is_meaningful_directory(self, path: Path) -> bool:
        """Check if directory likely contains package content"""
        # Skip .git, build directories, etc.
        # Check minimum file count
        pass
        
    def _count_relevant_files(self, path: Path) -> int:
        """Count source files, ignore build artifacts"""
        pass

    def detect_git_submodules(self, repo_path: Path) -> List[Path]:
        """Parse .gitmodules and return submodule paths"""
        # NOTE: Experimental feature - needs testing
        pass
```

#### 3.4 Fuzzy Matcher
```python
class FuzzyMatcher:
    """
    Implements fuzzy matching for near-miss directory identification
    """
    
    def __init__(self, sh_client: SoftwareHeritageClient):
        self.sh_client = sh_client
        
    async def find_fuzzy_matches(self, 
                                candidate: DirectoryCandidate, 
                                threshold: float = 0.8) -> List[Tuple[str, float]]:
        """
        Multi-tier fuzzy matching:
        1. File set similarity (Jaccard)
        2. Directory structure similarity
        3. Content similarity via file hashes
        """
        # Tier 1: Fast file set comparison
        similar_dirs = await self._find_similar_filesets(candidate)
        
        # Tier 2: Structure comparison
        structure_candidates = []
        for dir_swhid in similar_dirs:
            score = await self._calculate_structure_similarity(candidate, dir_swhid)
            if score > threshold:
                structure_candidates.append((dir_swhid, score))
        
        # Tier 3: Content similarity
        final_matches = []
        for dir_swhid, struct_score in structure_candidates:
            content_score = await self._calculate_content_similarity(candidate, dir_swhid)
            final_score = (struct_score * 0.6) + (content_score * 0.4)
            if final_score > threshold:
                final_matches.append((dir_swhid, final_score))
                
        return final_matches
        
    async def _find_similar_filesets(self, candidate: DirectoryCandidate) -> List[str]:
        """Find directories with similar file names/paths"""
        # NOTE: Experimental - SH API may not support this query pattern
        # May need to implement via batch file content queries
        pass
        
    async def _calculate_structure_similarity(self, 
                                            candidate: DirectoryCandidate, 
                                            sh_swhid: str) -> float:
        """Compare directory tree structures"""
        local_tree = self._build_tree_structure(candidate.path)
        sh_tree = await self.sh_client.get_directory_tree(sh_swhid)
        return self._tree_similarity_score(local_tree, sh_tree)
        
    async def _calculate_content_similarity(self, 
                                          candidate: DirectoryCandidate, 
                                          sh_swhid: str) -> float:
        """Compare file content hashes using Jaccard similarity"""
        local_hashes = self._get_all_file_hashes(candidate.path)
        sh_hashes = await self.sh_client.get_directory_file_hashes(sh_swhid)
        
        intersection = len(local_hashes & sh_hashes)
        union = len(local_hashes | sh_hashes)
        return intersection / union if union > 0 else 0.0
        
    def _tree_similarity_score(self, tree1: Dict, tree2: Dict) -> float:
        """Calculate structural similarity between directory trees"""
        # NOTE: Needs experimentation on best algorithm
        # Options: tree edit distance, structural hash comparison
        pass
```

#### 3.5 Package Coordinate Extractor
```python
class PackageCoordinateExtractor:
    """
    Extracts package metadata from SH origin URLs and metadata
    """
    
    # Known official organizations
    OFFICIAL_ORGS = {
        'github.com': [
            'opencv', 'microsoft', 'google', 'facebook', 'apple',
            'llvm', 'boost-org', 'protocolbuffers', 'grpc'
        ],
        'gitlab.com': ['freedesktop-sdk', 'gnome', 'kde']
    }
    
    def extract_coordinates(self, origin: SHOriginMatch) -> Dict[str, Optional[str]]:
        """Extract name, version, download_url from origin"""
        url = origin.origin_url
        
        # Parse different URL patterns
        if 'github.com' in url:
            return self._extract_github_coordinates(url, origin.metadata)
        elif 'gitlab.com' in url:
            return self._extract_gitlab_coordinates(url, origin.metadata)
        elif 'pypi.org' in url:
            return self._extract_pypi_coordinates(url)
        elif 'registry.npmjs.org' in url:
            return self._extract_npm_coordinates(url)
        else:
            return self._extract_generic_coordinates(url, origin.metadata)
            
    def _extract_github_coordinates(self, url: str, metadata: Dict) -> Dict[str, Optional[str]]:
        """Extract coordinates from GitHub URLs"""
        # Parse org/repo from URL
        # Look for version in tags, releases
        # Check for manifest files in metadata
        pass
        
    def _extract_version_from_tags(self, tags: List[str]) -> Optional[str]:
        """Extract semantic version from git tags"""
        # Priority: semver > date-based > sequential
        # Handle prefixes: v1.2.3, release-1.2.3, 1.2.3
        pass
        
    def is_official_organization(self, url: str) -> bool:
        """Check if URL belongs to known official organization"""
        for domain, orgs in self.OFFICIAL_ORGS.items():
            if domain in url:
                org = self._extract_organization(url)
                return org.lower() in [o.lower() for o in orgs]
        return False
        
    def _extract_organization(self, url: str) -> str:
        """Extract organization name from repository URL"""
        pass
```

#### 3.6 Confidence Scorer
```python
class ConfidenceScorer:
    """
    Calculates confidence scores for package matches
    """
    
    def __init__(self, config: SHPIConfig):
        self.config = config
        
    def calculate_confidence(self, match_data: Dict[str, Any]) -> float:
        """
        Multi-factor confidence scoring:
        - Match type (exact vs fuzzy)
        - Frequency/popularity
        - Official organization authority
        - Recency of activity
        """
        base_score = self._get_base_score(match_data)
        
        multipliers = [
            self._frequency_multiplier(match_data['frequency_rank']),
            self._authority_multiplier(match_data['is_official_org']),
            self._recency_multiplier(match_data['last_activity'])
        ]
        
        final_score = base_score
        for multiplier in multipliers:
            final_score *= multiplier
            
        return min(1.0, final_score)
        
    def _get_base_score(self, match_data: Dict[str, Any]) -> float:
        """Base confidence from match type"""
        if match_data['match_type'] == 'exact':
            return 0.9
        else:  # fuzzy
            return match_data['similarity_score'] * 0.8
            
    def _frequency_multiplier(self, frequency_rank: int) -> float:
        """Boost confidence for frequently appearing packages"""
        return min(1.2, 1.0 + (frequency_rank * 0.05))
        
    def _authority_multiplier(self, is_official: bool) -> float:
        """Boost confidence for official organizations"""
        return 1.15 if is_official else 1.0
        
    def _recency_multiplier(self, last_activity: Optional[datetime]) -> float:
        """Boost confidence for recently active repositories"""
        if not last_activity:
            return 1.0
            
        days_ago = (datetime.now() - last_activity).days
        if days_ago < 30:
            return 1.1
        elif days_ago < 365:
            return 1.05
        else:
            return 0.95
```

#### 3.7 PURL Generator
```python
class PURLGenerator:
    """
    Generates Package URLs following PURL specification
    """
    
    def generate_purl(self, coordinates: Dict[str, str], confidence: float) -> Optional[str]:
        """Generate PURL only for high-confidence matches"""
        if confidence < 0.85:  # From config.purl_generation_threshold
            return None
            
        download_url = coordinates.get('download_url', '')
        name = coordinates.get('name', '')
        version = coordinates.get('version', '')
        
        if not self._validate_download_url(download_url):
            return None
            
        if 'github.com' in download_url:
            org_repo = self._extract_org_repo(download_url)
            return f'pkg:github/{org_repo}@{version}' if version else f'pkg:github/{org_repo}'
        elif 'gitlab.com' in download_url:
            org_repo = self._extract_org_repo(download_url)
            return f'pkg:gitlab/{org_repo}@{version}' if version else f'pkg:gitlab/{org_repo}'
        # Add more ecosystems as needed
        
        return None
        
    def _validate_download_url(self, url: str) -> bool:
        """Validate that URL follows expected package patterns"""
        # Check for proper repository structure, release patterns
        pass
        
    def _extract_org_repo(self, url: str) -> str:
        """Extract org/repo from repository URL"""
        pass
```

### 4. Main Orchestrator

```python
class SHPackageIdentifier:
    """
    Main orchestrator class that coordinates all components
    """
    
    def __init__(self, config: SHPIConfig = None):
        self.config = config or SHPIConfig()
        self.swhid_generator = SWHIDGenerator()
        self.sh_client = SoftwareHeritageClient(self.config)
        self.scanner = DirectoryScanner(self.config, self.swhid_generator)
        self.fuzzy_matcher = FuzzyMatcher(self.sh_client)
        self.coordinate_extractor = PackageCoordinateExtractor()
        self.confidence_scorer = ConfidenceScorer(self.config)
        self.purl_generator = PURLGenerator()
        
    async def identify_packages(self, path: Path) -> List[PackageMatch]:
        """
        Main entry point for package identification
        """
        # 1. Scan directories and generate candidates
        candidates = self.scanner.scan_recursive(path)
        
        # 2. Query SH for exact matches
        all_matches = []
        for candidate in candidates:
            exact_matches = await self._find_exact_matches(candidate)
            all_matches.extend(exact_matches)
            
            # 3. If no exact matches, try fuzzy matching
            if not exact_matches:
                fuzzy_matches = await self._find_fuzzy_matches(candidate)
                all_matches.extend(fuzzy_matches)
        
        # 4. Extract coordinates and calculate confidence
        package_matches = []
        for match in all_matches:
            coordinates = self.coordinate_extractor.extract_coordinates(match)
            confidence = self.confidence_scorer.calculate_confidence({
                'match_type': match.match_type,
                'similarity_score': getattr(match, 'similarity_score', 1.0),
                'frequency_rank': match.frequency_count,
                'is_official_org': self.coordinate_extractor.is_official_organization(match.origin_url),
                'last_activity': match.last_seen
            })
            
            if confidence >= self.config.report_match_threshold:
                purl = self.purl_generator.generate_purl(coordinates, confidence)
                
                package_match = PackageMatch(
                    download_url=coordinates.get('download_url', match.origin_url),
                    name=coordinates.get('name'),
                    version=coordinates.get('version'),
                    license=coordinates.get('license'),
                    sh_url=f"{self.config.sh_api_base}/directory/{match.swhid}/",
                    match_type=match.match_type,
                    confidence_score=confidence,
                    frequency_count=match.frequency_count,
                    is_official_org=self.coordinate_extractor.is_official_organization(match.origin_url),
                    purl=purl
                )
                package_matches.append(package_match)
        
        # 5. Sort and deduplicate results
        return self._prioritize_and_deduplicate(package_matches)
        
    async def _find_exact_matches(self, candidate: DirectoryCandidate) -> List[SHOriginMatch]:
        """Find exact SWHID matches in Software Heritage"""
        origins = await self.sh_client.get_directory_origins(candidate.swhid)
        return [SHOriginMatch(
            origin_url=origin['url'],
            swhid=candidate.swhid,
            last_seen=datetime.fromisoformat(origin['last_seen']),
            visit_count=origin.get('visit_count', 1),
            metadata=origin.get('metadata', {}),
            match_type='exact'
        ) for origin in origins]
        
    async def _find_fuzzy_matches(self, candidate: DirectoryCandidate) -> List[SHOriginMatch]:
        """Find fuzzy matches using similarity algorithms"""
        fuzzy_results = await self.fuzzy_matcher.find_fuzzy_matches(
            candidate, 
            self.config.fuzzy_consideration_threshold
        )
        
        matches = []
        for swhid, similarity_score in fuzzy_results:
            origins = await self.sh_client.get_directory_origins(swhid)
            for origin in origins:
                match = SHOriginMatch(
                    origin_url=origin['url'],
                    swhid=swhid,
                    last_seen=datetime.fromisoformat(origin['last_seen']),
                    visit_count=origin.get('visit_count', 1),
                    metadata=origin.get('metadata', {}),
                    match_type='fuzzy'
                )
                match.similarity_score = similarity_score
                matches.append(match)
                
        return matches
        
    def _prioritize_and_deduplicate(self, matches: List[PackageMatch]) -> List[PackageMatch]:
        """Sort by confidence and remove duplicates"""
        # Group by base repository URL
        grouped = {}
        for match in matches:
            base_url = self._extract_base_repo_url(match.download_url)
            if base_url not in grouped or match.confidence_score > grouped[base_url].confidence_score:
                grouped[base_url] = match
                
        # Sort by official orgs first, then confidence
        result = list(grouped.values())
        result.sort(key=lambda m: (-1 if m.is_official_org else 0, -m.confidence_score))
        
        return result
```

### 5. CLI Interface

```python
class SHPICLIInterface:
    """
    Command-line interface for the tool
    """
    
    def __init__(self):
        self.parser = self._build_parser()
        
    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Identify package coordinates from source code using Software Heritage"
        )
        
        parser.add_argument('path', help='Directory path to analyze')
        parser.add_argument('--max-depth', type=int, default=5, 
                          help='Maximum parent directory levels to scan')
        parser.add_argument('--confidence-threshold', type=float, default=0.65,
                          help='Minimum confidence to report matches')
        parser.add_argument('--output-format', choices=['json', 'table'], default='table',
                          help='Output format')
        parser.add_argument('--no-fuzzy', action='store_true',
                          help='Disable fuzzy matching')
        parser.add_argument('--cache', action='store_true', default=True,
                          help='Enable API response caching')
        parser.add_argument('--verbose', '-v', action='store_true',
                          help='Verbose output')
        
        return parser
        
    async def run(self, args: List[str] = None):
        """Main CLI entry point"""
        parsed_args = self.parser.parse_args(args)
        
        config = SHPIConfig(
            max_depth=parsed_args.max_depth,
            report_match_threshold=parsed_args.confidence_threshold,
            cache_enabled=parsed_args.cache
        )
        
        identifier = SHPackageIdentifier(config)
        
        try:
            matches = await identifier.identify_packages(Path(parsed_args.path))
            
            if parsed_args.output_format == 'json':
                self._output_json(matches)
            else:
                self._output_table(matches)
                
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    def _output_json(self, matches: List[PackageMatch]):
        """Output results as JSON"""
        output = {
            'matches': [match.to_dict() for match in matches],
            'count': len(matches),
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(output, indent=2))
        
    def _output_table(self, matches: List[PackageMatch]):
        """Output results as formatted table"""
        if not matches:
            print("No package matches found.")
            return
            
        # Use tabulate or similar for formatted output
        headers = ['Name', 'Version', 'Confidence', 'License', 'PURL', 'Download URL']
        rows = []
        for match in matches:
            rows.append([
                match.name or 'Unknown',
                match.version or 'Unknown',
                f"{match.confidence_score:.2f}",
                match.license or 'Unknown',
                match.purl or 'N/A',
                match.download_url[:60] + '...' if len(match.download_url) > 60 else match.download_url
            ])
            
        print(tabulate(rows, headers=headers, tablefmt='grid'))
```

## Experimental Features (Require Testing)

### License Detection Integration
```python
# NOTE: Experimental - integration with semantic-copycat-oslili
class LicenseDetector:
    """
    Optional integration with external license detection tools
    """
    
    def detect_license(self, path: Path) -> Optional[str]:
        """Detect license using external tools or heuristics"""
        # Integration point for semantic-copycat-oslili
        # Or fallback to simple LICENSE file detection
        pass
```

### C++ Specific Detection
```python
# NOTE: Experimental - C++ ecosystem specific heuristics
class CppPackageDetector:
    """
    C++ specific package detection heuristics
    """
    
    def classify_cpp_library(self, path: Path) -> str:
        """Classify as header-only, compiled, etc."""
        pass
        
    def extract_cmake_metadata(self, path: Path) -> Dict[str, str]:
        """Extract package info from CMakeLists.txt"""
        pass
        
    def detect_build_system(self, path: Path) -> List[str]:
        """Detect cmake, autotools, meson, bazel, etc."""
        pass
```

## Installation & Usage

### Dependencies
```txt
# requirements.txt
aiohttp>=3.8.0
miniswhid>=0.1.0  # or implement custom SWHID generation
tabulate>=0.9.0
click>=8.0.0  # Alternative to argparse
```

### Usage Examples
```bash
# Basic usage
shpi /path/to/source/code

# High confidence only
shpi /path/to/source --confidence-threshold 0.85

# JSON output
shpi /path/to/source --output-format json

# Disable fuzzy matching for speed
shpi /path/to/source --no-fuzzy

# Verbose debugging
shpi /path/to/source -v
```

## Testing Strategy

### Unit Tests Required
- SWHID generation correctness
- API client error handling
- Confidence scoring algorithm
- PURL generation validation

### Integration Tests Required
- End-to-end with known packages (OpenCV, Boost)
- Rate limiting behavior
- Cache functionality
- Fuzzy matching accuracy

### Experimental Validation Needed
- Fuzzy matching algorithm effectiveness
- C++ specific detection accuracy
- Performance with large directory trees
- SH API query optimization

## Performance Considerations

### Optimization Targets
- Minimize SH API calls through intelligent caching
- Parallel processing of directory candidates
- Early termination on high-confidence exact matches
- Efficient fuzzy matching algorithms

### Expected Bottlenecks
- SH API rate limiting
- Large directory tree traversal
- Fuzzy matching computational cost
- Network latency for API calls

## Future Enhancements

### Phase 2 Features
- Support for more package ecosystems
- Integration with package manager databases
- Batch processing of multiple directories
- Web UI for interactive exploration

### Advanced Features
- Machine learning for improved matching
- Custom package coordinate systems
- Enterprise deployment support
- API server mode

