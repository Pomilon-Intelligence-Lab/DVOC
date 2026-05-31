from PIL import Image
from dvoc_core._types import Point


class Planner:
    def __init__(
        self,
        mode: str = "manual",
        manual_target: Point | None = None,
        model_client=None,
    ):
        self.mode = mode
        self.manual_target = manual_target
        self.model_client = model_client

    def draft(self, task: str, frame: Image.Image | None = None) -> Point:
        if self.mode == "manual":
            if self.manual_target is not None:
                return self.manual_target
            return Point(960.0, 540.0)
        if self.mode == "model":
            if self.model_client is None:
                raise ValueError("Model planner requires model_client")
            if frame is None:
                raise ValueError("Model planner requires a frame")
            return self.model_client.plan(task, frame)
        raise ValueError(f"Unknown planner mode: {self.mode}")
