"""Platform detection and backend factory.

Auto-detects the display server at runtime and returns the correct backend.
"""
import os, sys


def detect_platform() -> str:
    """Detect display server platform.
    
    Returns one of: 'wayland', 'x11', 'windows'.
    """
    if sys.platform == "win32":
        return "windows"
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    return "x11"


_backend_cache: dict[str, type] = {}


def _load_backend(platform: str):
    if platform not in _backend_cache:
        if platform == "wayland":
            from dvoc_os._wayland import WaylandBackend as cls
        else:
            from dvoc_os._x11_windows import MSSBackend as cls
        _backend_cache[platform] = cls
    return _backend_cache[platform]


def OSSBackend(*args, **kwargs):
    """Auto-detecting OS backend factory. Use this for any platform."""
    platform = detect_platform()
    cls = _load_backend(platform)
    return cls(*args, **kwargs)
