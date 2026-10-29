"""Small outline-geometry toolkit for TrueType glyphs (numpy based).

* :func:`decompose_all` turns every composite glyph into a simple glyph (the
  point structure is identical for every instance of the same source VF).
* :func:`flatten` samples contours into closed polylines.
* :func:`raster` is a tiny nonzero-winding scanline rasterizer used for shape
  analysis (headline detection etc.) on the default master only.
"""

from __future__ import annotations

import numpy as np
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates, flagOnCurve

FLAG_OVERLAP_SIMPLE = 0x40


def glyph_arrays(glyf, name: str):
    """(coords Nx2 float array, endPts list, flags bytearray) of a glyph (decomposed)."""
    g = glyf[name]
    if g.numberOfContours == 0:
        return np.zeros((0, 2)), [], bytearray()
    coords, endPts, flags = g.getCoordinates(glyf)
    arr = np.frombuffer(coords._a, dtype=np.float64).reshape(-1, 2).copy()
    return arr, list(endPts), bytearray(flags)


def make_simple_glyph(coords, endPts, flags, overlap: bool = True) -> Glyph:
    g = Glyph()
    if len(endPts) == 0:
        g.numberOfContours = 0
        return g
    g.numberOfContours = len(endPts)
    gc = GlyphCoordinates()
    gc._a.extend(np.round(np.asarray(coords, dtype=np.float64)).ravel().tolist())
    g.coordinates = gc
    g.endPtsOfContours = list(endPts)
    fl = bytearray(f & flagOnCurve for f in flags)
    if overlap and fl:
        fl[0] |= FLAG_OVERLAP_SIMPLE
    g.flags = fl
    g.program = _empty_program()
    return g


def _empty_program():
    from fontTools.ttLib.tables import ttProgram

    p = ttProgram.Program()
    p.fromBytecode(b"")
    return p


def decompose_all(font) -> None:
    """Replace composites by simple glyphs and drop all glyph instructions."""
    glyf = font["glyf"]
    new = {}
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite():
            c, e, f = glyph_arrays(glyf, name)
            new[name] = make_simple_glyph(c, e, f)
    for name, g in new.items():
        glyf[name] = g
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.numberOfContours > 0:
            g.program = _empty_program()


def contours(coords, endPts, flags):
    start = 0
    for end in endPts:
        yield coords[start : end + 1], flags[start : end + 1]
        start = end + 1


def flatten(coords, endPts, flags, steps: int = 8) -> list[np.ndarray]:
    """Closed polylines approximating each TrueType contour."""
    out = []
    for pts, fl in contours(coords, endPts, flags):
        n = len(pts)
        if n == 0:
            continue
        on = [bool(f & flagOnCurve) for f in fl]
        # Build a list of (point, on) including implied on-curve points.
        seq = []
        for i in range(n):
            p, o = pts[i], on[i]
            q, qo = pts[(i + 1) % n], on[(i + 1) % n]
            seq.append((p, o))
            if not o and not qo:
                seq.append(((p + q) / 2.0, True))
        # rotate to start on an on-curve point
        k = next((i for i, (_, o) in enumerate(seq) if o), None)
        if k is None:
            continue
        seq = seq[k:] + seq[:k]
        poly = [seq[0][0]]
        i = 0
        m = len(seq)
        t = np.linspace(0, 1, steps + 1)[1:, None]
        while i < m:
            p0 = seq[i][0]
            p1, o1 = seq[(i + 1) % m]
            if o1:
                poly.append(p1)
                i += 1
            else:
                p2 = seq[(i + 2) % m][0]
                curve = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2
                poly.extend(curve)
                i += 2
        out.append(np.array(poly, dtype=float))
    return out


def raster(polys: list[np.ndarray], scale: float = 0.25):
    """Nonzero-winding coverage bitmap.

    Returns ``(mask, x0, y0, scale)``: ``mask[r, c]`` covers the font-unit
    point ``(x0 + (c + .5)/scale, y0 + (r + .5)/scale)`` (rows go up).
    """
    if not polys:
        return np.zeros((0, 0), bool), 0.0, 0.0, scale
    allp = np.concatenate(polys)
    x0, y0 = np.floor(allp.min(axis=0)) - 2
    x1, y1 = np.ceil(allp.max(axis=0)) + 2
    W = int((x1 - x0) * scale) + 1
    H = int((y1 - y0) * scale) + 1
    ax, ay, bx, by = [], [], [], []
    for p in polys:
        q = np.roll(p, -1, axis=0)
        ax.append(p[:, 0]); ay.append(p[:, 1]); bx.append(q[:, 0]); by.append(q[:, 1])
    ax = (np.concatenate(ax) - x0) * scale
    ay = (np.concatenate(ay) - y0) * scale
    bx = (np.concatenate(bx) - x0) * scale
    by = (np.concatenate(by) - y0) * scale
    keep = ay != by
    ax, ay, bx, by = ax[keep], ay[keep], bx[keep], by[keep]
    wind = np.where(by > ay, 1, -1)
    ymin = np.minimum(ay, by)
    ymax = np.maximum(ay, by)
    mask = np.zeros((H, W), bool)
    cols = np.arange(W) + 0.5
    for r in range(H):
        yc = r + 0.5
        sel = (ymin <= yc) & (ymax > yc)
        if not sel.any():
            continue
        t = (yc - ay[sel]) / (by[sel] - ay[sel])
        xs = ax[sel] + t * (bx[sel] - ax[sel])
        ws = wind[sel]
        order = np.argsort(xs)
        xs, ws = xs[order], ws[order]
        acc = np.cumsum(ws)
        # spans where winding != 0: between xs[i] and xs[i+1] when acc[i] != 0
        inside = acc[:-1] != 0
        if not inside.any():
            continue
        starts = xs[:-1][inside]
        ends = xs[1:][inside]
        row = mask[r]
        for s, e in zip(starts, ends):
            c0 = int(np.ceil(s - 0.5))
            c1 = int(np.floor(e - 0.5))
            if c1 >= c0:
                row[max(c0, 0) : min(c1 + 1, W)] = True
    return mask, float(x0), float(y0), scale


def bounds(coords) -> tuple[float, float, float, float] | None:
    if len(coords) == 0:
        return None
    return (float(coords[:, 0].min()), float(coords[:, 1].min()),
            float(coords[:, 0].max()), float(coords[:, 1].max()))


def rect_contour(x0: float, y0: float, x1: float, y1: float):
    """Clockwise (TrueType outer) rectangle: coords, flags."""
    pts = np.array([(x0, y0), (x0, y1), (x1, y1), (x1, y0)], dtype=float)
    return pts, bytearray([flagOnCurve] * 4)
