from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional
import json
import base64
import os
from PIL import Image
from litellm import completion
from dvoc_core._types import Point, Vector


@dataclass
class EphemeralTurn:
    draft: Point
    error: Vector
    confidence: float


@dataclass
class EphemeralContext:
    action_id: str
    task: str
    turns: list[EphemeralTurn] = field(default_factory=list)
    converged: bool = False
    result: Optional[str] = None


VERIFY_TOOLS = [{
    "type": "function",
    "function": {
        "name": "report_offset",
        "description": "Report the pixel offset from the crosshair to the target element center.",
        "parameters": {
            "type": "object",
            "properties": {
                "dx": {"type": "number", "description": "Pixels right. Negative = left."},
                "dy": {"type": "number", "description": "Pixels down. Negative = up."},
                "confidence": {"type": "number", "description": "Confidence 0.0 to 1.0"},
            },
            "required": ["dx", "dy", "confidence"],
        },
    }
}]

VERIFY_SYSTEM = """You are a UI grounding verifier in a DVOC (Draft-Verify-Action Loop) system.

HOW THE LOOP WORKS:
A red crosshair (+) shows the current predicted click position on the screen.
A fixed blue circle gives you spatial reference.
You estimate the pixel offset from the crosshair to the target the user wants.
The system adds your offset to the crosshair position, moving it closer to the target.
This repeats until the crosshair converges on the target.

CONVERGENCE RULE:
Only report dx=0, dy=0 if the crosshair is within a few pixels of the target.
If uncertain, set lower confidence so the loop keeps refining.
Check your previous estimates in the history below. If oscillating, converge."""  # noqa: E501


class ModelClient:
    def __init__(self, api_key: str, model_name: str = "gemini/gemma-4-26b-a4b-it"):
        os.environ["GEMINI_API_KEY"] = api_key
        self.model = model_name

    def _image_b64(self, img: Image.Image) -> str:
        buf = BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def _format_history(self, history: list[tuple[Point, Vector, float]]) -> str:
        if not history:
            return ""
        lines = ["Previous iterations:"]
        for i, (pt, err, conf) in enumerate(history):
            corr = Point(pt.x + err.dx, pt.y + err.dy)
            lines.append(f"  iter {i}: crosshair at ({pt.x:.0f},{pt.y:.0f}), "
                         f"you said dx={err.dx:.0f} dy={err.dy:.0f} conf={conf:.2f}"
                         f" -> moved to ({corr.x:.0f},{corr.y:.0f})")
        return "\n".join(lines)

    def verify(self, annotated_frame: Image.Image, draft: Point, task: str,
               history: list[tuple[Point, Vector, float]] | None = None) -> tuple[Vector, float]:
        b64 = self._image_b64(annotated_frame)
        history_str = self._format_history(history or [])

        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": f"{VERIFY_SYSTEM}\n\nTask: {task}\n{history_str}\n\nCall report_offset()."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]},
        ]

        try:
            resp = completion(model=self.model, messages=messages, tools=VERIFY_TOOLS)
            msg = resp.choices[0].message
            if msg.tool_calls:
                args = json.loads(msg.tool_calls[0].function.arguments)
                error = Vector(dx=float(args.get("dx", 0)), dy=float(args.get("dy", 0)))
                confidence = min(max(float(args.get("confidence", 0)), 0.0), 1.0)
                return error, confidence
            return Vector(0.0, 0.0), 0.0
        except Exception:
            return Vector(0.0, 0.0), 0.0

    def plan(self, task: str, frame: Image.Image) -> Point:
        b64 = self._image_b64(frame)
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": f"Find the target for: {task}\nCall click_at(x, y, confidence)."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]},
        ]
        try:
            resp = completion(model=self.model, messages=messages, tools=[{
                "type": "function",
                "function": {
                    "name": "click_at",
                    "parameters": {"type": "object", "properties": {
                        "x": {"type": "number"}, "y": {"type": "number"},
                        "confidence": {"type": "number"},
                    }, "required": ["x", "y", "confidence"]},
                }
            }])
            msg = resp.choices[0].message
            if msg.tool_calls:
                args = json.loads(msg.tool_calls[0].function.arguments)
                return Point(x=float(args["x"]), y=float(args["y"]))
            return Point(frame.width / 2, frame.height / 2)
        except Exception:
            return Point(frame.width / 2, frame.height / 2)
