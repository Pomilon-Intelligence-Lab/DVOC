"""Integration tests for WebBackend with real (data URI) web pages."""

import pytest
from PIL import Image
from dvoc_core import Point, Vector, Action, LoopEngine, Planner, Verifier, Corrector, Renderer, Policy
from dvoc_web import WebBackend


BUTTON_PAGE = (
    "data:text/html,"
    "<body><button id=btn style='"
    "position:absolute;left:200px;top:225px;width:100px;height:50px"
    "' onclick=\"document.title='CLICKED'\">CLICK ME</button></body>"
)

FORM_PAGE = (
    "data:text/html,"
    "<body>"
    "<input id=name style='position:absolute;left:200px;top:200px;width:200px;height:30px'>"
    "</body>"
)


class TestIntegration:
    def test_dval_loop_on_button_page(self, page):
        page.goto(BUTTON_PAGE, wait_until="load")
        b = WebBackend(headless=True)
        b.start(page=page)

        planner = Planner(mode="manual", manual_target=Point(250, 250))
        verifier = Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99)
        corrector = Corrector(epsilon=30.0, threshold=0.5)
        renderer = Renderer()
        policy = Policy(epsilon=30.0, threshold=0.5, convergence_window=2)

        engine = LoopEngine(
            backend=b, planner=planner, verifier=verifier,
            corrector=corrector, renderer=renderer, policy=policy,
        )
        result = engine.run("Click the button")
        assert result.success is True
        assert page.title() == "CLICKED"
        b.stop()

    def test_dval_loop_click_input_and_type(self, page):
        page.goto(FORM_PAGE, wait_until="load")
        b = WebBackend(headless=True)
        b.start(page=page)

        planner = Planner(mode="manual", manual_target=Point(300, 215))
        verifier = Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99)
        corrector = Corrector(epsilon=30.0, threshold=0.5)
        renderer = Renderer()
        policy = Policy(epsilon=30.0, threshold=0.5, convergence_window=2)

        engine = LoopEngine(
            backend=b, planner=planner, verifier=verifier,
            corrector=corrector, renderer=renderer, policy=policy,
        )
        result = engine.run("Click the input")
        assert result.success is True

        r2 = b.execute(Action(type="type", text="hello"))
        assert r2.success is True
        assert page.evaluate("document.getElementById('name').value") == "hello"
        b.stop()

    def test_capture_has_page_content(self, page):
        page.goto("data:text/html,<div style='width:100%;height:100%;background:rgb(255,0,0)'></div>", wait_until="load")
        b = WebBackend(headless=True)
        b.start(page=page)
        img = b.capture()
        px = img.getpixel((10, 10))
        assert px[0] > 200 and px[1] < 50 and px[2] < 50
        b.stop()
