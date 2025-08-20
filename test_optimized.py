#!/usr/bin/env python3
"""Test the optimized identification without SWH."""

import asyncio
import time
from pathlib import Path
from rich.console import Console

console = Console()

async def test_optimized():
    """Test optimized identification strategies."""
    
    console.print("[bold cyan]Testing Optimized Identification (No SWH)[/bold cyan]\n")
    
    from swhpi.search import identify_source
    
    path = Path("test_data/darktable/packaging")
    
    # Test WITHOUT SWH (default, optimized)
    console.print("[yellow]Test 1: Without SWH (Optimized)[/yellow]")
    start = time.time()
    
    results = await identify_source(
        path=path,
        max_depth=1,
        confidence_threshold=0.3,
        verbose=True,
        use_swh=False  # Default
    )
    
    elapsed = time.time() - start
    
    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"Time: {elapsed:.2f} seconds")
    console.print(f"Identified: {results['identified']}")
    console.print(f"Confidence: {results['confidence']:.1%}")
    console.print(f"Strategies used: {', '.join(results['strategies_used'])}")
    if results['final_origin']:
        console.print(f"Repository: {results['final_origin']}")
    
    # Test WITH SWH (optional, slower)
    console.print("\n[yellow]Test 2: With SWH (Optional)[/yellow]")
    start = time.time()
    
    results_swh = await identify_source(
        path=path,
        max_depth=1,
        confidence_threshold=0.3,
        verbose=False,
        use_swh=True  # Include SWH
    )
    
    elapsed_swh = time.time() - start
    
    console.print(f"\n[bold]Results with SWH:[/bold]")
    console.print(f"Time: {elapsed_swh:.2f} seconds")
    console.print(f"Strategies used: {', '.join(results_swh['strategies_used'])}")
    
    # Compare
    console.print(f"\n[bold green]Performance Comparison:[/bold green]")
    console.print(f"Without SWH: {elapsed:.2f}s")
    console.print(f"With SWH: {elapsed_swh:.2f}s")
    console.print(f"Speedup: {elapsed_swh/elapsed:.1f}x faster without SWH")

if __name__ == "__main__":
    asyncio.run(test_optimized())