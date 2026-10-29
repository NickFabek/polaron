"""Greek and Coptic (U+0370–03FF)."""

from __future__ import annotations

from ..glyph import Glyph, glyph, register
from ..stroke import Path, Pen
from .latin_lower import (
    arch_top,
    diag_between,
    inner_serif,
    junction,
    s_shape,
    ybot,
    ytop,
)
from .latin_upper import cbot, ctop, feet, heads
from .marks import GAP_C, MH_C
from .parts import arc_h, arch, bowl_side, c_shape, clamp, diag, dot, hbar, oval, serif_foot, serif_head, vstem


def tonos_anchor(g, p):
    g.anchor("tonos", p.L * 0.1, p.CAP + 12 - GAP_C - MH_C)


def ref(name, uni, base, tonos=False):
    def fn(g, p):
        g.compose = [base]
        if tonos:
            tonos_anchor(g, p)

    register(name, fn, uni)


# shared with Latin
for _n, _u, _b in [
    ("Alpha", 0x391, "A"), ("Beta", 0x392, "B"), ("Epsilon", 0x395, "E"), ("Zeta", 0x396, "Z"),
    ("Eta", 0x397, "H"), ("Iota", 0x399, "I"), ("Kappa", 0x39A, "K"), ("Mu", 0x39C, "M"),
    ("Nu", 0x39D, "N"), ("Omicron", 0x39F, "O"), ("Rho", 0x3A1, "P"), ("Tau", 0x3A4, "T"),
    ("Upsilon", 0x3A5, "Y"), ("Chi", 0x3A7, "X"), ("omicron", 0x3BF, "o"),
]:
    ref(_n, _u, _b, tonos=_n[0].isupper())


def anchors(g, p, upper=True):
    if upper:
        g.anchor("top", p.M, p.CAP).anchor("bottom", p.M, 0)
        tonos_anchor(g, p)
    else:
        g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


# ------------------------------------------------------------------ capitals
def gamma_body(g, p, top):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + S * 0.25
    vstem(g, p, xs, 0, top)
    hbar(g, p, xs - S / 2, p.R - S * 0.05, top - Hb / 2)
    if p.serif:
        from .latin_upper import beak

        beak(g, p, p.R - S * 0.05, top - Hb, -1, -1)
        serif_foot(g, p, xs, 0, rl=p.SL * 1.1)
        serif_foot(g, p, xs, top, down=True, rl=0)


@glyph("Gamma", 0x393)
def Gamma(g, p):
    gamma_body(g, p, p.CAP)
    anchors(g, p)


@glyph("Delta", 0x394)
def Delta(g, p):
    S = p.S
    thin = 1.0 if p.sans else 0.62
    a, b = diag_between(p, p.M, p.CAP, p.L - S * 0.05, p.Hb * 0.5, 0, 1, w=thin)
    diag(g, p, a, b, w=thin)
    c, d = diag_between(p, p.M, p.CAP, p.R + S * 0.05, p.Hb * 0.5, 0, -1)
    diag(g, p, c, d)
    hbar(g, p, p.L - S * 0.05, p.R + S * 0.05, p.Hb / 2)
    anchors(g, p)


@glyph("Theta", 0x398)
def Theta(g, p):
    oval(g, p, p.L, p.R, cbot(p), ctop(p))
    hw = (p.R - p.L) * 0.24
    hbar(g, p, p.M - hw, p.M + hw, p.CAP / 2)
    anchors(g, p)


@glyph("Lambda", 0x39B)
def Lambda(g, p):
    thin = 1.0 if p.sans else 0.62
    a, b = diag_between(p, p.M, p.CAP, p.L, 0, 0, 1, w=thin)
    diag(g, p, a, b, w=thin)
    c, d = diag_between(p, p.M, p.CAP, p.R, 0, 0, -1)
    diag(g, p, c, d)
    if p.serif:
        serif_foot(g, p, b[0], 0, sx=p.S * thin, rl=p.SL * 0.5)
        serif_foot(g, p, d[0], 0, ll=p.SL * 0.5)
    anchors(g, p)


@glyph("Xi", 0x39E)
def Xi(g, p):
    S, Hb = p.S, p.Hb
    hbar(g, p, p.L + S * 0.05, p.R - S * 0.05, p.CAP - Hb / 2)
    hbar(g, p, p.L + S * 0.4, p.R - S * 0.4, p.CAP / 2)
    hbar(g, p, p.L, p.R, Hb / 2)
    anchors(g, p)


def pi_body(g, p, top, x0=None, x1=None):
    S, Hb = p.S, p.Hb
    x0 = p.L if x0 is None else x0
    x1 = p.R if x1 is None else x1
    xl, xr = x0 + S / 2, x1 - S / 2
    vstem(g, p, xl, 0, top)
    vstem(g, p, xr, 0, top)
    hbar(g, p, x0, x1, top - Hb / 2)
    if p.serif:
        inner = inner_serif(p, x1 - x0 - 2 * S)
        serif_foot(g, p, xl, 0, rl=inner)
        serif_foot(g, p, xr, 0, ll=inner)


@glyph("Pi", 0x3A0)
def Pi(g, p):
    pi_body(g, p, p.CAP)
    anchors(g, p)


@glyph("Sigma", 0x3A3)
def Sigma(g, p):
    S, Hb = p.S, p.Hb
    x0, x1 = p.L + S * 0.05, p.R
    hbar(g, p, x0, x1, p.CAP - Hb / 2)
    hbar(g, p, x0, x1 + S * 0.05, Hb / 2)
    xm = p.M + (p.R - p.L) * 0.05
    ym = p.CAP / 2
    a, b = diag_between(p, x0, p.CAP - Hb / 2, xm, ym, 1, 0, w=0.95)
    diag(g, p, a, (xm, ym), w=0.95, end="butt")
    c, d = diag_between(p, x0, Hb / 2, xm, ym, 1, 0, w=0.95)
    diag(g, p, c, (xm, ym), w=0.95, end="butt")
    g.poly((xm - S * 0.3, ym + S * 0.42), (xm + S * 0.42, ym), (xm - S * 0.3, ym - S * 0.42))
    if p.serif:
        from .latin_upper import beak

        beak(g, p, x1, p.CAP - Hb, -1, -1)
        beak(g, p, x1 + S * 0.05, Hb, -1, 1)
    anchors(g, p)


def phi_body(g, p, y0, y1, stem0, stem1, x0=None, x1=None):
    x0 = p.L - p.S * 0.1 if x0 is None else x0
    x1 = p.R + p.S * 0.1 if x1 is None else x1
    S = p.S * 0.92
    oval(g, p, x0, x1, y0, y1, sx=S, sy=p.H * 0.92)
    vstem(g, p, p.M, stem0, stem1)


@glyph("Phi", 0x3A6)
def Phi(g, p):
    phi_body(g, p, p.CAP * 0.12, p.CAP * 0.88, 0, p.CAP)
    if p.serif:
        serif_foot(g, p, p.M, 0)
        serif_foot(g, p, p.M, p.CAP, down=True)
    anchors(g, p)


def psi_body(g, p, y_cup0, y_top, stem0, stem1):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yb = y_cup0 + H / 2
    r = arc_h(p, (xr - xl) / 2, (y_top - yb) / 2)
    path = Path((xl, y_top)).L((xl, yb + r)).vh((p.M, yb)).hv((xr, yb + r)).L((xr, y_top))
    g.stroke(path)
    vstem(g, p, p.M, stem0, stem1)


@glyph("Psi", 0x3A8)
def Psi(g, p):
    psi_body(g, p, p.CAP * 0.3, p.CAP, 0, p.CAP)
    if p.serif:
        serif_foot(g, p, p.M, 0)
    anchors(g, p)


@glyph("Omega", 0x3A9)
def Omega(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    xl, xr = p.L + S / 2, p.R - S / 2
    yt = ctop(p) - H / 2
    cx = p.M
    ry = arc_h(p, (xr - xl) / 2, p.CAP / 2)
    fx = (p.R - p.L) * 0.17
    path = (
        Path((p.M - fx, Hb))
        .C((xl + (p.M - fx - xl) * 0.2, p.CAP * 0.12), (xl, p.CAP * 0.28), (xl, p.CAP * 0.45))
        .L((xl, yt - ry))
        .vh((cx, yt))
        .hv((xr, yt - ry))
        .L((xr, p.CAP * 0.45))
        .C((xr, p.CAP * 0.28), (xr - (xr - p.M - fx) * 0.2, p.CAP * 0.12), (p.M + fx, Hb))
    )
    g.stroke(path, start=0, end=0)
    hbar(g, p, p.L - S * 0.1, p.M - fx + S * 0.4, Hb / 2)
    hbar(g, p, p.M + fx - S * 0.4, p.R + S * 0.1, Hb / 2)
    anchors(g, p)


# ------------------------------------------------------------------ lowercase
@glyph("alpha", 0x3B1)
def alpha(g, p):
    S, H = p.S, p.H
    xs = p.R - S / 2 - S * 0.15
    bowl_side(g, p, xs, p.L, ybot(p), ytop(p), wj=0.55)
    yb = ybot(p) * 0.4 + H / 2
    r = p.XH * 0.22
    path = Path((xs, p.XH + p.OV * 0.5)).L((xs, yb + r)).vh((xs + S * 0.5 + r * 0.3, yb)).L((p.R + S * 0.1, yb))
    g.stroke(path, start=0)
    anchors(g, p, False)


@glyph("beta", 0x3B2)
def beta(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2
    xr_u = p.R - S / 2 - S * 0.3
    xr_l = p.R - S / 2
    yt = p.ASC + p.OV - H / 2
    ym = p.XH * 0.62
    cx = (xs + xr_u) / 2
    ru = (yt - ym) / 2
    path = Path((xs, p.DESC)).L((xs, yt - ru)).vh((cx, yt)).hv((xr_u, yt - ru)).vh((cx, ym)).L((xs + S * 0.3, ym))
    g.stroke(path, start=0)
    yb = ybot(p) + H / 2
    rl = (ym - yb) / 2
    cl = (xs + xr_l) / 2
    path = Path((xs + S * 0.3, ym)).L((cl, ym)).hv((xr_l, ym - rl)).vh((cl, yb)).L((xs, yb))
    g.stroke(path)
    anchors(g, p, False)


@glyph("gamma", 0x3B3)
def gamma(g, p):
    yv = p.DESC * 0.75
    a, b = diag_between(p, p.L, p.XH, p.M, yv, 1, 0)
    diag(g, p, a, (p.M, yv), end="butt")
    c, d = diag_between(p, p.R, p.XH, p.M, yv, -1, 0, w=1.0 if p.sans else 0.62)
    diag(g, p, c, (p.M, yv), w=1.0 if p.sans else 0.62, end="butt")
    vstem(g, p, p.M, p.DESC, yv + p.S * 0.3, sx=p.S * 0.9)
    anchors(g, p, False)


@glyph("delta", 0x3B4)
def delta(g, p):
    S, H = p.S, p.H
    oval(g, p, p.L, p.R, ybot(p), p.XH * 0.98 + p.OV)
    xl = p.L + S / 2 + S * 0.25
    yt = p.ASC + p.OV - H / 2
    r = (p.ASC - p.XH) * 0.6
    path = (
        Path((p.M + S * 0.3, p.XH * 0.95))
        .C((p.M - S * 0.2, p.XH * 1.05), (xl, p.XH * 1.15), (xl, yt - r))
        .vh((p.M + S * 0.1, yt))
        .hv((p.R - S / 2 - S * 0.1, yt - r * 0.7))
    )
    g.stroke(path, start="butt")
    anchors(g, p, False)
    g.anchor("top", p.M, p.ASC)


def epsilon_body(g, p, top, mirror=False):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2 + S * 0.1, p.R - S / 2 - S * 0.15
    yt, yb = top + p.OV - H / 2, ybot(p) + H / 2
    ym = top * 0.54
    xru = xr - S * 0.25
    cxu = (xl + xru) / 2
    cxl = (xl + xr) / 2
    ru = (yt - ym) / 2
    rl = (ym - yb) / 2
    xmid = p.M + S * 0.4
    path = Path((xru, yt - ru * 0.75)).vh((cxu, yt)).hv((xl + S * 0.12, yt - ru)).vh((cxu, ym)).L((xmid, ym))
    g.stroke(path)
    path = Path((xmid, ym)).L((cxl, ym)).hv((xl, ym - rl)).vh((cxl, yb)).hv((xr, yb + rl * 0.75))
    g.stroke(path)


@glyph("epsilon", 0x3B5)
def epsilon(g, p):
    epsilon_body(g, p, p.XH)
    anchors(g, p, False)


@glyph("zeta", 0x3B6)
def zeta(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    top = p.ASC
    hbar(g, p, p.L + S * 0.6, p.R - S * 0.1, top - Hb / 2)
    xl = p.L + S / 2 + S * 0.1
    yb = H / 2 + 10
    path = (
        Path((p.R - S * 0.4, top - Hb))
        .C((p.M, top * 0.72), (xl, top * 0.45), (xl, top * 0.22))
        .vh((p.M, yb))
        .L((p.R - S * 0.9, yb))
        .hv((p.R - S / 2, yb - 90))
        .vh((p.M + S * 0.2, p.DESC + H / 2 + 10))
    )
    g.stroke(path, start="butt", end="butt")
    anchors(g, p, False)


@glyph("eta", 0x3B7)
def eta(g, p):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.XH)
    arch(g, p, xs, p.R, arch_top(p), p.DESC, junction(p))
    anchors(g, p, False)


@glyph("theta", 0x3B8)
def theta(g, p):
    oval(g, p, p.L, p.R, ybot(p), p.ASC + p.OV)
    hbar(g, p, p.L + p.S * 0.5, p.R - p.S * 0.5, (p.ASC) / 2)
    anchors(g, p, False)
    g.anchor("top", p.M, p.ASC)


def iota_body(g, p, xc):
    S, H = p.S, p.H
    yb = H / 2 - p.OV * 0.3
    r = p.XH * 0.22
    xe = p.R - S * 0.35
    path = Path((xc, p.XH)).L((xc, yb + r)).vh((xc + (xe - xc) * 0.55, yb)).L((xe, yb))
    g.stroke(path)


@glyph("iota", 0x3B9)
def iota(g, p):
    xc = p.M - (p.R - p.L) * 0.12
    iota_body(g, p, xc)
    g.anchor("top", xc, p.XH).anchor("bottom", p.M, 0)


@glyph("kappa", 0x3BA)
def kappa(g, p):
    S = p.S
    xs = p.L + S / 2 + S * 0.1
    vstem(g, p, xs, 0, p.XH)
    a, b = diag_between(p, p.R - S * 0.15, p.XH, xs, p.XH * 0.3, -1, 0, w=0.92)
    diag(g, p, a, b, w=0.92, end="butt")
    m = (a[0] + (b[0] - a[0]) * 0.5, a[1] + (b[1] - a[1]) * 0.5)
    c, d = diag_between(p, m[0], m[1], p.R, 0, 0, -1)
    diag(g, p, c, d, start="butt")
    anchors(g, p, False)


@glyph("lambda", 0x3BB)
def lambda_(g, p):
    S = p.S
    a, b = diag_between(p, p.L + S * 0.3, p.ASC, p.R, 0, 1, -1)
    diag(g, p, a, b)
    t = 0.48
    m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    c, d = diag_between(p, m[0], m[1], p.L, 0, 0, 1, w=1.0 if p.sans else 0.62)
    diag(g, p, c, d, w=1.0 if p.sans else 0.62, start="butt")
    anchors(g, p, False)


@glyph("mu", 0x3BC)
def mu(g, p):
    from .latin_lower import u as draw_u

    draw_u(g, p)
    vstem(g, p, p.L + p.S / 2, p.DESC, p.XH * 0.5)
    anchors(g, p, False)


@glyph("uni00B5", 0xB5)
def micro(g, p):
    mu(g, p)


@glyph("nu", 0x3BD)
def nu(g, p):
    S = p.S
    xl, xr = p.L + S / 2, p.R - S / 2
    xv = p.M + S * 0.15
    path = Path((xl, p.XH)).L((xl, p.XH * 0.55)).C((xl, p.XH * 0.2), (xv - S * 0.6, p.XH * 0.05), (xv, 0))
    g.stroke(path, start=0, end=0)
    path = Path((xr, p.XH)).C((xr, p.XH * 0.55), (xv + S * 0.4, p.XH * 0.25), (xv, 0))
    g.stroke(path, start=0, end=0)
    anchors(g, p, False)


@glyph("xi", 0x3BE)
def xi(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    top = p.ASC
    hbar(g, p, p.L + S * 0.6, p.R - S * 0.1, top - Hb / 2)
    xl = p.L + S / 2 + S * 0.1
    ym = p.XH * 0.78
    path = (
        Path((p.M + S * 0.5, ym))
        .L((p.M, ym))
        .hv((xl + S * 0.15, (top - Hb + ym) / 2))
        .vh((p.M + S * 0.2, top - Hb / 2 - H / 2 + 4))
    )
    g.stroke(path)
    yb = H / 2 + 10
    path = (
        Path((p.M + S * 0.5, ym))
        .L((p.M, ym))
        .hv((xl, (ym + yb) / 2))
        .vh((p.M, yb))
        .L((p.R - S * 0.9, yb))
        .hv((p.R - S / 2, yb - 90))
        .vh((p.M + S * 0.2, p.DESC + H / 2 + 10))
    )
    g.stroke(path, end="butt")
    anchors(g, p, False)


@glyph("pi", 0x3C0)
def pi(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    hbar(g, p, p.L - S * 0.1, p.R + S * 0.1, p.XH - Hb / 2)
    xl = p.L + S / 2 + (p.R - p.L) * 0.1
    vstem(g, p, xl, 0, p.XH)
    xr = p.R - S / 2 - (p.R - p.L) * 0.1
    yb = H / 2 - p.OV * 0.3
    r = p.XH * 0.2
    path = Path((xr, p.XH)).L((xr, yb + r)).vh((xr + S * 0.6, yb)).L((p.R + S * 0.1, yb))
    g.stroke(path)
    anchors(g, p, False)


@glyph("rho", 0x3C1)
def rho(g, p):
    oval(g, p, p.L, p.R, ybot(p), ytop(p))
    vstem(g, p, p.L + p.S / 2, p.DESC, p.XH * 0.45)
    anchors(g, p, False)
    g.anchor("bottom", p.M, p.DESC)


@glyph("sigma", 0x3C3)
def sigma(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    oval(g, p, p.L, p.R - S * 0.35, ybot(p), p.XH - Hb + H + p.OV * 0.3)
    hbar(g, p, p.M - S * 0.2, p.R + S * 0.15, p.XH - Hb / 2)
    anchors(g, p, False)


@glyph("sigma1", 0x3C2)
def finalsigma(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yt = ytop(p) - H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.XH / 2)
    path = (
        Path((xr, p.XH - p.XH * 0.27))
        .vh((cx, yt))
        .hv((xl, yt - r))
        .L((xl, p.XH * 0.35))
        .C((xl, p.XH * 0.1), (xr, p.XH * 0.12), (xr, -p.XH * 0.08))
        .C((xr, -p.XH * 0.22), (p.M + S * 0.3, p.DESC * 0.85), (p.M - S * 0.2, p.DESC * 0.9))
    )
    g.stroke(path)
    anchors(g, p, False)


@glyph("tau", 0x3C4)
def tau(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    hbar(g, p, p.L, p.R, p.XH - Hb / 2)
    xc = p.M - S * 0.2
    yb = H / 2 - p.OV * 0.3
    r = p.XH * 0.22
    path = Path((xc, p.XH)).L((xc, yb + r)).vh((xc + S * 0.6 + r * 0.3, yb)).L((p.R - S * 0.2, yb))
    g.stroke(path)
    anchors(g, p, False)


def upsilon_body(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yb = ybot(p) + H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.XH / 2, f=1.1)
    path = Path((xl, p.XH)).L((xl, yb + r)).vh((cx, yb)).hv((xr, yb + r)).L((xr, p.XH))
    g.stroke(path)


@glyph("upsilon", 0x3C5)
def upsilon(g, p):
    upsilon_body(g, p)
    anchors(g, p, False)


@glyph("phi", 0x3C6)
def phi(g, p):
    # loopy phi: open left bowl, closed right loop around the stem
    S, H = p.S, p.H
    xl, xr = p.L + S / 2 - S * 0.1, p.R - S / 2 + S * 0.1
    yt, yb = ytop(p) - H / 2, ybot(p) + H / 2
    r = arc_h(p, (xr - xl) / 2, p.XH / 2)
    path = (
        Path((xl + S * 0.2, p.XH))
        .C((xl - S * 0.1, p.XH * 0.75), (xl, p.XH * 0.6), (xl, p.XH * 0.45))
        .vh((p.M, yb))
        .hv((xr, yb + r))
        .L((xr, yt - r))
        .vh((p.M + (xr - p.M) * 0.35, yt))
        .hv((p.M - S * 0.1, yt - r * 0.8))
        .L((p.M - S * 0.1, p.DESC))
    )
    g.stroke(path, start=0, end=0)
    anchors(g, p, False)


@glyph("phi1", 0x3D5)
def phisymbol(g, p):
    phi_body(g, p, ybot(p), ytop(p), p.DESC, p.ASC, x0=p.L - p.S * 0.05, x1=p.R + p.S * 0.05)
    anchors(g, p, False)


@glyph("chi", 0x3C7)
def chi(g, p):
    a, b = diag_between(p, p.L, p.XH, p.R, p.DESC, 1, -1)
    diag(g, p, a, b)
    c, d = diag_between(p, p.R, p.XH, p.L, p.DESC, -1, 1, w=1.0 if p.sans else 0.62)
    diag(g, p, c, d, w=1.0 if p.sans else 0.62)
    anchors(g, p, False)


@glyph("psi", 0x3C8)
def psi(g, p):
    psi_body(g, p, ybot(p), p.XH, p.DESC, p.ASC)
    anchors(g, p, False)


def omega_body(g, p):
    S, H = p.S * 0.9, p.H * 0.9
    pen = Pen(S, H)
    L, R = p.L - p.S * 0.1, p.R + p.S * 0.1
    xl, xr = L + S / 2, R - S / 2
    yb = ybot(p) + H / 2
    q1 = xl + (p.M - xl) * 0.5
    q2 = p.M + (xr - p.M) * 0.5
    rl = (p.M - xl) * 0.5 * 1.1
    path = (
        Path((xl + S * 0.2, p.XH))
        .C((xl - S * 0.1, p.XH * 0.7), (xl, p.XH * 0.5), (xl, yb + rl))
        .vh((q1, yb))
        .hv((p.M, yb + rl))
        .L((p.M, p.XH * 0.55))
    )
    g.stroke(path, pen=pen, start=0)
    path = (
        Path((xr - S * 0.2, p.XH))
        .C((xr + S * 0.1, p.XH * 0.7), (xr, p.XH * 0.5), (xr, yb + rl))
        .vh((q2, yb))
        .hv((p.M, yb + rl))
    )
    g.stroke(path, pen=pen, start=0)


@glyph("omega", 0x3C9)
def omega(g, p):
    omega_body(g, p)
    anchors(g, p, False)


@glyph("omega1", 0x3D6)
def pisymbol(g, p):
    omega_body(g, p)
    hbar(g, p, p.L - p.S * 0.15, p.R + p.S * 0.15, p.XH - p.Hb / 2)
    anchors(g, p, False)


@glyph("theta1", 0x3D1)
def thetasymbol(g, p):
    """Script theta: open bowl rising into a tall loop that crosses back
    and exits right as a horizontal tail."""
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2 - S * 0.2
    yb = ybot(p) + H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.XH / 2, f=1.0)
    yt = p.ASC + p.OV - H / 2
    xl2 = p.L + (p.R - p.L) * 0.3
    cx2 = (xl2 + xr) / 2
    r2 = (xr - xl2) / 2
    ym = p.XH * 0.55
    path = (
        Path((xl - S * 0.15, p.XH * 0.78))
        .C((xl, p.XH * 0.72), (xl, p.XH * 0.6), (xl, p.XH * 0.5))
        .L((xl, yb + r))
        .vh((cx, yb))
        .hv((xr, yb + r))
        .L((xr, yt - r2))
        .vh((cx2, yt))
        .hv((xl2, yt - r2))
        .L((xl2, ym + r2 * 0.6))
        .vh((xl2 + r2 * 0.6, ym))
        .L((p.R + S * 0.15, ym))
    )
    g.stroke(path, pen=Pen(S * 0.92, H * 0.92), end="butt")
    anchors(g, p, False)


@glyph("uni03F5", 0x3F5)
def lunateepsilon(g, p):
    te, be = p.XH * 0.75, p.XH * 0.24
    c_shape(g, p, p.L + p.S * 0.1, p.R - p.S * 0.1, ybot(p), ytop(p), te, be)
    hbar(g, p, p.L + p.S * 0.3, p.M + p.S * 0.8, p.XH * 0.5)
    anchors(g, p, False)


@glyph("uni03F6", 0x3F6)
def revlunateepsilon(g, p):
    lunateepsilon(g, p)
    g.mirror_x()


@glyph("uni03F1", 0x3F1)
def rhosymbol(g, p):
    S, H = p.S, p.H
    oval(g, p, p.L, p.R, ybot(p), ytop(p))
    xl = p.L + S / 2
    path = Path((xl, p.XH * 0.4)).L((xl, -p.XH * 0.05)).C((xl, p.DESC * 0.45), (p.M, p.DESC * 0.55), (p.R - S * 0.2, p.DESC * 0.6))
    g.stroke(path, end="butt")
    anchors(g, p, False)


@glyph("uni03F0", 0x3F0)
def kappasymbol(g, p):
    S = p.S
    a, b = diag_between(p, p.R - S * 0.1, p.XH, p.L + S * 0.1, 0, -1, 1)
    diag(g, p, a, b)
    path = Path((p.L, p.XH * 0.92)).C((p.M - S * 0.3, p.XH * 0.95), (p.M - S * 0.2, p.XH * 0.6), (p.M, p.XH * 0.45))
    path.C((p.M + S * 0.2, p.XH * 0.3), (p.M + S * 0.3, 0), (p.R + S * 0.05, 0.05 * p.XH))
    g.stroke(path, pen=Pen(p.S * 0.9, p.H * 0.9))
    anchors(g, p, False)


@glyph("uni03F2", 0x3F2)
def lunatesigma(g, p):
    from .latin_lower import c as draw_c

    draw_c(g, p)


@glyph("uni03F9", 0x3F9)
def Lunatesigma(g, p):
    from .latin_upper import C_ as draw_C

    draw_C(g, p)


@glyph("uni03F3", 0x3F3)
def yot(g, p):
    from .latin_lower import j as draw_j

    draw_j(g, p)


@glyph("uni037F", 0x37F)
def Yot(g, p):
    from .latin_upper import J as draw_J

    draw_J(g, p)


@glyph("Digamma", 0x3DC)
def Digamma(g, p):
    from .latin_upper import F as draw_F

    draw_F(g, p)


@glyph("digamma", 0x3DD)
def digamma(g, p):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + S * 0.4
    vstem(g, p, xs, p.DESC, p.XH)
    hbar(g, p, xs - S / 2, p.R - S * 0.2, p.XH - Hb / 2)
    hbar(g, p, xs - S / 2, p.R - S * 0.5, p.XH * 0.35)


@glyph("uni0374", 0x374)
def numeralsign(g, p):
    g.stroke(Path((p.M - p.S * 0.3, p.CAP * 0.72)).L((p.M + p.S * 0.4, p.CAP + 20)), start=0, end=0)


@glyph("uni0375", 0x375)
def lownumeralsign(g, p):
    g.stroke(Path((p.M + p.S * 0.3, 0)).L((p.M - p.S * 0.4, -p.CAP * 0.28)), start=0, end=0)


@glyph("uni037E", 0x37E)
def greekquestion(g, p):
    from .punct import semicolon

    semicolon(g, p)


@glyph("anoteleia", 0x387)
def anoteleia(g, p):
    from .punct import pdot, pdot_d

    pdot(g, p, p.M, p.XH - pdot_d(p))


@glyph("tonos", 0x384)
def tonos(g, p):
    g.stroke(Path((p.M - p.S * 0.25, p.XH + 80), 0.62).L((p.M + p.S * 0.35, p.XH + 230), 1.0))


@glyph("dieresistonos", 0x385)
def dieresistonos(g, p):
    from .marks import mdot

    d = mdot(p)
    o = (p.R - p.L) * 0.28
    for dx in (-o, o):
        dot(g, p, p.M + dx, p.XH + 80 + d / 2, d=d, k=0.66)
    g.stroke(Path((p.M - p.S * 0.15, p.XH + 80), 0.62).L((p.M + p.S * 0.3, p.XH + 250), 1.0))
