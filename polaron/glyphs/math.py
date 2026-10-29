"""Mathematical operators.

Blocks: Mathematical Operators (U+2200-22FF, complete), Supplemental
Mathematical Operators (U+2A00-2AFF, common), Miscellaneous Mathematical
Symbols-A/-B (U+27C0-27EF, U+2980-29FF, common), math pieces of
Miscellaneous Technical (U+2308-230B, 2310, 2320-2321, 239B-23AE, 23B7) and
super/subscript operators (U+207A-207E, 208A-208E).

Everything is built from a small set of primitives sized by an *ink box*
(x0, x1, y0, y1).  Relations are vertical stacks of layers (an angle, a bar,
a tilde, a dot ...) laid out by `stack`, which centres the whole pile on the
math axis p.AX and keeps the outer extents of `plus`/`equal`/`less`
(+-op_hw).  Modifiers (negation slash, enclosing circle/square) are drawn
on top.  The contour structure of every glyph only depends on the spec,
never on numbers, so all masters stay point-compatible.
"""

from __future__ import annotations

import math

from fontTools import agl

from ..geom import Contour, add, bounds_of, dot as vdot, line_intersect, mul, perp, sub, unit
from ..glyph import REGISTRY, Glyph, register
from ..stroke import Path, Pen, arc_cubic
from .latin_lower import diag_between
from .parts import KC, clamp, disc, dot, hbar, ring_circle, serif_foot, vstem
from .punct import eq_gap, op_hw, pdot_d
from .scaled import draw_scaled

# ====================================================================== registry
_AVOID = {0x2206, 0x2126, 0xB5}  # AGL names that clash with Greek letters


def gname(cp):
    n = agl.UV2AGL.get(cp)
    if n and cp not in _AVOID:
        return n
    return f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"


def _taken(name, cp):
    if name in REGISTRY:
        return True
    if cp is not None:
        for gd in REGISTRY.values():
            if cp in gd.unicodes:
                return True
    return False


DEFINED = []  # (cp, name) registered by this module


def define(cp, name=None, slant=True):
    """Register fn(g, p) for code point cp (skipped if already provided)."""

    def deco(fn):
        n = name or gname(cp)
        if not _taken(n, cp):
            register(n, fn, cp, slant=slant)
            DEFINED.append((cp, n))
        return fn

    return deco


def defn(cp, fn, name=None, slant=True):
    define(cp, name, slant)(fn)


# ====================================================================== metrics
def HW(p):
    """Half width of operators (same as plus / equal)."""
    return op_hw(p)


def T(p):
    """Stroke thickness of relations (equal bars)."""
    return p.S * 0.92


def TB(p):
    """Stroke thickness of binary operators (plus)."""
    return p.S * 0.95


def mpen(t):
    return Pen(t, t)


def WG(p):
    """White gap between stacked parts (as in equal)."""
    return eq_gap(p) - T(p)


def fit_t(p, t, span, n, gf=0.6):
    """Largest stroke <= t so that n strokes and n-1 gaps (>= gf * WG) fit
    into span."""
    gmin = WG(p) * gf
    return max(min(t, (span - (n - 1) * gmin) / n), t * 0.3)


def DOTD(p):
    return pdot_d(p) * 0.86


def BIGH(p):
    """Half height of n-ary operators."""
    return (p.BT - p.BB) * 0.455


def TALL(p):
    """Half height of tall relations (divides, parallel ...)."""
    return (p.BT - p.BB) * 0.42


# ====================================================================== geometry helpers
def shoelace(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


def inset_poly(pts, t):
    """Polygon inset by t (works for convex and mildly concave shapes)."""
    n = len(pts)
    sgn = 1.0 if shoelace(pts) > 0 else -1.0
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        u = unit(sub(b, a))
        nn = perp(u)
        lines.append((add(a, mul(nn, t * sgn)), u))
    out = []
    for i in range(n):
        p0, u0 = lines[i - 1]
        p1, u1 = lines[i]
        x = line_intersect(p0, u0, p1, u1)
        if x is None:
            x = p1
        out.append(x)
    return out


def poly_ring(g, pts, t):
    """Outline of a polygon: outer pts, wall thickness t inwards."""
    g.add(Contour.polygon(pts).clockwise())
    g.add(Contour.polygon(inset_poly(pts, t)).counterclockwise())


def fill_poly(g, pts):
    g.add(Contour.polygon(pts).clockwise())


def chevron_pts(apex, e1, e2, pen, w1=1.0, w2=1.0, lim=None, cut1=None, cut2=None):
    """Polygon of two straight arms meeting at apex (mitred, the miter
    truncated to `lim` beyond the apex).  cut1/cut2: None = butt end,
    otherwise the direction of the cut line through the end point."""
    u1 = unit(sub(e1, apex))
    u2 = unit(sub(e2, apex))
    n1, n2 = perp(u1), perp(u2)
    s1, s2 = pen.support(n1), pen.support(n2)
    o1 = mul(s1, w1) if vdot(n1, u2) < 0 else mul(s1, -w1)
    o2 = mul(s2, w2) if vdot(n2, u1) < 0 else mul(s2, -w2)
    mo = line_intersect(add(apex, o1), u1, add(apex, o2), u2) or apex
    ni = line_intersect(sub(apex, o1), u1, sub(apex, o2), u2) or apex
    b = unit((-(u1[0] + u2[0]), -(u1[1] + u2[1])))
    dm = vdot(sub(mo, apex), b)
    lt = dm if lim is None else min(dm, lim)

    def on_edge(p0, u):
        den = vdot(u, b)
        if abs(den) < 1e-9:
            return p0
        t = (lt - vdot(sub(p0, apex), b)) / den
        return add(p0, mul(u, t))

    t1 = on_edge(add(apex, o1), u1)
    t2 = on_edge(add(apex, o2), u2)

    def ends(e, u, o, cut):
        if cut is None:
            return add(e, o), sub(e, o)
        a = line_intersect(add(e, o), u, e, cut) or add(e, o)
        c = line_intersect(sub(e, o), u, e, cut) or sub(e, o)
        return a, c

    e1o, e1i = ends(e1, u1, o1, cut1)
    e2o, e2i = ends(e2, u2, o2, cut2)
    return [e1o, t1, t2, e2o, e2i, ni, e1i]


def chevron(g, apex, e1, e2, pen, **kw):
    pts = chevron_pts(apex, e1, e2, pen, **kw)
    fill_poly(g, pts)
    return pts


def bbox(pts):
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


def tmp_glyph(p):
    return Glyph("tmp", p)


def mirror_into(g, tmp, cx=None, cy=None):
    """Add tmp's contours to g mirrored about x=cx and/or y=cy."""
    if cx is not None:
        tmp.transform(lambda q: (2 * cx - q[0], q[1]), flip=True)
    if cy is not None:
        tmp.transform(lambda q: (q[0], 2 * cy - q[1]), flip=True)
    g.add(tmp.contours)


def rot_into(g, tmp, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    tmp.transform(lambda q: (cx + (q[0] - cx) * c - (q[1] - cy) * s, cy + (q[0] - cx) * s + (q[1] - cy) * c))
    g.add(tmp.contours)


def line(g, a, b, t, start=0, end=0, w0=1.0, w1=None):
    """Monoline straight stroke; caps default to horizontal cuts."""
    g.stroke(Path(a, w0).L(b, w0 if w1 is None else w1), pen=mpen(t), start=start, end=end)


def seg(g, a, b, t):
    """Monoline straight stroke with butt caps."""
    g.stroke(Path(a).L(b), pen=mpen(t))


def circle_ring(g, cx, cy, r, t):
    ring_circle(g, cx, cy, r, r - t)


def ellipse_ring(g, cx, cy, rx, ry, t, ty=None):
    ty = t if ty is None else ty
    disc(g, cx, cy, rx, ry)
    k = KC
    a, b = rx - t, ry - ty
    c = Contour(
        (cx + a, cy),
        [
            ("C", (cx + a, cy + b * k), (cx + a * k, cy + b), (cx, cy + b)),
            ("C", (cx - a * k, cy + b), (cx - a, cy + b * k), (cx - a, cy)),
            ("C", (cx - a, cy - b * k), (cx - a * k, cy - b), (cx, cy - b)),
            ("C", (cx + a * k, cy - b), (cx + a, cy - b * k), (cx + a, cy)),
        ],
    )
    g.add(c.counterclockwise())


def sheared_path(nodes, shear, ym):
    """Build a Path from upright cubic pieces, then shear x by (y-ym)*shear.
    nodes: [(p0, w0), ("C", c1, c2, p, w) | ("A", mode, p, w, k) | ("L", p, w)]"""
    f = lambda q: (q[0] + (q[1] - ym) * shear, q[1])  # noqa: E731
    p0, w0 = nodes[0]
    path = Path(f(p0), w0)
    cur = p0
    for nd in nodes[1:]:
        if nd[0] == "C":
            _, c1, c2, q, w = nd
            path.C(f(c1), f(c2), f(q), w)
            cur = q
        elif nd[0] == "A":
            _, mode, q, w, k = nd
            _, c1, c2, _ = arc_cubic(cur, q, mode, k)
            path.C(f(c1), f(c2), f(q), w)
            cur = q
        else:
            _, q, w = nd
            path.L(f(q), w)
            cur = q
    return path


# ====================================================================== primitives
# Every primitive draws into g filling the ink box x0..x1, y0..y1 with stroke t.
def prim_bar(g, p, x0, x1, y0, y1, t):
    g.rect(x0, y0, x1, y1)


def angle_pen(p, t):
    """Pen of < > (the elliptical letter pen, as in `less`)."""
    return p.pen.scaled(0.95 * t / T(p))


def angle_poly(p, x0, x1, y0, y1, t, tip_left=True, pen=None, lim_f=2.3):
    """< shaped chevron filling the box (tip on the left)."""
    pen = angle_pen(p, t) if pen is None else pen
    cy = (y0 + y1) / 2
    xt, xe, hh = x0 + t, x1 - t * 0.3, (y1 - y0) / 2 - t * 0.4
    lim = pen.A * lim_f
    pts = None
    for _ in range(5):
        pts = chevron_pts((xt, cy), (xe, cy + hh), (xe, cy - hh), pen, lim=lim)
        bx0, by0, bx1, by1 = bbox(pts)
        xt += x0 - bx0
        xe += x1 - bx1
        hh += y1 - by1
    if not tip_left:
        pts = [(x0 + x1 - q[0], q[1]) for q in pts]
    return pts


def prim_less(g, p, x0, x1, y0, y1, t):
    fill_poly(g, angle_poly(p, x0, x1, y0, y1, t))


def prim_greater(g, p, x0, x1, y0, y1, t):
    fill_poly(g, angle_poly(p, x0, x1, y0, y1, t, tip_left=False))


def prec_paths(p, x0, x1, y0, y1, t):
    """Curved angle (precedes), tip on the left: two arms, cusp at the tip."""
    w = t / 2
    cy = (y0 + y1) / 2
    xt = x0 + w * 0.2
    xe = x1 - w * 0.75
    ye = y1 - w
    dx, dy = xe - xt, ye - cy
    up = Path((xt, cy), 0.42).C((xt + dx * 0.42, cy + dy * 0.06), (xe - dx * 0.22, ye - dy * 0.42), (xe, ye), 1.0)
    ye2 = y0 + w
    dy2 = ye2 - cy
    lo = Path((xt, cy), 0.42).C((xt + dx * 0.42, cy + dy2 * 0.06), (xe - dx * 0.22, ye2 - dy2 * 0.42), (xe, ye2), 1.0)
    return up, lo


def prim_prec(g, p, x0, x1, y0, y1, t, right=False):
    tmp = tmp_glyph(p)
    for path in prec_paths(p, x0, x1, y0, y1, t):
        tmp.stroke(path, pen=mpen(t), start="butt", end=0)
    if right:
        mirror_into(g, tmp, cx=(x0 + x1) / 2)
    else:
        g.add(tmp.contours)


def prim_succ(g, p, x0, x1, y0, y1, t):
    prim_prec(g, p, x0, x1, y0, y1, t, right=True)


def prim_cbar(g, p, x0, x1, y0, y1, t, right=False):
    """Curved bar under precedes (parallel to its lower arm)."""
    w = t / 2
    xt, xe = x0 + w * 0.2, x1 - w * 0.75
    yt, ye = y1 - w, y0 + w
    dx, dy = xe - xt, ye - yt
    path = Path((xt, yt), 0.7).C((xt + dx * 0.42, yt + dy * 0.06), (xe - dx * 0.22, ye - dy * 0.42), (xe, ye), 1.0)
    tmp = tmp_glyph(p)
    tmp.stroke(path, pen=mpen(t), start="butt", end=0)
    if right:
        mirror_into(g, tmp, cx=(x0 + x1) / 2)
    else:
        g.add(tmp.contours)


def prim_cbar_r(g, p, x0, x1, y0, y1, t):
    prim_cbar(g, p, x0, x1, y0, y1, t, right=True)


def sub_path(p, x0, x1, y0, y1, t, square=False):
    """Subset-like U opening to the right."""
    w = t / 2
    xl, xr = x0 + w, x1
    yt, yb = y1 - w, y0 + w
    cy = (yt + yb) / 2
    r = (yt - yb) / 2
    if square:
        return Path((xr, yt)).L((xl, yt)).L((xl, yb)).L((xr, yb))
    xa = min(xl + r * 1.02, xr - t * 0.8)
    return Path((xr, yt)).L((xa, yt)).hv((xl, cy)).vh((xa, yb)).L((xr, yb))


def prim_sub(g, p, x0, x1, y0, y1, t, right=False, square=False):
    tmp = tmp_glyph(p)
    tmp.stroke(sub_path(p, x0, x1, y0, y1, t, square), pen=mpen(t))
    if right:
        mirror_into(g, tmp, cx=(x0 + x1) / 2)
    else:
        g.add(tmp.contours)


def prim_sup(g, p, x0, x1, y0, y1, t):
    prim_sub(g, p, x0, x1, y0, y1, t, right=True)


def prim_sqsub(g, p, x0, x1, y0, y1, t):
    prim_sub(g, p, x0, x1, y0, y1, t, square=True)


def prim_sqsup(g, p, x0, x1, y0, y1, t):
    prim_sub(g, p, x0, x1, y0, y1, t, right=True, square=True)


def prim_elem(g, p, x0, x1, y0, y1, t, right=False, square=False, bar_x0=None):
    prim_sub(g, p, x0, x1, y0, y1, t, right=right, square=square)
    cy = (y0 + y1) / 2
    if right:
        g.rect(x1 - t / 2 if bar_x0 is None else bar_x0, cy - t / 2, x0, cy + t / 2)
    else:
        g.rect(x0 + t / 2 if bar_x0 is None else bar_x0, cy - t / 2, x1, cy + t / 2)


def prim_ni(g, p, x0, x1, y0, y1, t):
    prim_elem(g, p, x0, x1, y0, y1, t, right=True)


def cup_path(p, x0, x1, y0, y1, t, square=False):
    w = t / 2
    xl, xr = x0 + w, x1 - w
    yb = y0 + w
    cx = (xl + xr) / 2
    if square:
        return Path((xl, y1)).L((xl, yb)).L((xr, yb)).L((xr, y1))
    r = min((xr - xl) / 2 * 1.1, (y1 - yb) * 0.72)
    return Path((xl, y1)).L((xl, yb + r)).vh((cx, yb)).hv((xr, yb + r)).L((xr, y1))


def prim_cup(g, p, x0, x1, y0, y1, t, square=False, flip=False):
    tmp = tmp_glyph(p)
    tmp.stroke(cup_path(p, x0, x1, y0, y1, t, square), pen=mpen(t))
    if flip:
        mirror_into(g, tmp, cy=(y0 + y1) / 2)
    else:
        g.add(tmp.contours)


def prim_cap(g, p, x0, x1, y0, y1, t):
    prim_cup(g, p, x0, x1, y0, y1, t, flip=True)


def prim_sqcup(g, p, x0, x1, y0, y1, t):
    prim_cup(g, p, x0, x1, y0, y1, t, square=True)


def prim_sqcap(g, p, x0, x1, y0, y1, t):
    prim_cup(g, p, x0, x1, y0, y1, t, square=True, flip=True)


def wedge_pts(p, x0, x1, y0, y1, t, pen=None):
    """Logical and: two arms from the bottom corners to a flat-cut apex."""
    pen = mpen(t) if pen is None else pen
    cx = (x0 + x1) / 2
    a, b = diag_between(p, cx, y1, x0, y0, 0, 1, pen=pen)
    c, d = diag_between(p, cx, y1, x1, y0, 0, -1, pen=pen)
    return a, b, c, d


def prim_wedge(g, p, x0, x1, y0, y1, t, flip=False):
    pen = mpen(t)
    tmp = tmp_glyph(p)
    a, b, c, d = wedge_pts(p, x0, x1, y0, y1, t)
    tmp.stroke(Path(b).L(a), pen=pen, start=0, end=0)
    tmp.stroke(Path(d).L(c), pen=pen, start=0, end=0)
    if flip:
        mirror_into(g, tmp, cy=(y0 + y1) / 2)
    else:
        g.add(tmp.contours)


def prim_vee(g, p, x0, x1, y0, y1, t):
    prim_wedge(g, p, x0, x1, y0, y1, t, flip=True)


def tri_pts(x0, x1, y0, y1, d="left"):
    cy = (y0 + y1) / 2
    cx = (x0 + x1) / 2
    if d == "left":
        return [(x0, cy), (x1, y1), (x1, y0)]
    if d == "right":
        return [(x1, cy), (x0, y0), (x0, y1)]
    if d == "up":
        return [(cx, y1), (x1, y0), (x0, y0)]
    return [(cx, y0), (x0, y1), (x1, y1)]


def prim_tri(g, p, x0, x1, y0, y1, t, d="left", filled=False):
    pts = tri_pts(x0, x1, y0, y1, d)
    if filled:
        fill_poly(g, pts)
    else:
        poly_ring(g, pts, t)


def prim_tril(g, p, x0, x1, y0, y1, t):
    # triangles look bigger than angles: inset slightly
    e = (x1 - x0) * 0.03
    prim_tri(g, p, x0 + e, x1 - e, y0, y1, t, "left")


def prim_trir(g, p, x0, x1, y0, y1, t):
    e = (x1 - x0) * 0.03
    prim_tri(g, p, x0 + e, x1 - e, y0, y1, t, "right")


# ---------------------------------------------------------------------- tilde
_TILDE_PEAK = 0.696  # centre-line extreme of the asciitilde curve per unit a


def tilde_path(x0, x1, cy, a, rev=False):
    w = x1 - x0
    m = (x0 + x1) / 2
    s = -1 if rev else 1
    return (
        Path((x0, cy - s * a * 0.45))
        .C((x0 + w * 0.12, cy + s * a * 1.1), (m - w * 0.2, cy + s * a * 0.9), (m, cy))
        .C((m + w * 0.2, cy - s * a * 0.9), (x1 - w * 0.12, cy - s * a * 1.1), (x1, cy + s * a * 0.45))
    )


def tilde_h(p, t, f=1.0):
    """Natural ink height of the operator tilde."""
    a = (p.S * 0.35 + 34) * f
    return 2 * (_TILDE_PEAK * a + t / 2)


def prim_tilde(g, p, x0, x1, y0, y1, t, rev=False):
    cy = (y0 + y1) / 2
    a = max(((y1 - y0) / 2 - t / 2) / _TILDE_PEAK, 4)
    e = (x1 - x0) * 0.025
    g.stroke(tilde_path(x0 + e, x1 - e, cy, a, rev), pen=mpen(t))


def prim_rtilde(g, p, x0, x1, y0, y1, t):
    prim_tilde(g, p, x0, x1, y0, y1, t, rev=True)


def prim_vtilde(g, p, cx, y0, y1, hw, t):
    """Vertical tilde (wreath product)."""
    tmp = tmp_glyph(p)
    cy = (y0 + y1) / 2
    hl = (y1 - y0) / 2
    a = max((hw - t / 2) / _TILDE_PEAK, 4)
    tmp.stroke(tilde_path(-hl, hl, 0, a), pen=mpen(t))
    tmp.transform(lambda q: (cx - q[1], cy - q[0]))
    g.add(tmp.contours)


# ---------------------------------------------------------------------- dots & small marks
def prim_dot(g, p, x0, x1, y0, y1, t, d=None):
    d = (y1 - y0) if d is None else d
    dot(g, p, (x0 + x1) / 2, (y0 + y1) / 2, d=d, k=0.66)


def prim_dots2(g, p, x0, x1, y0, y1, t):
    d = y1 - y0
    off = (x1 - x0) * 0.24
    for s in (-1, 1):
        dot(g, p, (x0 + x1) / 2 + s * off, (y0 + y1) / 2, d=d, k=0.66)


def prim_ring(g, p, x0, x1, y0, y1, t):
    r = (y1 - y0) / 2
    circle_ring(g, (x0 + x1) / 2, (y0 + y1) / 2, r, min(t * 0.8, r * 0.55))


def prim_hat(g, p, x0, x1, y0, y1, t, flip=False):
    cx = (x0 + x1) / 2
    hw = (y1 - y0) * 1.0
    prim_wedge(g, p, cx - hw, cx + hw, y0, y1, t * 0.85, flip=flip)


def prim_hatv(g, p, x0, x1, y0, y1, t):
    prim_hat(g, p, x0, x1, y0, y1, t, flip=True)


def prim_frown(g, p, x0, x1, y0, y1, t, flip=False):
    """Small arc (frown) above relations."""
    cx = (x0 + x1) / 2
    hw = (x1 - x0) * 0.3
    w = t * 0.85 / 2
    yb, yt = y0 + w, y1 - w
    if flip:
        path = Path((cx - hw, yt)).vh((cx, yb)).hv((cx + hw, yt))
    else:
        path = Path((cx - hw, yb)).vh((cx, yt)).hv((cx + hw, yb))
    g.stroke(path, pen=mpen(t * 0.85))


def prim_smile(g, p, x0, x1, y0, y1, t):
    prim_frown(g, p, x0, x1, y0, y1, t, flip=True)


def star_pts(cx, cy, r, ri=None, n=5, rot=90.0):
    ri = r * 0.42 if ri is None else ri
    pts = []
    for i in range(2 * n):
        a = math.radians(rot + i * 180.0 / n)
        rr = r if i % 2 == 0 else ri
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def prim_star(g, p, x0, x1, y0, y1, t):
    r = (y1 - y0) / 2 / 0.905
    fill_poly(g, star_pts((x0 + x1) / 2, (y0 + y1) / 2 - r * 0.05, r))


def prim_smalltri(g, p, x0, x1, y0, y1, t):
    cx = (x0 + x1) / 2
    hw = (y1 - y0) * 0.62
    poly_ring(g, [(cx, y1), (cx + hw, y0), (cx - hw, y0)], t * 0.75)


def letters_layer(names, fy=0.36, fx=0.3, wf=0.6, ref="xh"):
    def draw(g, p, x0, x1, y0, y1, t):
        n = len(names)
        step = (p.R - p.L) * fx * 1.05
        for i, nm in enumerate(names):
            dx = (i - (n - 1) / 2) * step
            draw_scaled(g, p, nm, fx, fy, wf, dx=dx, dy=y0)

    return draw


def bump_draw(up=True):
    def draw(g, p, x0, x1, y0, y1, t):
        w = t / 2
        cx = (x0 + x1) / 2
        r = (y1 - y0) - t
        if up:
            yb = y0 + w
            path = Path((x0, yb)).L((cx - r, yb)).vh((cx, yb + r)).hv((cx + r, yb)).L((x1, yb))
        else:
            yb = y1 - w
            path = Path((x0, yb)).L((cx - r, yb)).vh((cx, yb - r)).hv((cx + r, yb)).L((x1, yb))
        g.stroke(path, pen=mpen(t))

    return draw


# ====================================================================== stacking
class Lay:
    """A layer of a relation stack.  h=None means flexible (a big shape)."""

    __slots__ = ("draw", "h", "flex", "gap", "inset")

    def __init__(self, draw, h=None, flex=1.0, gap=1.0, inset=0.0):
        self.draw = draw
        self.h = h
        self.flex = flex
        self.gap = gap  # gap factor *above* this layer
        self.inset = inset  # horizontal inset (fraction of half width)


def stack(g, p, layers, x0=None, x1=None, cy=None, tf=None):
    """Lay out layers top to bottom centred on cy (default math axis).
    Returns (y_bottom, y_top, boxes)."""
    hw = HW(p)
    x0 = p.M - hw if x0 is None else x0
    x1 = p.M + hw if x1 is None else x1
    cy = p.AX if cy is None else cy
    n = len(layers)
    nf = sum(1 for l in layers if l.h is None)
    if tf is None:
        tf = stack_tf(p, n)
    t = T(p) * tf
    F = 2 * hw
    if n == 1:
        ff = 1.0
    elif nf == 1:
        ff = 0.97
    elif nf == 2:
        ff = 0.64
    else:
        ff = 0.5
    hs = []
    for l in layers:
        if l.h is None:
            hs.append(max(F * ff * l.flex, t * 2.3))
        else:
            hs.append(l.h * (tf if l.h < t * 1.5 else 1.0))
    wg = WG(p) * (0.9 if n > 2 else 1.0)
    gaps = [wg * layers[i].gap for i in range(1, n)]
    total = sum(hs) + sum(gaps)
    hmax = (p.BT - p.BB) * 0.84
    if total > hmax:
        fixed = sum(h for h, l in zip(hs, layers) if l.h is not None)
        var = total - fixed
        s = max(0.3, (hmax - fixed) / var)
        hs = [h if l.h is not None else h * s for h, l in zip(hs, layers)]
        gaps = [gp * s for gp in gaps]
        total = sum(hs) + sum(gaps)
    y = cy + total / 2
    boxes = []
    for i, l in enumerate(layers):
        if i:
            y -= gaps[i - 1]
        yt, yb = y, y - hs[i]
        ins = (x1 - x0) / 2 * l.inset
        l.draw(g, p, x0 + ins, x1 - ins, yb, yt, t)
        boxes.append((x0 + ins, x1 - ins, yb, yt))
        y = yb
    return cy - total / 2, cy + total / 2, boxes


def stack_tf(p, n):
    """Stroke factor for stacks of n layers: lighter at heavy weights."""
    return 1.0 - max(0, n - 1) * 0.04 * (p.S / 76) ** 1.5


def negate(g, p, y0, y1, cx=None, ext=None, t=None, sx=None, rev=False):
    """Negation slash through y0..y1."""
    cx = p.M if cx is None else cx
    ext = HW(p) * 0.16 if ext is None else ext
    t = T(p) if t is None else t
    h = (y1 - y0) + 2 * ext
    sx = min(h * 0.2, HW(p) * 0.62) if sx is None else sx
    s = -1 if rev else 1
    a = (cx - s * sx, y0 - ext)
    b = (cx + s * sx, y1 + ext)
    g.stroke(Path(a).L(b), pen=mpen(t), start=0, end=0)


# ---------------------------------------------------------------------- layer factories
def L_flex(draw, flex=1.0, gap=1.0, inset=0.0):
    return Lay(draw, None, flex, gap, inset)


def L_bar(p, gap=1.0, tf=1.0):
    return Lay(prim_bar, T(p) * tf, gap=gap)


def L_tilde(p, rev=False, f=0.82, gap=1.0):
    return Lay(prim_rtilde if rev else prim_tilde, tilde_h(p, T(p), f), gap=gap)


def L_dot(p, gap=0.85):
    return Lay(prim_dot, DOTD(p), gap=gap)


def L_dots2(p, gap=0.85):
    return Lay(prim_dots2, DOTD(p) * 0.9, gap=gap)


def L_ring(p, gap=0.8):
    return Lay(prim_ring, DOTD(p) * 1.25 + p.S * 0.2, gap=gap)


def L_hat(p, up=True, gap=0.8):
    return Lay(prim_hat if up else prim_hatv, HW(p) * 0.36 + p.S * 0.3, gap=gap)


def L_frown(p, up=True, gap=0.8):
    return Lay(prim_frown if up else prim_smile, HW(p) * 0.28 + T(p) * 0.85, gap=gap)


def L_star(p, gap=0.8):
    return Lay(prim_star, HW(p) * 0.62 + p.S * 0.15, gap=gap)


def L_smalltri(p, gap=0.8):
    return Lay(prim_smalltri, HW(p) * 0.52 + p.S * 0.25, gap=gap)


def L_bump(p, up=True, gap=1.0):
    return Lay(bump_draw(up), T(p) + HW(p) * 0.32, gap=gap)


SHAPES = {
    "lt": prim_less, "gt": prim_greater, "prec": prim_prec, "succ": prim_succ,
    "sub": prim_sub, "sup": prim_sup, "sqsub": prim_sqsub, "sqsup": prim_sqsup,
    "elem": prim_elem, "ni": prim_ni, "cup": prim_cup, "cap": prim_cap,
    "sqcup": prim_sqcup, "sqcap": prim_sqcap, "wedge": prim_wedge, "vee": prim_vee,
    "tril": prim_tril, "trir": prim_trir,
}


def parse(p, spec):
    """'lt bar' -> layers.  Tokens: shape names (flexible), bar, tilde,
    rtilde, dot, dots2, ring, hat, vhat, frown, smile, star, tri, bump, dbump,
    cbar (curved bar for prec), cbarr."""
    out = []
    for tok in spec.split():
        if tok in SHAPES:
            out.append(L_flex(SHAPES[tok]))
        elif tok == "bar":
            out.append(L_bar(p))
        elif tok == "tilde":
            out.append(L_tilde(p))
        elif tok == "rtilde":
            out.append(L_tilde(p, rev=True))
        elif tok == "dot":
            out.append(L_dot(p))
        elif tok == "dots2":
            out.append(L_dots2(p))
        elif tok == "ring":
            out.append(L_ring(p))
        elif tok == "hat":
            out.append(L_hat(p))
        elif tok == "vhat":
            out.append(L_hat(p, up=False))
        elif tok == "frown":
            out.append(L_frown(p))
        elif tok == "smile":
            out.append(L_frown(p, up=False))
        elif tok == "star":
            out.append(L_star(p))
        elif tok == "tri":
            out.append(L_smalltri(p))
        elif tok == "bump":
            out.append(L_bump(p))
        elif tok == "dbump":
            out.append(L_bump(p, up=False))
        elif tok == "cbar":
            out.append(Lay(prim_cbar, T(p) + HW(p) * 0.42))
        elif tok == "cbarr":
            out.append(Lay(prim_cbar_r, T(p) + HW(p) * 0.42))
        else:
            raise ValueError(f"unknown stack token {tok}")
    return out


def rel(spec, neg=None, small=False, cy=None):
    """Glyph function for a relation stack.
    neg: None, 'all' (slash through everything) or an int k = slash through
    the last k layers only (not-equal-to bars), or 'rev' (reversed slash)."""

    def fn(g, p):
        layers = parse(p, spec)
        x0 = x1 = None
        if small:
            for l in layers:
                if l.h is None:
                    l.flex = 0.72
            hw = HW(p) * 0.78
            x0, x1 = p.M - hw, p.M + hw
        yb, yt, boxes = stack(g, p, layers, x0=x0, x1=x1, cy=cy)
        t = T(p)
        if neg == "all":
            negate(g, p, yb, yt)
        elif neg == "rev":
            negate(g, p, yb, yt, rev=True)
        elif isinstance(neg, int):
            lo = boxes[-1][2]
            hi = boxes[-neg][3]
            negate(g, p, lo, hi, ext=WG(p) * 0.6 + t * 0.2, sx=HW(p) * 0.3)

    return fn


def prim_cbaru(g, p, x0, x1, y0, y1, t, right=False):
    """Curved bar above precedes (parallel to its upper arm)."""
    tmp = tmp_glyph(p)
    prim_cbar(tmp, p, x0, x1, y0, y1, t, right=right)
    mirror_into(g, tmp, cy=(y0 + y1) / 2)


def prim_cbaru_r(g, p, x0, x1, y0, y1, t):
    prim_cbaru(g, p, x0, x1, y0, y1, t, right=True)


def tri_wall(pts, t):
    per = sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
    inr = 2 * abs(shoelace(pts)) / per
    return min(t * 0.88, inr * 0.5)


def prim_tri2(g, p, x0, x1, y0, y1, t, d="left"):
    e = (x1 - x0) * 0.03
    pts = tri_pts(x0 + e, x1 - e, y0, y1, d)
    poly_ring(g, pts, tri_wall(pts, t))


def prim_tril2(g, p, x0, x1, y0, y1, t):
    prim_tri2(g, p, x0, x1, y0, y1, t, "left")


def prim_trir2(g, p, x0, x1, y0, y1, t):
    prim_tri2(g, p, x0, x1, y0, y1, t, "right")


def prim_smalltri2(g, p, x0, x1, y0, y1, t):
    cx = (x0 + x1) / 2
    hw = (y1 - y0) * 0.62
    pts = [(cx, y1), (cx + hw, y0), (cx - hw, y0)]
    poly_ring(g, pts, tri_wall(pts, t * 0.8))


def elem_t(p, h, t, n=3):
    """Stroke for shapes with n horizontal strokes in height h."""
    gmin = WG(p) * 0.55
    return max(min(t, (h - (n - 1) * gmin) / n), t * 0.55)


def prim_elem2(g, p, x0, x1, y0, y1, t, right=False, square=False):
    t = elem_t(p, y1 - y0, t)
    prim_elem(g, p, x0, x1, y0, y1, t, right=right, square=square)


def prim_ni2(g, p, x0, x1, y0, y1, t):
    prim_elem2(g, p, x0, x1, y0, y1, t, right=True)


def prim_sqelem(g, p, x0, x1, y0, y1, t):
    prim_elem2(g, p, x0, x1, y0, y1, t, square=True)


def prim_ltdot(g, p, x0, x1, y0, y1, t, right=False):
    if right:
        prim_greater(g, p, x0, x1, y0, y1, t)
    else:
        prim_less(g, p, x0, x1, y0, y1, t)
    d = min(DOTD(p) * 0.85, (y1 - y0) * 0.24)
    cx = x0 + (x1 - x0) * (0.66 if not right else 0.34)
    dot(g, p, cx, (y0 + y1) / 2, d=d, k=0.66)


def prim_gtdot(g, p, x0, x1, y0, y1, t):
    prim_ltdot(g, p, x0, x1, y0, y1, t, right=True)


SHAPES.update({
    "tril": prim_tril2, "trir": prim_trir2, "elem": prim_elem2, "ni": prim_ni2,
    "sqelem": prim_sqelem, "ltdot": prim_ltdot, "gtdot": prim_gtdot,
})

_parse0 = parse


def parse(p, spec):  # noqa: F811  (extended token set)
    out = []
    for tok in spec.split():
        if tok == "cbaru":
            out.append(Lay(prim_cbaru, T(p) + HW(p) * 0.42))
        elif tok == "cbarur":
            out.append(Lay(prim_cbaru_r, T(p) + HW(p) * 0.42))
        elif tok == "tri":
            out.append(Lay(prim_smalltri2, HW(p) * 0.52 + p.S * 0.25, gap=0.8))
        elif tok == "sdot":
            out.append(Lay(prim_dot, DOTD(p) * 0.8, gap=0.8))
        elif tok.startswith("small:"):
            lay = _parse0(p, tok[6:])[0]
            lay.flex = 0.72
            lay.inset = 0.2
            out.append(lay)
        else:
            out.extend(_parse0(p, tok))
    return out


# ====================================================================== U+2200 block: letter-like
def draw_glyph(g, p, name):
    gd = REGISTRY[name]
    tmp = Glyph("tmp", p)
    tmp.adv = g.adv
    gd.fn(tmp, p)
    g.add(tmp.contours)
    return tmp


@define(0x2200)
def universal(g, p):
    tmp = tmp_glyph(p)
    tmp.adv = g.adv
    REGISTRY["V"].fn(tmp, p)
    g.add(tmp.contours)
    y = p.CAP * 0.56
    f = y / p.CAP
    cw = p.S * 0.5
    xl = p.M + (p.L + cw - p.M) * f
    xr = p.M + (p.R - cw - p.M) * f
    hbar(g, p, xl, xr, y)


@define(0x2201)
def complement(g, p):
    draw_scaled(g, p, "C", 0.84, 1.0, 1.0)


@define(0x2203)
def existential(g, p):
    tmp = tmp_glyph(p)
    tmp.adv = g.adv
    REGISTRY["E"].fn(tmp, p)
    mirror_into(g, tmp, cx=p.M + p.S * 0.06)


@define(0x2204)
def notexistential(g, p):
    existential(g, p)
    negate(g, p, 0, p.CAP, ext=p.CAP * 0.08, sx=HW(p) * 0.5)


@define(0x2205)
def emptyset(g, p):
    r = min(HW(p) * 1.08, p.CAP * 0.4)
    cy = p.CAP * 0.5
    t = T(p) * 0.95
    circle_ring(g, p.M, cy, r, t)
    a = (p.M - r * 0.92, cy - r * 1.3)
    b = (p.M + r * 0.92, cy + r * 1.3)
    g.stroke(Path(a).L(b), pen=mpen(t), start=0, end=0)


def delta_shape(g, p, top=None):
    top = p.CAP if top is None else top
    thin = 1.0 if p.sans else 0.62
    a, b = diag_between(p, p.M, top, p.L, 0, 0, 1, w=thin)
    g.stroke(Path(b, thin).L(a, thin), start=0, end=0)
    c, d = diag_between(p, p.M, top, p.R, 0, 0, -1)
    g.stroke(Path(d).L(c), start=0, end=0)
    g.rect(p.L + p.S * 0.1, 0, p.R - p.S * 0.1, p.Hb)


@define(0x2206)
def increment(g, p):
    delta_shape(g, p)


@define(0x2207)
def gradient(g, p):
    tmp = tmp_glyph(p)
    delta_shape(tmp, p)
    mirror_into(g, tmp, cy=p.CAP / 2)


@define(0x2202)
def partialdiff(g, p):
    from .parts import oval

    S, H = p.S, p.H
    x0 = p.L + S * 0.1
    x1 = p.R - S * 0.05
    bx1 = x1 - S * 0.2 - (p.R - p.L) * 0.03
    bt = p.XH * 0.9 + p.OV
    oval(g, p, x0, bx1, -p.OV, bt)
    xr = bx1 - S / 2
    yt = p.CAP + p.OV - H / 2
    bm = bt * 0.5
    cxt = p.M - (p.R - p.L) * 0.06
    xlt = x0 + S / 2 + (p.R - p.L) * 0.1
    rh = (yt - bt) * 0.5
    xb = x1 - S / 2
    path = (
        Path((xr, bm), 1.0)
        .C((xr, bt * 0.72), (xb, bt * 0.7), (xb, bt * 1.0), 1.0)
        .C((xb, bt + (yt - bt) * 0.55), (cxt + (xb - cxt) * 0.5, yt), (cxt, yt), 1.0)
        .hv((xlt, yt - rh), 0.9)
    )
    g.stroke(path, end=0)
    if p.serif:
        d = S * 1.25
        disc(g, xlt + S * 0.1, yt - rh - d * 0.1, d / 2, d / 2)


@define(0x220E)
def endofproof(g, p):
    hw = HW(p) * 0.66
    g.rect(p.M - hw, 0, p.M + hw, hw * 2.4)


# ---------------------------------------------------------------------- element of
defn(0x2208, rel("elem"))
defn(0x2209, rel("elem", "all"))
defn(0x220A, rel("elem", small=True))
defn(0x220B, rel("ni"))
defn(0x220C, rel("ni", "all"))
defn(0x220D, rel("ni", small=True))


# ---------------------------------------------------------------------- big operators
def big_box(p):
    h = BIGH(p)
    return p.L - p.S * 0.05, p.R + p.S * 0.05, p.AX - h, p.AX + h


def product_shape(g, p):
    x0, x1, y0, y1 = big_box(p)
    S, Hb = p.S, p.Hb
    xs0, xs1 = x0 + S / 2 + S * 0.12, x1 - S / 2 - S * 0.12
    vstem(g, p, xs0, y0, y1)
    vstem(g, p, xs1, y0, y1)
    g.rect(x0, y1 - Hb, x1, y1)
    if p.serif:
        ins = ((xs1 - xs0) - S) * 0.2
        serif_foot(g, p, xs0, y0, rl=ins)
        serif_foot(g, p, xs1, y0, ll=ins)


@define(0x220F, slant=False)
def product(g, p):
    product_shape(g, p)


@define(0x2210, slant=False)
def coproduct(g, p):
    tmp = tmp_glyph(p)
    tmp.adv = g.adv
    product_shape(tmp, p)
    mirror_into(g, tmp, cy=p.AX)


@define(0x2211, slant=False)
def summation(g, p):
    from .latin_upper import beak

    x0, x1, y0, y1 = big_box(p)
    S, Hb = p.S, p.Hb
    if p.serif:
        x1 -= S * 0.3
    g.rect(x0 + S * 0.05, y1 - Hb, x1, y1)
    g.rect(x0, y0, x1 + S * 0.03, y0 + Hb)
    xv = x0 + (x1 - x0) * 0.6
    xa = x0 + S * 0.45
    thin = 1.0 if p.sans else 0.6
    chevron(g, (xv, p.AX), (xa, y1 - Hb * 0.5), (xa, y0 + Hb * 0.5), p.pen,
            w1=1.0, w2=thin, lim=S * 0.9, cut1=(1, 0), cut2=(1, 0))
    beak(g, p, x1, y1 - Hb, -1, -1)
    beak(g, p, x1 + S * 0.03, y0 + Hb, -1, 1)


# ---------------------------------------------------------------------- arithmetic
@define(0x2212)
def minus(g, p):
    hw = HW(p)
    hbar(g, p, p.M - hw, p.M + hw, p.AX, sy=p.S * 0.95)


@define(0x2213)
def minusplus(g, p):
    tmp = tmp_glyph(p)
    REGISTRY["plusminus"].fn(tmp, p)
    mirror_into(g, tmp, cy=p.AX)


def plus_at(g, p, cx, cy, hw, t=None, vhw=None):
    t = TB(p) if t is None else t
    vhw = hw if vhw is None else vhw
    g.rect(cx - hw, cy - t / 2, cx + hw, cy + t / 2)
    g.rect(cx - t / 2, cy - vhw, cx + t / 2, cy + vhw)


@define(0x2214)
def dotplus(g, p):
    hw = HW(p)
    d = DOTD(p)
    cy = p.AX - d * 0.35
    plus_at(g, p, p.M, cy, hw, vhw=hw * 0.82)
    dot(g, p, p.M, cy + hw * 0.82 + WG(p) * 0.8 + d / 2, d=d, k=0.66)


@define(0x2215)
def divisionslash(g, p):
    REGISTRY["slash"].fn(g, p)


@define(0x2216)
def setminus(g, p):
    hw = HW(p) * 0.82
    hh = HW(p) * 1.55
    t = T(p)
    g.stroke(Path((p.M - hw, p.AX + hh)).L((p.M + hw, p.AX - hh)), pen=mpen(t), start=0, end=0)


def asterisk_at(g, p, cx, cy, r, t, n=6, rot=90.0):
    for i in range(n):
        a = math.radians(rot + i * 360.0 / n)
        tip = (cx + r * math.cos(a), cy + r * math.sin(a))
        g.stroke(Path((cx, cy), 1.0).L(tip, 0.84), pen=mpen(t))


@define(0x2217)
def asteriskmath(g, p):
    r = HW(p) * 0.86
    asterisk_at(g, p, p.M, p.AX, r, min(TB(p) * 0.92, r * 0.52))


@define(0x2218)
def ringoperator(g, p):
    r = HW(p) * 0.5 + p.S * 0.12
    circle_ring(g, p.M, p.AX, r, min(T(p) * 0.82, r * 0.6))


@define(0x2219)
def bulletoperator(g, p):
    d = pdot_d(p) * 1.12
    dot(g, p, p.M, p.AX, d=d, k=0.66)


# ---------------------------------------------------------------------- radicals
def radical_shape(g, p, x0=None):
    S = p.S
    x0 = p.L - S * 0.1 if x0 is None else x0
    yb = p.CAP + 120
    xb = x0 + (p.R - p.L) * 0.16
    yB = p.CAP * 0.46
    xv = x0 + (p.R - p.L) * 0.46
    yv = -40
    xu = p.R - (p.R - p.L) * 0.06
    yu = yb - p.Hb * 0.5
    thin = 0.55 if p.serif else 0.72
    chevron(g, (xv, yv), (xb, yB), (xu, yu), p.pen, w1=1.0, w2=thin, lim=S * 0.5, cut2=(1, 0))
    # lead-in tick
    g.stroke(Path((x0, yB - p.CAP * 0.05), 0.6).L((xb + S * 0.2, yB + S * 0.12), 0.75), start="butt", end="butt")
    # vinculum to the cell edge
    g.rect(xu - S * 0.2, yb - p.Hb, p.W, yb)
    return x0, xb, yB


@define(0x221A, slant=False)
def radical(g, p):
    radical_shape(g, p)


def root_index(g, p, name):
    x0, xb, yB = radical_shape(g, p)
    f = 0.44
    cx = (x0 + xb) / 2 + p.S * 0.1
    draw_scaled(g, p, name, f * 0.95, f, 0.62, dx=cx - p.M, dy=yB + p.S * 0.4 + 30)


@define(0x221B, slant=False)
def cuberoot(g, p):
    root_index(g, p, "three")


@define(0x221C, slant=False)
def fourthroot(g, p):
    root_index(g, p, "four")


# ---------------------------------------------------------------------- infinity, proportional
def lobe_path(cx, cy, xr, h, out_w=1.0, mid_w=0.8):
    """Right lobe of an infinity sign: from the crossing at (cx, cy) around
    a loop reaching x = xr and back (centre line)."""
    d = xr - cx
    xt = cx + d * 0.5
    path = (
        Path((cx, cy), mid_w)
        .C((cx + d * 0.18, cy + h * 0.42), (xt - d * 0.28, cy + h), (xt, cy + h), out_w)
        .hv((xr, cy), out_w)
        .vh((xt, cy - h), out_w)
        .C((xt - d * 0.28, cy - h), (cx + d * 0.18, cy - h * 0.42), (cx, cy), mid_w)
    )
    return path


@define(0x221E)
def infinity(g, p):
    hw = HW(p) * 1.12
    t = TB(p) * 0.92
    h = hw * 0.5 - t * 0.25
    tmp = tmp_glyph(p)
    tmp.stroke(lobe_path(p.M, p.AX, p.M + hw - t / 2, h), pen=mpen(t))
    g.add([c.copy() for c in tmp.contours])
    mirror_into(g, tmp, cx=p.M)


@define(0x221D)
def proportional(g, p):
    hw = HW(p) * 1.05
    t = TB(p) * 0.92
    h = hw * 0.5 - t * 0.25
    cx = p.M + hw * 0.12
    xl = p.M - hw + t / 2
    xr = p.M + hw
    tmp = tmp_glyph(p)
    tmp.stroke(lobe_path(cx, p.AX, xl, h), pen=mpen(t))
    g.add(tmp.contours)
    d = xr - cx
    up = Path((cx, p.AX), 0.8).C((cx + d * 0.25, p.AX + h * 0.7), (cx + d * 0.55, p.AX + h), (xr, p.AX + h), 1.0)
    lo = Path((cx, p.AX), 0.8).C((cx + d * 0.25, p.AX - h * 0.7), (cx + d * 0.55, p.AX - h), (xr, p.AX - h), 1.0)
    g.stroke(up, pen=mpen(t))
    g.stroke(lo, pen=mpen(t))


# ---------------------------------------------------------------------- angles
def rbox(p, f=1.0):
    hw = HW(p) * f
    return p.M - hw, p.M + hw, p.AX - hw, p.AX + hw


@define(0x221F)
def orthogonal(g, p):
    x0, x1, y0, y1 = rbox(p, 1.05)
    t = T(p)
    g.stroke(Path((x0 + t / 2, y1)).L((x0 + t / 2, y0 + t / 2)).L((x1, y0 + t / 2)), pen=mpen(t))


def angle_sym(g, p):
    x0, x1, y0, y1 = rbox(p, 1.05)
    t = T(p)
    apex = (x0 + t * 1.0, y0 + t / 2)
    chevron(g, apex, (x1, y0 + t / 2), (x1 - t * 0.2, y1 - t / 2), mpen(t), lim=t * 1.4, cut1=(0, 1), cut2=(1, 0))
    return apex, x0, x1, y0, y1, t


def arc_path(cx, cy, r, a0, a1, w=1.0, n=None):
    """Circular arc a0 -> a1 (degrees) as n cubic pieces (n fixed by the
    angles given, which are constants of each glyph)."""
    if n is None:
        n = max(1, int(math.ceil(abs(a1 - a0) / 90.0 - 1e-9)))
    da = (a1 - a0) / n
    k = 4 / 3 * math.tan(math.radians(da) / 4)
    pt = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))  # noqa: E731
    path = Path(pt(a0), w)
    for i in range(n):
        s = a0 + i * da
        e = s + da
        ps, pe = pt(s), pt(e)
        ts = (-math.sin(math.radians(s)), math.cos(math.radians(s)))
        te = (-math.sin(math.radians(e)), math.cos(math.radians(e)))
        c1 = (ps[0] + ts[0] * k * r, ps[1] + ts[1] * k * r)
        c2 = (pe[0] - te[0] * k * r, pe[1] - te[1] * k * r)
        path.C(c1, c2, pe, w)
    return path


@define(0x2220)
def angle(g, p):
    angle_sym(g, p)


@define(0x2221)
def measuredangle(g, p):
    apex, x0, x1, y0, y1, t = angle_sym(g, p)
    ang = math.degrees(math.atan2((y1 - t / 2) - apex[1], (x1 - t * 0.2) - apex[0]))
    r = (x1 - x0) * 0.62
    g.stroke(arc_path(apex[0], apex[1], r, 0, ang + 12, n=1), pen=mpen(t * 0.75))


@define(0x2222)
def sphericalangle(g, p):
    x0, x1, y0, y1 = rbox(p, 1.0)
    t = T(p)
    pts = angle_poly(p, x0, x1, y0 + (y1 - y0) * 0.06, y1 - (y1 - y0) * 0.06, t)
    fill_poly(g, pts)
    r = (x1 - x0) * 0.6
    ta = min(t * 0.8, r * 0.3)
    g.stroke(arc_path(x0 + t * 0.4, p.AX, r, -42, 42, n=1), pen=mpen(ta))


# ---------------------------------------------------------------------- divides, parallel
def tall_bars(g, p, xs, t=None, f=1.0):
    t = T(p) if t is None else t
    h = TALL(p) * f
    for x in xs:
        g.rect(x - t / 2, p.AX - h, x + t / 2, p.AX + h)
    return p.AX - h, p.AX + h


def short_slash(g, p, cy, hw, hh, t=None, cx=None):
    t = T(p) if t is None else t
    cx = p.M if cx is None else cx
    g.stroke(Path((cx - hw, cy - hh)).L((cx + hw, cy + hh)), pen=mpen(t), start=0, end=0)


def par_off(p):
    return max(p.S * 0.9, HW(p) * 0.36)


@define(0x2223)
def divides(g, p):
    tall_bars(g, p, [p.M])


@define(0x2224)
def notdivides(g, p):
    tall_bars(g, p, [p.M])
    short_slash(g, p, p.AX, HW(p) * 0.55, HW(p) * 0.42)


@define(0x2225)
def parallel(g, p):
    o = par_off(p)
    tall_bars(g, p, [p.M - o, p.M + o])


@define(0x2226)
def notparallel(g, p):
    o = par_off(p)
    tall_bars(g, p, [p.M - o, p.M + o])
    short_slash(g, p, p.AX, HW(p) * 0.78, HW(p) * 0.5)


defn(0x2227, rel("wedge"))
defn(0x2228, rel("vee"))
defn(0x2229, rel("cap"))
defn(0x222A, rel("cup"))


# ====================================================================== integrals
INT_DISP = (0.15, 0.08, 0.05, 0.04)
INT_WF = (1.0, 0.82, 0.7, 0.6)


def int_metrics(p):
    """y0, y1 (ink), available centre-line width aw."""
    y0, y1 = p.BB, p.BT
    t = p.S * 0.9
    aw = p.W * 0.98 - t
    return y0, y1, aw


def int_wf(p, n=1):
    return INT_WF[n - 1] * (1 - 0.15 * (p.S / 144) ** 2)


def integral_shape(g, p, cx, r, disp, wf=1.0, y0=None, y1=None, ball=None):
    """Slanted calligraphic integral sign: stem centre cx, hook radius r,
    horizontal displacement of the stem ends +-disp.  Returns (ym, t)."""
    Y0, Y1, AW = int_metrics(p)
    y0 = Y0 if y0 is None else y0
    y1 = Y1 if y1 is None else y1
    t = p.S * 0.9 * wf
    w = t / 2
    ym = (y0 + y1) / 2
    sh = disp / (y1 - ym)
    rh = r * 1.45
    yt = y1 - w * 0.55
    yb = y0 + w * 0.55
    yst, ysb = yt - rh, yb + rh
    ball = p.serif if ball is None else ball
    we = 0.46 if ball else 0.52
    k = 0.62
    nodes = [
        ((cx + 2 * r, yt - rh * 0.8), we),
        ("A", "vh", (cx + r, yt), 0.56, k),
        ("A", "hv", (cx, yst), 0.8, k),
        ("C", (cx, yst - (yst - ym) * 0.4), (cx, ym + (yst - ym) * 0.4), (cx, ym), 1.15),
        ("C", (cx, ym - (ym - ysb) * 0.4), (cx, ysb + (ym - ysb) * 0.4), (cx, ysb), 0.8),
        ("A", "vh", (cx - r, yb), 0.56, k),
        ("A", "hv", (cx - 2 * r, yb + rh * 0.8), we, k),
    ]
    path = sheared_path(nodes, sh, ym)
    g.stroke(path, pen=mpen(t), start="butt", end="butt")
    if ball:
        d = t * 1.2
        f = lambda q: (q[0] + (q[1] - ym) * sh, q[1])  # noqa: E731
        a = f((cx + 2 * r - d * 0.08, yt - rh * 0.8 - d * 0.12))
        b = f((cx - 2 * r + d * 0.08, yb + rh * 0.8 + d * 0.12))
        disc(g, a[0], a[1], d / 2)
        disc(g, b[0], b[1], d / 2)
    return ym, t


def multi_integral(g, p, n, ring=None):
    y0, y1, aw = int_metrics(p)
    wf = int_wf(p, n)
    t = p.S * 0.9 * wf
    disp = aw * INT_DISP[n - 1]
    gap = t * 1.25
    r = (aw - 2 * disp - (n - 1) * gap) / (4 + 2 * (n - 1))
    step = 2 * r + gap
    ym = (y0 + y1) / 2
    for i in range(n):
        cx = p.M + (i - (n - 1) / 2) * step
        integral_shape(g, p, cx, r, disp, wf)
    return ym, wf


def contour_ring(g, p, ym, rx, wf, arrow=0):
    ry = min(rx * 0.9, p.XH * 0.4)
    t = min(T(p) * 0.75 * wf, ry * 0.3)
    if arrow == 0:
        ellipse_ring(g, p.M, ym, rx, ry, t)
        return
    # open ring with an arrow head (arrow=+1 clockwise, -1 anticlockwise)
    sgn = arrow
    a0, a1 = (110, -200) if sgn > 0 else (70, 380)
    path = ellipse_arc_path(p.M, ym, rx - t / 2, ry - t / 2, a0, a1, 3)
    g.stroke(path, pen=mpen(t))
    tip_a = a1
    tip = (p.M + (rx - t / 2) * math.cos(math.radians(tip_a)), ym + (ry - t / 2) * math.sin(math.radians(tip_a)))
    tang = unit((-(rx) * math.sin(math.radians(tip_a)) * (1 if sgn < 0 else -1),
                 (ry) * math.cos(math.radians(tip_a)) * (1 if sgn < 0 else -1)))
    small_head(g, tip, tang, t, size=rx * 0.5)


def ellipse_arc_path(cx, cy, rx, ry, a0, a1, n):
    da = (a1 - a0) / n
    k = 4 / 3 * math.tan(math.radians(da) / 4)
    pt = lambda a: (cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))  # noqa: E731
    tg = lambda a: (-rx * math.sin(math.radians(a)), ry * math.cos(math.radians(a)))  # noqa: E731
    path = Path(pt(a0))
    for i in range(n):
        s, e = a0 + i * da, a0 + (i + 1) * da
        ps, pe, ts, te = pt(s), pt(e), tg(s), tg(e)
        path.C((ps[0] + ts[0] * k, ps[1] + ts[1] * k), (pe[0] - te[0] * k, pe[1] - te[1] * k), pe)
    return path


def small_head(g, tip, d, t, size):
    """Open chevron arrowhead at tip pointing along unit d."""
    nrm = perp(d)
    back = mul(d, -size * 0.85)
    e1 = add(add(tip, back), mul(nrm, size * 0.75))
    e2 = add(add(tip, back), mul(nrm, -size * 0.75))
    chevron(g, tip, e1, e2, mpen(t), lim=t * 1.2)


@define(0x222B, slant=False)
def integral(g, p):
    multi_integral(g, p, 1)


@define(0x222C, slant=False)
def dblintegral(g, p):
    multi_integral(g, p, 2)


@define(0x222D, slant=False)
def tripleintegral(g, p):
    multi_integral(g, p, 3)


@define(0x222E, slant=False)
def contourintegral(g, p):
    ym, wf = multi_integral(g, p, 1)
    contour_ring(g, p, ym, int_metrics(p)[2] * 0.3, wf)


@define(0x222F, slant=False)
def surfaceintegral(g, p):
    ym, wf = multi_integral(g, p, 2)
    contour_ring(g, p, ym, int_metrics(p)[2] * 0.4, wf)


@define(0x2230, slant=False)
def volumeintegral(g, p):
    ym, wf = multi_integral(g, p, 3)
    contour_ring(g, p, ym, int_metrics(p)[2] * 0.47, wf)


@define(0x2231, slant=False)
def clockwiseintegral(g, p):
    ym, wf = multi_integral(g, p, 1)
    t = T(p) * 0.72 * wf
    r = int_metrics(p)[2] * 0.24
    cx = p.M
    path = arc_path(cx, ym, r, 160, -100, n=3)
    g.stroke(path, pen=mpen(t))
    a = math.radians(-100)
    tip = (cx + r * math.cos(a), ym + r * math.sin(a))
    small_head(g, tip, (math.sin(a), -math.cos(a)), t, r * 0.62)


@define(0x2232, slant=False)
def clockwisecontourintegral(g, p):
    ym, wf = multi_integral(g, p, 1)
    contour_ring(g, p, ym, int_metrics(p)[2] * 0.3, wf, arrow=1)


@define(0x2233, slant=False)
def anticlockwisecontourintegral(g, p):
    ym, wf = multi_integral(g, p, 1)
    contour_ring(g, p, ym, int_metrics(p)[2] * 0.3, wf, arrow=-1)


# ====================================================================== dots
def odot(g, p, x, y, f=1.0):
    d = DOTD(p) * f
    dot(g, p, x, y, d=d, k=0.66)


def dot_vs(p):
    """Vertical offset of colon-like dots from the axis."""
    d = DOTD(p)
    return max((p.XH - d) * 0.36, d * 0.75 + WG(p) * 0.4)


def dot_hs(p):
    return HW(p) * 0.72


@define(0x2234)
def therefore(g, p):
    vs, hs = dot_vs(p), dot_hs(p)
    odot(g, p, p.M, p.AX + vs)
    odot(g, p, p.M - hs, p.AX - vs)
    odot(g, p, p.M + hs, p.AX - vs)


@define(0x2235)
def because(g, p):
    vs, hs = dot_vs(p), dot_hs(p)
    odot(g, p, p.M, p.AX - vs)
    odot(g, p, p.M - hs, p.AX + vs)
    odot(g, p, p.M + hs, p.AX + vs)


@define(0x2236)
def ratio(g, p):
    vs = dot_vs(p)
    odot(g, p, p.M, p.AX + vs)
    odot(g, p, p.M, p.AX - vs)


@define(0x2237)
def proportion(g, p):
    vs, hs = dot_vs(p), dot_hs(p)
    for sx in (-1, 1):
        for sy in (-1, 1):
            odot(g, p, p.M + sx * hs, p.AX + sy * vs)


@define(0x2238)
def dotminus(g, p):
    minus(g, p)
    odot(g, p, p.M, p.AX + dot_vs(p))


@define(0x2239)
def excess(g, p):
    hw = HW(p)
    hbar(g, p, p.M - hw, p.M + hw * 0.25, p.AX, sy=p.S * 0.95)
    vs = dot_vs(p) * 0.8
    odot(g, p, p.M + hw * 0.75, p.AX + vs, 0.9)
    odot(g, p, p.M + hw * 0.75, p.AX - vs, 0.9)


@define(0x223A)
def geometricproportion(g, p):
    minus(g, p)
    vs, hs = dot_vs(p), dot_hs(p)
    for sx in (-1, 1):
        for sy in (-1, 1):
            odot(g, p, p.M + sx * hs, p.AX + sy * vs, 0.9)


@define(0x223B)
def homothetic(g, p):
    hw = HW(p)
    t = T(p)
    th = tilde_h(p, t, 0.8)
    prim_tilde(g, p, p.M - hw, p.M + hw, p.AX - th / 2, p.AX + th / 2, t)
    vs = th / 2 + WG(p) * 0.7 + DOTD(p) * 0.45
    odot(g, p, p.M, p.AX + vs, 0.9)
    odot(g, p, p.M, p.AX - vs, 0.9)


def tilde_full(g, p, rev=False, cy=None):
    hw = HW(p)
    t = TB(p)
    th = tilde_h(p, t, 1.0)
    cy = p.AX if cy is None else cy
    prim_tilde(g, p, p.M - hw, p.M + hw, cy - th / 2, cy + th / 2, t, rev=rev)
    return cy - th / 2, cy + th / 2


@define(0x223C)
def similar(g, p):
    tilde_full(g, p)


@define(0x223D)
def reversedtilde(g, p):
    tilde_full(g, p, rev=True)


@define(0x223E)
def invertedlazys(g, p):
    hw = HW(p)
    t = TB(p) * 0.92
    a = hw * 0.42
    x0, x1 = p.M - hw + t / 2, p.M + hw - t / 2
    cy = p.AX
    lw = (x1 - x0) * 0.24
    path = (
        Path((x0 + lw * 1.5, cy - a * 0.15))
        .C((x0 + lw * 1.5, cy - a * 0.75), (x0, cy - a * 0.75), (x0, cy), 0.95)
        .C((x0, cy + a * 0.9), (x0 + lw * 1.6, cy + a), (p.M, cy), 1.0)
        .C((x1 - lw * 1.6, cy - a), (x1, cy - a * 0.9), (x1, cy), 1.0)
        .C((x1, cy + a * 0.75), (x1 - lw * 1.5, cy + a * 0.75), (x1 - lw * 1.5, cy + a * 0.15), 0.95)
    )
    g.stroke(path, pen=mpen(t))


@define(0x223F)
def sinewave(g, p):
    hw = HW(p)
    t = TB(p) * 0.92
    a = hw * 0.45
    x0, x1 = p.M - hw, p.M + hw
    q = (x1 - x0) / 4
    k = 0.36
    cy = p.AX
    path = (
        Path((x0, cy))
        .C((x0 + q * k, cy + a * 0.9), (x0 + q * (1 - k * 0.5), cy + a), (x0 + q, cy + a))
        .C((x0 + q * (1 + k * 0.5), cy + a), (p.M - q * k, cy + a * 0.9), (p.M, cy))
        .C((p.M + q * k, cy - a * 0.9), (p.M + q * (1 - k * 0.5), cy - a), (p.M + q, cy - a))
        .C((p.M + q * (1 + k * 0.5), cy - a), (x1 - q * k, cy - a * 0.9), (x1, cy))
    )
    g.stroke(path, pen=mpen(t))


@define(0x2240)
def wreathproduct(g, p):
    h = HW(p) * 1.25
    prim_vtilde(g, p, p.M, p.AX - h, p.AX + h, HW(p) * 0.32, TB(p) * 0.92)


# ---------------------------------------------------------------------- tilde relations
TILDE_RELS = {
    0x2241: ("tilde", "all"), 0x2242: ("bar tilde", None), 0x2243: ("tilde bar", None),
    0x2244: ("tilde bar", "all"), 0x2245: ("tilde bar bar", None), 0x2246: ("tilde bar bar", 2),
    0x2247: ("tilde bar bar", "all"), 0x2248: ("tilde tilde", None), 0x2249: ("tilde tilde", "all"),
    0x224A: ("tilde tilde bar", None), 0x224B: ("tilde tilde tilde", None), 0x224C: ("rtilde bar bar", None),
}


def tilde_rel(spec, neg):
    base = rel(spec, neg)

    def fn(g, p):
        if spec == "tilde":
            y0, y1 = tilde_full(g, p)
            if neg:
                negate(g, p, y0, y1)
            return
        base(g, p)

    return fn


for _cp, (_s, _n) in TILDE_RELS.items():
    defn(_cp, tilde_rel(_s, _n))


def arcpair_draw(g, p, x0, x1, y0, y1, t, away=False):
    """Two arcs: upper one a smile, lower a frown (equivalent to)."""
    hw = (x1 - x0) / 2 * 0.92
    cx = (x0 + x1) / 2
    h = (y1 - y0 - WG(p) * 0.8) / 2
    w = t / 2
    ru = h - t
    up_y = y1 - w
    lo_y = y0 + w
    if away:
        up = Path((cx - hw, up_y - ru)).vh((cx, up_y)).hv((cx + hw, up_y - ru))
        lo = Path((cx - hw, lo_y + ru)).vh((cx, lo_y)).hv((cx + hw, lo_y + ru))
    else:
        up = Path((cx - hw, up_y)).vh((cx, up_y - ru)).hv((cx + hw, up_y))
        lo = Path((cx - hw, lo_y)).vh((cx, lo_y + ru)).hv((cx + hw, lo_y))
    g.stroke(up, pen=mpen(t))
    g.stroke(lo, pen=mpen(t))


def asymp(neg=False):
    def fn(g, p):
        hw = HW(p)
        t = T(p)
        h = eq_gap(p) + t + HW(p) * 0.36
        arcpair_draw(g, p, p.M - hw, p.M + hw, p.AX - h / 2, p.AX + h / 2, t)
        if neg:
            negate(g, p, p.AX - h / 2, p.AX + h / 2)

    return fn


defn(0x224D, asymp())
defn(0x226D, asymp(True))
defn(0x224E, rel("bump dbump"))
defn(0x224F, rel("bump bar"))
defn(0x2250, rel("dot bar bar"))
defn(0x2251, rel("dot bar bar dot"))


def eq_bars(g, p, x0=None, x1=None, cy=None, t=None, gap=None):
    hw = HW(p)
    x0 = p.M - hw if x0 is None else x0
    x1 = p.M + hw if x1 is None else x1
    cy = p.AX if cy is None else cy
    t = T(p) if t is None else t
    gap = eq_gap(p) if gap is None else gap
    g.rect(x0, cy + gap / 2 - t / 2, x1, cy + gap / 2 + t / 2)
    g.rect(x0, cy - gap / 2 - t / 2, x1, cy - gap / 2 + t / 2)
    return cy - gap / 2 - t / 2, cy + gap / 2 + t / 2


def eq_diag_dots(rising):
    def fn(g, p):
        y0, y1 = eq_bars(g, p)
        d = DOTD(p)
        vs = (y1 - y0) / 2 + WG(p) * 0.8 + d / 2
        hs = HW(p) * 0.72
        s = 1 if rising else -1
        odot(g, p, p.M - s * hs, p.AX + vs)
        odot(g, p, p.M + s * hs, p.AX - vs)

    return fn


defn(0x2252, eq_diag_dots(False))
defn(0x2253, eq_diag_dots(True))


def colon_eq(rev=False, dbl=False, eqn=2):
    def fn(g, p):
        hw = HW(p) * 1.08
        d = min(DOTD(p) * 0.9, (eq_gap(p) + T(p)) * 0.4)
        cw = d * (1.0 if not dbl else 2.2)
        gapx = WG(p) * 0.7
        if not rev:
            cx0 = p.M - hw + d / 2
            bx0, bx1 = p.M - hw + cw + gapx, p.M + hw
        else:
            cx0 = p.M + hw - cw + d / 2
            bx0, bx1 = p.M - hw, p.M + hw - cw - gapx
        if eqn == 2:
            y0, y1 = eq_bars(g, p, bx0, bx1)
        else:
            gp = eq_gap(p) * 0.82
            t = T(p) * 0.9
            for k in (-1, 0, 1):
                g.rect(bx0, p.AX + k * gp - t / 2, bx1, p.AX + k * gp + t / 2)
            y0, y1 = p.AX - gp - t / 2, p.AX + gp + t / 2
        vs = (y1 - y0) / 2 - d / 2 + d * 0.05
        for i in range(2 if dbl else 1):
            for s in (-1, 1):
                dot(g, p, cx0 + i * d * 1.2, p.AX + s * vs, d=d, k=0.66)

    return fn


defn(0x2254, colon_eq())
defn(0x2255, colon_eq(rev=True))


@define(0x2256)
def ringinequal(g, p):
    y0, y1 = eq_bars(g, p)
    r = (y1 - y0) / 2 * 0.62 + p.S * 0.1
    circle_ring(g, p.M, p.AX, r, min(T(p) * 0.85, r * 0.55))


defn(0x2257, rel("ring bar bar"))
defn(0x2258, rel("frown bar bar"))
defn(0x2259, rel("hat bar bar"))
defn(0x225A, rel("vhat bar bar"))
defn(0x225B, rel("star bar bar"))
defn(0x225C, rel("tri bar bar"))


def text_eq(names, fy=0.4, fx=0.33):
    def fn(g, p):
        y0, y1 = eq_bars(g, p, cy=p.AX - HW(p) * 0.3)
        draw_scaled_row(g, p, names, y1 + WG(p) * 0.8, fx, fy)

    return fn


def draw_scaled_row(g, p, names, ybase, fx, fy, wf=0.62):
    n = len(names)
    step = (p.R - p.L) * fx * 1.02
    for i, nm in enumerate(names):
        dx = (i - (n - 1) / 2) * step
        draw_scaled(g, p, nm, fx, fy, wf, dx=dx, dy=ybase)


defn(0x225D, text_eq(["d", "e", "f"], fy=0.36, fx=0.31))
defn(0x225E, text_eq(["m"], fy=0.4, fx=0.5))


@define(0x225F)
def questionedequal(g, p):
    y0, y1 = eq_bars(g, p, cy=p.AX - HW(p) * 0.3)
    draw_scaled(g, p, "question", 0.5, 0.36, 0.62, dy=y1 + WG(p) * 0.8)


defn(0x2260, rel("bar bar", "all"))


def bars_n(n, neg=False):
    def fn(g, p):
        t = T(p) * (1.0 if n < 4 else 0.85)
        gp = eq_gap(p) * (0.86 if n == 3 else 0.68)
        hw = HW(p)
        ys = [(i - (n - 1) / 2) * gp for i in range(n)]
        for y in ys:
            g.rect(p.M - hw, p.AX + y - t / 2, p.M + hw, p.AX + y + t / 2)
        if neg:
            negate(g, p, p.AX + ys[0] - t / 2, p.AX + ys[-1] + t / 2)

    return fn


defn(0x2261, bars_n(3))
defn(0x2262, bars_n(3, True))
defn(0x2263, bars_n(4))

for _cp, _spec, _neg in [
    (0x2264, "lt bar", None), (0x2265, "gt bar", None),
    (0x2266, "lt bar bar", None), (0x2267, "gt bar bar", None),
    (0x2268, "lt bar bar", 2), (0x2269, "gt bar bar", 2),
    (0x226E, "lt", "all"), (0x226F, "gt", "all"),
    (0x2270, "lt bar", "all"), (0x2271, "gt bar", "all"),
    (0x2272, "lt tilde", None), (0x2273, "gt tilde", None),
    (0x2274, "lt tilde", "all"), (0x2275, "gt tilde", "all"),
    (0x2276, "lt gt", None), (0x2277, "gt lt", None),
    (0x2278, "lt gt", "all"), (0x2279, "gt lt", "all"),
    (0x227A, "prec", None), (0x227B, "succ", None),
    (0x227C, "prec cbar", None), (0x227D, "succ cbarr", None),
    (0x227E, "prec tilde", None), (0x227F, "succ tilde", None),
]:
    defn(_cp, rel(_spec, _neg))


def nested(kind, n, right=False):
    """Much less-than: n angles side by side."""

    def fn(g, p):
        hw = HW(p)
        t = T(p) * (1.0 if n == 2 else 0.88)
        y0, y1 = p.AX - hw * 0.95, p.AX + hw * 0.95
        total = 2 * hw * 1.06
        wid = total * (0.62 if n == 2 else 0.5)
        step = (total - wid) / (n - 1)
        x0 = p.M - total / 2
        for i in range(n):
            a = x0 + i * step
            if kind == "lt":
                fill_poly(g, angle_poly(p, a, a + wid, y0, y1, t, tip_left=not right))
            else:
                tmp = tmp_glyph(p)
                prim_prec(tmp, p, a, a + wid, y0, y1, t, right=right)
                g.add(tmp.contours)

    return fn


defn(0x226A, nested("lt", 2))
defn(0x226B, nested("lt", 2, True))


@define(0x226C)
def between(g, p):
    h = TALL(p) * 0.92
    t = T(p)
    hw = HW(p) * 0.62
    xl, xr = p.M - hw, p.M + hw
    y0, y1 = p.AX - h, p.AX + h
    for s in (-1, 1):
        xe = p.M + s * hw
        xm = p.M - s * t * 0.1
        path = Path((xe, y1), 0.85).C((xe - s * hw * 0.2, y1 - h * 0.45), (xm, p.AX + h * 0.35), (xm, p.AX), 1.0)
        path.C((xm, p.AX - h * 0.35), (xe - s * hw * 0.2, y0 + h * 0.45), (xe, y0), 0.85)
        g.stroke(path, pen=mpen(t), start=0, end=0)


# ---------------------------------------------------------------------- U+2280..
for _cp, _spec, _neg in [
    (0x2280, "prec", "all"), (0x2281, "succ", "all"),
    (0x2282, "sub", None), (0x2283, "sup", None), (0x2284, "sub", "all"), (0x2285, "sup", "all"),
    (0x2286, "sub bar", None), (0x2287, "sup bar", None),
    (0x2288, "sub bar", "all"), (0x2289, "sup bar", "all"),
    (0x228A, "sub bar", 1), (0x228B, "sup bar", 1),
    (0x228F, "sqsub", None), (0x2290, "sqsup", None),
    (0x2291, "sqsub bar", None), (0x2292, "sqsup bar", None),
    (0x2293, "sqcap", None), (0x2294, "sqcup", None),
]:
    defn(_cp, rel(_spec, _neg))


def cup_with(inner):
    def fn(g, p):
        hw = HW(p)
        t = T(p)
        x0, x1, y0, y1 = p.M - hw, p.M + hw, p.AX - hw, p.AX + hw
        prim_cup(g, p, x0, x1, y0, y1, t)
        cx, cy = p.M, (y0 + t + y1) / 2 + hw * 0.05
        iw = (x1 - x0) / 2 - t - WG(p) * 0.45
        ti = t * 0.85
        if inner == "plus":
            plus_at(g, p, cx, cy, iw, t=ti)
        elif inner == "dot":
            odot(g, p, cx, cy, 0.95)
        elif inner == "arrow":
            g.rect(cx - iw, cy - ti / 2, cx + iw, cy + ti / 2)
            small_head(g, (cx - iw, cy), (-1, 0), ti, iw * 0.9)

    return fn


defn(0x228C, cup_with("arrow"))
defn(0x228D, cup_with("dot"))
defn(0x228E, cup_with("plus"))


# ---------------------------------------------------------------------- circled / squared
def circ_r(p):
    return min(HW(p) * 1.12, p.W * 0.47)


def circ_t(p):
    return T(p) * 0.85


def enclosed(inner, square=False, big=False):
    def fn(g, p):
        cx, cy = p.M, p.AX
        if big:
            x0, x1, y0, y1 = big_box(p)
            r = min((x1 - x0) / 2, BIGH(p)) * 0.98
            t = p.S * 0.88
            cy = p.AX
        else:
            r = circ_r(p) * (0.93 if square else 1.0)
            t = fit_t(p, circ_t(p), 2 * r, ENC_N.get(inner, 3))
        if square:
            poly_ring(g, [(cx - r, cy - r), (cx - r, cy + r), (cx + r, cy + r), (cx + r, cy - r)], t)
        else:
            circle_ring(g, cx, cy, r, t)
        ri = r - t / 2  # strokes end in the middle of the wall
        inner_draw(g, p, inner, cx, cy, r, t, ri, square)

    return fn


ENC_N = {"eq": 4, "par": 4, "ring": 4, "wbullet": 4, "wsq": 4, "ast": 3.4, "lt": 3.4, "gt": 3.4}


def inner_draw(g, p, inner, cx, cy, r, t, ri, square=False):
    if inner == "plus":
        plus_at(g, p, cx, cy, ri, t=t)
    elif inner == "minus":
        g.rect(cx - ri, cy - t / 2, cx + ri, cy + t / 2)
    elif inner == "times":
        e = ri if square else ri / math.sqrt(2)
        for sx in (-1, 1):
            g.stroke(Path((cx - e, cy - sx * e)).L((cx + e, cy + sx * e)), pen=mpen(t))
    elif inner == "slash":
        e = ri if square else ri / math.sqrt(2)
        g.stroke(Path((cx - e, cy - e)).L((cx + e, cy + e)), pen=mpen(t))
    elif inner == "bslash":
        e = ri if square else ri / math.sqrt(2)
        g.stroke(Path((cx - e, cy + e)).L((cx + e, cy - e)), pen=mpen(t))
    elif inner == "dot":
        d = min(DOTD(p) * 1.05, (r - t) * 0.9)
        dot(g, p, cx, cy, d=d, k=0.66)
    elif inner == "ring":
        rr = (r - t) * 0.55
        circle_ring(g, cx, cy, rr, min(t * 0.85, rr * 0.55))
    elif inner == "ast":
        asterisk_at(g, p, cx, cy, (r - t) * 0.72, t * 0.85)
    elif inner == "eq":
        gp = min(eq_gap(p), (r - t) * 0.95)
        for s in (-1, 1):
            y = s * gp / 2
            xe = math.sqrt(max(ri * ri - y * y, 1)) if not square else ri
            g.rect(cx - xe, cy + y - t * 0.45, cx + xe, cy + y + t * 0.45)
    elif inner == "dash":
        e = (r - t) * 0.6
        g.rect(cx - e, cy - t / 2, cx + e, cy + t / 2)
    elif inner == "vbar":
        g.rect(cx - t / 2, cy - ri, cx + t / 2, cy + ri)
    elif inner == "par":
        o = (r - t) * 0.32
        for s in (-1, 1):
            e = math.sqrt(max(ri * ri - o * o, 1)) if not square else ri
            g.rect(cx + s * o - t * 0.45, cy - e, cx + s * o + t * 0.45, cy + e)
    elif inner == "perp":
        e = (r - t) * 0.62
        g.rect(cx - t / 2, cy - e * 0.75, cx + t / 2, cy + e)
        g.rect(cx - e, cy - e * 0.75 - t, cx + e, cy - e * 0.75)
    elif inner == "lt" or inner == "gt":
        e = (r - t) * 0.72
        fill_poly(g, angle_poly(p, cx - e, cx + e, cy - e * 0.85, cy + e * 0.85, t * 0.9, tip_left=inner == "lt"))
    elif inner == "hbar":
        g.rect(cx - ri, cy - t / 2, cx + ri, cy + t / 2)
    elif inner == "bullet":
        d = (r - t) * 1.1
        dot(g, p, cx, cy, d=d, k=0.66)
    elif inner == "wbullet":
        rr = (r - t) * 0.6
        circle_ring(g, cx, cy, rr, min(t * 0.85, rr * 0.5))
    elif inner == "sq":
        e = (r - t) * 0.5
        g.rect(cx - e, cy - e, cx + e, cy + e)
    elif inner == "wsq":
        e = (r - t) * 0.55
        poly_ring(g, [(cx - e, cy - e), (cx - e, cy + e), (cx + e, cy + e), (cx + e, cy - e)], min(t * 0.8, e * 0.5))
    elif inner == "none":
        pass
    else:
        raise ValueError(inner)


for _cp, _inner in [(0x2295, "plus"), (0x2296, "minus"), (0x2297, "times"), (0x2298, "slash"),
                    (0x2299, "dot"), (0x229A, "ring"), (0x229B, "ast"), (0x229C, "eq"), (0x229D, "dash")]:
    defn(_cp, enclosed(_inner))
for _cp, _inner in [(0x229E, "plus"), (0x229F, "minus"), (0x22A0, "times"), (0x22A1, "dot")]:
    defn(_cp, enclosed(_inner, square=True))


# ---------------------------------------------------------------------- tacks
def tack(nstems=1, nbars=1, short=False, neg=False, d="right", cross=False):
    def fn(g, p):
        tmp = tmp_glyph(p)
        hw = HW(p)
        t = T(p)
        x0, x1 = p.M - hw, p.M + hw
        y0, y1 = p.AX - hw * 1.02, p.AX + hw * 1.02
        sg = WG(p) * 0.85
        if nstems > 1:
            t = fit_t(p, t, (x1 - x0) * 0.72, nstems, 0.5)
            sg = min(sg, ((x1 - x0) * 0.72 - nstems * t) / (nstems - 1))
        xs = [x0 + t / 2 + i * (t + sg) for i in range(nstems)]
        for x in xs:
            tmp.rect(x - t / 2, y0, x + t / 2, y1)
        xe = x1 if not short else x0 + (x1 - x0) * 0.6
        if nbars == 1:
            ys = [p.AX]
        else:
            gp = eq_gap(p) - (T(p) - t)
            ys = [p.AX - gp / 2, p.AX + gp / 2]
        for y in ys:
            tmp.rect(xs[0] if cross else xs[-1], y - t / 2, xe, y + t / 2)
        if neg:
            negate(tmp, p, y0 + hw * 0.2, y1 - hw * 0.2, cx=(xs[-1] + x1) / 2 + t * 0.2,
                   sx=hw * 0.36)
        if d == "right":
            g.add(tmp.contours)
        elif d == "left":
            mirror_into(g, tmp, cx=p.M)
        elif d == "down":
            rot_into(g, tmp, p.M, p.AX, -math.pi / 2)
        else:
            rot_into(g, tmp, p.M, p.AX, math.pi / 2)

    return fn


defn(0x22A2, tack())
defn(0x22A3, tack(d="left"))
defn(0x22A4, tack(d="down"))
defn(0x22A5, tack(d="up"))
defn(0x22A6, tack(short=True))
defn(0x22A7, tack(nbars=2, short=True))
defn(0x22A8, tack(nbars=2))
defn(0x22A9, tack(nstems=2))
defn(0x22AA, tack(nstems=3))
defn(0x22AB, tack(nstems=2, nbars=2))
defn(0x22AC, tack(neg=True))
defn(0x22AD, tack(nbars=2, neg=True))
defn(0x22AE, tack(nstems=2, neg=True))
defn(0x22AF, tack(nstems=2, nbars=2, neg=True))


def prec_rel(right=False):
    """Precedes under relation: precedes with arms curling outwards."""

    def fn(g, p):
        hw = HW(p)
        t = T(p)
        tmp = tmp_glyph(p)
        x0, x1, y0, y1 = p.M - hw, p.M + hw, p.AX - hw, p.AX + hw
        xt = x0 + t * 0.2
        for s in (1, -1):
            ye = p.AX + s * (hw - t / 2)
            path = Path((xt, p.AX), 0.42).C((xt + hw * 0.7, p.AX + s * hw * 0.05), (p.M + hw * 0.05, ye - s * hw * 0.5), (p.M + hw * 0.35, ye - s * hw * 0.08), 1.0)
            path.C((p.M + hw * 0.55, ye + s * hw * 0.12), (x1 - hw * 0.12, ye), (x1, ye), 0.9)
            tmp.stroke(path, pen=mpen(t))
        if right:
            mirror_into(g, tmp, cx=p.M)
        else:
            g.add(tmp.contours)

    return fn


defn(0x22B0, prec_rel())
defn(0x22B1, prec_rel(True))

for _cp, _spec, _neg in [
    (0x22B2, "tril", None), (0x22B3, "trir", None), (0x22B4, "tril bar", None), (0x22B5, "trir bar", None),
]:
    defn(_cp, rel(_spec, _neg))


def multimap(left=None, right="ring"):
    def fn(g, p):
        hw = HW(p) * 1.06
        t = T(p)
        rr = hw * 0.44
        x0, x1 = p.M - hw, p.M + hw
        xa = x0 + (2 * rr - t / 2 if left else 0)
        xb = x1 - (2 * rr - t / 2 if right else 0)
        g.rect(xa, p.AX - t / 2, xb, p.AX + t / 2)
        for side, kind in ((-1, left), (1, right)):
            if not kind:
                continue
            cx = (x0 + rr) if side < 0 else (x1 - rr)
            if kind == "ring":
                circle_ring(g, cx, p.AX, rr, min(t * 0.9, rr * 0.55))
            else:
                disc(g, cx, p.AX, rr)

    return fn


defn(0x22B6, multimap("ring", "disc"))
defn(0x22B7, multimap("disc", "ring"))
defn(0x22B8, multimap(None, "ring"))


@define(0x22B9)
def hermitian(g, p):
    hw = HW(p) * 0.95
    t = TB(p) * 0.9
    gp = max(t * 0.8, hw * 0.3)
    g.rect(p.M - hw, p.AX - t / 2, p.M - gp, p.AX + t / 2)
    g.rect(p.M + gp, p.AX - t / 2, p.M + hw, p.AX + t / 2)
    g.rect(p.M - t / 2, p.AX + gp, p.M + t / 2, p.AX + hw)
    g.rect(p.M - t / 2, p.AX - hw, p.M + t / 2, p.AX - gp)


@define(0x22BA)
def intercal(g, p):
    hw = HW(p)
    t = T(p)
    yt = p.AX + hw * 0.55
    g.rect(p.M - hw * 0.75, yt - t, p.M + hw * 0.75, yt)
    g.rect(p.M - t / 2, p.AX - hw * 1.6, p.M + t / 2, yt)


defn(0x22BB, rel("vee bar"))
defn(0x22BC, rel("bar wedge"))
defn(0x22BD, rel("bar vee"))


@define(0x22BE)
def rightanglearc(g, p):
    x0, x1, y0, y1 = rbox(p, 1.05)
    t = T(p)
    g.stroke(Path((x0 + t / 2, y1)).L((x0 + t / 2, y0 + t / 2)).L((x1, y0 + t / 2)), pen=mpen(t))
    r = (x1 - x0) * 0.55
    g.stroke(arc_path(x0 + t / 2, y0 + t / 2, r, 0, 90, n=1), pen=mpen(t * 0.75))


@define(0x22BF)
def righttriangle(g, p):
    x0, x1, y0, y1 = rbox(p, 1.05)
    pts = [(x1, y0), (x0, y0), (x1, y1)]
    poly_ring(g, pts, tri_wall(pts, T(p)))


# ---------------------------------------------------------------------- n-ary logical etc.
@define(0x22C0, slant=False)
def naryand(g, p):
    x0, x1, y0, y1 = big_box(p)
    prim_wedge(g, p, x0 + p.S * 0.1, x1 - p.S * 0.1, y0, y1, p.S * 0.95)


@define(0x22C1, slant=False)
def naryor(g, p):
    x0, x1, y0, y1 = big_box(p)
    prim_wedge(g, p, x0 + p.S * 0.1, x1 - p.S * 0.1, y0, y1, p.S * 0.95, flip=True)


def big_cup(g, p, flip=False, square=False):
    x0, x1, y0, y1 = big_box(p)
    tmp = tmp_glyph(p)
    S = p.S
    path = cup_path(p, x0 + S * 0.1, x1 - S * 0.1, y0, y1, S, square)
    tmp.stroke(path, pen=Pen(S, p.H))
    if flip:
        mirror_into(g, tmp, cy=p.AX)
    else:
        g.add(tmp.contours)
    return x0 + S * 0.1, x1 - S * 0.1, y0, y1


@define(0x22C2, slant=False)
def naryintersection(g, p):
    big_cup(g, p, flip=True)


@define(0x22C3, slant=False)
def naryunion(g, p):
    big_cup(g, p)


@define(0x22C4)
def diamondop(g, p):
    r = HW(p) * 0.66
    pts = [(p.M, p.AX + r), (p.M + r, p.AX), (p.M, p.AX - r), (p.M - r, p.AX)]
    poly_ring(g, pts, min(T(p) * 0.85, r * 0.42))


@define(0x22C5)
def dotmath(g, p):
    dot(g, p, p.M, p.AX, d=pdot_d(p), k=0.66)


@define(0x22C6)
def starop(g, p):
    r = HW(p) * 0.72 + p.S * 0.1
    fill_poly(g, star_pts(p.M, p.AX - r * 0.05, r, r * 0.45))


@define(0x22C7)
def divisiontimes(g, p):
    r = HW(p) * 0.58
    t = TB(p) * 0.92
    for s in (-1, 1):
        g.stroke(Path((p.M - r, p.AX - s * r)).L((p.M + r, p.AX + s * r)), pen=mpen(t))
    d = DOTD(p)
    vs = r + WG(p) * 0.7 + d / 2
    odot(g, p, p.M, p.AX + vs)
    odot(g, p, p.M, p.AX - vs)


def bowtie_parts(g, p, left=True, right=True, x0=None, x1=None, h=None):
    hw = HW(p) * 1.04
    x0 = p.M - hw if x0 is None else x0
    x1 = p.M + hw if x1 is None else x1
    h = hw * 0.86 if h is None else h
    t = fit_t(p, T(p), x1 - x0, 3.2, 0.5)
    y0, y1 = p.AX - h, p.AX + h
    pen = mpen(t)
    xa = x0 + (t * 0.5 if left else 0)
    xb = x1 - (t * 0.5 if right else 0)
    u = unit((xb - xa, y0 - y1))
    off = abs(t / 2 / u[0])
    for s in (1, -1):
        a = (xa, (y1 - off) if s > 0 else (y0 + off))
        b = (xb, (y0 + off) if s > 0 else (y1 - off))
        g.stroke(Path(a).L(b), pen=pen, start=90, end=90)
    if left:
        g.rect(x0, y0, x0 + t, y1)
    if right:
        g.rect(x1 - t, y0, x1, y1)


@define(0x22C8)
def bowtie(g, p):
    bowtie_parts(g, p)


@define(0x22C9)
def ltimes(g, p):
    bowtie_parts(g, p, right=False)


@define(0x22CA)
def rtimes(g, p):
    bowtie_parts(g, p, left=False)


def threetimes(right=False):
    def fn(g, p):
        hw = HW(p) * 0.92
        t = TB(p) * 0.92
        tmp = tmp_glyph(p)
        tmp.stroke(Path((p.M - hw, p.AX + hw)).L((p.M + hw, p.AX - hw)), pen=mpen(t))
        tmp.stroke(Path((p.M, p.AX)).L((p.M - hw, p.AX - hw)), pen=mpen(t), start="butt")
        if right:
            mirror_into(g, tmp, cx=p.M)
        else:
            g.add(tmp.contours)

    return fn


defn(0x22CB, threetimes())
defn(0x22CC, threetimes(True))
defn(0x22CD, rel("rtilde bar"))


def curly(flip=False):
    """Curly logical or/and: a precedes turned by 90 degrees."""

    def fn(g, p):
        hw = HW(p)
        t = T(p)
        tmp = tmp_glyph(p)
        prim_prec(tmp, p, -hw, hw, -hw * 0.95, hw * 0.95, t)
        ang = -math.pi / 2 if not flip else math.pi / 2
        c, s = math.cos(ang), math.sin(ang)
        tmp.transform(lambda q: (p.M + q[0] * c - q[1] * s, p.AX + q[0] * s + q[1] * c))
        g.add(tmp.contours)

    return fn


defn(0x22CE, curly())
defn(0x22CF, curly(True))


def double_shape(kind):
    def fn(g, p):
        hw = HW(p)
        t = fit_t(p, T(p) * 0.86, 2 * hw, 4, 0.55)
        x0, x1, y0, y1 = p.M - hw, p.M + hw, p.AX - hw, p.AX + hw
        gp = WG(p) * 0.6 + t
        if kind in ("sub", "sup"):
            prim_sub(g, p, x0, x1, y0, y1, t, right=kind == "sup")
            if kind == "sub":
                prim_sub(g, p, x0 + gp, x1, y0 + gp, y1 - gp, t)
            else:
                prim_sub(g, p, x0, x1 - gp, y0 + gp, y1 - gp, t, right=True)
        else:
            flip = kind == "cap"
            prim_cup(g, p, x0, x1, y0, y1, t, flip=flip)
            if flip:
                prim_cup(g, p, x0 + gp, x1 - gp, y0, y1 - gp, t, flip=True)
            else:
                prim_cup(g, p, x0 + gp, x1 - gp, y0 + gp, y1, t)

    return fn


defn(0x22D0, double_shape("sub"))
defn(0x22D1, double_shape("sup"))
defn(0x22D2, double_shape("cap"))
defn(0x22D3, double_shape("cup"))


@define(0x22D4)
def pitchfork(g, p):
    hw = HW(p)
    t = T(p)
    prim_cap(g, p, p.M - hw, p.M + hw, p.AX - hw, p.AX + hw * 0.7, t)
    g.rect(p.M - t / 2, p.AX - hw, p.M + t / 2, p.AX + hw * 1.15)


@define(0x22D5)
def equalparallel(g, p):
    hw = HW(p)
    t = fit_t(p, T(p), 2 * hw, 4, 0.5)
    eq_bars(g, p, t=t)
    o = max(hw * 0.36, (t + WG(p) * 0.5) / 2)
    for s in (-1, 1):
        g.rect(p.M + s * o - t / 2, p.AX - hw, p.M + s * o + t / 2, p.AX + hw)


for _cp, _spec, _neg in [
    (0x22D6, "ltdot", None), (0x22D7, "gtdot", None),
    (0x22DA, "lt bar gt", None), (0x22DB, "gt bar lt", None),
    (0x22DC, "bar lt", None), (0x22DD, "bar gt", None),
    (0x22DE, "cbaru prec", None), (0x22DF, "cbarur succ", None),
    (0x22E0, "prec cbar", "all"), (0x22E1, "succ cbarr", "all"),
    (0x22E2, "sqsub bar", "all"), (0x22E3, "sqsup bar", "all"),
    (0x22E4, "sqsub bar", 1), (0x22E5, "sqsup bar", 1),
    (0x22E6, "lt tilde", 1), (0x22E7, "gt tilde", 1),
    (0x22E8, "prec tilde", 1), (0x22E9, "succ tilde", 1),
    (0x22EA, "tril", "all"), (0x22EB, "trir", "all"),
    (0x22EC, "tril bar", "all"), (0x22ED, "trir bar", "all"),
]:
    defn(_cp, rel(_spec, _neg))

defn(0x22D8, nested("lt", 3))
defn(0x22D9, nested("lt", 3, True))


# ---------------------------------------------------------------------- ellipses
@define(0x22EE)
def vellipsis(g, p):
    d = DOTD(p)
    s = max(HW(p) * 1.0, d * 1.6)
    for i in (-1, 0, 1):
        odot(g, p, p.M, p.AX + i * s)


@define(0x22EF)
def midhellipsis(g, p):
    d = min(DOTD(p), p.W * 0.24)
    for i in (-1, 0, 1):
        dot(g, p, p.M + i * p.W * 0.33, p.AX, d=d, k=0.66)


@define(0x22F0)
def uprightellipsis(g, p):
    d = min(DOTD(p), p.W * 0.24)
    for i in (-1, 0, 1):
        dot(g, p, p.M + i * p.W * 0.31, p.AX + i * HW(p) * 1.05, d=d, k=0.66)


@define(0x22F1)
def downrightellipsis(g, p):
    d = min(DOTD(p), p.W * 0.24)
    for i in (-1, 0, 1):
        dot(g, p, p.M + i * p.W * 0.31, p.AX - i * HW(p) * 1.05, d=d, k=0.66)


# ---------------------------------------------------------------------- element-of variants
def elem_var(kind, right=False, small=False):
    def fn(g, p):
        hw = HW(p) * (0.8 if small else 1.0)
        tmp = tmp_glyph(p)
        t = T(p)
        h = hw * (1.0 if not small else 0.95)
        x0, x1 = p.M - hw, p.M + hw
        y0, y1 = p.AX - h, p.AX + h
        if kind == "long":
            te = elem_t(p, 2 * h, t)
            prim_sub(tmp, p, x0 + hw * 0.42, x1, y0, y1, te)
            tmp.rect(x0, p.AX - te / 2, x1, p.AX + te / 2)
        elif kind == "vbar":
            te = elem_t(p, 2 * h, t)
            prim_elem(tmp, p, x0, x1 - te * 0.2, y0, y1, te)
            tmp.rect(x1 - te, p.AX - h * 0.42, x1, p.AX + h * 0.42)
        elif kind == "two":
            te = elem_t(p, 2 * h, t, n=4)
            prim_sub(tmp, p, x0, x1, y0, y1, te)
            gp = (2 * h - te) / 3
            for k in (-0.5, 0.5):
                tmp.rect(x0 + te / 2, p.AX + k * gp - te / 2, x1, p.AX + k * gp + te / 2)
        if right:
            mirror_into(g, tmp, cx=p.M)
        else:
            g.add(tmp.contours)

    return fn


defn(0x22F2, elem_var("long"))
defn(0x22F3, elem_var("vbar"))
defn(0x22F4, elem_var("vbar", small=True))
defn(0x22F5, rel("dot elem"))
defn(0x22F6, rel("bar elem"))
defn(0x22F7, rel("bar small:elem"))
defn(0x22F8, rel("elem bar"))
defn(0x22F9, elem_var("two"))
defn(0x22FA, elem_var("long", right=True))
defn(0x22FB, elem_var("vbar", right=True))
defn(0x22FC, elem_var("vbar", right=True, small=True))
defn(0x22FD, rel("bar ni"))
defn(0x22FE, rel("bar small:ni"))
defn(0x22FF, rel("sqelem"))


# ====================================================================== more stack tokens
def prim_plus(g, p, x0, x1, y0, y1, t):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    h = (y1 - y0) / 2
    plus_at(g, p, cx, cy, min((x1 - x0) / 2, h * 1.15), t=TB(p) * t / T(p), vhw=h)


def prim_times(g, p, x0, x1, y0, y1, t):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (y1 - y0) / 2
    tt = TB(p) * t / T(p)
    e = r - tt * 0.35
    for s in (-1, 1):
        g.stroke(Path((cx - e, cy - s * e)).L((cx + e, cy + s * e)), pen=mpen(tt))


def prim_ast(g, p, x0, x1, y0, y1, t):
    r = (y1 - y0) / 2
    asterisk_at(g, p, (x0 + x1) / 2, (y0 + y1) / 2, r, min(t * 0.85, r * 0.5))


def slbar_draw(up=False, right=False):
    def draw(g, p, x0, x1, y0, y1, t):
        w = t / 2
        if up != right:
            a, b = (x0, y0 + w), (x1, y1 - w)
        else:
            a, b = (x0, y1 - w), (x1, y0 + w)
        g.stroke(Path(a).L(b), pen=angle_pen(p, t), start=90, end=90)

    return draw


def prim_dots4(g, p, x0, x1, y0, y1, t):
    d = y1 - y0
    for i in range(4):
        cx = x0 + d / 2 + i * ((x1 - x0) - d) / 3
        dot(g, p, cx, (y0 + y1) / 2, d=d, k=0.66)


def prim_ltc(g, p, x0, x1, y0, y1, t, right=False):
    """Less-than closed by a curve on its open side."""
    tmp = tmp_glyph(p)
    pts = angle_poly(p, x0, x1 - (x1 - x0) * 0.12, y0, y1, t, pen=mpen(t))
    fill_poly(tmp, pts)
    w = t / 2
    xe = x1 - (x1 - x0) * 0.12 - w
    path = Path((xe, y1 - w)).C((x1 - w * 0.2, y1 - (y1 - y0) * 0.2), (x1 - w * 0.2, y0 + (y1 - y0) * 0.2), (xe, y0 + w))
    tmp.stroke(path, pen=mpen(t))
    if right:
        mirror_into(g, tmp, cx=(x0 + x1) / 2)
    else:
        g.add(tmp.contours)


def prim_gtc(g, p, x0, x1, y0, y1, t):
    prim_ltc(g, p, x0, x1, y0, y1, t, right=True)


def prim_csub(g, p, x0, x1, y0, y1, t, right=False):
    tmp = tmp_glyph(p)
    prim_sub(tmp, p, x0, x1, y0, y1, t)
    tmp.rect(x1 - t, y0, x1, y1)
    if right:
        mirror_into(g, tmp, cx=(x0 + x1) / 2)
    else:
        g.add(tmp.contours)


def prim_csup(g, p, x0, x1, y0, y1, t):
    prim_csub(g, p, x0, x1, y0, y1, t, right=True)


def prim_lt_ring(g, p, x0, x1, y0, y1, t, right=False):
    if right:
        prim_greater(g, p, x0, x1, y0, y1, t)
    else:
        prim_less(g, p, x0, x1, y0, y1, t)
    r = min((y1 - y0) * 0.17, DOTD(p) * 0.62)
    cx = x0 + (x1 - x0) * (0.66 if not right else 0.34)
    circle_ring(g, cx, (y0 + y1) / 2, r, min(t * 0.7, r * 0.5))


def prim_gt_ring(g, p, x0, x1, y0, y1, t):
    prim_lt_ring(g, p, x0, x1, y0, y1, t, right=True)


def prim_nested(g, p, x0, x1, y0, y1, t, right=False, kind="lt", n=2):
    """Angles nested inside each other (double nested less-than)."""
    tmp = tmp_glyph(p)
    tt = fit_t(p, t, (y1 - y0) / 2, n, 0.5)
    step = tt + WG(p) * 0.55
    for i in range(n):
        dx = step * i * 1.6
        dy = step * i
        bx0, by0, by1 = x0 + dx, y0 + dy, y1 - dy
        if kind == "lt":
            fill_poly(tmp, angle_poly(p, bx0, x1, by0, by1, tt))
        else:
            prim_prec(tmp, p, bx0, x1, by0, by1, tt)
    if right:
        mirror_into(g, tmp, cx=(x0 + x1) / 2)
    else:
        g.add(tmp.contours)


def prim_wedge_dot(g, p, x0, x1, y0, y1, t):
    prim_wedge(g, p, x0, x1, y0, y1, t)


SHAPES.update({
    "ltc": prim_ltc, "gtc": prim_gtc, "csub": prim_csub, "csup": prim_csup,
    "ltring": prim_lt_ring, "gtring": prim_gt_ring,
    "nlt": lambda g, p, x0, x1, y0, y1, t: prim_nested(g, p, x0, x1, y0, y1, t),
    "ngt": lambda g, p, x0, x1, y0, y1, t: prim_nested(g, p, x0, x1, y0, y1, t, right=True),
    "nlt3": lambda g, p, x0, x1, y0, y1, t: prim_nested(g, p, x0, x1, y0, y1, t, n=3),
    "ngt3": lambda g, p, x0, x1, y0, y1, t: prim_nested(g, p, x0, x1, y0, y1, t, right=True, n=3),
})

_parse1 = parse


def parse(p, spec):  # noqa: F811
    out = []
    for tok in spec.split():
        if tok == "plus":
            out.append(Lay(prim_plus, HW(p) * 1.5))
        elif tok == "times":
            out.append(Lay(prim_times, HW(p) * 1.2))
        elif tok == "ast":
            out.append(Lay(prim_ast, HW(p) * 0.85, gap=0.8))
        elif tok in ("slbar", "slbarg", "slbaru", "slbarug"):
            up = tok.startswith("slbaru")
            right = tok.endswith("g")
            out.append(Lay(slbar_draw(up, right), HW(p) * 0.9 + T(p) * 0.3))
        elif tok == "dots4":
            out.append(Lay(prim_dots4, DOTD(p) * 0.8, gap=0.85))
        elif tok == "question":
            out.append(Lay(lambda g, p, x0, x1, y0, y1, t: draw_scaled(g, p, "question", 0.5, 0.36, 0.62, dy=y0),
                           p.CAP * 0.36, gap=0.8))
        else:
            out.extend(_parse1(p, tok))
    return out


# ====================================================================== U+2A00 Supplemental Mathematical Operators
for _cp, _inner in [(0x2A00, "dot"), (0x2A01, "plus"), (0x2A02, "times")]:
    defn(_cp, enclosed(_inner, big=True), slant=False)


def big_cup_with(inner, square=False, flip=False):
    def fn(g, p):
        x0, x1, y0, y1 = big_cup(g, p, flip=flip, square=square)
        S = p.S
        cx = p.M
        cy = (y0 + S + y1) / 2 + (y1 - y0) * 0.04
        iw = (x1 - x0) / 2 - S - WG(p) * 0.6
        if inner == "plus":
            plus_at(g, p, cx, cy, iw, t=S * 0.88)
        elif inner == "dot":
            dot(g, p, cx, cy, d=min(pdot_d(p) * 1.2, iw * 1.2), k=0.66)

    return fn


defn(0x2A03, big_cup_with("dot"), slant=False)
defn(0x2A04, big_cup_with("plus"), slant=False)
defn(0x2A05, big_cup_with(None, square=True, flip=True), slant=False)
defn(0x2A06, big_cup_with(None, square=True), slant=False)


def big_two_wedge(flip=False):
    def fn(g, p):
        x0, x1, y0, y1 = big_box(p)
        t = p.S * 0.88
        tmp = tmp_glyph(p)
        prim_wedge(tmp, p, x0 + p.S * 0.1, x1 - p.S * 0.1, y0, y1, t)
        d = (x1 - x0) * 0.24
        prim_wedge(tmp, p, x0 + d, x1 - d, y0, y1 - (y1 - y0) * 0.36, t * 0.9)
        if flip:
            mirror_into(g, tmp, cy=p.AX)
        else:
            g.add(tmp.contours)

    return fn


defn(0x2A07, big_two_wedge(), slant=False)
defn(0x2A08, big_two_wedge(True), slant=False)


@define(0x2A09, slant=False)
def narytimes(g, p):
    x0, x1, y0, y1 = big_box(p)
    t = p.S * 0.95
    r = min((x1 - x0) / 2, BIGH(p)) * 0.92
    for s in (-1, 1):
        g.stroke(Path((p.M - r, p.AX - s * r)).L((p.M + r, p.AX + s * r)), pen=mpen(t))


@define(0x2A0C, slant=False)
def quadintegral(g, p):
    multi_integral(g, p, 4)


def int_with(kind):
    def fn(g, p):
        ym, wf = multi_integral(g, p, 1)
        t = T(p) * 0.8
        aw = int_metrics(p)[2]
        hw = aw * 0.3
        if kind == "bar":
            g.rect(p.M - hw, ym - t / 2, p.M + hw, ym + t / 2)
        elif kind == "dbar":
            for s in (-1, 1):
                g.rect(p.M - hw, ym + s * eq_gap(p) * 0.45 - t / 2, p.M + hw, ym + s * eq_gap(p) * 0.45 + t / 2)
        elif kind == "slash":
            g.stroke(Path((p.M - hw, ym - hw * 1.3)).L((p.M + hw, ym + hw * 1.3)), pen=mpen(t), start=0, end=0)
        elif kind == "times":
            e = hw * 0.75
            for s in (-1, 1):
                g.stroke(Path((p.M - e, ym - s * e)).L((p.M + e, ym + s * e)), pen=mpen(t))
        elif kind in ("cap", "cup"):
            prim_cup(g, p, p.M - hw, p.M + hw, ym - hw, ym + hw, t, flip=kind == "cap")
        elif kind == "overbar":
            y = p.BT + 10
            g.rect(p.M - hw * 1.2, y - t, p.M + hw * 1.2, y)
        elif kind == "underbar":
            y = p.BB - 10
            g.rect(p.M - hw * 1.2, y, p.M + hw * 1.2, y + t)
        elif kind == "ring":
            r = hw * 0.55
            circle_ring(g, p.M, ym, r, min(t * 0.9, r * 0.5))
        elif kind == "square":
            e = hw * 0.75
            poly_ring(g, [(p.M - e, ym - e), (p.M - e, ym + e), (p.M + e, ym + e), (p.M + e, ym - e)], t * 0.85)
        elif kind == "semi":
            r = hw * 0.7
            g.stroke(arc_path(p.M, ym, r, -90, 90, n=2), pen=mpen(t * 0.85))
        elif kind == "anti":
            r = aw * 0.24
            path = arc_path(p.M, ym, r, 20, 280, n=3)
            g.stroke(path, pen=mpen(t * 0.9))
            a = math.radians(280)
            tip = (p.M + r * math.cos(a), ym + r * math.sin(a))
            small_head(g, tip, (-math.sin(a), math.cos(a)), t * 0.9, r * 0.62)
        elif kind == "hook":
            g.rect(p.M - hw * 1.1, ym - t / 2, p.M + hw * 0.6, ym + t / 2)
            small_head(g, (p.M - hw * 1.1, ym), (-1, 0), t, hw * 0.55)
            r = hw * 0.3
            g.stroke(arc_path(p.M + hw * 0.6, ym + r, r, -90, 90, n=2), pen=mpen(t))

    return fn


for _cp, _k in [(0x2A0D, "bar"), (0x2A0E, "dbar"), (0x2A0F, "slash"), (0x2A10, "square"),
                (0x2A11, "anti"), (0x2A12, "square"), (0x2A13, "semi"), (0x2A14, "semi"),
                (0x2A15, "ring"), (0x2A17, "hook"), (0x2A18, "times"),
                (0x2A19, "cap"), (0x2A1A, "cup"), (0x2A1B, "overbar"), (0x2A1C, "underbar")]:
    defn(_cp, int_with(_k), slant=False)


@define(0x2A16, slant=False)
def quaternionintegral(g, p):
    x0, x1, y0, y1 = big_box(p)
    t = T(p) * 0.8
    poly_ring(g, [(x0, y0), (x0, y1), (x1, y1), (x1, y0)], t)
    aw = (x1 - x0) - 2 * t - WG(p)
    disp = aw * 0.1
    r = (aw - 2 * disp) / 4
    integral_shape(g, p, p.M, r, disp, int_wf(p, 2), y0=y0 + t + WG(p) * 0.4, y1=y1 - t - WG(p) * 0.4)


@define(0x2A1D)
def join(g, p):
    hw = HW(p) * 1.08
    h = hw * 0.95
    t = fit_t(p, T(p), hw, 2.2, 0.4)
    for s in (-1, 1):
        pts = [(p.M, p.AX), (p.M + s * hw, p.AX + h), (p.M + s * hw, p.AX - h)]
        poly_ring(g, pts, tri_wall(pts, t))


@define(0x2A1E)
def largelefttriangle(g, p):
    x0, x1, y0, y1 = big_box(p)
    h = min(BIGH(p), (x1 - x0) * 0.75)
    pts = [(x0, p.AX), (x1, p.AX + h), (x1, p.AX - h)]
    poly_ring(g, pts, tri_wall(pts, p.S * 0.9))


@define(0x2A1F)
def schemacomposition(g, p):
    draw_glyph(g, p, "semicolon")


defn(0x2A20, nested("lt", 2, True))


@define(0x2A21)
def schemaprojection(g, p):
    t = T(p)
    h = TALL(p) * 0.85
    x = p.M - HW(p) * 0.25
    g.rect(x - t / 2, p.AX - h, x + t / 2, p.AX + h)
    hd = HW(p) * 0.75
    g.stroke(Path((x + hd * 0.9, p.AX + h - hd)).L((x + t * 0.1, p.AX + h - t * 0.2)), pen=mpen(t), start="butt", end=0)


for _cp, _spec in [(0x2A22, "ring plus"), (0x2A23, "hat plus"), (0x2A24, "tilde plus"),
                   (0x2A25, "plus dot"), (0x2A26, "plus tilde"),
                   (0x2A2A, "bar dot"), (0x2A30, "dot times"), (0x2A31, "times bar"),
                   (0x2A71, "bar bar plus"), (0x2A72, "plus bar bar")]:
    defn(_cp, rel(_spec))


@define(0x2A27)
def plussubtwo(g, p):
    hw = HW(p) * 0.85
    plus_at(g, p, p.M - hw * 0.2, p.AX + hw * 0.1, hw)
    draw_scaled(g, p, "two", 0.42, 0.42, 0.62, dx=hw * 0.75, dy=p.AX - hw * 1.55)


@define(0x2A28)
def plusblacktriangle(g, p):
    hw = HW(p) * 0.85
    plus_at(g, p, p.M - hw * 0.15, p.AX - hw * 0.15, hw)
    e = hw * 0.62
    cx, cy = p.M + hw * 0.55, p.AX + hw * 0.6
    fill_poly(g, [(cx - e * 0.5, cy - e * 0.45), (cx + e * 0.5, cy - e * 0.45), (cx, cy + e * 0.5)])


@define(0x2A29)
def minuscomma(g, p):
    minus(g, p)
    from .punct import comma_at

    tmp = tmp_glyph(p)
    comma_at(tmp, p, p.M, 0)
    tmp.transform(lambda q: (q[0], q[1] + p.AX + WG(p) * 0.9 + p.S * 0.5))
    g.add(tmp.contours)


def minus_dots(rising):
    def fn(g, p):
        minus(g, p)
        vs = dot_vs(p) * 0.85
        hs = HW(p) * 0.7
        s = 1 if rising else -1
        odot(g, p, p.M - s * hs, p.AX - vs, 0.9)
        odot(g, p, p.M + s * hs, p.AX + vs, 0.9)

    return fn


defn(0x2A2B, minus_dots(False))
defn(0x2A2C, minus_dots(True))


def half_circle_op(inner, right=False):
    def fn(g, p):
        r = circ_r(p)
        t = fit_t(p, circ_t(p), 2 * r, 3)
        tmp = tmp_glyph(p)
        tmp.stroke(arc_path(p.M, p.AX, r - t / 2, 90, 270, n=2), pen=mpen(t))
        inner_draw(tmp, p, inner, p.M, p.AX, r, t, r - t / 2)
        if right:
            mirror_into(g, tmp, cx=p.M)
        else:
            g.add(tmp.contours)

    return fn


defn(0x2A2D, half_circle_op("plus"))
defn(0x2A2E, half_circle_op("plus", True))
defn(0x2A34, half_circle_op("times"))
defn(0x2A35, half_circle_op("times", True))


@define(0x2A2F)
def crossproduct(g, p):
    draw_glyph(g, p, "multiply")


@define(0x2A32)
def semidirectclosed(g, p):
    hw = HW(p) * 0.92
    t = TB(p) * 0.9
    for s in (-1, 1):
        g.stroke(Path((p.M - hw, p.AX - s * hw)).L((p.M + hw, p.AX + s * hw)), pen=mpen(t), start=0, end=0)
    g.rect(p.M - hw - t * 0.4, p.AX - hw, p.M + hw + t * 0.4, p.AX - hw + t)


@define(0x2A33)
def smashproduct(g, p):
    hw = HW(p) * 0.95
    t = fit_t(p, TB(p) * 0.9, 2 * hw, 3.5, 0.4)
    o = hw * 0.3
    for dx in (-o, o):
        for s in (-1, 1):
            g.stroke(Path((p.M + dx - hw * 0.7, p.AX - s * hw * 0.85)).L((p.M + dx + hw * 0.7, p.AX + s * hw * 0.85)),
                     pen=mpen(t), start=0, end=0)


@define(0x2A36)
def circledtimeshat(g, p):
    r = circ_r(p) * 0.86
    t = fit_t(p, circ_t(p), 2 * r, 3)
    cy = p.AX - r * 0.18
    circle_ring(g, p.M, cy, r, t)
    inner_draw(g, p, "times", p.M, cy, r, t, r - t / 2)
    y0 = cy + r + WG(p) * 0.6
    prim_wedge(g, p, p.M - r * 0.55, p.M + r * 0.55, y0, y0 + r * 0.42, t * 0.85)


@define(0x2A37)
def timesdoublecircle(g, p):
    r = circ_r(p)
    t = fit_t(p, circ_t(p) * 0.8, 2 * r, 5)
    circle_ring(g, p.M, p.AX, r, t)
    r2 = r - t - WG(p) * 0.45
    circle_ring(g, p.M, p.AX, r2, t)
    inner_draw(g, p, "times", p.M, p.AX, r2, t, r2 - t / 2)


@define(0x2A38)
def circleddivision(g, p):
    r = circ_r(p)
    t = fit_t(p, circ_t(p), 2 * r, 5)
    circle_ring(g, p.M, p.AX, r, t)
    g.rect(p.M - (r - t / 2), p.AX - t / 2, p.M + (r - t / 2), p.AX + t / 2)
    d = min(DOTD(p), (r - t) * 0.42)
    vs = (r - t) * 0.52
    for s in (-1, 1):
        dot(g, p, p.M, p.AX + s * vs, d=d, k=0.66)


def triangle_op(inner):
    def fn(g, p):
        hw = HW(p) * 1.15
        h = hw * 1.9
        y0 = p.AX - h * 0.38
        pts = [(p.M, y0 + h), (p.M + hw, y0), (p.M - hw, y0)]
        t = tri_wall(pts, fit_t(p, T(p) * 0.85, hw * 1.2, 3))
        poly_ring(g, pts, t)
        cy = y0 + h * 0.33
        e = hw * 0.32
        if inner == "plus":
            plus_at(g, p, p.M, cy, e, t=t)
        elif inner == "minus":
            g.rect(p.M - e, cy - t / 2, p.M + e, cy + t / 2)
        else:
            for s in (-1, 1):
                g.stroke(Path((p.M - e * 0.8, cy - s * e * 0.8)).L((p.M + e * 0.8, cy + s * e * 0.8)), pen=mpen(t))

    return fn


defn(0x2A39, triangle_op("plus"))
defn(0x2A3A, triangle_op("minus"))
defn(0x2A3B, triangle_op("times"))


@define(0x2A3C)
def interiorproduct(g, p):
    hw = HW(p)
    t = T(p)
    g.rect(p.M - hw, p.AX - hw * 0.4 - t / 2, p.M + hw, p.AX - hw * 0.4 + t / 2)
    g.rect(p.M + hw - t, p.AX - hw * 0.4 - t / 2, p.M + hw, p.AX + hw * 0.6)


@define(0x2A3D)
def righthandinteriorproduct(g, p):
    hw = HW(p)
    t = T(p)
    g.rect(p.M - hw, p.AX - hw * 0.4 - t / 2, p.M + hw, p.AX - hw * 0.4 + t / 2)
    g.rect(p.M - hw, p.AX - hw * 0.4 - t / 2, p.M - hw + t, p.AX + hw * 0.6)


@define(0x2A3F)
def amalgamation(g, p):
    hw = HW(p)
    t = T(p)
    prim_sqcup(g, p, p.M - hw * 0.78, p.M + hw * 0.78, p.AX - hw, p.AX + hw, t)
    for s in (-1, 1):
        g.rect(p.M + s * hw * 0.78, p.AX + hw - t, p.M + s * hw * 1.05, p.AX + hw)


def cupcap_with(kind, inner):
    def fn(g, p):
        hw = HW(p)
        t = T(p)
        flip = kind == "cap"
        x0, x1, y0, y1 = p.M - hw, p.M + hw, p.AX - hw, p.AX + hw
        prim_cup(g, p, x0, x1, y0, y1, t, flip=flip)
        cy = p.AX + (-1 if flip else 1) * hw * 0.08
        iw = hw - t - WG(p) * 0.45
        ti = t * 0.85
        if inner == "dot":
            odot(g, p, p.M, cy, 0.95)
        elif inner == "minus":
            g.rect(p.M - iw, cy - ti / 2, p.M + iw, cy + ti / 2)
        elif inner == "wedge":
            prim_wedge(g, p, p.M - iw, p.M + iw, y0 + t * 0.2, y1 - t - WG(p) * 0.5, ti)
        elif inner == "vee":
            prim_wedge(g, p, p.M - iw, p.M + iw, y0 + t + WG(p) * 0.5, y1 - t * 0.2, ti, flip=True)

    return fn


defn(0x2A40, cupcap_with("cap", "dot"))
defn(0x2A41, cupcap_with("cup", "minus"))
defn(0x2A44, cupcap_with("cap", "wedge"))
defn(0x2A45, cupcap_with("cup", "vee"))

for _cp, _spec, _neg in [
    (0x2A42, "bar cup", None), (0x2A43, "bar cap", None),
    (0x2A46, "cup cap", None), (0x2A47, "cap cup", None),
    (0x2A48, "cup bar cap", None), (0x2A49, "cap bar cup", None),
    (0x2A51, "dot wedge", None), (0x2A52, "dot vee", None),
    (0x2A5E, "bar bar wedge", None), (0x2A5F, "wedge bar", None), (0x2A60, "wedge bar bar", None),
    (0x2A61, "small:vee bar", None), (0x2A62, "bar bar vee", None), (0x2A63, "vee bar bar", None),
    (0x2A66, "bar bar dot", None), (0x2A67, "dot bar bar bar", None),
    (0x2A6A, "dot tilde", None), (0x2A6C, "tilde bar tilde", None), (0x2A6D, "dot tilde bar bar", None),
    (0x2A6E, "ast bar bar", None), (0x2A6F, "hat tilde tilde", None), (0x2A70, "tilde tilde bar bar", None),
    (0x2A73, "bar bar tilde", None), (0x2A77, "dots2 bar bar dots2", None), (0x2A78, "dots4 bar bar bar", None),
    (0x2A79, "ltring", None), (0x2A7A, "gtring", None),
    (0x2A7B, "question lt", None), (0x2A7C, "question gt", None),
    (0x2A7D, "lt slbar", None), (0x2A7E, "gt slbarg", None),
    (0x2A7F, "ltdot slbar", None), (0x2A80, "gtdot slbarg", None),
    (0x2A81, "sdot lt slbar", None), (0x2A82, "sdot gt slbarg", None),
    (0x2A85, "lt tilde tilde", None), (0x2A86, "gt tilde tilde", None),
    (0x2A87, "lt bar", 1), (0x2A88, "gt bar", 1),
    (0x2A89, "lt tilde tilde", 2), (0x2A8A, "gt tilde tilde", 2),
    (0x2A8B, "lt bar bar gt", None), (0x2A8C, "gt bar bar lt", None),
    (0x2A8D, "lt tilde bar", None), (0x2A8E, "gt tilde bar", None),
    (0x2A8F, "lt tilde gt", None), (0x2A90, "gt tilde lt", None),
    (0x2A91, "lt gt bar bar", None), (0x2A92, "gt lt bar bar", None),
    (0x2A93, "lt slbar gt slbarg", None), (0x2A94, "gt slbarg lt slbar", None),
    (0x2A95, "slbaru lt", None), (0x2A96, "slbarug gt", None),
    (0x2A97, "slbaru ltdot", None), (0x2A98, "slbarug gtdot", None),
    (0x2A99, "bar bar lt", None), (0x2A9A, "bar bar gt", None),
    (0x2A9B, "slbaru slbaru lt", None), (0x2A9C, "slbarug slbarug gt", None),
    (0x2A9D, "tilde lt", None), (0x2A9E, "tilde gt", None),
    (0x2A9F, "tilde lt bar", None), (0x2AA0, "tilde gt bar", None),
    (0x2AA1, "nlt", None), (0x2AA2, "ngt", None), (0x2AA3, "nlt bar", None),
    (0x2AA6, "ltc", None), (0x2AA7, "gtc", None), (0x2AA8, "ltc slbar", None), (0x2AA9, "gtc slbarg", None),
    (0x2AAE, "bump bar bar", None),
    (0x2AAF, "prec bar", None), (0x2AB0, "succ bar", None),
    (0x2AB1, "prec bar", 1), (0x2AB2, "succ bar", 1),
    (0x2AB3, "prec bar bar", None), (0x2AB4, "succ bar bar", None),
    (0x2AB5, "prec bar bar", 2), (0x2AB6, "succ bar bar", 2),
    (0x2AB7, "prec tilde tilde", None), (0x2AB8, "succ tilde tilde", None),
    (0x2AB9, "prec tilde tilde", 2), (0x2ABA, "succ tilde tilde", 2),
    (0x2ABF, "sub plus", None), (0x2AC0, "sup plus", None),
    (0x2AC1, "sub times", None), (0x2AC2, "sup times", None),
    (0x2AC3, "sdot sub bar", None), (0x2AC4, "sdot sup bar", None),
    (0x2AC5, "sub bar bar", None), (0x2AC6, "sup bar bar", None),
    (0x2AC7, "sub tilde", None), (0x2AC8, "sup tilde", None),
    (0x2AC9, "sub tilde tilde", None), (0x2ACA, "sup tilde tilde", None),
    (0x2ACB, "sub bar bar", 2), (0x2ACC, "sup bar bar", 2),
    (0x2ACF, "csub", None), (0x2AD0, "csup", None), (0x2AD1, "csub bar", None), (0x2AD2, "csup bar", None),
    (0x2AD3, "sub sup", None), (0x2AD4, "sup sub", None), (0x2AD5, "sub sub", None), (0x2AD6, "sup sup", None),
    (0x2AF7, "nlt3", None), (0x2AF8, "ngt3", None),
    (0x2AF9, "lt slbar slbar", None), (0x2AFA, "gt slbarg slbarg", None),
]:
    defn(_cp, rel(_spec, _neg))

defn(0x2ABB, nested("prec", 2))
defn(0x2ABC, nested("prec", 2, True))


def dot_rel(kind, right=False):
    """Less/greater-than or slanted equal with dot above (right)."""

    def fn(g, p):
        rel("lt slbar" if not right else "gt slbarg")(g, p)
        d = DOTD(p) * 0.85
        hw = HW(p)
        x = p.M + (hw * 0.75 if not right else -hw * 0.75)
        odot(g, p, x, p.AX + hw * 1.25 + d * 0.2, 0.85)

    return fn


defn(0x2A83, dot_rel("lt"))
defn(0x2A84, dot_rel("gt", True))


def sub_dot(right=False):
    def fn(g, p):
        hw = HW(p)
        t = T(p)
        prim_sub(g, p, p.M - hw, p.M + hw, p.AX - hw, p.AX + hw, t, right=right)
        odot(g, p, p.M + (hw * 0.2 if not right else -hw * 0.2), p.AX, 0.9)

    return fn


defn(0x2ABD, sub_dot())
defn(0x2ABE, sub_dot(True))


@define(0x2AA4)
def gtoverlt(g, p):
    hw = HW(p)
    t = T(p)
    y0, y1 = p.AX - hw, p.AX + hw
    fill_poly(g, angle_poly(p, p.M - hw, p.M + hw * 0.45, y0, y1, t, tip_left=False))
    fill_poly(g, angle_poly(p, p.M - hw * 0.45, p.M + hw, y0, y1, t))


@define(0x2AA5)
def gtbesidelt(g, p):
    hw = HW(p) * 1.05
    t = T(p) * 0.92
    y0, y1 = p.AX - hw * 0.9, p.AX + hw * 0.9
    fill_poly(g, angle_poly(p, p.M - hw, p.M - t * 0.1, y0, y1, t, tip_left=False))
    fill_poly(g, angle_poly(p, p.M + t * 0.1, p.M + hw, y0, y1, t))


def wedges(kind):
    def fn(g, p):
        hw = HW(p)
        t = T(p)
        x0, x1, y0, y1 = p.M - hw, p.M + hw, p.AX - hw, p.AX + hw
        if kind == "dbl":
            tt = fit_t(p, t, hw, 2.2, 0.45)
            prim_wedge(g, p, x0, x1, y0, y1, tt)
            gp = tt * 1.0 + WG(p) * 0.5
            prim_wedge(g, p, x0 + gp * 1.4, x1 - gp * 1.4, y0, y1 - gp * 2.4, tt)
        elif kind == "dblv":
            tt = fit_t(p, t, hw, 2.2, 0.45)
            prim_wedge(g, p, x0, x1, y0, y1, tt, flip=True)
            gp = tt * 1.0 + WG(p) * 0.5
            prim_wedge(g, p, x0 + gp * 1.4, x1 - gp * 1.4, y0 + gp * 2.4, y1, tt, flip=True)
        elif kind == "two":
            o = hw * 0.32
            prim_wedge(g, p, x0, x1 - 2 * o, y0, y1, t * 0.9)
            prim_wedge(g, p, x0 + 2 * o, x1, y0, y1, t * 0.9)
        elif kind == "twov":
            o = hw * 0.32
            prim_wedge(g, p, x0, x1 - 2 * o, y0, y1, t * 0.9, flip=True)
            prim_wedge(g, p, x0 + 2 * o, x1, y0, y1, t * 0.9, flip=True)
        elif kind == "overlap":
            prim_wedge(g, p, x0, x1, y0, y1, t * 0.9)
            prim_wedge(g, p, x0, x1, y0, y1, t * 0.9, flip=True)
        elif kind in ("stem", "stemv"):
            prim_wedge(g, p, x0, x1, y0, y1, t, flip=kind == "stemv")
            g.rect(p.M - t / 2, y0, p.M + t / 2, y1)
        elif kind in ("dash", "dashv"):
            prim_wedge(g, p, x0, x1, y0, y1, t, flip=kind == "dashv")
            g.rect(x0 + hw * 0.1, p.AX - t / 2, x1 - hw * 0.1, p.AX + t / 2)

    return fn


for _cp, _k in [(0x2A53, "dbl"), (0x2A54, "dblv"), (0x2A55, "two"), (0x2A56, "twov"), (0x2A59, "overlap"),
                (0x2A5A, "stem"), (0x2A5B, "stemv"), (0x2A5C, "dash"), (0x2A5D, "dashv")]:
    defn(_cp, wedges(_k))


def cups_joined(cap=False):
    def fn(g, p):
        hw = HW(p) * 1.08
        t = fit_t(p, T(p), 2 * hw, 3, 0.5)
        tmp = tmp_glyph(p)
        y0, y1 = p.AX - hw * 0.92, p.AX + hw * 0.92
        prim_cup(tmp, p, p.M - hw, p.M + t / 2, y0, y1, t)
        prim_cup(tmp, p, p.M - t / 2, p.M + hw, y0, y1, t)
        if cap:
            mirror_into(g, tmp, cy=p.AX)
        else:
            g.add(tmp.contours)

    return fn


defn(0x2A4A, cups_joined())
defn(0x2A4B, cups_joined(True))


def closed_cup(cap=False):
    def fn(g, p):
        hw = HW(p) * 0.85
        t = T(p)
        tmp = tmp_glyph(p)
        y0, y1 = p.AX - hw * 1.1, p.AX + hw * 1.1
        prim_cup(tmp, p, p.M - hw, p.M + hw, y0, y1 - t * 0.5, t)
        tmp.rect(p.M - hw * 1.25, y1 - t, p.M + hw * 1.25, y1)
        if cap:
            mirror_into(g, tmp, cy=p.AX)
        else:
            g.add(tmp.contours)

    return fn


defn(0x2A4C, closed_cup())
defn(0x2A4D, closed_cup(True))


def double_square(cup=False):
    def fn(g, p):
        hw = HW(p)
        t = fit_t(p, T(p) * 0.86, 2 * hw, 4, 0.55)
        x0, x1, y0, y1 = p.M - hw, p.M + hw, p.AX - hw, p.AX + hw
        gp = WG(p) * 0.6 + t
        if cup:
            prim_sqcup(g, p, x0, x1, y0, y1, t)
            prim_sqcup(g, p, x0 + gp, x1 - gp, y0 + gp, y1, t)
        else:
            prim_sqcap(g, p, x0, x1, y0, y1, t)
            prim_sqcap(g, p, x0 + gp, x1 - gp, y0, y1 - gp, t)

    return fn


defn(0x2A4E, double_square())
defn(0x2A4F, double_square(True))


def triple_bar_vert(n):
    def fn(g, p):
        bars_n(3)(g, p)
        hw = HW(p)
        t = fit_t(p, T(p), 2 * hw, 2 * n + 1, 0.4)
        o = hw * (0.36 if n == 2 else 0.5)
        for i in range(n):
            x = p.M + (i - (n - 1) / 2) * (2 * o / (n - 1))
            g.rect(x - t / 2, p.AX - hw * 1.05, x + t / 2, p.AX + hw * 1.05)

    return fn


defn(0x2A68, triple_bar_vert(2))
defn(0x2A69, triple_bar_vert(3))


@define(0x2A6B)
def tildedots(g, p):
    y0, y1 = tilde_full(g, p)
    vs = (y1 - y0) / 2 + WG(p) * 0.7 + DOTD(p) * 0.4
    hs = HW(p) * 0.72
    odot(g, p, p.M - hs, p.AX - vs, 0.85)
    odot(g, p, p.M + hs, p.AX + vs, 0.85)


defn(0x2A74, colon_eq(dbl=True))


def consecutive_eq(n):
    def fn(g, p):
        hw = HW(p) * 1.12
        gap = WG(p) * 0.55
        w = (2 * hw - (n - 1) * gap) / n
        for i in range(n):
            x0 = p.M - hw + i * (w + gap)
            eq_bars(g, p, x0, x0 + w, t=T(p) * (0.92 if n == 3 else 1.0))

    return fn


defn(0x2A75, consecutive_eq(2))
defn(0x2A76, consecutive_eq(3))


@define(0x2AD7)
def supbesidesub(g, p):
    hw = HW(p) * 1.08
    t = fit_t(p, T(p), hw, 2, 0.4)
    y0, y1 = p.AX - hw * 0.8, p.AX + hw * 0.8
    prim_sub(g, p, p.M - hw, p.M - t * 0.15, y0, y1, t, right=True)
    prim_sub(g, p, p.M + t * 0.15, p.M + hw, y0, y1, t)


@define(0x2AD8)
def supdashsub(g, p):
    supbesidesub(g, p)
    hw = HW(p) * 1.08
    t = fit_t(p, T(p), hw, 2, 0.4)
    g.rect(p.M - hw * 0.5, p.AX - t / 2, p.M + hw * 0.5, p.AX + t / 2)


def rot_shape(shape, ang):
    def fn(g, p):
        hw = HW(p)
        tmp = tmp_glyph(p)
        SHAPES[shape](tmp, p, -hw, hw, -hw, hw, T(p))
        c, s = math.cos(ang), math.sin(ang)
        tmp.transform(lambda q: (p.M + q[0] * c - q[1] * s, p.AX + q[0] * s + q[1] * c))
        g.add(tmp.contours)

    return fn


defn(0x2AD9, rot_shape("elem", math.pi / 2))


def fork(kind):
    def fn(g, p):
        hw = HW(p)
        t = T(p)
        tmp = tmp_glyph(p)
        if kind == "tee":
            prim_cap(tmp, p, p.M - hw, p.M + hw, p.AX - hw, p.AX + hw * 0.55, t)
            tmp.rect(p.M - t / 2, p.AX - hw, p.M + t / 2, p.AX + hw * 1.1)
            tmp.rect(p.M - hw * 0.6, p.AX + hw * 1.1 - t, p.M + hw * 0.6, p.AX + hw * 1.1)
        elif kind == "trans":
            prim_cap(tmp, p, p.M - hw, p.M + hw, p.AX - hw * 0.75, p.AX + hw * 0.75, t)
            tmp.rect(p.M - t / 2, p.AX - hw * 1.15, p.M + t / 2, p.AX + hw * 1.15)
        elif kind in ("nonfork", "fork"):
            prim_cup(tmp, p, p.M - hw, p.M + hw, p.AX - hw * 0.7, p.AX + hw, t)
            tmp.rect(p.M - t / 2, p.AX - hw * 1.15, p.M + t / 2, p.AX + hw)
            if kind == "fork":
                negate(tmp, p, p.AX - hw, p.AX + hw)
        g.add(tmp.contours)

    return fn


defn(0x2ADA, fork("tee"))
defn(0x2ADB, fork("trans"))
defn(0x2ADC, fork("fork"))
defn(0x2ADD, fork("nonfork"))


def short_tack(d):
    def fn(g, p):
        tmp = tmp_glyph(p)
        hw = HW(p)
        t = T(p)
        tmp.rect(-t / 2, -hw * 0.62, t / 2, hw * 0.62)
        tmp.rect(-t / 2, -t / 2, hw * 1.0, t / 2)
        ang = {"left": math.pi, "down": -math.pi / 2, "up": math.pi / 2}[d]
        c, s = math.cos(ang), math.sin(ang)
        ox, oy = {"left": (p.M + hw * 0.5, p.AX), "down": (p.M, p.AX + hw * 0.5), "up": (p.M, p.AX - hw * 0.5)}[d]
        tmp.transform(lambda q: (ox + q[0] * c - q[1] * s, oy + q[0] * s + q[1] * c))
        g.add(tmp.contours)

    return fn


defn(0x2ADE, short_tack("left"))
defn(0x2ADF, short_tack("down"))
defn(0x2AE0, short_tack("up"))


@define(0x2AE2)
def triplerightturnstile(g, p):
    hw = HW(p)
    t = fit_t(p, T(p), 2 * hw, 5, 0.45)
    g.rect(p.M - hw, p.AX - hw, p.M - hw + t, p.AX + hw)
    gp = (2 * hw - t) / 2 * 0.55
    for k in (-1, 0, 1):
        g.rect(p.M - hw, p.AX + k * gp - t / 2, p.M + hw, p.AX + k * gp + t / 2)


defn(0x2AE3, tack(nstems=2, d="left"))
defn(0x2AE4, tack(nbars=2, d="left"))
defn(0x2AE5, tack(nstems=2, nbars=2, d="left"))
defn(0x2AE6, tack(nstems=2, cross=True))


def tack_bar(kind):
    def fn(g, p):
        hw = HW(p)
        t = T(p)
        if kind == "downbar":
            g.rect(p.M - hw * 0.7, p.AX + hw - t, p.M + hw * 0.7, p.AX + hw)
            g.rect(p.M - hw * 0.7, p.AX + hw - 2 * t - WG(p), p.M + hw * 0.7, p.AX + hw - t - WG(p))
            g.rect(p.M - t / 2, p.AX - hw, p.M + t / 2, p.AX + hw - t - WG(p))
        elif kind == "upbar":
            g.rect(p.M - hw * 0.7, p.AX - hw, p.M + hw * 0.7, p.AX - hw + t)
            g.rect(p.M - hw * 0.7, p.AX - hw + t + WG(p), p.M + hw * 0.7, p.AX - hw + 2 * t + WG(p))
            g.rect(p.M - t / 2, p.AX - hw + t + WG(p), p.M + t / 2, p.AX + hw)
        elif kind == "updown":
            g.rect(p.M - hw * 0.7, p.AX - t / 2 - WG(p) * 0.5 - t, p.M + hw * 0.7, p.AX - WG(p) * 0.5 - t / 2)
            g.rect(p.M - hw * 0.7, p.AX + WG(p) * 0.5 + t / 2, p.M + hw * 0.7, p.AX + t / 2 + WG(p) * 0.5 + t)
            g.rect(p.M - t / 2, p.AX + WG(p) * 0.5 + t, p.M + t / 2, p.AX + hw * 1.1)
            g.rect(p.M - t / 2, p.AX - hw * 1.1, p.M + t / 2, p.AX - WG(p) * 0.5 - t)

    return fn


defn(0x2AE7, tack_bar("downbar"))
defn(0x2AE8, tack_bar("upbar"))
defn(0x2AE9, tack_bar("updown"))


def double_tack(up=True):
    def fn(g, p):
        tmp = tmp_glyph(p)
        hw = HW(p)
        t = fit_t(p, T(p), 2 * hw, 3, 0.6)
        o = max(hw * 0.32, t * 0.5 + WG(p) * 0.4)
        tmp.rect(p.M - hw, p.AX - hw, p.M + hw, p.AX - hw + t)
        for s in (-1, 1):
            tmp.rect(p.M + s * o - t / 2, p.AX - hw, p.M + s * o + t / 2, p.AX + hw)
        if up:
            g.add(tmp.contours)
        else:
            mirror_into(g, tmp, cy=p.AX)

    return fn


defn(0x2AEA, double_tack(False))
defn(0x2AEB, double_tack(True))


def double_not(rev=False):
    def fn(g, p):
        tmp = tmp_glyph(p)
        hw = HW(p)
        t = T(p) * 0.92
        gp = eq_gap(p) * 0.85
        y1 = p.AX + hw * 0.45
        tmp.rect(p.M - hw, y1 - t, p.M + hw, y1)
        tmp.rect(p.M - hw, y1 - t - gp, p.M + hw - t - WG(p) * 0.6, y1 - gp)
        tmp.rect(p.M + hw - t, y1, p.M + hw, p.AX - hw * 0.85)
        if rev:
            mirror_into(g, tmp, cx=p.M)
        else:
            g.add(tmp.contours)

    return fn


defn(0x2AEC, double_not())
defn(0x2AED, double_not(True))


@define(0x2AEE)
def notdividesrev(g, p):
    tall_bars(g, p, [p.M])
    hw, hh = HW(p) * 0.55, HW(p) * 0.42
    g.stroke(Path((p.M - hw, p.AX + hh)).L((p.M + hw, p.AX - hh)), pen=mpen(T(p)), start=0, end=0)


def line_circle(kind):
    def fn(g, p):
        t = T(p)
        h = TALL(p)
        r = HW(p) * 0.42
        y0, y1 = p.AX - h, p.AX + h
        if kind == "above":
            circle_ring(g, p.M, y1 - r, r, min(t * 0.85, r * 0.5))
            g.rect(p.M - t / 2, y0, p.M + t / 2, y1 - 2 * r + t * 0.4)
        elif kind == "below":
            circle_ring(g, p.M, y0 + r, r, min(t * 0.85, r * 0.5))
            g.rect(p.M - t / 2, y0 + 2 * r - t * 0.4, p.M + t / 2, y1)
        else:  # down tack with circle below
            hw = HW(p)
            circle_ring(g, p.M, y0 + r, r, min(t * 0.85, r * 0.5))
            g.rect(p.M - t / 2, y0 + 2 * r - t * 0.4, p.M + t / 2, p.AX + hw)
            g.rect(p.M - hw, p.AX + hw - t, p.M + hw, p.AX + hw)

    return fn


defn(0x2AEF, line_circle("above"))
defn(0x2AF0, line_circle("below"))
defn(0x2AF1, line_circle("tack"))


@define(0x2AF2)
def parallelstroke(g, p):
    o = par_off(p)
    tall_bars(g, p, [p.M - o, p.M + o])
    hw = HW(p)
    g.rect(p.M - hw, p.AX - T(p) / 2, p.M + hw, p.AX + T(p) / 2)


@define(0x2AF3)
def paralleltilde(g, p):
    o = par_off(p)
    tall_bars(g, p, [p.M - o, p.M + o])
    tilde_full(g, p)


def tri_vbar(stroke=False, big=False):
    def fn(g, p):
        hw = HW(p)
        t = fit_t(p, T(p) * (1.1 if big else 1.0), 2 * hw, 3, 0.6)
        o = max(hw * 0.62, t + WG(p) * 0.6)
        if big:
            h = BIGH(p)
            for k in (-1, 0, 1):
                g.rect(p.M + k * o - t / 2, p.AX - h, p.M + k * o + t / 2, p.AX + h)
        else:
            tall_bars(g, p, [p.M - o, p.M, p.M + o], t=t)
        if stroke:
            g.rect(p.M - hw * 1.05, p.AX - T(p) / 2, p.M + hw * 1.05, p.AX + T(p) / 2)

    return fn


defn(0x2AF4, tri_vbar())
defn(0x2AF5, tri_vbar(True))
defn(0x2AFC, tri_vbar(big=True), slant=False)


@define(0x2AF6)
def triplecolon(g, p):
    vs = dot_vs(p) * 1.1
    for k in (-1, 0, 1):
        odot(g, p, p.M, p.AX + k * vs, 0.9)


def solidi(n):
    def fn(g, p):
        hw = HW(p) * 1.05
        t = fit_t(p, T(p), 2 * hw, n * 1.6, 0.4)
        h = TALL(p) * 0.92
        sx = h * 0.32
        step = (2 * hw - 2 * sx) / max(n - 1, 1) * (0.9 if n > 1 else 0)
        for i in range(n):
            cx = p.M + (i - (n - 1) / 2) * step
            g.stroke(Path((cx - sx, p.AX - h)).L((cx + sx, p.AX + h)), pen=mpen(t), start=0, end=0)

    return fn


defn(0x2AFB, solidi(3))
defn(0x2AFD, solidi(2))


def white_vbar(big=False):
    def fn(g, p):
        h = BIGH(p) if big else TALL(p)
        hw = HW(p) * (0.42 if not big else 0.55)
        t = T(p) * 0.8
        poly_ring(g, [(p.M - hw, p.AX - h), (p.M - hw, p.AX + h), (p.M + hw, p.AX + h), (p.M + hw, p.AX - h)],
                  min(t, hw * 0.42))

    return fn


defn(0x2AFE, white_vbar())
defn(0x2AFF, white_vbar(True), slant=False)
