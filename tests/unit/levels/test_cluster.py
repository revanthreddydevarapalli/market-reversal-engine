from src.levels.generate import Level
from src.levels.cluster import cluster_levels


def test_nearby_levels_from_different_timeframes_cluster_together():
    levels = [
        Level("NVDA", "4H", "VAL", 176.90, 1.0),
        Level("NVDA", "1D", "POC", 177.20, 1.0),
        Level("NVDA", "1W", "VAL", 177.10, 1.0),
        Level("NVDA", "4H", "POC", 150.00, 1.0),  # far away, separate cluster
    ]

    zones = cluster_levels(levels, tolerance_pct=0.005)

    assert len(zones) == 2
    big_zone = max(zones, key=lambda z: len(z.levels))
    assert len(big_zone.levels) == 3
    assert big_zone.timeframes_present == {"4H", "1D", "1W"}
    assert big_zone.lower == 176.90
    assert big_zone.upper == 177.20


def test_confluence_zone_scores_higher_with_more_timeframes():
    single_tf = cluster_levels([Level("NVDA", "4H", "POC", 100.0, 1.0)], tolerance_pct=0.005)[0]
    multi_tf = cluster_levels(
        [
            Level("NVDA", "4H", "POC", 100.0, 1.0),
            Level("NVDA", "1D", "POC", 100.05, 1.0),
            Level("NVDA", "1W", "POC", 100.1, 1.0),
        ],
        tolerance_pct=0.005,
    )[0]

    assert multi_tf.base_score > single_tf.base_score
    assert multi_tf.strength_stars >= single_tf.strength_stars


def test_empty_levels_returns_no_zones():
    assert cluster_levels([], tolerance_pct=0.005) == []
