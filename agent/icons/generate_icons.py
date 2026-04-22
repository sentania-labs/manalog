"""Generate mana pip tray icons and MSI identity icon for Manalog.

Produces 8 ICO files in this directory:
  W.ico / U.ico / B.ico / R.ico / G.ico / C.ico / M_idle.ico  (16x16 + 32x32)
  rainbow_pentagon.ico                                        (48x48 + 256x256)

All artwork is simple geometric primitives drawn with Pillow — clean,
recognizable-at-16px pips inspired by MTG mana symbols but not derived
from WotC art. Re-run this script to regenerate the .ico files.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = Path(__file__).resolve().parent
BASE = 512  # high-resolution render size; PIL downsamples to ICO frames

PIP_SIZES = [16, 32]
PENTAGON_SIZES = [48, 256]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]


def load_bold_font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def new_canvas() -> Image.Image:
    return Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))


def draw_pip_disc(img: Image.Image, bg: str, border: str) -> None:
    """Fill a circle that nearly fills the canvas, with a border ring."""
    draw = ImageDraw.Draw(img)
    pad = 12
    draw.ellipse([pad, pad, BASE - pad, BASE - pad], fill=border)
    ring = 40  # ~2px at 16x16 after LANCZOS
    draw.ellipse(
        [pad + ring, pad + ring, BASE - pad - ring, BASE - pad - ring],
        fill=bg,
    )


def symbol_white(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    gold = "#C8A020"
    cx = cy = BASE // 2
    outer = 170
    hub = 55
    for i in range(8):
        angle = i * (math.pi / 4)
        x = cx + math.cos(angle) * outer
        y = cy + math.sin(angle) * outer
        draw.line([(cx, cy), (x, y)], fill=gold, width=32)
    draw.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=gold)


def symbol_blue(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    color = "#7EC8E3"
    cx = BASE // 2
    top_y = BASE // 2 - 150
    shoulder_y = BASE // 2 + 30
    r = 115
    # Round bottom bulb
    draw.ellipse([cx - r, shoulder_y - r + 30, cx + r, shoulder_y + r + 30], fill=color)
    # Pointed top (triangle closing into the bulb)
    draw.polygon(
        [
            (cx, top_y),
            (cx - r, shoulder_y + 30),
            (cx + r, shoulder_y + 30),
        ],
        fill=color,
    )


def symbol_black(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    skull = "#A0A0A0"
    cx = BASE // 2
    cy = BASE // 2
    r = 140
    # Skull dome
    draw.ellipse([cx - r, cy - r + 20, cx + r, cy + r + 20], fill=skull)
    # Eye sockets (punch dark holes)
    eye_r = 34
    offset_x = 55
    eye_y = cy - 10
    hole = "#150B00"
    draw.ellipse(
        [cx - offset_x - eye_r, eye_y - eye_r, cx - offset_x + eye_r, eye_y + eye_r],
        fill=hole,
    )
    draw.ellipse(
        [cx + offset_x - eye_r, eye_y - eye_r, cx + offset_x + eye_r, eye_y + eye_r],
        fill=hole,
    )


def symbol_red(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    flame = "#FF8C00"
    cx = BASE // 2
    cy = BASE // 2
    points = [
        (cx, cy - 170),           # tip
        (cx + 85, cy - 30),       # right curl
        (cx + 45, cy + 30),       # right dip
        (cx + 115, cy + 150),     # right base
        (cx, cy + 120),           # bottom notch
        (cx - 115, cy + 150),     # left base
        (cx - 45, cy + 30),       # left dip
        (cx - 85, cy - 30),       # left curl
    ]
    draw.polygon(points, fill=flame)


def symbol_green(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    leaf = "#90EE90"
    vein = "#00733E"
    cx = BASE // 2
    cy = BASE // 2
    top_y = cy - 160
    bot_y = cy + 160
    width = 110
    # Lens/leaf shape via sine-curve outline
    pts = []
    steps = 24
    for t in range(steps + 1):
        u = t / steps
        y = top_y + u * (bot_y - top_y)
        w = math.sin(u * math.pi) * width
        pts.append((cx + w, y))
    for t in range(steps, -1, -1):
        u = t / steps
        y = top_y + u * (bot_y - top_y)
        w = math.sin(u * math.pi) * width
        pts.append((cx - w, y))
    draw.polygon(pts, fill=leaf)
    draw.line([(cx, top_y + 15), (cx, bot_y - 15)], fill=vein, width=12)


def symbol_colorless(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    diamond = "#E8E8E8"
    edge = "#808080"
    cx = BASE // 2
    cy = BASE // 2
    r = 140
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(pts, fill=diamond)
    draw.line(pts + [pts[0]], fill=edge, width=6)


def symbol_m(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    gold = "#FFD700"
    font = load_bold_font(340)
    text = "M"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (BASE - tw) // 2 - bbox[0]
    ty = (BASE - th) // 2 - bbox[1]
    draw.text((tx, ty), text, fill=gold, font=font)


def save_ico(img: Image.Image, filename: str, sizes: list[int]) -> Path:
    path = ICONS_DIR / filename
    img.save(path, format="ICO", sizes=[(s, s) for s in sizes])
    return path


def make_pip(name: str, bg: str, border: str, symbol_fn) -> Path:
    img = new_canvas()
    draw_pip_disc(img, bg, border)
    symbol_fn(img)
    return save_ico(img, f"{name}.ico", PIP_SIZES)


def make_rainbow_pentagon() -> Path:
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    cx = cy = BASE // 2
    r = 240
    # WUBRG clockwise from top
    wedge_colors = ["#F9FAF4", "#0E68AB", "#150B00", "#D3202A", "#00733E"]
    pentagon_pts = []
    for i in range(5):
        angle = -math.pi / 2 + i * (2 * math.pi / 5)
        pentagon_pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    for i, color in enumerate(wedge_colors):
        p1 = pentagon_pts[i]
        p2 = pentagon_pts[(i + 1) % 5]
        draw.polygon([(cx, cy), p1, p2], fill=color)
    # Subtle outline for the pentagon so the white (W) wedge is visible on light bg
    draw.polygon(pentagon_pts + [pentagon_pts[0]], outline="#333333", width=5)
    # Center colorless hub
    hub_r = 55
    draw.ellipse([cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r], fill="#BFBFBF")
    draw.ellipse(
        [cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r],
        outline="#808080",
        width=5,
    )
    return save_ico(img, "rainbow_pentagon.ico", PENTAGON_SIZES)


def main() -> None:
    produced: list[Path] = []
    produced.append(make_pip("W", "#F9FAF4", "#C8A020", symbol_white))
    produced.append(make_pip("U", "#0E68AB", "#3D8EC9", symbol_blue))
    produced.append(make_pip("B", "#150B00", "#4A4A4A", symbol_black))
    produced.append(make_pip("R", "#D3202A", "#FF6B00", symbol_red))
    produced.append(make_pip("G", "#00733E", "#4CAF50", symbol_green))
    produced.append(make_pip("C", "#BFBFBF", "#808080", symbol_colorless))
    produced.append(make_pip("M_idle", "#1A1A2E", "#FFD700", symbol_m))
    produced.append(make_rainbow_pentagon())
    for p in produced:
        print(f"  wrote {p.relative_to(ICONS_DIR.parent.parent)}")
    print(f"generated {len(produced)} icons")


if __name__ == "__main__":
    main()
