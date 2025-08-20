"""Unified test suite for source identification."""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from src2id.search import (
    SourceIdentifier,
    identify_source,
    HashSearcher,
    create_default_registry
)
from src2id.core.client import SoftwareHeritageClient
from src2id.core.scanner import DirectoryScanner

console = Console()


class IdentificationTester:
    """Test suite for source identification functionality."""
    
    def __init__(self, verbose: bool = True):
        """Initialize the test suite."""
        self.verbose = verbose
        self.results = []
    
    async def test_swh_identification(self, path: Path) -> Dict[str, Any]:
        """Test Software Heritage identification."""
        console.print("\n[bold cyan]Testing SWH Identification[/bold cyan]")
        
        from src2id.core.config import SWHPIConfig
        config = SWHPIConfig(verbose=self.verbose, max_depth=2)
        client = SoftwareHeritageClient(config)
        from src2id.core.swhid import SWHIDGenerator
        scanner = DirectoryScanner(config, SWHIDGenerator())
        
        # Scan directory
        dir_candidates, file_candidates = scanner.scan_recursive(path)
        
        # Check SWHIDs
        all_swhids = [c.swhid for c in dir_candidates[:5]] + [c.swhid for c in file_candidates[:10]]
        
        if all_swhids:
            known_swhids = await client.check_swhids_known(all_swhids)
            
            found_count = sum(1 for is_known in known_swhids.values() if is_known)
            
            result = {
                "test": "swh_identification",
                "total_checked": len(all_swhids),
                "found_in_archive": found_count,
                "success_rate": found_count / len(all_swhids) if all_swhids else 0
            }
            
            console.print(f"✓ Found {found_count}/{len(all_swhids)} items in SWH archive")
            
            return result
        
        return {"test": "swh_identification", "error": "No candidates found"}
    
    async def test_hash_search(self, path: Path) -> Dict[str, Any]:
        """Test hash-based search."""
        console.print("\n[bold cyan]Testing Hash Search[/bold cyan]")
        
        registry = create_default_registry(verbose=self.verbose)
        searcher = HashSearcher(search_registry=registry, verbose=self.verbose)
        
        # Find a file to test
        test_files = list(path.glob("**/*.md"))[:1] + list(path.glob("**/*.c"))[:1]
        
        if not test_files:
            return {"test": "hash_search", "error": "No test files found"}
        
        all_results = []
        
        for test_file in test_files:
            results = await searcher.search_file(test_file)
            if results:
                all_results.append(results)
                console.print(f"✓ Found results for {test_file.name}")
        
        await registry.close_all()
        
        return {
            "test": "hash_search",
            "files_tested": len(test_files),
            "files_with_results": len(all_results),
            "success": len(all_results) > 0
        }
    
    async def test_unified_identification(self, path: Path) -> Dict[str, Any]:
        """Test unified identification with all strategies."""
        console.print("\n[bold cyan]Testing Unified Identification[/bold cyan]")
        
        results = await identify_source(
            path=path,
            max_depth=2,
            confidence_threshold=0.3,
            verbose=self.verbose
        )
        
        if results["identified"]:
            console.print(f"✓ Successfully identified: {results['final_origin']}")
            console.print(f"  Confidence: {results['confidence']:.1%}")
            console.print(f"  Strategies used: {', '.join(results['strategies_used'])}")
        else:
            console.print("✗ Could not identify repository")
        
        return results
    
    async def run_all_tests(self, path: Path):
        """Run all identification tests."""
        console.print(f"\n[bold]Running Identification Tests for: {path}[/bold]\n")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Running tests...", total=3)
            
            # Test 1: SWH Identification
            progress.update(task, description="[cyan]Testing SWH identification...")
            swh_result = await self.test_swh_identification(path)
            self.results.append(swh_result)
            progress.advance(task)
            
            # Test 2: Hash Search
            progress.update(task, description="[cyan]Testing hash search...")
            hash_result = await self.test_hash_search(path)
            self.results.append(hash_result)
            progress.advance(task)
            
            # Test 3: Unified Identification
            progress.update(task, description="[cyan]Testing unified identification...")
            unified_result = await self.test_unified_identification(path)
            self.results.append(unified_result)
            progress.advance(task)
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary."""
        console.print("\n[bold]Test Results Summary[/bold]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details")
        
        for result in self.results:
            test_name = result.get("test", "Unknown")
            
            if "error" in result:
                status = "[red]✗ Failed[/red]"
                details = result["error"]
            elif result.get("success") or result.get("identified"):
                status = "[green]✓ Passed[/green]"
                if "success_rate" in result:
                    details = f"Success rate: {result['success_rate']:.1%}"
                elif "confidence" in result:
                    details = f"Confidence: {result['confidence']:.1%}"
                else:
                    details = "Completed successfully"
            else:
                status = "[yellow]⚠ Partial[/yellow]"
                details = "Some issues encountered"
            
            table.add_row(test_name, status, details)
        
        console.print(table)


async def test_identification_suite(path: Path = None):
    """Run the complete identification test suite.
    
    Args:
        path: Path to test (defaults to test_data/darktable)
    """
    if path is None:
        path = Path("test_data/darktable")
    
    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        return
    
    tester = IdentificationTester(verbose=False)
    await tester.run_all_tests(path)


async def test_specific_strategy(
    path: Path,
    strategy: str = "scanoss"
):
    """Test a specific identification strategy.
    
    Args:
        path: Path to test
        strategy: Strategy to test (swh, hash_search, scanoss, web_search)
    """
    console.print(f"\n[bold]Testing {strategy} strategy on {path}[/bold]\n")
    
    results = await identify_source(
        path=path,
        strategies=[strategy],
        verbose=True
    )
    
    return results


if __name__ == "__main__":
    # Run test suite
    asyncio.run(test_identification_suite())
    
    # Test specific strategies if needed
    # asyncio.run(test_specific_strategy(Path("test_data/darktable"), "scanoss"))