"""Synthetic task generators.

Each task creates a PIL Image and returns metadata including the target center.
Element dimensions are provided for hit-test based success evaluation.
"""

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def _font(size=14):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except (OSError, IOError):
        return ImageFont.load_default()


@dataclass
class SynthTask:
    id: str
    name: str
    prompt: str
    difficulty: str
    target: tuple[int, int]
    target_w: int
    target_h: int
    img: Image.Image


def _bg(w, h, color=(40, 42, 48)):
    return Image.new("RGB", (w, h), color=color)


def single_button() -> SynthTask:
    img = _bg(800, 600)
    d = ImageDraw.Draw(img)
    d.rectangle([360, 275, 440, 325], fill=(100, 200, 100), outline=(255, 255, 255), width=2)
    d.text((366, 290), "CLICK ME", fill=(255, 255, 255), font=_font(14))
    return SynthTask(id="S1", name="single-button", prompt="Click the CLICK ME button",
                     difficulty="easy", target=(400, 300), target_w=80, target_h=50, img=img)


def small_target() -> SynthTask:
    img = _bg(800, 600)
    d = ImageDraw.Draw(img)
    d.rectangle([388, 294, 412, 306], fill=(100, 200, 100), outline=(255, 255, 255), width=1)
    return SynthTask(id="S2", name="small-target", prompt="Click the small green button",
                     difficulty="medium", target=(400, 300), target_w=24, target_h=12, img=img)


def multi_button() -> SynthTask:
    img = _bg(800, 600)
    d = ImageDraw.Draw(img)
    buttons = [
        (100, 200, "Cancel"),
        (300, 200, "Submit"),
        (500, 200, "Delete"),
        (200, 350, "Save"),
    ]
    for bx, by, label in buttons:
        d.rectangle([bx, by, bx+120, by+40], fill=(80, 120, 200), outline=(200, 200, 200), width=2)
        d.text((bx+8, by+12), label, fill=(255, 255, 255), font=_font(14))
    return SynthTask(id="S3", name="multi-button", prompt="Click the button labeled 'Submit'",
                     difficulty="medium", target=(360, 220), target_w=120, target_h=40, img=img)


def edge_target() -> SynthTask:
    img = _bg(800, 600)
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 70, 40], fill=(100, 200, 100), outline=(255, 255, 255), width=2)
    return SynthTask(id="S4", name="edge-target", prompt="Click the button in the top-left corner",
                     difficulty="hard", target=(40, 25), target_w=60, target_h=30, img=img)


def input_field() -> SynthTask:
    img = _bg(800, 600)
    d = ImageDraw.Draw(img)
    d.text((200, 200), "Username:", fill=(180, 180, 180), font=_font(16))
    d.rectangle([200, 224, 450, 256], fill=(60, 62, 68), outline=(120, 120, 120), width=2)
    d.text((206, 230), "type here...", fill=(100, 100, 100), font=_font(14))
    return SynthTask(id="S5", name="input-field", prompt="Click inside the username input field",
                     difficulty="medium", target=(325, 240), target_w=250, target_h=32, img=img)


def distractors() -> SynthTask:
    img = _bg(800, 600)
    d = ImageDraw.Draw(img)
    positions = [(150, 200), (350, 200), (550, 200), (150, 350), (350, 350), (550, 350)]
    targets = [(100, 200, 100), (100, 200, 100), (200, 100, 100), (100, 100, 200), (100, 200, 100), (200, 200, 100)]
    for (x, y), (r, g, b) in zip(positions, targets):
        d.rectangle([x, y, x+80, y+40], fill=(r, g, b), outline=(255, 255, 255), width=2)
        d.text((x+8, y+12), "CLICK", fill=(255, 255, 255), font=_font(12))
    return SynthTask(id="S6", name="distractors", prompt="Click the BLUE button",
                     difficulty="hard", target=(190, 370), target_w=80, target_h=40, img=img)


ALL = [single_button, small_target, multi_button, edge_target, input_field, distractors]
