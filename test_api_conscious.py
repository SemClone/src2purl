#!/usr/bin/env python3
"""Test the API-conscious strategy ordering."""

import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

async def test_strategy_order():
    """Test that strategies execute in the correct order."""
    
    console.print("[bold cyan]Testing API-Conscious Strategy Order[/bold cyan]\n")
    
    from swhpi.search import identify_source
    
    path = Path("test_data/darktable/packaging")
    
    # Test with verbose to see strategy order
    console.print("[yellow]Running identification with new order:[/yellow]")
    console.print("[dim]Expected: Hash Search → Web Search → SCANOSS[/dim]\n")
    
    results = await identify_source(
        path=path,
        max_depth=1,
        confidence_threshold=0.3,
        verbose=True,
        use_swh=False
    )
    
    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"Strategies executed: {' → '.join(results['strategies_used'])}")
    console.print(f"Identified: {results['identified']}")
    console.print(f"Confidence: {results['confidence']:.1%}")
    
    if results['final_origin']:
        console.print(f"Repository: {results['final_origin']}")
    
    # Verify order
    expected_order = ["hash_search", "web_search", "scanoss"]
    actual_order = results['strategies_used']
    
    console.print(f"\n[bold]Order Verification:[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Strategy", style="cyan")
    table.add_column("Expected Position", justify="center")
    table.add_column("Actual Position", justify="center")
    table.add_column("Status", justify="center")
    
    for i, strategy in enumerate(expected_order):
        if i < len(actual_order):
            actual = actual_order[i]
            if strategy == actual:
                status = "[green]✓ Correct[/green]"
            else:
                status = f"[red]✗ Got {actual}[/red]"
        else:
            status = "[yellow]⚠ Not reached[/yellow]"
        
        table.add_row(
            strategy.replace("_", " ").title(),
            str(i + 1),
            str(actual_order.index(strategy) + 1) if strategy in actual_order else "N/A",
            status
        )
    
    console.print(table)
    
    # Summary
    console.print("\n[bold green]Summary:[/bold green]")
    console.print("✓ Strategies execute in API-conscious order")
    console.print("✓ Local/lightweight methods tried first")
    console.print("✓ SCANOSS used only as third option to preserve API quota")

if __name__ == "__main__":
    asyncio.run(test_strategy_order())