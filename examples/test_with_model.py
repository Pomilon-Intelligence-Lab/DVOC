"""DVOC model-based test harness.

Creates synthetic screenshots with visible targets, runs the DVOC loop
using a real vision model (Gemini/GeMMA), and tracks every refinement step.

Usage:
    export GEMINI_API_KEY="your-key-here"
    python examples/test_with_model.py
"""

import os, sys
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

from dvoc_core import (
    Point, Vector, Geometry, Action, ActionResult,
    DVOCBackend, Planner, Verifier, Corrector, Renderer, Policy,
    LoopEngine,
)
from dvoc_core._model import ModelClient


TARGET_COLOR = (100, 200, 100)
BG_COLOR = (40, 42, 48)


@dataclass
class TestScene:
    width: int
    height: int
    target_center: Point
    initial_draft: Point
    label: str = ""


def create_scene(scene: TestScene) -> Image.Image:
    img = Image.new("RGB", (scene.width, scene.height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    cx, cy = int(scene.target_center.x), int(scene.target_center.y)

    draw.rectangle(
        [cx - 40, cy - 25, cx + 40, cy + 25],
        fill=TARGET_COLOR,
        outline=(255, 255, 255),
        width=2,
    )

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.text((cx - 30, cy - 12), scene.label or "CLICK ME", fill=(255, 255, 255), font=font)

    return img


class SyntheticBackend(DVOCBackend):
    def __init__(self, scene: TestScene):
        self.scene = scene

    def capture(self) -> Image.Image:
        return create_scene(self.scene)

    def execute(self, action: Action) -> ActionResult:
        tx, ty = self.scene.target_center.x, self.scene.target_center.y
        ax, ay = action.target.x, action.target.y
        dist = ((tx - ax) ** 2 + (ty - ay) ** 2) ** 0.5
        return ActionResult(success=dist < 10.0, error=f"missed by {dist:.1f}px")

    def get_screen_geometry(self) -> Geometry:
        return Geometry(self.scene.width, self.scene.height)


def run_test(api_key: str, scene: TestScene, model_name: str = "gemma-4-26b-a4b-it", epsilon: float = 15.0):
    print(f"\n{'='*60}")
    print(f"Test: target at ({int(scene.target_center.x)}, {int(scene.target_center.y)})")
    print(f"      initial draft at ({int(scene.initial_draft.x)}, {int(scene.initial_draft.y)})")
    print(f"      model: {model_name}")
    print(f"{'='*60}")

    model = ModelClient(api_key=api_key, model_name=model_name)

    engine = LoopEngine(
        backend=SyntheticBackend(scene),
        planner=Planner(mode="manual", manual_target=scene.initial_draft),
        verifier=Verifier(mode="model", model_client=model),
        corrector=Corrector(epsilon=epsilon, threshold=0.6),
        renderer=Renderer(),
        policy=Policy(epsilon=epsilon, threshold=0.6, convergence_window=2),
    )

    result = engine.run(f"Click the button labeled '{scene.label or 'CLICK ME'}'")

    tx, ty = scene.target_center.x, scene.target_center.y
    fx, fy = result.final_point.x, result.final_point.y if result.final_point else (0, 0)
    final_dist = ((tx - fx) ** 2 + (ty - fy) ** 2) ** 0.5 if result.final_point else float("inf")

    print(f"\nIterations: {result.iterations}")
    print(f"Decision: {result.decision}")
    print(f"Final draft: ({fx:.0f}, {fy:.0f})")
    print(f"Target: ({tx:.0f}, {ty:.0f})")
    print(f"Final distance: {final_dist:.1f}px")
    print(f"Success: {result.success}")

    print(f"\nRefinement steps:")
    for i, snap in enumerate(result.history):
        d = ((tx - snap.draft_point.x) ** 2 + (ty - snap.draft_point.y) ** 2) ** 0.5
        print(f"  iter {i}: draft=({snap.draft_point.x:.0f}, {snap.draft_point.y:.0f}) "
              f"error=({snap.error_vector.dx:.0f}, {snap.error_vector.dy:.0f}) "
              f"conf={snap.confidence:.2f} dist_to_target={d:.0f}px")

    if result.final_point:
        test_passed = final_dist < epsilon
        print(f"\n{'PASS' if test_passed else 'FAIL'}: "
              f"{'Converged within epsilon' if test_passed else f'Missed by {final_dist:.0f}px'}")
        return test_passed
    return False


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable")
        sys.exit(1)

    model_name = os.environ.get("DVAL_MODEL", "gemini-2.5-flash")

    scenes = [
        TestScene(
            width=800, height=600,
            target_center=Point(400.0, 300.0),
            initial_draft=Point(100.0, 100.0),
            label="CLICK ME",
        ),
        TestScene(
            width=800, height=600,
            target_center=Point(600.0, 150.0),
            initial_draft=Point(300.0, 450.0),
            label="SUBMIT",
        ),
        TestScene(
            width=1024, height=768,
            target_center=Point(512.0, 500.0),
            initial_draft=Point(200.0, 200.0),
            label="LOGIN",
        ),
    ]

    passed = 0
    for scene in scenes:
        try:
            if run_test(api_key, scene, model_name=model_name):
                passed += 1
        except Exception as e:
            print(f"\nERROR: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(scenes)} passed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
