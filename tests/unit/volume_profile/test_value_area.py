import numpy as np

from src.volume_profile.value_area import compute_value_area


def test_poc_is_highest_volume_bin():
    # 10 bins, price range 100-110, bin index 5 has the most volume.
    volume_by_bin = np.array([10, 10, 10, 10, 10, 100, 10, 10, 10, 10], dtype=float)
    edges = np.linspace(100, 110, 11)

    result = compute_value_area(volume_by_bin, edges, value_area_pct=0.70)

    assert result["poc_idx"] == 5
    assert 105 <= result["poc"] <= 106


def test_value_area_covers_at_least_target_pct():
    volume_by_bin = np.array([5, 5, 5, 5, 5, 50, 5, 5, 5, 5], dtype=float)
    edges = np.linspace(100, 110, 11)
    total = volume_by_bin.sum()

    result = compute_value_area(volume_by_bin, edges, value_area_pct=0.70)
    covered = volume_by_bin[result["lo_idx"] : result["hi_idx"] + 1].sum()

    assert covered / total >= 0.70
    assert result["val"] < result["poc"] < result["vah"]


def test_zero_total_volume_raises():
    import pytest

    volume_by_bin = np.zeros(5)
    edges = np.linspace(100, 105, 6)
    with pytest.raises(ValueError):
        compute_value_area(volume_by_bin, edges)
