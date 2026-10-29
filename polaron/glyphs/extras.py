"""Gap fillers: more Cyrillic, Greek symbol variants, General Punctuation."""

from __future__ import annotations

import math

from ..glyph import REGISTRY, Glyph, glyph, register
from ..stroke import Path, Pen
from .latin_lower import diag_between, ybot, ytop
from .parts import arc_h, dot, hbar, oval, vstem
from .punct import pdot, pdot_d, question_body, exclam
from .scaled import derive


def drawn(p, name, q=None):
    t = Glyph("tmp", q or p)
    t.adv = p.W
    REGISTRY[name].fn(t, q or p)
    return t


def put(g, p, name, q=None):
    t = drawn(p, name, q)
    g.add(t.contours)
    for k, v in t.anchors.items():
        g.anchors.setdefault(k, v)
    return t


def ref(name, uni, base):
    def fn(g, p):
        g.compose = [base]

    register(name, fn, uni)


def tail_right(g, p, top):
    """Descender tail at the right edge (Ҙ Ҫ Ҭ …)."""
    S = p.S
    x = p.R + S * 0.25
    g.rect(x - S * 0.9, -min(170, -p.DESC * 0.75), x, p.Hb)


def tail_center(g, p, x):
    S = p.S
    g.rect(x - S * 0.45, -min(170, -p.DESC * 0.75), x + S * 0.45, 2)


def with_extra(name, uni, base, extra):
    def fn(g, p):
        put(g, p, base)
        extra(g, p)

    register(name, fn, uni)


# ------------------------------------------------------------------ Cyrillic
for _n, _u, _b in [("uni0472", 0x472, "uni04E8"), ("uni0473", 0x473, "uni04E9"), ("uni0474", 0x474, "V"),
                   ("uni0475", 0x475, "v"), ("uni051A", 0x51A, "Q"), ("uni051B", 0x51B, "q"),
                   ("uni051C", 0x51C, "W"), ("uni051D", 0x51D, "w"), ("uni04C0.alt", None, "I"),
                   ("uni0500", 0x500, "d")]:
    if _u is not None:
        ref(_n, _u, _b)

with_extra("uni0498", 0x498, "uni0417", lambda g, p: tail_center(g, p, p.M))
with_extra("uni0499", 0x499, "uni0437", lambda g, p: tail_center(g, p, p.M))
with_extra("uni04AA", 0x4AA, "C", lambda g, p: tail_center(g, p, p.M))
with_extra("uni04AB", 0x4AB, "c", lambda g, p: tail_center(g, p, p.M))
with_extra("uni04AC", 0x4AC, "T", lambda g, p: tail_center(g, p, p.M + p.S * 0.9))
with_extra("uni04AD", 0x4AD, "uni0442", lambda g, p: tail_center(g, p, p.M + p.S * 0.9))
with_extra("uni04C3", 0x4C3, "K", lambda g, p: hook_desc(g, p, p.R - p.S / 2, p.CAP * 0.3))
with_extra("uni04C4", 0x4C4, "uni043A", lambda g, p: hook_desc(g, p, p.R - p.S / 2, p.XH * 0.3))
with_extra("uni04C7", 0x4C7, "H", lambda g, p: hook_desc(g, p, p.R - p.S / 2, 0))
with_extra("uni04C8", 0x4C8, "uni043D", lambda g, p: hook_desc(g, p, p.R - p.S / 2, 0))
with_extra("uni04C5", 0x4C5, "uni041B", lambda g, p: tail_right(g, p, p.CAP))
with_extra("uni04C6", 0x4C6, "uni043B", lambda g, p: tail_right(g, p, p.XH))
with_extra("uni04CD", 0x4CD, "M", lambda g, p: tail_right(g, p, p.CAP))
with_extra("uni04CE", 0x4CE, "uni043C", lambda g, p: tail_right(g, p, p.XH))
with_extra("uni04C9", 0x4C9, "H", lambda g, p: tail_right(g, p, p.CAP))
with_extra("uni04CA", 0x4CA, "uni043D", lambda g, p: tail_right(g, p, p.XH))
with_extra("uni04CB", 0x4CB, "uni0427", lambda g, p: tail_center(g, p, p.L + p.S / 2))
with_extra("uni04CC", 0x4CC, "uni0447", lambda g, p: tail_center(g, p, p.L + p.S / 2))


def hook_desc(g, p, x, y0):
    S, H = p.S, p.H
    yb = p.DESC * 0.85 + H / 2
    r = (0 - yb) * 0.55
    path = Path((x, max(y0, 10))).L((x, yb + r)).vh((x - r * 0.9, yb)).L((x - r * 1.5, yb))
    g.stroke(path, end="butt")


def ka_bashkir(g, p, top):
    """Ҡ ҡ: K with a bar instead of a stem top (Bashkir ka)."""
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + (p.R - p.L) * 0.12
    vstem(g, p, xs, 0, top)
    hbar(g, p, p.L - S * 0.1, xs, top - Hb / 2)
    a, b = diag_between(p, p.R - S * 0.05, top, xs, top * 0.3, -1, 0, w=0.95)
    g.stroke(Path(a, 0.95).L(b, 0.95), start=0, end="butt")
    m = (a[0] + (b[0] - a[0]) * 0.5, a[1] + (b[1] - a[1]) * 0.5)
    c, d = diag_between(p, m[0], m[1], p.R, 0, 0, -1)
    g.stroke(Path(c).L(d), start="butt", end=0)


register("uni04A0", lambda g, p: ka_bashkir(g, p, p.CAP), 0x4A0)
register("uni04A1", lambda g, p: ka_bashkir(g, p, p.XH), 0x4A1)


def ka_vert(g, p, top):
    """Ҝ ҝ: K with a vertical stroke through the arm."""
    put(g, p, "K" if top == p.CAP else "uni043A")
    vstem(g, p, p.L + (p.R - p.L) * 0.42, top * 0.3, top * 0.72, sx=p.S * 0.7)


register("uni049C", lambda g, p: ka_vert(g, p, p.CAP), 0x49C)
register("uni049D", lambda g, p: ka_vert(g, p, p.XH), 0x49D)


def ghe_hook(g, p, top):
    """Ҕ ҕ: Ghe with a middle hook."""
    from .greek import gamma_body

    gamma_body(g, p, top)
    S, H = p.S, p.H
    xs = p.L + S / 2 + S * 0.25
    ym = top * 0.52
    r = (ym - (p.DESC * 0.6)) * 0.5
    path = Path((xs, ym)).L((p.M, ym)).hv((p.R - S / 2, ym - r)).L((p.R - S / 2, p.DESC * 0.25)).vh((p.M + S * 0.2, p.DESC * 0.7))
    g.stroke(path, end="butt")


register("uni0494", lambda g, p: ghe_hook(g, p, p.CAP), 0x494)
register("uni0495", lambda g, p: ghe_hook(g, p, p.XH), 0x495)


def en_ghe(g, p, top, lower):
    """Ҥ ҥ: En + ghe ligature."""
    S = p.S * 0.85
    L, R = p.L - p.S * 0.15, p.R + p.S * 0.15
    xl = L + S / 2
    xm = L + (R - L) * 0.6
    vstem(g, p, xl, 0, top, sx=S)
    vstem(g, p, xm, 0, top, sx=S)
    hbar(g, p, xl, xm, top * 0.5, sy=p.Hb * 0.9)
    hbar(g, p, xm, R, top - p.Hb * 0.45, sy=p.Hb * 0.9)


register("uni04A4", lambda g, p: en_ghe(g, p, p.CAP, False), 0x4A4)
register("uni04A5", lambda g, p: en_ghe(g, p, p.XH, True), 0x4A5)


def big_yus(g, p, top):
    """Ѫ ѫ: big yus."""
    S = p.S * 0.85
    pen = Pen(S, p.H * 0.85)
    L, R = p.L - p.S * 0.1, p.R + p.S * 0.1
    ym = top * 0.48
    g.stroke(Path((L + S * 0.5, top - p.Hb * 0.45)).L((R - S * 0.5, top - p.Hb * 0.45)).L((p.M, ym)).close(), pen=pen)
    vstem(g, p, p.M, 0, ym, sx=S)
    for side in (-1, 1):
        g.stroke(Path((p.M, ym)).L((p.M + side * (R - L) * 0.42, 0)), pen=pen, start="butt", end=0)


register("uni046A", lambda g, p: big_yus(g, p, p.CAP), 0x46A)
register("uni046B", lambda g, p: big_yus(g, p, p.XH), 0x46B)


def omega_cyr(g, p, top):
    """Ѡ ѡ: Cyrillic omega (w-like with round bottoms)."""
    from .greek import omega_body

    q = derive(p, 1.0, top / p.XH, 1.0)
    q.XH = top
    t = Glyph("tmp", q)
    omega_body(t, q)
    g.add(t.contours)


register("uni0460", lambda g, p: omega_cyr(g, p, p.CAP), 0x460)
register("uni0461", lambda g, p: omega_cyr(g, p, p.XH), 0x461)


# ------------------------------------------------------------------ Greek symbol variants
ref("uni03F4", 0x3F4, "uni04E8")  # ϴ capital theta symbol


@glyph("uni03D0", 0x3D0)
def betasymbol(g, p):
    """ϐ curled beta: an open loop rising from the baseline."""
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yb = ybot(p) + H / 2
    yt = p.ASC + p.OV - H / 2
    cx = (xl + xr) / 2
    ym = p.XH * 0.75
    r = (xr - xl) / 2
    path = (
        Path((xl, ym))
        .L((xl, yt - r))
        .vh((cx, yt))
        .hv((xr - S * 0.15, yt - r))
        .vh((cx, ym))
        .L((xl + S * 0.4, ym))
    )
    g.stroke(path)
    rl = (ym - yb) / 2
    path = Path((xl + S * 0.4, ym)).L((cx, ym)).hv((xr, ym - rl)).vh((cx, yb)).hv((xl, ym - rl * 0.4))
    g.stroke(path)


@glyph("uni03D2", 0x3D2)
def upsilonhook(g, p):
    """ϒ: Upsilon with hooked arms."""
    S, H = p.S, p.H
    ym = p.CAP * 0.5
    vstem(g, p, p.M, 0, ym + 20)
    for side in (-1, 1):
        x0 = p.M + side * ((p.R - p.L) / 2 - S / 2)
        path = Path((p.M, ym)).C((p.M, p.CAP * 0.8), (p.M + side * S * 0.6, p.CAP - H / 2), (p.M + side * (p.R - p.L) * 0.28, p.CAP - H / 2))
        path.C((x0, p.CAP - H / 2), (x0 + side * S * 0.1, p.CAP * 0.88), (x0 + side * S * 0.1, p.CAP * 0.82))
        g.stroke(path, start="butt", end="butt")


ref("uni03DA", 0x3DA, "C")  # Ϛ stigma (approximation)


@glyph("uni03DB", 0x3DB)
def stigma(g, p):
    from .greek import finalsigma

    finalsigma(g, p)
    hbar(g, p, p.M, p.R + p.S * 0.1, p.XH - p.Hb / 2)


@glyph("uni03DE", 0x3DE)
def Koppa(g, p):
    S = p.S
    a, b = diag_between(p, p.L + S * 0.2, p.CAP, p.R - S * 0.2, 0, 1, -1)
    g.stroke(Path(a).L(b), start=0, end=0)
    hbar(g, p, p.L, p.M, p.CAP - p.Hb / 2)


@glyph("uni03DF", 0x3DF)
def koppa(g, p):
    S = p.S
    a, b = diag_between(p, p.M + S * 0.2, p.ASC, p.M - S * 0.2, 0, 0, 0)
    g.stroke(Path(a).L(b), start=0, end=0)
    a, b = diag_between(p, p.M - S * 0.1, p.XH * 0.6, p.R - S * 0.1, 0, 0, -1)
    g.stroke(Path(a).L(b), start="butt", end=0)


@glyph("uni03E0", 0x3E0)
def Sampi(g, p):
    S = p.S
    a, b = diag_between(p, p.L + S * 0.1, p.CAP, p.R - S * 0.2, 0, 1, -1)
    g.stroke(Path(a).C((p.R, p.CAP * 0.8), (p.R, p.CAP * 0.4), b), start=0, end=0)
    for f in (0.42, 0.7):
        g.stroke(Path((p.M, p.CAP * f)).L((p.M + (p.R - p.L) * 0.4, p.CAP * (f - 0.2))), pen=Pen(S * 0.8, S * 0.8),
                 start="butt", end=0)


@glyph("uni03E1", 0x3E1)
def sampi(g, p):
    q = derive(p, 1.0, p.XH / p.CAP, 1.0)
    t = Glyph("tmp", q)
    Sampi(t, q)
    g.add(t.contours)


ref("uni03F7", 0x3F7, "Thorn")
ref("uni03F8", 0x3F8, "thorn")
ref("uni03FA", 0x3FA, "M")
ref("uni03FD", 0x3FD, "uni0186")
ref("uni03FE", 0x3FE, "uni0186")
ref("uni0370", 0x370, "uni2C75" if False else "H")
ref("uni0371", 0x371, "uni0371" if False else "h")
ref("uni037B", 0x37B, "uni0254")
ref("uni037C", 0x37C, "c")
ref("uni037D", 0x37D, "uni0254")


# ------------------------------------------------------------------ General Punctuation
@glyph("uni2047", 0x2047)
def dblquestion(g, p):
    for dx in (-0.22, 0.22):
        q = derive(p, 0.5, 1.0, 0.85, cx=p.M + (p.R - p.L) * dx)
        put(g, p, "question", q)


@glyph("uni2048", 0x2048)
def questionexclam(g, p):
    q = derive(p, 0.5, 1.0, 0.85, cx=p.M - (p.R - p.L) * 0.22)
    put(g, p, "question", q)
    q = derive(p, 0.5, 1.0, 0.85, cx=p.M + (p.R - p.L) * 0.25)
    put(g, p, "exclam", q)


@glyph("uni2049", 0x2049)
def exclamquestion(g, p):
    q = derive(p, 0.5, 1.0, 0.85, cx=p.M - (p.R - p.L) * 0.25)
    put(g, p, "exclam", q)
    q = derive(p, 0.5, 1.0, 0.85, cx=p.M + (p.R - p.L) * 0.22)
    put(g, p, "question", q)


def _asterisk_at(g, p, cx, cy, f):
    r = (p.R - p.L) * 0.4 * f
    pen = Pen(p.S * 0.9 * (0.6 + 0.4 * f), p.S * 0.9 * (0.6 + 0.4 * f))
    for ang in (90, 210, 330, 270, 30, 150):
        a = math.radians(ang)
        g.stroke(Path((cx, cy), 1.0).L((cx + r * math.cos(a), cy + r * math.sin(a)), 0.82), pen=pen)


@glyph("uni204E", 0x204E)
def lowasterisk(g, p):
    _asterisk_at(g, p, p.M, (p.R - p.L) * 0.2, 0.75)


@glyph("uni2051", 0x2051)
def twoasterisks(g, p):
    _asterisk_at(g, p, p.M, p.CAP * 0.78, 0.62)
    _asterisk_at(g, p, p.M, p.CAP * 0.28, 0.62)


@glyph("uni2042", 0x2042)
def asterism(g, p):
    _asterisk_at(g, p, p.M, p.CAP * 0.75, 0.5)
    _asterisk_at(g, p, p.M - (p.R - p.L) * 0.24, p.CAP * 0.33, 0.5)
    _asterisk_at(g, p, p.M + (p.R - p.L) * 0.24, p.CAP * 0.33, 0.5)


@glyph("uni2053", 0x2053)
def swungdash(g, p):
    from .punct import asciitilde

    asciitilde(g, p)


@glyph("uni2038", 0x2038)
def caretsym(g, p):
    hw = (p.R - p.L) * 0.32
    g.stroke(Path((p.M - hw, -150)).L((p.M, 30)).L((p.M + hw, -150)), pen=Pen(p.S * 0.85, p.S * 0.85))


@glyph("uni2052", 0x2052)
def commercialminus(g, p):
    a, b = diag_between(p, p.R, p.CAP, p.L, 0, -1, 1, w=0.8)
    g.stroke(Path(a, 0.8).L(b, 0.8), start=0, end=0)
    d = pdot_d(p) * 0.85
    dot(g, p, p.L + (p.R - p.L) * 0.22, p.CAP * 0.72, d=d, k=0.66)
    dot(g, p, p.R - (p.R - p.L) * 0.22, p.CAP * 0.28, d=d, k=0.66)


def dots(name, uni, pts):
    def fn(g, p):
        d = min(pdot_d(p), (p.R - p.L) * 0.3)
        for fx, fy in pts:
            dot(g, p, p.M + (p.R - p.L) * fx, d / 2 + (p.CAP - d) * fy, d=d, k=0.66)

    register(name, fn, uni)


dots("uni2056", 0x2056, [(-0.3, 0), (0.3, 0), (0, 0.32)])
dots("uni2058", 0x2058, [(0, 0.62), (-0.3, 0.31), (0.3, 0.31), (0, 0)])
dots("uni2059", 0x2059, [(-0.3, 0.62), (0.3, 0.62), (0, 0.31), (-0.3, 0), (0.3, 0)])
dots("uni205A", 0x205A, [(0, 0.62), (0, 0)])
dots("uni205B", 0x205B, [(0, 0.75), (-0.3, 0.37), (0.3, 0.37), (0, 0)])
dots("uni205C", 0x205C, [(0, 0.66), (0, 0.33), (-0.33, 0.33), (0.33, 0.33), (0, 0)])
dots("uni205D", 0x205D, [(0, 0.75), (0, 0.37), (0, 0)])
dots("uni205E", 0x205E, [(0, 0.9), (0, 0.6), (0, 0.3), (0, 0)])
dots("uni2E2A", 0x2E2A, [(-0.3, 0.6), (0.3, 0.6), (0, 0)])


def tie(name, uni, up, y):
    def fn(g, p):
        pen = Pen(p.S * 0.8, p.S * 0.8)
        hw = p.W * 0.62
        yy = y(p)
        if up:
            path = Path((p.M - hw, yy)).vh((p.M, yy + 70)).hv((p.M + hw, yy))
        else:
            path = Path((p.M - hw, yy)).vh((p.M, yy - 70)).hv((p.M + hw, yy))
        g.stroke(path, pen=pen)

    register(name, fn, uni)


tie("uni2040", 0x2040, True, lambda p: p.CAP + 40)
tie("uni203F", 0x203F, False, lambda p: -60)
tie("uni2054", 0x2054, True, lambda p: -150)
tie("uni2050", 0x2050, True, lambda p: p.CAP * 0.2)


@glyph("uni204F", 0x204F)
def revsemicolon(g, p):
    from .punct import semicolon

    semicolon(g, p)
    g.mirror_x()


@glyph("uni2045", 0x2045)
def quillbracketleft(g, p):
    put(g, p, "bracketleft")
    hbar(g, p, p.M - p.S * 0.4, p.M + (p.R - p.L) * 0.25, (p.BT + p.BB) / 2, sy=p.Hb * 0.85)


@glyph("uni2046", 0x2046)
def quillbracketright(g, p):
    quillbracketleft(g, p)
    g.mirror_x()


@glyph("uni204A", 0x204A)
def tironianet(g, p):
    hbar(g, p, p.L, p.R - p.S * 0.4, p.XH - p.Hb / 2)
    vstem(g, p, p.M - p.S * 0.2, p.DESC * 0.6, p.XH)


@glyph("uni204B", 0x204B)
def revpilcrow(g, p):
    from .punct import paragraph

    paragraph(g, p)
    g.mirror_x()


@glyph("uni2E18", 0x2E18)
def invinterrobang(g, p):
    from .punct import interrobang

    interrobang(g, p)
    g.transform(lambda q: (2 * p.M - q[0], p.XH - q[1]))


# ------------------------------------------------------------------ African Latin capitals
def cap_hook_left(g, p, x, top):
    """Stem top that curls over to the left (Ɓ Ɗ Ƈ)."""
    S, H = p.S, p.H
    yt = top + p.OV * 0.5 - H / 2
    r = (p.R - p.L) * 0.2
    path = Path((x, top * 0.7)).L((x, yt - r)).vh((x - r * 0.9, yt)).L((x - r * 1.4, yt - 10))
    g.stroke(path, end="butt")


def cap_hook_right(g, p, x, top):
    S, H = p.S, p.H
    yt = top + p.OV * 0.5 - H / 2
    r = (p.R - p.L) * 0.2
    path = Path((x, top * 0.7)).L((x, yt - r)).vh((x + r * 0.9, yt)).L((x + r * 1.4, yt - 10))
    g.stroke(path, end="butt")


def _shift(dx):
    def f(g, p):
        g.translate(dx(p))
    return f


@glyph("uni0181", 0x181)
def Bhook(g, p):
    t = drawn(p, "B")
    t.translate(p.S * 0.35)
    g.add(t.contours)
    cap_hook_left(g, p, p.L + p.S / 2 + p.S * 0.4, p.CAP)


@glyph("uni018A", 0x18A)
def Dhook(g, p):
    t = drawn(p, "D")
    t.translate(p.S * 0.35)
    g.add(t.contours)
    cap_hook_left(g, p, p.L + p.S / 2 + p.S * 0.4, p.CAP)


@glyph("uni0187", 0x187)
def Chook(g, p):
    put(g, p, "C")
    cap_hook_right(g, p, p.R - p.S * 0.6, p.CAP + 40)


@glyph("uni0188", 0x188)
def chook(g, p):
    put(g, p, "c")
    cap_hook_right(g, p, p.R - p.S * 0.6, p.XH + 60)


@glyph("uni0191", 0x191)
def Fhook(g, p):
    put(g, p, "F")
    from .latin_ext import hook_below

    hook_below(g, p, p.L + p.S / 2 + p.S * 0.15)


@glyph("uni0193", 0x193)
def Ghook(g, p):
    put(g, p, "G")
    cap_hook_right(g, p, p.R - p.S * 0.6, p.CAP + 40)


@glyph("uni0194", 0x194)
def Gammalatin(g, p):
    from .greek import gamma

    q = derive(p, 1.0, p.CAP / p.XH, 1.0)
    q.XH = p.CAP
    t = Glyph("tmp", q)
    gamma(t, q)
    g.add(t.contours)


@glyph("uni0196", 0x196)
def Iotalatin(g, p):
    put(g, p, "I")


@glyph("uni0198", 0x198)
def Khook(g, p):
    put(g, p, "K")
    cap_hook_right(g, p, p.L + p.S / 2 + p.S * 0.1, p.CAP + 30)


@glyph("uni019D", 0x19D)
def Nlefthook(g, p):
    put(g, p, "N")
    from .latin_ext import hook_below

    hook_below(g, p, p.L + p.S / 2)


@glyph("uni01B1", 0x1B1)
def Upsilonlatin(g, p):
    from .greek import Omega

    Omega(g, p)
    g.transform(lambda q: (q[0], p.CAP - q[1]), flip=True)


@glyph("uni01B2", 0x1B2)
def Vhook(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    yb = -p.OV + H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.CAP / 2, f=1.1)
    path = Path((xl, p.CAP)).L((xl, yb + r)).vh((cx, yb)).hv((xr, yb + r)).L((xr, p.CAP - r * 0.6)).vh((xr - r * 0.5, p.CAP + p.OV - H / 2))
    g.stroke(path)


@glyph("uni01B3", 0x1B3)
def Yhook(g, p):
    put(g, p, "Y")
    cap_hook_right(g, p, p.R - p.S * 0.9, p.CAP + 40)


@glyph("uni01B4", 0x1B4)
def yhook(g, p):
    put(g, p, "y")
    cap_hook_right(g, p, p.R - p.S * 0.6, p.XH + 60)


@glyph("uni0190", 0x190)
def Epsilonlatin(g, p):
    from .greek import epsilon_body

    epsilon_body(g, p, p.CAP)


@glyph("uniA78B", 0xA78B)
def Saltillo(g, p):
    g.stroke(Path((p.M, p.CAP)).L((p.M, p.CAP * 0.45), 0.7), pen=Pen(p.S * 1.1, p.S * 1.1))


@glyph("uniA78C", 0xA78C)
def saltillo(g, p):
    g.stroke(Path((p.M, p.XH + 60)).L((p.M, p.XH * 0.4), 0.7), pen=Pen(p.S * 1.1, p.S * 1.1))


@glyph("uni021C", 0x21C)
def Yogh(g, p):
    put(g, p, "Ezh")


@glyph("uni021D", 0x21D)
def yogh(g, p):
    put(g, p, "ezh")
