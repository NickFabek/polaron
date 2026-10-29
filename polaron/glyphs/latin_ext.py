"""Latin letters that have no canonical decomposition: stroked letters,
ligatures, IPA (U+0250–02AF), turned/mirrored forms, small capitals."""

from __future__ import annotations

from ..geom import Contour
from ..glyph import REGISTRY, Glyph, glyph, register
from ..stroke import Path, Pen
from .latin_lower import (
    arch,
    arch_top,
    diag_between,
    i_dot_y,
    junction,
    s_shape,
    ybot,
    ytop,
)
from .parts import arc_h, bowl_side, c_shape, diag, dot, hbar, oval, serif_head, vstem
from .scaled import derive


def draw(g, p, name):
    """Run another glyph's drawing function into g (contours + anchors)."""
    tmp = Glyph("tmp", p)
    tmp.adv = g.adv
    REGISTRY[name].fn(tmp, p)
    g.add(tmp.contours)
    for k, v in tmp.anchors.items():
        g.anchors.setdefault(k, v)
    return tmp


def drawn(p, name):
    tmp = Glyph("tmp", p)
    REGISTRY[name].fn(tmp, p)
    return tmp


def turned(name, uni, src, cy="x", mirror=False, newname=None):
    """180° rotation (or mirror) of an existing glyph."""

    def fn(g, p):
        t = drawn(p, src)
        W = p.W
        if mirror:
            t.mirror_x()
        else:
            c = {"x": p.XH / 2, "cap": p.CAP / 2}[cy]
            t.transform(lambda q: (W - q[0], 2 * c - q[1]))
        g.add(t.contours)
        top = p.XH if cy == "x" else p.CAP
        g.anchor("top", p.M, top).anchor("bottom", p.M, 0)

    register(name, fn, uni)


def smallcap(name, uni, src):
    def fn(g, p):
        q = derive(p, 1.0, p.XH / p.CAP, 1.0)
        q.XH, q.ASC, q.DESC = p.XH, p.ASC, p.DESC
        tmp = Glyph("tmp", q)
        tmp.adv = g.adv
        REGISTRY[src].fn(tmp, q)
        g.add(tmp.contours)
        g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)

    register(name, fn, uni)


def with_bar(name, uni, src, y, x0, x1, t=0.85):
    """src + horizontal bar from x0..x1 at height y (callables of p)."""

    def fn(g, p):
        draw(g, p, src)
        hbar(g, p, x0(p), x1(p), y(p), sy=p.Hb * t)

    register(name, fn, uni)


def with_slash(name, uni, src, a, b, w=0.85):
    def fn(g, p):
        draw(g, p, src)
        g.stroke(Path(a(p)).L(b(p)), pen=Pen(p.S * w, p.S * w), start="butt", end="butt")

    register(name, fn, uni)


# ------------------------------------------------------------------ stroked letters
def _barh(p):
    return p.ASC - (p.ASC - p.XH) * 0.45


with_bar("dcroat", 0x111, "d", _barh, lambda p: p.M - p.S * 0.1, lambda p: p.R + p.S * 0.25)
with_bar("hbar", 0x127, "h", _barh, lambda p: p.L - p.S * 0.25, lambda p: p.M + p.S * 0.1)
with_bar("bstroke", 0x180, "b", _barh, lambda p: p.L - p.S * 0.25, lambda p: p.M + p.S * 0.1)
with_bar("Dcroat", 0x110, "D", lambda p: p.CAP / 2, lambda p: p.L - p.S * 0.3, lambda p: p.L + p.S * 1.6)
with_bar("Eth", 0xD0, "D", lambda p: p.CAP / 2, lambda p: p.L - p.S * 0.3, lambda p: p.L + p.S * 1.6)
with_bar("Hbar", 0x126, "H", lambda p: p.CAP * 0.78, lambda p: p.L - p.S * 0.3, lambda p: p.R + p.S * 0.3)
with_bar("Tbar", 0x166, "T", lambda p: p.CAP * 0.45, lambda p: p.M - (p.R - p.L) * 0.3, lambda p: p.M + (p.R - p.L) * 0.3)
with_bar("tbar", 0x167, "t", lambda p: p.XH * 0.45, lambda p: p.M - (p.R - p.L) * 0.32,
         lambda p: p.M + (p.R - p.L) * 0.2)
with_bar("uni0268", 0x268, "i", lambda p: p.XH * 0.5, lambda p: p.L + p.S * 0.3, lambda p: p.R - p.S * 0.3)
with_bar("uni0197", 0x197, "I", lambda p: p.CAP * 0.5, lambda p: p.L, lambda p: p.R)
with_bar("uni0289", 0x289, "u", lambda p: p.XH * 0.45, lambda p: p.L - p.S * 0.2, lambda p: p.R + p.S * 0.2)
with_bar("uni0244", 0x244, "U", lambda p: p.CAP * 0.4, lambda p: p.L - p.S * 0.25, lambda p: p.R + p.S * 0.25)
with_bar("uni01E5", 0x1E5, "g", lambda p: p.DESC * 0.42, lambda p: p.M, lambda p: p.R + p.S * 0.3)
with_bar("uni01E4", 0x1E4, "G", lambda p: p.CAP * 0.22, lambda p: p.M + p.S * 0.5, lambda p: p.R + p.S * 0.3)
with_bar("uni0249", 0x249, "dotlessj", lambda p: p.XH * 0.4, lambda p: p.M - p.S * 0.2, lambda p: p.R)
with_bar("uni0248", 0x248, "J", lambda p: p.CAP * 0.5, lambda p: p.M, lambda p: p.R + p.S * 0.25)
with_bar("uni024D", 0x24D, "r", lambda p: p.XH * 0.35, lambda p: p.L, lambda p: p.M + p.S * 0.6)
with_bar("uni024C", 0x24C, "R", lambda p: p.CAP * 0.25, lambda p: p.L - p.S * 0.3, lambda p: p.L + p.S * 1.6)
with_bar("uni024F", 0x24F, "y", lambda p: p.XH * 0.28, lambda p: p.L + p.S * 0.4, lambda p: p.R - p.S * 0.3)
with_bar("uni024E", 0x24E, "Y", lambda p: p.CAP * 0.3, lambda p: p.L + p.S * 0.5, lambda p: p.R - p.S * 0.5)
with_bar("uni01B6", 0x1B6, "z", lambda p: p.XH * 0.5, lambda p: p.L + p.S * 0.4, lambda p: p.R - p.S * 0.4)
with_bar("uni01B5", 0x1B5, "Z", lambda p: p.CAP * 0.5, lambda p: p.L + p.S * 0.3, lambda p: p.R - p.S * 0.3)
with_bar("uni0243", 0x243, "B", lambda p: p.CAP * 0.28, lambda p: p.L - p.S * 0.3, lambda p: p.L + p.S * 1.6)
with_bar("uni0246", 0x246, "E", lambda p: p.CAP * 0.5, lambda p: p.L, lambda p: p.R)
with_bar("uni019A", 0x19A, "l", lambda p: p.XH * 0.75, lambda p: p.L + p.S * 0.3, lambda p: p.R - p.S * 0.4)
with_bar("uni023D", 0x23D, "L", lambda p: p.CAP * 0.5, lambda p: p.L - p.S * 0.1, lambda p: p.L + p.S * 1.9)

with_slash("lslash", 0x142, "l", lambda p: (p.M - (p.R - p.L) * 0.33, p.XH * 0.42),
           lambda p: (p.M + (p.R - p.L) * 0.22, p.XH * 0.86))
with_slash("Lslash", 0x141, "L", lambda p: (p.L - p.S * 0.2, p.CAP * 0.32),
           lambda p: (p.L + (p.R - p.L) * 0.48, p.CAP * 0.66))
with_slash("oslash", 0xF8, "o", lambda p: (p.L + p.S * 0.2, -p.OV - 20), lambda p: (p.R - p.S * 0.2, p.XH + p.OV + 20))
with_slash("Oslash", 0xD8, "O", lambda p: (p.L + p.S * 0.1, -p.OV - 30), lambda p: (p.R - p.S * 0.1, p.CAP + p.OV + 30))
with_slash("uni023C", 0x23C, "c", lambda p: (p.L + p.S * 0.5, -p.OV - 40), lambda p: (p.R - p.S * 0.4, p.XH + p.OV + 40))
with_slash("uni023B", 0x23B, "C", lambda p: (p.L + p.S * 0.5, -p.OV - 40), lambda p: (p.R - p.S * 0.4, p.CAP + p.OV + 40))
with_slash("uni023A", 0x23A, "A", lambda p: (p.L + p.S * 0.3, -40), lambda p: (p.R - p.S * 0.3, p.CAP + 40))
with_slash("uni0247", 0x247, "e", lambda p: (p.L + p.S * 0.3, -p.OV - 40), lambda p: (p.R - p.S * 0.3, p.XH + p.OV + 40))
with_slash("uni023E", 0x23E, "T", lambda p: (p.L + p.S * 0.3, -40), lambda p: (p.R - p.S * 0.3, p.CAP + 40))


@glyph("uni0275", 0x275)
def obarred(g, p):
    draw(g, p, "o")
    hbar(g, p, p.L + p.S * 0.5, p.R - p.S * 0.5, p.XH / 2)


@glyph("uni019F", 0x19F)
def Obarred(g, p):
    draw(g, p, "O")
    hbar(g, p, p.L + p.S * 0.5, p.R - p.S * 0.5, p.CAP / 2)


@glyph("thorn", 0xFE)
def thorn(g, p):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, p.DESC, p.ASC)
    bowl_side(g, p, xs, p.R, ybot(p), ytop(p))
    if p.serif:
        serif_head(g, p, xs, p.ASC)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, p.DESC)


@glyph("Thorn", 0xDE)
def Thorn(g, p):
    from .latin_upper import d_bowl

    S, H = p.S, p.H
    xs = p.L + S / 2 + S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    d_bowl(g, p, xs, p.R - S / 2, p.CAP * 0.2, p.CAP * 0.78, f=1.0)
    g.anchor("top", p.M, p.CAP).anchor("bottom", p.M, 0)


@glyph("eth", 0xF0)
def eth(g, p):
    S, H = p.S, p.H
    oval(g, p, p.L, p.R, ybot(p), p.XH * 0.95 + p.OV)
    xr = p.R - S / 2
    path = (
        Path((p.M - S * 0.2, p.XH * 0.88))
        .C((p.M + S * 0.5, p.XH * 0.86), (xr, p.XH * 0.75), (xr, p.XH * 0.45))
    )
    g.stroke(path)
    path = Path((xr, p.XH * 0.5)).C((xr, p.XH * 1.05), (p.M + S * 0.5, p.ASC * 0.95), (p.L + S * 0.6, p.ASC + p.OV - H / 2))
    g.stroke(path, end="butt")
    g.stroke(Path((p.L + S * 0.6, p.XH * 1.05)).L((p.R - S * 0.2, p.ASC * 0.98)), pen=Pen(S * 0.85, S * 0.85))
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


@glyph("germandbls", 0xDF)
def germandbls(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2
    yt = p.ASC + p.OV - H / 2
    xr = p.R - S / 2 - S * 0.2
    cx = (xs + xr) / 2
    r = (xr - xs) / 2
    ym = p.XH * 0.78
    path = Path((xs, 0)).L((xs, yt - r)).vh((cx, yt)).hv((xr, yt - r)).C((xr, yt - r * 1.8), (p.M, ym + 40), (p.M, ym))
    g.stroke(path, start=0, end="butt")
    yb = ybot(p) + H / 2
    xr2 = p.R - S / 2
    path = Path((p.M, ym)).C((xr2, ym - 10), (xr2, p.XH * 0.55), (xr2, p.XH * 0.35)).vh((p.M + S * 0.2, yb)).L((p.M - S * 0.4, yb))
    g.stroke(path, end="butt")
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


@glyph("uni1E9E", 0x1E9E)
def Germandbls(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2 + S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    xr = p.R - S / 2
    hbar(g, p, xs, xr - S * 0.4, p.CAP - p.Hb / 2)
    a, b = diag_between(p, xr + S / 2, p.CAP, p.M - S * 0.2, p.CAP * 0.56, -1, 0, w=0.9)
    g.stroke(Path(a, 0.9).L(b, 0.9), start=0, end="butt")
    yb = H / 2
    ym = p.CAP * 0.56
    path = Path((p.M - S * 0.2, ym)).L((p.M, ym)).hv((xr, ym * 0.5)).vh((p.M, yb)).L((p.M - S * 0.3, yb))
    g.stroke(path, end="butt")
    g.anchor("top", p.M, p.CAP).anchor("bottom", p.M, 0)


@glyph("ae", 0xE6)
def ae(g, p):
    S = p.S * 0.8
    H = p.H * 0.8
    pen = Pen(S, H)
    L, R = p.L - p.S * 0.25, p.R + p.S * 0.25
    xm = (L + R) / 2
    # left: a-bowl + stem at the middle
    bowl_side(g, p, xm, L, ybot(p), p.XH * 0.6, sx=S, sy=H)
    path = Path((L + S / 2, p.XH * 0.8)).vh((L + (xm - L) * 0.5, p.XH + p.OV - H / 2)).hv((xm, p.XH * 0.7)).L((xm, 0))
    g.stroke(path, pen=pen, end=0)
    # right: e
    yb, yt = ybot(p) + H / 2, ytop(p) - H / 2
    xr = R - S / 2
    cx = (xm + xr) / 2
    ry = (xr - xm) / 2
    ybar = p.XH * 0.5
    g.rect(xm, ybar - H / 2, R, ybar + H / 2)
    path = Path((xr, ybar - H / 2)).L((xr, yt - ry)).vh((cx, yt)).hv((xm, yt - ry))
    g.stroke(path, pen=pen)
    path = Path((xm, p.XH * 0.3)).vh((cx, yb)).hv((xr, p.XH * 0.2))
    g.stroke(path, pen=pen)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("AE", 0xC6)
def AE(g, p):
    S = p.S * 0.85
    pen = Pen(S, p.H * 0.85)
    L, R = p.L - p.S * 0.2, p.R + p.S * 0.1
    xm = p.M + S * 0.1
    a, b = diag_between(p, xm, p.CAP, L, 0, 0, 1, pen=pen)
    g.stroke(Path(a).L(b), pen=pen, start=0, end=0)
    vstem(g, p, xm, 0, p.CAP, sx=S)
    hbar(g, p, xm - S * 0.5, R, p.CAP - p.Hb * 0.425, sy=p.Hb * 0.85)
    hbar(g, p, xm, R - S * 0.3, p.CAP * 0.52, sy=p.Hb * 0.85)
    hbar(g, p, xm, R, p.Hb * 0.425, sy=p.Hb * 0.85)
    t = (p.CAP - p.CAP * 0.3) / p.CAP
    hbar(g, p, a[0] + (b[0] - a[0]) * t, xm, p.CAP * 0.3, sy=p.Hb * 0.85)
    g.anchor("top", p.M, p.CAP).anchor("bottom", p.M, 0)


@glyph("oe", 0x153)
def oe(g, p):
    S = p.S * 0.8
    H = p.H * 0.8
    pen = Pen(S, H)
    L, R = p.L - p.S * 0.25, p.R + p.S * 0.25
    xm = (L + R) / 2
    oval(g, p, L, xm + S / 2, ybot(p), ytop(p), sx=S, sy=H)
    yb, yt = ybot(p) + H / 2, ytop(p) - H / 2
    xr = R - S / 2
    cx = (xm + xr) / 2
    ry = (xr - xm) / 2
    ybar = p.XH * 0.5
    g.rect(xm, ybar - H / 2, R, ybar + H / 2)
    path = Path((xr, ybar - H / 2)).L((xr, yt - ry)).vh((cx, yt)).hv((xm, yt - ry))
    g.stroke(path, pen=pen)
    path = Path((xm, p.XH * 0.3)).vh((cx, yb)).hv((xr, p.XH * 0.2))
    g.stroke(path, pen=pen)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("OE", 0x152)
def OE(g, p):
    S = p.S * 0.85
    H = p.H * 0.85
    L, R = p.L - p.S * 0.2, p.R + p.S * 0.1
    xm = p.M + S * 0.15
    oval(g, p, L, xm + S / 2, -p.OV, p.CAP + p.OV, sx=S, sy=H)
    hbar(g, p, xm, R, p.CAP - p.Hb * 0.425, sy=p.Hb * 0.85)
    hbar(g, p, xm, R - S * 0.3, p.CAP * 0.52, sy=p.Hb * 0.85)
    hbar(g, p, xm, R, p.Hb * 0.425, sy=p.Hb * 0.85)
    vstem(g, p, xm, 0, p.CAP, sx=S)
    g.anchor("top", p.M, p.CAP).anchor("bottom", p.M, 0)


@glyph("eng", 0x14B)
def eng(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.XH)
    xr = p.R - S / 2
    yb = p.DESC + H / 2
    r = (0 - yb) * 0.55
    path = Path((xr, p.XH * 0.5)).L((xr, yb + r)).vh((xr - r * 0.9, yb)).L((p.M - S * 0.3, yb))
    g.stroke(path, end="butt")
    arch(g, p, xs, p.R, arch_top(p), p.XH * 0.45, junction(p))
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("Eng", 0x14A)
def Eng(g, p):
    S, H = p.S, p.H
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.CAP)
    xr = p.R - S / 2
    yb = p.DESC * 0.8 + H / 2
    r = (0 - yb) * 0.55
    arch(g, p, xs, p.R, p.CAP + p.OV * 0.7, p.CAP * 0.45, p.CAP * 0.6)
    path = Path((xr, p.CAP * 0.5)).L((xr, yb + r)).vh((xr - r * 0.9, yb)).L((p.M - S * 0.3, yb))
    g.stroke(path, end="butt")
    g.anchor("top", p.M, p.CAP).anchor("bottom", p.M, 0)


@glyph("kgreenlandic", 0x138)
def kgreenlandic(g, p):
    from .greek import kappa

    kappa(g, p)


@glyph("longs", 0x17F)
def longs(g, p):
    S, H = p.S, p.H
    xc = p.M - S * 0.3
    yt = p.ASC + p.OV * 0.5 - H / 2
    rf = (p.ASC - p.XH) * 0.62
    xr = p.R - S * 0.2
    xm = xc + (xr - xc) * 0.5
    path = Path((xc, 0)).L((xc, yt - rf)).vh((xm, yt)).hv((xr, yt - rf * 0.45 - S * 0.15))
    g.stroke(path)
    g.anchor("top", xc, p.ASC).anchor("bottom", xc, 0)


@glyph("florin", 0x192)
def florin(g, p):
    S, H = p.S, p.H
    xc = p.M
    yt = p.ASC + p.OV * 0.5 - H / 2
    yb = p.DESC - p.OV * 0.5 + H / 2
    rf = (p.ASC - p.XH) * 0.6
    xr, xl = p.R - S * 0.1, p.L + S * 0.1
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


@glyph("ldot", 0x140)
def ldot(g, p):
    draw(g, p, "l")
    dot(g, p, p.R - p.S * 0.15, p.XH * 0.55, d=min(p.S * 1.18 + 16, (p.R - p.L) * 0.3))


@glyph("Ldot", 0x13F)
def Ldot(g, p):
    draw(g, p, "L")
    dot(g, p, p.R - p.S * 0.5, p.CAP * 0.5, d=min(p.S * 1.18 + 16, (p.R - p.L) * 0.3))


@glyph("napostrophe", 0x149)
def napostrophe(g, p):
    from .marks import comma_shape

    q = derive(p, 0.82, 1.0, 0.92, cx=p.M + p.S * 0.5)
    t = Glyph("tmp", q)
    REGISTRY["n"].fn(t, q)
    g.add(t.contours)
    comma_shape(g, p, p.L + p.S * 0.1, p.CAP + 20, size=0.85)


@glyph("ij", 0x133)
def ij(g, p):
    S = p.S * 0.85
    from .latin_lower import i_dot_y

    xl = p.L + S
    xr = p.R - S
    vstem(g, p, xl, 0, p.XH, sx=S)
    dot(g, p, xl, i_dot_y(p))
    yb = p.DESC + p.H / 2
    r = (0 - yb) * 0.5
    path = Path((xr, p.XH)).L((xr, yb + r)).vh((xr - r, yb)).L((p.M - S * 0.2, yb))
    g.stroke(path, pen=Pen(S, p.H * 0.9))
    dot(g, p, xr, i_dot_y(p))


@glyph("IJ", 0x132)
def IJ(g, p):
    S = p.S * 0.9
    xl = p.L + S / 2
    vstem(g, p, xl, 0, p.CAP, sx=S)
    xr = p.R - S / 2
    yb = -p.OV + p.H / 2
    r = (xr - p.M) * 0.8
    path = Path((xr, p.CAP)).L((xr, yb + r)).vh((xr - r, yb)).hv((p.M - S * 0.3, yb + r * 0.7))
    g.stroke(path, pen=Pen(S, p.H * 0.9))


# ------------------------------------------------------------------ turned / mirrored
for _n, _u, _s, _c, _m in [
    ("uni0250", 0x250, "a", "x", False), ("uni0254", 0x254, "c", "x", True), ("schwa", 0x259, "e", "x", False),
    ("uni01DD", 0x1DD, "e", "x", False), ("uni0258", 0x258, "e", "x", True), ("uni0265", 0x265, "h", "x", False),
    ("uni026F", 0x26F, "m", "x", False), ("uni0279", 0x279, "r", "x", False), ("uni0287", 0x287, "t", "x", False),
    ("uni028C", 0x28C, "v", "x", False), ("uni028D", 0x28D, "w", "x", False), ("uni028E", 0x28E, "y", "x", False),
    ("uni029E", 0x29E, "k", "x", False), ("uni018E", 0x18E, "E", "cap", True), ("uni0186", 0x186, "C", "cap", True),
    ("uni2C6F", 0x2C6F, "A", "cap", False), ("uni0245", 0x245, "V", "cap", False), ("uni025C", 0x25C, "epsilon", "x", True),
    ("uni0252", 0x252, "uni0251", "x", False), ("uni0270", 0x270, "uni0271.base", "x", False),
    ("uni025F", 0x25F, "f", "x", False), ("uni01A7", 0x1A7, "S", "cap", True),
    ("uni01A8", 0x1A8, "s", "x", True), ("uni2C6D", 0x2C6D, "uni0251", "x", False), ("uni0296", 0x296, "uni0294", "cap", False),
    ("uni2132", 0x2132, "F", "cap", False), ("uni214E", 0x214E, "F.small", "x", False),
]:
    turned(_n, _u, _s, _c, _m)

for _n, _u, _s in [
    ("uni0262", 0x262, "G"), ("uni026A", 0x26A, "I"), ("uni0280", 0x280, "R"), ("uni028F", 0x28F, "Y"),
    ("uni0299", 0x299, "B"), ("uni029C", 0x29C, "H"), ("uni029F", 0x29F, "L"), ("uni0274", 0x274, "N"),
    ("uni0276", 0x276, "OE"), ("uni1D00", 0x1D00, "A"), ("uni1D04", 0x1D04, "C"), ("uni1D05", 0x1D05, "D"),
    ("uni1D07", 0x1D07, "E"), ("uni1D0A", 0x1D0A, "J"), ("uni1D0B", 0x1D0B, "K"), ("uni1D0D", 0x1D0D, "M"),
    ("uni1D0F", 0x1D0F, "O"), ("uni1D18", 0x1D18, "P"), ("uni1D1B", 0x1D1B, "T"), ("uni1D1C", 0x1D1C, "U"),
    ("uni1D20", 0x1D20, "V"), ("uni1D21", 0x1D21, "W"), ("uni1D22", 0x1D22, "Z"), ("uni A73A", None, "F"),
    ("F.small", None, "F"),
]:
    if " " in _n:
        continue
    smallcap(_n, _u, _s)


@glyph("uni0281", 0x281)
def smallcapRinv(g, p):
    t = drawn(p, "uni0280")
    XH = p.XH
    t.transform(lambda q: (q[0], XH - q[1]), flip=True)
    g.add(t.contours)


# ------------------------------------------------------------------ IPA proper
@glyph("uni0251", 0x251)
def alpha_latin(g, p):
    S = p.S
    xs = p.R - S / 2
    vstem(g, p, xs, 0, p.XH)
    bowl_side(g, p, xs, p.L, ybot(p), ytop(p))
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)


@glyph("uni0271.base")
def _m_hook_base(g, p):
    draw(g, p, "m")


@glyph("uni0271", 0x271)
def mhook(g, p):
    draw(g, p, "m")
    hook_below(g, p, p.R - min(p.S, (p.R - p.L) * 0.255) / 2 + p.S * 0.12)


def hook_below(g, p, x, left=True):
    """Descending hook (ɱ ɲ ŋ-like) from a stem bottom at x."""
    S, H = p.S, p.H
    yb = p.DESC + H / 2
    r = (0 - yb) * 0.5
    d = -1 if left else 1
    path = Path((x, 10)).L((x, yb + r)).vh((x + d * r * 0.9, yb)).L((x + d * r * 1.4, yb))
    g.stroke(path, end="butt")


def retroflex(g, p, x):
    """Retroflex hook: stem continues below the baseline curling right."""
    S, H = p.S, p.H
    yb = p.DESC * 0.8 + H / 2
    r = (0 - yb) * 0.45
    path = Path((x, 10)).L((x, yb + r)).vh((x + r * 0.9, yb)).L((x + r * 1.5, yb))
    g.stroke(path, end="butt")


def hook_top(g, p, x, top):
    """Top hook (ɓ ɗ ɠ ƙ): stem top curling right."""
    S, H = p.S, p.H
    yt = top + p.OV * 0.5 - H / 2
    r = (p.ASC - p.XH) * 0.55
    path = Path((x, top - r - 10)).L((x, yt - r)).vh((x + r * 0.9, yt)).L((x + r * 1.5, yt - 20))
    g.stroke(path, end="butt")


@glyph("uni0272", 0x272)
def nhookleft(g, p):
    from .latin_lower import n

    n(g, p)
    hook_below(g, p, p.L + p.S / 2)


@glyph("uni0273", 0x273)
def nretroflex(g, p):
    from .latin_lower import n

    n(g, p)
    retroflex(g, p, p.R - p.S / 2)


@glyph("uni026D", 0x26D)
def lretroflex(g, p):
    S = p.S
    xc = p.M
    vstem(g, p, xc, 0, p.ASC)
    serif_head(g, p, xc, p.ASC, length=(xc - S / 2) - (p.L + S * 0.25), sans=True)
    retroflex(g, p, xc)


@glyph("uni0288", 0x288)
def tretroflex(g, p):
    S = p.S
    xc = p.M - S * 0.35
    top = p.XH + (p.ASC - p.XH) * 0.55
    g.stroke(Path((xc, top)).L((xc, 0)), start=25)
    hbar(g, p, p.L + S * 0.1, p.R - S * 0.35, p.XH - p.Hb / 2)
    retroflex(g, p, xc)


@glyph("uni0256", 0x256)
def dretroflex(g, p):
    S = p.S
    xs = p.R - S / 2
    vstem(g, p, xs, 0, p.ASC)
    bowl_side(g, p, xs, p.L, ybot(p), ytop(p))
    retroflex(g, p, xs)


@glyph("uni0282", 0x282)
def sretroflex(g, p):
    draw(g, p, "s")
    retroflex(g, p, p.L + p.S * 0.7)


@glyph("uni0290", 0x290)
def zretroflex(g, p):
    draw(g, p, "z")
    retroflex(g, p, p.R - p.S * 0.7)


@glyph("uni027D", 0x27D)
def rretroflex(g, p):
    draw(g, p, "r")
    retroflex(g, p, p.L + p.S / 2 + (p.R - p.L) * 0.1)


@glyph("uni0253", 0x253)
def bhook(g, p):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.ASC * 0.8)
    bowl_side(g, p, xs, p.R, ybot(p), ytop(p))
    hook_top(g, p, xs, p.ASC)


@glyph("uni0257", 0x257)
def dhook(g, p):
    S = p.S
    xs = p.R - S / 2 - S * 0.4
    vstem(g, p, xs, 0, p.ASC * 0.8)
    bowl_side(g, p, xs, p.L, ybot(p), ytop(p))
    hook_top(g, p, xs, p.ASC)


@glyph("uni0260", 0x260)
def ghook(g, p):
    draw(g, p, "g")
    hook_top(g, p, p.R - p.S / 2, p.XH + (p.ASC - p.XH) * 0.7)


@glyph("uni0199", 0x199)
def khook(g, p):
    draw(g, p, "k")
    hook_top(g, p, p.L + p.S / 2, p.ASC)


@glyph("uni0266", 0x266)
def hhook(g, p):
    from .latin_lower import n_body

    n_body(g, p, p.ASC * 0.8)
    hook_top(g, p, p.L + p.S / 2, p.ASC)


@glyph("uni0267", 0x267)
def henghook(g, p):
    from .latin_lower import n_body

    n_body(g, p, p.ASC * 0.8)
    hook_top(g, p, p.L + p.S / 2, p.ASC)
    hook_below(g, p, p.R - p.S / 2)


@glyph("uni0284", 0x284)
def jbarhook(g, p):
    draw(g, p, "uni025F")
    hook_top(g, p, p.M + p.S * 0.3, p.ASC)


@glyph("uni0255", 0x255)
def ccurl(g, p):
    S = p.S
    te = p.XH * 0.73
    c_shape(g, p, p.L, p.R - S * 0.05, ybot(p), ytop(p), te, p.XH * 0.35)
    r = (p.R - p.L) * 0.14
    g.stroke(Path((p.R - S * 0.7, p.XH * 0.3)).vh((p.M + r, 0)).hv((p.M, r * 1.2)), pen=Pen(S * 0.8, p.H * 0.8))


@glyph("uni0291", 0x291)
def zcurl(g, p):
    draw(g, p, "z")


@glyph("uni0263", 0x263)
def gammalatin(g, p):
    from .greek import gamma

    gamma(g, p)


@glyph("uni0264", 0x264)
def ramshorn(g, p):
    a, b = diag_between(p, p.L, p.XH, p.M, p.S * 0.2, 1, 0)
    diag(g, p, a, (p.M, p.S * 0.2), end="butt")
    c, d = diag_between(p, p.R, p.XH, p.M, p.S * 0.2, -1, 0)
    diag(g, p, c, (p.M, p.S * 0.2), end="butt")
    r = (p.R - p.L) * 0.2
    pen = Pen(p.S * 0.85, p.H * 0.85)
    g.stroke(Path((p.M, p.S * 0.2)).C((p.M - r * 1.4, p.DESC * 0.3), (p.M - r, p.DESC), (p.M, p.DESC * 0.95))
             .C((p.M + r, p.DESC), (p.M + r * 1.4, p.DESC * 0.3), (p.M, p.S * 0.2)), pen=pen)


@glyph("uni025B", 0x25B)
def epsilonlatin(g, p):
    from .greek import epsilon

    epsilon(g, p)


@glyph("uni0278", 0x278)
def philatin(g, p):
    from .greek import phi_body

    phi_body(g, p, ybot(p), ytop(p), p.DESC, p.ASC, x0=p.L, x1=p.R)


@glyph("esh", 0x283)
def esh(g, p):
    S, H = p.S, p.H
    xc = p.M
    yt = p.ASC + p.OV * 0.5 - H / 2
    yb = p.DESC - p.OV * 0.5 + H / 2
    rf = (p.ASC - p.XH) * 0.6
    xr, xl = p.R - S * 0.1, p.L + S * 0.1
    path = (
        Path((xl, yb + rf * 0.45 + S * 0.15))
        .vh((xc - (xc - xl) * 0.5, yb))
        .hv((xc, yb + rf))
        .L((xc, yt - rf))
        .vh((xc + (xr - xc) * 0.5, yt))
        .hv((xr, yt - rf * 0.45 - S * 0.15))
    )
    g.stroke(path)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, p.DESC)


@glyph("Esh", 0x1A9)
def Esh(g, p):
    from .greek import Sigma

    Sigma(g, p)


@glyph("ezh", 0x292)
def ezh(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    x0, x1 = p.L + S * 0.2, p.R - S * 0.2
    hbar(g, p, x0, x1, p.XH - Hb / 2)
    ym = p.XH * 0.42
    a, b = diag_between(p, x1, p.XH - Hb / 2, p.M - S * 0.2, ym, -1, 0)
    g.stroke(Path(a).L(b), start=0, end="butt")
    xr = p.R - S / 2
    yb = p.DESC * 0.95 + H / 2
    cx = p.M
    r = (ym - yb) / 2
    path = Path((p.M - S * 0.2, ym)).L((cx, ym)).hv((xr, ym - r)).vh((cx, yb)).hv((p.L + S / 2, yb + r * 0.6))
    g.stroke(path)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("Ezh", 0x1B7)
def Ezh(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    x0, x1 = p.L + S * 0.1, p.R - S * 0.1
    hbar(g, p, x0, x1, p.CAP - Hb / 2)
    ym = p.CAP * 0.5
    a, b = diag_between(p, x1, p.CAP - Hb / 2, p.M - S * 0.2, ym, -1, 0)
    g.stroke(Path(a).L(b), start=0, end="butt")
    xr = p.R - S / 2
    yb = -p.OV + H / 2
    cx = p.M
    r = (ym - yb) / 2
    path = Path((p.M - S * 0.2, ym)).L((cx, ym)).hv((xr, ym - r)).vh((cx, yb)).hv((p.L + S / 2, yb + r * 0.6))
    g.stroke(path)


@glyph("uni0294", 0x294)
def glottalstop(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2 + S * 0.2, p.R - S / 2 - S * 0.2
    yt = p.ASC + p.OV - H / 2
    cx = (xl + xr) / 2
    r = (xr - xl) / 2
    path = Path((xl, yt - r * 0.85)).vh((cx, yt)).hv((xr, yt - r)).C((xr, yt - r * 1.7), (p.M, p.XH * 0.6), (p.M, p.XH * 0.4)).L((p.M, 0))
    g.stroke(path)


@glyph("uni0295", 0x295)
def pharyngeal(g, p):
    t = drawn(p, "uni0294")
    t.mirror_x()
    g.add(t.contours)


@glyph("uni02A1", 0x2A1)
def glottalstopbar(g, p):
    draw(g, p, "uni0294")
    hbar(g, p, p.M - (p.R - p.L) * 0.25, p.M + (p.R - p.L) * 0.25, p.XH * 0.3, sy=p.Hb * 0.85)


@glyph("uni028A", 0x28A)
def upsilonlatin(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yb = ybot(p) + H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.XH / 2, f=1.1)
    path = Path((p.L - S * 0.1, p.XH - H / 2)).L((xl + S * 0.2, p.XH - H / 2)).C((xl, p.XH * 0.8), (xl, p.XH * 0.6), (xl, yb + r))
    path.vh((cx, yb)).hv((xr, yb + r)).C((xr, p.XH * 0.6), (xr, p.XH * 0.8), (xr - S * 0.2, p.XH - H / 2)).L((p.R + S * 0.1, p.XH - H / 2))
    g.stroke(path)


@glyph("uni028B", 0x28B)
def vhook(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yb = ybot(p) + H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.XH / 2, f=1.1)
    path = Path((xl, p.XH)).L((xl, yb + r)).vh((cx, yb)).hv((xr, yb + r)).L((xr, p.XH - r * 0.6)).vh((xr - r * 0.5, p.XH + p.OV - H / 2))
    g.stroke(path)


@glyph("uni027E", 0x27E)
def fishhookr(g, p):
    S, H = p.S, p.H
    xs = p.M - S * 0.3
    yt = arch_top(p) - H / 2
    r = (p.R - xs) * 0.45
    path = Path((xs, 0)).L((xs, yt - r)).vh((xs + r, yt)).hv((p.R - S * 0.2, yt - r * 0.6))
    g.stroke(path, start=0)


@glyph("uni0298", 0x298)
def bilabialclick(g, p):
    draw(g, p, "O")
    dot(g, p, p.M, p.CAP / 2, d=min(p.S * 1.3 + 14, (p.R - p.L) * 0.3))


@glyph("uni01C0", 0x1C0)
def dentalclick(g, p):
    vstem(g, p, p.M, p.DESC * 0.8, p.ASC)


@glyph("uni01C1", 0x1C1)
def lateralclick(g, p):
    o = (p.R - p.L) * 0.17
    vstem(g, p, p.M - o, p.DESC * 0.8, p.ASC)
    vstem(g, p, p.M + o, p.DESC * 0.8, p.ASC)


@glyph("uni01C2", 0x1C2)
def alveolarclick(g, p):
    vstem(g, p, p.M, p.DESC * 0.8, p.ASC)
    hw = (p.R - p.L) * 0.33
    hbar(g, p, p.M - hw, p.M + hw, p.XH * 0.65)
    hbar(g, p, p.M - hw, p.M + hw, p.XH * 0.35)


@glyph("uni01C3", 0x1C3)
def retroflexclick(g, p):
    from .punct import exclam

    exclam(g, p)


@glyph("uni026B", 0x26B)
def lmiddletilde(g, p):
    draw(g, p, "l")
    from .marks import Z, tilde_shape

    z = Z(p, p.XH * 0.4, 120, p.M)
    tilde_shape(g, p, z, hw=(p.R - p.L) * 0.42, ym=p.XH * 0.55, amp=40)


@glyph("uni026C", 0x26C)
def lbelt(g, p):
    draw(g, p, "l")
    S = p.S
    xc = p.M - (p.R - p.L) * 0.07
    y = p.XH * 0.55
    r = (p.R - p.L) * 0.17
    g.stroke(Path((xc, y + r * 0.6)).L((xc - r * 0.6, y + r * 0.6)).hv((xc - r * 1.1, y)).vh((xc, y - r * 0.6)).L((xc + r * 1.4, y - r * 0.6)),
             pen=Pen(S * 0.75, p.H * 0.75))


@glyph("uni026E", 0x26E)
def lezh(g, p):
    S = p.S
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.ASC)
    t = drawn(derive(p, 0.62, 1.0, 0.85, cx=p.M + (p.R - p.L) * 0.18), "ezh")
    g.add(t.contours)


@glyph("uni02A4", 0x2A4)
def dezh(g, p):
    q = derive(p, 0.6, 1.0, 0.8, cx=p.L + (p.R - p.L) * 0.28)
    g.add(drawn(q, "d").contours)
    q2 = derive(p, 0.6, 1.0, 0.8, cx=p.R - (p.R - p.L) * 0.26)
    g.add(drawn(q2, "ezh").contours)


def digraph(name, uni, a, b, fx=0.56, wf=0.8):
    def fn(g, p):
        q1 = derive(p, fx, 1.0, wf, cx=p.L + (p.R - p.L) * 0.27)
        q2 = derive(p, fx, 1.0, wf, cx=p.R - (p.R - p.L) * 0.27)
        g.add(drawn(q1, a).contours)
        g.add(drawn(q2, b).contours)

    register(name, fn, uni)


for _n, _u, _a, _b in [
    ("uni02A3", 0x2A3, "d", "z"), ("uni02A6", 0x2A6, "t", "s"), ("uni02A7", 0x2A7, "t", "esh"),
    ("uni02A8", 0x2A8, "t", "uni0255"), ("uni02A5", 0x2A5, "d", "uni0291"), ("uni02AA", 0x2AA, "l", "s"),
    ("uni02AB", 0x2AB, "l", "z"), ("uni01C7", 0x1C7, "L", "J"), ("uni01C8", 0x1C8, "L", "j"),
    ("uni01C9", 0x1C9, "l", "j"), ("uni01CA", 0x1CA, "N", "J"), ("uni01CB", 0x1CB, "N", "j"),
    ("uni01CC", 0x1CC, "n", "j"), ("uni01F1", 0x1F1, "D", "Z"), ("uni01F2", 0x1F2, "D", "z"),
    ("uni01F3", 0x1F3, "d", "z"), ("uniFB00", 0xFB00, "f", "f"), ("uniFB01", 0xFB01, "f", "i"),
    ("uniFB02", 0xFB02, "f", "l"), ("uniFB06", 0xFB06, "s", "t"), ("uni1D6B", 0x1D6B, "u", "e"),
    ("uniAB63", 0xAB63, "u", "o"),
]:
    digraph(_n, _u, _a, _b)


@glyph("uni0261", 0x261)
def scriptg(g, p):
    g.compose = ["g"]


@glyph("uni0269", 0x269)
def iotalatin(g, p):
    g.compose = ["iota"]


@glyph("uni029D", 0x29D)
def jcrossedtail(g, p):
    draw(g, p, "j")
    S = p.S
    xc = p.M + S * 0.6
    y = p.DESC * 0.55
    r = (p.R - p.L) * 0.14
    pen = Pen(S * 0.75, p.H * 0.75)
    g.stroke(Path((xc - r * 2.2, y - r * 0.6)).L((xc + r * 0.4, y - r * 0.6)).hv((xc + r * 1.2, y)).vh((xc + r * 0.2, y + r * 0.6)), pen=pen)
