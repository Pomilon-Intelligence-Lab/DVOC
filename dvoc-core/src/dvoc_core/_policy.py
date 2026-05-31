from enum import Enum
from dvoc_core._state import DVOCState


class Decision(Enum):
    REFINE = "refine"
    ACT_SAFE = "act_safe"
    ABORT_OSCILLATION = "abort_oscillation"


class Policy:
    def __init__(self, epsilon: float = 5.0, threshold: float = 0.85, convergence_window: int = 2):
        self.epsilon = epsilon
        self.threshold = threshold
        self.convergence_window = convergence_window

    def evaluate(self, state: DVOCState) -> Decision:
        if not state.snapshots:
            return Decision.REFINE

        last_errors = [s.error_vector for s in state.snapshots]
        last_confs = [s.confidence for s in state.snapshots]
        last_mags = [e.magnitude for e in last_errors]

        if len(last_errors) >= 3:
            recent_mags = last_mags[-3:]
            if recent_mags[0] <= recent_mags[1] <= recent_mags[2]:
                return Decision.ABORT_OSCILLATION

        if len(last_errors) >= self.convergence_window:
            recent_stuck = all(m == 0.0 and c == 0.0 for m, c in zip(last_mags[-self.convergence_window:], last_confs[-self.convergence_window:]))
            if recent_stuck:
                return Decision.ABORT_OSCILLATION

        recent = list(zip(last_errors[-self.convergence_window:], last_confs[-self.convergence_window:]))
        if len(recent) == self.convergence_window:
            if all(e.magnitude < self.epsilon and c >= self.threshold for e, c in recent):
                return Decision.ACT_SAFE

        return Decision.REFINE
