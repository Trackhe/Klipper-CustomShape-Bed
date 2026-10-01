#!/usr/bin/env python3
"""Geometry tests for keepout_zone (no Klipper required)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from keepout_zone import (  # noqa: E402
    expand_rect,
    point_in_rect,
    segment_intersects_rect,
)


class TestPointInRect(unittest.TestCase):
    def test_inside(self):
        self.assertTrue(point_in_rect(25, 25, 0, 0, 50, 50))

    def test_edge(self):
        self.assertTrue(point_in_rect(0, 0, 0, 0, 50, 50))
        self.assertTrue(point_in_rect(50, 50, 0, 0, 50, 50))

    def test_outside(self):
        self.assertFalse(point_in_rect(51, 25, 0, 0, 50, 50))


class TestSegment(unittest.TestCase):
    def test_both_outside_no_cross(self):
        # Front middle travel — should NOT hit left keepout
        self.assertFalse(
            segment_intersects_rect(100, 0, 400, 0, 0, 0, 50, 50)
        )

    def test_diagonal_through_corner(self):
        # From center-ish into left keepout
        self.assertTrue(
            segment_intersects_rect(100, 100, 25, 25, 0, 0, 50, 50)
        )

    def test_skims_edge(self):
        # Horizontal line along y=25 through the zone
        self.assertTrue(
            segment_intersects_rect(-10, 25, 60, 25, 0, 0, 50, 50)
        )

    def test_endpoint_inside(self):
        self.assertTrue(
            segment_intersects_rect(100, 100, 10, 10, 0, 0, 50, 50)
        )

    def test_parallel_miss(self):
        self.assertFalse(
            segment_intersects_rect(60, 0, 60, 100, 0, 0, 50, 50)
        )

    def test_right_zone_path(self):
        # Travel across front that clips right keepout
        self.assertTrue(
            segment_intersects_rect(400, 10, 480, 10, 450, 0, 500, 50)
        )
        # Safe front middle
        self.assertFalse(
            segment_intersects_rect(100, 10, 400, 10, 450, 0, 500, 50)
        )


class TestMargin(unittest.TestCase):
    def test_expand(self):
        self.assertEqual(
            expand_rect(0, 0, 50, 50, 2),
            (-2, -2, 52, 52),
        )


if __name__ == '__main__':
    unittest.main()
