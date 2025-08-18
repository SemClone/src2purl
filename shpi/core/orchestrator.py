"""Main orchestrator for the SH Package Identifier."""

import asyncio
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from shpi.core.config import SHPIConfig
from shpi.core.models import DirectoryCandidate, PackageMatch, SHOriginMatch

console = Console()


class SHPackageIdentifier:
    """Main orchestrator class that coordinates all components."""
    
    def __init__(self, config: Optional[SHPIConfig] = None):
        """Initialize the package identifier with configuration."""
        self.config = config or SHPIConfig()
        
        # Components will be lazily initialized
        self._swhid_generator = None
        self._sh_client = None
        self._scanner = None
        self._fuzzy_matcher = None
        self._coordinate_extractor = None
        self._confidence_scorer = None
        self._purl_generator = None
    
    @property
    def swhid_generator(self):
        """Lazy load SWHID generator."""
        if self._swhid_generator is None:
            from shpi.core.swhid import SWHIDGenerator
            self._swhid_generator = SWHIDGenerator()
        return self._swhid_generator
    
    @property
    def sh_client(self):
        """Lazy load Software Heritage client."""
        if self._sh_client is None:
            from shpi.core.client import SoftwareHeritageClient
            self._sh_client = SoftwareHeritageClient(self.config)
        return self._sh_client
    
    @property
    def scanner(self):
        """Lazy load directory scanner."""
        if self._scanner is None:
            from shpi.core.scanner import DirectoryScanner
            self._scanner = DirectoryScanner(self.config, self.swhid_generator)
        return self._scanner
    
    @property
    def coordinate_extractor(self):
        """Lazy load package coordinate extractor."""
        if self._coordinate_extractor is None:
            from shpi.core.extractor import PackageCoordinateExtractor
            self._coordinate_extractor = PackageCoordinateExtractor()
        return self._coordinate_extractor
    
    @property
    def confidence_scorer(self):
        """Lazy load confidence scorer."""
        if self._confidence_scorer is None:
            from shpi.core.scorer import ConfidenceScorer
            self._confidence_scorer = ConfidenceScorer(self.config)
        return self._confidence_scorer
    
    @property
    def purl_generator(self):
        """Lazy load PURL generator."""
        if self._purl_generator is None:
            from shpi.core.purl import PURLGenerator
            self._purl_generator = PURLGenerator()
        return self._purl_generator
    
    async def identify_packages(self, path: Path) -> List[PackageMatch]:
        """
        Main entry point for package identification.
        
        Args:
            path: Directory path to analyze
            
        Returns:
            List of package matches found
        """
        try:
            if self.config.verbose:
                console.print("[bold blue]Starting package identification...[/bold blue]")
            
            # Step 1: Scan directories and generate candidates
            candidates = await self._scan_directories(path)
            
            if not candidates:
                if self.config.verbose:
                    console.print("[yellow]No valid directories found to scan[/yellow]")
                return []
            
            # Step 2: Query Software Heritage for matches
            all_matches = await self._find_matches(candidates)
            
            if not all_matches:
                if self.config.verbose:
                    console.print("[yellow]No matches found in Software Heritage[/yellow]")
                return []
            
            # Step 3: Process matches and extract package information
            package_matches = await self._process_matches(all_matches)
            
            # Step 4: Sort and deduplicate results
            final_matches = self._prioritize_and_deduplicate(package_matches)
            
            if self.config.verbose:
                console.print(f"[green]Found {len(final_matches)} package matches[/green]")
            
            return final_matches
        finally:
            # Clean up the session if it was created
            if self._sh_client is not None:
                await self._sh_client.close_session()
    
    async def _scan_directories(self, path: Path) -> List[DirectoryCandidate]:
        """Scan directories and generate SWHID candidates."""
        if self.config.verbose:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Scanning directories...", total=None)
                candidates = self.scanner.scan_recursive(path)
                progress.update(task, completed=True)
        else:
            candidates = self.scanner.scan_recursive(path)
        
        if self.config.verbose:
            console.print(f"[dim]Generated {len(candidates)} directory candidates[/dim]")
        
        return candidates
    
    async def _find_matches(self, candidates: List[DirectoryCandidate]) -> List[SHOriginMatch]:
        """Find matches in Software Heritage for all candidates."""
        all_matches = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=not self.config.verbose,
        ) as progress:
            task = progress.add_task(
                "Querying Software Heritage...", 
                total=len(candidates)
            )
            
            for candidate in candidates:
                # Try exact match first
                exact_matches = await self._find_exact_matches(candidate)
                
                if exact_matches:
                    all_matches.extend(exact_matches)
                    if self.config.verbose:
                        console.print(
                            f"[green]Found exact match for {candidate.path.name}[/green]"
                        )
                    # Early termination on high-confidence exact match
                    if any(self._is_high_confidence_match(m) for m in exact_matches):
                        break
                elif self.config.enable_fuzzy_matching:
                    # Try fuzzy matching if no exact matches
                    fuzzy_matches = await self._find_fuzzy_matches(candidate)
                    all_matches.extend(fuzzy_matches)
                    if fuzzy_matches and self.config.verbose:
                        console.print(
                            f"[yellow]Found fuzzy match for {candidate.path.name}[/yellow]"
                        )
                
                progress.update(task, advance=1)
        
        return all_matches
    
    async def _find_exact_matches(self, candidate: DirectoryCandidate) -> List[SHOriginMatch]:
        """Find exact SWHID matches in Software Heritage."""
        try:
            return await self.sh_client.get_directory_origins(candidate.swhid)
        except Exception as e:
            if self.config.verbose:
                console.print(f"[red]Error querying SH for {candidate.swhid}: {e}[/red]")
            return []
    
    async def _find_fuzzy_matches(self, candidate: DirectoryCandidate) -> List[SHOriginMatch]:
        """Find fuzzy matches using similarity algorithms."""
        # Placeholder for fuzzy matching implementation
        # This will be implemented when we add the fuzzy matcher
        return []
    
    async def _process_matches(
        self, matches: List[SHOriginMatch]
    ) -> List[PackageMatch]:
        """Process matches to extract package information."""
        package_matches = []
        
        for match in matches:
            # Extract package coordinates
            coordinates = self.coordinate_extractor.extract_coordinates(match)
            
            # Calculate confidence score
            confidence = self.confidence_scorer.calculate_confidence({
                'match_type': match.match_type,
                'similarity_score': getattr(match, 'similarity_score', 1.0),
                'frequency_rank': match.visit_count,
                'is_official_org': self.coordinate_extractor.is_official_organization(
                    match.origin_url
                ),
                'last_activity': match.last_seen
            })
            
            # Skip low confidence matches
            if confidence < self.config.report_match_threshold:
                continue
            
            # Generate PURL if confidence is high enough
            purl = None
            if confidence >= self.config.purl_generation_threshold:
                purl = self.purl_generator.generate_purl(coordinates, confidence)
            
            package_match = PackageMatch(
                download_url=coordinates.get('download_url', match.origin_url),
                name=coordinates.get('name'),
                version=coordinates.get('version'),
                license=coordinates.get('license'),
                sh_url=f"{self.config.sh_api_base}/directory/{match.swhid}/",
                match_type=match.match_type,
                confidence_score=confidence,
                frequency_count=match.visit_count,
                is_official_org=self.coordinate_extractor.is_official_organization(
                    match.origin_url
                ),
                purl=purl
            )
            package_matches.append(package_match)
        
        return package_matches
    
    def _prioritize_and_deduplicate(
        self, matches: List[PackageMatch]
    ) -> List[PackageMatch]:
        """Sort by confidence and remove duplicates."""
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
    
    def _extract_base_repo_url(self, url: str) -> str:
        """Extract base repository URL for deduplication."""
        # Simple extraction - can be improved
        if 'github.com' in url or 'gitlab.com' in url:
            parts = url.split('/')
            if len(parts) >= 5:
                return '/'.join(parts[:5])
        return url
    
    def _is_high_confidence_match(self, match: SHOriginMatch) -> bool:
        """Check if a match is high confidence for early termination."""
        # Simple heuristic - can be improved
        return (
            match.match_type.value == "exact" and
            match.visit_count > 10 and
            self.coordinate_extractor.is_official_organization(match.origin_url)
        )