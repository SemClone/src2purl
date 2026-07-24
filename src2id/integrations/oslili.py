"""Integration with oslili for enhanced license detection.

This module provides integration with the oslili (Open Source License 
Identification Library) tool for more accurate license detection in packages.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from osslili import (
        LicenseCopyrightDetector,
        DetectionResult,
        DetectedLicense,
        CopyrightInfo,
        Config
    )
    HAS_OSLILI = True
except ImportError:
    HAS_OSLILI = False
    Config = None  # Define Config as None for type hints when oslili not available


class OsliliIntegration:
    """Integration with oslili for license detection."""
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize oslili integration.
        
        Args:
            config: Optional Config object for oslili configuration
        """
        self.available = HAS_OSLILI
        if self.available:
            try:
                # Create config if not provided
                if config is None and HAS_OSLILI:
                    config = Config(
                        verbose=False,
                        debug=False,
                        thread_count=4,
                        similarity_threshold=0.97,
                        max_recursion_depth=5
                    )
                self.detector = LicenseCopyrightDetector(config)
            except Exception:
                self.detector = None
                self.available = False
        else:
            self.detector = None
    
    def detect_licenses(self, path: Path) -> Dict[str, Any]:
        """
        Detect licenses in a directory or file.
        
        Args:
            path: Path to analyze
            
        Returns:
            Dictionary with license information:
            - licenses: List of detected license identifiers
            - own_licenses: Identifiers eligible to be the project's own license
            - third_party_licenses: Identifiers from bundled third-party notice files
            - confidence: Confidence score (0-1) across all detections
            - own_confidence: Confidence score (0-1) across own licenses only
            - files: Dict mapping files to their licenses
            - summary: Human-readable summary
        """
        if not self.available or not self.detector:
            return {
                "licenses": [],
                "own_licenses": [],
                "third_party_licenses": [],
                "confidence": 0.0,
                "own_confidence": 0.0,
                "files": {},
                "summary": "oslili not available",
                "error": "oslili integration not available"
            }
        
        try:
            # Process the path using oslili v1.3.2
            result: DetectionResult = self.detector.process_local_path(str(path))
            
            if result and result.licenses:
                # Extract license information
                licenses = []
                confidence_scores = []
                files = {}
                
                # Group licenses by category for better understanding
                declared = [lic for lic in result.licenses if lic.category == "declared"]
                detected = [lic for lic in result.licenses if lic.category == "detected"]
                referenced = [lic for lic in result.licenses if lic.category == "referenced"]
                # Licenses of bundled dependencies (THIRD_PARTY_NOTICES.txt and
                # friends), not the project's own license. Kept, but ranked last so
                # they never win the primary-license selection.
                third_party = [lic for lic in result.licenses if lic.category == "third-party"]

                # Prioritize declared licenses, then detected, then referenced,
                # with bundled third-party licenses last
                own = declared + detected + referenced
                all_licenses = own + third_party

                for license_info in all_licenses:
                    licenses.append(license_info.spdx_id)
                    confidence_scores.append(license_info.confidence)
                    
                    # Map files to licenses
                    if license_info.source_file:
                        if license_info.source_file not in files:
                            files[license_info.source_file] = []
                        files[license_info.source_file].append({
                            "spdx_id": license_info.spdx_id,
                            "confidence": license_info.confidence,
                            "category": license_info.category,
                            "method": license_info.detection_method
                        })
                
                # Calculate average confidence
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.8

                # Confidence in the project's own licenses, kept separate so a pile of
                # high-confidence bundled notice files cannot inflate the score used to
                # decide the package's own license
                own_scores = [lic.confidence for lic in own]
                own_confidence = sum(own_scores) / len(own_scores) if own_scores else 0.0
                
                # Generate summary
                if licenses:
                    # Remove duplicates while preserving order
                    unique_licenses = self._deduplicate_licenses(licenses)
                    summary = f"Found {len(unique_licenses)} unique license(s): {', '.join(unique_licenses[:3])}"
                    if len(unique_licenses) > 3:
                        summary += f" and {len(unique_licenses) - 3} more"
                    
                    # Add category info to summary
                    if declared:
                        summary += f" (Declared: {len(declared)})"
                    if detected:
                        summary += f" (Detected: {len(detected)})"
                else:
                    summary = "No licenses detected"
                
                return {
                    "licenses": licenses,
                    # Split view of the same licenses: "own" are candidates for the
                    # project's license, "third_party" come from bundled notice files
                    # and must not be attributed to the project itself.
                    "own_licenses": self._deduplicate_licenses([lic.spdx_id for lic in own]),
                    "third_party_licenses": self._deduplicate_licenses(
                        [lic.spdx_id for lic in third_party]
                    ),
                    "confidence": avg_confidence,
                    "own_confidence": own_confidence,
                    "files": files,
                    "summary": summary,
                    "copyrights": [c.to_dict() for c in result.copyrights] if result.copyrights else []
                }
            else:
                return {
                    "licenses": [],
                    "own_licenses": [],
                    "third_party_licenses": [],
                    "confidence": 0.0,
                    "own_confidence": 0.0,
                    "files": {},
                    "summary": "No licenses detected",
                    "copyrights": []
                }
                
        except Exception as e:
            return {
                "licenses": [],
                "own_licenses": [],
                "third_party_licenses": [],
                "confidence": 0.0,
                "own_confidence": 0.0,
                "files": {},
                "summary": f"Error during detection: {e}",
                "error": str(e)
            }
    
    def _deduplicate_licenses(self, licenses: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        return list(dict.fromkeys(licenses))
    
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
        
        # Only the project's own licenses are eligible to become this package's
        # license: one found in a bundled third-party notice file belongs to a
        # dependency, so attributing it here would be wrong. Bundled notices must
        # therefore neither raise nor lower the bar for the own license, which is
        # why the decision below uses own_confidence rather than the aggregate.
        own_licenses = self._deduplicate_licenses(license_info.get("own_licenses") or [])
        own_confidence = license_info.get("own_confidence") or 0.0

        # Update match if we found licenses with good confidence
        if license_info["licenses"] and (
            license_info["confidence"] > 0.7 or own_confidence > 0.7
        ):
            # Remove duplicates while preserving order
            unique_licenses = self._deduplicate_licenses(license_info["licenses"])
            
            # Update match license if not already set or if ours is more confident.
            # When nothing but bundled notices was found there is no own license, so
            # match.license is left alone rather than guessed at.
            if own_licenses and own_confidence > 0.7 and (
                not match.license or own_confidence > 0.85
            ):
                match.license = own_licenses[0]
            
            # Add metadata about additional licenses and copyrights
            if not hasattr(match, "metadata"):
                match.metadata = {}
            
            if len(unique_licenses) > 1:
                match.metadata["additional_licenses"] = unique_licenses[1:]

            # Surface bundled third-party licenses separately so callers can report
            # them without mistaking them for the package's own license
            if license_info.get("third_party_licenses"):
                match.metadata["third_party_licenses"] = license_info["third_party_licenses"]
            
            match.metadata["license_confidence"] = license_info["confidence"]
            
            # Add copyright information if available
            if license_info.get("copyrights"):
                match.metadata["copyrights"] = license_info["copyrights"]
            
            # Add file mapping if available
            if license_info.get("files"):
                match.metadata["license_files"] = license_info["files"]
        
        return match
    


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