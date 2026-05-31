from dataclasses import dataclass, field
from io import BytesIO
from PIL import Image
from dvoc_core._types import Point, Vector


@dataclass(frozen=True)
class DVOCSnapshot:
    iteration: int
    draft_point: Point
    error_vector: Vector
    confidence: float
    _frame_data: bytes = field(repr=False)

    def __init__(
        self,
        iteration: int,
        draft_point: Point,
        annotated_frame: Image.Image,
        error_vector: Vector,
        confidence: float,
    ):
        buf = BytesIO()
        annotated_frame.save(buf, format="PNG")
        object.__setattr__(self, "iteration", iteration)
        object.__setattr__(self, "draft_point", draft_point)
        object.__setattr__(self, "error_vector", error_vector)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "_frame_data", buf.getvalue())

    @property
    def annotated_frame(self) -> Image.Image:
        return Image.open(BytesIO(self._frame_data))


@dataclass(frozen=True)
class DVOCState:
    task: str
    snapshots: tuple[DVOCSnapshot, ...] = ()

    def push(self, snapshot: DVOCSnapshot) -> "DVOCState":
        corrected_snap = DVOCSnapshot(
            iteration=len(self.snapshots),
            draft_point=snapshot.draft_point,
            annotated_frame=snapshot.annotated_frame,
            error_vector=snapshot.error_vector,
            confidence=snapshot.confidence,
        )
        return DVOCState(
            task=self.task,
            snapshots=self.snapshots + (corrected_snap,),
        )

    @property
    def iteration(self) -> int:
        return len(self.snapshots)

    @property
    def current_draft(self) -> Point | None:
        if not self.snapshots:
            return None
        return self.snapshots[-1].draft_point
