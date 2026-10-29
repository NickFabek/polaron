"""Block Elements (U+2580-259F), Braille Patterns (U+2800-28FF), Symbols for
Legacy Computing (sextants, smooth mosaic wedges, eighth blocks), Unicode 16
octants (U+1CD00-1CDE5) and the Powerline glyphs (U+E0A0-E0A3, E0B0-E0BF).

All cell-filling glyphs use the full line box: x 0..W, y BOXB..BOXT, so they
tile seamlessly horizontally and vertically (with line gap 0). Mosaic
geometry is computed in unit cell coordinates with exact fractions and only
then mapped to the master, so the contour structure never depends on it.
"""

from __future__ import annotations

import re
import unicodedata
from fractions import Fraction as Fr

from ..geom import Contour
from ..glyph import register
from ..stroke import Path, Pen
from .box import light
from .parts import disc

KAPPA = 0.5522847498


# ------------------------------------------------------------------ helpers
def cell_h(p):
    return p.BOXT - p.BOXB


def ux(p, u):
    return float(u) * p.W


def vy(p, v):
    """v: 0 = bottom of the line box, 1 = top."""
    return p.BOXB + float(v) * cell_h(p)


def urect(g, p, u0, v0, u1, v1):
    g.rect(ux(p, u0), vy(p, v0), ux(p, u1), vy(p, v1))


def upoly(g, p, pts):
    g.poly(*[(ux(p, u), vy(p, v)) for u, v in pts])


def grid_rects(cells, ncols, nrows):
    """Merge filled grid cells (col, row; row 0 = top) into rectangles:
    horizontal runs per row, then identical runs stacked vertically.
    Returns unit rects (u0, v0, u1, v1)."""
    runs = []  # (row, c0, c1)
    for r in range(nrows):
        c = 0
        while c < ncols:
            if (c, r) in cells:
                c0 = c
                while c < ncols and (c, r) in cells:
                    c += 1
                runs.append((r, c0, c))
            else:
                c += 1
    merged = []  # [r0, r1, c0, c1]
    for r, c0, c1 in runs:
        for m in merged:
            if m[1] == r and m[2] == c0 and m[3] == c1:
                m[1] = r + 1
                break
        else:
            merged.append([r, r + 1, c0, c1])
    out = []
    for r0, r1, c0, c1 in merged:
        out.append((Fr(c0, ncols), 1 - Fr(r1, nrows), Fr(c1, ncols), 1 - Fr(r0, nrows)))
    return out


def fill_grid(g, p, cells, ncols, nrows):
    for r in grid_rects(set(cells), ncols, nrows):
        urect(g, p, *r)


def reg(cp, fn, name=None):
    if name is None:
        name = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"
    register(name, fn, cp, slant=False)


def _const(rects=(), polys=()):
    rects = tuple(rects)
    polys = tuple(polys)

    def fn(g, p):
        for r in rects:
            urect(g, p, *r)
        for q in polys:
            upoly(g, p, q)

    return fn


def _cells(cells, ncols, nrows):
    cells = frozenset(cells)
    return lambda g, p: fill_grid(g, p, cells, ncols, nrows)


# ------------------------------------------------------------------ blocks
E = Fr(1, 8)
reg(0x2580, _const([(0, Fr(1, 2), 1, 1)]))  # upper half
for _k in range(1, 8):  # lower 1/8 .. 7/8
    reg(0x2580 + _k, _const([(0, 0, 1, _k * E)]))
reg(0x2588, _const([(0, 0, 1, 1)]))  # full block
for _i, _k in enumerate(range(7, 0, -1)):  # left 7/8 .. 1/8
    reg(0x2589 + _i, _const([(0, 0, _k * E, 1)]))
reg(0x2590, _const([(Fr(1, 2), 0, 1, 1)]))  # right half
reg(0x2594, _const([(0, 7 * E, 1, 1)]))  # upper 1/8
reg(0x2595, _const([(7 * E, 0, 1, 1)]))  # right 1/8

# quadrants: UL=(0,0) UR=(1,0) LL=(0,1) LR=(1,1) in a 2x2 grid
_Q = {"UL": (0, 0), "UR": (1, 0), "LL": (0, 1), "LR": (1, 1)}
for _cp, _qs in {
    0x2596: "LL",
    0x2597: "LR",
    0x2598: "UL",
    0x2599: "UL LL LR",
    0x259A: "UL LR",
    0x259B: "UL UR LL",
    0x259C: "UL UR LR",
    0x259D: "UR",
    0x259E: "UR LL",
    0x259F: "UR LL LR",
}.items():
    reg(_cp, _cells([_Q[q] for q in _qs.split()], 2, 2))


# shades: a 4 x 8 pixel grid per cell (pixels roughly square at wdth 100);
# every pattern has a period that divides the grid, so cells tile.
SH_C, SH_R = 4, 8


def _light_shade_cells():
    return {(c, r) for r in range(SH_R) for c in range(SH_C) if r % 2 == 0 and c % 2 == (r // 2) % 2}


_LIGHT = _light_shade_cells()
_MEDIUM = {(c, r) for r in range(SH_R) for c in range(SH_C) if (c + r) % 2 == 0}
_DARK = {(c, r) for r in range(SH_R) for c in range(SH_C)} - _LIGHT
reg(0x2591, _cells(_LIGHT, SH_C, SH_R))
reg(0x2592, _cells(_MEDIUM, SH_C, SH_R))
reg(0x2593, _cells(_DARK, SH_C, SH_R))


# ------------------------------------------------------------------ braille
def braille_dot(p):
    return p.W / 2 * 0.34 + p.S * 0.5


def _braille(bits):
    # dot n -> (col, row); rows top to bottom
    pos = {1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (1, 0), 5: (1, 1), 6: (1, 2), 7: (0, 3), 8: (1, 3)}
    dots = [pos[i + 1] for i in range(8) if bits >> i & 1]

    def fn(g, p):
        r = braille_dot(p) / 2
        ch = cell_h(p)
        for col, row in dots:
            cx = p.W * (0.25 + 0.5 * col)
            cy = p.BOXT - ch * (row + 0.5) / 4
            disc(g, cx, cy, r)

    return fn


for _b in range(256):
    reg(0x2800 + _b, _braille(_b))


# ------------------------------------------------------------------ sextants / octants
def _numbered_cells(digits, ncols):
    return [((int(d) - 1) % ncols, (int(d) - 1) // ncols) for d in digits]


for _cp in range(0x1FB00, 0x1FB3C):
    _m = re.fullmatch(r"BLOCK SEXTANT-(\d+)", unicodedata.name(chr(_cp)))
    reg(_cp, _cells(_numbered_cells(_m.group(1), 2), 2, 3))

_HAS_OCTANTS = tuple(map(int, unicodedata.unidata_version.split("."))) >= (16, 0, 0)
if _HAS_OCTANTS:
    for _cp in range(0x1CD00, 0x1CDE6):
        _m = re.fullmatch(r"BLOCK OCTANT-(\d+)", unicodedata.name(chr(_cp)))
        reg(_cp, _cells(_numbered_cells(_m.group(1), 2), 2, 4))


# ------------------------------------------------------------------ smooth mosaic wedges
_PT = {
    "UPPER LEFT": (Fr(0), Fr(1)),
    "UPPER MIDDLE LEFT": (Fr(0), Fr(2, 3)),
    "LOWER MIDDLE LEFT": (Fr(0), Fr(1, 3)),
    "LOWER LEFT": (Fr(0), Fr(0)),
    "UPPER CENTRE": (Fr(1, 2), Fr(1)),
    "LOWER CENTRE": (Fr(1, 2), Fr(0)),
    "UPPER RIGHT": (Fr(1), Fr(1)),
    "UPPER MIDDLE RIGHT": (Fr(1), Fr(2, 3)),
    "LOWER MIDDLE RIGHT": (Fr(1), Fr(1, 3)),
    "LOWER RIGHT": (Fr(1), Fr(0)),
}
_SQUARE = [(Fr(0), Fr(0)), (Fr(0), Fr(1)), (Fr(1), Fr(1)), (Fr(1), Fr(0))]


def clip_halfplane(poly, a, b, keep):
    """Clip a polygon by the line a-b keeping the side containing `keep`.
    Exact arithmetic (Fractions); points on the line are kept once."""

    def side(q):
        return (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])

    sk = side(keep)
    assert sk != 0
    out = []
    n = len(poly)
    for i in range(n):
        P, Q = poly[i], poly[(i + 1) % n]
        sp, sq = side(P) * sk, side(Q) * sk
        if sp >= 0:
            out.append(P)
        if (sp > 0 and sq < 0) or (sp < 0 and sq > 0):
            t = sp / (sp - sq)
            out.append((P[0] + (Q[0] - P[0]) * t, P[1] + (Q[1] - P[1]) * t))
    ded = []
    for q in out:
        if not ded or ded[-1] != q:
            ded.append(q)
    if len(ded) > 1 and ded[0] == ded[-1]:
        ded.pop()
    return ded


for _cp in range(0x1FB3C, 0x1FB68):
    _nm = unicodedata.name(chr(_cp))
    _m = re.fullmatch(r"(LOWER|UPPER) (LEFT|RIGHT) BLOCK DIAGONAL (.+) TO (.+)", _nm)
    _corner = (Fr(0) if _m.group(2) == "LEFT" else Fr(1), Fr(0) if _m.group(1) == "LOWER" else Fr(1))
    _poly = clip_halfplane(_SQUARE, _PT[_m.group(3)], _PT[_m.group(4)], _corner)
    reg(_cp, _const(polys=[_poly]))

_C = (Fr(1, 2), Fr(1, 2))
_TRI = {  # quarter triangles meeting in the cell centre
    "LEFT": [(Fr(0), Fr(0)), (Fr(0), Fr(1)), _C],
    "UPPER": [(Fr(0), Fr(1)), (Fr(1), Fr(1)), _C],
    "RIGHT": [(Fr(1), Fr(1)), (Fr(1), Fr(0)), _C],
    "LOWER": [(Fr(1), Fr(0)), (Fr(0), Fr(0)), _C],
}
# three quarters = the square minus one triangle (a concave pentagon)
_THREEQ = {
    0x1FB68: "LEFT",
    0x1FB69: "UPPER",
    0x1FB6A: "RIGHT",
    0x1FB6B: "LOWER",
}
for _cp, _miss in _THREEQ.items():
    _a, _b, _ = _TRI[_miss]
    # walk the square clockwise starting after the missing edge
    _sq = [(Fr(0), Fr(0)), (Fr(0), Fr(1)), (Fr(1), Fr(1)), (Fr(1), Fr(0))]
    _i = _sq.index(_b)
    _ring = _sq[_i:] + _sq[:_i]  # starts at _b, ends at _a
    reg(_cp, _const(polys=[_ring + [_C]]))
for _cp, _which in {0x1FB6C: "LEFT", 0x1FB6D: "UPPER", 0x1FB6E: "RIGHT", 0x1FB6F: "LOWER"}.items():
    reg(_cp, _const(polys=[_TRI[_which]]))


# ------------------------------------------------------------------ eighth blocks (1FB70-1FB8B)
for _n in range(2, 8):
    reg(0x1FB70 + _n - 2, _const([((_n - 1) * E, 0, _n * E, 1)]))  # vertical 1/8 #n
    reg(0x1FB76 + _n - 2, _const([(0, 1 - _n * E, 1, 1 - (_n - 1) * E)]))  # horizontal 1/8 #n
_L8, _R8 = (0, 0, E, 1), (7 * E, 0, 1, 1)
_U8, _B8 = (0, 7 * E, 1, 1), (0, 0, 1, E)
reg(0x1FB7C, _const([_L8, (E, 0, 1, E)]))
reg(0x1FB7D, _const([_L8, (E, 7 * E, 1, 1)]))
reg(0x1FB7E, _const([_R8, (0, 7 * E, 7 * E, 1)]))
reg(0x1FB7F, _const([_R8, (0, 0, 7 * E, E)]))
reg(0x1FB80, _const([_U8, _B8]))
reg(0x1FB81, _const([(0, 1 - _r * E, 1, 1 - (_r - 1) * E) for _r in (1, 3, 5, 8)]))
for _i, _k in enumerate((2, 3, 5, 6, 7)):
    reg(0x1FB82 + _i, _const([(0, 1 - _k * E, 1, 1)]))  # upper k/8
    reg(0x1FB87 + _i, _const([(1 - _k * E, 0, 1, 1)]))  # right k/8


# ------------------------------------------------------------------ powerline
def _pl_thin(p):
    return light(p)


def pl_arrow(g, p, solid, left):
    W, y0, y1 = p.W, p.BOXB, p.BOXT
    cy = (y0 + y1) / 2
    if solid:
        g.poly((0, y0), (0, y1), (W, cy))
    else:
        t = _pl_thin(p)
        half = (y1 - y0) / 2
        ln = (W * W + half * half) ** 0.5
        d = t * ln / W  # vertical thickness at x = 0
        e = t * ln / half  # horizontal inset of the inner tip
        g.poly((0, y1), (W, cy), (0, y0), (0, y0 + d), (W - e, cy), (0, y1 - d))
    if left:
        g.mirror_x(W / 2)


def _half_ellipse_down(rx, cy, ry):
    """Right half of an ellipse centred on (0, cy), top to bottom."""
    k = KAPPA
    return [
        ("C", (rx * k, cy + ry), (rx, cy + ry * k), (rx, cy)),
        ("C", (rx, cy - ry * k), (rx * k, cy - ry), (0, cy - ry)),
    ]


def _half_ellipse_up(rx, cy, ry):
    """Right half of an ellipse centred on (0, cy), bottom to top."""
    k = KAPPA
    return [
        ("C", (rx * k, cy - ry), (rx, cy - ry * k), (rx, cy)),
        ("C", (rx, cy + ry * k), (rx * k, cy + ry), (0, cy + ry)),
    ]


def pl_round(g, p, solid, left):
    """Half ellipse spanning the whole line box (rx = W); the thin version
    is a crescent: the outer half ellipse minus an inset one."""
    W, y0, y1 = p.W, p.BOXB, p.BOXT
    cy = (y0 + y1) / 2
    ry = (y1 - y0) / 2
    if solid:
        c = Contour((0, y1), _half_ellipse_down(W, cy, ry) + [("L", (0, y1))])
    else:
        t = _pl_thin(p)
        c = Contour(
            (0, y1),
            _half_ellipse_down(W, cy, ry)
            + [("L", (0, y0 + t))]
            + _half_ellipse_up(W - t, cy, ry - t)
            + [("L", (0, y1))],
        )
    g.add(c.clockwise())
    if left:
        g.mirror_x(W / 2)


def pl_corner(g, p, corner):
    """Full-cell right triangle; corner names the right-angle corner."""
    W, y0, y1 = p.W, p.BOXB, p.BOXT
    pts = {
        "LL": [(0, y1), (0, y0), (W, y0)],
        "LR": [(W, y1), (W, y0), (0, y0)],
        "UL": [(0, y0), (0, y1), (W, y1)],
        "UR": [(0, y1), (W, y1), (W, y0)],
    }[corner]
    g.poly(*pts)


def pl_slash(g, p, rising):
    """Corner-to-corner line clipped to the cell (hexagon)."""
    W, y0, y1 = p.W, p.BOXB, p.BOXT
    H = y1 - y0
    t = _pl_thin(p)
    ln = (W * W + H * H) ** 0.5
    a = (t / 2) * ln / H
    b = (t / 2) * ln / W
    g.poly((0, y0), (a, y0), (W, y1 - b), (W, y1), (W - a, y1), (0, y0 + b))
    if not rising:
        g.mirror_x(W / 2)


reg(0xE0B0, lambda g, p: pl_arrow(g, p, True, False))
reg(0xE0B1, lambda g, p: pl_arrow(g, p, False, False))
reg(0xE0B2, lambda g, p: pl_arrow(g, p, True, True))
reg(0xE0B3, lambda g, p: pl_arrow(g, p, False, True))
reg(0xE0B4, lambda g, p: pl_round(g, p, True, False))
reg(0xE0B5, lambda g, p: pl_round(g, p, False, False))
reg(0xE0B6, lambda g, p: pl_round(g, p, True, True))
reg(0xE0B7, lambda g, p: pl_round(g, p, False, True))
reg(0xE0B8, lambda g, p: pl_corner(g, p, "LL"))
reg(0xE0B9, lambda g, p: pl_slash(g, p, False))
reg(0xE0BA, lambda g, p: pl_corner(g, p, "LR"))
reg(0xE0BB, lambda g, p: pl_slash(g, p, True))
reg(0xE0BC, lambda g, p: pl_corner(g, p, "UL"))
reg(0xE0BD, lambda g, p: pl_slash(g, p, True))
reg(0xE0BE, lambda g, p: pl_corner(g, p, "UR"))
reg(0xE0BF, lambda g, p: pl_slash(g, p, False))


# ---- powerline icons (text-sized, drawn between baseline and cap height)
def _icon_t(p):
    return min(max(p.S * 0.9, 30), p.W * 0.15)


def _letter_t(p):
    return min(max(p.S * 0.75, 28), p.W * 0.1)


def pl_branch(g, p):
    """Version-control branch: a stem on the left and a branch that leaves
    it, swings right and ends in an arrow head pointing up."""
    t = _icon_t(p)
    pen = Pen(t, t)
    L, R = p.W * 0.2, p.W * 0.8
    xs = L + t / 2  # stem centre
    top = p.CAP
    # stem: top part only (the branch takes over below)
    g.rect(xs - t / 2, top * 0.52, xs + t / 2, top)
    # S-curve from the bottom of the stem to the right column
    xb = R - p.W * 0.13  # branch column centre
    y_lo, y_hi = top * 0.2, top * 0.52
    path = (
        Path((xs, 0))
        .L((xs, y_lo))
        .C((xs, (y_lo + y_hi) / 2), (xb, (y_lo + y_hi) / 2), (xb, y_hi))
        .L((xb, top * 0.66))
    )
    g.stroke(path, pen=pen)
    # arrow head
    ah = p.W * 0.27
    g.poly((xb - ah, top * 0.64), (xb + ah, top * 0.64), (xb, top * 0.64 + ah * 1.15))


def _letter_L(g, p, x0, x1, y0, y1, t):
    g.rect(x0, y0, x0 + t, y1)
    g.rect(x0, y0, x1, y0 + t * 0.9)


def _letter_N(g, p, x0, x1, y0, y1, t):
    g.rect(x0, y0, x0 + t, y1)
    g.rect(x1 - t, y0, x1, y1)
    g.poly((x0, y1), (x0 + t * 1.15, y1), (x1, y0), (x1 - t * 1.15, y0))


def _letter_C(g, p, x0, x1, y0, y1, t):
    """C as an open ring: half ellipse on the left plus short arms."""
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    tx, ty = t, t * 0.9
    k = KAPPA
    ox, oy = rx, ry
    ix, iy = rx - tx, ry - ty
    c = Contour(
        (x1, y1 - 0),
        [
            ("L", (cx, y1)),
            ("C", (cx - ox * k, cy + oy), (cx - ox, cy + oy * k), (cx - ox, cy)),
            ("C", (cx - ox, cy - oy * k), (cx - ox * k, cy - oy), (cx, cy - oy)),
            ("L", (x1, y0)),
            ("L", (x1, y0 + ty)),
            ("L", (cx, cy - iy)),
            ("C", (cx - ix * k, cy - iy), (cx - ix, cy - iy * k), (cx - ix, cy)),
            ("C", (cx - ix, cy + iy * k), (cx - ix * k, cy + iy), (cx, cy + iy)),
            ("L", (x1, y1 - ty)),
            ("L", (x1, y1)),
        ],
    )
    g.add(c.clockwise())


def pl_ln(g, p, first):
    t = _letter_t(p)
    x0, x1 = p.W * 0.16, p.W * 0.84
    top = p.CAP + 40
    mid = top * 0.5
    gap = top * 0.06
    # first letter upper left, N lower right
    first(g, p, x0, x0 + (x1 - x0) * 0.62, mid + gap / 2, top, t)
    _letter_N(g, p, x0 + (x1 - x0) * 0.3, x1, -10, mid - gap / 2, t)


def pl_lock(g, p):
    t = _icon_t(p)
    x0, x1 = p.W * 0.16, p.W * 0.84
    body_top = p.CAP * 0.5
    # body with a keyhole
    g.rect(x0, 0, x1, body_top)
    cx = p.W / 2
    # keyhole: a slot with a round top (one hole contour)
    kr = (x1 - x0) * 0.085
    kb, kc = body_top * 0.2, body_top * 0.58
    k = KAPPA
    kh = Contour(
        (cx - kr, kb),
        [
            ("L", (cx - kr, kc)),
            ("C", (cx - kr, kc + kr * k), (cx - kr * k, kc + kr), (cx, kc + kr)),
            ("C", (cx + kr * k, kc + kr), (cx + kr, kc + kr * k), (cx + kr, kc)),
            ("L", (cx + kr, kb)),
            ("L", (cx - kr, kb)),
        ],
    )
    g.add(kh.counterclockwise())
    # shackle: arch from the body up to cap height
    r = (x1 - x0) / 2 - p.W * 0.08 - t / 2
    xl, xr = cx - r, cx + r
    ys = body_top - 5
    ytop = p.CAP - t / 2
    path = Path((xl, ys)).L((xl, ytop - r)).C((xl, ytop - r + r * KAPPA), (cx - r * KAPPA, ytop), (cx, ytop))
    path.C((cx + r * KAPPA, ytop), (xr, ytop - r + r * KAPPA), (xr, ytop - r)).L((xr, ys))
    g.stroke(path, pen=Pen(t, t))


reg(0xE0A0, pl_branch)
reg(0xE0A1, lambda g, p: pl_ln(g, p, _letter_L))
reg(0xE0A2, pl_lock)
reg(0xE0A3, lambda g, p: pl_ln(g, p, _letter_C))
