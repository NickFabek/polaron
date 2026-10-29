"""Basic Latin lowercase."""

from __future__ import annotations

import math

from ..geom import Contour, lerp, unit, sub
from ..glyph import Glyph, glyph
from ..stroke import Path, Pen
from .parts import (
    ball,
    disc,
    serif_foot,
    arc_h,
    arch,
    bowl_side,
    c_shape,
    clamp,
    diag,
    dot,
    hbar,
    oval,
    serif_foot,
    serif_head,
    vstem,
)


# ------------------------------------------------------------------ helpers
def cut_hw(pen: Pen, a, b):
    """Horizontal half-width of a straight stroke a->b at a horizontal cut."""
    t = unit(sub(b, a))
    if abs(t[1]) < 1e-6:
        return pen.A
    n = (-t[1], t[0])
    s = pen.support(n)
    lam = -s[1] / t[1]
    return abs(s[0] + lam * t[0])


def diag_between(p, xa, ya, xb, yb, side_a, side_b, pen=None, w=1.0, iters=3):
    """Centre-line end points of a diagonal whose *outer* edges touch xa/xb.
    side_a/side_b: +1 means the given x is the left edge of the stroke at
    that end, -1 the right edge, 0 means centre."""
    pen = (pen or p.pen).scaled(w)
    ca, cb = xa, xb
    for _ in range(iters):
        hw = cut_hw(pen, (ca, ya), (cb, yb))
        ca = xa + side_a * hw
        cb = xb + side_b * hw
    return (ca, ya), (cb, yb)


def lc_foot(g, p, *a, **k):
    """Lowercase foot serif: cursive italics have none (only head serifs)."""
    if p.italic and not k.get("down"):
        return
    serif_foot(g, p, *a, **k)


def tail_stem(g, p, xc, top, f=1.0, sx=None, sy=None):
    """Italic stem ending in a rightward cursive tail at the baseline."""
    S = p.S if sx is None else sx
    H = p.H if sy is None else sy
    yb = H / 2 - p.OV * 0.3
    r = p.XH * 0.2 * f
    xe = max(xc + r * 0.75 + 8, min(xc + S * 0.5 + r * 1.1, g.adv - p.cellpad * 0.4))
    path = Path((xc, top)).L((xc, yb + r)).vh((xc + r * 0.75, yb)).L((xe, yb))
    g.stroke(path, pen=Pen(S, H))


def caron_gap(p):
    return min(p.S * 1.18 + 16, (p.R - p.L) * 0.3) * 0.62


def inner_serif(p, counter, n=2):
    """Serif length allowed inside a counter so neighbouring serifs never touch."""
    return max(0.0, min(p.SL, counter * (0.5 - 0.1 * n) - p.S * 0.05))


def ytop(p):
    return p.XH + p.OV


def ybot(p):
    return -p.OV


def arch_top(p):
    return p.XH + p.OV * 0.75


def junction(p):
    return p.XH * 0.5


def i_dot_y(p):
    return p.XH + (p.ASC - p.XH) * 0.62 + p.S * 0.05


# ------------------------------------------------------------------ o, c, e
@glyph("o", 0x6F)
def o(g, p):
    oval(g, p, p.L, p.R, ybot(p), ytop(p))
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


def c_terminals(p):
    return p.XH - (p.XH * 0.27), p.XH * 0.24


@glyph("c", 0x63)
def c(g, p):
    te, be = c_terminals(p)
    xl, xr, yb, yt, cx = c_shape(g, p, p.L, p.R - p.S * 0.05, ybot(p), ytop(p), te, be)
    c_serif_terminals(g, p, xr, te, be, yt, yb)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


def c_serif_terminals(g, p, xr, te, be, yt, yb, top=True, bottom=False):
    if not p.serif:
        return
    if top:
        r = p.S * 0.62 + 6
        ball(g, p, xr - r * 0.22, te - r * 0.2, f=1.0)
        return
    if top:
        # vertical beak hanging from the top terminal
        x0 = xr - p.S / 2
        x1 = xr + p.S / 2 + p.S * 0.12
        g.poly((x0, te + 2), (x1, te + 2), (x1, te - p.S * 0.55), (x1 - p.S * 0.2, te - p.S * 0.55))


@glyph("e", 0x65)
def e(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    x0, x1 = p.L, p.R
    xl, xr = x0 + S / 2, x1 - S / 2
    yb, yt = ybot(p) + H / 2, ytop(p) - H / 2
    cx = (xl + xr) / 2
    hh = (yt - yb) / 2
    ry = arc_h(p, (xr - xl) / 2, hh)
    ybar = p.XH * 0.5 + Hb * 0.05
    bot_end = p.XH * 0.22
    hbar(g, p, xl, x1, ybar)
    path = (
        Path((xr, ybar - Hb / 2))
        .L((xr, max(yt - ry, ybar + 2)))
        .vh((cx, yt))
        .hv((xl, yt - ry))
        .L((xl, yb + ry))
        .vh((cx, yb))
        .hv((xr - S * 0.04, bot_end))
    )
    g.stroke(path)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


# ------------------------------------------------------------------ n h m u r
def n_body(g, p, stem_top, serif=True):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, 0, stem_top)
    if p.italic and p.serif:
        xr = p.R - S * 0.3
        arch(g, p, xs, xr, arch_top(p), p.XH * 0.3, junction(p))
        tail_stem(g, p, xr - S / 2, p.XH * 0.32)
    else:
        arch(g, p, xs, p.R, arch_top(p), 0, junction(p))
    if serif:
        inner = inner_serif(p, (p.R - S) - (p.L + S))
        serif_head(g, p, xs, stem_top)
        lc_foot(g, p, xs, 0, rl=inner)
        lc_foot(g, p, p.R - S / 2, 0, ll=inner)


@glyph("n", 0x6E)
def n(g, p):
    n_body(g, p, p.XH)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("h", 0x68)
def h(g, p):
    n_body(g, p, p.ASC)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


@glyph("m", 0x6D)
def m(g, p):
    S = min(p.S, (p.R - p.L) * 0.255)
    H = p.H * (S / p.S) ** 0.5
    pen = Pen(S, H)
    L, R = p.L - p.S * 0.12, p.R + p.S * 0.12
    xs1 = L + S / 2
    xmid = (L + R) / 2
    vstem(g, p, xs1, 0, p.XH, sx=S)
    at = arch_top(p)
    if p.italic and p.serif:
        R = R - p.S * 0.3
        xmid = (L + R) / 2
    arch(g, p, xs1, xmid + S / 2, at, 0, p.XH * 0.55, sx=S, sy=H)
    if p.italic and p.serif:
        arch(g, p, xmid, R, at, p.XH * 0.3, p.XH * 0.55, sx=S, sy=H)
        tail_stem(g, p, R - S / 2, p.XH * 0.32, sx=S, sy=H, f=0.8)
    else:
        arch(g, p, xmid, R, at, 0, p.XH * 0.55, sx=S, sy=H)
    if p.serif:
        serif_head(g, p, xs1, p.XH, sx=S, length=p.SL * 0.7)
        inner = inner_serif(p, (xmid - S / 2) - (xs1 + S / 2))
        for x in (xs1, xmid, R - S / 2):
            lc_foot(g, p, x, 0, sx=S, ll=inner, rl=inner)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("u", 0x75)
def u(g, p):
    tmp = Glyph("tmp", p)
    S = p.S
    sh = S * 0.3 if p.italic else 0
    xs = p.L + S / 2 + sh
    if not p.italic:
        vstem(tmp, p, xs, 0, p.XH)
    arch(tmp, p, xs, p.R, arch_top(p), 0, junction(p))
    W, XH = p.W, p.XH
    tmp.transform(lambda q: (W - q[0], XH - q[1]))
    g.add(tmp.contours)
    if p.italic:
        tail_stem(g, p, p.R - S / 2 - sh, p.XH)
    if p.serif:
        serif_head(g, p, p.L + S / 2, p.XH)
        serif_head(g, p, p.R - S / 2, p.XH)
        lc_foot(g, p, p.R - S / 2, 0, left=False)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("r", 0x72)
def r(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2 + (p.R - p.L) * 0.1
    vstem(g, p, xs, 0, p.XH)
    yt = arch_top(p) - H / 2
    xr = p.R - S * 0.25
    xm = xs + (xr - xs) * 0.55
    yend = yt - (p.XH * 0.13 + S * 0.25)
    path = Path((xs, junction(p)), 0.42).vh((xm, yt)).hv((xr, yend))
    g.stroke(path)
    ball(g, p, xr - (p.S * 0.62 + 6) * 0.2, yend - (p.S * 0.62 + 6) * 0.15)
    if p.serif:
        serif_head(g, p, xs, p.XH)
        lc_foot(g, p, xs, 0, ll=p.SL * 0.9, rl=p.SL * 1.3)
    g.anchor("top", p.M, p.XH).anchor("bottom", xs, 0)


# ------------------------------------------------------------------ a b d p q g
@glyph("a", 0x61)
def a(g, p):
    if p.italic:
        return a_single(g, p)
    S, H, Hb = p.S, p.H, p.Hb
    xr = p.R - S / 2
    yt = ytop(p) - H / 2
    xm = (p.L + p.R) / 2 - S * 0.02
    ry = arc_h(p, xr - xm, (yt - 0) / 2) * 0.92
    xl_t = p.L + S / 2 + S * 0.12
    te = yt - ry * 0.95
    path = Path((xr, 0)).L((xr, yt - ry)).vh((xm, yt)).hv((xl_t, te))
    g.stroke(path, start=0)
    ball(g, p, xl_t + (p.S * 0.62 + 6) * 0.22, te - (p.S * 0.62 + 6) * 0.2)
    # bowl
    ybt = p.XH * 0.55
    xl = p.L + S / 2
    yb = ybot(p) + H / 2
    xbm = p.L + (p.R - p.L) * 0.47
    hb = (ybt - yb) / 2
    rb = arc_h(p, xbm - xl, hb)
    path = (
        Path((xr, ybt), 1.0)
        .L((xbm, ybt))
        .hv((xl, ybt - rb))
        .L((xl, yb + rb))
        .vh((xbm, yb))
        .hv((xr, yb + rb * 0.9), 0.45)
    )
    g.stroke(path, pen=Pen(S, Hb))
    if p.serif:
        lc_foot(g, p, xr, 0, left=False, rl=p.SL * 0.8)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


def a_single(g, p):
    S = p.S
    xs = p.R - S / 2 - (S * 0.3 if p.italic else 0)
    if p.italic:
        tail_stem(g, p, xs, p.XH)
    else:
        vstem(g, p, xs, 0, p.XH)
    bowl_side(g, p, xs, p.L, ybot(p), ytop(p))
    if p.serif:
        lc_foot(g, p, xs, 0, left=False, rl=p.SL * 0.8)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("b", 0x62)
def b(g, p):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.ASC)
    bowl_side(g, p, xs, p.R, ybot(p), ytop(p))
    if p.serif:
        serif_head(g, p, xs, p.ASC)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


@glyph("d", 0x64)
def d(g, p):
    S = p.S
    xs = p.R - S / 2 - (S * 0.3 if p.italic else 0)
    if p.italic:
        tail_stem(g, p, xs, p.ASC)
    else:
        vstem(g, p, xs, 0, p.ASC)
    bowl_side(g, p, xs, p.L, ybot(p), ytop(p))
    if p.serif:
        serif_head(g, p, xs, p.ASC)
        lc_foot(g, p, xs, 0, left=False)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)
    g.anchor("caron", p.R + caron_gap(p), p.XH)


@glyph("p", 0x70)
def p_(g, p):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, p.DESC, p.XH)
    bowl_side(g, p, xs, p.R, ybot(p), ytop(p))
    if p.serif:
        serif_head(g, p, xs, p.XH)
        lc_foot(g, p, xs, p.DESC)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("q", 0x71)
def q(g, p):
    S = p.S
    xs = p.R - S / 2
    vstem(g, p, xs, p.DESC, p.XH)
    bowl_side(g, p, xs, p.L, ybot(p), ytop(p))
    if p.serif:
        lc_foot(g, p, xs, p.DESC)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("g", 0x67)
def g_(g, p):
    if p.serif and not p.italic:
        return g_double(g, p)
    S, H = p.S, p.H
    xs = p.R - S / 2
    bowl_side(g, p, xs, p.L, ybot(p) + S * 0.1, ytop(p))
    yb = p.DESC - p.OV * 0.6 + H / 2
    rg = (p.XH * 0.0 + (0 - yb)) * 0.55
    xg = (p.L + p.R) / 2 - S * 0.05
    path = (
        Path((xs, p.XH))
        .L((xs, yb + rg))
        .vh((xg, yb))
        .hv((p.L + S / 2 + S * 0.1, yb + rg * 0.75))
    )
    g.stroke(path, start=0)
    if p.serif:
        pass
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


def g_double(g, p):
    """Libertinus-like double-story g: upper bowl, ear, link, lower loop."""
    S, H = p.S, p.H
    sb = S * 0.92
    x0, x1 = p.L + S * 0.25, p.R - S * 0.5
    yb0, yt0 = p.XH * 0.3, p.XH + p.OV * 0.6
    oval(g, p, x0, x1, yb0, yt0, sx=sb, sy=H)
    # ear
    ex = x1 - sb * 0.35
    path = Path((ex, p.XH - H * 0.6)).L((p.R + S * 0.08, p.XH - H * 0.6))
    g.stroke(path, pen=Pen(sb * 0.8, H * 0.9), start="butt", end="butt")
    ball(g, p, p.R + S * 0.08 - (p.S * 0.62 + 6) * 0.6, p.XH - H * 0.6 - (p.S * 0.62 + 6) * 0.35, f=0.75)
    # lower loop
    y_lt = 40
    oval(g, p, p.L - S * 0.1, p.R + S * 0.05, p.DESC - p.OV * 0.6, y_lt + H / 2, sx=S, sy=H,
         ry=(y_lt + H / 2 - p.DESC) * 0.38)
    # link from the upper bowl to the loop
    cx0 = (x0 + x1) / 2
    path = (
        Path((cx0 - sb * 0.6, yb0 + H * 0.35))
        .C((p.L + S * 0.2, yb0 - 10), (p.L + S * 0.4, y_lt + 10), (p.L + (p.R - p.L) * 0.42, y_lt))
    )
    g.stroke(path, pen=Pen(sb * 0.85, H), start="butt", end="butt")
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


# ------------------------------------------------------------------ s
def s_shape(g, p, x0, x1, y0, y1, sx=None, sy=None, spine_w=None, te_f=0.27, be_f=0.25):
    sx = p.S if sx is None else sx
    sy = p.H if sy is None else sy
    spine_w = (1.0 if p.sans else 1.2) if spine_w is None else spine_w
    pen = Pen(sx, sy)
    xl, xr = x0 + sx / 2, x1 - sx / 2
    yb, yt = y0 + sy / 2, y1 - sy / 2
    hgt = yt - yb
    cx = (xl + xr) / 2
    ru = hgt * 0.255
    rl = hgt * 0.27
    te = yt - hgt * te_f
    be = yb + hgt * be_f
    ym = (yt - ru + yb + rl) / 2 + hgt * 0.01
    y_up = yt - ru
    y_lo = yb + rl
    dy = y_up - y_lo
    # spine tangent at the middle
    sl = (xr - xl) * 0.42
    sv = dy * 0.40
    tm = unit((sl, -sv))
    h1 = dy * 0.36
    hm = math.hypot(xr - xl, dy) * 0.24
    path = (
        Path((xr, te))
        .vh((cx, yt))
        .hv((xl, y_up))
        .C((xl, y_up - h1), (cx - tm[0] * hm, ym - tm[1] * hm), (cx, ym), spine_w)
        .C((cx + tm[0] * hm, ym + tm[1] * hm), (xr, y_lo + h1), (xr, y_lo))
        .vh((cx, yb))
        .hv((xl, be))
    )
    g.stroke(path, pen=pen)
    if p.serif:
        # small vertical serifs at both terminals
        bl = 16 + sx * 0.32 + (y1 - y0) * 0.035
        g.rect(xr - sx * 0.05, te + 1, xr + sx * 0.5 + sx * 0.08, te - bl)
        g.rect(xl - sx * 0.5 - sx * 0.08, be - 1, xl + sx * 0.05, be + bl)
    return xl, xr, yb, yt, te, be


@glyph("s", 0x73)
def s(g, p):
    inset = p.S * 0.12 + (p.R - p.L) * 0.02
    s_shape(g, p, p.L + inset, p.R - inset, ybot(p), ytop(p))
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


# ------------------------------------------------------------------ i j l
def i_body(g, p, xc, top, bar=True):
    S = p.S
    if p.italic:
        xc = xc - (p.R - p.L) * 0.12
        tail_stem(g, p, xc, top, f=1.1)
        serif_head(g, p, xc, top, length=(xc - S / 2) - (p.L + S * 0.1), sans=True)
        return xc
    vstem(g, p, xc, 0, top)
    serif_head(g, p, xc, top, length=(xc - S / 2) - (p.L + S * 0.25), sans=True)
    if bar:
        hw = (p.R - p.L) / 2 - S * 0.05
        g.rect(p.M - hw, 0, p.M + hw, p.Hb if p.sans else p.ST)
    return xc


@glyph("dotlessi", 0x131)
def dotlessi(g, p):
    xc = i_body(g, p, p.M + p.S * 0.1, p.XH)
    g.anchor("top", xc, p.XH).anchor("bottom", p.M, 0)


@glyph("i", 0x69)
def i(g, p):
    xc = i_body(g, p, p.M + p.S * 0.1, p.XH)
    dot(g, p, xc, i_dot_y(p))
    g.anchor("top", xc, p.XH).anchor("bottom", p.M, 0)


def j_body(g, p, xc, top):
    S, H = p.S, p.H
    yb = p.DESC + H / 2 - p.OV * 0.4
    rj = (0 - yb) * 0.5
    xe = p.L + S * 0.35
    path = Path((xc, top)).L((xc, yb + rj)).vh((xc - (xc - xe) * 0.55, yb)).L((xe, yb))
    g.stroke(path)
    ball(g, p, xe + (p.S * 0.62 + 6) * 0.3, yb + (p.S * 0.62 + 6) * 0.25)
    serif_head(g, p, xc, top, length=(xc - S / 2) - (p.L + S * 0.6), sans=True)


@glyph("dotlessj", 0x237)
def dotlessj(g, p):
    xc = p.M + p.S * 0.6
    j_body(g, p, xc, p.XH)
    g.anchor("top", xc, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("j", 0x6A)
def j(g, p):
    xc = p.M + p.S * 0.6
    j_body(g, p, xc, p.XH)
    dot(g, p, xc, i_dot_y(p))
    g.anchor("top", xc, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("l", 0x6C)
def l(g, p):
    S, H = p.S, p.H
    if p.serif and not p.italic:
        xc = p.M
        vstem(g, p, xc, 0, p.ASC)
        serif_head(g, p, xc, p.ASC, length=(xc - S / 2) - (p.L + S * 0.25))
        hw = (p.R - p.L) / 2 - S * 0.05
        g.rect(p.M - hw, 0, p.M + hw, p.ST)
        g.anchor("top", xc, p.ASC).anchor("bottom", p.M, 0)
        g.anchor("caron", xc + S / 2 + caron_gap(p) * 1.2, p.XH)
        return
    xc = p.M - (p.R - p.L) * 0.07
    yb = H / 2 - p.OV * 0.3
    rl = p.XH * 0.26
    xe = p.R - S * 0.15
    path = Path((xc, p.ASC)).L((xc, yb + rl)).vh((xc + (xe - xc) * 0.5, yb)).L((xe, yb))
    g.stroke(path)
    serif_head(g, p, xc, p.ASC, length=(xc - S / 2) - (p.L + S * 0.2), sans=True)
    g.anchor("top", xc, p.ASC).anchor("bottom", p.M, 0)
    g.anchor("caron", xc + S / 2 + caron_gap(p) * 1.2, p.XH)


# ------------------------------------------------------------------ f t
@glyph("f", 0x66)
def f(g, p):
    if p.italic:
        return f_italic(g, p)
    S, H = p.S, p.H
    xc = p.M - S * 0.3
    yt = p.ASC + p.OV * 0.5 - H / 2
    rf = (p.ASC - p.XH) * 0.62
    xr = p.R - S * 0.2
    xm = xc + (xr - xc) * 0.5
    path = Path((xc, 0)).L((xc, yt - rf)).vh((xm, yt)).hv((xr, yt - rf * 0.45 - S * 0.15))
    g.stroke(path)
    ball(g, p, xr - (p.S * 0.62 + 6) * 0.22, yt - rf * 0.45 - S * 0.15 - (p.S * 0.62 + 6) * 0.1)
    hbar(g, p, p.L + S * 0.1, p.R - S * 0.35, p.XH - p.Hb / 2)
    if p.serif:
        lc_foot(g, p, xc, 0, ll=p.SL * 1.1, rl=p.SL * 1.1)
    g.anchor("top", xc, p.ASC).anchor("bottom", xc, 0)


def f_italic(g, p):
    S, H = p.S, p.H
    xc = p.M
    yt = p.ASC + p.OV * 0.5 - H / 2
    yb = p.DESC - p.OV * 0.5 + H / 2
    rf = (p.ASC - p.XH) * 0.6
    xr = p.R - S * 0.1
    xl = p.L + S * 0.1
    path = (
        Path((xl, yb + rf * 0.45 + S * 0.15))
        .vh((xc - (xc - xl) * 0.5, yb))
        .hv((xc, yb + rf))
        .L((xc, yt - rf))
        .vh((xc + (xr - xc) * 0.5, yt))
        .hv((xr, yt - rf * 0.45 - S * 0.15))
    )
    g.stroke(path)
    hbar(g, p, p.L + S * 0.1, p.R - S * 0.3, p.XH - p.Hb / 2)
    g.anchor("top", xc, p.ASC).anchor("bottom", xc, p.DESC)


@glyph("t", 0x74)
def t(g, p):
    S, H = p.S, p.H
    xc = p.M - S * 0.35
    top = p.XH + (p.ASC - p.XH) * 0.55
    yb = ybot(p) * 0.6 + H / 2
    rt = p.XH * 0.24
    xr = p.R - S * 0.2
    xm = xc + (xr - xc) * 0.5
    path = Path((xc, top)).L((xc, yb + rt)).vh((xm, yb)).hv((xr, yb + rt * 0.55 + S * 0.1))
    g.stroke(path, start=25)
    hbar(g, p, p.L + S * 0.1, p.R - S * 0.35, p.XH - p.Hb / 2)
    g.anchor("top", xc, p.XH).anchor("bottom", p.M, 0)
    g.anchor("caron", xc + S / 2 + caron_gap(p) * 1.3, p.XH - (p.ASC - top) - 20)


# ------------------------------------------------------------------ diagonals
@glyph("v", 0x76)
def v(g, p):
    pen = p.pen
    a, b = diag_between(p, p.L, p.XH, p.M, 0, 1, 0)
    diag(g, p, a, b)
    a2, b2 = diag_between(p, p.R, p.XH, p.M, 0, -1, 0)
    diag(g, p, a2, b2, w=1.0 if p.sans else 0.62)
    if p.serif:
        top_serifs(g, p, [(a[0], 1.0), (a2[0], 0.62)])
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


def top_serifs(g, p, xs, y=None):
    y = p.XH if y is None else y
    for x, w in xs:
        hw = cut_hw(p.pen, (0, 0), (0.0001, 1)) * w
        lc_foot(g, p, x, y, sx=p.S * w, ll=p.SL * 0.8, rl=p.SL * 0.8, down=True)


@glyph("w", 0x77)
def w(g, p):
    f = 0.8
    pen = p.pen.scaled(f)
    L, R = p.L - p.S * 0.15, p.R + p.S * 0.15
    x1 = L + (R - L) * 0.27
    x2 = L + (R - L) * 0.73
    ym = p.XH * 0.72
    a, b = diag_between(p, L, p.XH, x1, 0, 1, 0, w=f)
    diag(g, p, a, b, w=f)
    c_, d_ = diag_between(p, p.M, ym, x1, 0, 0, 0, w=f)
    diag(g, p, c_, d_, w=f * (1 if p.sans else 0.6))
    e_, f_ = diag_between(p, p.M, ym, x2, 0, 0, 0, w=f)
    diag(g, p, e_, f_, w=f)
    g_, h_ = diag_between(p, R, p.XH, x2, 0, -1, 0, w=f)
    diag(g, p, g_, h_, w=f * (1 if p.sans else 0.6))
    if p.serif:
        top_serifs(g, p, [(a[0], f), (g_[0], f * 0.6)])
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("x", 0x78)
def x(g, p):
    a, b = diag_between(p, p.L, p.XH, p.R, 0, 1, -1)
    diag(g, p, a, b)
    c_, d_ = diag_between(p, p.R, p.XH, p.L, 0, -1, 1)
    diag(g, p, c_, d_, w=1.0 if p.sans else 0.62)
    if p.serif:
        top_serifs(g, p, [(a[0], 1), (c_[0], 0.62)])
        for xx, ww in ((b[0], 1), (d_[0], 0.62)):
            lc_foot(g, p, xx, 0, sx=p.S * ww, ll=p.SL * 0.8, rl=p.SL * 0.8)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("y", 0x79)
def y(g, p):
    if p.italic:
        return y_italic(g, p)
    S = p.S
    a, b = diag_between(p, p.R, p.XH, p.L + S * 0.4, p.DESC, -1, 1)
    diag(g, p, a, b, w=1.0 if p.sans else 0.62)
    ball(g, p, b[0] - (p.S * 0.62 + 6) * 0.3, p.DESC + (p.S * 0.62 + 6) * 0.75, f=0.9)
    # point on the right stroke at baseline
    t = (p.XH - 0) / (p.XH - p.DESC)
    mx = a[0] + (b[0] - a[0]) * t
    c_, d_ = diag_between(p, p.L, p.XH, mx, 0, 1, 0)
    diag(g, p, c_, (mx, 0), end="butt")
    if p.serif:
        top_serifs(g, p, [(c_[0], 1), (a[0], 0.62)])
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


def y_italic(g, p):
    S, H = p.S, p.H
    tmp = Glyph("tmp", p)
    xs = p.L + S / 2
    arch(tmp, p, xs, p.R, arch_top(p), 0, junction(p))
    W, XH = p.W, p.XH
    tmp.transform(lambda q: (W - q[0], XH - q[1]))
    g.add(tmp.contours)
    xr = p.R - S / 2
    yb = p.DESC - p.OV * 0.6 + H / 2
    rg = (0 - yb) * 0.55
    xg = (p.L + p.R) / 2 - S * 0.05
    path = Path((xr, p.XH)).L((xr, yb + rg)).vh((xg, yb)).hv((p.L + S / 2 + S * 0.1, yb + rg * 0.75))
    g.stroke(path, start=0)
    lc_foot(g, p, p.L + S / 2, p.XH, down=True, ll=p.SL * 0.7, rl=p.SL * 0.5)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("z", 0x7A)
def z(g, p):
    S, Hb = p.S, p.Hb
    x0, x1 = p.L + S * 0.15, p.R - S * 0.15
    hbar(g, p, x0, x1, p.XH - Hb / 2)
    hbar(g, p, x0, x1 + S * 0.05, Hb / 2)
    a, b = diag_between(p, x1, p.XH - Hb * 0.5, x0, Hb * 0.5, -1, 1, w=0.95)
    diag(g, p, a, b, w=0.95)
    if p.serif:
        g.rect(x0, p.XH - Hb, x0 + p.S * 0.55, p.XH - Hb - p.S * 0.45)
        g.rect(x1 + S * 0.05, Hb, x1 + S * 0.05 - p.S * 0.55, Hb + p.S * 0.45)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("k", 0x6B)
def k(g, p):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.ASC)
    a, b = diag_between(p, p.R - S * 0.05, p.XH, xs, p.XH * 0.3, -1, 0, w=0.95)
    diag(g, p, a, b, w=0.95, end="butt")
    t = 0.48
    m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    c_, d_ = diag_between(p, m[0], m[1], p.R, 0, 0, -1)
    diag(g, p, c_, d_, start="butt")
    if p.serif:
        serif_head(g, p, xs, p.ASC)
        lc_foot(g, p, xs, 0)
        top_serifs(g, p, [(a[0], 0.62)])
        lc_foot(g, p, d_[0], 0, ll=p.SL * 0.6, rl=p.SL * 0.8)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)
