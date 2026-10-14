"""Draw the Home Screen icon: a sunrise whose reflections double as sound waves."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def make_icons(out: Path) -> None:
    S = 1024
    img = Image.new("RGB", (S, S))
    top, bot = (0x24, 0x31, 0x3B), (0x12, 0x18, 0x1D)
    d = ImageDraw.Draw(img)
    for y in range(S):
        t = y / (S - 1)
        d.line([(0, y), (S, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bot)))
    hz = 590                                    # horizon
    # sun: glow, then disc, clipped at the horizon
    glow = Image.new("L", (S, S), 0)
    gd = ImageDraw.Draw(glow)
    for r, a in ((330, 40), (290, 70)):
        gd.ellipse([S/2 - r, hz - r, S/2 + r, hz + r], fill=a)
    gd.rectangle([0, hz, S, S], fill=0)
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    ImageDraw.Draw(glow).rectangle([0, hz, S, S], fill=0)
    img.paste((0xE8, 0xA5, 0x4B), (0, 0), glow)
    sun = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sun).ellipse([S/2 - 230, hz - 230, S/2 + 230, hz + 230], fill=255)
    ImageDraw.Draw(sun).rectangle([0, hz - 6, S, S], fill=0)
    img.paste((0xF0, 0xB2, 0x5A), (0, 0), sun)
    d = ImageDraw.Draw(img)
    # horizon and reflections, which double as sound waves
    def bar(y, half, w, color):
        d.rounded_rectangle([S/2 - half, y - w/2, S/2 + half, y + w/2], radius=w/2, fill=color)
    bar(hz, 330, 30, (0xE4, 0xE8, 0xEA))
    bar(hz + 92, 230, 24, (0xB8, 0x86, 0x45))
    bar(hz + 170, 140, 22, (0x8A, 0x6A, 0x3E))
    bar(hz + 238, 60, 20, (0x5E, 0x4E, 0x36))
    img.resize((1400, 1400), Image.LANCZOS).save(out / "podcast-cover.png", optimize=True)
    for size, name in ((512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png"),
                       (32, "favicon-32.png")):
        img.resize((size, size), Image.LANCZOS).save(out / name, optimize=True)
