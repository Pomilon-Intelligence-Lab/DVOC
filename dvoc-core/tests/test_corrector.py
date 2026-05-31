import pytest
from dvoc_core import Point, Vector, Corrector


class TestCorrector:
    def test_alpha_1_at_iter_0(self):
        c = Corrector(epsilon=5.0)
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=0)
        assert result == Point(120.0, 100.0)

    def test_alpha_half_at_iter_1(self):
        c = Corrector(epsilon=5.0)
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=1)
        assert result == Point(110.0, 100.0)

    def test_alpha_quarter_at_iter_2(self):
        c = Corrector(epsilon=5.0)
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=2)
        assert result == Point(105.0, 100.0)

    def test_alpha_min_at_iter_10(self):
        c = Corrector(epsilon=5.0)
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=5)
        assert result == Point(105.0, 100.0)

    def test_converged_true_when_error_small(self):
        c = Corrector(epsilon=5.0, threshold=0.9)
        assert c.is_converged(Vector(3.0, 0.0), 0.95) is True

    def test_converged_false_when_error_large(self):
        c = Corrector(epsilon=5.0, threshold=0.9)
        assert c.is_converged(Vector(10.0, 0.0), 0.95) is False

    def test_converged_false_when_confidence_low(self):
        c = Corrector(epsilon=5.0, threshold=0.9)
        assert c.is_converged(Vector(3.0, 0.0), 0.5) is False

    def test_custom_epsilon(self):
        c = Corrector(epsilon=10.0, threshold=0.9)
        assert c.is_converged(Vector(8.0, 0.0), 0.95) is True
        assert c.is_converged(Vector(12.0, 0.0), 0.95) is False
