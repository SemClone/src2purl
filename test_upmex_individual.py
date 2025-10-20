#!/usr/bin/env python3
"""Test UPMEX/Manifest parsing discovery method individually."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '/Users/ovalenzuela/Projects/semantic-copycat-src2id')

from src2id.integrations.upmex import UpmexIntegration
import json

async def test_upmex_on_directory(directory: Path):
    """Test UPMEX/manifest parsing on a specific directory."""
    print(f"\n=== Testing UPMEX/Manifest Parsing on {directory} ===")

    upmex = UpmexIntegration(enabled=True)
    results = []

    # Step 1: Scan for package files
    package_files = upmex.scan_directory_for_packages(directory)
    print(f"Found {len(package_files)} manifest files:")
    for file_path in package_files:
        print(f"  - {file_path.relative_to(directory)}")

    # Step 2: Extract metadata from directory
    try:
        matches = upmex.extract_metadata_from_directory(directory)
        print(f"\nExtracted metadata from {len(matches)} packages:")

        for match in matches:
            result = {
                "name": match.name,
                "version": match.version,
                "license": match.license,
                "purl": match.purl,
                "confidence": match.confidence_score,
                "match_type": match.match_type.value,
                "download_url": match.download_url,
                "is_official": match.is_official_org
            }
            results.append(result)

            print(f"\n  📦 {match.name or 'Unknown'}")
            if match.version:
                print(f"     Version: {match.version}")
            if match.license:
                print(f"     License: {match.license}")
            if match.purl:
                print(f"     PURL: {match.purl}")
            print(f"     Confidence: {match.confidence_score:.1%}")
            print(f"     Type: {match.match_type.value}")
            if match.download_url:
                print(f"     URL: {match.download_url}")

    except Exception as e:
        print(f"  ✗ Error extracting metadata: {e}")

    return results

async def main():
    """Test UPMEX/manifest parsing on all test directories."""
    test_data = Path("test_data")

    all_results = {}

    # Test each subdirectory
    for subdir in test_data.iterdir():
        if subdir.is_dir():
            try:
                results = await test_upmex_on_directory(subdir)
                all_results[subdir.name] = results

                print(f"\n--- Summary for {subdir.name} ---")
                if results:
                    print(f"Extracted {len(results)} packages:")
                    for result in results:
                        name = result['name'] or 'Unknown'
                        version = result['version'] or 'No version'
                        purl = result['purl'] or 'No PURL'
                        print(f"  • {name} v{version} - {purl}")
                else:
                    print("  No packages extracted")

            except Exception as e:
                print(f"Error testing {subdir.name}: {e}")
                all_results[subdir.name] = []

    # Save detailed results
    print(f"\n=== UPMEX/Manifest Parsing Discovery Summary ===")
    with open("upmex_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    total_packages = sum(len(results) for results in all_results.values())
    directories_with_packages = sum(1 for results in all_results.values() if results)

    print(f"Total packages found: {total_packages}")
    print(f"Directories with packages: {directories_with_packages}/{len(all_results)}")
    print(f"Results saved to: upmex_test_results.json")

    # Summary by package type
    all_packages = []
    for results in all_results.values():
        all_packages.extend(results)

    if all_packages:
        licenses = [p['license'] for p in all_packages if p['license']]
        purls = [p['purl'] for p in all_packages if p['purl']]
        print(f"\nPackage Details:")
        print(f"  - Packages with licenses: {len(licenses)}/{len(all_packages)}")
        print(f"  - Packages with PURLs: {len(purls)}/{len(all_packages)}")

        # Most common ecosystems
        ecosystems = {}
        for purl in purls:
            if purl.startswith('pkg:'):
                ecosystem = purl.split('/')[0].split(':')[1]
                ecosystems[ecosystem] = ecosystems.get(ecosystem, 0) + 1

        if ecosystems:
            print(f"  - Ecosystems detected: {dict(ecosystems)}")

if __name__ == "__main__":
    asyncio.run(main())