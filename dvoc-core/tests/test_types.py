import pytest
from dvoc_core import Point, Vector, Geometry, Action, ActionResult


class TestPoint:
    def test_creates_with_xy(self):
        p = Point(100.0, 200.0)
        assert p.x == 100.0
        assert p.y == 200.0

    def test_is_frozen(self):
        p = Point(1.0, 2.0)
        with pytest.raises(AttributeError):
            p.x = 99.0

    def test_equality(self):
        assert Point(1.0, 2.0) == Point(1.0, 2.0)
        assert Point(1.0, 2.0) != Point(3.0, 4.0)

    def test_repr(self):
        r = repr(Point(1.5, 2.5))
        assert "Point" in r
        assert "1.5" in r


class TestVector:
    def test_creates_with_dx_dy(self):
        v = Vector(10.0, -5.0)
        assert v.dx == 10.0
        assert v.dy == -5.0

    def test_is_frozen(self):
        v = Vector(1.0, 2.0)
        with pytest.raises(AttributeError):
            v.dx = 99.0

    def test_magnitude(self):
        v = Vector(3.0, 4.0)
        assert v.magnitude == 5.0

    def test_zero_vector(self):
        v = Vector(0.0, 0.0)
        assert v.magnitude == 0.0


class TestGeometry:
    def test_creates_with_dimensions(self):
        g = Geometry(width=1920, height=1080)
        assert g.width == 1920
        assert g.height == 1080

    def test_is_frozen(self):
        g = Geometry(1920, 1080)
        with pytest.raises(AttributeError):
            g.width = 999


class TestAction:
    def test_click_action(self):
        a = Action(type="click", target=Point(100.0, 200.0))
        assert a.type == "click"
        assert a.target == Point(100.0, 200.0)

    def test_type_action(self):
        a = Action(type="type", text="hello")
        assert a.type == "type"
        assert a.text == "hello"

    def test_is_frozen(self):
        a = Action(type="click", target=Point(1.0, 2.0))
        with pytest.raises(AttributeError):
            a.type = "type"


class TestActionResult:
    def test_success(self):
        r = ActionResult(success=True)
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = ActionResult(success=False, error="click missed")
        assert r.success is False
        assert r.error == "click missed"

    def test_is_frozen(self):
        r = ActionResult(success=True)
        with pytest.raises(AttributeError):
            r.success = False
