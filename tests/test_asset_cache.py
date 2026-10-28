"""
Unit tests and retrieval performance benchmarks for PieceAssetCache.
"""

import time
import pytest
import cairo

from chess_reader.theme.schema import ChessReaderTheme
from chess_reader.theme.loader import ThemeManager
from chess_reader.theme.asset_cache import PieceAssetCache
from chess_reader.theme.fallback import AssetResolver


def test_asset_cache_renders_and_caches_surfaces():
    manager = ThemeManager(user_themes_dir="/tmp/non_existent_123")
    theme = manager.active_theme
    cache = PieceAssetCache()

    # Initial retrieval (render + cache)
    surf1 = cache.get_piece_surface(theme, "wK", square_size=80, scale_factor=1)
    assert isinstance(surf1, cairo.ImageSurface)
    assert surf1.get_width() == 80
    assert surf1.get_height() == 80
    assert cache.cached_count == 1

    # Second retrieval (must be the exact same cached object)
    surf2 = cache.get_piece_surface(theme, "wK", square_size=80, scale_factor=1)
    assert surf1 is surf2
    assert cache.cached_count == 1

    # HiDPI 2x scale retrieval
    surf_hidpi = cache.get_piece_surface(theme, "wK", square_size=80, scale_factor=2)
    assert surf_hidpi.get_width() == 160
    assert surf_hidpi.get_height() == 160
    assert surf_hidpi.get_device_scale() == (2.0, 2.0)
    assert cache.cached_count == 2


def test_asset_cache_prewarm():
    manager = ThemeManager(user_themes_dir="/tmp/non_existent_123")
    theme = manager.active_theme
    cache = PieceAssetCache()

    assert cache.cached_count == 0
    cache.prewarm(theme, square_size=75, scale_factor=1)
    # Pre-warming all 12 standard pieces
    assert cache.cached_count == len(AssetResolver.PIECE_SYMBOLS)
    assert cache.cached_count == 12

    cache.clear()
    assert cache.cached_count == 0


def test_asset_cache_retrieval_benchmark():
    """Verify that cached piece retrieval takes < 0.05ms (< 50 microseconds) per lookup."""
    manager = ThemeManager(user_themes_dir="/tmp/non_existent_123")
    theme = manager.active_theme
    cache = PieceAssetCache()

    # Prewarm
    cache.prewarm(theme, square_size=80, scale_factor=1)

    # Benchmark 2,000 cached lookups
    iterations = 2000
    start_time = time.perf_counter()
    for _ in range(iterations):
        for symbol in ["wK", "wQ", "bP", "bN"]:
            _ = cache.get_piece_surface(theme, symbol, square_size=80, scale_factor=1)
    elapsed = time.perf_counter() - start_time

    total_lookups = iterations * 4
    avg_lookup_ms = (elapsed / total_lookups) * 1000.0

    print(f"\n[Benchmark] {total_lookups} cached piece lookups in {elapsed*1000:.2f}ms (avg: {avg_lookup_ms:.5f}ms per lookup)")
    # Must be under 0.05ms (50 microseconds)
    assert avg_lookup_ms < 0.05
