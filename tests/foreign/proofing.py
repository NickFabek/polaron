"""Proof rendering: HarfBuzz shaping + FreeType rasterizing (variable aware).

Every shaped line is drawn with a cell grid underneath: thin vertical lines at
every multiple of the cell width and a tick at every glyph origin.  Ticks are
green when the pen position is on the grid and red otherwise, so the PNG
itself proves (or disproves) the monospace property.
"""

from __future__ import annotations

from pathlib import Path

import freetype
import numpy as np
import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageFont


def _is_rtl(ch: str) -> bool:
    cp = ord(ch)
    return 0x0590 <= cp <= 0x08FF or 0xFB1D <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF


def _runs(text: str) -> list[str]:
    """Split into direction runs only when the text mixes RTL with letters of
    other scripts (pure RTL or pure LTR text stays one run)."""
    strong = [(_is_rtl(c), c) for c in text if c.isalpha()]
    if not strong or all(r for r, _ in strong) or not any(r for r, _ in strong):
        return [text]
    runs, cur, cur_rtl = [], "", None
    for c in text:
        r = _is_rtl(c) if c.isalpha() else cur_rtl
        if cur and r != cur_rtl:
            runs.append(cur)
            cur = ""
        cur += c
        cur_rtl = r
    if cur:
        runs.append(cur)
    return runs


class Shaper:
    def __init__(self, path: Path):
        self.path = str(path)
        self.blob = hb.Blob.from_file_path(self.path)
        self.face = hb.Face(self.blob)
        self.upem = self.face.upem
        self.ft = freetype.Face(self.path)
        self.axes = [a for a in getattr(self.face, "axis_infos", [])]

    def shape(self, text: str, variations: dict | None = None, features=None):
        """Shape ``text``; mixed-direction text is split into runs (a minimal
        stand-in for bidi: RTL runs inside an LTR line, laid out in order)."""
        font = hb.Font(self.face)
        if variations:
            font.set_variations(variations)
        out = []
        direction = None
        for run in _runs(text):
            buf = hb.Buffer()
            buf.add_str(run)
            buf.guess_segment_properties()
            hb.shape(font, buf, features or {})
            direction = direction or buf.direction
            out.extend(zip(buf.glyph_infos, buf.glyph_positions))
        return out, direction

    def set_coords(self, variations: dict | None):
        if not variations or not self.axes:
            return
        coords = []
        for a in self.axes:
            tag = a.tag if isinstance(a.tag, str) else a.tag.decode()
            coords.append(float(variations.get(tag, a.default_value)))
        self.ft.set_var_design_coords(coords)


def _label_font(px=14):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def render_lines(shaper: Shaper, lines, out_png: Path, *, size: int = 40,
                 variations: dict | None = None, cell: int | None = None,
                 title: str = "") -> dict:
    """Render ``lines`` = [(label, text)] to ``out_png``.

    Returns stats: number of glyphs, number of off-grid pen positions.
    """
    shaper.set_coords(variations)
    ft = shaper.ft
    ft.set_char_size(size * 64)
    scale = size / shaper.upem
    asc, desc = 950, -250
    line_h = int((asc - desc) * scale) + 34
    label_w = 150
    shaped = []
    width = 400
    for label, text in lines:
        glyphs, direction = shaper.shape(text, variations)
        total = sum(p.x_advance for _, p in glyphs)
        shaped.append((label, text, glyphs, total))
        width = max(width, label_w + int(total * scale) + 40)
    top = 40 if title else 10
    H = top + line_h * len(lines) + 10
    img = Image.new("RGB", (width, H), "white")
    draw = ImageDraw.Draw(img)
    lf = _label_font(13)
    if title:
        draw.text((10, 10), title, fill=(0, 0, 0), font=_label_font(16))
    off_grid = 0
    nglyphs = 0
    canvas = np.zeros((H, width), dtype=np.float32)
    for li, (label, text, glyphs, total) in enumerate(shaped):
        base_y = top + li * line_h + int(asc * scale) + 12
        x0 = label_w
        draw.text((10, base_y - 20), label, fill=(90, 90, 90), font=lf)
        if cell:
            ncell = int(np.ceil(total / cell)) if total else 0
            for k in range(ncell + 1):
                gx = x0 + k * cell * scale
                draw.line([(gx, base_y - asc * scale), (gx, base_y - desc * scale)],
                          fill=(225, 232, 245), width=1)
            draw.line([(x0, base_y), (x0 + total * scale, base_y)], fill=(240, 220, 220))
        pen = 0
        for info, pos in glyphs:
            nglyphs += 1
            ok = cell is None or pen % cell == 0
            if not ok:
                off_grid += 1
            tx = x0 + pen * scale
            col = (0, 160, 0) if ok else (230, 0, 0)
            draw.line([(tx, base_y - desc * scale + 2), (tx, base_y - desc * scale + 8)], fill=col, width=1)
            gx = pen + pos.x_offset
            gy = pos.y_offset
            ft.load_glyph(info.codepoint, freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_RENDER)
            bm = ft.glyph.bitmap
            if bm.width and bm.rows:
                arr = np.array(bm.buffer, dtype=np.float32).reshape(bm.rows, bm.pitch)[:, : bm.width] / 255.0
                px = int(round(x0 + gx * scale)) + ft.glyph.bitmap_left
                py = int(round(base_y - gy * scale)) - ft.glyph.bitmap_top
                ys, xs = slice(max(py, 0), min(py + bm.rows, H)), slice(max(px, 0), min(px + bm.width, width))
                sub = arr[ys.start - py: ys.stop - py, xs.start - px: xs.stop - px]
                region = canvas[ys, xs]
                canvas[ys, xs] = 1 - (1 - region) * (1 - sub)
            pen += pos.x_advance
        if cell:
            ok = pen % cell == 0
            tx = x0 + pen * scale
            draw.line([(tx, base_y - desc * scale + 2), (tx, base_y - desc * scale + 8)],
                      fill=(0, 160, 0) if ok else (230, 0, 0), width=1)
            if not ok:
                off_grid += 1
    rgb = np.array(img, dtype=np.float32)
    ink = canvas[..., None]
    rgb = rgb * (1 - ink) + np.array([10, 10, 30], dtype=np.float32) * ink
    Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).save(out_png)
    return {"glyphs": nglyphs, "off_grid": off_grid}
