import pytest
from PIL import Image
from dvoc_core import (
    Point, Vector, Geometry, Action, ActionResult,
    DVOCBackend, Planner, Verifier, Corrector, Renderer, Policy,
)
from dvoc_core._loop import LoopEngine


class FakeBackend(DVOCBackend):
    def __init__(self):
        self.captures = 0
        self.executions = []

    def capture(self):
        self.captures += 1
        return Image.new("RGB", (1920, 1080))

    def execute(self, action: Action) -> ActionResult:
        self.executions.append(action)
        return ActionResult(success=True)

    def get_screen_geometry(self):
        return Geometry(1920, 1080)


class TestLoopEngine:
    def test_converges_on_zero_error(self):
        backend = FakeBackend()
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(100.0, 100.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert result.success is True
        assert result.final_point == Point(100.0, 100.0)
        assert result.iterations == 2
        assert len(backend.executions) == 1

    def test_corrects_to_target(self):
        backend = FakeBackend()
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(200.0, 200.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(3.0, 0.0), fixed_confidence=0.9),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert result.success is True
        assert result.final_point == Point(203.0, 200.0)  # alpha=1.0 * 3px correction
        assert len(backend.executions) == 1

    def test_aborts_on_oscillation(self):
        backend = FakeBackend()
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(100.0, 100.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(100.0, 0.0), fixed_confidence=0.5),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert result.success is False
        assert result.decision == "abort_oscillation"

    def test_full_history_returned(self):
        backend = FakeBackend()
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(50.0, 50.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert len(result.history) == 2


class TestLoopEngineIntegration:
    def test_os_backend_capture_works(self):
        try:
            from dvoc_os import OSSBackend
        except ImportError as e:
            pytest.skip(f"dvoc-os not available: {e}")
        try:
            backend = OSSBackend()
        except RuntimeError as e:
            pytest.skip(f"OSSBackend init failed: {e}")

        img = backend.capture()
        geom = backend.get_screen_geometry()
        assert img.size == (geom.width, geom.height)
        assert geom.width > 0
        assert geom.height > 0
