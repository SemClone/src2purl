"""Main CLI entry point for SWHPI."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from swhpi import __version__
from swhpi.core.config import SWHPIConfig
from swhpi.core.models import PackageMatch
from swhpi.core.orchestrator import SHPackageIdentifier

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
    "--no-fuzzy",
    is_flag=True,
    help="Disable fuzzy matching for faster execution",
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
    no_fuzzy: bool,
    no_cache: bool,
    clear_cache: bool,
    verbose: bool,
) -> None:
    """
    Software Heritage Package Identifier - Identify package coordinates from source code.
    
    Analyzes the given PATH to identify packages using Software Heritage archive.
    """
    # Handle cache clearing
    if clear_cache:
        from swhpi.core.cache import PersistentCache
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
        enable_fuzzy_matching=not no_fuzzy,
        output_format=output_format,
        verbose=verbose,
    )
    
    if verbose:
        console.print(f"[dim]SWHPI v{__version__}[/dim]")
        console.print(f"[dim]Analyzing: {path}[/dim]")
        console.print(f"[dim]Max depth: {max_depth}[/dim]")
        console.print(f"[dim]Confidence threshold: {confidence_threshold}[/dim]")
        
        # Show cache status
        if not no_cache:
            from swhpi.core.cache import PersistentCache
            cache = PersistentCache()
            stats = cache.get_cache_stats()
            console.print(f"[dim]Cache: {stats['entries']} entries ({stats['total_size_mb']} MB)[/dim]")
        console.print()
    
    try:
        # Run the identifier
        identifier = SHPackageIdentifier(config)
        matches = asyncio.run(identifier.identify_packages(path))
        
        # Output results
        if output_format == "json":
            output_json(matches, config)
        else:
            output_table(matches, config)
            
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


def output_table(matches: list[PackageMatch], config: SWHPIConfig) -> None:
    """Output results as a formatted table."""
    if not matches:
        console.print("[yellow]No package matches found.[/yellow]")
        return
    
    if config.verbose:
        # Use rich table for verbose output
        table = Table(title="Package Matches")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Confidence", justify="right", style="green")
        table.add_column("License", style="yellow")
        table.add_column("PURL", style="blue")
        table.add_column("Type", style="dim")
        
        for match in matches:
            table.add_row(
                match.name or "Unknown",
                match.version or "Unknown",
                f"{match.confidence_score:.2f}",
                match.license or "Unknown",
                match.purl or "N/A",
                match.match_type.value,
            )
        
        console.print(table)
    else:
        # Use tabulate for standard output
        headers = ["Name", "Version", "Confidence", "License", "PURL"]
        rows = []
        for match in matches:
            rows.append([
                match.name or "Unknown",
                match.version or "Unknown",
                f"{match.confidence_score:.2f}",
                match.license or "Unknown",
                match.purl or "N/A",
            ])
        
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    if config.verbose:
        console.print(f"\n[dim]Found {len(matches)} matches[/dim]")


if __name__ == "__main__":
    main()