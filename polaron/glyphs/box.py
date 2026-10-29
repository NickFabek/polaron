"""Box Drawing (U+2500-257F).

Every glyph is built from axis-aligned rectangles that overlap at the
junctions (nonzero fill, no overlap removal needed), plus a few true
quarter-circle arcs and diagonals. Lines that reach a cell edge end exactly
on x = 0 / x = W and y = BOXB / y = BOXT so the glyphs tile seamlessly.

The structure of each glyph is derived from its Unicode character name
(arms LEFT/RIGHT/UP/DOWN with LIGHT/HEAVY/SINGLE/DOUBLE weights), so the
contour structure only ever depends on the character, never on the master.
"""

from __future__ import annotations

import math
import re
import unicodedata

from ..geom import Contour
from ..glyph import register

KAPPA = 0.5522847498

LIGHT, HEAVY, DOUBLE = 1, 2, 3
_WEIGHTS = {"LIGHT": LIGHT, "HEAVY": HEAVY, "SINGLE": LIGHT, "DOUBLE": DOUBLE}
_DIRS = {"LEFT": "L", "RIGHT": "R", "UP": "U", "DOWN": "D", "HORIZONTAL": "LR", "VERTICAL": "UD"}


# ------------------------------------------------------------------ metrics
def light(p):
    """Light line thickness: never thinner than 34 units, grows gently
    with weight (65 at Regular, ~106 at Heavy)."""
    return 34 + max(0.0, p.S - 24) * 0.6


def centre(p):
    return p.W / 2, (p.BOXT + p.BOXB) / 2


# ------------------------------------------------------------------ parsing
def parse_arms(desc):
    """'UP HEAVY AND RIGHT DOWN LIGHT' -> {'L':0,'R':1,'U':2,'D':1}.
    A part without a weight word inherits the previous part's weight."""
    arms = dict(L=0, R=0, U=0, D=0)
    weight = None
    for part in desc.split(" AND "):
        words = part.split()
        ws = [_WEIGHTS[w] for w in words if w in _WEIGHTS]
        if ws:
            weight = ws[0]
        for w in words:
            if w in _DIRS:
                if weight is None:
                    raise ValueError(f"no weight in {desc!r}")
                for a in _DIRS[w]:
                    arms[a] = weight
    return arms


# ------------------------------------------------------------------ drawing
def draw_light_heavy(g, p, arms):
    lt = light(p)
    th = {k: (0, lt, 2 * lt)[v] for k, v in arms.items()}
    cx, cy = centre(p)
    vmax = max(th["U"], th["D"])
    hmax = max(th["L"], th["R"])
    L, R, U, D = (th[k] for k in "LRUD")
    # horizontal arms
    if L and R and L == R:
        g.rect(0, cy - L / 2, p.W, cy + L / 2)
    else:
        if L:
            g.rect(0, cy - L / 2, cx + vmax / 2, cy + L / 2)
        if R:
            g.rect(cx - vmax / 2, cy - R / 2, p.W, cy + R / 2)
    # vertical arms
    if U and D and U == D:
        g.rect(cx - U / 2, p.BOXB, cx + U / 2, p.BOXT)
    else:
        if U:
            g.rect(cx - U / 2, cy - hmax / 2, cx + U / 2, p.BOXT)
        if D:
            g.rect(cx - D / 2, p.BOXB, cx + D / 2, cy + hmax / 2)


def draw_double(g, p, arms):
    """Junctions involving double lines (U+2550-256C). The two strokes of a
    double line are light lines centred +-lt from the centre line, so the
    gap between them equals the light thickness."""
    lt = light(p)
    h = lt / 2
    o = 1.5 * lt  # outer half extent of a double line
    cx, cy = centre(p)
    x0, x1, y0, y1 = 0, p.W, p.BOXB, p.BOXT
    L, R, U, D = (arms[k] for k in "LRUD")
    hd = DOUBLE in (L, R)
    vd = DOUBLE in (U, D)
    if hd and not vd:
        # single vertical against a double horizontal
        if U and D:
            g.rect(cx - h, y0, cx + h, y1)
        elif D:
            g.rect(cx - h, y0, cx + h, (cy - lt) if (L and R) else (cy + o))
        elif U:
            g.rect(cx - h, (cy + lt) if (L and R) else (cy - o), cx + h, y1)
        xa = x0 if L else cx - h
        xb = x1 if R else cx + h
        for s in (-1, 1):
            g.rect(xa, cy + s * lt - h, xb, cy + s * lt + h)
        return
    if vd and not hd:
        if L and R:
            g.rect(x0, cy - h, x1, cy + h)
        elif R:
            g.rect((cx + lt) if (U and D) else (cx - o), cy - h, x1, cy + h)
        elif L:
            g.rect(x0, cy - h, (cx - lt) if (U and D) else (cx + o), cy + h)
        ya = y0 if D else cy - h
        yb = y1 if U else cy + h
        for s in (-1, 1):
            g.rect(cx + s * lt - h, ya, cx + s * lt + h, yb)
        return
    # double in both directions: every strip is interrupted by the arm on
    # its own side (inner corners) or runs on as an outer corner.
    for yc, side in ((cy + lt, U), (cy - lt, D)):
        if side:
            if L:
                g.rect(x0, yc - h, cx - h, yc + h)
            if R:
                g.rect(cx + h, yc - h, x1, yc + h)
        else:
            g.rect(x0 if L else cx - o, yc - h, x1 if R else cx + o, yc + h)
    for xc, side in ((cx - lt, L), (cx + lt, R)):
        if side:
            if D:
                g.rect(xc - h, y0, xc + h, cy - h)
            if U:
                g.rect(xc - h, cy + h, xc + h, y1)
        else:
            g.rect(xc - h, y0 if D else cy - o, xc + h, y1 if U else cy + o)


def draw_dashes(g, p, n, vertical, heavy):
    t = light(p) * (2 if heavy else 1)
    cx, cy = centre(p)
    if vertical:
        per = (p.BOXT - p.BOXB) / n
        gap = per * 0.34
        for i in range(n):
            ya = p.BOXB + i * per + gap / 2
            g.rect(cx - t / 2, ya, cx + t / 2, ya + per - gap)
    else:
        per = p.W / n
        gap = per * 0.40
        for i in range(n):
            xa = i * per + gap / 2
            g.rect(xa, cy - t / 2, xa + per - gap, cy + t / 2)


def draw_arc(g, p, vert, horiz):
    """Rounded corner made of a true quarter circle (radius W/2 on the
    centre line) and a straight vertical run to the cell edge."""
    lt = light(p)
    h = lt / 2
    cx, cy = centre(p)
    r = p.W / 2
    # drawn as ARC DOWN AND RIGHT, then mirrored
    ox, oy = cx + r, cy - r  # arc centre
    ro, ri = r + h, r - h
    k = KAPPA
    c = Contour(
        (ox, oy + ro),
        [
            ("C", (ox - ro * k, oy + ro), (ox - ro, oy + ro * k), (ox - ro, oy)),
            ("L", (cx - h, p.BOXB)),
            ("L", (cx + h, p.BOXB)),
            ("L", (ox - ri, oy)),
            ("C", (ox - ri, oy + ri * k), (ox - ri * k, oy + ri), (ox, oy + ri)),
            ("L", (ox, oy + ro)),
        ],
    )
    g.add(c.clockwise())
    if horiz == "L":
        g.mirror_x(cx)
    if vert == "U":
        g.mirror_y(cy)


def diagonal(g, p, rising):
    """Diagonal from corner to corner with horizontal cuts. The ends
    overhang the cell by the horizontal half width so that diagonals in
    diagonally adjacent cells join without a pinch at the shared corner."""
    lt = light(p)
    H = p.BOXT - p.BOXB
    a = (lt / 2) * math.hypot(p.W, H) / H
    y0, y1 = p.BOXB, p.BOXT
    if rising:
        g.poly((-a, y0), (a, y0), (p.W + a, y1), (p.W - a, y1))
    else:
        g.poly((-a, y1), (a, y1), (p.W + a, y0), (p.W - a, y0))


# ------------------------------------------------------------------ registry
_DASH = re.compile(r"^(LIGHT|HEAVY) (DOUBLE|TRIPLE|QUADRUPLE) DASH (HORIZONTAL|VERTICAL)$")
_ARC = re.compile(r"^LIGHT ARC (UP|DOWN) AND (LEFT|RIGHT)$")
_NDASH = {"DOUBLE": 2, "TRIPLE": 3, "QUADRUPLE": 4}


def _make(cp):
    desc = unicodedata.name(chr(cp))
    assert desc.startswith("BOX DRAWINGS "), desc
    desc = desc[len("BOX DRAWINGS "):]

    m = _DASH.match(desc)
    if m:
        heavy = m.group(1) == "HEAVY"
        n = _NDASH[m.group(2)]
        vertical = m.group(3) == "VERTICAL"
        return lambda g, p: draw_dashes(g, p, n, vertical, heavy)

    m = _ARC.match(desc)
    if m:
        vert = m.group(1)[0]
        horiz = m.group(2)[0]
        return lambda g, p: draw_arc(g, p, vert, horiz)

    if desc == "LIGHT DIAGONAL UPPER RIGHT TO LOWER LEFT":
        return lambda g, p: diagonal(g, p, True)
    if desc == "LIGHT DIAGONAL UPPER LEFT TO LOWER RIGHT":
        return lambda g, p: diagonal(g, p, False)
    if desc == "LIGHT DIAGONAL CROSS":
        return lambda g, p: (diagonal(g, p, True), diagonal(g, p, False))

    arms = parse_arms(desc)
    if DOUBLE in arms.values():
        return lambda g, p: draw_double(g, p, arms)
    return lambda g, p: draw_light_heavy(g, p, arms)


for _cp in range(0x2500, 0x2580):
    register(f"uni{_cp:04X}", _make(_cp), _cp, slant=False)
