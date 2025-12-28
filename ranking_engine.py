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
MIN_NORM_LENGTH = 25  # Minimum list length used to prevent small-list inflation
CLUSTER_THRESHOLD = 50  # Rank limit to qualify for the Crossover Bonus
CONSENSUS_BOOST = 0.05  # Multiplier for ln(number_of_lists)
PROVOCATION_BOOST = 0.10  # Max bonus for bold/polarized choices
CLUSTER_BOOST = 0.03  # Bonus for hit in a new cluster (within Top 50)
TOP_BONUSES = {1: 0.10, 2: 0.075, 3: 0.025}


def get_decay_value(rank, mode):
    """Calculates the point value for a specific rank based on chosen mode."""
    if mode == "consensus":
        # (1+K) / (rank+K) -> Easier to explain, favors broad agreement
        val = (1 + K_VALUE) / (rank + K_VALUE)
    else:
        # 1 / (rank^P) -> More aggressive, favors absolute #1 rankings
        val = 1.0 / (rank**P_EXPONENT)

    # Apply conviction bonuses for integer ranks 1, 2, or 3
    if rank in TOP_BONUSES:
        val *= 1.0 + TOP_BONUSES[rank]
    return val


def compute_max_ranks(df: pd.DataFrame, sources: dict):
    source_max_ranks = {}
    for src, config in sources.items():
        source_max_ranks[src] = float(df["rank" + config["suffix"]].max())
    assert len(sources) == len(source_max_ranks)
    return source_max_ranks


def compute_source_norm_factors(source_max_ranks: dict, mode: str):
    source_norm_factors = {}
    for name, max_r in source_max_ranks.items():
        eff_len = max(int(math.ceil(max_r)), MIN_NORM_LENGTH)
        start_r = 26 if name == "NPR Top 125" else 1

        # Sum of decay points from start_r to eff_len
        total_points = sum(
            get_decay_value(r, mode) for r in range(start_r, eff_len + 1)
        )
        source_norm_factors[name] = total_points
    return source_norm_factors


def score_song(
    row,
    source_norm_factors: dict,
    mode: str,
    sources: dict,
    consensus_boost: float,
    provocation_boost: float,
    cluster_boost: float,
):

    total_normalized_score = 0
    ranks = []
    top50_clusters_counts = Counter()
    all_cluster_counts = Counter()

    for name, config in sources.items():
        rank_col = "rank" + config["suffix"]
        assert rank_col in row

        if pd.isna(row[rank_col]):
            continue

        rank = float(row[rank_col])
        ranks.append(rank)
        category = config["cluster"]
        if rank <= CLUSTER_THRESHOLD:
            top50_clusters_counts[category] += 1
        all_cluster_counts[category] += 1

        norm_pts = get_decay_value(rank, mode) / source_norm_factors[name]
        trust_weight = config["weight"]

        total_normalized_score += norm_pts * trust_weight

    # Multipliers
    # A. Consensus (Logarithmic)
    c_mul = 1 + (consensus_boost * np.log(len(ranks)))

    # B. Provocation (Polarization)
    p_mul = 1 + (provocation_boost * (np.std(ranks) / 100)) if len(ranks) > 1 else 1.0

    # C. Cluster Diversity (within Top 50)
    cl_mul = (
        1 + (cluster_boost * (len(top50_clusters_counts) - 1))
        if len(top50_clusters_counts) > 0
        else 1.0
    )

    top50_cluster_counts_list = [
        (cluster, count) for cluster, count in top50_clusters_counts.items()
    ]
    top50_cluster_counts_list.sort(key=lambda t: t[1], reverse=True)

    all_cluster_counts_list = [
        (cluster, count) for cluster, count in all_cluster_counts.items()
    ]
    all_cluster_counts_list.sort(key=lambda t: t[1], reverse=True)

    return (
        total_normalized_score * c_mul * p_mul * cl_mul,
        total_normalized_score,
        c_mul,
        p_mul,
        cl_mul,
        len(ranks),
        len(top50_cluster_counts_list),
        len(all_cluster_counts_list),
        top50_cluster_counts_list[0][0] if top50_cluster_counts_list else None,
        all_cluster_counts_list[0][0] if all_cluster_counts_list else None,
        ", ".join(
            [f"{cluster}:{count}" for cluster, count in top50_cluster_counts_list]
        ),
        ", ".join([f"{cluster}:{count}" for cluster, count in all_cluster_counts_list]),
    )


def compute_rankings_with_configs(
    df: pd.DataFrame, sources: dict, mode: str = "consensus"
):
    df = df.copy()

    # 1. Detect Source Max Ranks (Volume Detection)
    source_max_ranks = compute_max_ranks(df, sources)
    source_norm_factors = compute_source_norm_factors(source_max_ranks, mode)

    results = df.apply(
        lambda row: score_song(
            row,
            source_norm_factors,
            mode,
            sources,
            CONSENSUS_BOOST,
            PROVOCATION_BOOST,
            CLUSTER_BOOST,
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
    df["top50_unique_clusters_count"] = results[6]
    df["all_clusters_count"] = results[7]
    df["top50_best_cluster"] = results[8]
    df["all_best_cluster"] = results[9]
    df["top50_clusters"] = results[10]
    df["all_clusters"] = results[11]

    # Normalize final score to 0.0 - 1.0
    df["score"] = df["raw_score"] / df["raw_score"].max()

    # Sort and add final rank
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)

    return df
