#!/usr/bin/env python3
"""Test GitHub discovery method individually."""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '/Users/ovalenzuela/Projects/semantic-copycat-src2id')

from src2id.search.providers import GitHubSearchProvider
import json

async def test_github_on_directory(directory: Path):
    """Test GitHub search on a specific directory."""
    print(f"\n=== Testing GitHub on {directory} ===")

    # Get GitHub token if available
    github_token = os.environ.get('GITHUB_TOKEN')
    provider = GitHubSearchProvider(api_key=github_token, verbose=True)

    results = []

    # Extract potential project names from directory structure
    project_names = []

    # Use directory name as primary search term
    project_names.append(directory.name)

    # Look for known project indicators
    readme_files = list(directory.glob("README*"))
    for readme in readme_files:
        if readme.is_file():
            try:
                content = readme.read_text(encoding='utf-8', errors='ignore')[:500]
                # Extract project name from first line often contains "# ProjectName"
                lines = content.split('\n')
                for line in lines[:3]:
                    if line.startswith('#'):
                        potential_name = line.strip('# ').strip()
                        if potential_name and len(potential_name) < 50:
                            project_names.append(potential_name)
                        break
            except:
                pass

    # Look for package.json, setup.py, etc for project names
    for pattern in ["package.json", "setup.py", "Cargo.toml", "go.mod"]:
        manifest_files = list(directory.glob(f"**/{pattern}"))[:1]
        for manifest in manifest_files:
            try:
                content = manifest.read_text(encoding='utf-8', errors='ignore')
                if 'name' in content:
                    # Simple extraction - could be improved
                    for line in content.split('\n'):
                        if '"name"' in line and ':' in line:
                            name_part = line.split(':')[1].strip().strip('"').strip(',')
                            if name_part and len(name_part) < 30:
                                project_names.append(name_part)
                            break
            except:
                pass

    # Remove duplicates and clean names
    unique_names = list(set(project_names))
    clean_names = []
    for name in unique_names:
        clean_name = name.replace('_', '-').replace(' ', '-').lower()
        if len(clean_name) >= 3 and clean_name.replace('-', '').isalnum():
            clean_names.append(clean_name)

    print(f"Search terms: {clean_names}")

    for search_term in clean_names[:3]:  # Limit to avoid rate limits
        try:
            print(f"\nSearching GitHub for: '{search_term}'")
            urls = await provider.search(search_term)

            if urls:
                print(f"  ✓ Found {len(urls)} repositories")
                for i, url in enumerate(urls[:5], 1):
                    print(f"    {i}. {url}")
                    results.append({
                        "search_term": search_term,
                        "url": url,
                        "rank": i,
                        "source": "github_search"
                    })
            else:
                print(f"  - No repositories found for '{search_term}'")

        except Exception as e:
            print(f"  ✗ Error searching for '{search_term}': {e}")

    await provider.close()
    return results

async def main():
    """Test GitHub search on all test directories."""
    test_data = Path("test_data")

    all_results = {}

    # Test each subdirectory
    for subdir in test_data.iterdir():
        if subdir.is_dir():
            try:
                results = await test_github_on_directory(subdir)
                all_results[subdir.name] = results

                print(f"\n--- Summary for {subdir.name} ---")
                if results:
                    unique_repos = set(r['url'] for r in results)
                    search_terms = set(r['search_term'] for r in results)
                    print(f"Found {len(unique_repos)} unique repositories from {len(search_terms)} search terms")

                    # Show top result for each search term
                    for term in search_terms:
                        term_results = [r for r in results if r['search_term'] == term]
                        if term_results:
                            top_result = min(term_results, key=lambda x: x['rank'])
                            print(f"  '{term}' → {top_result['url']} (rank #{top_result['rank']})")
                else:
                    print("  No repositories found")

            except Exception as e:
                print(f"Error testing {subdir.name}: {e}")
                all_results[subdir.name] = []

    # Save detailed results
    print(f"\n=== GitHub Discovery Summary ===")
    with open("github_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    total_repos = sum(len(set(r['url'] for r in results)) for results in all_results.values())
    directories_with_matches = sum(1 for results in all_results.values() if results)

    print(f"Total unique repositories found: {total_repos}")
    print(f"Directories with matches: {directories_with_matches}/{len(all_results)}")
    print(f"Results saved to: github_test_results.json")

    # Check if we have GitHub token
    if os.environ.get('GITHUB_TOKEN'):
        print("✅ Using GitHub token for authenticated requests")
    else:
        print("⚠️ No GitHub token - using unauthenticated requests (rate limited)")

if __name__ == "__main__":
    asyncio.run(main())