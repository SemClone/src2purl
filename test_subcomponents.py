#!/usr/bin/env python3
"""Test subcomponent detection and identification."""

import asyncio
from pathlib import Path
from rich.console import Console

console = Console()


async def test_subcomponent_detection():
    """Test detection of multiple subcomponents."""
    
    console.print("[bold cyan]Testing Subcomponent Detection[/bold cyan]\n")
    
    from swhpi.core.subcomponent_detector import (
        SubcomponentDetector,
        identify_subcomponents
    )
    
    # Test 1: Check a directory that might have subcomponents
    test_path = Path("test_data")
    
    console.print(f"[yellow]Scanning: {test_path}[/yellow]\n")
    
    detector = SubcomponentDetector(verbose=True)
    subcomponents = detector.detect_subcomponents(test_path, max_depth=3)
    
    console.print(f"\nFound {len(subcomponents)} subcomponents")
    
    # Test 2: Full identification of subcomponents
    console.print("\n[yellow]Testing Full Subcomponent Identification[/yellow]\n")
    
    results = await identify_subcomponents(
        root_path=test_path,
        max_depth=2,
        confidence_threshold=0.5,
        verbose=True,
        use_swh=False
    )
    
    # Print results
    console.print("\n[bold]Results:[/bold]")
    console.print(f"Root: {results['root']}")
    console.print(f"Total components: {results.get('total_components', 0)}")
    console.print(f"Identified: {results.get('total_identified', 0)}")
    
    if results.get('subcomponents'):
        console.print("\n[bold]Component Details:[/bold]")
        for comp in results['subcomponents']:
            console.print(f"\n• {comp['path']}")
            console.print(f"  Type: {comp['type']}")
            console.print(f"  Identified: {'✓' if comp['identified'] else '✗'}")
            if comp['identified']:
                console.print(f"  Repository: {comp['repository']}")
                console.print(f"  Confidence: {comp['confidence']:.1%}")


async def test_monorepo_detection():
    """Test detection in monorepo structures."""
    
    console.print("\n[bold cyan]Testing Monorepo Detection[/bold cyan]\n")
    
    from swhpi.core.subcomponent_detector import SubcomponentDetector
    
    # Create a mock monorepo structure for testing
    console.print("[dim]Checking for monorepo patterns...[/dim]\n")
    
    detector = SubcomponentDetector(verbose=False)
    
    # Test with test_data which might have multiple projects
    test_dirs = [
        Path("test_data/darktable"),
        Path("test_data/scanoss_py"),
        Path("test_data/tempo")
    ]
    
    for test_dir in test_dirs:
        if test_dir.exists():
            console.print(f"Checking: {test_dir}")
            subcomps = detector.detect_subcomponents(test_dir, max_depth=2)
            if len(subcomps) > 1:
                console.print(f"  [green]✓ Found {len(subcomps)} components (potential monorepo)[/green]")
            elif len(subcomps) == 1:
                console.print(f"  [yellow]Single component: {subcomps[0].type}[/yellow]")
            else:
                console.print(f"  [dim]No components detected[/dim]")


async def main():
    """Run all subcomponent tests."""
    
    await test_subcomponent_detection()
    await test_monorepo_detection()
    
    console.print("\n[bold green]✓ Subcomponent testing complete[/bold green]")


if __name__ == "__main__":
    asyncio.run(main())