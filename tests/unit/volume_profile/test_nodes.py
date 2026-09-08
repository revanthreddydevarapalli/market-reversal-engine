import numpy as np

from src.volume_profile.nodes import detect_hvn_lvn


def test_detects_clear_hvn_spike():
    volume_by_bin = np.array([10, 10, 10, 100, 10, 10, 10], dtype=float)
    edges = np.linspace(100, 107, 8)

    hvns, lvns = detect_hvn_lvn(volume_by_bin, edges, window=2, min_prominence_pct=0.15)

    hvn_indices = [h["bin_index"] for h in hvns]
    assert 3 in hvn_indices


def test_detects_clear_lvn_dip():
    volume_by_bin = np.array([50, 50, 50, 1, 50, 50, 50], dtype=float)
    edges = np.linspace(100, 107, 8)

    hvns, lvns = detect_hvn_lvn(volume_by_bin, edges, window=2, min_prominence_pct=0.15)

    lvn_indices = [lv["bin_index"] for lv in lvns]
    assert 3 in lvn_indices


def test_flat_distribution_has_no_nodes():
    volume_by_bin = np.full(10, 50.0)
    edges = np.linspace(100, 110, 11)

    hvns, lvns = detect_hvn_lvn(volume_by_bin, edges, window=2, min_prominence_pct=0.15)

    assert hvns == []
    assert lvns == []
