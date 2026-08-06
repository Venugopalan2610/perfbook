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

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = ROOT / "theme" / "custom.css"
ILLUS = ROOT / "src" / "img" / "illus-01-five-microseconds.png"
OUT = ROOT / "src" / "img" / "social-card.png"

W, H = 1200, 630
TITLE = "Deriving Systems"
SUB = "Performance engineering from first principles"
TAG = "Twelve chapters. Nothing looked up."

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def css_var(name, fallback):
    m = re.search(rf"{name}:\s*(#[0-9a-fA-F]+)", CSS.read_text())
    return m.group(1) if m else fallback


def main():
    paper = css_var("--paper", "#f7f8fa")
    ink = css_var("--ink", "#14181f")
    flag = css_var("--flag", "#a81e4d")
    muted = css_var("--muted", "#5c6675")

    card = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(card)

    # The illustration bleeds off the right edge. Cropping it rather than
    # fitting it keeps the linework at a readable scale; a whole 4:3
    # drawing shrunk into half a card reads as a smudge.
    if ILLUS.exists():
        art = Image.open(ILLUS).convert("RGB")
        scale = H / art.height
        art = art.resize((int(art.width * scale), H), Image.LANCZOS)
        card.paste(art, (W - art.width + 130, 0))
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

    d.rectangle([0, 0, W, 10], fill=flag)

    t = ImageFont.truetype(SERIF_B, 76)
    s = ImageFont.truetype(SERIF, 30)
    g = ImageFont.truetype(SERIF, 25)

    d.text((72, 196), TITLE, font=t, fill=ink)
    d.rectangle([74, 300, 74 + 96, 303], fill=flag)
    d.text((72, 336), SUB, font=s, fill=ink)
    d.text((72, 386), TAG, font=g, fill=muted)
    d.text((72, H - 78), "derivingsystems.com", font=g, fill=flag)

    card.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size // 1024} KB  {W}x{H}")


if __name__ == "__main__":
    main()
