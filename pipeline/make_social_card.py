#!/usr/bin/env python3
"""Compose src/img/social-card.png, the image shared links unfurl to.

1200x630 because that is what every scraper crops to. Built rather than
reusing a chapter illustration directly: the illustrations are 4:3, so a
scraper letterboxes them and the drawing ends up small and off-centre
with grey bars. Composing the card means the title is legible at the
size a link preview actually renders.

Colours are read from theme/custom.css so the card cannot drift from the
site. Fonts are not: IBM Plex is not installed here and is not bundled,
so this falls back to DejaVu Serif, which is close enough in a 1200px
image that nobody will write in about it.

    python3 pipeline/make_social_card.py
"""
import pathlib
import re

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = ROOT / "theme" / "custom.css"
ILLUS = ROOT / "src" / "img" / "illus-01-five-microseconds.png"
OUT = ROOT / "src" / "img" / "social-card.png"

W, H = 1200, 630
TITLE = "Deriving Systems"
SUB = "Performance engineering from first principles"
TAG = "Thirteen chapters. Nothing taken on authority."

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def css_var(name, fallback):
    m = re.search(rf"{name}:\s*(#[0-9a-fA-F]+)", CSS.read_text())
    return m.group(1) if m else fallback


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def roller(card, y, h, dark, wood, lite):
    """A wooden roller across the card, the same gradient as the site's
    main::before and main::after: dark, light at 35%, wood at 60%, dark."""
    stops = [(0.0, dark), (0.35, lite), (0.60, wood), (1.0, dark)]
    d = ImageDraw.Draw(card)
    for row in range(h):
        t = row / (h - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / (t1 - t0)
                c = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
                d.line([(0, y + row), (W, y + row)], fill=c)
                break


def main():
    # Since 2026-11-02 the site is a parchment scroll; the card follows.
    sheet = css_var("--sheet", "#f4e8c8")
    ink = css_var("--ink", "#2b2014")
    flag = css_var("--flag", "#a81e4d")
    muted = css_var("--muted", "#6b5843")
    wood = [hex_rgb(css_var(v, f)) for v, f in
            (("--wood-dark", "#5a3a1c"), ("--wood", "#9a6a3a"), ("--wood-lite", "#c99a62"))]
    paper = sheet

    card = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(card)

    # The illustration bleeds off the right edge. Cropping it rather than
    # fitting it keeps the linework at a readable scale; a whole 4:3
    # drawing shrunk into half a card reads as a smudge.
    if ILLUS.exists():
        art = Image.open(ILLUS).convert("RGB")
        scale = H / art.height
        art = art.resize((int(art.width * scale), H), Image.LANCZOS)
        # The drawing's paper is near-white. Lift it to pure white, then
        # multiply it onto the sheet, as the site does with CSS: white
        # becomes parchment and the ink stays ink.
        art = ImageEnhance.Brightness(art).enhance(1.05)
        region = (W - art.width + 130, 0)
        under = card.crop((region[0], 0, region[0] + art.width, H))
        card.paste(ImageChops.multiply(under, art), region)
        # Fade it into the paper so the title has somewhere quiet to sit.
        # The solid stop is past the end of the wordmark on purpose: with
        # it any earlier, the tail of "Systems" lands on the spilled mail
        # and the one thing that has to be legible is the one thing that
        # is not.
        veil = Image.new("L", (W, H), 0)
        vd = ImageDraw.Draw(veil)
        for x in range(660, 980):
            vd.line([(x, 0), (x, H)], fill=int(255 * (1 - (x - 660) / 320)))
        vd.rectangle([0, 0, 660, H], fill=255)
        card.paste(Image.new("RGB", (W, H), paper), (0, 0), veil)

    roller(card, 0, 26, *wood)
    roller(card, H - 26, 26, *wood)

    t = ImageFont.truetype(SERIF_B, 76)
    s = ImageFont.truetype(SERIF, 30)
    g = ImageFont.truetype(SERIF, 25)

    d.text((72, 196), TITLE, font=t, fill=ink)
    d.rectangle([74, 300, 74 + 96, 303], fill=flag)
    d.text((72, 336), SUB, font=s, fill=ink)
    d.text((72, 386), TAG, font=g, fill=muted)
    d.text((72, H - 96), "derivingsystems.com", font=g, fill=flag)

    card.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size // 1024} KB  {W}x{H}")


if __name__ == "__main__":
    main()
