"""Main orchestrator for the SH Package Identifier."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src2id.core.config import SWHPIConfig
from src2id.core.models import DirectoryCandidate, ContentCandidate, MatchType, PackageMatch, SHOriginMatch
from src2id.search import SourceIdentifier, create_default_registry

console = Console()


class SHPackageIdentifier:
    """Main orchestrator class that coordinates all components."""
    
    def __init__(self, config: Optional[SWHPIConfig] = None):
        """Initialize the package identifier with configuration."""
        self.config = config or SWHPIConfig()
        
        # Components will be lazily initialized
        self._swhid_generator = None
        self._sh_client = None
        self._scanner = None
        self._coordinate_extractor = None
        self._confidence_scorer = None
        self._purl_generator = None
        self._source_identifier = None
        self._search_registry = None
        self._upmex_integration = None
    
    @property
    def swhid_generator(self):
        """Lazy load SWHID generator."""
        if self._swhid_generator is None:
            from src2id.core.swhid import SWHIDGenerator
            self._swhid_generator = SWHIDGenerator()
        return self._swhid_generator
    
    @property
    def sh_client(self):
        """Lazy load Software Heritage client."""
        if self._sh_client is None:
            from src2id.core.client import SoftwareHeritageClient
            self._sh_client = SoftwareHeritageClient(self.config)
        return self._sh_client
    
    @property
    def scanner(self):
        """Lazy load directory scanner."""
        if self._scanner is None:
            from src2id.core.scanner import DirectoryScanner
            self._scanner = DirectoryScanner(self.config, self.swhid_generator)
        return self._scanner
    
    @property
    def coordinate_extractor(self):
        """Lazy load package coordinate extractor."""
        if self._coordinate_extractor is None:
            from src2id.core.extractor import PackageCoordinateExtractor
            self._coordinate_extractor = PackageCoordinateExtractor()
        return self._coordinate_extractor
    
    @property
    def confidence_scorer(self):
        """Lazy load confidence scorer."""
        if self._confidence_scorer is None:
            from src2id.core.scorer import ConfidenceScorer
            self._confidence_scorer = ConfidenceScorer(self.config)
        return self._confidence_scorer
    
    @property
    def purl_generator(self):
        """Lazy load PURL generator."""
        if self._purl_generator is None:
            from src2id.core.purl import PURLGenerator
            self._purl_generator = PURLGenerator()
        return self._purl_generator
    
    @property
    def source_identifier(self):
        """Lazy load source identifier."""
        if self._source_identifier is None:
            self._source_identifier = SourceIdentifier(
                swh_client=self.sh_client,
                search_registry=self.search_registry,
                verbose=self.config.verbose
            )
        return self._source_identifier
    
    @property
    def search_registry(self):
        """Lazy load search provider registry."""
        if self._search_registry is None:
            self._search_registry = create_default_registry(verbose=self.config.verbose)
        return self._search_registry

    @property
    def upmex_integration(self):
        """Lazy load UPMEX integration."""
        if self._upmex_integration is None:
            from src2id.integrations.upmex import UpmexIntegration
            self._upmex_integration = UpmexIntegration(enabled=True)
        return self._upmex_integration
    
    async def identify_packages(self, path: Path, enhance_licenses: bool = True) -> List[PackageMatch]:
        """
        Main entry point for package identification.
        
        Args:
            path: Directory path to analyze
            enhance_licenses: Whether to use oslili for license enhancement
            
        Returns:
            List of package matches found
        """
        try:
            if self.config.verbose:
                console.print("[bold blue]Starting package identification...[/bold blue]")

            # Step 1: PRIMARY - Hash-based discovery (SWHIDs + Software Heritage + Web Search)
            if self.config.verbose:
                console.print("[bold blue]Phase 1: Hash-based package discovery[/bold blue]")

            dir_candidates, file_candidates = await self._scan_directories(path)
            
            # Phase 1: Hash-based discovery
            hash_based_matches = []

            if dir_candidates or file_candidates:
                # Step 1a: Query for matches based on configuration
                if self.config.use_swh:
                    # Query Software Heritage for matches (both dirs and files)
                    all_matches = await self._find_matches(dir_candidates, file_candidates)
                else:
                    all_matches = []
                    if self.config.verbose:
                        console.print("[dim]Skipping Software Heritage (use --use-swh to enable)[/dim]")

                if not all_matches:
                    # Try keyword search with GitHub and SCANOSS
                    if self.config.verbose:
                        console.print("[yellow]Trying web search (GitHub, SCANOSS)[/yellow]")

                    # Try keyword search
                    keyword_matches = await self._find_keyword_matches(path)
                    if keyword_matches:
                        all_matches = keyword_matches

                # Step 1b: Process hash-based matches
                if all_matches:
                    hash_based_matches = await self._process_matches(all_matches)
                    if self.config.verbose:
                        console.print(f"[green]✓ Phase 1 complete: Found {len(hash_based_matches)} packages via hash-based discovery[/green]")
                else:
                    if self.config.verbose:
                        console.print("[yellow]Phase 1 complete: No packages found via hash-based discovery[/yellow]")

            # Phase 2: Manifest-based enhancement and supplementation (TEMP DISABLED FOR TESTING)
            if self.config.verbose:
                console.print("[bold blue]Phase 2: Manifest-based validation and enhancement (DISABLED FOR TESTING)[/bold blue]")

            # TEMPORARILY DISABLE FOR PERFORMANCE TESTING
            manifest_matches = []
            enhanced_matches = hash_based_matches

            if self.config.verbose:
                hash_count = len(hash_based_matches)
                manifest_count = len(manifest_matches)
                final_count = len(enhanced_matches)
                console.print(f"[green]✓ Phase 2 complete: {hash_count} hash-based + {manifest_count} manifest-based = {final_count} total packages[/green]")

            # Final deduplication and sorting
            final_matches = self._prioritize_and_deduplicate(enhanced_matches)
            
            # Step 5: Optionally enhance with oslili license detection
            if enhance_licenses:
                try:
                    from src2id.integrations.oslili import enhance_with_oslili
                    final_matches = enhance_with_oslili(final_matches, path)
                    # License enhancement is now silent by default
                except ImportError:
                    if self.config.verbose:
                        console.print("[yellow]oslili not available for license enhancement[/yellow]")
            
            # Match count is now shown in CLI output, not here
            
            return final_matches
        finally:
            # Clean up the session if it was created
            if self._sh_client is not None:
                await self._sh_client.close_session()

    def _extract_with_upmex(self, path: Path) -> List[PackageMatch]:
        """
        Try to extract package metadata directly using UPMEX.

        Args:
            path: Directory path to analyze

        Returns:
            List of package matches found via direct metadata extraction
        """
        if not self.upmex_integration.enabled:
            return []

        try:
            matches = self.upmex_integration.extract_metadata_from_directory(path)

            if self.config.verbose and matches:
                console.print("[green]Found package metadata files:[/green]")
                for match in matches:
                    if match.name:
                        console.print(f"  [green]📦 {match.name} v{match.version or 'unknown'}[/green]")
                        if match.license:
                            console.print(f"    License: {match.license}")
                        if match.purl:
                            console.print(f"    PURL: {match.purl}")

            return matches

        except Exception as e:
            if self.config.verbose:
                console.print(f"[yellow]UPMEX extraction failed: {e}[/yellow]")
            return []

    def _merge_and_enhance_matches(
        self,
        hash_based_matches: List[PackageMatch],
        manifest_matches: List[PackageMatch],
        path: Path
    ) -> List[PackageMatch]:
        """
        Intelligently merge hash-based and manifest-based matches.

        Strategy:
        1. Use manifest data to enhance/validate hash-based matches
        2. Add manifest-only packages as supplementary findings
        3. Prefer hash-based discovery but enhance with manifest precision

        Args:
            hash_based_matches: Packages found via SWHID/Software Heritage
            manifest_matches: Packages found via manifest parsing
            path: The scanned directory path

        Returns:
            Enhanced and merged list of package matches
        """
        if not manifest_matches:
            return hash_based_matches

        if not hash_based_matches:
            # Only manifest matches found - add them all as supplementary
            if self.config.verbose:
                console.print(f"[blue]Adding {len(manifest_matches)} manifest-only packages[/blue]")
            return manifest_matches

        # Create enhanced results starting with hash-based matches
        enhanced_matches = list(hash_based_matches)

        # Create lookup for hash-based matches by normalized name/URL
        hash_lookup = {}
        for match in hash_based_matches:
            # Try multiple keys for matching
            keys = []
            if match.name:
                keys.append(match.name.lower())
                # Handle different name formats (e.g., "org:artifact" vs "artifact")
                if ':' in match.name:
                    keys.append(match.name.split(':')[-1].lower())
            if match.download_url:
                # Normalize URL for matching
                normalized_url = self._normalize_url_for_matching(match.download_url)
                keys.append(normalized_url)

            for key in keys:
                hash_lookup[key] = match

        # Process manifest matches
        supplementary_count = 0
        enhanced_count = 0

        for manifest_match in manifest_matches:
            # Try to find corresponding hash-based match
            corresponding_hash_match = None

            # Check by name
            if manifest_match.name:
                name_key = manifest_match.name.lower()
                if name_key in hash_lookup:
                    corresponding_hash_match = hash_lookup[name_key]
                elif ':' in manifest_match.name:
                    # Try just the artifact name
                    artifact_key = manifest_match.name.split(':')[-1].lower()
                    if artifact_key in hash_lookup:
                        corresponding_hash_match = hash_lookup[artifact_key]

            # Check by URL if no name match
            if not corresponding_hash_match and manifest_match.download_url:
                url_key = self._normalize_url_for_matching(manifest_match.download_url)
                if url_key in hash_lookup:
                    corresponding_hash_match = hash_lookup[url_key]

            if corresponding_hash_match:
                # ENHANCE: Update hash-based match with manifest precision
                enhanced_count += 1
                if self.config.verbose:
                    console.print(f"[cyan]Enhanced {corresponding_hash_match.name or 'package'} with manifest data[/cyan]")

                # Keep hash-based match but enhance with manifest data
                if manifest_match.version and not corresponding_hash_match.version:
                    corresponding_hash_match.version = manifest_match.version

                if manifest_match.license and not corresponding_hash_match.license:
                    corresponding_hash_match.license = manifest_match.license
                elif manifest_match.license and corresponding_hash_match.license:
                    # Combine licenses if different
                    if manifest_match.license not in corresponding_hash_match.license:
                        corresponding_hash_match.license = f"{corresponding_hash_match.license}, {manifest_match.license}"

                if manifest_match.purl and not corresponding_hash_match.purl:
                    corresponding_hash_match.purl = manifest_match.purl

                # Boost confidence slightly for validation
                corresponding_hash_match.confidence_score = min(1.0, corresponding_hash_match.confidence_score + 0.05)

            else:
                # SUPPLEMENT: Add manifest-only package
                supplementary_count += 1
                if self.config.verbose:
                    console.print(f"[blue]Added supplementary package: {manifest_match.name or 'unknown'}[/blue]")

                # Slightly lower confidence for manifest-only packages
                manifest_match.confidence_score = min(0.85, manifest_match.confidence_score)
                enhanced_matches.append(manifest_match)

        if self.config.verbose and (enhanced_count > 0 or supplementary_count > 0):
            console.print(f"[green]✓ Enhanced {enhanced_count} packages, added {supplementary_count} supplementary packages[/green]")

        return enhanced_matches

    def _normalize_url_for_matching(self, url: str) -> str:
        """Normalize URL for matching between hash-based and manifest-based results."""
        if not url:
            return ""

        # Remove protocol and common suffixes
        normalized = url.lower()
        normalized = normalized.replace('https://', '').replace('http://', '')
        normalized = normalized.replace('.git', '')
        normalized = normalized.rstrip('/')

        # Extract key parts for matching using proper URL parsing
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}')
            hostname = parsed.hostname.lower() if parsed.hostname else ''
            path_parts = parsed.path.strip('/').split('/')

            if hostname == 'github.com' and len(path_parts) >= 2:
                return f"github.com/{path_parts[0]}/{path_parts[1]}"
            elif hostname == 'gitlab.com' and len(path_parts) >= 2:
                return f"gitlab.com/{path_parts[0]}/{path_parts[1]}"
        except Exception:
            pass

        return normalized
    
    async def _scan_directories(self, path: Path) -> Tuple[List[DirectoryCandidate], List[ContentCandidate]]:
        """Scan directories and files to generate SWHID candidates."""
        if self.config.verbose:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Scanning directories and files...", total=None)
                
                # Scan the main path - returns both dirs and files
                dir_candidates, file_candidates = self.scanner.scan_recursive(path)
                
                # Also scan subdirectories for better matching
                progress.update(task, description="Scanning subdirectories...")
                subdirs = await self._scan_subdirectories(path)
                dir_candidates.extend(subdirs)
                
                progress.update(task, completed=True)
        else:
            dir_candidates, file_candidates = self.scanner.scan_recursive(path)
            subdirs = await self._scan_subdirectories(path)
            dir_candidates.extend(subdirs)
        
        # Remove duplicate directories based on SWHID
        seen_swhids = set()
        unique_dirs = []
        for candidate in dir_candidates:
            if candidate.swhid not in seen_swhids:
                seen_swhids.add(candidate.swhid)
                unique_dirs.append(candidate)
        
        if self.config.verbose:
            console.print(f"[dim]Generated {len(unique_dirs)} directory candidates and {len(file_candidates)} file candidates[/dim]")
            # Show breakdown
            target_count = sum(1 for c in unique_dirs if c.path == path)
            parent_count = sum(1 for c in unique_dirs if path in c.path.parents)
            child_count = sum(1 for c in unique_dirs if c.path.parent == path)
            
            if child_count > 0 or file_candidates:
                console.print(f"[dim]  → Directories: {len(unique_dirs)} (Target: {target_count}, Parents: {parent_count}, Children: {child_count})[/dim]")
                console.print(f"[dim]  → Files: {len(file_candidates)} collected[/dim]")
        
        return unique_dirs, file_candidates
    
    async def _scan_subdirectories(self, path: Path) -> List[DirectoryCandidate]:
        """Scan immediate subdirectories for better matching."""
        candidates = []
        
        # Priority directories that rarely change
        priority_dirs = ['cmake', 'docs', 'doc', 'tools', 'packaging', 
                        'data', 'po', 'translations', 'config', 'scripts']
        
        subdirs_checked = 0
        max_subdirs = 10
        
        # Check priority directories first
        for dir_name in priority_dirs:
            if subdirs_checked >= max_subdirs:
                break
                
            subdir = path / dir_name
            if subdir.exists() and subdir.is_dir():
                try:
                    from src2id.core.models import DirectoryCandidate
                    
                    file_count = sum(1 for _ in subdir.rglob('*') if _.is_file())
                    if file_count >= 3:  # Low threshold for subdirs
                        swhid = self.swhid_generator.generate_directory_swhid(subdir)
                        
                        candidate = DirectoryCandidate(
                            path=subdir,
                            swhid=swhid,
                            depth=1,
                            specificity_score=0.8,  # High score for stable dirs
                            file_count=file_count
                        )
                        candidates.append(candidate)
                        subdirs_checked += 1
                        
                except (PermissionError, OSError):
                    continue
        
        return candidates
    
    async def _find_matches(self, dir_candidates: List[DirectoryCandidate], file_candidates: List[ContentCandidate]) -> List[SHOriginMatch]:
        """Find matches in Software Heritage for all candidates (dirs and files)."""
        all_matches = []
        # Find the most specific path (highest specificity score) as target
        target_path = max(dir_candidates, key=lambda c: c.specificity_score).path if dir_candidates else None
        
        # Track match statistics
        parent_matches = 0
        child_matches = 0
        target_match = False
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=not self.config.verbose,
        ) as progress:
            task = progress.add_task(
                "Checking archive status (batch)...", 
                total=len(dir_candidates) + len(file_candidates)
            )
            
            # Batch check all SWHIDs (both dirs and files) for efficiency
            all_swhids = []
            swhid_to_candidate = {}
            
            # Add directory SWHIDs
            for candidate in dir_candidates:
                all_swhids.append(candidate.swhid)
                swhid_to_candidate[candidate.swhid] = ("dir", candidate)
            
            # Add file SWHIDs
            for candidate in file_candidates:
                all_swhids.append(candidate.swhid)
                swhid_to_candidate[candidate.swhid] = ("file", candidate)
            
            if self.config.verbose:
                console.print(f"[dim]Batch checking {len(all_swhids)} SWHIDs ({len(dir_candidates)} dirs, {len(file_candidates)} files)...[/dim]")
            
            known_status = await self.sh_client.check_swhids_known(all_swhids)
            
            # Filter to only items that exist in archive
            existing_dirs = []
            existing_files = []
            
            for swhid, is_known in known_status.items():
                if is_known:
                    # Convert CoreSWHID back to string if needed
                    swhid_str = str(swhid) if not isinstance(swhid, str) else swhid
                    if swhid_str in swhid_to_candidate:
                        item_type, candidate = swhid_to_candidate[swhid_str]
                        if item_type == "dir":
                            existing_dirs.append(candidate)
                        else:
                            existing_files.append(candidate)
            
            if self.config.verbose:
                dirs_found = len(existing_dirs)
                files_found = len(existing_files)
                total_dirs = len(dir_candidates)
                total_files = len(file_candidates)
                console.print(f"[dim]Found {dirs_found}/{total_dirs} directories and {files_found}/{total_files} files in archive[/dim]")
            
            # Now get detailed origins info for existing directories
            # Note: Files don't have origins, but we can report them as found
            progress.update(task, description="Getting origin details...")
            
            # Report found files
            if self.config.verbose and existing_files:
                console.print(f"[green]✓ Found {len(existing_files)} files in archive:[/green]")
                for file_candidate in existing_files[:10]:  # Show first 10
                    rel_path = file_candidate.path.name
                    console.print(f"  [green]📄 {rel_path}[/green]")
                if len(existing_files) > 10:
                    console.print(f"  [dim]... and {len(existing_files) - 10} more files[/dim]")
            
            # Process directories for origin information
            for candidate in existing_dirs:
                # Determine relationship
                if target_path:
                    if candidate.path == target_path:
                        relationship = "target"
                    elif candidate.path.parent == target_path:
                        relationship = "child"
                    elif target_path in candidate.path.parents:
                        relationship = "parent"
                    else:
                        relationship = "other"
                else:
                    relationship = "unknown"
                
                # Get detailed origin information for known directories
                if self.config.verbose:
                    console.print(f"[dim]Getting origins: {candidate.swhid}[/dim]")
                exact_matches = await self._find_exact_matches(candidate)
                
                if exact_matches:
                    all_matches.extend(exact_matches)
                    
                    # Update statistics
                    if relationship == "target":
                        target_match = True
                    elif relationship == "child":
                        child_matches += 1
                    elif relationship == "parent":
                        parent_matches += 1
                    
                    if self.config.verbose:
                        if relationship == "child":
                            console.print(
                                f"[green]✓ Found exact match for subdirectory: {candidate.path.name}[/green]"
                            )
                        else:
                            console.print(
                                f"[green]✓ Found exact match for {candidate.path.name}[/green]"
                            )
                    # Early termination on high-confidence exact match
                    if any(self._is_high_confidence_match(m) for m in exact_matches):
                        break
                
                progress.advance(task)
            
        # Log non-existing directories in verbose mode
        if self.config.verbose:
            non_existing_dirs = [
                candidate for candidate in dir_candidates 
                if not known_status.get(candidate.swhid, False)
            ]
            for candidate in non_existing_dirs:
                console.print(f"[yellow]✗ No match for {candidate.path.name} ({candidate.swhid[:12]}...)[/yellow]")
        
        # Try keyword search fallback if no exact matches and fuzzy is enabled
        if not all_matches and self.config.enable_fuzzy_matching:
            if self.config.verbose:
                console.print("[yellow]No exact matches found - trying keyword search[/yellow]")
            # Only try keyword search if fuzzy matching is enabled
            keyword_matches = await self._find_keyword_matches(dir_candidates[0].path if dir_candidates else Path("."))
            all_matches.extend(keyword_matches)
        
        # Report match summary
        if self.config.verbose and (child_matches > 0 or parent_matches > 0):
            console.print("\n[bold]Match Summary:[/bold]")
            if target_match:
                console.print("  [green]✓ Target directory found in archive[/green]")
            else:
                console.print("  [yellow]✗ Target directory not found[/yellow]")
            
            if child_matches > 0:
                console.print(f"  [green]✓ {child_matches} subdirectories found in archive[/green]")
                console.print("    [dim]→ Subdirectory matches indicate partial repository presence[/dim]")
            
            if parent_matches > 0:
                console.print(f"  [blue]ℹ {parent_matches} parent directories checked[/blue]")
        
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
        # Not implemented yet - placeholder for Issue #9
        return []
    
    async def _find_keyword_matches(self, path: Path) -> List[SHOriginMatch]:
        """Find matches by searching for project name keywords."""
        # Extract potential project name from path
        # Walk up the path to find the most likely project name
        parts = path.parts
        
        # Common subdirectory names to skip
        skip_dirs = {'packaging', 'src', 'lib', 'bin', 'build', 'dist', 'test', 
                    'tests', 'test_data', 'Projects', 'tmp', 'temp', 'vendor',
                    'node_modules', '.git', 'docs', 'doc', 'cmake', 'po', 'data'}
        
        keywords_to_try = []
        
        # Try to find the project name by walking up the path
        for i in range(len(parts) - 1, -1, -1):
            part = parts[i]
            if part not in skip_dirs and not part.startswith('.'):
                keywords_to_try.append(part)
                break
        
        # If we didn't find anything, use the immediate parent if it's not a skip dir
        if not keywords_to_try and path.parent.name not in skip_dirs:
            keywords_to_try.append(path.parent.name)
        
        # As a last resort, use the current directory name if it's not generic
        if not keywords_to_try and path.name not in skip_dirs:
            keywords_to_try.append(path.name)
        
        all_origin_urls = set()
        origin_matches = []
        
        for keyword in keywords_to_try:
            if self.config.verbose:
                console.print(f"[dim]Searching for origins with keyword: {keyword}[/dim]")
            
            try:
                origins = await self.sh_client.search_origins_by_keyword(keyword)
                
                for origin_data in origins:
                    url = origin_data.get('url', '')
                    if url and url not in all_origin_urls:
                        all_origin_urls.add(url)
                        
                        # Calculate similarity score based on URL matching
                        similarity_score = 0.5  # Base score for keyword match
                        
                        # Boost score for official organization matches
                        if f"{keyword}-org" in url.lower() or f"/{keyword}/{keyword}" in url.lower():
                            similarity_score = 0.9
                        elif f"/{keyword}/" in url.lower() or url.lower().endswith(f"/{keyword}"):
                            similarity_score = 0.7
                        elif keyword.lower() in url.lower():
                            similarity_score = 0.6
                        
                        # Create a match for each origin found
                        origin_match = SHOriginMatch(
                            origin_url=url,
                            swhid="",  # No specific SWHID since this is keyword search
                            last_seen=datetime.now(),
                            visit_count=1,
                            metadata={'keyword_match': keyword},
                            match_type=MatchType.FUZZY,
                            similarity_score=similarity_score
                        )
                        origin_matches.append(origin_match)
                        
                        if self.config.verbose and len(origin_matches) <= 3:
                            console.print(f"  [green]→ Found: {url} (score: {similarity_score:.2f})[/green]")
            except Exception as e:
                if self.config.verbose:
                    console.print(f"[red]Error searching for keyword {keyword}: {e}[/red]")
        
        if self.config.verbose and origin_matches:
            console.print(f"[green]Found {len(origin_matches)} potential matches via keyword search[/green]")
        
        # Sort by similarity score (highest first) and return top matches
        origin_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return origin_matches[:10]  # Limit to top 10 matches
    
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
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.hostname.lower() if parsed.hostname else ''

            if hostname in ('github.com', 'gitlab.com'):
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    return f"{parsed.scheme}://{hostname}/{path_parts[0]}/{path_parts[1]}"
        except Exception:
            pass
        return url
    
    def _is_high_confidence_match(self, match: SHOriginMatch) -> bool:
        """Check if a match is high confidence for early termination."""
        # Simple heuristic - can be improved
        return (
            match.match_type.value == "exact" and
            match.visit_count > 10 and
            self.coordinate_extractor.is_official_organization(match.origin_url)
        )