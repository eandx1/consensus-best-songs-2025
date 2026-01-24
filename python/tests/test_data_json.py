"""Validate data.json structure and consistency.

These tests ensure the production data.json file is well-formed and internally
consistent. This validation was moved from runtime JavaScript to Python tests
that run once in CI before deployment, avoiding wasteful browser-side validation.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def data():
    """Load production data.json."""
    data_path = Path(__file__).parent.parent.parent / "data.json"
    with open(data_path) as f:
        return json.load(f)


class TestSourceConsistency:
    """Tests for source name consistency between songs and config."""

    def test_song_sources_exist_in_config(self, data):
        """Every source referenced by songs exists in config.sources."""
        valid_sources = set(data["config"]["sources"].keys())
        invalid_sources = {}

        for song in data["songs"]:
            for src in song["sources"]:
                if src["name"] not in valid_sources:
                    if src["name"] not in invalid_sources:
                        invalid_sources[src["name"]] = []
                    invalid_sources[src["name"]].append(
                        f"{song['artist']} - {song['name']}"
                    )

        assert not invalid_sources, (
            f"Songs reference unknown sources: {invalid_sources}"
        )

    def test_all_config_sources_have_songs(self, data):
        """Every configured source is used by at least one song."""
        configured_sources = set(data["config"]["sources"].keys())
        used_sources = set()

        for song in data["songs"]:
            for src in song["sources"]:
                used_sources.add(src["name"])

        unused_sources = configured_sources - used_sources
        assert not unused_sources, (
            f"Config sources not used by any song: {unused_sources}"
        )

    def test_unranked_sources_have_shadow_rank(self, data):
        """Sources with type 'unranked' have shadow_rank defined."""
        sources_config = data["config"]["sources"]
        missing_shadow_rank = []

        for name, config in sources_config.items():
            if config.get("type") == "unranked":
                if "shadow_rank" not in config:
                    missing_shadow_rank.append(name)

        assert not missing_shadow_rank, (
            f"Unranked sources missing shadow_rank: {missing_shadow_rank}"
        )

    def test_shadow_rank_usage_matches_source_type(self, data):
        """Songs with uses_shadow_rank reference unranked sources."""
        sources_config = data["config"]["sources"]
        mismatches = []

        for song in data["songs"]:
            for src in song["sources"]:
                source_name = src["name"]
                uses_shadow = src.get("uses_shadow_rank", False)

                if source_name not in sources_config:
                    continue  # Other test catches this

                source_type = sources_config[source_name].get("type", "ranked")

                if uses_shadow and source_type != "unranked":
                    mismatches.append(
                        f"{song['artist']} - {song['name']}: "
                        f"uses_shadow_rank=True but {source_name} is type '{source_type}'"
                    )
                elif not uses_shadow and source_type == "unranked" and "rank" in src:
                    mismatches.append(
                        f"{song['artist']} - {song['name']}: "
                        f"has rank for unranked source {source_name}"
                    )

        assert not mismatches, (
            f"Shadow rank usage mismatches:\n" + "\n".join(mismatches[:10])
        )


class TestSongStructure:
    """Tests for required song fields and structure."""

    def test_required_song_fields(self, data):
        """Every song has required fields: id, artist, name, sources, list_count."""
        required_fields = ["id", "artist", "name", "sources", "list_count"]
        missing = []

        for i, song in enumerate(data["songs"]):
            song_id = song.get("id", f"index-{i}")
            for field in required_fields:
                if field not in song:
                    missing.append(f"Song '{song_id}' missing field '{field}'")

        assert not missing, (
            f"Songs missing required fields:\n" + "\n".join(missing[:10])
        )

    def test_source_entries_have_rank_or_shadow(self, data):
        """Each source entry has rank or uses_shadow_rank."""
        issues = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            for src in song.get("sources", []):
                has_rank = "rank" in src
                has_shadow = src.get("uses_shadow_rank", False)

                if not has_rank and not has_shadow:
                    issues.append(
                        f"{song_id}: source '{src['name']}' has neither rank nor uses_shadow_rank"
                    )

        assert not issues, (
            f"Source entries missing rank info:\n" + "\n".join(issues[:10])
        )

    def test_list_count_matches_sources(self, data):
        """list_count equals len(sources) for each song."""
        mismatches = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            actual_count = len(song.get("sources", []))
            stated_count = song.get("list_count", 0)

            if actual_count != stated_count:
                mismatches.append(
                    f"{song_id}: list_count={stated_count} but has {actual_count} sources"
                )

        assert not mismatches, (
            f"list_count mismatches:\n" + "\n".join(mismatches[:10])
        )

    def test_sources_have_name_field(self, data):
        """Every source entry has a name field."""
        missing = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            for i, src in enumerate(song.get("sources", [])):
                if "name" not in src:
                    missing.append(f"{song_id}: source at index {i} missing 'name'")

        assert not missing, (
            f"Source entries missing name:\n" + "\n".join(missing[:10])
        )


class TestRankingConfig:
    """Tests for ranking configuration completeness."""

    def test_required_config_fields(self, data):
        """Ranking config has all required fields."""
        required_fields = [
            "k_value",
            "p_exponent",
            "cluster_threshold",
            "consensus_boost",
            "provocation_boost",
            "cluster_boost",
            "rank1_bonus",
            "rank2_bonus",
            "rank3_bonus",
            "decay_mode",
        ]

        ranking_config = data.get("config", {}).get("ranking", {})
        missing = [f for f in required_fields if f not in ranking_config]

        assert not missing, f"Ranking config missing fields: {missing}"

    def test_decay_mode_valid(self, data):
        """decay_mode is either 'consensus' or 'conviction'."""
        decay_mode = data["config"]["ranking"].get("decay_mode")
        assert decay_mode in ("consensus", "conviction"), (
            f"Invalid decay_mode: {decay_mode}"
        )

    def test_source_config_required_fields(self, data):
        """Each source config has required fields."""
        required_fields = ["url", "weight", "cluster", "type", "song_count"]
        issues = []

        for name, config in data["config"]["sources"].items():
            for field in required_fields:
                if field not in config:
                    issues.append(f"Source '{name}' missing field '{field}'")

        assert not issues, (
            f"Source configs missing fields:\n" + "\n".join(issues[:10])
        )

    def test_source_weights_in_range(self, data):
        """Source weights are within valid range (0.0 to 1.5)."""
        out_of_range = []

        for name, config in data["config"]["sources"].items():
            weight = config.get("weight", 1.0)
            if not (0.0 <= weight <= 1.5):
                out_of_range.append(f"{name}: weight={weight}")

        assert not out_of_range, (
            f"Source weights out of range (0.0-1.5):\n" + "\n".join(out_of_range)
        )

    def test_shadow_ranks_positive(self, data):
        """Shadow ranks are positive numbers."""
        invalid = []

        for name, config in data["config"]["sources"].items():
            if "shadow_rank" in config:
                sr = config["shadow_rank"]
                if not isinstance(sr, (int, float)) or sr <= 0:
                    invalid.append(f"{name}: shadow_rank={sr}")

        assert not invalid, (
            f"Invalid shadow_rank values:\n" + "\n".join(invalid)
        )


class TestDataIntegrity:
    """Tests for overall data integrity."""

    def test_songs_array_not_empty(self, data):
        """Songs array contains at least one song."""
        assert len(data.get("songs", [])) > 0, "No songs in data.json"

    def test_no_duplicate_song_ids(self, data):
        """All song IDs are unique."""
        ids = [song["id"] for song in data["songs"]]
        duplicates = [id for id in set(ids) if ids.count(id) > 1]

        assert not duplicates, f"Duplicate song IDs: {duplicates}"

    def test_ranks_are_positive_numbers(self, data):
        """All explicit ranks are positive numbers."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            for src in song.get("sources", []):
                if "rank" in src:
                    rank = src["rank"]
                    if not isinstance(rank, (int, float)) or rank < 1:
                        invalid.append(
                            f"{song_id}: {src['name']} rank={rank}"
                        )

        assert not invalid, (
            f"Invalid rank values:\n" + "\n".join(invalid[:10])
        )

    def test_cluster_metadata_exists(self, data):
        """Clusters referenced by sources have metadata defined."""
        sources_config = data["config"]["sources"]
        cluster_metadata = data["config"].get("cluster_metadata", {})

        used_clusters = {cfg["cluster"] for cfg in sources_config.values()}
        missing_metadata = used_clusters - set(cluster_metadata.keys())

        assert not missing_metadata, (
            f"Clusters missing metadata: {missing_metadata}"
        )
