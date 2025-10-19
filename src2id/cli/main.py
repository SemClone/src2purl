"""Main CLI entry point for src2id."""

import asyncio
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Optional

# Suppress urllib3 warnings about LibreSSL
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

import click
from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from src2id import __version__
from src2id.core.config import SWHPIConfig
from src2id.core.models import PackageMatch
from src2id.core.orchestrator import SHPackageIdentifier

console = Console()


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--max-depth",
    type=int,
    default=2,
    help="Maximum parent directory levels to scan",
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.3,
    help="Minimum confidence to report matches",
)
@click.option(
    "--output-format",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@click.option(
    "--enable-fuzzy",
    is_flag=True,
    help="Enable fuzzy matching (keyword search) when exact matches fail",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable API response caching",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear all cached API responses and exit",
)
@click.option(
    "--no-license-detection",
    is_flag=True,
    help="Skip automatic license detection from local source code",
)
@click.option(
    "--detect-subcomponents",
    is_flag=True,
    help="Detect and identify multiple subcomponents in the project",
)
@click.option(
    "--use-swh",
    is_flag=True,
    help="Include Software Heritage archive checking (slower but more comprehensive)",
)
@click.option(
    "--api-token",
    envvar="SWH_API_TOKEN",
    help="Software Heritage API token for authentication (can also be set via SWH_API_TOKEN env var)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output for debugging",
)
@click.version_option(version=__version__)
def main(
    path: Optional[Path],
    max_depth: int,
    confidence_threshold: float,
    output_format: str,
    enable_fuzzy: bool,
    no_cache: bool,
    clear_cache: bool,
    no_license_detection: bool,
    detect_subcomponents: bool,
    use_swh: bool,
    api_token: Optional[str],
    verbose: bool,
) -> None:
    """
    Source Package Identifier - Identify package coordinates from source code.
    
    Analyzes the given PATH to identify packages using multiple identification strategies
    including SCANOSS fingerprinting, hash search, and optionally Software Heritage archive.
    """
    # Handle cache clearing
    if clear_cache:
        from src2id.core.cache import PersistentCache
        cache = PersistentCache()
        cache.clear()
        stats = cache.get_cache_stats()
        console.print("[green]✓ Cache cleared successfully[/green]")
        console.print(f"[dim]Cache directory: {stats['cache_dir']}[/dim]")
        sys.exit(0)
    
    # Require path for normal operation
    if not path:
        console.print("[red]Error: PATH argument is required[/red]")
        sys.exit(1)
    
    # Create configuration
    config = SWHPIConfig(
        max_depth=max_depth,
        report_match_threshold=confidence_threshold,
        cache_enabled=not no_cache,
        enable_fuzzy_matching=enable_fuzzy,
        output_format=output_format,
        api_token=api_token or "",
        verbose=verbose,
        use_swh=use_swh,
    )
    
    # Always show analysis header (not just in verbose mode)
    console.print(f"[dim]src2id v{__version__}[/dim]")
    console.print(f"[dim]Analyzing: {path}[/dim]")
    console.print(f"[dim]Max depth: {max_depth}[/dim]")
    console.print(f"[dim]Confidence threshold: {confidence_threshold}[/dim]")
    
    # Show strategy configuration
    if use_swh:
        console.print(f"[dim]Strategies: Hash Search, Web Search, SCANOSS, SWH[/dim]")
        if api_token:
            console.print(f"[dim]SWH auth: [green]✓ Using API token[/green][/dim]")
    else:
        console.print(f"[dim]Strategies: Hash Search, Web Search, SCANOSS[/dim]")
    
    # Show cache status
    if not no_cache:
        from src2id.core.cache import PersistentCache
        cache = PersistentCache()
        stats = cache.get_cache_stats()
        console.print(f"[dim]Cache: {stats['entries']} entries ({stats['total_size_mb']} MB)[/dim]")
    console.print()
    
    try:
        if detect_subcomponents:
            # Use subcomponent detection
            from src2id.core.subcomponent_detector import identify_subcomponents
            results = asyncio.run(identify_subcomponents(
                root_path=path,
                max_depth=max_depth,
                confidence_threshold=confidence_threshold,
                verbose=verbose,
                use_swh=use_swh
            ))
            
            # Convert to matches format for output
            matches = []
            if results.get('subcomponents'):
                for comp in results['subcomponents']:
                    if comp['identified']:
                        from src2id.core.models import PackageMatch, MatchType
                        match = PackageMatch(
                            name=Path(comp['path']).name,
                            version="unknown",
                            confidence_score=comp['confidence'],
                            match_type=MatchType.EXACT if comp['confidence'] > 0.8 else MatchType.FUZZY,
                            download_url=comp['repository'],
                            purl=f"pkg:{comp['type']}/{Path(comp['path']).name}",
                            license="",
                            is_official_org=False
                        )
                        matches.append(match)
        else:
            # Use the standard identifier with UPMEX integration
            identifier = SHPackageIdentifier(config)
            matches = asyncio.run(identifier.identify_packages(path, enhance_licenses=not no_license_detection))
        
        # Output results
        if output_format == "json":
            output_json(matches, config)
        else:
            output_table(matches, config, path)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


def output_json(matches: list[PackageMatch], config: SWHPIConfig) -> None:
    """Output results as JSON."""
    match_list = []
    for match in matches:
        match_list.append({
            "name": match.name,
            "version": match.version,
            "confidence": round(match.confidence_score, 3),
            "type": match.match_type.value if match.match_type else "unknown",
            "url": match.download_url,
            "purl": match.purl,
            "license": match.license,
            "official": match.is_official_org,
        })
    
    output = {
        "matches": match_list,
        "count": len(matches),
        "threshold": config.report_match_threshold,
    }
    print(json.dumps(output, indent=2, default=str))


def show_local_source_analysis(path: Path, config: SWHPIConfig) -> None:
    """Show analysis of local source code."""
    console.print("[bold]Local Source Analysis[/bold]")
    
    # Detect licenses in local source code
    try:
        from src2id.integrations.oslili import OsliliIntegration
        integration = OsliliIntegration()
        
        if integration.available:
            license_info = integration.detect_licenses(path)
            
            if license_info["licenses"]:
                license_list = ", ".join(license_info["licenses"][:3])
                if len(license_info["licenses"]) > 3:
                    license_list += f" and {len(license_info['licenses']) - 3} more"
                console.print(f"[green]✓[/green] Licenses detected: [yellow]{license_list}[/yellow]")
                console.print(f"[dim]  Confidence: {license_info['confidence']:.1%}[/dim]")
            else:
                console.print("[yellow]⚠[/yellow] No licenses detected in source code")
        else:
            console.print("[dim]• License detection unavailable[/dim]")
    except ImportError:
        console.print("[dim]• License detection unavailable[/dim]")
    
    # Show directory scan info
    console.print(f"[dim]• Scanned {path} and subdirectories[/dim]")
    console.print()


def output_table(matches: list[PackageMatch], config: SWHPIConfig, path: Path) -> None:
    """Output results as a formatted table."""
    
    # Show local source analysis
    show_local_source_analysis(path, config)
    
    if not matches:
        console.print("[yellow]No package matches found.[/yellow]")
        return
    
    if config.verbose:
        # Use rich table for verbose output
        table = Table(title="Package Matches")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Confidence", justify="right", style="green")
        table.add_column("Method", style="yellow")
        table.add_column("PURL", style="blue")
        table.add_column("Source", style="dim")
        table.add_column("URL", style="dim")
        
        for match in matches:
            table.add_row(
                match.name or "Unknown",
                f"{match.confidence_score:.2f}",
                match.match_type.value,
                match.purl or "N/A",
                "Repository",
                match.download_url,
            )
        
        console.print(table)
    else:
        # Use rich table for clean standard output (better than tabulate)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Confidence", justify="right", style="green") 
        table.add_column("Method", style="yellow")
        table.add_column("PURL", style="blue", max_width=50)
        
        for match in matches:
            table.add_row(
                match.name or "Unknown",
                f"{match.confidence_score:.2f}",
                match.match_type.value, 
                match.purl or "N/A",
            )
        
        console.print(table)
    
    # Show result summary for both modes  
    if config.verbose:
        console.print(f"\n[green]Found {len(matches)} matches[/green]")
    else:
        console.print(f"\n✓ Found [green]{len(matches)}[/green] package matches")


if __name__ == "__main__":
    main()