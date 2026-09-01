"""Keyword search runs only when asked for, and only when nothing else answered.

Issue #59. Run against the extracted express@4.18.2 tarball without
--enable-fuzzy, src2purl returned the correct express match at 0.85 alongside
ten npm packages at 0.83:

    exact  0.85  pkg:npm/express@4.18.2  express
    fuzzy  0.83  None                    senam5jari-975
    fuzzy  0.83  None                    voiti-1xbet-rech-idet-urxfhkrm
    ...

Two things were wrong. The flag says fuzzy runs "when exact matches fail" and it
was never consulted at this call site, and the search ran in phase 1, before the
manifest parsing in phase 2 that produces the exact match, so "did the exact
match fail" could not have been known yet.

The 0.02 gap between the right answer and npm spam is what makes it costly:
anything consuming by --confidence-threshold gets both, and the spam carries
purl: null so it cannot be acted on downstream either.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src2id.core.config import SWHPIConfig
from src2id.core.models import MatchType, PackageMatch
from src2id.core.orchestrator import SHPackageIdentifier


def _manifest_match():
    """What phase 2 finds for express, from package.json."""
    return PackageMatch(
        name="express",
        version="4.18.2",
        confidence_score=0.85,
        match_type=MatchType.EXACT,
        download_url="https://www.npmjs.com/package/express",
        purl="pkg:npm/express@4.18.2",
        license="MIT",
        is_official_org=False,
    )


def _spam_match(name):
    """What keyword search finds: anything sharing the project name."""
    return PackageMatch(
        name=name,
        version=None,
        confidence_score=0.83,
        match_type=MatchType.FUZZY,
        download_url=f"https://www.npmjs.com/package/{name}",
        purl=None,
        license="MIT",
        is_official_org=False,
    )


def _identifier(enable_fuzzy, manifest, keyword):
    config = SWHPIConfig(enable_fuzzy_matching=enable_fuzzy, use_swh=False)
    identifier = SHPackageIdentifier(config)
    identifier._scan_directories = AsyncMock(return_value=([MagicMock()], []))
    identifier._extract_with_upmex = MagicMock(return_value=list(manifest))
    identifier._find_keyword_matches = AsyncMock(return_value=[MagicMock() for _ in keyword])
    identifier._process_matches = AsyncMock(return_value=list(keyword))
    return identifier


def _run(identifier, tmp_path):
    return asyncio.run(identifier.identify_packages(tmp_path, enhance_licenses=False))


class TestFuzzyIsGatedOnTheFlag:
    def test_not_requested_means_no_keyword_search(self, tmp_path):
        """The reported case: an exact match, and ten fuzzy ones nobody asked for."""
        identifier = _identifier(
            enable_fuzzy=False,
            manifest=[_manifest_match()],
            keyword=[_spam_match("senam5jari-975"), _spam_match("voiti-1xbet-rech-idet-urxfhkrm")],
        )

        result = _run(identifier, tmp_path)

        identifier._find_keyword_matches.assert_not_called()
        assert [m.name for m in result] == ["express"]
        assert all(m.match_type is not MatchType.FUZZY for m in result)

    def test_not_requested_and_nothing_found_still_means_no_keyword_search(self, tmp_path):
        identifier = _identifier(enable_fuzzy=False, manifest=[], keyword=[_spam_match("whatever")])

        result = _run(identifier, tmp_path)

        identifier._find_keyword_matches.assert_not_called()
        assert result == []


class TestFuzzyRunsOnlyWhenExactFailed:
    def test_requested_but_something_answered_means_no_keyword_search(self, tmp_path):
        """ "when exact matches fail" cannot be judged before phase 2 has run."""
        identifier = _identifier(
            enable_fuzzy=True,
            manifest=[_manifest_match()],
            keyword=[_spam_match("senam5jari-975")],
        )

        result = _run(identifier, tmp_path)

        identifier._find_keyword_matches.assert_not_called()
        assert [m.name for m in result] == ["express"]

    def test_requested_and_nothing_answered_means_keyword_search_runs(self, tmp_path):
        identifier = _identifier(
            enable_fuzzy=True, manifest=[], keyword=[_spam_match("something-alike")]
        )

        result = _run(identifier, tmp_path)

        identifier._find_keyword_matches.assert_called_once()
        assert [m.name for m in result] == ["something-alike"]


class TestTheSoftwareHeritagePathIsGatedToo:
    """--use-swh took a different route with its own ungated keyword search."""

    def _identifier(self, enable_fuzzy, manifest, keyword, sh_matches=None):
        config = SWHPIConfig(enable_fuzzy_matching=enable_fuzzy, use_swh=True)
        identifier = SHPackageIdentifier(config)
        identifier._scan_directories = AsyncMock(return_value=([MagicMock()], []))
        identifier._find_matches = AsyncMock(return_value=list(sh_matches or []))
        identifier._extract_with_upmex = MagicMock(return_value=list(manifest))
        identifier._find_keyword_matches = AsyncMock(return_value=[MagicMock() for _ in keyword])
        identifier._process_matches = AsyncMock(return_value=list(keyword))
        return identifier

    def test_no_keyword_search_when_the_manifest_answered(self, tmp_path):
        """Software Heritage found nothing, but package.json did."""
        identifier = self._identifier(
            enable_fuzzy=True,
            manifest=[_manifest_match()],
            keyword=[_spam_match("senam5jari-975")],
        )

        result = asyncio.run(identifier.identify_packages(tmp_path, enhance_licenses=False))

        identifier._find_keyword_matches.assert_not_called()
        assert [m.name for m in result] == ["express"]

    def test_no_keyword_search_without_the_flag(self, tmp_path):
        identifier = self._identifier(
            enable_fuzzy=False, manifest=[], keyword=[_spam_match("whatever")]
        )

        result = asyncio.run(identifier.identify_packages(tmp_path, enhance_licenses=False))

        identifier._find_keyword_matches.assert_not_called()
        assert result == []

    def test_keyword_search_runs_when_asked_and_nothing_answered(self, tmp_path):
        identifier = self._identifier(
            enable_fuzzy=True, manifest=[], keyword=[_spam_match("something-alike")]
        )

        result = asyncio.run(identifier.identify_packages(tmp_path, enhance_licenses=False))

        identifier._find_keyword_matches.assert_called_once()
        assert [m.name for m in result] == ["something-alike"]
