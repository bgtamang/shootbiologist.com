"""
Optimize every raster image that index.html actually references.

Two things happen per image:
  1. The original is resized to at most MAX_WIDTH px and re-encoded in place
     (JPEG quality 82 progressive, PNG optimized). Filenames never change, so
     index.html paths stay valid whether or not the WebP step is wired up.
  2. A .webp sibling is written next to it, for <picture> sources.

The file list is parsed out of index.html rather than hardcoded, so adding a
new image to the page and re-running this script is all that is needed --
unreferenced files in images/ are never touched.

Idempotent: re-running on already-optimized files rewrites them only when the
new encode is actually smaller, so repeated runs do not degrade quality.

Usage:
    python optimize_images.py            # optimize in place
    python optimize_images.py --dry-run  # report only, change nothing

Requires: Pillow  (pip install Pillow)
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"

# Largest the page ever shows an image: the lightbox at ~95vw/95vh on a big display.
# Applied to the longest edge, so tall portraits get scaled down too.
MAX_EDGE = 1400
JPEG_QUALITY = 82
WEBP_QUALITY = 80

RASTER_SUFFIXES = {".jpg", ".jpeg", ".png"}
# Animated/vector/video assets are left alone.
SKIP_SUFFIXES = {".webp", ".gif", ".svg", ".mp4", ".pdf", ".tif", ".tiff"}

# Already hand-optimized, with a matching .webp maintained alongside it.
SKIP_FILES = {"headshot-optimized.jpg"}

# Filenames encode their width for a srcset; re-encode but never resize these.
NO_RESIZE_DIRS = {"images/research"}

# Video poster frames never open in the lightbox -- they only ever render at
# gallery-tile size, so they need far less resolution than everything else.
EDGE_OVERRIDES = {
    "uav_flythrough_SoyFACE_2024-08-02_poster.jpg": 800,
    "spydercam.jpg": 800,
}

# <video poster="..."> takes a single URL and cannot be wrapped in a <picture>,
# so a .webp sibling for one of these could never be served. Don't make them.
NO_WEBP_FILES = set(EDGE_OVERRIDES)

# src/href/poster/data-src hold one URL verbatim (which may contain spaces);
# srcset holds comma-separated "url descriptor" candidates. Parsed separately
# so a filename with a space is not truncated at the space.
SINGLE_URL_RE = re.compile(r'(?:src|href|poster|data-src)="([^"]+)"')
SRCSET_RE = re.compile(r'srcset="([^"]+)"')


def referenced_images() -> list[Path]:
    """Local raster images referenced by index.html, de-duplicated, in page order."""
    html = INDEX.read_text(encoding="utf-8")
    seen: dict[Path, None] = {}

    urls = list(SINGLE_URL_RE.findall(html))
    for raw in SRCSET_RE.findall(html):
        for candidate in raw.split(","):
            candidate = candidate.strip()
            if candidate:
                # strip a trailing "800w" / "2x" descriptor, if present
                urls.append(re.sub(r"\s+\d+(?:\.\d+)?[wx]$", "", candidate))

    for url in urls:
        url = url.strip()
        if not url or url.startswith(("http://", "https://", "data:", "mailto:", "#")):
            continue
        path = ROOT / unquote(url)
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.suffix.lower() not in RASTER_SUFFIXES:
            continue
        if path.name in SKIP_FILES:
            continue
        if not path.exists():
            print(f"  MISS {url}  (referenced but not on disk)")
            continue
        seen.setdefault(path.resolve(), None)

    return list(seen)


def kb(n: int) -> str:
    return f"{n / 1024:8.0f} KB"


def write_in_place(path: Path, data: bytes, attempts: int = 6) -> None:
    """Overwrite a file's bytes directly.

    Deliberately not a temp-file + rename: under OneDrive Files On-Demand the
    originals are reparse-point placeholders, and renaming over one fails with
    'Access is denied'. A plain write succeeds and OneDrive re-syncs after.
    """
    for i in range(attempts):
        try:
            with open(path, "wb") as fh:
                fh.write(data)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.5 * (i + 1))


def optimize(path: Path, dry_run: bool) -> tuple[int, int, int]:
    """Return (bytes_before, bytes_after, webp_bytes) for one image."""
    before = path.stat().st_size
    rel = path.relative_to(ROOT).as_posix()

    with Image.open(path) as im:
        im.load()
        orig_size = im.size
        is_png = path.suffix.lower() == ".png"
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)

        may_resize = rel.rsplit("/", 1)[0] not in NO_RESIZE_DIRS
        max_edge = EDGE_OVERRIDES.get(path.name, MAX_EDGE)
        longest = max(im.size)
        if may_resize and longest > max_edge:
            scale = max_edge / longest
            im = im.resize(
                (max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                Image.LANCZOS,
            )

        webp_path = path.with_suffix(".webp")

        if dry_run:
            print(f"  DRY  {rel:58s} {kb(before)}  {orig_size[0]}x{orig_size[1]} -> {im.size[0]}x{im.size[1]}")
            return before, before, 0

        # --- WebP sibling ---
        if path.name in NO_WEBP_FILES:
            webp_bytes = 0
            if webp_path.exists():
                webp_path.unlink()
        else:
            webp_buf = io.BytesIO()
            webp_im = im if has_alpha else im.convert("RGB")
            webp_im.save(webp_buf, "WEBP", quality=WEBP_QUALITY, method=6)
            write_in_place(webp_path, webp_buf.getvalue())
            webp_bytes = webp_path.stat().st_size

        # --- Re-encode the original, in place, only if it gets smaller ---
        buf = io.BytesIO()
        if is_png:
            im.save(buf, "PNG", optimize=True)
        else:
            im.convert("RGB").save(
                buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True
            )

        after = buf.tell()
        if after < before:
            write_in_place(path, buf.getvalue())
        else:
            after = before

        # A WebP that does not beat the re-encoded original is just dead weight;
        # drop it so no <picture> source points at a larger file.
        if webp_bytes and webp_bytes >= after:
            webp_path.unlink()
            webp_bytes = 0

    saved = before - after
    flag = "RESZ" if im.size != orig_size else "REEN"
    if saved == 0:
        flag = "KEEP"
    print(
        f"  {flag} {rel:58s} {kb(before)} -> {kb(after)}   webp {kb(webp_bytes)}"
        f"   ({orig_size[0]}x{orig_size[1]} -> {im.size[0]}x{im.size[1]})"
    )
    return before, after, webp_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    args = parser.parse_args()

    if not INDEX.exists():
        print(f"index.html not found at {INDEX}", file=sys.stderr)
        return 1

    images = referenced_images()
    print(f"index.html references {len(images)} raster images")
    print(f"max longest edge {MAX_EDGE}px, JPEG q{JPEG_QUALITY}, WebP q{WEBP_QUALITY}\n")

    total_before = total_after = total_webp = total_served = 0
    failures = []
    for path in images:
        try:
            before, after, webp_bytes = optimize(path, args.dry_run)
        except Exception as exc:  # keep going; report at the end
            rel = path.relative_to(ROOT).as_posix()
            print(f"  FAIL {rel}: {exc}")
            failures.append(rel)
            continue
        total_before += before
        total_after += after
        total_webp += webp_bytes
        # What a modern browser actually downloads: the WebP where one was kept,
        # otherwise the re-encoded original.
        total_served += webp_bytes if webp_bytes else after

    mb = 1024 * 1024
    print(f"\n  originals on disk : {total_before / mb:7.2f} MB -> {total_after / mb:7.2f} MB")
    if not args.dry_run:
        print(f"  webp siblings     : {total_webp / mb:7.2f} MB")
        print(f"  served to a modern browser: {total_served / mb:7.2f} MB")

    if failures:
        print(f"\n  {len(failures)} file(s) failed:")
        for rel in failures:
            print(f"    {rel}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
