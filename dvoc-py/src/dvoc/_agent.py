import os as _os

from dvoc_core import (
    Point, Vector, Geometry, Action, ActionResult,
    DVOCBackend, Planner, Verifier, Corrector, Renderer, Policy,
)
from dvoc_core._loop import LoopEngine


class DVOC:
    def __init__(
        self,
        backend: str | DVOCBackend = "os",
        model: str | None = None,
        epsilon: float = 5.0,
        threshold: float = 0.85,
        manual_target: Point | None = None,
    ):
        if isinstance(backend, DVOCBackend):
            self._backend = backend
            self.backend_type = "preconfigured"
        else:
            self._backend = None
            self.backend_type = backend
        self.model = model
        self.epsilon = epsilon
        self.threshold = threshold
        self.manual_target = manual_target

    def _resolve_target(self, target):
        if target is None:
            return None
        if isinstance(target, tuple):
            return Point(float(target[0]), float(target[1]))
        return target

    def run(self, task: str) -> dict:
        backend = self._backend if self._backend else self._create_backend()
        manual_target = self._resolve_target(self.manual_target)

        if self.model:
            from dvoc_core._model import ModelClient
            api_key = _os.environ.get("GEMINI_API_KEY", "")
            model_client = ModelClient(api_key=api_key, model_name=self.model)
            verifier = Verifier(mode="model", model_client=model_client)
            planner_mode = "model" if manual_target is None else "manual"
            planner = Planner(mode=planner_mode, model_client=model_client if planner_mode == "model" else None,
                              manual_target=manual_target)
        else:
            verifier = Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99)
            planner = Planner(mode="manual", manual_target=manual_target)

        corrector = Corrector(epsilon=self.epsilon, threshold=self.threshold)
        renderer = Renderer()
        policy = Policy(epsilon=self.epsilon, threshold=self.threshold)

        engine = LoopEngine(
            backend=backend,
            planner=planner,
            verifier=verifier,
            corrector=corrector,
            renderer=renderer,
            policy=policy,
        )

        result = engine.run(task)
        return {
            "success": result.success,
            "final_point": result.final_point,
            "iterations": result.iterations,
            "decision": result.decision,
        }

    def _create_backend(self) -> DVOCBackend:
        if self.backend_type == "os":
            from dvoc_os import OSSBackend
            return OSSBackend()
        if self.backend_type == "web":
            from dvoc_web import WebBackend
            backend = WebBackend(headless=True)
            backend.start()
            return backend
        raise ValueError(f"Unknown backend: {self.backend_type}")
