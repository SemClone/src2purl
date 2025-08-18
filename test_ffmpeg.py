#!/usr/bin/env python3
"""Test script to verify SHPI with FFmpeg repository."""

import asyncio
import sys
from pathlib import Path

from shpi.core.config import SHPIConfig
from shpi.core.orchestrator import SHPackageIdentifier


async def test_with_local_directory():
    """Test with a local directory."""
    # You can change this path to point to your FFmpeg clone
    test_path = Path.cwd() / "test_data" / "ffmpeg"
    
    if not test_path.exists():
        print(f"Test directory {test_path} does not exist.")
        print("Please clone FFmpeg:")
        print("  git clone --depth 1 https://github.com/FFmpeg/FFmpeg.git test_data/ffmpeg")
        return
    
    print(f"Testing with: {test_path}")
    print("-" * 50)
    
    config = SHPIConfig(
        verbose=True,
        max_depth=3,
        report_match_threshold=0.5,
    )
    
    identifier = SHPackageIdentifier(config)
    
    try:
        matches = await identifier.identify_packages(test_path)
        
        print("\n" + "=" * 50)
        print("RESULTS:")
        print("=" * 50)
        
        if matches:
            for match in matches:
                print(f"\nPackage: {match.name or 'Unknown'}")
                print(f"  Version: {match.version or 'Unknown'}")
                print(f"  Confidence: {match.confidence_score:.2f}")
                print(f"  Type: {match.match_type.value}")
                print(f"  Official: {match.is_official_org}")
                print(f"  URL: {match.download_url}")
                if match.purl:
                    print(f"  PURL: {match.purl}")
                print(f"  SH URL: {match.sh_url}")
        else:
            print("No matches found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def test_swhid_generation():
    """Test SWHID generation on a simple directory."""
    from shpi.core.swhid import SWHIDGenerator
    
    print("\n" + "=" * 50)
    print("Testing SWHID Generation")
    print("=" * 50)
    
    generator = SWHIDGenerator(use_miniswhid=True)
    
    # Test on current directory
    test_path = Path.cwd()
    
    try:
        swhid = generator.generate_directory_swhid(test_path)
        print(f"Generated SWHID for {test_path.name}: {swhid}")
        
        # Validate the SWHID
        is_valid = generator.validate_swhid(swhid)
        print(f"SWHID valid: {is_valid}")
        
    except Exception as e:
        print(f"Error generating SWHID: {e}")


async def test_scanner():
    """Test directory scanner."""
    from shpi.core.scanner import DirectoryScanner
    from shpi.core.swhid import SWHIDGenerator
    
    print("\n" + "=" * 50)
    print("Testing Directory Scanner")
    print("=" * 50)
    
    config = SHPIConfig(verbose=True, max_depth=2)
    generator = SWHIDGenerator(use_miniswhid=True)
    scanner = DirectoryScanner(config, generator)
    
    test_path = Path.cwd()
    candidates = scanner.scan_recursive(test_path)
    
    print(f"\nFound {len(candidates)} directory candidates:")
    for candidate in candidates:
        print(f"  - {candidate.path.name}")
        print(f"    Depth: {candidate.depth}")
        print(f"    Files: {candidate.file_count}")
        print(f"    Score: {candidate.specificity_score:.2f}")
        print(f"    SWHID: {candidate.swhid[:50]}...")


async def main():
    """Run all tests."""
    print("SH Package Identifier - Test Suite")
    print("=" * 50)
    
    # Test SWHID generation
    await test_swhid_generation()
    
    # Test scanner
    await test_scanner()
    
    # Test with local directory
    await test_with_local_directory()


if __name__ == "__main__":
    asyncio.run(main())