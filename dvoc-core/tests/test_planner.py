import pytest
from dvoc_core import Point, Planner


class TestPlanner:
    def test_manual_mode_returns_target(self):
        p = Planner(mode="manual", manual_target=Point(100.0, 200.0))
        result = p.draft("click anything")
        assert result == Point(100.0, 200.0)

    def test_manual_mode_different_target(self):
        p = Planner(mode="manual", manual_target=Point(800.0, 600.0))
        result = p.draft("click login")
        assert result == Point(800.0, 600.0)

    def test_manual_mode_default_is_center(self):
        p = Planner(mode="manual")
        result = p.draft("click")
        assert result == Point(960.0, 540.0)
