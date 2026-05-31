from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright, Page, Browser
from dvoc_core import DVOCBackend, Point, Action, ActionResult, Geometry


class WebBackend(DVOCBackend):
    def __init__(self, headless: bool = True, viewport: dict | None = None):
        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._headless = headless
        self._viewport = viewport or {"width": 1280, "height": 720}
        self._owns_browser = True

    def start(self, page: Page | None = None):
        if page is not None:
            self._page = page
            self._owns_browser = False
        else:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            ctx = self._browser.new_context(viewport=self._viewport)
            self._page = ctx.new_page()

    def stop(self):
        if self._owns_browser:
            if self._page and not self._page.is_closed():
                try:
                    self._page.close()
                except Exception:
                    pass
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass

    def goto(self, url: str, wait_until: str = "networkidle"):
        if self._page is None:
            raise RuntimeError("WebBackend not started. Call start() first.")
        self._page.goto(url, wait_until=wait_until)

    @property
    def page(self) -> Page | None:
        return self._page

    def capture(self) -> Image.Image:
        if self._page is None:
            raise RuntimeError("WebBackend not started. Call start() first.")
        screenshot_bytes = self._page.screenshot(type="png")
        return Image.open(BytesIO(screenshot_bytes))

    def execute(self, action: Action) -> ActionResult:
        if self._page is None:
            return ActionResult(success=False, error="WebBackend not started")
        try:
            if action.type == "click":
                vp = self._page.viewport_size
                self._page.mouse.click(int(action.target.x), int(action.target.y))
                return ActionResult(success=True)
            elif action.type == "type":
                self._page.keyboard.type(action.text or "")
                return ActionResult(success=True)
            elif action.type == "keypress":
                self._page.keyboard.press(action.key)
                return ActionResult(success=True)
            elif action.type == "scroll":
                self._page.evaluate(f"window.scrollBy(0, {action.scroll_dy})")
                return ActionResult(success=True)
            else:
                return ActionResult(success=False, error=f"unknown action type: {action.type}")
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def get_screen_geometry(self) -> Geometry:
        if self._page is None:
            raise RuntimeError("WebBackend not started. Call start() first.")
        vp = self._page.viewport_size
        return Geometry(width=vp["width"], height=vp["height"])
