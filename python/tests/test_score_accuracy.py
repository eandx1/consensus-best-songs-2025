"""
Test that JavaScript scoring matches Python scoring.

This test verifies that the JavaScript RankingEngine produces identical scores,
boosts, and source contributions as the Python ranking_engine.py for songs at
ranks 1, 10, and 20.
"""
import pytest
import json
import sys
import os
from playwright.sync_api import Page, expect

# Add the notebooks directory to the path to import ranking_engine
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../notebooks"))
from ranking_engine import compute_rankings_with_configs, TOP_BONUSES_CONSENSUS

@pytest.fixture(scope="module")
def expected_scores(test_data):
    """
    Pre-compute expected scores using the Python ranking engine.
    
    Returns a dict mapping song names to their expected scoring details.
    """
    import pandas as pd
    
    # Convert test data songs to a DataFrame format expected by ranking_engine
    songs = test_data["songs"]
    sources_config = test_data["config"]["sources"]
    
    # Build the sources dict with proper structure
    sources = {}
    for source_name, source_cfg in sources_config.items():
        sources[source_name] = {
            "suffix": f"_{source_name.lower().replace(' ', '_')}",
            "weight": source_cfg["weight"],
            "cluster": source_cfg["cluster"],
            "type": source_cfg.get("type", "ranked"),
            "shadow_rank": source_cfg.get("shadow_rank")
        }
    
    # Create DataFrame with one row per song
    rows = []
    for song in songs:
        row = {
            "name": song["name"],
            "artist": song["artist"],
            "id": song["id"]
        }
        
        # Add rank columns for each source
        for source_name in sources.keys():
            rank_col = f"rank{sources[source_name]['suffix']}"
            row[rank_col] = None
        
        # Fill in the ranks from the song's sources
        for src_entry in song["sources"]:
            src_name = src_entry["name"]
            if src_name in sources:
                rank_col = f"rank{sources[src_name]['suffix']}"
                if src_entry.get("uses_shadow_rank"):
                    row[rank_col] = sources[src_name]["shadow_rank"]
                else:
                    row[rank_col] = src_entry["rank"]
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Compute rankings using Python engine
    config = test_data["config"]["ranking"]
    ranked_df = compute_rankings_with_configs(
        df,
        sources,
        mode=config["decay_mode"],
        consensus_boost=config["consensus_boost"],
        provocation_boost=config["provocation_boost"],
        cluster_boost=config["cluster_boost"],
        k_value=config["k_value"],
        p_exponent=config["p_exponent"],
        top_bonuses=TOP_BONUSES_CONSENSUS if config["decay_mode"] == "consensus" else {}
    )
    
    # Extract expected scores for ranks 1, 10, and 20
    expected = {}
    for target_rank in [1, 10, 20]:
        if target_rank <= len(ranked_df):
            row = ranked_df.iloc[target_rank - 1]
            song_name = row["name"]
            
            # Calculate individual source contributions
            source_contributions = []
            for src_name, src_config in sources.items():
                rank_col = f"rank{src_config['suffix']}"
                if pd.notna(row[rank_col]):
                    rank = float(row[rank_col])
                    
                    # Calculate decay value
                    if config["decay_mode"] == "consensus":
                        decay_val = (1 + config["k_value"]) / (rank + config["k_value"])
                    else:
                        decay_val = 1.0 / (rank ** config["p_exponent"])
                    
                    # Apply rank bonuses
                    int_rank = int(rank)
                    if int_rank == 1:
                        decay_val *= config["rank1_bonus"]
                    elif int_rank == 2:
                        decay_val *= config["rank2_bonus"]
                    elif int_rank == 3:
                        decay_val *= config["rank3_bonus"]
                    
                    contribution = decay_val * src_config["weight"]
                    source_contributions.append({
                        "name": src_name,
                        "rank": rank,
                        "contribution": contribution
                    })
            
            # Sort by contribution (highest first)
            source_contributions.sort(key=lambda x: x["contribution"], reverse=True)
            
            expected[song_name] = {
                "rank": int(row["rank"]),
                "artist": row["artist"],
                "normalizedScore": float(row["score"]),
                "finalScore": float(row["raw_score"]),
                "baseScore": float(row["raw_score_before_bonus"]),
                "listCount": int(row["list_count"]),
                "consensusBoost": float(row["consensus_bonus"]),
                "provocationBoost": float(row["provocation_bonus"]),
                "clusterBoost": float(row["diversity_bonus"]),
                "sourceContributions": source_contributions
            }
    
    return expected


def test_rank1_scoring_accuracy(page: Page, server_url, expected_scores):
    """Verify scoring accuracy for the #1 ranked song."""
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    
    # Get expected values for rank 1
    rank1_song = None
    for song_name, data in expected_scores.items():
        if data["rank"] == 1:
            rank1_song = song_name
            expected = data
            break
    
    assert rank1_song is not None, "No rank 1 song found in expected scores"
    
    # Find the song card (first song)
    song_card = page.locator(".song-card").first
    
    # Verify the song name matches
    song_title = song_card.locator("h3").inner_text()
    assert song_title == rank1_song, f"Expected rank 1 to be '{rank1_song}', got '{song_title}'"
    
    # Click the info button to open stats modal
    song_card.locator('a[aria-label="View ranking details"]').click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Verify normalized score (0-1 range)
    normalized_score_text = modal.locator('tr:has-text("Normalized Score") kbd').inner_text()
    normalized_score = float(normalized_score_text)
    assert abs(normalized_score - expected["normalizedScore"]) < 0.0001, \
        f"Normalized score mismatch: expected {expected['normalizedScore']:.4f}, got {normalized_score:.4f}"
    
    # Verify raw score (final score with multipliers)
    raw_score_text = modal.locator('tr:has-text("Raw Score") kbd').inner_text()
    raw_score = float(raw_score_text)
    assert abs(raw_score - expected["finalScore"]) < 0.01, \
        f"Raw score mismatch: expected {expected['finalScore']:.4f}, got {raw_score:.4f}"
    
    # Verify base score (score before multipliers)
    base_score_text = modal.locator('tr:has-text("Base Score") kbd').inner_text()
    base_score = float(base_score_text)
    assert abs(base_score - expected["baseScore"]) < 0.01, \
        f"Base score mismatch: expected {expected['baseScore']:.4f}, got {base_score:.4f}"
    
    # Verify list count
    list_count_text = modal.locator('tr:has-text("List Count") kbd').inner_text()
    list_count = int(list_count_text)
    assert list_count == expected["listCount"], \
        f"List count mismatch: expected {expected['listCount']}, got {list_count}"
    
    # Verify consensus boost (displayed as percentage)
    consensus_boost_text = modal.locator('tr:has-text("Consensus Boost") kbd').inner_text()
    consensus_boost_pct = float(consensus_boost_text.rstrip('%'))
    expected_consensus_pct = (expected["consensusBoost"] - 1) * 100
    assert abs(consensus_boost_pct - expected_consensus_pct) < 0.1, \
        f"Consensus boost mismatch: expected {expected_consensus_pct:.2f}%, got {consensus_boost_pct:.2f}%"
    
    # Verify provocation boost (displayed as percentage)
    provocation_boost_text = modal.locator('tr:has-text("Provocation Boost") kbd').inner_text()
    provocation_boost_pct = float(provocation_boost_text.rstrip('%'))
    expected_provocation_pct = (expected["provocationBoost"] - 1) * 100
    assert abs(provocation_boost_pct - expected_provocation_pct) < 0.1, \
        f"Provocation boost mismatch: expected {expected_provocation_pct:.2f}%, got {provocation_boost_pct:.2f}%"
    
    # Verify cluster boost (displayed as percentage)
    cluster_boost_text = modal.locator('tr:has-text("Cluster Boost") kbd').inner_text()
    cluster_boost_pct = float(cluster_boost_text.rstrip('%'))
    expected_cluster_pct = (expected["clusterBoost"] - 1) * 100
    assert abs(cluster_boost_pct - expected_cluster_pct) < 0.1, \
        f"Cluster boost mismatch: expected {expected_cluster_pct:.2f}%, got {cluster_boost_pct:.2f}%"
    
    # Verify source contributions (top 3)
    contribution_rows = modal.locator('section:has-text("Source Contributions") tbody tr')
    count = contribution_rows.count()
    
    # Check at least the top 3 contributions
    for i in range(min(3, count, len(expected["sourceContributions"]))):
        row = contribution_rows.nth(i)
        contribution_text = row.locator('kbd').inner_text()
        contribution_value = float(contribution_text.lstrip('+'))
        
        expected_contrib = expected["sourceContributions"][i]
        assert abs(contribution_value - expected_contrib["contribution"]) < 0.01, \
            f"Source contribution {i+1} mismatch: expected {expected_contrib['contribution']:.2f}, got {contribution_value:.2f}"
    
    modal.locator(".close-modal").first.click()


def test_rank10_scoring_accuracy(page: Page, server_url, expected_scores):
    """Verify scoring accuracy for the #10 ranked song."""
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    
    # Get expected values for rank 10
    rank10_song = None
    for song_name, data in expected_scores.items():
        if data["rank"] == 10:
            rank10_song = song_name
            expected = data
            break
    
    assert rank10_song is not None, "No rank 10 song found in expected scores"
    
    # Find the 10th song card
    song_card = page.locator(".song-card").nth(9)
    
    # Verify the song name matches
    song_title = song_card.locator("h3").inner_text()
    assert song_title == rank10_song, f"Expected rank 10 to be '{rank10_song}', got '{song_title}'"
    
    # Click the info button to open stats modal
    song_card.locator('a[aria-label="View ranking details"]').click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Verify normalized score
    normalized_score_text = modal.locator('tr:has-text("Normalized Score") kbd').inner_text()
    normalized_score = float(normalized_score_text)
    assert abs(normalized_score - expected["normalizedScore"]) < 0.0001, \
        f"Normalized score mismatch: expected {expected['normalizedScore']:.4f}, got {normalized_score:.4f}"
    
    # Verify raw score
    raw_score_text = modal.locator('tr:has-text("Raw Score") kbd').inner_text()
    raw_score = float(raw_score_text)
    assert abs(raw_score - expected["finalScore"]) < 0.01, \
        f"Raw score mismatch: expected {expected['finalScore']:.4f}, got {raw_score:.4f}"
    
    # Verify base score
    base_score_text = modal.locator('tr:has-text("Base Score") kbd').inner_text()
    base_score = float(base_score_text)
    assert abs(base_score - expected["baseScore"]) < 0.01, \
        f"Base score mismatch: expected {expected['baseScore']:.4f}, got {base_score:.4f}"
    
    # Verify boosts
    consensus_boost_text = modal.locator('tr:has-text("Consensus Boost") kbd').inner_text()
    consensus_boost_pct = float(consensus_boost_text.rstrip('%'))
    expected_consensus_pct = (expected["consensusBoost"] - 1) * 100
    assert abs(consensus_boost_pct - expected_consensus_pct) < 0.1, \
        f"Consensus boost mismatch: expected {expected_consensus_pct:.2f}%, got {consensus_boost_pct:.2f}%"
    
    modal.locator(".close-modal").first.click()


def test_rank20_scoring_accuracy(page: Page, server_url, expected_scores):
    """Verify scoring accuracy for the #20 ranked song."""
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    
    # Get expected values for rank 20
    rank20_song = None
    for song_name, data in expected_scores.items():
        if data["rank"] == 20:
            rank20_song = song_name
            expected = data
            break
    
    assert rank20_song is not None, "No rank 20 song found in expected scores"
    
    # Find the 20th song card
    song_card = page.locator(".song-card").nth(19)
    
    # Verify the song name matches
    song_title = song_card.locator("h3").inner_text()
    assert song_title == rank20_song, f"Expected rank 20 to be '{rank20_song}', got '{song_title}'"
    
    # Click the info button to open stats modal
    song_card.locator('a[aria-label="View ranking details"]').click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Verify normalized score
    normalized_score_text = modal.locator('tr:has-text("Normalized Score") kbd').inner_text()
    normalized_score = float(normalized_score_text)
    assert abs(normalized_score - expected["normalizedScore"]) < 0.0001, \
        f"Normalized score mismatch: expected {expected['normalizedScore']:.4f}, got {normalized_score:.4f}"
    
    # Verify raw score
    raw_score_text = modal.locator('tr:has-text("Raw Score") kbd').inner_text()
    raw_score = float(raw_score_text)
    assert abs(raw_score - expected["finalScore"]) < 0.01, \
        f"Raw score mismatch: expected {expected['finalScore']:.4f}, got {raw_score:.4f}"
    
    # Verify base score
    base_score_text = modal.locator('tr:has-text("Base Score") kbd').inner_text()
    base_score = float(base_score_text)
    assert abs(base_score - expected["baseScore"]) < 0.01, \
        f"Base score mismatch: expected {expected['baseScore']:.4f}, got {base_score:.4f}"
    
    # Verify all three boosts
    consensus_boost_text = modal.locator('tr:has-text("Consensus Boost") kbd').inner_text()
    consensus_boost_pct = float(consensus_boost_text.rstrip('%'))
    expected_consensus_pct = (expected["consensusBoost"] - 1) * 100
    assert abs(consensus_boost_pct - expected_consensus_pct) < 0.1, \
        f"Consensus boost mismatch: expected {expected_consensus_pct:.2f}%, got {consensus_boost_pct:.2f}%"
    
    provocation_boost_text = modal.locator('tr:has-text("Provocation Boost") kbd').inner_text()
    provocation_boost_pct = float(provocation_boost_text.rstrip('%'))
    expected_provocation_pct = (expected["provocationBoost"] - 1) * 100
    assert abs(provocation_boost_pct - expected_provocation_pct) < 0.1, \
        f"Provocation boost mismatch: expected {expected_provocation_pct:.2f}%, got {provocation_boost_pct:.2f}%"
    
    cluster_boost_text = modal.locator('tr:has-text("Cluster Boost") kbd').inner_text()
    cluster_boost_pct = float(cluster_boost_text.rstrip('%'))
    expected_cluster_pct = (expected["clusterBoost"] - 1) * 100
    assert abs(cluster_boost_pct - expected_cluster_pct) < 0.1, \
        f"Cluster boost mismatch: expected {expected_cluster_pct:.2f}%, got {cluster_boost_pct:.2f}%"
    
    modal.locator(".close-modal").first.click()


def test_all_source_contributions_match(page: Page, server_url, expected_scores):
    """
    Verify that ALL source contributions for rank 1 song match exactly.
    This is the most comprehensive test - every single source's contribution
    must match between Python and JavaScript.
    """
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    
    # Get expected values for rank 1
    rank1_song = None
    for song_name, data in expected_scores.items():
        if data["rank"] == 1:
            rank1_song = song_name
            expected = data
            break
    
    assert rank1_song is not None, "No rank 1 song found in expected scores"
    
    # Find the song card (first song)
    song_card = page.locator(".song-card").first
    
    # Click the info button to open stats modal
    song_card.locator('a[aria-label="View ranking details"]').click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Get all contribution rows
    contribution_rows = modal.locator('section:has-text("Source Contributions") tbody tr')
    actual_count = contribution_rows.count()
    expected_count = len(expected["sourceContributions"])
    
    assert actual_count == expected_count, \
        f"Source contribution count mismatch: expected {expected_count}, got {actual_count}"
    
    # Verify each contribution matches
    for i in range(actual_count):
        row = contribution_rows.nth(i)
        
        # Extract source name (before the emoji or rank info)
        source_cell_text = row.locator('td').first.inner_text()
        # The format is: "emoji SourceName #rank" or "emoji SourceName 👻 rank"
        # We need to extract the source name
        
        # Extract contribution value
        contribution_text = row.locator('kbd').inner_text()
        contribution_value = float(contribution_text.lstrip('+'))
        
        expected_contrib = expected["sourceContributions"][i]
        
        # Verify contribution value matches (allowing small floating point error)
        assert abs(contribution_value - expected_contrib["contribution"]) < 0.01, \
            f"Source contribution #{i+1} value mismatch: " \
            f"expected {expected_contrib['name']} with {expected_contrib['contribution']:.2f}, " \
            f"got {contribution_value:.2f}"
    
    modal.locator(".close-modal").first.click()
