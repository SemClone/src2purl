"""Unified source identification strategies."""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter

from rich.console import Console
from rich.table import Table

from ..core.models import DirectoryCandidate, ContentCandidate
from ..core.scanner import DirectoryScanner
from ..core.client import SoftwareHeritageClient
from .hash_search import HashSearcher
from .providers import (
    SearchProviderRegistry,
    create_default_registry,
    SCANOSSProvider
)

console = Console()


class SourceIdentifier:
    """Unified source identification using multiple strategies."""
    
    def __init__(
        self,
        swh_client: Optional[SoftwareHeritageClient] = None,
        search_registry: Optional[SearchProviderRegistry] = None,
        verbose: bool = False
    ):
        """Initialize the source identifier.
        
        Args:
            swh_client: Software Heritage client instance
            search_registry: Registry of search providers
            verbose: Enable verbose output
        """
        # Only store the client if provided, don't create it automatically
        self.swh_client = swh_client
        self.search_registry = search_registry or create_default_registry(verbose=verbose)
        self.verbose = verbose
        self.hash_searcher = HashSearcher(verbose=verbose)
        self._swh_config = None  # Store config for lazy initialization
    
    async def identify(
        self,
        path: Path,
        max_depth: int = 3,
        confidence_threshold: float = 0.5,
        strategies: Optional[List[str]] = None,
        use_swh: bool = False
    ) -> Dict[str, Any]:
        """Identify the source of a directory using multiple strategies.
        
        Args:
            path: Path to analyze
            max_depth: Maximum depth for recursive scanning
            confidence_threshold: Minimum confidence for identification
            strategies: List of strategies to use (default: optimized order)
            use_swh: Whether to include Software Heritage checking
            
        Returns:
            Dictionary with identification results
        """
        results = {
            "path": str(path),
            "identified": False,
            "confidence": 0.0,
            "strategies_used": [],
            "candidates": [],
            "final_origin": None
        }
        
        available_strategies = {
            "hash_search": self._identify_via_hash_search,
            "web_search": self._identify_via_web_search,
            "scanoss": self._identify_via_scanoss,
            "swh": self._identify_via_swh
        }
        
        # Default optimized order (local methods first, then external APIs)
        if strategies is None:
            strategies_to_use = ["hash_search", "web_search", "scanoss"]
            if use_swh:
                strategies_to_use.append("swh")
        else:
            strategies_to_use = strategies
        
        all_candidates = []
        
        for strategy_name in strategies_to_use:
            if strategy_name not in available_strategies:
                continue
                
            strategy_func = available_strategies[strategy_name]
            
            try:
                if self.verbose:
                    console.print(f"[cyan]Running {strategy_name} strategy...[/cyan]")
                
                candidates = await strategy_func(path, max_depth)
                
                if candidates:
                    all_candidates.extend(candidates)
                    results["strategies_used"].append(strategy_name)
                    
                    if self.verbose:
                        console.print(f"[green]✓ {strategy_name} found {len(candidates)} candidates[/green]")
                        
            except Exception as e:
                if self.verbose:
                    console.print(f"[yellow]⚠ {strategy_name} failed: {e}[/yellow]")
        
        # Clean up any open sessions
        if hasattr(self, 'search_registry') and self.search_registry:
            await self.search_registry.close_all()
        
        # Aggregate and score candidates
        if all_candidates:
            origin_scores = Counter()
            for candidate in all_candidates:
                if "origin" in candidate:
                    origin_scores[candidate["origin"]] += candidate.get("confidence", 1.0)
            
            if origin_scores:
                best_origin, best_score = origin_scores.most_common(1)[0]
                total_strategies = len(results["strategies_used"])
                confidence = best_score / total_strategies if total_strategies > 0 else 0
                
                if confidence >= confidence_threshold:
                    results["identified"] = True
                    results["confidence"] = confidence
                    results["final_origin"] = best_origin
                    results["candidates"] = all_candidates[:10]  # Top 10 candidates
        
        return results
    
    async def _identify_via_swh(
        self,
        path: Path,
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """Identify using Software Heritage archive."""
        candidates = []
        
        # Lazily create SWH client only when needed
        if self.swh_client is None:
            from ..core.config import SWHPIConfig
            config = SWHPIConfig(verbose=self.verbose)
            self.swh_client = SoftwareHeritageClient(config)
        
        # Scan directory
        from ..core.config import SWHPIConfig
        from ..core.swhid import SWHIDGenerator
        config = SWHPIConfig(verbose=self.verbose, max_depth=max_depth)
        scanner = DirectoryScanner(config, SWHIDGenerator())
        dir_candidates, file_candidates = scanner.scan_recursive(path)
        
        # Check SWHIDs
        all_swhids = [c.swhid for c in dir_candidates] + [c.swhid for c in file_candidates]
        
        if all_swhids:
            known_swhids = await self.swh_client.check_swhids_known(all_swhids[:100])
            
            for swhid, is_known in known_swhids.items():
                if is_known:
                    # Try to get origin information
                    origin = await self.swh_client.get_origin_for_swhid(swhid)
                    if origin:
                        candidates.append({
                            "source": "swh",
                            "swhid": swhid,
                            "origin": origin,
                            "confidence": 1.0
                        })
        
        return candidates
    
    async def _identify_via_hash_search(
        self,
        path: Path,
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """Identify using hash-based web search."""
        candidates = []
        
        # Scan for hashes
        from ..core.config import SWHPIConfig
        from ..core.swhid import SWHIDGenerator
        config = SWHPIConfig(verbose=self.verbose, max_depth=1)
        scanner = DirectoryScanner(config, SWHIDGenerator())
        dir_candidates, _ = scanner.scan_recursive(path)
        
        if dir_candidates:
            # Extract hash from SWHID
            swhid = dir_candidates[0].swhid
            hash_value = swhid.split(":")[-1] if ":" in swhid else swhid
            
            # Search for hash
            urls = await self.hash_searcher.search_hash(hash_value)
            
            for url in urls:
                candidates.append({
                    "source": "hash_search",
                    "hash": hash_value,
                    "origin": url,
                    "confidence": 0.8
                })
        
        return candidates
    
    async def _identify_via_scanoss(
        self,
        path: Path,
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """Identify using SCANOSS fingerprinting."""
        candidates = []
        
        # Initialize SCANOSS provider
        scanoss = SCANOSSProvider(verbose=self.verbose)
        
        try:
            await scanoss.ensure_session()
            
            # Use scan_file for individual files as scan_directory is not available
            # in the consolidated provider
            test_files = list(path.glob("**/*.c"))[:2] + list(path.glob("**/*.md"))[:1]
            
            if not test_files:
                test_files = list(path.iterdir())[:3]
            
            for test_file in test_files:
                if test_file.is_file():
                    result = await scanoss.scan_file(test_file)
                    # Parse SCANOSS results if available
                    if result and isinstance(result, dict):
                        for file_name, file_data in result.items():
                            if isinstance(file_data, list):
                                for match in file_data:
                                    if isinstance(match, dict) and match.get("component"):
                                        url = match.get("url", "")
                                        if self._is_trusted_git_host(url):
                                            # Ensure matched is numeric
                                            matched_val = match.get("matched", 0)
                                            if isinstance(matched_val, str):
                                                try:
                                                    matched_val = float(matched_val)
                                                except (ValueError, TypeError):
                                                    matched_val = 0
                                            candidates.append({
                                                "source": "scanoss",
                                                "component": match.get("component", ""),
                                                "origin": url,
                                                "confidence": matched_val / 100.0 if matched_val else 0.5
                                            })
        finally:
            await scanoss.close()
        
        return candidates

    def _is_trusted_git_host(self, url: str) -> bool:
        """
        Check if URL belongs to a trusted Git hosting service.

        Uses proper URL parsing to avoid substring attacks.
        """
        if not url:
            return False

        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)

            # Check if hostname exactly matches or is a subdomain of trusted hosts
            trusted_hosts = {
                'github.com',
                'gitlab.com',
                'gitorious.org',  # Found in our test results
                'src.fedoraproject.org'  # Found in our test results
            }

            hostname = parsed.hostname
            if not hostname:
                return False

            # Exact match or subdomain of trusted host
            hostname = hostname.lower()
            for trusted in trusted_hosts:
                if hostname == trusted or hostname.endswith('.' + trusted):
                    return True

            return False

        except Exception:
            # If URL parsing fails, be conservative and reject
            return False

    async def _identify_via_web_search(
        self,
        path: Path,
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """Identify using web search providers."""
        candidates = []
        
        # Get project name from path
        project_name = path.name
        
        # Search using all available providers
        search_results = await self.search_registry.search_all(
            f'"{project_name}" repository site:github.com OR site:gitlab.com'
        )
        
        for provider, urls in search_results.items():
            for url in urls:
                candidates.append({
                    "source": f"web_search_{provider}",
                    "query": project_name,
                    "origin": url,
                    "confidence": 0.6
                })
        
        return candidates
    
    def print_results(self, results: Dict[str, Any]):
        """Print identification results in a formatted table."""
        table = Table(title="Source Identification Results")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Path", results["path"])
        table.add_row("Identified", "✅ Yes" if results["identified"] else "❌ No")
        table.add_row("Confidence", f"{results['confidence']:.1%}")
        table.add_row("Strategies Used", ", ".join(results["strategies_used"]))
        
        if results["final_origin"]:
            table.add_row("Repository", results["final_origin"])
        
        console.print(table)
        
        if results["candidates"] and self.verbose:
            console.print("\n[bold]Top Candidates:[/bold]")
            for i, candidate in enumerate(results["candidates"][:5], 1):
                console.print(f"{i}. {candidate.get('origin', 'Unknown')} "
                            f"(via {candidate.get('source', 'unknown')}, "
                            f"confidence: {candidate.get('confidence', 0):.1%})")


async def identify_source(
    path: Path,
    max_depth: int = 3,
    confidence_threshold: float = 0.5,
    verbose: bool = False,
    strategies: Optional[List[str]] = None,
    use_swh: bool = False
) -> Dict[str, Any]:
    """Convenience function for source identification.
    
    Args:
        path: Path to analyze
        max_depth: Maximum depth for recursive scanning
        confidence_threshold: Minimum confidence for identification
        verbose: Enable verbose output
        strategies: List of strategies to use
        use_swh: Whether to include Software Heritage checking
        
    Returns:
        Identification results
    """
    identifier = SourceIdentifier(verbose=verbose)
    try:
        results = await identifier.identify(
            path=path,
            max_depth=max_depth,
            confidence_threshold=confidence_threshold,
            strategies=strategies,
            use_swh=use_swh
        )
        
        if verbose:
            identifier.print_results(results)
        
        return results
    finally:
        # Ensure cleanup of any open sessions
        if hasattr(identifier, 'search_registry') and identifier.search_registry:
            await identifier.search_registry.close_all()