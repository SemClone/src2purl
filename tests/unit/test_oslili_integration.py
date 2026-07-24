"""Unit tests for the oslili license detection integration."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
        assert enhanced.metadata["third_party_licenses"] == ["GPL-3.0-only"]

    def test_third_party_only_does_not_become_the_package_license(self, integration):
        """A bundled dependency license must not be attributed to the package."""
        detector = integration(
            [
                make_license(
                    "GPL-3.0-only",
                    "third-party",
                    confidence=0.99,
                    source_file="THIRD_PARTY_NOTICES.txt",
                ),
            ]
        )
        match = SimpleNamespace(license=None, metadata={})

        enhanced = detector.enhance_package_match(match, Path("/some/project"))

        assert enhanced.license is None
        # ...but it is still reported, just not as the package's own license
        assert enhanced.metadata["third_party_licenses"] == ["GPL-3.0-only"]

    def test_third_party_only_does_not_overwrite_an_existing_license(self, integration):
        """A high-confidence bundled notice must not clobber a known license."""
        detector = integration(
            [
                make_license(
                    "GPL-3.0-only",
                    "third-party",
                    confidence=0.99,
                    source_file="THIRD_PARTY_NOTICES.txt",
                ),
            ]
        )
        match = SimpleNamespace(license="Apache-2.0", metadata={})

        enhanced = detector.enhance_package_match(match, Path("/some/project"))

        assert enhanced.license == "Apache-2.0"
        assert enhanced.metadata["third_party_licenses"] == ["GPL-3.0-only"]

    def test_own_license_still_wins_when_only_referenced(self, integration):
        """A referenced license is still the project's own and remains eligible."""
        detector = integration(
            [
                make_license("MIT", "third-party", source_file="3rdpartylicenses.txt"),
                make_license("BSD-3-Clause", "referenced", source_file="README.md"),
            ]
        )
        match = SimpleNamespace(license=None, metadata={})

        enhanced = detector.enhance_package_match(match, Path("/some/project"))

        assert enhanced.license == "BSD-3-Clause"


class TestDetectLicensesSplitView:
    """detect_licenses reports own and third-party licenses separately."""

    def test_split_buckets(self, integration):
        detector = integration(
            [
                make_license("Apache-2.0", "declared", source_file="LICENSE"),
                make_license("BSD-3-Clause", "detected", source_file="src/main.py"),
                make_license("MIT", "third-party", source_file="THIRD_PARTY_NOTICES.txt"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        assert result["own_licenses"] == ["Apache-2.0", "BSD-3-Clause"]
        assert result["third_party_licenses"] == ["MIT"]
        assert result["licenses"] == ["Apache-2.0", "BSD-3-Clause", "MIT"]

    def test_same_license_can_be_both_own_and_third_party(self, integration):
        """Overlap is reported in both buckets, not resolved by set difference."""
        detector = integration(
            [
                make_license("MIT", "declared", source_file="LICENSE"),
                make_license("MIT", "third-party", source_file="THIRD_PARTY_NOTICES.txt"),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        assert result["own_licenses"] == ["MIT"]
        assert result["third_party_licenses"] == ["MIT"]

    def test_keys_present_when_nothing_detected(self, integration):
        """The contract holds on the empty path too."""
        detector = integration([])

        result = detector.detect_licenses(Path("/some/project"))

        assert result["own_licenses"] == []
        assert result["third_party_licenses"] == []
        assert result["own_confidence"] == 0.0


class TestOwnConfidence:
    """Third-party notices must not inflate the score used to pick the own license."""

    def test_own_confidence_excludes_third_party(self, integration):
        detector = integration(
            [
                make_license("Apache-2.0", "detected", confidence=0.5, source_file="a.py"),
                make_license(
                    "MIT",
                    "third-party",
                    confidence=1.0,
                    source_file="THIRD_PARTY_NOTICES.txt",
                ),
            ]
        )

        result = detector.detect_licenses(Path("/some/project"))

        # Overall confidence still averages everything that was detected
        assert result["confidence"] == pytest.approx(0.75)
        # ...but the own-license score reflects only the own detection
        assert result["own_confidence"] == pytest.approx(0.5)

    def test_high_confidence_notices_do_not_overwrite_known_license(self, integration):
        """A weak own detection must not clobber a known license on inflated score.

        Enough high-confidence bundled notices push the aggregate above the 0.85
        overwrite threshold while the own detection alone stays well below it.
        """
        detector = integration(
            [
                make_license("BSD-3-Clause", "detected", confidence=0.6, source_file="a.py"),
                make_license("MIT", "third-party", confidence=1.0, source_file="notices/a.txt"),
                make_license("ISC", "third-party", confidence=1.0, source_file="notices/b.txt"),
            ]
        )
        match = SimpleNamespace(license="Apache-2.0", metadata={})

        result = detector.detect_licenses(Path("/some/project"))
        # Aggregate clears the 0.85 overwrite bar purely because of the notices
        assert result["confidence"] > 0.85
        assert result["own_confidence"] == pytest.approx(0.6)

        enhanced = detector.enhance_package_match(match, Path("/some/project"))

        # ...so gating on own confidence is what keeps the known license intact
        assert enhanced.license == "Apache-2.0"
        assert enhanced.metadata["third_party_licenses"] == ["MIT", "ISC"]

    def test_confident_own_license_still_sets_the_license(self, integration):
        """The normal path is unchanged: a confident own license is still applied."""
        detector = integration(
            [
                make_license("BSD-3-Clause", "declared", confidence=0.99, source_file="LICENSE"),
                make_license(
                    "MIT",
                    "third-party",
                    confidence=0.99,
                    source_file="THIRD_PARTY_NOTICES.txt",
                ),
            ]
        )
        match = SimpleNamespace(license="Apache-2.0", metadata={})

        enhanced = detector.enhance_package_match(match, Path("/some/project"))

        assert enhanced.license == "BSD-3-Clause"


class TestPackageIdentifierLicenseAttribution:
    """The other direct detect_licenses() caller must not attribute bundled licenses.

    Driven through asyncio.run rather than pytest.mark.asyncio: CI installs only
    pytest and pytest-cov, so the suite must not depend on pytest-asyncio.
    """

    def _identify(self, licenses):
        """Run PackageIdentifier.identify_packages with oslili returning `licenses`."""
        from src2id.core.package_identifier import PackageIdentifier

        integration = OsliliIntegration.__new__(OsliliIntegration)
        integration.available = True
        integration.detector = FakeDetector(licenses)

        async def fake_identify_source(**kwargs):
            return {
                "identified": True,
                "confidence": 0.9,
                "final_origin": "https://example.com/pkg",
                "candidates": [],
            }

        with patch("src2id.core.package_identifier.identify_source", fake_identify_source):
            with patch("src2id.integrations.oslili.OsliliIntegration", return_value=integration):
                matches = asyncio.run(PackageIdentifier().identify_packages(Path("/some/project")))

        assert len(matches) == 1
        return matches[0]

    def test_third_party_only_leaves_license_unset(self):
        """A bundled dependency license must not identify the package."""
        match = self._identify(
            [make_license("MIT", "third-party", source_file="THIRD_PARTY_NOTICES.txt")]
        )

        assert match.license == ""

    def test_own_license_is_used(self):
        match = self._identify(
            [
                make_license("Apache-2.0", "declared", source_file="LICENSE"),
                make_license("MIT", "third-party", source_file="THIRD_PARTY_NOTICES.txt"),
            ]
        )

        assert match.license == "Apache-2.0"
