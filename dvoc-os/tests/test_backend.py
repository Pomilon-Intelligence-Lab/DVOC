import pytest
from PIL import Image
from dvoc_core import Point, Action, Geometry


def _can_init() -> bool:
    """Check if OSSBackend can initialize on this platform."""
    try:
        from dvoc_os import OSSBackend
        OSSBackend()
        return True
    except (ImportError, RuntimeError):
        return False


@pytest.mark.skipif(not _can_init(), reason="no suitable backend for this platform")
class TestOSSBackend:
    def test_capture_returns_image(self):
        from dvoc_os import OSSBackend
        backend = OSSBackend()
        img = backend.capture()
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_get_screen_geometry(self):
        from dvoc_os import OSSBackend
        backend = OSSBackend()
        geom = backend.get_screen_geometry()
        assert isinstance(geom, Geometry)
        assert geom.width > 0
        assert geom.height > 0

    def test_capture_size_matches_geometry(self):
        from dvoc_os import OSSBackend
        backend = OSSBackend()
        geom = backend.get_screen_geometry()
        img = backend.capture()
        assert img.size == (geom.width, geom.height)


class TestBackendDetection:
    def test_detect_platform(self):
        from dvoc_os._backend import detect_platform
        plat = detect_platform()
        assert plat in ("x11", "wayland", "windows")

    def test_x11_backend_imports(self):
        from dvoc_os._x11_windows import MSSBackend
        import inspect
        assert hasattr(MSSBackend, "capture")
        assert hasattr(MSSBackend, "execute")
        assert hasattr(MSSBackend, "get_screen_geometry")

    def test_wayland_backend_imports(self):
        from dvoc_os._wayland import WaylandBackend
        assert hasattr(WaylandBackend, "capture")
        assert hasattr(WaylandBackend, "execute")
        assert hasattr(WaylandBackend, "get_screen_geometry")
