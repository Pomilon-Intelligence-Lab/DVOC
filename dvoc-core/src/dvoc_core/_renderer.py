from PIL import Image, ImageDraw, ImageFont
from dvoc_core._types import Point


class Renderer:
    def __init__(self, overlay_mode: str = "full"):
        self.overlay_mode = overlay_mode
        self.crosshair_color = (255, 0, 0)
        self.crosshair_arm = 15
        self.crosshair_width = 3
        self.circle_color = (0, 100, 255)
        self.circle_width = 3
        self.text_bg = (0, 0, 0)
        self.text_fg = (255, 255, 255)
        self.font = ImageFont.load_default()

    def overlay(self, frame: Image.Image, draft: Point, radius: float, iteration: int = 0) -> Image.Image:
        if self.overlay_mode == "none":
            return frame.copy()

        img = frame.copy()
        draw = ImageDraw.Draw(img)
        cx, cy = int(draft.x), int(draft.y)

        if self.overlay_mode in ("full", "crosshair-only"):
            arm = self.crosshair_arm
            draw.line([(cx - arm, cy), (cx + arm, cy)], fill=self.crosshair_color, width=self.crosshair_width)
            draw.line([(cx, cy - arm), (cx, cy + arm)], fill=self.crosshair_color, width=self.crosshair_width)

        if self.overlay_mode == "full":
            r = int(max(10, radius))
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                outline=self.circle_color,
                width=self.circle_width,
            )

        w, h = img.size

        iter_label = f"iter {iteration}"
        ibbox = draw.textbbox((0, 0), iter_label, font=self.font)
        iw = ibbox[2] - ibbox[0]
        ih = ibbox[3] - ibbox[1]
        draw.rectangle([(8, 8), (12 + iw, 12 + ih)], fill=self.text_bg)
        draw.text((10, 10), iter_label, fill=self.text_fg, font=self.font)

        label = f"({cx}, {cy}) +/- {int(max(10, radius))}px"
        lbbox = draw.textbbox((0, 0), label, font=self.font)
        lw = lbbox[2] - lbbox[0]
        lh = lbbox[3] - lbbox[1]
        draw.rectangle([(w - lw - 12, h - lh - 12), (w - 8, h - 8)], fill=self.text_bg)
        draw.text((w - lw - 10, h - lh - 10), label, fill=self.text_fg, font=self.font)

        return img
