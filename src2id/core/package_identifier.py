"""Optimized package identifier using multiple strategies."""

import asyncio
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src2id.core.config import SWHPIConfig
from src2id.core.models import PackageMatch, MatchType
from src2id.search import identify_source

console = Console()


class PackageIdentifier:
    """Main package identifier using optimized strategy order."""
    
    def __init__(self, config: Optional[SWHPIConfig] = None):
        """Initialize the package identifier with configuration."""
        self.config = config or SWHPIConfig()
    
    async def identify_packages(self, path: Path, enhance_licenses: bool = True) -> List[PackageMatch]:
        """
        Identify packages using optimized strategies.
        
        Args:
            path: Directory path to analyze
            enhance_licenses: Whether to use oslili for license enhancement
            
        Returns:
            List of package matches found
        """
        matches = []
        
        try:
            if self.config.verbose:
                console.print("[bold blue]Starting package identification...[/bold blue]")
                console.print("[dim]Using optimized strategy order: Hash Search → Web Search → SCANOSS[/dim]")
                if self.config.use_swh:
                    console.print("[dim]Software Heritage checking enabled[/dim]")
            
            # Use the optimized identification strategy
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                disable=not self.config.verbose
            ) as progress:
                task = progress.add_task("Identifying source...", total=None)
                
                results = await identify_source(
                    path=path,
                    max_depth=self.config.max_depth,
                    confidence_threshold=self.config.report_match_threshold,
                    verbose=self.config.verbose,
                    use_swh=self.config.use_swh
                )
                
                progress.update(task, completed=True)
            
            # Convert results to PackageMatch objects
            if results["identified"]:
                # Create a match from the best result
                match = PackageMatch(
                    name=path.name,
                    version="unknown",
                    confidence_score=results["confidence"],
                    match_type=MatchType.EXACT if results["confidence"] > 0.8 else MatchType.FUZZY,
                    download_url=results["final_origin"],
                    purl=f"pkg:generic/{path.name}",
                    license="",
                    is_official_org=False
                )
                
                # Enhance with license detection if requested
                if enhance_licenses:
                    try:
                        from src2id.integrations.oslili import OsliliIntegration
                        integration = OsliliIntegration()
                        
                        if integration.available:
                            license_info = integration.detect_licenses(path)
                            if license_info["licenses"]:
                                match.license = ", ".join(license_info["licenses"][:3])
                    except ImportError:
                        pass
                
                matches.append(match)
                
                # Add additional candidates if confidence is lower
                if results["confidence"] < 0.8 and results["candidates"]:
                    for candidate in results["candidates"][:2]:  # Add top 2 alternatives
                        if candidate.get("origin") and candidate["origin"] != results["final_origin"]:
                            alt_match = PackageMatch(
                                name=path.name,
                                version="unknown",
                                confidence_score=candidate.get("confidence", 0.5),
                                match_type=MatchType.FUZZY,
                                download_url=candidate["origin"],
                                purl=f"pkg:generic/{path.name}",
                                license="",
                                is_official_org=False
                            )
                            matches.append(alt_match)
            
            if self.config.verbose:
                if matches:
                    console.print(f"[green]✓ Found {len(matches)} package matches[/green]")
                else:
                    console.print("[yellow]No package matches found[/yellow]")
            
        except Exception as e:
            if self.config.verbose:
                console.print(f"[red]Error during identification: {e}[/red]")
                console.print_exception()
        
        return matches


# Create an alias for backward compatibility
SHPackageIdentifier = PackageIdentifier