"""Integration with oslili for enhanced license detection.

This module provides integration with the oslili (Open Source License 
Identification Library) tool for more accurate license detection in packages.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from semantic_copycat_oslili import LegalAttributionGenerator
    HAS_OSLILI = True
except ImportError:
    HAS_OSLILI = False


class OsliliIntegration:
    """Integration with oslili for license detection."""
    
    def __init__(self):
        """Initialize oslili integration."""
        self.available = HAS_OSLILI
        if self.available:
            try:
                self.generator = LegalAttributionGenerator()
            except Exception:
                self.generator = None
                self.available = False
        else:
            self.generator = None
    
    def detect_licenses(self, path: Path) -> Dict[str, Any]:
        """
        Detect licenses in a directory or file.
        
        Args:
            path: Path to analyze
            
        Returns:
            Dictionary with license information:
            - licenses: List of detected license identifiers
            - confidence: Confidence score (0-1)
            - files: Dict mapping files to their licenses
            - summary: Human-readable summary
        """
        if not self.available or not self.generator:
            return {
                "licenses": [],
                "confidence": 0.0,
                "files": {},
                "summary": "oslili not available",
                "error": "oslili integration not available"
            }
        
        try:
            # Process the path using oslili
            result = self.generator.process_local_path(str(path))
            
            if result and result.licenses:
                # Extract license information
                licenses = []
                confidence_scores = []
                
                for license_info in result.licenses:
                    if hasattr(license_info, 'spdx_id'):
                        licenses.append(license_info.spdx_id)
                        if hasattr(license_info, 'confidence'):
                            confidence_scores.append(license_info.confidence)
                
                # Calculate average confidence
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.8
                
                # Generate summary
                if licenses:
                    summary = f"Found {len(licenses)} license(s): {', '.join(licenses[:3])}"
                    if len(licenses) > 3:
                        summary += f" and {len(licenses) - 3} more"
                else:
                    summary = "No licenses detected"
                
                return {
                    "licenses": licenses,
                    "confidence": avg_confidence,
                    "files": {},
                    "summary": summary
                }
            else:
                return {
                    "licenses": [],
                    "confidence": 0.0,
                    "files": {},
                    "summary": "No licenses detected"
                }
                
        except Exception as e:
            return {
                "licenses": [],
                "confidence": 0.0,
                "files": {},
                "summary": f"Error during detection: {e}",
                "error": str(e)
            }
    
    
    
    def enhance_package_match(self, match: "PackageMatch", path: Path) -> "PackageMatch":
        """
        Enhance a package match with oslili license detection.
        
        Args:
            match: Package match to enhance
            path: Path to the package directory
            
        Returns:
            Enhanced package match with better license information
        """
        if not self.available:
            return match
        
        # Detect licenses
        license_info = self.detect_licenses(path)
        
        # Update match if we found licenses with good confidence
        if license_info["licenses"] and license_info["confidence"] > 0.7:
            # Use the most common license as primary
            primary_license = license_info["licenses"][0]
            
            # Update match license if not already set or if ours is more confident
            if not match.license or license_info["confidence"] > 0.85:
                match.license = primary_license
            
            # Add metadata about additional licenses
            if len(license_info["licenses"]) > 1:
                if not hasattr(match, "metadata"):
                    match.metadata = {}
                match.metadata["additional_licenses"] = license_info["licenses"][1:]
                match.metadata["license_confidence"] = license_info["confidence"]
        
        return match
    
    def find_license_files(self, path: Path) -> List[Path]:
        """
        Find common license files in a directory.
        
        Args:
            path: Directory to search
            
        Returns:
            List of paths to license files
        """
        license_patterns = [
            "LICENSE", "LICENSE.*", "LICENCE", "LICENCE.*",
            "COPYING", "COPYING.*", "COPYRIGHT", "COPYRIGHT.*",
            "NOTICE", "NOTICE.*", "LEGAL", "LEGAL.*",
            "MIT-LICENSE", "APACHE-LICENSE", "BSD-LICENSE",
            "GPL-LICENSE", "LGPL-LICENSE"
        ]
        
        license_files = []
        for pattern in license_patterns:
            license_files.extend(path.glob(pattern))
            license_files.extend(path.glob(pattern.lower()))
        
        # Also check in common subdirectories
        for subdir in ["docs", "doc", "legal", "licenses"]:
            subpath = path / subdir
            if subpath.exists():
                for pattern in license_patterns:
                    license_files.extend(subpath.glob(pattern))
                    license_files.extend(subpath.glob(pattern.lower()))
        
        # Remove duplicates and return
        return list(set(license_files))


def enhance_with_oslili(package_matches: List["PackageMatch"], base_path: Path) -> List["PackageMatch"]:
    """
    Enhance package matches with oslili license detection.
    
    Args:
        package_matches: List of package matches to enhance
        base_path: Base path where the code is located
        
    Returns:
        Enhanced package matches
    """
    integration = OsliliIntegration()
    
    if not integration.available:
        print("oslili not available - skipping license enhancement")
        return package_matches
    
    enhanced_matches = []
    for match in package_matches:
        enhanced = integration.enhance_package_match(match, base_path)
        enhanced_matches.append(enhanced)
    
    return enhanced_matches