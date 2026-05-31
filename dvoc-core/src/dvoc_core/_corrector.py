from dvoc_core._types import Point, Vector


class Corrector:
    def __init__(self, epsilon: float = 5.0, threshold: float = 0.85,
                 alpha_schedule: str = "default"):
        self.epsilon = epsilon
        self.threshold = threshold
        self.alpha_schedule = alpha_schedule

    def correct(self, current: Point, error: Vector, iteration: int) -> Point:
        alpha = self._alpha(iteration)
        return Point(
            x=current.x + alpha * error.dx,
            y=current.y + alpha * error.dy,
        )

    def _alpha(self, iteration: int) -> float:
        if self.alpha_schedule == "constant05":
            return 0.5
        if self.alpha_schedule == "undamped":
            return 1.0
        # default: 1.0 -> 0.5 -> 0.25
        if iteration == 0:
            return 1.0
        if iteration == 1:
            return 0.5
        return 0.25

    def is_converged(self, error: Vector, confidence: float) -> bool:
        return error.magnitude < self.epsilon and confidence >= self.threshold
