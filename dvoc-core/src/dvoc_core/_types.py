from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Vector:
    dx: float
    dy: float

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.dx ** 2 + self.dy ** 2)


@dataclass(frozen=True)
class Geometry:
    width: int
    height: int


@dataclass(frozen=True)
class Action:
    type: str
    target: Point | None = None
    text: str | None = None
    key: str | None = None
    scroll_dx: int = 0
    scroll_dy: int = 0


@dataclass(frozen=True)
class ActionResult:
    success: bool
    error: str | None = None
