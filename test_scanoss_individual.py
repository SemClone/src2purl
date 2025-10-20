#!/usr/bin/env python3
"""Test SCANOSS discovery method individually."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '/Users/ovalenzuela/Projects/semantic-copycat-src2id')

from src2id.search.providers import SCANOSSProvider
import json

async def test_scanoss_on_directory(directory: Path):
    """Test SCANOSS on a specific directory."""
    print(f"\n=== Testing SCANOSS on {directory} ===")

    provider = SCANOSSProvider(verbose=True)
    results = []

    # Get some test files
    test_files = []

    # Priority file types for SCANOSS
    for pattern in ["*.c", "*.cpp", "*.h", "*.py", "*.js", "*.java", "*.go"]:
        test_files.extend(list(directory.glob(f"**/{pattern}"))[:3])

    # If no source files, try some common files
    if not test_files:
        for pattern in ["CMakeLists.txt", "*.md", "*.txt"]:
            test_files.extend(list(directory.glob(f"**/{pattern}"))[:2])

    # Limit to 5 files to avoid rate limits
    test_files = test_files[:5]

    print(f"Testing {len(test_files)} files:")
    for file_path in test_files:
        print(f"  - {file_path.relative_to(directory)}")

    for file_path in test_files:
        if file_path.is_file() and file_path.stat().st_size < 1024 * 1024:  # Skip large files
            try:
                print(f"\nScanning: {file_path.name}")
                result = await provider.scan_file(file_path)

                if result:
                    print(f"  ✓ SCANOSS found matches!")
                    # Parse results
                    for file_name, file_data in result.items():
                        if isinstance(file_data, list):
                            for match in file_data:
                                if isinstance(match, dict):
                                    component = match.get("component", "Unknown")
                                    url = match.get("url", "")
                                    confidence = match.get("matched", 0)
                                    license_info = match.get("licenses", [])

                                    results.append({
                                        "file": file_path.name,
                                        "component": component,
                                        "url": url,
                                        "confidence": confidence,
                                        "licenses": license_info
                                    })

                                    print(f"    Component: {component}")
                                    print(f"    URL: {url}")
                                    print(f"    Confidence: {confidence}%")
                                    if license_info:
                                        print(f"    Licenses: {license_info}")
                else:
                    print(f"  - No matches for {file_path.name}")

            except Exception as e:
                print(f"  ✗ Error scanning {file_path.name}: {e}")

    await provider.close()
    return results

async def main():
    """Test SCANOSS on all test directories."""
    test_data = Path("test_data")

    all_results = {}

    # Test each subdirectory
    for subdir in test_data.iterdir():
        if subdir.is_dir():
            try:
                results = await test_scanoss_on_directory(subdir)
                all_results[subdir.name] = results

                print(f"\n--- Summary for {subdir.name} ---")
                if results:
                    unique_components = set(r['component'] for r in results)
                    print(f"Found {len(results)} matches across {len(unique_components)} components")
                    for component in unique_components:
                        component_matches = [r for r in results if r['component'] == component]
                        urls = set(r['url'] for r in component_matches)
                        print(f"  • {component}: {urls}")
                else:
                    print("  No matches found")

            except Exception as e:
                print(f"Error testing {subdir.name}: {e}")
                all_results[subdir.name] = []

    # Save detailed results
    print(f"\n=== SCANOSS Discovery Summary ===")
    with open("scanoss_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    total_matches = sum(len(results) for results in all_results.values())
    directories_with_matches = sum(1 for results in all_results.values() if results)

    print(f"Total matches found: {total_matches}")
    print(f"Directories with matches: {directories_with_matches}/{len(all_results)}")
    print(f"Results saved to: scanoss_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())