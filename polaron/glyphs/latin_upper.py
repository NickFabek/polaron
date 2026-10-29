"""Basic Latin uppercase."""

from __future__ import annotations

from ..glyph import glyph
from ..stroke import Path, Pen
from .latin_lower import cut_hw, diag_between, inner_serif, s_shape
from .parts import arc_h, c_shape, clamp, diag, hbar, oval, serif_foot, vstem


def ctop(p):
    return p.CAP + p.OV


def cbot(p):
    return -p.OV


def anchors(g, p, x=None):
    x = p.M if x is None else x
    g.anchor("top", x, p.CAP).anchor("bottom", p.M, 0)


def feet(g, p, xs, y=0, inner=None, sx=None):
    """Foot serifs for a list of stem centres; inner serifs are limited."""
    for x in xs:
        serif_foot(g, p, x, y, sx=sx, ll=inner if x > p.M else None, rl=inner if x < p.M else None)


def heads(g, p, xs, y=None, inner=None, sx=None):
    y = p.CAP if y is None else y
    for x in xs:
        serif_foot(g, p, x, y, sx=sx, down=True, ll=inner if x > p.M else None,
                   rl=inner if x < p.M else None)


def beak(g, p, x, y, dir_x, dir_y, length=None):
    """Vertical serif (beak) at a bar end: x = outer bar end, y = bar edge
    (top edge for downward beaks); dir_x -1 means bar extends to the left."""
    if not p.serif:
        return
    length = p.S * 0.62 if length is None else length
    w = p.S * 0.6
    x0 = x
    x1 = x - dir_x * w
    g.poly((x0, y), (x0, y + dir_y * length), (x1, y + dir_y * length * 0.35), (x1, y))


# ------------------------------------------------------------------ straight
@glyph("H", 0x48)
def H(g, p):
    S = p.S
    L, R = p.L, p.R
    vstem(g, p, L + S / 2, 0, p.CAP)
    vstem(g, p, R - S / 2, 0, p.CAP)
    hbar(g, p, L + S / 2, R - S / 2, p.CAP * 0.5)
    inner = inner_serif(p, R - L - 2 * S)
    feet(g, p, (L + S / 2, R - S / 2), inner=inner)
    heads(g, p, (L + S / 2, R - S / 2), inner=inner)
    anchors(g, p)


@glyph("I", 0x49)
def I(g, p):
    S = p.S
    hw = (p.R - p.L) * 0.36 + S * 0.1
    vstem(g, p, p.M, 0, p.CAP)
    hbar(g, p, p.M - hw, p.M + hw, p.Hb / 2)
    hbar(g, p, p.M - hw, p.M + hw, p.CAP - p.Hb / 2)
    anchors(g, p)


@glyph("E", 0x45)
def E(g, p):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + S * 0.15
    x1 = p.R - S * 0.1
    vstem(g, p, xs, 0, p.CAP)
    hbar(g, p, xs, x1, p.CAP - Hb / 2)
    hbar(g, p, xs, x1 - S * 0.35, p.CAP * 0.52)
    hbar(g, p, xs, x1 + S * 0.05, Hb / 2)
    beak(g, p, x1, p.CAP - Hb, -1, -1)
    beak(g, p, x1 + S * 0.05, Hb, -1, 1)
    feet(g, p, (xs,), inner=0)
    heads(g, p, (xs,), inner=0)
    anchors(g, p)


@glyph("F", 0x46)
def F(g, p):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + S * 0.15
    x1 = p.R - S * 0.1
    vstem(g, p, xs, 0, p.CAP)
    hbar(g, p, xs, x1, p.CAP - Hb / 2)
    hbar(g, p, xs, x1 - S * 0.35, p.CAP * 0.5)
    beak(g, p, x1, p.CAP - Hb, -1, -1)
    serif_foot(g, p, xs, 0, rl=p.SL * 1.1)
    heads(g, p, (xs,), inner=0)
    anchors(g, p)


@glyph("L", 0x4C)
def L_(g, p):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + S * 0.2
    x1 = p.R - S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    hbar(g, p, xs, x1, Hb / 2)
    beak(g, p, x1, Hb, -1, 1)
    heads(g, p, (xs,), inner=p.SL)
    serif_foot(g, p, xs, 0, rl=0)
    anchors(g, p)
    g.anchor("caron", xs + S / 2 + min(p.S * 1.18 + 16, (p.R - p.L) * 0.3) * 0.9, p.XH)


@glyph("T", 0x54)
def T(g, p):
    S, Hb = p.S, p.Hb
    x0, x1 = p.L - S * 0.05, p.R + S * 0.05
    hbar(g, p, x0, x1, p.CAP - Hb / 2)
    vstem(g, p, p.M, 0, p.CAP)
    beak(g, p, x0, p.CAP - Hb, 1, -1)
    beak(g, p, x1, p.CAP - Hb, -1, -1)
    serif_foot(g, p, p.M, 0)
    anchors(g, p)


@glyph("Z", 0x5A)
def Z(g, p):
    S, Hb = p.S, p.Hb
    x0, x1 = p.L + S * 0.05, p.R - S * 0.05
    hbar(g, p, x0 + S * 0.1, x1, p.CAP - Hb / 2)
    hbar(g, p, x0, x1 + S * 0.05, Hb / 2)
    a, b = diag_between(p, x1, p.CAP - Hb * 0.5, x0, Hb * 0.5, -1, 1)
    diag(g, p, a, b)
    beak(g, p, x0 + S * 0.1, p.CAP - Hb, 1, -1)
    beak(g, p, x1 + S * 0.05, Hb, -1, 1)
    anchors(g, p)


# ------------------------------------------------------------------ diagonals
@glyph("A", 0x41)
def A(g, p):
    S = p.S
    thin = 1.0 if p.sans else 0.62
    a, b = diag_between(p, p.M, p.CAP, p.L, 0, 0, 1, w=thin)
    diag(g, p, a, b, w=thin)
    c, d = diag_between(p, p.M, p.CAP, p.R, 0, 0, -1)
    diag(g, p, c, d)
    yb = p.CAP * 0.27
    t = (p.CAP - yb) / p.CAP
    xl = a[0] + (b[0] - a[0]) * t
    xr = c[0] + (d[0] - c[0]) * t
    hbar(g, p, xl, xr, yb)
    if p.serif:
        serif_foot(g, p, b[0], 0, sx=S * thin, rl=p.SL * 0.5)
        serif_foot(g, p, d[0], 0, ll=p.SL * 0.5)
    anchors(g, p)


@glyph("V", 0x56)
def V(g, p):
    thin = 1.0 if p.sans else 0.62
    a, b = diag_between(p, p.L, p.CAP, p.M, 0, 1, 0)
    diag(g, p, a, b)
    c, d = diag_between(p, p.R, p.CAP, p.M, 0, -1, 0, w=thin)
    diag(g, p, c, d, w=thin)
    if p.serif:
        serif_foot(g, p, a[0], p.CAP, down=True, ll=p.SL * 0.8, rl=p.SL * 0.6)
        serif_foot(g, p, c[0], p.CAP, sx=p.S * thin, down=True, ll=p.SL * 0.6, rl=p.SL * 0.8)
    anchors(g, p)


@glyph("W", 0x57)
def W(g, p):
    f = 0.82
    thin = f if p.sans else f * 0.6
    L, R = p.L - p.S * 0.18, p.R + p.S * 0.18
    x1 = L + (R - L) * 0.26
    x2 = L + (R - L) * 0.74
    ym = p.CAP * 0.66
    a, b = diag_between(p, L, p.CAP, x1, 0, 1, 0, w=f)
    diag(g, p, a, b, w=f)
    c, d = diag_between(p, p.M, ym, x1, 0, 0, 0, w=thin)
    diag(g, p, c, d, w=thin)
    e, f_ = diag_between(p, p.M, ym, x2, 0, 0, 0, w=f)
    diag(g, p, e, f_, w=f)
    gg, h = diag_between(p, R, p.CAP, x2, 0, -1, 0, w=thin)
    diag(g, p, gg, h, w=thin)
    # cap the middle apex with a small horizontal cut
    if p.serif:
        serif_foot(g, p, a[0], p.CAP, sx=p.S * f, down=True, ll=p.SL * 0.6, rl=p.SL * 0.5)
        serif_foot(g, p, gg[0], p.CAP, sx=p.S * thin, down=True, ll=p.SL * 0.5, rl=p.SL * 0.6)
    anchors(g, p)


@glyph("X", 0x58)
def X(g, p):
    thin = 1.0 if p.sans else 0.62
    a, b = diag_between(p, p.L, p.CAP, p.R, 0, 1, -1)
    diag(g, p, a, b)
    c, d = diag_between(p, p.R, p.CAP, p.L, 0, -1, 1, w=thin)
    diag(g, p, c, d, w=thin)
    if p.serif:
        for x, w in ((a[0], 1), (c[0], thin)):
            serif_foot(g, p, x, p.CAP, sx=p.S * w, down=True, ll=p.SL * 0.6, rl=p.SL * 0.6)
        for x, w in ((b[0], 1), (d[0], thin)):
            serif_foot(g, p, x, 0, sx=p.S * w, ll=p.SL * 0.6, rl=p.SL * 0.6)
    anchors(g, p)


@glyph("Y", 0x59)
def Y(g, p):
    thin = 1.0 if p.sans else 0.62
    ym = p.CAP * 0.44
    a, b = diag_between(p, p.L, p.CAP, p.M, ym, 1, 0)
    diag(g, p, a, (p.M, ym), end="butt")
    c, d = diag_between(p, p.R, p.CAP, p.M, ym, -1, 0, w=thin)
    diag(g, p, c, (p.M, ym), w=thin, end="butt")
    vstem(g, p, p.M, 0, ym + p.S * 0.1)
    if p.serif:
        serif_foot(g, p, a[0], p.CAP, down=True, ll=p.SL * 0.7, rl=p.SL * 0.6)
        serif_foot(g, p, c[0], p.CAP, sx=p.S * thin, down=True, ll=p.SL * 0.6, rl=p.SL * 0.7)
        serif_foot(g, p, p.M, 0)
    anchors(g, p)


@glyph("K", 0x4B)
def K(g, p):
    S = p.S
    xs = p.L + S / 2 + S * 0.1
    vstem(g, p, xs, 0, p.CAP)
    a, b = diag_between(p, p.R - S * 0.05, p.CAP, xs, p.CAP * 0.28, -1, 0, w=0.95 if p.sans else 0.62)
    diag(g, p, a, b, w=0.95 if p.sans else 0.62, end="butt")
    t = 0.5
    m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    c, d = diag_between(p, m[0], m[1], p.R, 0, 0, -1)
    diag(g, p, c, d, start="butt")
    if p.serif:
        inner = p.SL * 0.5
        serif_foot(g, p, xs, 0, rl=inner)
        serif_foot(g, p, xs, p.CAP, down=True, rl=inner)
        serif_foot(g, p, a[0], p.CAP, sx=S * 0.62, down=True, ll=p.SL * 0.6, rl=p.SL * 0.5)
        serif_foot(g, p, d[0], 0, ll=p.SL * 0.5, rl=p.SL * 0.6)
    anchors(g, p)


@glyph("N", 0x4E)
def N(g, p):
    S = p.S
    xl, xr = p.L + S / 2, p.R - S / 2
    sn = S * (0.92 if p.sans else 0.7)
    vstem(g, p, xl, 0, p.CAP, sx=sn)
    vstem(g, p, xr, 0, p.CAP, sx=sn)
    a, b = diag_between(p, p.L, p.CAP, p.R, 0, 1, -1, w=0.95)
    diag(g, p, a, b, w=0.95)
    if p.serif:
        serif_foot(g, p, xl, 0, sx=sn, rl=p.SL * 0.5)
        serif_foot(g, p, xl, p.CAP, sx=sn, down=True, rl=0)
        serif_foot(g, p, xr, p.CAP, sx=sn, down=True, ll=p.SL * 0.5)
    anchors(g, p)


@glyph("M", 0x4D)
def M(g, p):
    S = p.S
    sm = min(S * 0.92, (p.R - p.L) * 0.24)
    L, R = p.L - S * 0.05, p.R + S * 0.05
    xl, xr = L + sm / 2, R - sm / 2
    vstem(g, p, xl, 0, p.CAP, sx=sm)
    vstem(g, p, xr, 0, p.CAP, sx=sm)
    ym = p.CAP * 0.3
    f = 0.82
    thin = f if p.sans else 0.55
    a, b = diag_between(p, L, p.CAP, p.M, ym, 1, 0, w=thin)
    diag(g, p, a, (p.M, ym), w=thin, end="butt")
    c, d = diag_between(p, R, p.CAP, p.M, ym, -1, 0, w=f)
    diag(g, p, c, (p.M, ym), w=f, end="butt")
    if p.serif:
        inner = p.SL * 0.35
        serif_foot(g, p, xl, 0, sx=sm, rl=inner)
        serif_foot(g, p, xr, 0, sx=sm, ll=inner)
    anchors(g, p)


# ------------------------------------------------------------------ rounds
@glyph("O", 0x4F)
def O(g, p):
    oval(g, p, p.L, p.R, cbot(p), ctop(p))
    anchors(g, p)


@glyph("Q", 0x51)
def Q(g, p):
    S = p.S
    oval(g, p, p.L, p.R, cbot(p), ctop(p))
    a = (p.M + (p.R - p.L) * 0.06, p.CAP * 0.06)
    b = (p.R - S * 0.15, -p.CAP * 0.2)
    diag(g, p, a, b, start="butt", end=0)
    anchors(g, p)


@glyph("C", 0x43)
def C_(g, p):
    te, be = p.CAP * 0.74, p.CAP * 0.25
    xl, xr, yb, yt, cx = c_shape(g, p, p.L, p.R - p.S * 0.03, cbot(p), ctop(p), te, be)
    if p.serif:
        x0 = xr - p.S / 2
        x1 = xr + p.S / 2 + p.S * 0.1
        g.poly((x0, te + 2), (x1, te + 2), (x1, te - p.S * 0.8), (x1 - p.S * 0.25, te - p.S * 0.8))
    anchors(g, p)


@glyph("G", 0x47)
def G(g, p):
    S, Hb = p.S, p.Hb
    te = p.CAP * 0.74
    ybar = p.CAP * 0.46
    xl, xr, yb, yt, cx = c_shape(g, p, p.L, p.R, cbot(p), ctop(p), te, ybar)
    hbar(g, p, p.M + S * 0.05, p.R, ybar - Hb / 2)
    if p.serif:
        x0 = xr - p.S / 2
        x1 = xr + p.S / 2 + p.S * 0.1
        g.poly((x0, te + 2), (x1, te + 2), (x1, te - p.S * 0.8), (x1 - p.S * 0.25, te - p.S * 0.8))
    anchors(g, p)


@glyph("D", 0x44)
def D(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2 + S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    xr = p.R - S / 2
    yt, yb = p.CAP - H / 2, H / 2
    xm = xs + (xr - xs) * 0.45
    ry = arc_h(p, xr - xm, (yt - yb) / 2, f=1.25)
    path = Path((xs, yt)).L((xm, yt)).hv((xr, yt - ry)).L((xr, yb + ry)).vh((xm, yb)).L((xs, yb))
    g.stroke(path)
    feet(g, p, (xs,), inner=0)
    heads(g, p, (xs,), inner=0)
    anchors(g, p)


def d_bowl(g, p, xs, xr, yb, yt, f=1.1):
    """Bowl with flat top/bottom attached to a stem (B, P, R)."""
    xm = xs + (xr - xs) * 0.5
    hh = (yt - yb) / 2
    ry = arc_h(p, xr - xm, hh, f=f)
    path = Path((xs, yt)).L((xm, yt)).hv((xr, yt - ry)).L((xr, yb + ry)).vh((xm, yb)).L((xs, yb))
    g.stroke(path)


@glyph("B", 0x42)
def B(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2 + S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    ym = p.CAP * 0.54
    d_bowl(g, p, xs, p.R - S / 2 - S * 0.25, ym, p.CAP - H / 2, f=1.0)
    d_bowl(g, p, xs, p.R - S / 2, H / 2, ym, f=1.0)
    feet(g, p, (xs,), inner=0)
    heads(g, p, (xs,), inner=0)
    anchors(g, p)


@glyph("P", 0x50)
def P(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2 + S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    d_bowl(g, p, xs, p.R - S / 2, p.CAP * 0.42, p.CAP - H / 2, f=1.0)
    serif_foot(g, p, xs, 0, rl=p.SL * 1.0)
    heads(g, p, (xs,), inner=0)
    anchors(g, p)


@glyph("R", 0x52)
def R(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2 + S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    yb = p.CAP * 0.45
    d_bowl(g, p, xs, p.R - S / 2 - S * 0.1, yb, p.CAP - H / 2, f=1.0)
    a, b = diag_between(p, p.M - S * 0.1, yb, p.R, 0, 0, -1)
    diag(g, p, a, b, start="butt")
    if p.serif:
        serif_foot(g, p, xs, 0, rl=p.SL * 0.5)
        serif_foot(g, p, b[0], 0, ll=p.SL * 0.3, rl=p.SL * 0.6)
    heads(g, p, (xs,), inner=0)
    anchors(g, p)


@glyph("S", 0x53)
def S_(g, p):
    inset = p.S * 0.05
    s_shape(g, p, p.L + inset, p.R - inset, cbot(p), ctop(p), te_f=0.24, be_f=0.24)
    anchors(g, p)


@glyph("U", 0x55)
def U(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yb = cbot(p) + H / 2
    cx = (xl + xr) / 2
    ry = arc_h(p, (xr - xl) / 2, p.CAP / 2)
    path = Path((xl, p.CAP)).L((xl, yb + ry)).vh((cx, yb)).hv((xr, yb + ry)).L((xr, p.CAP))
    g.stroke(path)
    inner = inner_serif(p, p.R - p.L - 2 * S)
    heads(g, p, (xl, xr), inner=inner)
    anchors(g, p)


@glyph("J", 0x4A)
def J(g, p):
    S, H = p.S, p.H
    xr = p.R - S / 2 - S * 0.15
    yb = cbot(p) + H / 2
    xe = p.L + S / 2
    cx = (xe + xr) / 2
    ry = arc_h(p, (xr - xe) / 2, p.CAP / 2)
    path = Path((xr, p.CAP)).L((xr, yb + ry)).vh((cx, yb)).hv((xe, yb + ry * 0.85))
    g.stroke(path)
    hbar(g, p, p.L + (p.R - p.L) * 0.28, xr + S / 2, p.CAP - p.Hb / 2)
    anchors(g, p, x=p.M)
