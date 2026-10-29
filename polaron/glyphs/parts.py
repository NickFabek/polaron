"""Reusable letter parts: ovals, arches, bowls, hooks, serifs, dots.

All functions draw into a Glyph `g` using Params `p`. Coordinates are outer
ink bounds unless a name says "c" (centre line).
"""

from __future__ import annotations

import math

from ..geom import Contour
from ..stroke import Path, Pen

KC = 0.5523


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def arc_h(p, half_w, half_h, f=None):
    """Vertical extent of the quarter arcs of a bowl (centre line)."""
    f = p.ovr if f is None else f
    return clamp(half_w * f, 4, half_h - 2)


def pen(p, sx=None, sy=None):
    return Pen(p.S if sx is None else sx, p.H if sy is None else sy)


# ---------------------------------------------------------------- ovals
def oval(g, p, x0, x1, y0, y1, sx=None, sy=None, ry=None, k=None):
    """Closed superelliptic ring with outer bounds x0..x1, y0..y1."""
    sx = p.S if sx is None else sx
    sy = p.H if sy is None else sy
    xl, xr = x0 + sx / 2, x1 - sx / 2
    yb, yt = y0 + sy / 2, y1 - sy / 2
    cx, cy = (xl + xr) / 2, (yb + yt) / 2
    hh = (yt - yb) / 2
    ry = arc_h(p, (xr - xl) / 2, hh) if ry is None else clamp(ry, 4, hh - 2)
    path = (
        Path((xr, cy))
        .L((xr, yt - ry))
        .vh((cx, yt))
        .hv((xl, yt - ry))
        .L((xl, yb + ry))
        .vh((cx, yb))
        .hv((xr, yb + ry))
        .close()
    )
    g.stroke(path, pen=Pen(sx, sy), k=k)


def c_shape(g, p, x0, x1, y0, y1, top_end, bot_end, sx=None, sy=None, ry=None,
            start="butt", end="butt", wt=1.0, wb=1.0, cx=None):
    """Open bowl, opening on the right (like 'c').

    top_end/bot_end: y of the terminal cuts (centre line end points on the
    right side); the right-hand arcs run straight from the terminals."""
    sx = p.S if sx is None else sx
    sy = p.H if sy is None else sy
    xl, xr = x0 + sx / 2, x1 - sx / 2
    yb, yt = y0 + sy / 2, y1 - sy / 2
    cx = (xl + xr) / 2 if cx is None else cx
    hh = (yt - yb) / 2
    ry = arc_h(p, (xr - xl) / 2, hh) if ry is None else clamp(ry, 4, hh - 2)
    top_end = min(top_end, yt - 3)
    bot_end = max(bot_end, yb + 3)
    path = Path((xr, top_end), wt)
    path.vh((cx, yt)).hv((xl, yt - ry)).L((xl, yb + ry)).vh((cx, yb))
    path.hv((xr, bot_end), wb)
    g.stroke(path, pen=Pen(sx, sy), start=start, end=end)
    return xl, xr, yb, yt, cx


# ---------------------------------------------------------------- arches
def arch(g, p, xs, x1, ytop, ybot, yj, sx=None, sy=None, ry=None, xm=None, wj=0.42,
         k=None, end="butt"):
    """n-shoulder: right stem from ybot up, over the top, into a left stem
    whose centre line is xs, merging at height yj (centre line).
    x1 = outer right edge, ytop = outer top (with overshoot)."""
    sx = p.S if sx is None else sx
    sy = p.H if sy is None else sy
    xr = x1 - sx / 2
    yt = ytop - sy / 2
    xm = (xs + xr) / 2 + sx * 0.12 if xm is None else xm
    ry = arc_h(p, xr - xm, (yt - ybot) / 2) if ry is None else ry
    path = Path((xr, ybot)).L((xr, yt - ry)).vh((xm, yt)).hv((xs, yj), wj)
    g.stroke(path, pen=Pen(sx, sy), start=0, end=end, k=k)


def bowl_side(g, p, xs, x1, y0, y1, sx=None, sy=None, ry=None, rj=None, rjb=None,
              wj=0.5, k=None):
    """b-bowl attached to a stem whose centre line is xs (bowl on the
    right of xs if x1 > xs, on the left otherwise). Outer bounds y0..y1."""
    sx = p.S if sx is None else sx
    sy = p.H if sy is None else sy
    d = 1 if x1 > xs else -1
    xr = x1 - d * sx / 2
    yb, yt = y0 + sy / 2, y1 - sy / 2
    hh = (yt - yb) / 2
    cx = xs + (xr - xs) * 0.52
    ry = arc_h(p, abs(xr - cx), hh) if ry is None else clamp(ry, 4, hh - 2)
    rj = ry * 0.86 if rj is None else rj
    rjb = rj if rjb is None else rjb
    path = (
        Path((xs, yt - rj), wj)
        .vh((cx, yt))
        .hv((xr, yt - ry))
        .L((xr, yb + ry))
        .vh((cx, yb))
        .hv((xs, yb + rjb), wj)
    )
    g.stroke(path, pen=Pen(sx, sy), k=k)


# ---------------------------------------------------------------- stems
def vstem(g, p, xc, y0, y1, sx=None):
    sx = p.S if sx is None else sx
    g.rect(xc - sx / 2, y0, xc + sx / 2, y1)


def hbar(g, p, x0, x1, yc, sy=None):
    sy = p.Hb if sy is None else sy
    g.rect(x0, yc - sy / 2, x1, yc + sy / 2)


def diag(g, p, a, b, w=1.0, sx=None, sy=None, start=0, end=0):
    """Straight diagonal stroke with horizontal cuts by default."""
    sx = p.S if sx is None else sx
    sy = p.H if sy is None else sy
    g.stroke(Path(a, w).L(b, w), pen=Pen(sx, sy), start=start, end=end)


def dot(g, p, cx, cy, d=None, k=0.62):
    """Superelliptic dot (i, j, punctuation)."""
    d = p.dotw if d is None else d
    r = d / 2
    pts = []
    c = Contour(
        (cx + r, cy),
        [
            ("C", (cx + r, cy + r * k), (cx + r * k, cy + r), (cx, cy + r)),
            ("C", (cx - r * k, cy + r), (cx - r, cy + r * k), (cx - r, cy)),
            ("C", (cx - r, cy - r * k), (cx - r * k, cy - r), (cx, cy - r)),
            ("C", (cx + r * k, cy - r), (cx + r, cy - r * k), (cx + r, cy)),
        ],
    )
    g.add(c.clockwise())


def disc(g, cx, cy, rx, ry=None, k=KC):
    ry = rx if ry is None else ry
    c = Contour(
        (cx + rx, cy),
        [
            ("C", (cx + rx, cy + ry * k), (cx + rx * k, cy + ry), (cx, cy + ry)),
            ("C", (cx - rx * k, cy + ry), (cx - rx, cy + ry * k), (cx - rx, cy)),
            ("C", (cx - rx, cy - ry * k), (cx - rx * k, cy - ry), (cx, cy - ry)),
            ("C", (cx + rx * k, cy - ry), (cx + rx, cy - ry * k), (cx + rx, cy)),
        ],
    )
    g.add(c.clockwise())


def ring_circle(g, cx, cy, r_out, r_in, k=KC):
    """Circular ring (two contours)."""
    disc(g, cx, cy, r_out, k=k)
    c = Contour(
        (cx + r_in, cy),
        [
            ("C", (cx + r_in, cy + r_in * k), (cx + r_in * k, cy + r_in), (cx, cy + r_in)),
            ("C", (cx - r_in * k, cy + r_in), (cx - r_in, cy + r_in * k), (cx - r_in, cy)),
            ("C", (cx - r_in, cy - r_in * k), (cx - r_in * k, cy - r_in), (cx, cy - r_in)),
            ("C", (cx + r_in * k, cy - r_in), (cx + r_in, cy - r_in * k), (cx + r_in, cy)),
        ],
    )
    g.add(c.counterclockwise())


# ---------------------------------------------------------------- serifs
def serif_foot(g, p, xc, y=0, left=True, right=True, sx=None, ll=None, rl=None, down=False,
               x_min=None, x_max=None):
    """Bracketed foot serif centred on a stem (centre xc) at baseline y.
    down=True makes a head serif hanging from y (top of a stem).
    The serif is clipped to stay inside [x_min, x_max] (cell minus padding)."""
    if not p.serif:
        return
    sx = p.S if sx is None else sx
    ll = p.SL if ll is None else ll
    rl = p.SL if rl is None else rl
    x_min = p.cellpad if x_min is None else x_min
    x_max = g.adv - p.cellpad if x_max is None else x_max
    ll = max(0.0, min(ll, xc - sx / 2 - x_min))
    rl = max(0.0, min(rl, x_max - (xc + sx / 2)))
    t = p.ST
    br = min(p.SL * 0.55, t * 1.6 + sx * 0.25)  # bracket size
    sgn = -1 if down else 1
    x0 = xc - sx / 2 - (ll if left else 0)
    x1 = xc + sx / 2 + (rl if right else 0)
    te = t * 0.72  # thinner at the tips (Libertinus-like taper)
    g.add(Contour.polygon([(x0, y), (x0, y + sgn * te), (xc, y + sgn * t), (x1, y + sgn * te), (x1, y)]).clockwise())
    for side, on in ((-1, left), (1, right)):
        if not on:
            continue
        ex = xc + side * sx / 2
        # concave bracket: from stem side down to the slab
        a = (ex - side * 1, y + sgn * (t + br))
        b = (ex + side * br, y + sgn * t * 0.9)
        c = Contour(
            a,
            [
                ("C", (ex, y + sgn * (t + br * 0.45)), (ex + side * br * 0.45, y + sgn * t * 0.92), b),
                ("L", (b[0], y + sgn * t * 0.5)),
                ("L", (ex - side * 2, y + sgn * t * 0.5)),
                ("L", a),
            ],
        )
        g.add(c.clockwise())


def serif_head(g, p, xc, y, sx=None, length=None, slope=0.32, sans=False):
    """Wedge head serif on the left of a stem top (Libertinus-like flag).
    In the sans style it is only drawn when sans=True (i, j, l...)."""
    if p.sans and not sans:
        return
    sx = p.S if sx is None else sx
    length = (p.SL * 1.05 if p.serif else p.SL * 0.95) if length is None else length
    t = p.ST if p.serif else p.Hb
    xl = xc - sx / 2
    length = max(4.0, min(length, xl - p.cellpad))
    if p.serif:
        drop = length * slope
        c = Contour.polygon(
            [
                (xl - length, y - drop - t),
                (xl - length, y - drop),
                (xl + 1, y),
                (xl + 1, y - drop - t - length * 0.25),
            ]
        )
        g.add(c.clockwise())
    else:
        g.rect(xl - length, y - t, xl + 1, y)


def serif_top_both(g, p, xc, y, sx=None, ll=None, rl=None):
    serif_foot(g, p, xc, y, sx=sx, ll=ll, rl=rl, down=True)


def ball(g, p, x, y, f=1.0):
    """Ball terminal (serif style only)."""
    if not p.serif:
        return
    r = (p.S * 0.6 + 6 - max(0.0, p.S - 76) * 0.3) * f
    disc(g, x, y, r, r * 1.08)
