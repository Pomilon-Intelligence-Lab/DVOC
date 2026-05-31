import pytest
from PIL import Image
from dvoc_core import Point, Vector, Verifier


class TestVerifier:
    def test_simulated_returns_expected_vector(self):
        v = Verifier(mode="simulated", fixed_error=Vector(15.0, -10.0), fixed_confidence=0.8)
        img = Image.new("RGB", (100, 100))
        error, confidence = v.verify(img, Point(50.0, 50.0))
        assert error == Vector(15.0, -10.0)
        assert confidence == 0.8

    def test_simulated_zero_error(self):
        v = Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99)
        img = Image.new("RGB", (100, 100))
        error, confidence = v.verify(img, Point(100.0, 100.0))
        assert error == Vector(0.0, 0.0)
        assert confidence == 0.99

    def test_confidence_clamped(self):
        v = Verifier(mode="simulated", fixed_error=Vector(1.0, 1.0), fixed_confidence=1.5)
        img = Image.new("RGB", (100, 100))
        _, confidence = v.verify(img, Point(0.0, 0.0))
        assert confidence == pytest.approx(1.0, abs=1e-6)

    def test_unknown_mode_raises(self):
        v = Verifier(mode="nonexistent")
        img = Image.new("RGB", (100, 100))
        with pytest.raises(ValueError, match="Unknown verifier mode"):
            v.verify(img, Point(0.0, 0.0))
