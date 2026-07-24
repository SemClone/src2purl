"""Unit tests for the oslili license detection integration."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src2id.integrations.oslili import OsliliIntegration


def make_license(spdx_id, category, confidence=0.95, source_file=None):
    """Build a stand-in for an osslili DetectedLicense."""
    return SimpleNamespace(
        spdx_id=spdx_id,
        category=category,
        confidence=confidence,
        source_file=source_file or f"{spdx_id}.txt",
        detection_method="full_text",
    )


class FakeDetector:
    """Stand-in for osslili's LicenseCopyrightDetector."""

    def __init__(self, licenses, copyrights=None):
        self.licenses = licenses
        self.copyrights = copyrights or []

    def process_local_path(self, path):
        return SimpleNamespace(licenses=self.licenses, copyrights=self.copyrights)


@pytest.fixture
def integration():
    """Integration wired to a fake detector, independent of osslili being installed."""

    def _build(licenses, copyrights=None):
        instance = OsliliIntegration.__new__(OsliliIntegration)
        instance.available = True
        instance.detector = FakeDetector(licenses, copyrights)
        return instance

    return _build


class TestThirdPartyCategory:
    """osslili 1.7.0 categorizes bundled notice files as `third-party`."""

    def test_third_party_licenses_are_retained(self, integration):
        """A third-party license must not be dropped from the aggregation."""
        detector = integration(
            [
                make_license("Apache-2.0", "declared", source_file="LICENSE"),
                make_license("MIT", "third-party", source_file="THIRD_PARTY_NOTICES.txt"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        assert result["licenses"] == ["Apache-2.0", "MIT"]

    def test_third_party_never_outranks_project_license(self, integration):
        """Third-party licenses sort last, so primary selection is unaffected."""
        detector = integration(
            [
                make_license("GPL-3.0-only", "third-party", source_file="3rdpartylicenses.txt"),
                make_license("BSD-3-Clause", "referenced", source_file="README.md"),
                make_license("Apache-2.0", "detected", source_file="src/main.py"),
                make_license("MIT", "declared", source_file="LICENSE"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        # declared -> detected -> referenced -> third-party
        assert result["licenses"] == [
            "MIT",
            "Apache-2.0",
            "BSD-3-Clause",
            "GPL-3.0-only",
        ]
        assert result["licenses"][0] == "MIT"

    def test_third_party_only_still_reports_the_license(self, integration):
        """When only bundled notices exist, the license is still surfaced."""
        detector = integration(
            [
                make_license("MIT", "third-party", source_file="THIRD_PARTY_NOTICES.txt"),
                make_license("ISC", "third-party", source_file="THIRD_PARTY_NOTICES.txt"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        assert result["licenses"] == ["MIT", "ISC"]
        assert result["files"]["THIRD_PARTY_NOTICES.txt"][0]["category"] == "third-party"

    def test_third_party_license_is_mapped_to_its_source_file(self, integration):
        """The file mapping records the third-party category for downstream use."""
        detector = integration(
            [
                make_license("Apache-2.0", "declared", source_file="LICENSE"),
                make_license("MIT", "third-party", source_file="THIRD_PARTY_NOTICES.txt"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        assert set(result["files"]) == {"LICENSE", "THIRD_PARTY_NOTICES.txt"}
        notice_entry = result["files"]["THIRD_PARTY_NOTICES.txt"][0]
        assert notice_entry["spdx_id"] == "MIT"
        assert notice_entry["category"] == "third-party"

    def test_legacy_categories_are_unaffected(self, integration):
        """Pre-1.7.0 osslili output (no third-party category) behaves as before."""
        detector = integration(
            [
                make_license("BSD-3-Clause", "referenced", source_file="README.md"),
                make_license("MIT", "declared", source_file="LICENSE"),
                make_license("Apache-2.0", "detected", source_file="src/main.py"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        assert result["licenses"] == ["MIT", "Apache-2.0", "BSD-3-Clause"]

    def test_unknown_future_category_does_not_crash(self, integration):
        """An unrecognized category is skipped without raising."""
        detector = integration(
            [
                make_license("MIT", "declared", source_file="LICENSE"),
                make_license("Apache-2.0", "some-future-category"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        assert result["licenses"] == ["MIT"]


class TestEnhancePackageMatch:
    """Primary-license selection must prefer the project's own license."""

    def test_primary_license_prefers_declared_over_third_party(self, integration):
        detector = integration(
            [
                make_license(
                    "GPL-3.0-only",
                    "third-party",
                    confidence=0.99,
                    source_file="THIRD_PARTY_NOTICES.txt",
                ),
                make_license("Apache-2.0", "declared", confidence=0.99, source_file="LICENSE"),
            ]
        )
        match = SimpleNamespace(license=None, metadata={})

        enhanced = detector.enhance_package_match(match, Path("/some/project"))

        assert enhanced.license == "Apache-2.0"
        assert enhanced.metadata["additional_licenses"] == ["GPL-3.0-only"]
