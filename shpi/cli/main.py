"""Main CLI entry point for SHPI."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from shpi import __version__
from shpi.core.config import SHPIConfig
from shpi.core.models import PackageMatch
from shpi.core.orchestrator import SHPackageIdentifier

console = Console()


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--max-depth",
    type=int,
    default=5,
    help="Maximum parent directory levels to scan",
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.65,
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
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output for debugging",
)
@click.version_option(version=__version__)
def main(
    path: Path,
    max_depth: int,
    confidence_threshold: float,
    output_format: str,
    no_fuzzy: bool,
    no_cache: bool,
    verbose: bool,
) -> None:
    """
    SH Package Identifier - Identify package coordinates from source code.
    
    Analyzes the given PATH to identify packages using Software Heritage archive.
    """
    # Create configuration
    config = SHPIConfig(
        max_depth=max_depth,
        report_match_threshold=confidence_threshold,
        cache_enabled=not no_cache,
        enable_fuzzy_matching=not no_fuzzy,
        output_format=output_format,
        verbose=verbose,
    )
    
    if verbose:
        console.print(f"[dim]SHPI v{__version__}[/dim]")
        console.print(f"[dim]Analyzing: {path}[/dim]")
        console.print(f"[dim]Max depth: {max_depth}[/dim]")
        console.print(f"[dim]Confidence threshold: {confidence_threshold}[/dim]")
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


def output_json(matches: list[PackageMatch], config: SHPIConfig) -> None:
    """Output results as JSON."""
    output = {
        "matches": [match.to_dict() for match in matches],
        "count": len(matches),
        "threshold": config.report_match_threshold,
    }
    print(json.dumps(output, indent=2, default=str))


def output_table(matches: list[PackageMatch], config: SHPIConfig) -> None:
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