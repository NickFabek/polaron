"""Render proof images with HarfBuzz shaping + FreeType rasterising."""

from __future__ import annotations

import sys
from pathlib import Path

import freetype
import numpy as np
import uharfbuzz as hb
from PIL import Image, ImageDraw


def _shape(blob_data, text, size, variations, features):
    face = hb.Face(blob_data)
    font = hb.Font(face)
    upem = face.upem
    if variations:
        font.set_variations(variations)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    scale = size / upem
    out = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((info.codepoint, pos.x_offset * scale, pos.y_offset * scale, pos.x_advance * scale))
    return out, upem


def render_lines(font_path, lines, size=48, variations=None, features=None, out=None,
                 margin=24, grid=True, line_gap=1.25, bg=255, fg=0, label=None):
    data = Path(font_path).read_bytes()
    ftface = freetype.Face(str(font_path))
    ftface.set_char_size(int(size * 64))
    if variations:
        axes = [a.tag for a in ftface.get_variation_info().axes]
        info = {a.tag: a for a in ftface.get_variation_info().axes}
        coords = [variations.get(t, info[t].default) for t in axes]
        ftface.set_var_design_coords(coords)
    shaped = [_shape(data, ln, size, variations, features)[0] for ln in lines]
    _, upem = _shape(data, " ", size, variations, features)
    asc = 950 * size / upem
    desc = 250 * size / upem
    lh = (asc + desc) * line_gap
    width = int(max([sum(g[3] for g in s) for s in shaped] + [10]) + 2 * margin)
    top_extra = 28 if label else 0
    height = int(lh * len(lines) + 2 * margin + top_extra)
    img = np.full((height, width), bg, dtype=np.uint8)
    flags = freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING
    pil = Image.fromarray(img)
    draw = ImageDraw.Draw(pil)
    for li, s in enumerate(shaped):
        base = margin + top_extra + li * lh + asc
        if grid:
            xh = 536 * size / upem
            cap = 730 * size / upem
            x_end = margin + sum(g[3] for g in s)
            for y, col in ((base, 200), (base - xh, 225), (base - cap, 225)):
                draw.line([(margin, y), (x_end, y)], fill=col)
            x = margin
            for g in s:
                draw.line([(x, base + desc * 0.6), (x, base + desc * 0.9)], fill=170)
                x += g[3]
            draw.line([(x, base + desc * 0.6), (x, base + desc * 0.9)], fill=170)
    img = np.array(pil).astype(np.float32)
    cov = np.zeros_like(img)
    for li, s in enumerate(shaped):
        base = margin + top_extra + li * lh + asc
        x = margin
        for gid, xo, yo, xa in s:
            gx_f = x + xo
            gy_f = base - yo
            ix, iy = int(np.floor(gx_f)), int(np.floor(gy_f))
            fx, fy = gx_f - ix, gy_f - iy
            vec = freetype.FT_Vector(int(round(fx * 64)), int(round(-fy * 64)))
            ftface.set_transform(freetype.Matrix(0x10000, 0, 0, 0x10000), vec)
            ftface.load_glyph(gid, flags)
            bm = ftface.glyph.bitmap
            if bm.width and bm.rows:
                a = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.pitch)[:, : bm.width]
                gx = ix + ftface.glyph.bitmap_left
                gy = iy - ftface.glyph.bitmap_top
                x0, y0 = max(gx, 0), max(gy, 0)
                x1, y1 = min(gx + bm.width, width), min(gy + bm.rows, height)
                if x1 > x0 and y1 > y0:
                    cov[y0:y1, x0:x1] += a[y0 - gy : y1 - gy, x0 - gx : x1 - gx].astype(np.float32) / 255.0
            x += xa
    cov = np.clip(cov, 0, 1)
    img = (img * (1 - cov) + fg * cov).astype(np.uint8)
    pil = Image.fromarray(img)
    if label:
        ImageDraw.Draw(pil).text((margin, 6), label, fill=90)
    if out:
        pil.save(out)
    return pil


def stack(images, out, pad=8):
    w = max(i.width for i in images)
    h = sum(i.height for i in images) + pad * (len(images) - 1)
    canvas = Image.new("L", (w, h), 255)
    y = 0
    for i in images:
        canvas.paste(i, (0, y))
        y += i.height + pad
    canvas.save(out)
    return canvas


if __name__ == "__main__":
    font = sys.argv[1]
    out = sys.argv[2]
    text = sys.argv[3:] or ["Hamburgefonstiv 0123456789"]
    render_lines(font, text, out=out)
