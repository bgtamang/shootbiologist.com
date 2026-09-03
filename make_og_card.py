"""
Build the 1200x630 social-share card (og-card.jpg) from the canopy figure.

Link previews on X/LinkedIn/Slack want a 1.91:1 image. The source figure is a
2x2 panel at 1600x1297, so this crops the top row -- the two canopy-assimilation
panels with their leaf-shape headers, which is the single most legible part of
the figure at thumbnail size -- and letterboxes it onto the site's paper colour.

Re-run after replacing the source figure:
    python make_og_card.py

Requires: Pillow
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "images" / "research" / "canopy_broad_vs_narrow_1600w.png"
OUT = ROOT / "og-card.jpg"

CARD_W, CARD_H = 1200, 630
PAPER = (250, 249, 247)  # --color-paper

# Fraction of the source height occupied by the top row of panels.
# Tuned to clear the colour-bar tick labels at the bottom of those panels.
TOP_ROW_FRACTION = 0.556


def main() -> None:
    with Image.open(SOURCE) as im:
        im = im.convert("RGB")
        crop_h = round(im.height * TOP_ROW_FRACTION)
        top_row = im.crop((0, 0, im.width, crop_h))

    # Fit inside the card, preserving aspect
    scale = min(CARD_W / top_row.width, CARD_H / top_row.height)
    new_size = (round(top_row.width * scale), round(top_row.height * scale))
    top_row = top_row.resize(new_size, Image.LANCZOS)

    card = Image.new("RGB", (CARD_W, CARD_H), PAPER)
    card.paste(top_row, ((CARD_W - new_size[0]) // 2, (CARD_H - new_size[1]) // 2))
    card.save(OUT, "JPEG", quality=88, optimize=True, progressive=True)

    print(f"wrote {OUT.name}  {CARD_W}x{CARD_H}  {OUT.stat().st_size / 1024:.0f} KB")
    print(f"  source crop: {im.width}x{crop_h} -> {new_size[0]}x{new_size[1]}")


if __name__ == "__main__":
    main()
