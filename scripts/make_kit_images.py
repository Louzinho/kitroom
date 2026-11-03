"""Draws the catalogue's shirt illustrations locally (no photos, no crests, no network)."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "uploads" / "products"
S = 4  # supersampling for clean edges
W, H = 800 * S, 800 * S


def pts(*coords):
    return [(x * S, y * S) for x, y in coords]


BODY = pts((285, 150), (515, 150), (525, 640), (275, 640))
SLEEVE_L = pts((285, 150), (130, 235), (190, 345), (280, 290))
SLEEVE_R = pts((515, 150), (670, 235), (610, 345), (520, 290))
SHIRT = pts((340, 130), (285, 150), (130, 235), (190, 345), (280, 290), (275, 640), (525, 640),
            (520, 290), (610, 345), (670, 235), (515, 150), (460, 130), (400, 165))


def pattern(kind, a, b):
    img = Image.new("RGB", (W, H), a)
    d = ImageDraw.Draw(img)
    if kind == "stripes":
        for x in range(140, 680, 90):
            d.rectangle((x * S, 0, (x + 45) * S, H), fill=b)
    elif kind == "hoops":
        for y in range(120, 660, 90):
            d.rectangle((0, y * S, W, (y + 45) * S), fill=b)
    elif kind == "halves":
        d.rectangle((400 * S, 0, W, H), fill=b)
    elif kind == "sash":
        d.polygon(pts((240, 640), (330, 640), (560, 130), (470, 130)), fill=b)
    elif kind == "band":
        d.rectangle((0, 300 * S, W, 390 * S), fill=b)
    elif kind == "chevron":
        d.polygon(pts((270, 250), (400, 370), (530, 250), (530, 330), (400, 450), (270, 330)), fill=b)
    return img


def draw_shirt(name, kind, a, b, trim):
    fill = pattern(kind, a, b)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(SHIRT, fill=255)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # soft fold shading on the body
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.polygon(pts((285, 290), (300, 640), (275, 640)), fill=(0, 0, 0, 40))
    sd.polygon(pts((515, 290), (500, 640), (525, 640)), fill=(0, 0, 0, 40))
    canvas.paste(fill, (0, 0), mask)
    canvas = Image.alpha_composite(canvas, shade)
    d = ImageDraw.Draw(canvas)
    d.line(pts((285, 150), (280, 290)), fill=(0, 0, 0, 70), width=3 * S)
    d.line(pts((515, 150), (520, 290)), fill=(0, 0, 0, 70), width=3 * S)
    # cuffs and collar
    d.line(pts((130, 235), (190, 345)), fill=trim, width=16 * S)
    d.line(pts((670, 235), (610, 345)), fill=trim, width=16 * S)
    d.line(pts((340, 130), (400, 165), (460, 130)), fill=trim, width=16 * S, joint="curve")
    # back of the neck
    d.polygon(pts((340, 130), (400, 165), (460, 130), (400, 118)), fill=(0, 0, 0, 90))
    canvas.resize((800, 800), Image.LANCZOS).save(OUT / f"{name}.png", optimize=True)


KITS = {
    "kit-01": ("stripes", "#ffffff", "#0b2e8a", "#0b2e8a"),
    "kit-02": ("stripes", "#000000", "#1457c8", "#000000"),
    "kit-03": ("stripes", "#c8102e", "#101010", "#101010"),
    "kit-04": ("hoops", "#0a7a3d", "#ffffff", "#0a7a3d"),
    "kit-05": ("sash", "#ffffff", "#d01d2c", "#d01d2c"),
    "kit-06": ("solid", "#6cabdd", "#6cabdd", "#ffffff"),
    "kit-07": ("solid", "#c8102e", "#c8102e", "#ffffff"),
    "kit-08": ("halves", "#a50044", "#004d98", "#edbb00"),
    "kit-09": ("solid", "#f7f7f2", "#f7f7f2", "#2b2b6e"),
    "kit-10": ("band", "#ffffff", "#7a1fa2", "#7a1fa2"),
    "kit-11": ("stripes", "#ffffff", "#101010", "#101010"),
    "kit-12": ("solid", "#034694", "#034694", "#ffffff"),
    "kit-13": ("solid", "#f4c20d", "#f4c20d", "#0a7a3d"),
    "kit-14": ("chevron", "#f26a1b", "#ffffff", "#ffffff"),
    "kit-15": ("solid", "#fbe122", "#fbe122", "#101010"),
    "kit-16": ("stripes", "#ffffff", "#e30613", "#e30613"),
    "kit-17": ("sash", "#16335b", "#ffffff", "#ffffff"),
    "kit-18": ("solid", "#002654", "#002654", "#ed2939"),
    "kit-19": ("halves", "#7a263a", "#1b458f", "#ffffff"),
    "kit-20": ("hoops", "#0e7c86", "#ffffff", "#ffffff"),
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in KITS.items():
        draw_shirt(name, *spec)
    print(len(KITS), "shirts drawn in", OUT)
