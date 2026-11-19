#!/usr/bin/env python3
"""Make small, fast-loading copies of the large pictures on the site.

For every source picture this writes WebP copies at several widths into
images/_opt/, for example

    images/research-program.png  ->  images/_opt/research-program-800.webp
                                     images/_opt/research-program-1200.webp
                                     images/_opt/research-program-1600.webp
                                     images/_opt/research-program-2400.webp

The pages list these copies in the <img srcset="..."> attribute, so the
browser downloads and decodes only the size it actually needs for the
screen it is on.  The original file stays untouched and is still what
"Open full size" links to, so nothing is lost.

Usage (from the site folder):

    python3 scripts/optimize_images.py              # all pictures listed below
    python3 scripts/optimize_images.py images/x.png # just one picture

Needs the Pillow library (pip install Pillow).  If Pillow is missing the
script says so and does nothing else.
"""
import os
import sys

try:
    from PIL import Image, features
except ImportError:  # pragma: no cover - friendly message for the Mac
    sys.exit("Pillow is not installed.  Run:  python3 -m pip install Pillow   and try again.")

if not features.check("webp"):  # pragma: no cover
    sys.exit("This Pillow build cannot write WebP files.  Run:  python3 -m pip install --upgrade Pillow")

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(SITE, "images", "_opt")

# Widths offered to the browser.  2400 covers a 1200 px-wide figure on a
# 2x (Retina) display; nothing on the site is drawn wider than that.
WIDTHS = (800, 1200, 1600, 2400)
QUALITY = 84

# Pictures to process when no file is named on the command line.  A tuple
# (path, crop) where crop is None or a (left, top, right, bottom) box in
# source pixels applied before resizing.  The homepage banner is shown as a
# wide strip (CSS object-fit: cover, object-position 50% 45%), so only the
# band that can ever be visible is kept: 2000 x 800 around the 45 % line.
DEFAULT = [
    ("images/glioma-multiplex.jpg", (0, 540, 2000, 1340), WIDTHS),
    ("images/research-program.png", None, WIDTHS),
    ("images/programs/pediatric-brain-tumours.png", None, WIDTHS),
    ("images/programs/brain-heart.png", None, WIDTHS),
    ("images/programs/lung-development.png", None, WIDTHS),
    # Footer logo: shown about 235 px wide, so 480 (2x) and 720 (3x) are plenty.
    ("images/logos/cheo-ri.png", None, (480, 720)),
]
# Journal covers on the Publications page: shown 84 px wide, so 180 (2x) and 360 (4x).
import glob as _glob
DEFAULT += [(os.path.relpath(f, SITE), None, (180, 360))
            for f in sorted(_glob.glob(os.path.join(SITE, "images", "covers", "*.jpg")))]


def variants_for(rel, crop=None, widths=WIDTHS):
    src = os.path.join(SITE, rel)
    stem = os.path.splitext(os.path.basename(rel))[0]
    im = Image.open(src)
    im.load()
    if crop:
        im = im.crop(crop)
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if has_alpha else "RGB")
    w, h = im.size
    os.makedirs(OUT_DIR, exist_ok=True)
    made = []
    for tw in widths:
        if tw > w:
            break
        th = max(1, round(h * tw / w))
        small = im if tw == w else im.resize((tw, th), Image.LANCZOS)
        out = os.path.join(OUT_DIR, "%s-%d.webp" % (stem, tw))
        small.save(out, "WEBP", quality=QUALITY, method=6)
        made.append((out, tw, th, os.path.getsize(out)))
    # Also offer the picture at its own width when that is below the largest step.
    if w < widths[-1] and w not in widths:
        out = os.path.join(OUT_DIR, "%s-%d.webp" % (stem, w))
        im.save(out, "WEBP", quality=QUALITY, method=6)
        made.append((out, w, h, os.path.getsize(out)))
    return made


def main(argv):
    jobs = DEFAULT if not argv else [(a, None, WIDTHS) for a in argv]
    for rel, crop, widths in jobs:
        rel = os.path.relpath(os.path.join(SITE, rel), SITE) if os.path.isabs(rel) else rel
        if not os.path.exists(os.path.join(SITE, rel)):
            print("skip (not found):", rel)
            continue
        made = variants_for(rel, crop, widths)
        print(rel)
        for out, tw, th, size in made:
            print("   %-52s %5d x %-5d %6.0f KB" % (os.path.relpath(out, SITE), tw, th, size / 1024))
        print("   srcset:", ", ".join("images/_opt/%s %dw" % (os.path.basename(o), tw) for o, tw, _, _ in made))


if __name__ == "__main__":
    main(sys.argv[1:])
