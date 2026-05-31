from PIL import Image
from dvoc_core._types import Point, Vector


class Verifier:
    def __init__(
        self,
        mode: str = "simulated",
        fixed_error: Vector = Vector(0.0, 0.0),
        fixed_confidence: float = 0.95,
        model_client=None,
    ):
        self.mode = mode
        self.fixed_error = fixed_error
        self.fixed_confidence = min(max(fixed_confidence, 0.0), 1.0)
        self.model_client = model_client

    def verify(self, annotated_frame: Image.Image, draft: Point, task: str = "",
               history: list[tuple[Point, Vector, float]] | None = None) -> tuple[Vector, float]:
        if self.mode == "simulated":
            return self.fixed_error, self.fixed_confidence
        if self.mode == "model":
            if self.model_client is None:
                raise ValueError("Model verifier requires model_client")
            return self.model_client.verify(annotated_frame, draft, task, history)
        raise ValueError(f"Unknown verifier mode: {self.mode}")
