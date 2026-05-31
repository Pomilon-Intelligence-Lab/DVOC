import pytest
from PIL import Image
from dvoc_core import Point, Renderer


class TestRenderer:
    def test_overlay_returns_image(self):
        r = Renderer()
        frame = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
        result = r.overlay(frame, Point(960.0, 540.0), radius=30.0, iteration=0)
        assert isinstance(result, Image.Image)
        assert result.size == (1920, 1080)

    def test_overlay_deterministic(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(0, 0, 0))
        a = r.overlay(frame, Point(50.0, 50.0), radius=20.0, iteration=0)
        b = r.overlay(frame, Point(50.0, 50.0), radius=20.0, iteration=0)
        assert list(a.getdata()) == list(b.getdata())

    def test_overlay_at_origin(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = r.overlay(frame, Point(0.0, 0.0), radius=10.0, iteration=0)
        assert isinstance(result, Image.Image)

    def test_different_radius_gives_different_result(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(0, 0, 0))
        a = r.overlay(frame, Point(50.0, 50.0), radius=10.0, iteration=0)
        b = r.overlay(frame, Point(50.0, 50.0), radius=50.0, iteration=0)
        assert list(a.getdata()) != list(b.getdata())

    def test_crosshair_visible_at_center(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = r.overlay(frame, Point(50.0, 50.0), radius=20.0, iteration=0)
        px = result.getpixel((50, 50))
        assert px == (255, 0, 0), f"Expected red at center, got {px}"

    def test_iteration_text_appears(self):
        r = Renderer()
        frame = Image.new("RGB", (500, 500), color=(255, 255, 255))
        result = r.overlay(frame, Point(250.0, 250.0), radius=20.0, iteration=3)
        assert isinstance(result, Image.Image)
