import pytest
from PIL import Image
from dvoc_core import Point, Action, Geometry
from dvoc_web import WebBackend


class TestWebBackendUnit:
    def test_capture_returns_image(self, page):
        b = WebBackend(headless=True)
        b.start(page=page)
        page.goto("data:text/html,<h1>Hello</h1>", wait_until="load")
        img = b.capture()
        assert isinstance(img, Image.Image)
        assert img.size == (1280, 720)
        b.stop()

    def test_get_screen_geometry(self, page):
        b = WebBackend(headless=True)
        b.start(page=page)
        geom = b.get_screen_geometry()
        assert isinstance(geom, Geometry)
        assert geom.width == 1280
        assert geom.height == 720
        b.stop()

    def test_execute_click(self, page):
        page.goto("data:text/html,<div id=target style='width:100px;height:100px;background:red;position:absolute;left:200px;top:200px' onclick='window.clicked=true'></div><script>window.clicked=false</script>", wait_until="load")
        b = WebBackend(headless=True)
        b.start(page=page)
        result = b.execute(Action(type="click", target=Point(250, 250)))
        assert result.success is True
        assert page.evaluate("window.clicked") is True
        b.stop()

    def test_execute_type(self, page):
        page.goto("data:text/html,<input id=inp>", wait_until="load")
        page.click("input")
        b = WebBackend(headless=True)
        b.start(page=page)
        result = b.execute(Action(type="type", text="hello world"))
        assert result.success is True
        assert page.evaluate("document.getElementById('inp').value") == "hello world"
        b.stop()

    def test_execute_keypress(self, page):
        page.goto("data:text/html,<input id=inp>", wait_until="load")
        page.click("input")
        b = WebBackend(headless=True)
        b.start(page=page)
        result = b.execute(Action(type="keypress", key="Enter"))
        assert result.success is True
        b.stop()

    def test_execute_unknown_action(self, page):
        b = WebBackend(headless=True)
        b.start(page=page)
        result = b.execute(Action(type="unknown"))
        assert result.success is False
        assert "unknown" in (result.error or "")
        b.stop()

    def test_capture_before_start_fails(self):
        b = WebBackend(headless=True)
        with pytest.raises(RuntimeError, match="not started"):
            b.capture()

    def test_geometry_before_start_fails(self):
        b = WebBackend(headless=True)
        with pytest.raises(RuntimeError, match="not started"):
            b.get_screen_geometry()

    def test_custom_viewport(self, browser):
        ctx = browser.new_context(viewport={"width": 800, "height": 600})
        p = ctx.new_page()
        b = WebBackend(headless=True)
        b.start(page=p)
        p.goto("data:text/html,<h1>Hello</h1>", wait_until="load")
        img = b.capture()
        assert img.size == (800, 600)
        b.stop()
        p.close()
        ctx.close()

    def test_inject_page(self, browser):
        ctx = browser.new_context(viewport={"width": 1024, "height": 768})
        p = ctx.new_page()
        p.goto("data:text/html,<h1>Injected</h1>", wait_until="load")
        b = WebBackend(headless=True)
        b.start(page=p)
        img = b.capture()
        assert img.size == (1024, 768)
        b.stop()
        p.close()
        ctx.close()
