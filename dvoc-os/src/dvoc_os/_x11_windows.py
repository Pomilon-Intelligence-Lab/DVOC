"""Backend for X11 and Windows (mss + pynput).

mss and pynput are only imported when this backend is instantiated,
so Wayland-only installs don't need them.
"""
from PIL import Image
from dvoc_core import DVOCBackend, Point, Action, ActionResult, Geometry


class MSSBackend(DVOCBackend):
    def __init__(self):
        import mss
        from pynput.mouse import Controller as MouseController
        from pynput.keyboard import Controller as KeyboardController, Key
        self._mss = mss
        self.screen = mss.MSS()
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self._Key = Key

    def capture(self) -> Image.Image:
        monitor = self.screen.monitors[0]
        sct_img = self.screen.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.rgb)

    def execute(self, action: Action) -> ActionResult:
        try:
            if action.type == "click":
                self.mouse.position = (int(action.target.x), int(action.target.y))
                self.mouse.click()
                return ActionResult(success=True)
            elif action.type == "type":
                self.keyboard.type(action.text or "")
                return ActionResult(success=True)
            elif action.type == "keypress":
                key = getattr(self._Key, action.key, None) or action.key
                self.keyboard.press(key)
                self.keyboard.release(key)
                return ActionResult(success=True)
            elif action.type == "scroll":
                self.mouse.scroll(0, action.scroll_dy)
                return ActionResult(success=True)
            else:
                return ActionResult(success=False, error=f"unknown action type: {action.type}")
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def get_screen_geometry(self) -> Geometry:
        monitor = self.screen.monitors[0]
        return Geometry(width=monitor["width"], height=monitor["height"])
