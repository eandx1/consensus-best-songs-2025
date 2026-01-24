"""Validate data.json structure and consistency.

These tests ensure the production data.json file is well-formed and internally
consistent. This validation was moved from runtime JavaScript to Python tests
that run once in CI before deployment, avoiding wasteful browser-side validation.
"""

import json
import re
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


class TestMediaStructure:
    """Tests for media object structure and format validation."""

    def test_youtube_ids_format(self, data):
        """YouTube IDs should be 11 characters (standard format)."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            youtube = song.get("media", {}).get("youtube", {})

            for key in ["video_id", "music_id"]:
                if key in youtube:
                    yt_id = youtube[key]
                    # YouTube IDs are typically 11 chars, alphanumeric + _ and -
                    if not isinstance(yt_id, str) or not re.match(r'^[\w-]{10,12}$', yt_id):
                        invalid.append(f"{song_id}: {key}='{yt_id}'")

        assert not invalid, (
            f"Invalid YouTube ID format:\n" + "\n".join(invalid[:10])
        )

    def test_spotify_ids_format(self, data):
        """Spotify IDs should be 22 character base62 strings."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            spotify = song.get("media", {}).get("spotify", {})

            if "id" in spotify:
                sp_id = spotify["id"]
                # Spotify IDs are 22 chars, base62 (alphanumeric)
                if not isinstance(sp_id, str) or not re.match(r'^[a-zA-Z0-9]{22}$', sp_id):
                    invalid.append(f"{song_id}: spotify.id='{sp_id}'")

        assert not invalid, (
            f"Invalid Spotify ID format:\n" + "\n".join(invalid[:10])
        )

    def test_apple_music_urls_valid(self, data):
        """Apple Music URLs should be properly formatted."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            apple = song.get("media", {}).get("apple", {})

            if "url" in apple:
                url = apple["url"]
                if not isinstance(url, str) or not url.startswith("https://"):
                    invalid.append(f"{song_id}: apple.url='{url}'")
                elif "music.apple.com" not in url and "geo.music.apple.com" not in url:
                    invalid.append(f"{song_id}: apple.url not Apple Music domain: '{url}'")

        assert not invalid, (
            f"Invalid Apple Music URLs:\n" + "\n".join(invalid[:10])
        )

    def test_bandcamp_urls_valid(self, data):
        """Bandcamp URLs should be properly formatted."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            bandcamp = song.get("media", {}).get("bandcamp", {})

            if "url" in bandcamp:
                url = bandcamp["url"]
                if not isinstance(url, str) or not url.startswith("https://"):
                    invalid.append(f"{song_id}: bandcamp.url='{url}'")
                elif "bandcamp.com" not in url:
                    invalid.append(f"{song_id}: bandcamp.url not Bandcamp domain: '{url}'")

        assert not invalid, (
            f"Invalid Bandcamp URLs:\n" + "\n".join(invalid[:10])
        )

    def test_other_urls_valid(self, data):
        """Other media URLs should be properly formatted HTTPS URLs."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            other = song.get("media", {}).get("other", {})

            if "url" in other:
                url = other["url"]
                if not isinstance(url, str) or not url.startswith("https://"):
                    invalid.append(f"{song_id}: other.url='{url}'")

        assert not invalid, (
            f"Invalid other URLs:\n" + "\n".join(invalid[:10])
        )

    def test_songs_have_at_least_one_media_link(self, data):
        """Every song should have at least one media link for playability."""
        missing_media = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            media = song.get("media", {})

            has_youtube = bool(media.get("youtube", {}).get("video_id") or
                              media.get("youtube", {}).get("music_id"))
            has_spotify = bool(media.get("spotify", {}).get("id"))
            has_apple = bool(media.get("apple", {}).get("url"))
            has_bandcamp = bool(media.get("bandcamp", {}).get("url"))
            has_other = bool(media.get("other", {}).get("url"))

            if not any([has_youtube, has_spotify, has_apple, has_bandcamp, has_other]):
                missing_media.append(song_id)

        assert not missing_media, (
            f"Songs with no media links:\n" + "\n".join(missing_media[:10])
        )


class TestSourceConfigValidation:
    """Tests for source configuration validity."""

    def test_source_type_valid(self, data):
        """Source type must be 'ranked' or 'unranked'."""
        invalid = []

        for name, config in data["config"]["sources"].items():
            source_type = config.get("type")
            if source_type not in ("ranked", "unranked"):
                invalid.append(f"{name}: type='{source_type}'")

        assert not invalid, (
            f"Invalid source types:\n" + "\n".join(invalid)
        )

    def test_source_urls_valid(self, data):
        """Source URLs should be properly formatted HTTP(S) URLs."""
        invalid = []

        for name, config in data["config"]["sources"].items():
            url = config.get("url", "")
            if not isinstance(url, str) or not (url.startswith("https://") or url.startswith("http://")):
                invalid.append(f"{name}: url='{url}'")

        assert not invalid, (
            f"Invalid source URLs:\n" + "\n".join(invalid)
        )

    def test_source_song_counts_reasonable(self, data):
        """Source song_count should be positive and reasonable."""
        invalid = []

        for name, config in data["config"]["sources"].items():
            count = config.get("song_count", 0)
            if not isinstance(count, int) or count < 1 or count > 500:
                invalid.append(f"{name}: song_count={count}")

        assert not invalid, (
            f"Invalid source song_count values:\n" + "\n".join(invalid)
        )

    def test_full_name_if_present_is_nonempty(self, data):
        """If full_name is present, it should be a non-empty string."""
        invalid = []

        for name, config in data["config"]["sources"].items():
            if "full_name" in config:
                full_name = config["full_name"]
                if not isinstance(full_name, str) or not full_name.strip():
                    invalid.append(f"{name}: full_name='{full_name}'")

        assert not invalid, (
            f"Invalid full_name values:\n" + "\n".join(invalid)
        )

    def test_ranked_sources_have_no_shadow_rank(self, data):
        """Sources with type 'ranked' should not have shadow_rank."""
        issues = []

        for name, config in data["config"]["sources"].items():
            if config.get("type") == "ranked" and "shadow_rank" in config:
                issues.append(f"{name}: ranked source has shadow_rank={config['shadow_rank']}")

        assert not issues, (
            f"Ranked sources with shadow_rank:\n" + "\n".join(issues)
        )


class TestClusterMetadataValidation:
    """Tests for cluster metadata structure."""

    def test_cluster_metadata_has_required_fields(self, data):
        """Each cluster metadata entry has emoji and descriptor."""
        issues = []
        cluster_metadata = data["config"].get("cluster_metadata", {})

        for cluster_name, metadata in cluster_metadata.items():
            if "emoji" not in metadata:
                issues.append(f"{cluster_name}: missing 'emoji'")
            if "descriptor" not in metadata:
                issues.append(f"{cluster_name}: missing 'descriptor'")

        assert not issues, (
            f"Cluster metadata missing fields:\n" + "\n".join(issues)
        )

    def test_cluster_descriptors_nonempty(self, data):
        """Cluster descriptors should be non-empty strings."""
        invalid = []
        cluster_metadata = data["config"].get("cluster_metadata", {})

        for cluster_name, metadata in cluster_metadata.items():
            descriptor = metadata.get("descriptor", "")
            if not isinstance(descriptor, str) or not descriptor.strip():
                invalid.append(f"{cluster_name}: descriptor='{descriptor}'")

        assert not invalid, (
            f"Empty cluster descriptors:\n" + "\n".join(invalid)
        )

    def test_no_orphan_cluster_metadata(self, data):
        """All cluster metadata entries should be used by at least one source."""
        sources_config = data["config"]["sources"]
        cluster_metadata = data["config"].get("cluster_metadata", {})

        used_clusters = {cfg["cluster"] for cfg in sources_config.values()}
        orphan_clusters = set(cluster_metadata.keys()) - used_clusters

        assert not orphan_clusters, (
            f"Cluster metadata not used by any source: {orphan_clusters}"
        )


class TestStringFieldValidation:
    """Tests for string field validity."""

    def test_song_names_nonempty(self, data):
        """Song names should be non-empty strings."""
        invalid = []

        for i, song in enumerate(data["songs"]):
            name = song.get("name", "")
            if not isinstance(name, str) or not name.strip():
                invalid.append(f"Song at index {i}: name='{name}'")

        assert not invalid, (
            f"Empty song names:\n" + "\n".join(invalid[:10])
        )

    def test_artist_names_nonempty(self, data):
        """Artist names should be non-empty strings."""
        invalid = []

        for song in data["songs"]:
            artist = song.get("artist", "")
            song_name = song.get("name", "unknown")
            if not isinstance(artist, str) or not artist.strip():
                invalid.append(f"'{song_name}': artist='{artist}'")

        assert not invalid, (
            f"Empty artist names:\n" + "\n".join(invalid[:10])
        )

    def test_quotes_if_present_are_nonempty(self, data):
        """If a source entry has a quote, it should be a non-empty string."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            for src in song.get("sources", []):
                if "quote" in src:
                    quote = src["quote"]
                    if not isinstance(quote, str) or not quote.strip():
                        invalid.append(f"{song_id} ({src['name']}): quote='{quote}'")

        assert not invalid, (
            f"Empty quotes:\n" + "\n".join(invalid[:10])
        )

    def test_song_ids_nonempty(self, data):
        """Song IDs should be non-empty strings."""
        invalid = []

        for i, song in enumerate(data["songs"]):
            song_id = song.get("id", "")
            if not isinstance(song_id, str) or not song_id.strip():
                invalid.append(f"Song at index {i}: id='{song_id}'")

        assert not invalid, (
            f"Empty song IDs:\n" + "\n".join(invalid[:10])
        )

    def test_genres_if_present_are_nonempty(self, data):
        """If genres field is present, it should be a non-empty string."""
        invalid = []

        for song in data["songs"]:
            song_id = f"{song['artist']} - {song['name']}"
            if "genres" in song:
                genres = song["genres"]
                if not isinstance(genres, str) or not genres.strip():
                    invalid.append(f"{song_id}: genres='{genres}'")

        assert not invalid, (
            f"Empty genres:\n" + "\n".join(invalid[:10])
        )


class TestRankingParameterBounds:
    """Tests for ranking parameter value bounds."""

    def test_k_value_in_range(self, data):
        """k_value should be within CONFIG_BOUNDS (0-50)."""
        k_value = data["config"]["ranking"].get("k_value")
        assert isinstance(k_value, (int, float)), f"k_value is not a number: {k_value}"
        assert 0 <= k_value <= 50, f"k_value out of range (0-50): {k_value}"

    def test_p_exponent_in_range(self, data):
        """p_exponent should be within CONFIG_BOUNDS (0.0-1.1)."""
        p_exponent = data["config"]["ranking"].get("p_exponent")
        assert isinstance(p_exponent, (int, float)), f"p_exponent is not a number: {p_exponent}"
        assert 0.0 <= p_exponent <= 1.1, f"p_exponent out of range (0.0-1.1): {p_exponent}"

    def test_consensus_boost_in_range(self, data):
        """consensus_boost should be within CONFIG_BOUNDS (0.0-0.20)."""
        boost = data["config"]["ranking"].get("consensus_boost")
        assert isinstance(boost, (int, float)), f"consensus_boost is not a number: {boost}"
        assert 0.0 <= boost <= 0.20, f"consensus_boost out of range (0.0-0.20): {boost}"

    def test_provocation_boost_in_range(self, data):
        """provocation_boost should be within CONFIG_BOUNDS (0.0-0.20)."""
        boost = data["config"]["ranking"].get("provocation_boost")
        assert isinstance(boost, (int, float)), f"provocation_boost is not a number: {boost}"
        assert 0.0 <= boost <= 0.20, f"provocation_boost out of range (0.0-0.20): {boost}"

    def test_cluster_boost_in_range(self, data):
        """cluster_boost should be within CONFIG_BOUNDS (0.0-0.20)."""
        boost = data["config"]["ranking"].get("cluster_boost")
        assert isinstance(boost, (int, float)), f"cluster_boost is not a number: {boost}"
        assert 0.0 <= boost <= 0.20, f"cluster_boost out of range (0.0-0.20): {boost}"

    def test_cluster_threshold_in_range(self, data):
        """cluster_threshold should be within CONFIG_BOUNDS (0-100)."""
        threshold = data["config"]["ranking"].get("cluster_threshold")
        assert isinstance(threshold, (int, float)), f"cluster_threshold is not a number: {threshold}"
        assert 0 <= threshold <= 100, f"cluster_threshold out of range (0-100): {threshold}"

    def test_rank_bonuses_in_range(self, data):
        """Rank bonuses (rank1/2/3_bonus) should be multipliers (1.0-1.2)."""
        ranking = data["config"]["ranking"]
        issues = []

        for key in ["rank1_bonus", "rank2_bonus", "rank3_bonus"]:
            bonus = ranking.get(key)
            if not isinstance(bonus, (int, float)):
                issues.append(f"{key} is not a number: {bonus}")
            elif not (1.0 <= bonus <= 1.2):
                issues.append(f"{key} out of range (1.0-1.2): {bonus}")

        assert not issues, "\n".join(issues)

    def test_rank_bonuses_descending_order(self, data):
        """Rank bonuses should be in descending order: rank1 >= rank2 >= rank3."""
        ranking = data["config"]["ranking"]
        r1 = ranking.get("rank1_bonus", 1.0)
        r2 = ranking.get("rank2_bonus", 1.0)
        r3 = ranking.get("rank3_bonus", 1.0)

        assert r1 >= r2 >= r3, (
            f"Rank bonuses not in descending order: rank1={r1}, rank2={r2}, rank3={r3}"
        )
