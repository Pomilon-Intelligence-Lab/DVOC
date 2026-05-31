"""Backend for Wayland compositors (wlroots/Hyprland/Sway).

Capture via grim. Input via ydotool (generic), with fallbacks for Hyprland.
"""
import os, subprocess, tempfile
from PIL import Image
from dvoc_core import DVOCBackend, Action, ActionResult, Geometry


def _which(*cmds: str) -> str | None:
    for cmd in cmds:
        r = subprocess.run(["which", cmd], capture_output=True)
        if r.returncode == 0:
            return cmd
    return None


def _check_env(*vars: str) -> str | None:
    for v in vars:
        val = os.environ.get(v)
        if val:
            return v
    return None


class WaylandBackend(DVOCBackend):
    def __init__(self):
        self._grim = _which("grim")
        if not self._grim:
            raise RuntimeError(
                "Wayland backend requires 'grim' for screen capture. "
                "Install: sudo apt install grim | pacman -S grim"
            )

        self._slurp = _which("slurp")
        self._geometry: Geometry | None = None

        input_tools = []
        self._ydotool = _which("ydotool")
        if self._ydotool:
            input_tools.append(f"ydotool ({self._ydotool})")

        self._hyprctl = None
        if _check_env("HYPRLAND_INSTANCE_SIGNATURE"):
            h = _which("hyprctl")
            if h:
                r = subprocess.run(
                    [h, "dispatch", "movecursor", "0 0"],
                    capture_output=True, text=True,
                )
                if r.returncode == 0 and not r.stdout.strip() and not r.stderr.strip():
                    self._hyprctl = h

        if self._hyprctl:
            input_tools.append(f"hyprctl ({self._hyprctl})")

        self._wtype = _which("wtype")

        if not input_tools:
            import warnings
            warnings.warn(
                "No input tool found — mouse/keyboard actions will fail. "
                "Install ydotool: sudo apt install ydotool | pacman -S ydotool"
            )

    # ── helpers ──────────────────────────────────────────

    def _run(self, *args, **kwargs):
        r = subprocess.run(*args, capture_output=True, text=True, **kwargs)
        if r.returncode != 0 or r.stderr.strip():
            raise subprocess.CalledProcessError(
                r.returncode, args[0] if args else [],
                output=r.stdout, stderr=r.stderr,
            )
        return r

    def _mouse_to(self, x: int, y: int) -> None:
        if self._ydotool:
            self._run([self._ydotool, "mousemove", "--", str(x), str(y)])
        elif self._hyprctl:
            self._run([self._hyprctl, "dispatch", "movecursor", f"{x} {y}"])

    def _click(self, btn: str = "1") -> None:
        if self._ydotool:
            self._run([self._ydotool, "click", btn])
        elif self._hyprctl:
            self._run([self._hyprctl, "dispatch", "click", btn])

    def _scroll(self, direction: str, times: int = 1) -> None:
        if self._ydotool:
            for _ in range(times):
                self._run([self._ydotool, "click", direction])
        elif self._hyprctl:
            self._run([self._hyprctl, "dispatch", "scroll", direction])

    # ── DVOCBackend interface ────────────────────────────

    def capture(self) -> Image.Image:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            subprocess.run([self._grim, path], check=True, capture_output=True)
            return Image.open(path).copy()
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def execute(self, action: Action) -> ActionResult:
        try:
            if action.type == "click":
                self._mouse_to(int(action.target.x), int(action.target.y))
                self._click()
                return ActionResult(success=True)

            elif action.type == "type":
                if not self._wtype:
                    return ActionResult(success=False, error="wtype not available for text input")
                subprocess.run([self._wtype, action.text or ""], check=True)
                return ActionResult(success=True)

            elif action.type == "keypress":
                if not self._wtype:
                    return ActionResult(success=False, error="wtype not available for key input")
                key = action.key or ""
                subprocess.run([self._wtype, "-k", key], check=True)
                return ActionResult(success=True)

            elif action.type == "scroll":
                dy = action.scroll_dy or 0
                self._scroll("up" if dy < 0 else "down", abs(dy))
                return ActionResult(success=True)

            else:
                return ActionResult(success=False, error=f"unknown action type: {action.type}")

        except subprocess.CalledProcessError as e:
            return ActionResult(success=False, error=str(e))
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def get_screen_geometry(self) -> Geometry:
        if self._geometry:
            return self._geometry
        img = self.capture()
        self._geometry = Geometry(width=img.width, height=img.height)
        return self._geometry
