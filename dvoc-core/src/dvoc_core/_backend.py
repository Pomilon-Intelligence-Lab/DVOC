from abc import ABC, abstractmethod
from PIL import Image
from dvoc_core._types import Action, ActionResult, Geometry


class DVOCBackend(ABC):
    @abstractmethod
    def capture(self) -> Image.Image: ...

    @abstractmethod
    def execute(self, action: Action) -> ActionResult: ...

    @abstractmethod
    def get_screen_geometry(self) -> Geometry: ...
