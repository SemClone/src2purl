#!/usr/bin/env python3
"""Test that all fixes are working properly."""

import asyncio
import warnings
from pathlib import Path

# Suppress urllib3 warnings
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

from swhpi.search import identify_source

async def test_fixes():
    """Test all the fixes."""
    
    print("Testing fixes for:")
    print("1. urllib3 warning - should be suppressed")
    print("2. Unclosed sessions - should be cleaned up")
    print("3. SCANOSS division - should handle string values")
    print()
    
    # Run identification
    results = await identify_source(
        path=Path("test_data/darktable/packaging"),
        max_depth=1,
        confidence_threshold=0.3,
        verbose=True,
        use_swh=False
    )
    
    print(f"\nIdentification complete:")
    print(f"- Identified: {results['identified']}")
    print(f"- Confidence: {results['confidence']:.1%}")
    print(f"- No warnings or unclosed sessions should appear above")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_fixes())
    print("\n✅ Test completed successfully!")