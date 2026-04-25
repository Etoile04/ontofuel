"""Tests for extraction merger module."""

import pytest

from ontofuel.extraction.extractor import ExtractionResult
from ontofuel.extraction.merger import Merger, MergeStats


class TestMergeStats:
    """Test MergeStats."""

    def test_default_stats(self):
        stats = MergeStats()
        assert stats.input_results == 0
        assert stats.duplicates_removed == 0

    def test_to_dict(self):
        stats = MergeStats(input_results=3, total_individuals_in=10, duplicates_removed=3)
        d = stats.to_dict()
        assert d["input_results"] == 3
        assert "dedup_rate" in d


class TestMergerExact:
    """Test merger with exact deduplication."""

    def test_merge_no_duplicates(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "U-10Mo"}])
        r2 = ExtractionResult(source="c1", individuals=[{"name": "U-10Zr"}])
        merger = Merger(strategy="exact")
        merged = merger.merge([r1, r2])
        assert merged.stats.final_individuals == 2
        assert merged.stats.duplicates_removed == 0

    def test_merge_with_duplicates(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "U-10Mo"}])
        r2 = ExtractionResult(source="c1", individuals=[{"name": "U-10Mo"}])
        merger = Merger(strategy="exact")
        merged = merger.merge([r1, r2])
        assert merged.stats.final_individuals == 1
        assert merged.stats.duplicates_removed == 1

    def test_merge_three_results(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "A"}])
        r2 = ExtractionResult(source="c1", individuals=[{"name": "B"}])
        r3 = ExtractionResult(source="c2", individuals=[{"name": "A"}])
        merger = Merger(strategy="exact")
        merged = merger.merge([r1, r2, r3])
        assert merged.stats.final_individuals == 2
        assert merged.stats.duplicates_removed == 1

    def test_merge_empty(self):
        merger = Merger()
        merged = merger.merge([])
        assert merged.stats.final_individuals == 0


class TestMergerFuzzy:
    """Test merger with fuzzy deduplication."""

    def test_fuzzy_match(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "U-10Mo alloy"}])
        r2 = ExtractionResult(source="c1", individuals=[{"name": "U-10Mo Alloy"}])
        merger = Merger(strategy="fuzzy", fuzzy_threshold=0.8)
        merged = merger.merge([r1, r2])
        assert merged.stats.duplicates_removed >= 1

    def test_fuzzy_no_match(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "U-10Mo"}])
        r2 = ExtractionResult(source="c1", individuals=[{"name": "U-10Zr"}])
        merger = Merger(strategy="fuzzy", fuzzy_threshold=0.9)
        merged = merger.merge([r1, r2])
        assert merged.stats.final_individuals == 2


class TestMergerConflictResolution:
    """Test conflict resolution strategies."""

    def test_latest_wins(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "A", "value": 1}])
        r2 = ExtractionResult(source="c1", individuals=[{"name": "A", "value": 2}])
        merger = Merger(conflict_resolution="latest")
        merged = merger.merge([r1, r2])
        # Latest should win
        assert merged.stats.final_individuals == 1
        assert merged.individuals[0]["value"] == 2

    def test_merge_strategy(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "A", "x": 1}])
        r2 = ExtractionResult(source="c1", individuals=[{"name": "A", "y": 2}])
        merger = Merger(conflict_resolution="merge")
        merged = merger.merge([r1, r2])
        assert merged.stats.final_individuals == 1


class TestMergerProperties:
    """Test property merging."""

    def test_merge_properties(self):
        r1 = ExtractionResult(
            source="c0",
            properties=[{"name": "density", "value": 15.8, "unit": "g/cm³"}],
        )
        r2 = ExtractionResult(
            source="c1",
            properties=[{"name": "density", "value": 15.8, "unit": "g/cm³"}],
        )
        merger = Merger()
        merged = merger.merge([r1, r2])
        # Duplicate properties should be deduped
        assert len(merged.properties) >= 1

    def test_merge_different_properties(self):
        r1 = ExtractionResult(
            source="c0",
            properties=[{"name": "density", "value": 15.8}],
        )
        r2 = ExtractionResult(
            source="c1",
            properties=[{"name": "melting_point", "value": 1132}],
        )
        merger = Merger()
        merged = merger.merge([r1, r2])
        assert len(merged.properties) == 2


class TestMergedResult:
    """Test MergedResult output."""

    def test_to_dict(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "A"}])
        merger = Merger()
        merged = merger.merge([r1])
        d = merged.to_dict()
        assert "individuals" in d
        assert "stats" in d
        assert "sources" in d
        assert "c0" in d["sources"]
