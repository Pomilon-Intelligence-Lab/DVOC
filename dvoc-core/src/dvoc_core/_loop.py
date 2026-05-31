from dataclasses import dataclass
from PIL import Image
from dvoc_core._types import Point, Action
from dvoc_core._state import DVOCSnapshot, DVOCState
from dvoc_core._backend import DVOCBackend
from dvoc_core._planner import Planner
from dvoc_core._verifier import Verifier
from dvoc_core._corrector import Corrector
from dvoc_core._renderer import Renderer
from dvoc_core._policy import Policy, Decision


@dataclass(frozen=True)
class LoopResult:
    success: bool
    final_point: Point | None
    iterations: int
    decision: str
    history: tuple[DVOCSnapshot, ...]


class LoopEngine:
    def __init__(
        self,
        backend: DVOCBackend,
        planner: Planner,
        verifier: Verifier,
        corrector: Corrector,
        renderer: Renderer,
        policy: Policy,
        radius: float = 30.0,
        max_iterations: int = 20,
    ):
        self.backend = backend
        self.planner = planner
        self.verifier = verifier
        self.corrector = corrector
        self.renderer = renderer
        self.policy = policy
        self.radius = radius
        self.max_iterations = max_iterations

    def run(self, task: str) -> LoopResult:
        state = DVOCState(task=task)
        frame = self.backend.capture()
        draft = self.planner.draft(task, frame)

        while True:
            if state.iteration >= self.max_iterations:
                return LoopResult(
                    success=False,
                    final_point=draft,
                    iterations=state.iteration,
                    decision="max_iterations",
                    history=state.snapshots,
                )
            frame = self.backend.capture()

            annotated = self.renderer.overlay(frame, draft, self.radius, iteration=state.iteration)

            history = [(s.draft_point, s.error_vector, s.confidence) for s in state.snapshots]
            error, confidence = self.verifier.verify(annotated, draft, task, history)

            snap = DVOCSnapshot(
                iteration=state.iteration,
                draft_point=draft,
                annotated_frame=annotated,
                error_vector=error,
                confidence=confidence,
            )
            state = state.push(snap)

            decision = self.policy.evaluate(state)

            match decision:
                case Decision.REFINE:
                    corrected = self.corrector.correct(draft, error, state.iteration - 1)
                    draft = Point(
                        x=max(0.0, min(corrected.x, float(frame.width - 1))),
                        y=max(0.0, min(corrected.y, float(frame.height - 1))),
                    )
                case Decision.ACT_SAFE:
                    action = Action(type="click", target=draft)
                    self.backend.execute(action)
                    return LoopResult(
                        success=True,
                        final_point=draft,
                        iterations=state.iteration,
                        decision="act_safe",
                        history=state.snapshots,
                    )
                case Decision.ABORT_OSCILLATION:
                    return LoopResult(
                        success=False,
                        final_point=draft,
                        iterations=state.iteration,
                        decision="abort_oscillation",
                        history=state.snapshots,
                    )
