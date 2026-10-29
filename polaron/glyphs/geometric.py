"""Geometric Shapes (U+25A0-25FF), a few Geometric Shapes Extended
(U+2B1B, 2B1C, 2B24, 2B55, 2B58) and common misc shapes (stars, ballot
boxes, check marks, crosses).

Shapes are centred horizontally in the cell and vertically on the math axis
(AXIS). Sizes scale with the cell width so squares stay square. Hollow shapes
use a stroke of ~0.8 x stem, limited by the shape's inradius so the counter
never closes up at heavy weights. The few cell-filling shapes (inverse
bullet / inverse white circle) span the full line box like block elements.
"""

from __future__ import annotations

import math

from ..geom import Contour
from ..glyph import register
from ..stroke import Path, Pen

KAPPA = 0.5522847498
AXIS = 330


def reg(cp, fn):
    register(f"uni{cp:04X}", fn, cp, slant=False)


def at(cp):
    """Decorator form of reg()."""

    def deco(fn):
        reg(cp, fn)
        return fn

    return deco


# ------------------------------------------------------------------ geometry helpers
def stroke_w(p, inr):
    """Outline stroke of hollow shapes, limited by the inradius."""
    return min(p.S * 0.8, 0.42 * inr)


def heavy_w(p, inr):
    """Stroke of the HEAVY variants (heavy circle, heavy check...)."""
    return min(p.S * 0.8 * 1.6 + 24, 0.5 * inr)


def poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


def poly_inradius(pts):
    """2A/P: exact for tangential polygons (triangles, rhombi, squares)."""
    per = sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
    return 2 * abs(poly_area(pts)) / per


def inset(pts, t):
    """Mitered inset of a simple polygon by t (result counter-clockwise)."""
    pts = list(pts)
    if poly_area(pts) < 0:
        pts.reverse()
    n = len(pts)
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        dx, dy = dx / ln, dy / ln
        nx, ny = -dy, dx  # left normal = inward for ccw
        lines.append(((a[0] + nx * t, a[1] + ny * t), (dx, dy)))
    out = []
    for i in range(n):
        (p0, d0), (p1, d1) = lines[i - 1], lines[i]
        den = d0[0] * d1[1] - d0[1] * d1[0]
        s = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / den
        out.append((p0[0] + d0[0] * s, p0[1] + d0[1] * s))
    return out


def fill_poly(g, pts):
    g.poly(*pts)


def hole_poly(g, pts):
    g.add(Contour.polygon(list(pts)).counterclockwise())


def hollow_poly(g, pts, t):
    g.poly(*pts)
    hole_poly(g, inset(pts, t))


def pt(cx, cy, r, a):
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def arc_segs(cx, cy, r, a0, a1, n):
    """n cubic segments along a circle from angle a0 to a1 (radians)."""
    segs = []
    da = (a1 - a0) / n
    k = 4 / 3 * math.tan(da / 4) * r
    for i in range(n):
        t0 = a0 + i * da
        t1 = t0 + da
        p0, p1 = pt(cx, cy, r, t0), pt(cx, cy, r, t1)
        c1 = (p0[0] - k * math.sin(t0), p0[1] + k * math.cos(t0))
        c2 = (p1[0] + k * math.sin(t1), p1[1] - k * math.cos(t1))
        segs.append(("C", c1, c2, p1))
    return segs


def circle_c(cx, cy, r):
    return Contour(pt(cx, cy, r, 0), arc_segs(cx, cy, r, 0, 2 * math.pi, 4))


def disc_(g, cx, cy, r):
    g.add(circle_c(cx, cy, r).clockwise())


def hole_circle(g, cx, cy, r):
    g.add(circle_c(cx, cy, r).counterclockwise())


def ring(g, cx, cy, r, t):
    disc_(g, cx, cy, r)
    hole_circle(g, cx, cy, r - t)


def sector_c(cx, cy, r, a0, a1, n):
    """Pie slice: centre -> arc a0..a1 -> centre."""
    return Contour((cx, cy), [("L", pt(cx, cy, r, a0))] + arc_segs(cx, cy, r, a0, a1, n) + [("L", (cx, cy))])


def half_disc_c(cx, cy, r, a0):
    """Half disc from angle a0 to a0 + pi, closed by the diameter."""
    start = pt(cx, cy, r, a0)
    return Contour(start, arc_segs(cx, cy, r, a0, a0 + math.pi, 2) + [("L", start)])


def arc_band_c(cx, cy, r_out, r_in, a0, a1, n):
    """Part of a ring between angles a0 and a1 (square ends)."""
    segs = arc_segs(cx, cy, r_out, a0, a1, n)
    segs.append(("L", pt(cx, cy, r_in, a1)))
    segs += arc_segs(cx, cy, r_in, a1, a0, n)
    segs.append(("L", pt(cx, cy, r_out, a0)))
    return Contour(pt(cx, cy, r_out, a0), segs)


def rrect_c(x0, y0, x1, y1, r):
    k = KAPPA * r
    return Contour(
        (x0, y0 + r),
        [
            ("L", (x0, y1 - r)),
            ("C", (x0, y1 - r + k), (x0 + r - k, y1), (x0 + r, y1)),
            ("L", (x1 - r, y1)),
            ("C", (x1 - r + k, y1), (x1, y1 - r + k), (x1, y1 - r)),
            ("L", (x1, y0 + r)),
            ("C", (x1, y0 + r - k), (x1 - r + k, y0), (x1 - r, y0)),
            ("L", (x0 + r, y0)),
            ("C", (x0 + r - k, y0), (x0, y0 + r - k), (x0, y0 + r)),
        ],
    )


def sq_box(p, f, cy=AXIS):
    s = p.W * f
    return p.M - s / 2, cy - s / 2, p.M + s / 2, cy + s / 2


def rect_pts(x0, y0, x1, y1):
    return [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]


# ------------------------------------------------------------------ squares & rectangles
BIG, MED, MEDSMALL, SMALL, LARGE = 0.80, 0.64, 0.50, 0.38, 0.94


def black_square(f):
    def fn(g, p):
        g.rect(*sq_box(p, f))

    return fn


def white_square(f):
    def fn(g, p):
        x0, y0, x1, y1 = sq_box(p, f)
        t = stroke_w(p, (x1 - x0) / 2)
        hollow_poly(g, rect_pts(x0, y0, x1, y1), t)

    return fn


for _cp, _f in ((0x25A0, BIG), (0x25AA, SMALL), (0x25FC, MED), (0x25FE, MEDSMALL), (0x2B1B, LARGE)):
    reg(_cp, black_square(_f))
for _cp, _f in ((0x25A1, BIG), (0x25AB, SMALL), (0x25FB, MED), (0x25FD, MEDSMALL), (0x2B1C, LARGE), (0x2610, BIG)):
    reg(_cp, white_square(_f))


@at(0x25A2)
def rounded_square(g, p):
    x0, y0, x1, y1 = sq_box(p, BIG)
    s = x1 - x0
    t = stroke_w(p, s / 2)
    ro = t + 0.12 * s
    g.add(rrect_c(x0, y0, x1, y1, ro).clockwise())
    g.add(rrect_c(x0 + t, y0 + t, x1 - t, y1 - t, ro - t).counterclockwise())


def frame(g, p, f=BIG):
    x0, y0, x1, y1 = sq_box(p, f)
    t = stroke_w(p, (x1 - x0) / 2)
    hollow_poly(g, rect_pts(x0, y0, x1, y1), t)
    return x0, y0, x1, y1, t


@at(0x25A3)
def square_in_square(g, p):
    x0, y0, x1, y1, t = frame(g, p)
    a = (x1 - x0 - 2 * t) * 0.46
    g.rect(p.M - a / 2, AXIS - a / 2, p.M + a / 2, AXIS + a / 2)


def _band(q, c1, c2, kind):
    """Region c1 <= x - y <= c2 inside the square [0,q]^2. kind: -1 band
    left of the diagonal, 0 straddling it, +1 right of it."""
    if kind > 0:
        return [(c1, 0), (c2, 0), (q, q - c2), (q, q - c1)]
    if kind < 0:
        return [(0, -c2), (0, -c1), (q + c1, q), (q + c2, q)]
    return [(0, 0), (c2, 0), (q, q - c2), (q, q), (q + c1, q), (0, -c1)]


def hatched(mode):
    def fn(g, p):
        x0, y0, x1, y1, t = frame(g, p)
        a = x1 - x0 - 2 * t  # interior
        q = x1 - x0 - t  # frame centre line square
        qx, qy = x0 + t / 2, y0 + t / 2
        if "h" in mode or "v" in mode:
            tb = min(0.6 * t, a / 7)
            for i in (1, 2, 3):
                m = t + a * i / 4
                if "h" in mode:
                    g.rect(qx, y0 + m - tb / 2, qx + q, y0 + m + tb / 2)
                if "v" in mode:
                    g.rect(x0 + m - tb / 2, qy, x0 + m + tb / 2, qy + q)
        for d in ("d1", "d2"):
            if d not in mode:
                continue
            tb = min(0.6 * t, q / 3 / math.sqrt(2) * 0.45)
            hc = tb * math.sqrt(2) / 2
            for k in (-2, -1, 0, 1, 2):
                c0 = q * k / 3
                kind = (k > 0) - (k < 0)
                band = _band(q, c0 - hc, c0 + hc, kind)
                if d == "d1":  # upper left to lower right: lines x + y = c
                    pts = [(qx + q - u, qy + v) for u, v in band]
                else:  # upper right to lower left: lines x - y = c
                    pts = [(qx + u, qy + v) for u, v in band]
                fill_poly(g, pts)

    return fn


reg(0x25A4, hatched("h"))
reg(0x25A5, hatched("v"))
reg(0x25A6, hatched("hv"))
reg(0x25A7, hatched("d1"))
reg(0x25A8, hatched("d2"))
reg(0x25A9, hatched("d1d2"))


def rect_shape(fw, fh, black):
    def fn(g, p):
        w, h = p.W * fw, p.W * fh
        pts = rect_pts(p.M - w / 2, AXIS - h / 2, p.M + w / 2, AXIS + h / 2)
        if black:
            fill_poly(g, pts)
        else:
            hollow_poly(g, pts, stroke_w(p, min(w, h) / 2))

    return fn


reg(0x25AC, rect_shape(0.84, 0.42, True))
reg(0x25AD, rect_shape(0.84, 0.42, False))
reg(0x25AE, rect_shape(0.50, 0.92, True))
reg(0x25AF, rect_shape(0.50, 0.92, False))


def parallelogram(black):
    def fn(g, p):
        w, h, sl = p.W * 0.9, p.W * 0.44, p.W * 0.24
        x0, x1 = p.M - w / 2, p.M + w / 2
        y0, y1 = AXIS - h / 2, AXIS + h / 2
        pts = [(x0, y0), (x0 + sl, y1), (x1, y1), (x1 - sl, y0)]
        if black:
            fill_poly(g, pts)
        else:
            hollow_poly(g, pts, stroke_w(p, poly_inradius(pts)))

    return fn


reg(0x25B0, parallelogram(True))
reg(0x25B1, parallelogram(False))


# ------------------------------------------------------------------ triangles
def tri_pts(p, direction, base, height):
    """Isosceles triangle with bbox centred on (M, AXIS)."""
    cx, cy = p.M, AXIS
    b, h = base / 2, height / 2
    if direction == "up":
        return [(cx - b, cy - h), (cx, cy + h), (cx + b, cy - h)]
    if direction == "down":
        return [(cx - b, cy + h), (cx + b, cy + h), (cx, cy - h)]
    if direction == "right":
        return [(cx - h, cy - b), (cx - h, cy + b), (cx + h, cy)]
    return [(cx + h, cy + b), (cx + h, cy - b), (cx - h, cy)]


def triangle(direction, fbase, black, fheight=None):
    def fn(g, p):
        base = p.W * fbase
        height = base * math.sqrt(3) / 2 if fheight is None else p.W * fheight
        pts = tri_pts(p, direction, base, height)
        if black:
            fill_poly(g, pts)
        else:
            hollow_poly(g, pts, stroke_w(p, poly_inradius(pts)))

    return fn


TRI, TRI_S = 0.88, 0.50
_TRIS = {
    0x25B2: ("up", TRI, True), 0x25B3: ("up", TRI, False),
    0x25B4: ("up", TRI_S, True), 0x25B5: ("up", TRI_S, False),
    0x25B6: ("right", TRI, True), 0x25B7: ("right", TRI, False),
    0x25B8: ("right", TRI_S, True), 0x25B9: ("right", TRI_S, False),
    0x25BC: ("down", TRI, True), 0x25BD: ("down", TRI, False),
    0x25BE: ("down", TRI_S, True), 0x25BF: ("down", TRI_S, False),
    0x25C0: ("left", TRI, True), 0x25C1: ("left", TRI, False),
    0x25C2: ("left", TRI_S, True), 0x25C3: ("left", TRI_S, False),
}
for _cp, (_d, _f, _b) in _TRIS.items():
    reg(_cp, triangle(_d, _f, _b))
# pointers: flatter and wider than the triangles
reg(0x25BA, triangle("right", 0.50, True, 0.84))
reg(0x25BB, triangle("right", 0.50, False, 0.84))
reg(0x25C4, triangle("left", 0.50, True, 0.84))
reg(0x25C5, triangle("left", 0.50, False, 0.84))


def up_tri(p):
    base = p.W * TRI
    pts = tri_pts(p, "up", base, base * math.sqrt(3) / 2)
    return pts, stroke_w(p, poly_inradius(pts))


@at(0x25EC)
def tri_dot(g, p):
    pts, t = up_tri(p)
    hollow_poly(g, pts, t)
    inner = inset(pts, t)
    cx = sum(q[0] for q in inner) / 3
    cy = sum(q[1] for q in inner) / 3
    r_in = poly_inradius(inner)
    disc_(g, cx, cy, min(t * 0.9 + 8, r_in * 0.45))


def tri_half(right_black):
    def fn(g, p):
        pts, t = up_tri(p)
        fill_poly(g, pts)
        inner = inset(pts, t)
        # identify apex / base corners of the inset triangle
        apex = max(inner, key=lambda q: q[1])
        base_l = min(inner, key=lambda q: q[0])
        base_r = max(inner, key=lambda q: q[0])
        if right_black:  # hole = left half
            hole_poly(g, [apex, (apex[0], base_l[1]), base_l])
        else:
            hole_poly(g, [apex, base_r, (apex[0], base_r[1])])

    return fn


reg(0x25ED, tri_half(False))  # left half black
reg(0x25EE, tri_half(True))  # right half black


def right_tri(corner, black):
    def fn(g, p):
        x0, y0, x1, y1 = sq_box(p, BIG)
        pts = {
            "UL": [(x0, y0), (x0, y1), (x1, y1)],
            "UR": [(x0, y1), (x1, y1), (x1, y0)],
            "LL": [(x0, y1), (x1, y0), (x0, y0)],
            "LR": [(x1, y1), (x1, y0), (x0, y0)],
        }[corner]
        if black:
            fill_poly(g, pts)
        else:
            hollow_poly(g, pts, stroke_w(p, poly_inradius(pts)))

    return fn


reg(0x25E2, right_tri("LR", True))
reg(0x25E3, right_tri("LL", True))
reg(0x25E4, right_tri("UL", True))
reg(0x25E5, right_tri("UR", True))
reg(0x25F8, right_tri("UL", False))
reg(0x25F9, right_tri("UR", False))
reg(0x25FA, right_tri("LL", False))
reg(0x25FF, right_tri("LR", False))


# ------------------------------------------------------------------ diamonds & lozenge
def diamond_pts(p, fw, fh):
    w, h = p.W * fw / 2, p.W * fh / 2
    cx, cy = p.M, AXIS
    return [(cx - w, cy), (cx, cy + h), (cx + w, cy), (cx, cy - h)]


DIA_W, DIA_H = 0.90, 1.02


@at(0x25C6)
def black_diamond(g, p):
    fill_poly(g, diamond_pts(p, DIA_W, DIA_H))


@at(0x25C7)
def white_diamond(g, p):
    pts = diamond_pts(p, DIA_W, DIA_H)
    hollow_poly(g, pts, stroke_w(p, poly_inradius(pts)))


@at(0x25C8)
def diamond_in_diamond(g, p):
    pts = diamond_pts(p, DIA_W, DIA_H)
    t = stroke_w(p, poly_inradius(pts)) * 0.9
    hollow_poly(g, pts, t)
    inner = inset(pts, t)
    f = 0.48
    fill_poly(g, [(p.M + (q[0] - p.M) * f, AXIS + (q[1] - AXIS) * f) for q in inner])


@at(0x25CA)
def lozenge(g, p):
    w, h = p.W * 0.66 / 2, 0.95 * p.CAP / 2
    cx, cy = p.M, AXIS
    pts = [(cx - w, cy), (cx, cy + h), (cx + w, cy), (cx, cy - h)]
    hollow_poly(g, pts, stroke_w(p, poly_inradius(pts)))


# ------------------------------------------------------------------ circles
R_BIG, R_LARGE, R_BULLET = 0.43, 0.48, 0.2


def r_of(p, f):
    return p.W * f


@at(0x25CF)
def black_circle(g, p):
    disc_(g, p.M, AXIS, r_of(p, R_BIG))


@at(0x2B24)
def black_large_circle(g, p):
    disc_(g, p.M, AXIS, r_of(p, R_LARGE))


def white_circle(f, heavy=False):
    def fn(g, p):
        r = r_of(p, f)
        ring(g, p.M, AXIS, r, heavy_w(p, r) if heavy else stroke_w(p, r))

    return fn


reg(0x25CB, white_circle(R_BIG))
reg(0x25EF, white_circle(R_LARGE))
reg(0x25E6, white_circle(R_BULLET))
reg(0x2B55, white_circle(R_LARGE, heavy=True))
reg(0x2B58, white_circle(R_BIG, heavy=True))


@at(0x25C9)
def fisheye(g, p):
    r = r_of(p, R_BIG)
    t = stroke_w(p, r)
    ring(g, p.M, AXIS, r, t)
    disc_(g, p.M, AXIS, (r - t) * 0.6)


@at(0x25CE)
def bullseye(g, p):
    r = r_of(p, R_BIG)
    t = min(p.S * 0.8, 0.26 * r)
    ring(g, p.M, AXIS, r, t)
    ring(g, p.M, AXIS, r / 2, t)


@at(0x25CC)
def dotted_circle(g, p):
    r = r_of(p, R_BIG)
    d = min(1.3 * p.S * 0.8, 0.26 * r)
    for i in range(12):
        a = math.pi / 2 - i * 2 * math.pi / 12
        cx, cy = pt(p.M, AXIS, r - d / 2, a)
        disc_(g, cx, cy, d / 2)


@at(0x25CD)
def circle_vertical_fill(g, p):
    r = r_of(p, R_BIG)
    t = stroke_w(p, r)
    cx, cy = p.M, AXIS
    ring(g, cx, cy, r, t)
    rc = r - t / 2  # bars end on the ring's centre line
    tb = min(0.6 * t, (r - t) / 2 * 0.5)
    for xc in (-(r - t) / 2, 0.0, (r - t) / 2):
        xa, xb = xc - tb / 2, xc + tb / 2
        a_bl = math.atan2(-math.sqrt(rc * rc - xa * xa), xa)
        a_br = math.atan2(-math.sqrt(rc * rc - xb * xb), xb)
        a_tr = math.atan2(math.sqrt(rc * rc - xb * xb), xb)
        a_tl = math.atan2(math.sqrt(rc * rc - xa * xa), xa)
        start = pt(cx, cy, rc, a_bl)
        segs = arc_segs(cx, cy, rc, a_bl, a_br, 1)
        segs.append(("L", pt(cx, cy, rc, a_tr)))
        segs += arc_segs(cx, cy, rc, a_tr, a_tl, 1)
        segs.append(("L", start))
        g.add(Contour(start, segs).clockwise())


# half / quadrant black circles: black disc with the white part cut out
_DIR_A = {"R": -math.pi / 2, "U": 0.0, "L": math.pi / 2, "D": math.pi}


def circle_half_black(white_side):
    def fn(g, p):
        r = r_of(p, R_BIG)
        t = stroke_w(p, r)
        disc_(g, p.M, AXIS, r)
        g.add(half_disc_c(p.M, AXIS, r - t, _DIR_A[white_side]).counterclockwise())

    return fn


reg(0x25D0, circle_half_black("R"))  # left half black
reg(0x25D1, circle_half_black("L"))  # right half black
reg(0x25D2, circle_half_black("U"))  # lower half black
reg(0x25D3, circle_half_black("D"))  # upper half black


@at(0x25D4)
def circle_ur_black(g, p):
    r = r_of(p, R_BIG)
    t = stroke_w(p, r)
    disc_(g, p.M, AXIS, r)
    g.add(sector_c(p.M, AXIS, r - t, math.pi / 2, 2 * math.pi, 3).counterclockwise())


@at(0x25D5)
def circle_ul_white(g, p):
    r = r_of(p, R_BIG)
    t = stroke_w(p, r)
    disc_(g, p.M, AXIS, r)
    g.add(sector_c(p.M, AXIS, r - t, math.pi / 2, math.pi, 1).counterclockwise())


def half_black_circle(side):
    def fn(g, p):
        r = r_of(p, R_BIG)
        if side == "L":  # flat edge on the right, bbox centred
            g.add(half_disc_c(p.M + r / 2, AXIS, r, math.pi / 2).clockwise())
        else:
            g.add(half_disc_c(p.M - r / 2, AXIS, r, -math.pi / 2).clockwise())

    return fn


reg(0x25D6, half_black_circle("L"))
reg(0x25D7, half_black_circle("R"))


def quadrant_arc(a0):
    def fn(g, p):
        r = r_of(p, R_BIG)
        t = stroke_w(p, r)
        g.add(arc_band_c(p.M, AXIS, r, r - t, a0, a0 + math.pi / 2, 1).clockwise())

    return fn


reg(0x25DC, quadrant_arc(math.pi / 2))  # upper left
reg(0x25DD, quadrant_arc(0.0))  # upper right
reg(0x25DE, quadrant_arc(-math.pi / 2))  # lower right
reg(0x25DF, quadrant_arc(math.pi))  # lower left


def half_circle_arc(a0):
    def fn(g, p):
        r = r_of(p, R_BIG)
        t = stroke_w(p, r)
        g.add(arc_band_c(p.M, AXIS, r, r - t, a0, a0 + math.pi, 2).clockwise())

    return fn


reg(0x25E0, half_circle_arc(0.0))  # upper half
reg(0x25E1, half_circle_arc(math.pi))  # lower half


def circle_quadrant_lines(quad):
    """White circle with one quadrant marked by two radii."""

    def fn(g, p):
        r = r_of(p, R_BIG)
        t = stroke_w(p, r)
        cx, cy = p.M, AXIS
        ring(g, cx, cy, r, t)
        e = r - t / 2
        h = t / 2
        # drawn for the upper-left quadrant, then mirrored
        g.rect(cx - h, cy - h, cx + h, cy + e)
        g.rect(cx - e, cy - h, cx + h, cy + h)
        if quad[1] == "R":
            g.mirror_x(cx)
        if quad[0] == "L":  # lower
            g.mirror_y(cy)

    return fn


reg(0x25F4, circle_quadrant_lines("UL"))
reg(0x25F5, circle_quadrant_lines("LL"))
reg(0x25F6, circle_quadrant_lines("LR"))
reg(0x25F7, circle_quadrant_lines("UR"))


# ---- cell-filling inverse circles (CP437 heritage): span the line box
def cell_centre(p):
    return p.M, (p.BOXT + p.BOXB) / 2


INV_R = 0.38


@at(0x25D8)
def inverse_bullet(g, p):
    g.rect(0, p.BOXB, p.W, p.BOXT)
    cx, cy = cell_centre(p)
    hole_circle(g, cx, cy, p.W * 0.22)


@at(0x25D9)
def inverse_white_circle(g, p):
    g.rect(0, p.BOXB, p.W, p.BOXT)
    cx, cy = cell_centre(p)
    r = p.W * INV_R
    t = stroke_w(p, r)
    hole_circle(g, cx, cy, r)
    disc_(g, cx, cy, r - t)


def inverse_half(upper):
    def fn(g, p):
        cx, cy = cell_centre(p)
        r = p.W * INV_R
        ri = r - stroke_w(p, r)
        # the cell half with a half-ring notch: one outer contour
        segs = [("L", (0, p.BOXT)), ("L", (p.W, p.BOXT)), ("L", (p.W, cy)), ("L", (cx + r, cy))]
        segs += arc_segs(cx, cy, r, 0, math.pi, 2)
        segs.append(("L", (0, cy)))
        g.add(Contour((0, cy), segs).clockwise())
        g.add(half_disc_c(cx, cy, ri, 0.0).clockwise())
        if not upper:
            g.mirror_y(cy)

    return fn


reg(0x25DA, inverse_half(True))
reg(0x25DB, inverse_half(False))


# ------------------------------------------------------------------ squares with parts
def square_half_black(kind):
    def fn(g, p):
        x0, y0, x1, y1 = sq_box(p, BIG)
        t = stroke_w(p, (x1 - x0) / 2)
        g.rect(x0, y0, x1, y1)
        a0, b0, a1, b1 = x0 + t, y0 + t, x1 - t, y1 - t
        if kind == "L":  # left half black -> right half white
            hole_poly(g, rect_pts(p.M, b0, a1, b1))
        elif kind == "R":
            hole_poly(g, rect_pts(a0, b0, p.M, b1))
        elif kind == "UL":  # upper-left diagonal half black
            hole_poly(g, [(a0, b0), (a1, b1), (a1, b0)])
        else:  # lower-right diagonal half black
            hole_poly(g, [(a0, b0), (a0, b1), (a1, b1)])

    return fn


reg(0x25E7, square_half_black("L"))
reg(0x25E8, square_half_black("R"))
reg(0x25E9, square_half_black("UL"))
reg(0x25EA, square_half_black("LR"))


@at(0x25EB)
def square_bisected(g, p):
    x0, y0, x1, y1, t = frame(g, p)
    g.rect(p.M - t / 2, y0 + t / 2, p.M + t / 2, y1 - t / 2)


def square_quadrant(quad):
    def fn(g, p):
        x0, y0, x1, y1, t = frame(g, p)
        cx, cy = p.M, AXIS
        h = t / 2
        # upper-left quadrant, mirrored as needed
        g.rect(cx - h, cy - h, cx + h, y1 - h)
        g.rect(x0 + h, cy - h, cx + h, cy + h)
        if quad[1] == "R":
            g.mirror_x(cx)
        if quad[0] == "L":
            g.mirror_y(cy)

    return fn


reg(0x25F0, square_quadrant("UL"))
reg(0x25F1, square_quadrant("LL"))
reg(0x25F2, square_quadrant("LR"))
reg(0x25F3, square_quadrant("UR"))


# ------------------------------------------------------------------ stars
def star_pts(p, R, ratio=0.382):
    cx = p.M
    cy = AXIS + R * (1 + math.cos(math.pi / 5)) / 2 - R  # bbox centred on AXIS
    pts = []
    for i in range(10):
        a = math.pi / 2 - i * math.pi / 5
        rr = R if i % 2 == 0 else R * ratio
        pts.append(pt(cx, cy, rr, a))
    return pts, (cx, cy)


def star_R(p):
    return p.W * 0.92 / (2 * math.sin(2 * math.pi / 5))


@at(0x2605)
def black_star(g, p):
    pts, _ = star_pts(p, star_R(p))
    fill_poly(g, pts)


@at(0x2606)
def white_star(g, p):
    R = star_R(p)
    pts, (cx, cy) = star_pts(p, R)
    # distance from the centre to an edge line
    a, b = pts[0], pts[1]
    rho = abs((b[0] - a[0]) * (cy - a[1]) - (b[1] - a[1]) * (cx - a[0])) / math.dist(a, b)
    t = min(p.S * 0.8, 0.45 * rho)
    f = 1 - t / rho  # a mitered inset of a regular star is a scaled star
    fill_poly(g, pts)
    hole_poly(g, [(cx + (q[0] - cx) * f, cy + (q[1] - cy) * f) for q in pts])


# ------------------------------------------------------------------ check marks & crosses
def check_path(x0, y0, w, h):
    return [(x0 + 0.0 * w, y0 + 0.47 * h), (x0 + 0.36 * w, y0 + 0.06 * h), (x0 + w, y0 + h)]


def draw_check(g, p, box, t, cap="butt"):
    x0, y0, x1, y1 = box
    m = t / 2
    a, b, c = check_path(x0 + m, y0 + m, x1 - x0 - 2 * m, y1 - y0 - 2 * m)
    g.stroke(Path(a).L(b).L(c), pen=Pen(t, t), start=cap, end=cap)


def check_mark(heavy):
    def fn(g, p):
        w, h = p.W * 0.86, p.W * 0.86
        box = (p.M - w / 2, AXIS - h / 2, p.M + w / 2, AXIS + h / 2)
        t = min(p.S * 0.8 * 1.6 + 24, p.W * 0.2) if heavy else min(p.S * 0.8, p.W * 0.14)
        draw_check(g, p, box, t)

    return fn


reg(0x2713, check_mark(False))
reg(0x2714, check_mark(True))


def draw_x(g, p, box, t):
    x0, y0, x1, y1 = box
    m = t * 0.36  # keep the butt-cap corners inside the box
    g.line((x0 + m, y0 + m), (x1 - m, y1 - m), pen=Pen(t, t))
    g.line((x0 + m, y1 - m), (x1 - m, y0 + m), pen=Pen(t, t))


def mult_x(heavy):
    def fn(g, p):
        s = p.W * 0.74
        box = (p.M - s / 2, AXIS - s / 2, p.M + s / 2, AXIS + s / 2)
        t = min(p.S * 0.8 * 1.6 + 24, p.W * 0.2) if heavy else min(p.S * 0.8, p.W * 0.14)
        draw_x(g, p, box, t)

    return fn


reg(0x2715, mult_x(False))
reg(0x2716, mult_x(True))


def ballot_x(heavy):
    """Hand-drawn X: a long slightly bowed stroke rising to the right and a
    shorter falling one, both tapering at the start."""

    def fn(g, p):
        w, h = p.W * 0.84, p.W * 0.88
        x0, y0 = p.M - w / 2, AXIS - h / 2
        t = min(p.S * 0.8 * 1.6 + 24, p.W * 0.2) if heavy else min(p.S * 0.8 + 6, p.W * 0.15)
        pen = Pen(t, t)
        m = t / 2

        def P(u, v):
            return (x0 + m + (w - 2 * m) * u, y0 + m + (h - 2 * m) * v)

        rise = Path(P(0.02, 0.0), 0.55).C(P(0.30, 0.30), P(0.62, 0.66), P(1.0, 1.0), 1.0)
        fall = Path(P(0.10, 0.92), 0.5).C(P(0.38, 0.62), P(0.66, 0.30), P(0.92, 0.04), 1.0)
        g.stroke(rise, pen=pen, start="round", end="round")
        g.stroke(fall, pen=pen, start="round", end="round")

    return fn


reg(0x2717, ballot_x(False))
reg(0x2718, ballot_x(True))


@at(0x2611)
def ballot_check(g, p):
    x0, y0, x1, y1, t = frame(g, p)
    a = x1 - x0 - 2 * t
    tc = min(t * 0.95, a * 0.17)
    mg = a * 0.16
    box = (x0 + t + mg, y0 + t + mg * 1.15, x1 - t - mg, y1 - t - mg * 0.85)
    draw_check(g, p, box, tc)


@at(0x2612)
def ballot_cross(g, p):
    x0, y0, x1, y1, t = frame(g, p)
    a = x1 - x0 - 2 * t
    tc = min(t * 0.95, a * 0.17)
    mg = a * 0.16
    box = (x0 + t + mg, y0 + t + mg, x1 - t - mg, y1 - t - mg)
    draw_x(g, p, box, tc)
