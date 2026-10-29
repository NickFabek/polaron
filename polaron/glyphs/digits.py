"""Lining figures."""

from __future__ import annotations

from ..glyph import glyph
from ..stroke import Path
from .latin_lower import diag_between
from .parts import arc_h, ball, clamp, diag, disc, hbar, oval, vstem


def frame(p):
    inset = p.S * 0.12 + (p.R - p.L) * 0.02
    return p.L + inset, p.R - inset


def top(p):
    return p.CAP + p.OV


def bot(p):
    return -p.OV


def anchors(g, p):
    g.anchor("top", p.M, p.CAP).anchor("bottom", p.M, 0)


def zero_body(g, p):
    x0, x1 = frame(p)
    oval(g, p, x0, x1, bot(p), top(p), ry=arc_h(p, (x1 - x0 - p.S) / 2, p.CAP / 2, f=1.25))
    return x0, x1


@glyph("zero", 0x30)
def zero(g, p):
    x0, x1 = zero_body(g, p)
    inner = (x1 - x0) - 2 * p.S
    rx = clamp(p.S * 0.62, 6, inner * 0.24)
    disc(g, p.M, p.CAP / 2, rx, rx * 1.55)
    anchors(g, p)


@glyph("zero.slash")
def zero_slash(g, p):
    x0, x1 = zero_body(g, p)
    S = p.S
    a = (x0 + S * 1.05, p.CAP * 0.2)
    b = (x1 - S * 1.05, p.CAP * 0.8)
    diag(g, p, a, b, w=0.85, start="butt", end="butt")
    anchors(g, p)


@glyph("zero.plain")
def zero_plain(g, p):
    zero_body(g, p)
    anchors(g, p)


@glyph("one", 0x31)
def one(g, p):
    S, H = p.S, p.H
    x0, x1 = frame(p)
    xc = p.M + S * 0.2
    vstem(g, p, xc, 0, p.CAP)
    # flag
    a = (xc - S * 0.1, p.CAP - H * 0.55)
    b = (x0 + S * 0.35, p.CAP * 0.73)
    g.stroke(Path(a, 1.0).L(b, 1.0), start="butt", end="butt")
    hbar(g, p, x0 + S * 0.25, x1 - S * 0.15, p.Hb / 2)
    anchors(g, p)


@glyph("two", 0x32)
def two(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    x0, x1 = frame(p)
    xl, xr = x0 + S / 2, x1 - S / 2
    yt = top(p) - H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.CAP / 2, f=0.95)
    te = yt - r * 0.92
    path = (
        Path((xl, te))
        .vh((cx, yt))
        .hv((xr, yt - r))
        .C((xr, yt - r * 1.75), (xl + (xr - xl) * 0.1, p.CAP * 0.25), (xl - S * 0.05, Hb * 0.5))
    )
    g.stroke(path, end=0)
    ball(g, p, xl + S * 0.12, te - S * 0.1)
    hbar(g, p, x0, x1 + S * 0.05, Hb / 2)
    anchors(g, p)


@glyph("three", 0x33)
def three(g, p):
    S, H = p.S, p.H
    x0, x1 = frame(p)
    xl, xr = x0 + S / 2, x1 - S / 2
    yt, yb = top(p) - H / 2, bot(p) + H / 2
    ym = p.CAP * 0.54
    xru = xr - S * 0.22
    cxu = (xl + xru) / 2 + S * 0.05
    ru = clamp((yt - ym) / 2, 4, (yt - ym) / 2)
    xmid = p.M - (xr - xl) * 0.12
    path = (
        Path((xl, yt - ru * 0.95))
        .vh((cxu, yt))
        .hv((xru, yt - ru))
        .vh((cxu, ym))
        .L((xmid, ym))
    )
    g.stroke(path)
    rl = clamp((ym - yb) / 2, 4, (ym - yb) / 2)
    cxl = (xl + xr) / 2 + S * 0.05
    path = (
        Path((xmid, ym))
        .L((cxl, ym))
        .hv((xr, ym - rl))
        .vh((cxl, yb))
        .hv((xl, yb + rl * 0.95))
    )
    g.stroke(path)
    ball(g, p, xl + S * 0.12, yt - ru * 0.95 - S * 0.1)
    ball(g, p, xl + S * 0.12, yb + rl * 0.95 + S * 0.1)
    anchors(g, p)


@glyph("four", 0x34)
def four(g, p):
    S, Hb = p.S, p.Hb
    x0, x1 = frame(p)
    xs = x1 - S / 2 - (x1 - x0) * 0.12
    ybar = p.CAP * 0.27
    vstem(g, p, xs, 0, p.CAP)
    hbar(g, p, x0, x1, ybar)
    a, b = diag_between(p, xs + S / 2, p.CAP, x0, ybar - Hb / 2, -1, 1, w=0.92)
    diag(g, p, a, b, w=0.92)
    anchors(g, p)


@glyph("five", 0x35)
def five(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    x0, x1 = frame(p)
    xl, xr = x0 + S / 2 + S * 0.05, x1 - S / 2
    yb = bot(p) + H / 2
    ybt = p.CAP * 0.58
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - cx), (ybt - yb) / 2, f=1.05)
    path = Path((xl, ybt)).L((cx, ybt)).hv((xr, ybt - r)).L((xr, yb + r)).vh((cx, yb)).hv((x0 + S / 2, yb + r * 0.9))
    g.stroke(path)
    ball(g, p, x0 + S / 2 + S * 0.12, yb + r * 0.9 + S * 0.1)
    g.rect(xl - S / 2, ybt - H / 2, xl + S / 2, p.CAP)
    hbar(g, p, xl - S / 2, x1 - S * 0.05, p.CAP - Hb / 2)
    anchors(g, p)


def six_body(g, p):
    S, H = p.S, p.H
    x0, x1 = frame(p)
    xl, xr = x0 + S / 2, x1 - S / 2
    ytop_b = p.CAP * 0.6
    oval(g, p, x0, x1, bot(p), ytop_b + H / 2, ry=arc_h(p, (xr - xl) / 2, (ytop_b) / 2, f=1.0))
    yt = top(p) - H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.CAP / 2, f=0.95)
    path = Path((xl, ytop_b * 0.5)).L((xl, yt - r)).vh((cx, yt)).hv((xr - S * 0.05, yt - r * 0.72))
    g.stroke(path)
    ball(g, p, xr - S * 0.05 - S * 0.12, yt - r * 0.72 - S * 0.1)


@glyph("six", 0x36)
def six(g, p):
    six_body(g, p)
    anchors(g, p)


@glyph("nine", 0x39)
def nine(g, p):
    six_body(g, p)
    W, CAP = p.W, p.CAP
    g.transform(lambda q: (W - q[0], CAP - q[1]))
    anchors(g, p)


@glyph("seven", 0x37)
def seven(g, p):
    S, Hb = p.S, p.Hb
    x0, x1 = frame(p)
    hbar(g, p, x0, x1, p.CAP - Hb / 2)
    a, b = diag_between(p, x1, p.CAP - Hb / 2, x0 + (x1 - x0) * 0.22, 0, -1, 1)
    diag(g, p, a, b)
    anchors(g, p)


@glyph("eight", 0x38)
def eight(g, p):
    x0, x1 = frame(p)
    S = min(p.S, (x1 - x0) * 0.3)
    H = p.H * S / p.S
    ym = p.CAP * 0.55
    ins = min(S * 0.3 + (x1 - x0) * 0.03, (x1 - x0) * 0.07)
    oval(g, p, x0 + ins, x1 - ins, ym - H / 2, top(p), sx=S, sy=H,
         ry=arc_h(p, (x1 - x0 - 2 * ins - S) / 2, (top(p) - ym) / 2, f=0.9))
    oval(g, p, x0, x1, bot(p), ym + H / 2, sx=S, sy=H, ry=arc_h(p, (x1 - x0 - S) / 2, ym / 2, f=0.9))
    anchors(g, p)
