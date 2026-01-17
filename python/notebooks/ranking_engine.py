import pandas as pd
import numpy as np
import math

from collections import Counter

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

# Mathematical Tuning Constants
K_VALUE = 20  # Constant for 'Consensus' mode decay
P_EXPONENT = 0.55  # Exponent for 'Conviction' mode decay

CLUSTER_THRESHOLD = 25  # Rank limit to qualify for the Crossover Bonus
CONSENSUS_BOOST = 0.03  # Multiplier for ln(number_of_lists)
PROVOCATION_BOOST = 0.0  # Max bonus for bold/polarized choices
CLUSTER_BOOST = 0.03  # Bonus for hit in a new cluster (within Top 50)
TOP_BONUSES_CONSENSUS = {1: 0.1, 2: 0.075, 3: 0.025}
TOP_BONUSES_CONVICTION = {1: 0.25, 2: 0.15, 3: 0.075}


def get_decay_value(rank, mode, k_value: float, p_exponent: float, top_bonuses: dict):
    """Calculates the point value for a specific rank based on chosen mode."""
    if mode == "consensus":
        # (1 + K) / (rank + K)
        val = (1.0 + k_value) / (rank + k_value)
    else:
        # 1 / (rank ^ P)
        val = 1.0 / (rank**p_exponent)

    # Apply conviction bonuses for integer ranks 1, 2, or 3
    int_rank = int(math.floor(rank))
    if int_rank in top_bonuses:
        val *= 1.0 + top_bonuses[int_rank]
    return val


def score_song(
    row,
    mode: str,
    sources: dict,
    consensus_boost: float,
    provocation_boost: float,
    cluster_boost: float,
    k_value: float,
    p_exponent: float,
    top_bonuses: dict,
    ln_max_list_count: float = None,
):

    total_score = 0
    ranks = []
    topn_clusters_counts = Counter()
    all_cluster_counts = Counter()

    for _, config in sources.items():
        rank_col = "rank" + config["suffix"]
        assert rank_col in row

        if pd.isna(row[rank_col]):
            continue

        rank = float(row[rank_col])
        ranks.append(rank)
        category = config["cluster"]
        if rank <= CLUSTER_THRESHOLD:
            topn_clusters_counts[category] += 1
        all_cluster_counts[category] += 1

        # DIRECT SCORING (ANCHOR-RANK)
        pts = (
            get_decay_value(rank, mode, k_value, p_exponent, top_bonuses)
            * config["weight"]
        )
        total_score += pts

    # Multipliers
    # A. Consensus (Logarithmic, normalized by max list count)
    # Normalizing ensures the slider percentage represents the maximum possible boost
    if len(ranks) > 0 and ln_max_list_count is not None and ln_max_list_count > 0:
        c_mul = 1 + (consensus_boost * np.log(len(ranks)) / ln_max_list_count)
    else:
        c_mul = 1.0

    # B. Provocation (Polarization)
    p_mul = 1 + (provocation_boost * (np.std(ranks) / 100)) if len(ranks) > 1 else 1.0

    # C. Cluster Diversity (within Top 50)
    cl_mul = (
        1 + (cluster_boost * (len(topn_clusters_counts) - 1))
        if len(topn_clusters_counts) > 0
        else 1.0
    )

    topn_cluster_counts_list = [
        (cluster, count) for cluster, count in topn_clusters_counts.items()
    ]
    topn_cluster_counts_list.sort(key=lambda t: t[1], reverse=True)

    all_cluster_counts_list = [
        (cluster, count) for cluster, count in all_cluster_counts.items()
    ]
    all_cluster_counts_list.sort(key=lambda t: t[1], reverse=True)

    # Calculate min_rank for tie-breaking (lower is better)
    min_rank = min(ranks) if ranks else float("inf")

    return (
        total_score * c_mul * p_mul * cl_mul,
        total_score,
        c_mul,
        p_mul,
        cl_mul,
        len(ranks),
        min_rank,
        len(topn_cluster_counts_list),
        len(all_cluster_counts_list),
        topn_cluster_counts_list[0][0] if topn_cluster_counts_list else None,
        all_cluster_counts_list[0][0] if all_cluster_counts_list else None,
        ", ".join(
            [f"{cluster}:{count}" for cluster, count in topn_cluster_counts_list]
        ),
        ", ".join([f"{cluster}:{count}" for cluster, count in all_cluster_counts_list]),
    )


def compute_rankings_with_configs(
    df: pd.DataFrame,
    sources: dict,
    mode: str = "consensus",
    consensus_boost=CONSENSUS_BOOST,
    provocation_boost=PROVOCATION_BOOST,
    cluster_boost=CLUSTER_BOOST,
    k_value: float = K_VALUE,
    p_exponent: float = P_EXPONENT,
    top_bonuses: dict = TOP_BONUSES_CONSENSUS,
):
    df = df.copy()

    # Calculate max_list_count across all songs for consensus boost normalization
    # This ensures the consensus_boost slider percentage represents the maximum possible boost
    rank_columns = [f"rank{config['suffix']}" for config in sources.values()]
    list_counts = df[rank_columns].notna().sum(axis=1)
    max_list_count = list_counts.max() if len(list_counts) > 0 else 1
    ln_max_list_count = np.log(max_list_count) if max_list_count > 1 else 0

    results = df.apply(
        lambda row: score_song(
            row,
            mode,
            sources,
            consensus_boost=consensus_boost,
            provocation_boost=provocation_boost,
            cluster_boost=cluster_boost,
            k_value=k_value,
            p_exponent=p_exponent,
            top_bonuses=top_bonuses,
            ln_max_list_count=ln_max_list_count,
        ),
        axis=1,
        result_type="expand",
    )
    df["raw_score"] = results[0]
    df["raw_score_before_bonus"] = results[1]
    df["consensus_bonus"] = results[2]
    df["provocation_bonus"] = results[3]
    df["diversity_bonus"] = results[4]
    df["list_count"] = results[5]
    df["min_rank"] = results[6]
    df["topn_unique_clusters_count"] = results[7]
    df["all_clusters_count"] = results[8]
    df["topn_best_cluster"] = results[9]
    df["all_best_cluster"] = results[10]
    df["topn_clusters"] = results[11]
    df["all_clusters"] = results[12]

    # Normalize final score to 0.0 - 1.0
    df["score"] = df["raw_score"] / df["raw_score"].max()

    # Create tie-breaking columns
    # Convert score to integer (scaled by 1e8) for stable comparison without floating point issues
    df["_sort_score"] = (df["score"] * 1e8).round().astype(int)
    # Convert min_rank to integer (scaled by 100) to handle fractional ranks like 6.7
    df["_sort_min_rank"] = (df["min_rank"] * 100).round().astype(int)
    # Lowercase name and artist for alphabetical tie-breaking
    df["_name_lower"] = df["name"].str.lower()
    df["_artist_lower"] = df["artist"].str.lower()

    # Sort with tie-breaking:
    # 1. score (descending, as integer scaled by 1e8)
    # 2. list_count (descending - more sources is better)
    # 3. min_rank (ascending - lower rank is better, as integer scaled by 100)
    # 4. name (ascending - alphabetical)
    # 5. artist (ascending - alphabetical)
    df = df.sort_values(
        by=["_sort_score", "list_count", "_sort_min_rank", "_name_lower", "_artist_lower"],
        ascending=[False, False, True, True, True],
    ).reset_index(drop=True)

    # Remove temporary sorting columns
    df = df.drop(columns=["_sort_score", "_sort_min_rank", "_name_lower", "_artist_lower"])

    if "rank" in df.columns:
        df.drop(columns=["rank"], inplace=True)
    df.insert(0, "rank", df.index + 1)

    return df
