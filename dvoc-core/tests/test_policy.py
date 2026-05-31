import pytest
from PIL import Image
from dvoc_core import Point, Vector
from dvoc_core._state import DVOCSnapshot, DVOCState
from dvoc_core._policy import Policy, Decision


def _state_with_errors(errors: list[Vector], confidences: list[float]) -> DVOCState:
    state = DVOCState(task="test")
    img = Image.new("RGB", (100, 100))
    for i, (err, conf) in enumerate(zip(errors, confidences)):
        snap = DVOCSnapshot(
            iteration=i,
            draft_point=Point(0.0, 0.0),
            annotated_frame=img,
            error_vector=err,
            confidence=conf,
        )
        state = state.push(snap)
    return state


class TestPolicy:
    def test_refine_on_first_iteration(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(20.0, 0.0)],
            [0.8],
        )
        assert policy.evaluate(state) == Decision.REFINE

    def test_act_when_converged_two_in_a_row(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(3.0, 0.0), Vector(2.0, 0.0)],
            [0.9, 0.95],
        )
        assert policy.evaluate(state) == Decision.ACT_SAFE

    def test_not_converged_with_one_good(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(3.0, 0.0)],
            [0.9],
        )
        assert policy.evaluate(state) == Decision.REFINE

    def test_oscillation_aborts(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(5.0, 0.0), Vector(10.0, 0.0), Vector(20.0, 0.0)],
            [0.8, 0.7, 0.6],
        )
        assert policy.evaluate(state) == Decision.ABORT_OSCILLATION

    def test_no_oscillation_after_two_iters(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(20.0, 0.0), Vector(10.0, 0.0)],
            [0.6, 0.7],
        )
        assert policy.evaluate(state) == Decision.REFINE

    def test_oscillation_confidence_not_checked(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(3.0, 0.0), Vector(8.0, 0.0), Vector(15.0, 0.0)],
            [0.9, 0.9, 0.9],
        )
        assert policy.evaluate(state) == Decision.ABORT_OSCILLATION

    def test_custom_threshold(self):
        policy = Policy(epsilon=10.0, threshold=0.5, convergence_window=1)
        state = _state_with_errors(
            [Vector(8.0, 0.0)],
            [0.6],
        )
        assert policy.evaluate(state) == Decision.ACT_SAFE
