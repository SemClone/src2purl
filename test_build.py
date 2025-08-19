#!/usr/bin/env python3
"""Test script to verify the build and functionality."""

import asyncio
import sys
from pathlib import Path
from rich.console import Console

console = Console()

async def test_identification():
    """Test the identification system with a small directory."""
    console.print("[bold]Testing Identification System[/bold]\n")
    
    try:
        # Test with a smaller directory first
        test_path = Path("test_data/darktable/packaging")
        
        if not test_path.exists():
            console.print(f"[red]Test path {test_path} does not exist[/red]")
            return False
        
        console.print(f"Testing with: {test_path}")
        
        # Import and test
        from swhpi.search import identify_source
        
        # Use minimal settings for quick test
        results = await identify_source(
            path=test_path,
            max_depth=1,
            confidence_threshold=0.5,
            strategies=["swh"],  # Only test SWH strategy
            verbose=True
        )
        
        console.print(f"\n[bold]Results:[/bold]")
        console.print(f"Identified: {results['identified']}")
        console.print(f"Confidence: {results['confidence']:.1%}")
        console.print(f"Strategies used: {results['strategies_used']}")
        
        if results['final_origin']:
            console.print(f"Repository: {results['final_origin']}")
            
        return True
        
    except Exception as e:
        console.print(f"[red]Error during test: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

async def test_hash_search():
    """Test hash search functionality."""
    console.print("\n[bold]Testing Hash Search[/bold]\n")
    
    try:
        from swhpi.search import HashSearcher
        
        searcher = HashSearcher(verbose=False)
        
        # Test with a known file
        test_file = Path("test_data/darktable/README.md")
        if test_file.exists():
            hashes = searcher.compute_file_hashes(test_file)
            console.print(f"Computed hashes for {test_file.name}:")
            for hash_type, hash_value in hashes.items():
                console.print(f"  {hash_type}: {hash_value[:16]}...")
            return True
        else:
            console.print("[yellow]Test file not found[/yellow]")
            return True
            
    except Exception as e:
        console.print(f"[red]Hash search error: {e}[/red]")
        return False

async def test_scanoss():
    """Test SCANOSS provider."""
    console.print("\n[bold]Testing SCANOSS Provider[/bold]\n")
    
    try:
        from swhpi.search.providers import SCANOSSProvider
        
        provider = SCANOSSProvider(verbose=True)
        
        # Test WFP creation
        test_file = Path("test_data/darktable/README.md")
        if test_file.exists():
            content = test_file.read_bytes()
            wfp = provider._create_wfp(test_file, content)
            console.print(f"Created WFP: {wfp[:100]}...")
            return True
        else:
            console.print("[yellow]Test file not found[/yellow]")
            return True
            
    except Exception as e:
        console.print(f"[red]SCANOSS error: {e}[/red]")
        return False

async def main():
    """Run all tests."""
    console.print("[bold cyan]Running Build and Functionality Tests[/bold cyan]\n")
    
    results = []
    
    # Test 1: Hash Search
    console.print("[cyan]1. Hash Search Test[/cyan]")
    results.append(await test_hash_search())
    
    # Test 2: SCANOSS
    console.print("\n[cyan]2. SCANOSS Test[/cyan]")
    results.append(await test_scanoss())
    
    # Test 3: Identification (limited)
    console.print("\n[cyan]3. Identification Test (SWH only)[/cyan]")
    results.append(await test_identification())
    
    # Summary
    console.print("\n" + "="*50)
    console.print("[bold]Test Summary:[/bold]")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        console.print(f"[green]✅ All {total} tests passed![/green]")
        return 0
    else:
        console.print(f"[yellow]⚠ {passed}/{total} tests passed[/yellow]")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))