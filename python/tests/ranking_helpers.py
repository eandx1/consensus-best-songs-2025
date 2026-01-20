"""
Shared helper functions for ranking engine tests.

These functions bridge test_data.json source names to Python's sources.py
and help build DataFrames compatible with the ranking engine.
"""
import os
import sys

import pandas as pd

# Add the notebooks directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../notebooks"))
from sources import SHADOW_RANKS, SOURCES


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
    Build a sources configuration dict compatible with ranking_engine.

    Uses Python's SOURCES as the source of truth for weights and clusters.
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
    rows = []

    for song in test_data["songs"]:
        row = {
            "name": song["name"],
            "artist": song["artist"],
            "id": song["id"],
        }

        # Initialize all rank columns to None
        for source_name, config in sources.items():
            rank_col = f"rank{config['suffix']}"
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
