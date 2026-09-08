import numpy as np

from tests.fixtures.synthetic_bars import make_bars
from src.volume_profile.binning import compute_bin_edges
from src.volume_profile.volume_allocation import allocate_volume


def test_total_allocated_volume_matches_input():
    bars = make_bars([(100, 105, 99, 102, 1000), (102, 110, 101, 108, 2000), (108, 112, 107, 109, 500)])
    edges = compute_bin_edges(bars, bin_count=20)
    volume_by_bin = allocate_volume(bars, edges)

    assert np.isclose(volume_by_bin.sum(), 3500)


def test_single_bar_single_bin_gets_all_volume():
    bars = make_bars([(100, 100.01, 99.99, 100, 1000)])
    edges = compute_bin_edges(bars, bin_count=1)
    volume_by_bin = allocate_volume(bars, edges)

    assert volume_by_bin.shape == (1,)
    assert np.isclose(volume_by_bin[0], 1000)
