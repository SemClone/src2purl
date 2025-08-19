"""Integration with oslili for enhanced license detection.

This module provides integration with the oslili (Open Source License 
Identification Library) tool for more accurate license detection in packages.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import oslili
    HAS_OSLILI = True
except ImportError:
    HAS_OSLILI = False


class OsliliIntegration:
    """Integration with oslili for license detection."""
    
    def __init__(self):
        """Initialize oslili integration."""
        self.available = self._check_availability()
        if self.available and HAS_OSLILI:
            try:
                # Initialize oslili if available
                self.detector = oslili.LicenseDetector()
            except Exception:
                self.detector = None
        else:
            self.detector = None
    
    def _check_availability(self) -> bool:
        """Check if oslili is available."""
        if HAS_OSLILI:
            return True
        
        # Check if oslili CLI is available
        try:
            result = subprocess.run(
                ["oslili", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
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
        if not self.available:
            return {
                "licenses": [],
                "confidence": 0.0,
                "files": {},
                "summary": "oslili not available",
                "error": "oslili integration not available"
            }
        
        # Use Python API if available
        if self.detector:
            return self._detect_with_api(path)
        else:
            # Fall back to CLI
            return self._detect_with_cli(path)
    
    def _detect_with_api(self, path: Path) -> Dict[str, Any]:
        """Detect licenses using oslili Python API."""
        try:
            # Scan the path
            results = self.detector.scan(str(path))
            
            # Process results
            licenses = set()
            file_licenses = {}
            confidence_scores = []
            
            for file_path, file_result in results.items():
                if file_result.licenses:
                    file_licenses[file_path] = file_result.licenses
                    licenses.update(file_result.licenses)
                    if file_result.confidence:
                        confidence_scores.append(file_result.confidence)
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Generate summary
            license_list = sorted(licenses)
            if license_list:
                summary = f"Found {len(license_list)} license(s): {', '.join(license_list)}"
            else:
                summary = "No licenses detected"
            
            return {
                "licenses": license_list,
                "confidence": avg_confidence,
                "files": file_licenses,
                "summary": summary
            }
            
        except Exception as e:
            return {
                "licenses": [],
                "confidence": 0.0,
                "files": {},
                "summary": f"Error during detection: {e}",
                "error": str(e)
            }
    
    def _detect_with_cli(self, path: Path) -> Dict[str, Any]:
        """Detect licenses using oslili CLI."""
        try:
            # Run oslili CLI
            result = subprocess.run(
                ["oslili", "scan", str(path), "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "licenses": [],
                    "confidence": 0.0,
                    "files": {},
                    "summary": f"oslili CLI error: {result.stderr}",
                    "error": result.stderr
                }
            
            # Parse JSON output
            import json
            data = json.loads(result.stdout)
            
            # Extract licenses
            licenses = data.get("licenses", [])
            confidence = data.get("confidence", 0.0)
            
            return {
                "licenses": licenses,
                "confidence": confidence,
                "files": data.get("files", {}),
                "summary": data.get("summary", "Processed with oslili CLI")
            }
            
        except subprocess.TimeoutExpired:
            return {
                "licenses": [],
                "confidence": 0.0,
                "files": {},
                "summary": "oslili scan timeout",
                "error": "Scan timeout exceeded"
            }
        except Exception as e:
            return {
                "licenses": [],
                "confidence": 0.0,
                "files": {},
                "summary": f"Error running oslili CLI: {e}",
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