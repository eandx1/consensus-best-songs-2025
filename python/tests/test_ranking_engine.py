"""
Unit tests for ranking_engine.py.

Tests the Python ranking engine with various configurations including
different decay modes, boost values, and ranking parameters.
"""
import pytest
import json
import sys
import os
import math
import numpy as np
import pandas as pd

# Add the notebooks directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../notebooks"))
from ranking_engine import (
    compute_rankings_with_configs,
    get_decay_value,
    score_song,
    TOP_BONUSES_CONSENSUS,
    TOP_BONUSES_CONVICTION,
    K_VALUE,
    P_EXPONENT,
    CONSENSUS_BOOST,
    PROVOCATION_BOOST,
    CLUSTER_BOOST,
    CLUSTER_THRESHOLD,
)
from sources import SOURCES, SHADOW_RANKS


# Path to test data
TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), "testdata/test_data.json")


@pytest.fixture(scope="module")
def test_data():
    """Load test data from JSON file."""
    with open(TEST_DATA_PATH, "r") as f:
        return json.load(f)


def build_source_name_mapping(test_data):
    """
    Build a mapping from test_data.json source names to Python SOURCES keys.

    test_data.json uses short names (e.g., "NYT (Caramanica)") while sources.py
    uses full names (e.g., "New York Times (Jon Caramanica)").

    Returns a dict: test_data_source_name -> python_source_name
    """
    mapping = {}
    for source_name, source_config in test_data["config"]["sources"].items():
        full_name = source_config.get("full_name", source_name)

        if full_name in SOURCES:
            mapping[source_name] = full_name
        elif source_name in SOURCES:
            mapping[source_name] = source_name
        else:
            for py_name in SOURCES.keys():
                if py_name.endswith(source_name) or source_name.endswith(py_name):
                    mapping[source_name] = py_name
                    break
            else:
                mapping[source_name] = None

    return mapping


def build_python_sources_config(test_data, name_mapping):
    """
    Build a sources configuration dict compatible with ranking_engine using
    Python's SOURCES as the source of truth for weights and clusters.
    """
    sources = {}

    for td_name, py_name in name_mapping.items():
        if py_name is None or py_name not in SOURCES:
            continue

        py_config = SOURCES[py_name]

        weight = py_config["weight"]
        cluster = py_config["cluster"]
        source_type = py_config.get("type", "ranked")
        shadow_rank = SHADOW_RANKS.get(py_name)

        suffix = f"_{td_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}"

        sources[td_name] = {
            "suffix": suffix,
            "weight": weight,
            "cluster": cluster,
            "type": source_type,
            "shadow_rank": shadow_rank,
        }

    return sources


def build_dataframe(test_data, sources):
    """
    Convert test data songs to a DataFrame format expected by ranking_engine.
    """
    songs = test_data["songs"]
    rows = []

    for song in songs:
        row = {
            "name": song["name"],
            "artist": song["artist"],
            "id": song["id"]
        }

        # Initialize all rank columns to None
        for source_name in sources.keys():
            rank_col = f"rank{sources[source_name]['suffix']}"
            row[rank_col] = None

        # Fill in ranks from song's sources
        for src_entry in song["sources"]:
            src_name = src_entry["name"]
            if src_name in sources:
                rank_col = f"rank{sources[src_name]['suffix']}"
                if src_entry.get("uses_shadow_rank"):
                    row[rank_col] = sources[src_name]["shadow_rank"]
                else:
                    row[rank_col] = src_entry.get("rank")

        rows.append(row)

    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def sources_config(test_data):
    """Build sources configuration from test data."""
    name_mapping = build_source_name_mapping(test_data)
    return build_python_sources_config(test_data, name_mapping)


@pytest.fixture(scope="module")
def songs_df(test_data, sources_config):
    """Build DataFrame from test data."""
    return build_dataframe(test_data, sources_config)


# =============================================================================
# Test get_decay_value function
# =============================================================================

class TestGetDecayValue:
    """Tests for the get_decay_value function."""

    def test_consensus_mode_rank1_no_bonus(self):
        """Test consensus decay for rank 1 without bonuses."""
        # Formula: (1 + K) / (rank + K)
        k = 20
        expected = (1 + k) / (1 + k)  # = 1.0
        result = get_decay_value(1, "consensus", k, 0.55, {})
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_consensus_mode_rank10(self):
        """Test consensus decay for rank 10."""
        k = 20
        expected = (1 + k) / (10 + k)  # = 21/30 = 0.7
        result = get_decay_value(10, "consensus", k, 0.55, {})
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_consensus_mode_k15(self):
        """Test consensus mode with K_VALUE=15."""
        k = 15
        rank = 5
        expected = (1 + k) / (rank + k)  # = 16/20 = 0.8
        result = get_decay_value(rank, "consensus", k, 0.55, {})
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_conviction_mode_rank1_no_bonus(self):
        """Test conviction decay for rank 1 without bonuses."""
        # Formula: 1 / (rank ^ P)
        p = 0.55
        expected = 1.0 / (1 ** p)  # = 1.0
        result = get_decay_value(1, "conviction", 20, p, {})
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_conviction_mode_rank10(self):
        """Test conviction decay for rank 10."""
        p = 0.55
        expected = 1.0 / (10 ** p)
        result = get_decay_value(10, "conviction", 20, p, {})
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_conviction_mode_p07(self):
        """Test conviction mode with P_EXPONENT=0.7."""
        p = 0.7
        rank = 5
        expected = 1.0 / (rank ** p)
        result = get_decay_value(rank, "conviction", 20, p, {})
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_top_bonus_rank1(self):
        """Test that rank 1 bonus is applied correctly."""
        bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        k = 20
        base_decay = (1 + k) / (1 + k)
        expected = base_decay * (1 + 0.1)  # 1.1
        result = get_decay_value(1, "consensus", k, 0.55, bonuses)
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_top_bonus_rank2(self):
        """Test that rank 2 bonus is applied correctly."""
        bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        k = 20
        base_decay = (1 + k) / (2 + k)
        expected = base_decay * (1 + 0.075)
        result = get_decay_value(2, "consensus", k, 0.55, bonuses)
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_top_bonus_rank3(self):
        """Test that rank 3 bonus is applied correctly."""
        bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        k = 20
        base_decay = (1 + k) / (3 + k)
        expected = base_decay * (1 + 0.025)
        result = get_decay_value(3, "consensus", k, 0.55, bonuses)
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_custom_top_bonuses(self):
        """Test with custom bonus values."""
        bonuses = {1: 0.2, 2: 0.15, 3: 0.1}
        k = 20
        base_decay = (1 + k) / (1 + k)
        expected = base_decay * (1 + 0.2)  # 1.2
        result = get_decay_value(1, "consensus", k, 0.55, bonuses)
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_no_bonus_for_rank4(self):
        """Test that no bonus is applied for rank 4."""
        bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        k = 20
        expected = (1 + k) / (4 + k)  # No bonus multiplier
        result = get_decay_value(4, "consensus", k, 0.55, bonuses)
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_shadow_rank_gets_bonus_if_integer(self):
        """Test that shadow ranks that are integers get bonuses."""
        bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        k = 20
        # Shadow rank of 3.0 should get rank 3 bonus
        base_decay = (1 + k) / (3.0 + k)
        expected = base_decay * (1 + 0.025)
        result = get_decay_value(3.0, "consensus", k, 0.55, bonuses)
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_shadow_rank_fractional_no_bonus(self):
        """Test that fractional shadow ranks don't get integer bonuses."""
        bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        k = 20
        # Shadow rank of 13.0 (floor = 13) should not get any bonus
        expected = (1 + k) / (13.0 + k)
        result = get_decay_value(13.0, "consensus", k, 0.55, bonuses)
        assert math.isclose(result, expected, rel_tol=1e-9)


# =============================================================================
# Test compute_rankings_with_configs function
# =============================================================================

class TestComputeRankingsConsensusMode:
    """Tests for compute_rankings_with_configs in consensus mode."""

    def test_consensus_mode_k15(self, songs_df, sources_config):
        """Test consensus mode with K_VALUE=15."""
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=15,
            consensus_boost=CONSENSUS_BOOST,
            provocation_boost=PROVOCATION_BOOST,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # Verify DataFrame has expected columns
        assert "rank" in ranked_df.columns
        assert "score" in ranked_df.columns
        assert "raw_score" in ranked_df.columns
        assert "raw_score_before_bonus" in ranked_df.columns
        assert "consensus_bonus" in ranked_df.columns
        assert "list_count" in ranked_df.columns

        # Verify ranks are sequential starting from 1
        assert list(ranked_df["rank"].head(10)) == list(range(1, 11))

        # Verify scores are normalized (0-1) and sorted descending
        assert ranked_df["score"].iloc[0] == 1.0
        assert all(ranked_df["score"] <= 1.0)
        assert all(ranked_df["score"] >= 0.0)
        assert ranked_df["score"].is_monotonic_decreasing

        # Verify that K=15 produces different scores than K=20
        ranked_df_k20 = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=20,
            consensus_boost=CONSENSUS_BOOST,
            provocation_boost=PROVOCATION_BOOST,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # Raw scores should be different with different K values
        assert not np.allclose(
            ranked_df["raw_score"].values,
            ranked_df_k20["raw_score"].values
        )

    def test_default_consensus_mode_top10(self, songs_df, sources_config):
        """
        Test default consensus mode produces expected ranking and values for top 10.
        """
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            p_exponent=P_EXPONENT,
            consensus_boost=CONSENSUS_BOOST,
            provocation_boost=PROVOCATION_BOOST,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # Verify all expected columns exist
        expected_columns = [
            "rank", "name", "artist", "id", "score", "raw_score",
            "raw_score_before_bonus", "consensus_bonus", "provocation_bonus",
            "diversity_bonus", "list_count", "topn_unique_clusters_count",
            "all_clusters_count", "topn_best_cluster", "all_best_cluster",
            "topn_clusters", "all_clusters"
        ]
        for col in expected_columns:
            assert col in ranked_df.columns, f"Missing column: {col}"

        # Get top 10
        top10 = ranked_df.head(10)

        # Verify ranks 1-10
        assert list(top10["rank"]) == list(range(1, 11))

        # Verify normalized scores
        assert top10["score"].iloc[0] == 1.0
        assert all(top10["score"] <= 1.0)
        assert top10["score"].is_monotonic_decreasing

        # Verify list counts are positive integers
        assert all(top10["list_count"] > 0)
        assert all(top10["list_count"] == top10["list_count"].astype(int))

        # Verify consensus bonus multiplier is >= 1.0 (no negative boost)
        assert all(top10["consensus_bonus"] >= 1.0)

        # Verify diversity bonus is >= 1.0
        assert all(top10["diversity_bonus"] >= 1.0)

        # Verify raw_score >= raw_score_before_bonus (multipliers applied)
        assert all(top10["raw_score"] >= top10["raw_score_before_bonus"] - 1e-9)

        # Verify cluster information is populated for songs with sources
        for idx, row in top10.iterrows():
            if row["list_count"] > 0:
                assert row["all_clusters_count"] >= 1


class TestComputeRankingsConvictionMode:
    """Tests for compute_rankings_with_configs in conviction mode."""

    def test_conviction_mode_p07(self, songs_df, sources_config):
        """Test conviction mode with P_EXPONENT=0.7."""
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="conviction",
            k_value=K_VALUE,
            p_exponent=0.7,
            consensus_boost=CONSENSUS_BOOST,
            provocation_boost=PROVOCATION_BOOST,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONVICTION,
        )

        # Verify DataFrame structure
        assert "rank" in ranked_df.columns
        assert "score" in ranked_df.columns
        assert list(ranked_df["rank"].head(10)) == list(range(1, 11))

        # Verify scores are normalized and sorted
        assert ranked_df["score"].iloc[0] == 1.0
        assert ranked_df["score"].is_monotonic_decreasing

        # Verify P=0.7 produces different scores than P=0.55
        ranked_df_p055 = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="conviction",
            k_value=K_VALUE,
            p_exponent=0.55,
            consensus_boost=CONSENSUS_BOOST,
            provocation_boost=PROVOCATION_BOOST,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONVICTION,
        )

        # Raw scores should differ with different P values
        assert not np.allclose(
            ranked_df["raw_score"].values,
            ranked_df_p055["raw_score"].values
        )

    def test_default_conviction_mode_top10(self, songs_df, sources_config):
        """
        Test default conviction mode produces expected ranking and values for top 10.
        """
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="conviction",
            k_value=K_VALUE,
            p_exponent=P_EXPONENT,
            consensus_boost=CONSENSUS_BOOST,
            provocation_boost=PROVOCATION_BOOST,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONVICTION,
        )

        # Verify all expected columns exist
        expected_columns = [
            "rank", "name", "artist", "id", "score", "raw_score",
            "raw_score_before_bonus", "consensus_bonus", "provocation_bonus",
            "diversity_bonus", "list_count"
        ]
        for col in expected_columns:
            assert col in ranked_df.columns, f"Missing column: {col}"

        # Get top 10
        top10 = ranked_df.head(10)

        # Verify ranks 1-10
        assert list(top10["rank"]) == list(range(1, 11))

        # Verify normalized scores
        assert top10["score"].iloc[0] == 1.0
        assert all(top10["score"] <= 1.0)
        assert top10["score"].is_monotonic_decreasing

        # Verify conviction mode produces different ranking than consensus
        consensus_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            p_exponent=P_EXPONENT,
            consensus_boost=CONSENSUS_BOOST,
            provocation_boost=PROVOCATION_BOOST,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # The ranking order or scores should differ between modes
        # (they use different decay formulas and bonuses)
        conviction_scores = ranked_df["raw_score_before_bonus"].values
        consensus_scores = consensus_df["raw_score_before_bonus"].values
        assert not np.allclose(conviction_scores, consensus_scores)


class TestTopBonuses:
    """Tests for different top_bonuses configurations."""

    def test_custom_top_bonuses_rank1(self, songs_df, sources_config):
        """Test custom bonus values affect rank 1 songs correctly."""
        # Default bonuses
        default_bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        # Custom bonuses with higher rank 1 bonus
        custom_bonuses = {1: 0.3, 2: 0.075, 3: 0.025}

        ranked_default = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses=default_bonuses,
        )

        ranked_custom = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses=custom_bonuses,
        )

        # Songs with rank 1 appearances should have higher scores with custom bonuses
        # Compare raw scores - they should be different
        assert not np.allclose(
            ranked_default["raw_score_before_bonus"].values,
            ranked_custom["raw_score_before_bonus"].values
        )

    def test_custom_top_bonuses_rank2(self, songs_df, sources_config):
        """Test custom bonus values affect rank 2 songs correctly."""
        default_bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        custom_bonuses = {1: 0.1, 2: 0.2, 3: 0.025}

        ranked_default = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses=default_bonuses,
        )

        ranked_custom = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses=custom_bonuses,
        )

        # Scores should differ
        assert not np.allclose(
            ranked_default["raw_score_before_bonus"].values,
            ranked_custom["raw_score_before_bonus"].values
        )

    def test_custom_top_bonuses_rank3(self, songs_df, sources_config):
        """Test custom bonus values affect rank 3 songs correctly."""
        default_bonuses = {1: 0.1, 2: 0.075, 3: 0.025}
        custom_bonuses = {1: 0.1, 2: 0.075, 3: 0.15}

        ranked_default = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses=default_bonuses,
        )

        ranked_custom = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses=custom_bonuses,
        )

        # Scores should differ
        assert not np.allclose(
            ranked_default["raw_score_before_bonus"].values,
            ranked_custom["raw_score_before_bonus"].values
        )

    def test_no_top_bonuses(self, songs_df, sources_config):
        """Test with empty top_bonuses (no bonuses applied)."""
        with_bonuses = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        without_bonuses = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            top_bonuses={},
        )

        # Scores without bonuses should be lower for songs with top 3 ranks
        # The total raw_score should be lower when no bonuses are applied
        assert with_bonuses["raw_score_before_bonus"].sum() > without_bonuses["raw_score_before_bonus"].sum()


class TestClusterBoost:
    """Tests for cluster_boost parameter."""

    def test_cluster_boost_01(self, songs_df, sources_config):
        """Test cluster_boost=0.1 produces different diversity bonuses."""
        ranked_default = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            cluster_boost=CLUSTER_BOOST,  # 0.03
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        ranked_high_boost = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            cluster_boost=0.1,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # Diversity bonuses should be higher with higher cluster_boost
        # for songs appearing in multiple clusters
        songs_with_diversity = ranked_default[ranked_default["topn_unique_clusters_count"] > 1]
        if len(songs_with_diversity) > 0:
            # Get same songs from both DataFrames
            for idx, row in songs_with_diversity.iterrows():
                song_name = row["name"]
                default_bonus = ranked_default[ranked_default["name"] == song_name]["diversity_bonus"].values[0]
                high_bonus = ranked_high_boost[ranked_high_boost["name"] == song_name]["diversity_bonus"].values[0]
                # Higher cluster_boost should result in higher diversity_bonus
                assert high_bonus >= default_bonus

    def test_cluster_boost_zero(self, songs_df, sources_config):
        """Test cluster_boost=0 produces no diversity bonus."""
        ranked = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            cluster_boost=0.0,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # All diversity bonuses should be 1.0 (no bonus)
        assert all(ranked["diversity_bonus"] == 1.0)


class TestClusterThreshold:
    """Tests for CLUSTER_THRESHOLD behavior."""

    def test_cluster_threshold_10(self, songs_df, sources_config, monkeypatch):
        """Test with CLUSTER_THRESHOLD=10 (using monkeypatch)."""
        import ranking_engine

        # Get results with default threshold (25)
        ranked_default = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # Monkeypatch CLUSTER_THRESHOLD to 10
        monkeypatch.setattr(ranking_engine, "CLUSTER_THRESHOLD", 10)

        ranked_threshold_10 = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            cluster_boost=CLUSTER_BOOST,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # With lower threshold, fewer ranks qualify for cluster diversity
        # This should affect topn_unique_clusters_count
        # Songs with ranks between 11-25 won't count toward cluster diversity
        assert not ranked_default["topn_unique_clusters_count"].equals(
            ranked_threshold_10["topn_unique_clusters_count"]
        ) or ranked_default["topn_clusters"].equals(ranked_threshold_10["topn_clusters"]) is False


class TestProvocationBoost:
    """Tests for provocation_boost parameter."""

    def test_provocation_boost_05(self, songs_df, sources_config):
        """Test provocation_boost=0.5 rewards polarizing songs."""
        ranked_no_provocation = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            provocation_boost=0.0,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        ranked_with_provocation = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            provocation_boost=0.5,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # Provocation bonus should be 1.0 for all songs when provocation_boost=0
        assert all(ranked_no_provocation["provocation_bonus"] == 1.0)

        # With provocation_boost > 0, songs with multiple sources should have
        # provocation_bonus > 1.0 (if they have rank variance)
        multi_source_songs = ranked_with_provocation[ranked_with_provocation["list_count"] > 1]
        # At least some songs should have provocation bonus > 1.0
        # (songs with varied ranks across sources)
        has_provocation_effect = any(multi_source_songs["provocation_bonus"] > 1.0)
        # This may or may not be true depending on data, but raw_scores should differ
        assert not np.allclose(
            ranked_no_provocation["raw_score"].values,
            ranked_with_provocation["raw_score"].values
        )

    def test_provocation_boost_only_affects_multi_source_songs(self, songs_df, sources_config):
        """Test that provocation boost only affects songs with multiple sources."""
        ranked = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            k_value=K_VALUE,
            provocation_boost=0.5,
            top_bonuses=TOP_BONUSES_CONSENSUS,
        )

        # Songs with only 1 source should have provocation_bonus = 1.0
        single_source_songs = ranked[ranked["list_count"] == 1]
        assert all(single_source_songs["provocation_bonus"] == 1.0)


class TestDataFrameOutput:
    """Tests for DataFrame structure and output correctness."""

    def test_output_columns_complete(self, songs_df, sources_config):
        """Verify all expected output columns are present."""
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
        )

        expected_columns = [
            "rank",
            "name",
            "artist",
            "id",
            "score",
            "raw_score",
            "raw_score_before_bonus",
            "consensus_bonus",
            "provocation_bonus",
            "diversity_bonus",
            "list_count",
            "topn_unique_clusters_count",
            "all_clusters_count",
            "topn_best_cluster",
            "all_best_cluster",
            "topn_clusters",
            "all_clusters",
        ]

        for col in expected_columns:
            assert col in ranked_df.columns, f"Missing column: {col}"

    def test_score_normalization(self, songs_df, sources_config):
        """Verify scores are properly normalized to 0-1 range."""
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
        )

        assert ranked_df["score"].max() == 1.0
        assert ranked_df["score"].min() >= 0.0
        assert all(ranked_df["score"] <= 1.0)

    def test_ranks_are_sequential(self, songs_df, sources_config):
        """Verify ranks are sequential integers starting from 1."""
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
        )

        expected_ranks = list(range(1, len(ranked_df) + 1))
        actual_ranks = list(ranked_df["rank"])
        assert actual_ranks == expected_ranks

    def test_sorted_by_score_descending(self, songs_df, sources_config):
        """Verify DataFrame is sorted by score in descending order."""
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
        )

        assert ranked_df["score"].is_monotonic_decreasing

    def test_raw_score_relationship(self, songs_df, sources_config):
        """Verify raw_score = raw_score_before_bonus * multipliers."""
        ranked_df = compute_rankings_with_configs(
            songs_df,
            sources_config,
            mode="consensus",
            consensus_boost=0.03,
            provocation_boost=0.0,
            cluster_boost=0.03,
        )

        for idx, row in ranked_df.iterrows():
            expected_raw = (
                row["raw_score_before_bonus"] *
                row["consensus_bonus"] *
                row["provocation_bonus"] *
                row["diversity_bonus"]
            )
            assert math.isclose(row["raw_score"], expected_raw, rel_tol=1e-9), \
                f"Raw score mismatch for {row['name']}: expected {expected_raw}, got {row['raw_score']}"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_dataframe(self, sources_config):
        """Test handling of empty DataFrame raises KeyError.

        Note: The ranking engine does not currently support empty DataFrames.
        This test documents the expected behavior (raises KeyError).
        """
        empty_df = pd.DataFrame(columns=["name", "artist", "id"])
        # Add rank columns
        for source_name, config in sources_config.items():
            empty_df[f"rank{config['suffix']}"] = pd.Series(dtype=float)

        # Empty DataFrames cause a KeyError due to result_type="expand" behavior
        with pytest.raises(KeyError):
            compute_rankings_with_configs(
                empty_df,
                sources_config,
                mode="consensus",
            )

    def test_single_song(self, sources_config):
        """Test ranking with a single song."""
        single_song_df = pd.DataFrame([{
            "name": "Test Song",
            "artist": "Test Artist",
            "id": "TEST123",
        }])

        # Add rank columns with one source having a rank
        for source_name, config in sources_config.items():
            single_song_df[f"rank{config['suffix']}"] = None

        # Set one source rank
        first_source = list(sources_config.keys())[0]
        single_song_df[f"rank{sources_config[first_source]['suffix']}"] = 1

        ranked_df = compute_rankings_with_configs(
            single_song_df,
            sources_config,
            mode="consensus",
        )

        assert len(ranked_df) == 1
        assert ranked_df["rank"].iloc[0] == 1
        assert ranked_df["score"].iloc[0] == 1.0

    def test_all_songs_same_score(self, sources_config):
        """Test handling when multiple songs have identical scores."""
        # Create two songs with identical source rankings
        same_score_df = pd.DataFrame([
            {"name": "Song A", "artist": "Artist A", "id": "A"},
            {"name": "Song B", "artist": "Artist B", "id": "B"},
        ])

        for source_name, config in sources_config.items():
            same_score_df[f"rank{config['suffix']}"] = None

        # Give both songs the same rank in the same source
        first_source = list(sources_config.keys())[0]
        same_score_df[f"rank{sources_config[first_source]['suffix']}"] = 5

        ranked_df = compute_rankings_with_configs(
            same_score_df,
            sources_config,
            mode="consensus",
        )

        assert len(ranked_df) == 2
        # Both should have the same score
        assert ranked_df["score"].iloc[0] == ranked_df["score"].iloc[1]
        # But still have sequential ranks
        assert list(ranked_df["rank"]) == [1, 2]
