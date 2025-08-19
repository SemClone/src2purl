#!/usr/bin/env python3
"""Final comprehensive test of the cleaned-up codebase."""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

async def main():
    """Run final comprehensive tests."""
    console.print("[bold cyan]Final Build Verification Tests[/bold cyan]\n")
    
    results = []
    
    # Test 1: Import all modules
    console.print("[yellow]Test 1: Module Imports[/yellow]")
    try:
        from swhpi.core import models, scanner, client, config, orchestrator
        from swhpi.search import (
            SourceIdentifier, HashSearcher, create_default_registry,
            SearchProvider, SerpAPIProvider, GitHubSearchProvider, SCANOSSProvider
        )
        from swhpi.cli import main
        console.print("✅ All modules imported successfully\n")
        results.append(("Module Imports", "✅ Passed", "All modules load correctly"))
    except Exception as e:
        console.print(f"❌ Import failed: {e}\n")
        results.append(("Module Imports", "❌ Failed", str(e)))
    
    # Test 2: Component Instantiation
    console.print("[yellow]Test 2: Component Instantiation[/yellow]")
    try:
        from swhpi.core.config import SWHPIConfig
        from swhpi.core.orchestrator import SHPackageIdentifier
        
        config = SWHPIConfig(verbose=False)
        orchestrator = SHPackageIdentifier(config)
        
        from swhpi.search import create_default_registry
        registry = create_default_registry(verbose=False)
        
        console.print("✅ All components instantiate correctly\n")
        results.append(("Component Creation", "✅ Passed", "All components created"))
    except Exception as e:
        console.print(f"❌ Instantiation failed: {e}\n")
        results.append(("Component Creation", "❌ Failed", str(e)))
    
    # Test 3: Hash Computation
    console.print("[yellow]Test 3: Hash Computation[/yellow]")
    try:
        from swhpi.search import HashSearcher
        searcher = HashSearcher(verbose=False)
        
        test_file = Path("test_data/darktable/README.md")
        if test_file.exists():
            hashes = searcher.compute_file_hashes(test_file)
            console.print(f"✅ Computed {len(hashes)} hash types\n")
            results.append(("Hash Computation", "✅ Passed", f"{len(hashes)} hash types"))
        else:
            console.print("⚠️  Test file not found\n")
            results.append(("Hash Computation", "⚠️  Skipped", "Test file not found"))
    except Exception as e:
        console.print(f"❌ Hash computation failed: {e}\n")
        results.append(("Hash Computation", "❌ Failed", str(e)))
    
    # Test 4: Directory Scanning
    console.print("[yellow]Test 4: Directory Scanning[/yellow]")
    try:
        from swhpi.core.config import SWHPIConfig
        from swhpi.core.scanner import DirectoryScanner
        from swhpi.core.swhid import SWHIDGenerator
        
        config = SWHPIConfig(verbose=False, max_depth=1)
        scanner = DirectoryScanner(config, SWHIDGenerator())
        
        test_path = Path("test_data/darktable/packaging")
        if test_path.exists():
            dir_candidates, file_candidates = scanner.scan_recursive(test_path)
            console.print(f"✅ Found {len(dir_candidates)} dirs, {len(file_candidates)} files\n")
            results.append(("Directory Scanning", "✅ Passed", 
                          f"{len(dir_candidates)} dirs, {len(file_candidates)} files"))
        else:
            console.print("⚠️  Test path not found\n")
            results.append(("Directory Scanning", "⚠️  Skipped", "Test path not found"))
    except Exception as e:
        console.print(f"❌ Scanning failed: {e}\n")
        results.append(("Directory Scanning", "❌ Failed", str(e)))
    
    # Test 5: Search Provider Registry
    console.print("[yellow]Test 5: Search Provider Registry[/yellow]")
    try:
        from swhpi.search import create_default_registry
        
        registry = create_default_registry(verbose=False)
        providers = list(registry.providers.keys())
        
        console.print(f"✅ Registered {len(providers)} providers: {', '.join(providers)}\n")
        results.append(("Provider Registry", "✅ Passed", f"{len(providers)} providers"))
        
        # Clean up
        await registry.close_all()
    except Exception as e:
        console.print(f"❌ Registry failed: {e}\n")
        results.append(("Provider Registry", "❌ Failed", str(e)))
    
    # Test 6: SCANOSS WFP Creation
    console.print("[yellow]Test 6: SCANOSS WFP Creation[/yellow]")
    try:
        from swhpi.search.providers import SCANOSSProvider
        
        provider = SCANOSSProvider(verbose=False)
        test_file = Path("test_data/darktable/README.md")
        
        if test_file.exists():
            content = test_file.read_bytes()
            wfp = provider._create_wfp(test_file, content)
            console.print(f"✅ Created WFP with {len(wfp)} bytes\n")
            results.append(("SCANOSS WFP", "✅ Passed", f"{len(wfp)} bytes"))
        else:
            console.print("⚠️  Test file not found\n")
            results.append(("SCANOSS WFP", "⚠️  Skipped", "Test file not found"))
    except Exception as e:
        console.print(f"❌ WFP creation failed: {e}\n")
        results.append(("SCANOSS WFP", "❌ Failed", str(e)))
    
    # Test 7: CLI Module
    console.print("[yellow]Test 7: CLI Module[/yellow]")
    try:
        from swhpi.cli.main import main as cli_main
        console.print("✅ CLI module loads correctly\n")
        results.append(("CLI Module", "✅ Passed", "Module loads"))
    except Exception as e:
        console.print(f"❌ CLI module failed: {e}\n")
        results.append(("CLI Module", "❌ Failed", str(e)))
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold]Test Results Summary[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Test", style="cyan", width=20)
    table.add_column("Status", justify="center", width=15)
    table.add_column("Details", width=25)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, status, details in results:
        table.add_row(test_name, status, details)
        if "✅" in status:
            passed += 1
        elif "❌" in status:
            failed += 1
        else:
            skipped += 1
    
    console.print(table)
    
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  ✅ Passed: {passed}")
    console.print(f"  ❌ Failed: {failed}")
    console.print(f"  ⚠️  Skipped: {skipped}")
    
    if failed == 0:
        console.print("\n[bold green]🎉 All tests passed! The build is functional.[/bold green]")
        return 0
    else:
        console.print(f"\n[bold yellow]⚠️  {failed} test(s) failed. Review needed.[/bold yellow]")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))