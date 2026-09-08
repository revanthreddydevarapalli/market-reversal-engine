import pytest

from tests.fixtures.synthetic_bars import make_bars
from src.volume_profile.binning import compute_bin_edges


def test_bin_edges_span_full_range():
    bars = make_bars([(100, 105, 99, 102, 1000), (102, 110, 101, 108, 2000)])
    edges = compute_bin_edges(bars, bin_count=10)

    assert len(edges) == 11
    assert edges[0] == 99  # min low
    assert edges[-1] == 110  # max high


def test_bin_edges_empty_bars_raises():
    with pytest.raises(ValueError):
        compute_bin_edges([], bin_count=10)


def test_bin_edges_degenerate_flat_bar():
    bars = make_bars([(100, 100, 100, 100, 500)])
    edges = compute_bin_edges(bars, bin_count=5)
    assert edges[-1] > edges[0]
