"""ASCII punctuation and symbols, Latin-1 and General Punctuation."""

from __future__ import annotations

import math

from ..geom import Contour, unit
from ..glyph import Glyph, glyph
from ..stroke import Path, Pen
from .latin_lower import diag_between, s_shape
from .parts import arc_h, c_shape, clamp, diag, disc, dot, hbar, oval, ring_circle, vstem


# ------------------------------------------------------------------ helpers
def pdot_d(p):
    """Diameter of punctuation dots."""
    return min(p.S * 1.3 + 14, (p.R - p.L) * 0.42)


def pdot(g, p, cx, y_bottom):
    d = pdot_d(p)
    dot(g, p, cx, y_bottom + d / 2, d=d, k=0.66)


def comma_at(g, p, cx, y_bottom, flip=False):
    """Comma: dot head with a tail sweeping down-left. flip -> rotated 180°
    about the dot centre (for turned quotes)."""
    d = pdot_d(p)
    cy = y_bottom + d / 2
    tmp = Glyph("tmp", p)
    dot(tmp, p, cx, cy, d=d, k=0.66)
    a = (cx + d * 0.2, cy - d * 0.05)
    b = (cx - d * 0.55, cy - d * 1.75)
    path = Path(a, 1.0).C((cx + d * 0.25, cy - d * 0.7), (cx - d * 0.05, cy - d * 1.3), b, 0.55)
    tmp.stroke(path, pen=Pen(d * 0.62, d * 0.62))
    if flip:
        tmp.transform(lambda q: (2 * cx - q[0], 2 * cy - q[1]))
    g.add(tmp.contours)


def rot180(g, cx, cy):
    g.transform(lambda q: (2 * cx - q[0], 2 * cy - q[1]))


def draw_into(g, p, fn):
    tmp = Glyph("tmp", p)
    fn(tmp, p)
    return tmp


def anchors(g, p, top=None):
    g.anchor("top", p.M, p.XH if top is None else top).anchor("bottom", p.M, 0)


# ------------------------------------------------------------------ dots
@glyph("period", 0x2E)
def period(g, p):
    pdot(g, p, p.M, 0)


@glyph("comma", 0x2C)
def comma(g, p):
    comma_at(g, p, p.M, 0)


@glyph("colon", 0x3A)
def colon(g, p):
    pdot(g, p, p.M, 0)
    pdot(g, p, p.M, p.XH - pdot_d(p))


@glyph("semicolon", 0x3B)
def semicolon(g, p):
    comma_at(g, p, p.M, 0)
    pdot(g, p, p.M, p.XH - pdot_d(p))


@glyph("exclam", 0x21)
def exclam(g, p):
    d = pdot_d(p)
    path = Path((p.M, p.CAP), 1.08).L((p.M, d + p.CAP * 0.2), 0.8)
    g.stroke(path)
    pdot(g, p, p.M, 0)


@glyph("exclamdown", 0xA1)
def exclamdown(g, p):
    exclam(g, p)
    rot180(g, p.M, p.XH / 2)


def question_body(g, p):
    S, H = p.S, p.H
    d = pdot_d(p)
    x0, x1 = p.L + S * 0.2, p.R - S * 0.2
    xl, xr = x0 + S / 2, x1 - S / 2
    yt = p.CAP + p.OV - H / 2
    cx = (xl + xr) / 2
    r = arc_h(p, (xr - xl) / 2, p.CAP / 2, f=0.75)
    ym = p.CAP * 0.42
    path = (
        Path((xl, yt - r * 0.85))
        .vh((cx, yt))
        .hv((xr, yt - r))
        .C((xr, yt - r * 1.6), (p.M, ym + r * 0.5), (p.M, ym))
        .L((p.M, d + p.CAP * 0.2))
    )
    g.stroke(path)
    pdot(g, p, p.M, 0)


@glyph("question", 0x3F)
def question(g, p):
    question_body(g, p)


@glyph("questiondown", 0xBF)
def questiondown(g, p):
    question_body(g, p)
    rot180(g, p.M, p.XH / 2)


@glyph("periodcentered", 0xB7)
def periodcentered(g, p):
    d = pdot_d(p)
    pdot(g, p, p.M, p.AX - d / 2)


@glyph("ellipsis", 0x2026)
def ellipsis(g, p):
    d = min(pdot_d(p), p.W * 0.26)
    for i in (-1, 0, 1):
        dot(g, p, p.M + i * p.W * 0.33, d / 2, d=d, k=0.66)


@glyph("onedotenleader", 0x2024)
def onedotenleader(g, p):
    pdot(g, p, p.M, 0)


@glyph("twodotenleader", 0x2025)
def twodotenleader(g, p):
    d = min(pdot_d(p), p.W * 0.3)
    for i in (-1, 1):
        dot(g, p, p.M + i * p.W * 0.25, d / 2, d=d, k=0.66)


@glyph("bullet", 0x2022)
def bullet(g, p):
    r = min(p.S * 0.9 + 60, (p.R - p.L) * 0.32)
    disc(g, p.M, p.AX, r, r)


@glyph("uni2023", 0x2023)
def triangularbullet(g, p):
    r = min(p.S * 0.9 + 60, (p.R - p.L) * 0.32)
    g.poly((p.M - r * 0.75, p.AX + r), (p.M + r * 0.95, p.AX), (p.M - r * 0.75, p.AX - r))


@glyph("uni2043", 0x2043)
def hyphenbullet(g, p):
    hw = (p.R - p.L) * 0.24
    g.rect(p.M - hw, p.AX - p.Hb * 0.7, p.M + hw, p.AX + p.Hb * 0.7)


@glyph("uni2027", 0x2027)
def hyphenationpoint(g, p):
    d = pdot_d(p) * 0.8
    dot(g, p, p.M, p.AX, d=d, k=0.66)


# ------------------------------------------------------------------ quotes
def straight_quote(g, p, x):
    top = p.CAP + 10
    path = Path((x, top), 1.0).L((x, top - p.CAP * 0.3), 0.72)
    g.stroke(path)


@glyph("quotesingle", 0x27)
def quotesingle(g, p):
    straight_quote(g, p, p.M)


@glyph("quotedbl", 0x22)
def quotedbl(g, p):
    off = max(p.S * 0.9, (p.R - p.L) * 0.16)
    straight_quote(g, p, p.M - off)
    straight_quote(g, p, p.M + off)


def qdy(p):
    return p.CAP - pdot_d(p) * 0.95


@glyph("quoteright", 0x2019)
def quoteright(g, p):
    comma_at(g, p, p.M, qdy(p))


@glyph("quoteleft", 0x2018)
def quoteleft(g, p):
    comma_at(g, p, p.M, qdy(p) - pdot_d(p) * 0.75, flip=True)


@glyph("quotesinglbase", 0x201A)
def quotesinglbase(g, p):
    comma_at(g, p, p.M, 0)


@glyph("quotereversed", 0x201B)
def quotereversed(g, p):
    comma_at(g, p, p.M, qdy(p))
    g.mirror_x()


def dq_off(p):
    return min(pdot_d(p) * 0.85, (p.R - p.L) * 0.24)


@glyph("quotedblright", 0x201D)
def quotedblright(g, p):
    o = dq_off(p)
    comma_at(g, p, p.M - o, qdy(p))
    comma_at(g, p, p.M + o, qdy(p))


@glyph("quotedblleft", 0x201C)
def quotedblleft(g, p):
    o = dq_off(p)
    y = qdy(p) - pdot_d(p) * 0.75
    comma_at(g, p, p.M - o, y, flip=True)
    comma_at(g, p, p.M + o, y, flip=True)


@glyph("quotedblbase", 0x201E)
def quotedblbase(g, p):
    o = dq_off(p)
    comma_at(g, p, p.M - o, 0)
    comma_at(g, p, p.M + o, 0)


@glyph("uni201F", 0x201F)
def quotedblreversed(g, p):
    quotedblright(g, p)
    g.mirror_x()


def chevron(g, p, cx, cy, hw, hh, right, w=0.9):
    d = 1 if right else -1
    path = Path((cx - d * hw, cy + hh), w).L((cx + d * hw, cy), w).L((cx - d * hw, cy - hh), w)
    g.stroke(path)


@glyph("guilsinglleft", 0x2039)
def guilsinglleft(g, p):
    chevron(g, p, p.M, p.XH * 0.5, (p.R - p.L) * 0.17, p.XH * 0.27, False)


@glyph("guilsinglright", 0x203A)
def guilsinglright(g, p):
    chevron(g, p, p.M, p.XH * 0.5, (p.R - p.L) * 0.17, p.XH * 0.27, True)


@glyph("guillemotleft", 0xAB)
def guillemotleft(g, p):
    o = (p.R - p.L) * 0.2
    for dx in (-o, o):
        chevron(g, p, p.M + dx, p.XH * 0.5, (p.R - p.L) * 0.14, p.XH * 0.25, False, w=0.82)


@glyph("guillemotright", 0xBB)
def guillemotright(g, p):
    o = (p.R - p.L) * 0.2
    for dx in (-o, o):
        chevron(g, p, p.M + dx, p.XH * 0.5, (p.R - p.L) * 0.14, p.XH * 0.25, True, w=0.82)


# ------------------------------------------------------------------ dashes & bars
@glyph("hyphen", 0x2D)
def hyphen(g, p):
    hw = (p.R - p.L) * 0.34
    hbar(g, p, p.M - hw, p.M + hw, p.AX)


@glyph("uni00AD", 0xAD)
def softhyphen(g, p):
    hyphen(g, p)


@glyph("uni2010", 0x2010)
def hyphentwo(g, p):
    hyphen(g, p)


@glyph("uni2011", 0x2011)
def nbhyphen(g, p):
    hyphen(g, p)


@glyph("figuredash", 0x2012)
def figuredash(g, p):
    hbar(g, p, p.L, p.R, p.AX)


@glyph("endash", 0x2013)
def endash(g, p):
    hbar(g, p, p.L * 0.5, p.W - p.L * 0.5, p.AX)


@glyph("emdash", 0x2014)
def emdash(g, p):
    hbar(g, p, 0, p.W, p.AX)


@glyph("horizontalbar", 0x2015)
def horizontalbar(g, p):
    hbar(g, p, 0, p.W, p.AX)


@glyph("uni2E3A", 0x2E3A, cells=2)
def twoemdash(g, p):
    hbar(g, p, 0, 2 * p.W, p.AX)


@glyph("underscore", 0x5F)
def underscore(g, p):
    g.rect(0, -130, p.W, -130 + p.Hb)


@glyph("underscoredbl", 0x2017)
def underscoredbl(g, p):
    g.rect(0, -130, p.W, -130 + p.Hb)
    g.rect(0, -130 - p.Hb * 2.1, p.W, -130 - p.Hb * 1.1)


@glyph("overline", 0x203E)
def overline(g, p):
    g.rect(0, p.CAP + 120 - p.Hb, p.W, p.CAP + 120)


@glyph("macron", 0xAF)
def macron(g, p):
    hw = (p.R - p.L) * 0.32
    g.rect(p.M - hw, p.CAP + 60, p.M + hw, p.CAP + 60 + p.Hb)


@glyph("bar", 0x7C)
def bar(g, p):
    vstem(g, p, p.M, p.BB, p.BT)


@glyph("brokenbar", 0xA6)
def brokenbar(g, p):
    mid = (p.BB + p.BT) / 2
    gap = p.S * 0.6 + 40
    vstem(g, p, p.M, p.BB, mid - gap / 2)
    vstem(g, p, p.M, mid + gap / 2, p.BT)


@glyph("dblverticalbar", 0x2016)
def dblverticalbar(g, p):
    o = max(p.S * 0.9, (p.R - p.L) * 0.17)
    vstem(g, p, p.M - o, p.BB, p.BT)
    vstem(g, p, p.M + o, p.BB, p.BT)


# ------------------------------------------------------------------ slashes
def slash_pts(p, flip=False):
    top, bot = p.ASC + 50, p.DESC + 40
    a, b = diag_between(p, p.R - p.S * 0.1, top, p.L + p.S * 0.1, bot, -1, 1, w=0.95)
    if flip:
        a = (p.W - a[0], a[1])
        b = (p.W - b[0], b[1])
    return a, b


@glyph("slash", 0x2F)
def slash(g, p):
    a, b = slash_pts(p)
    diag(g, p, a, b, w=0.95)


@glyph("backslash", 0x5C)
def backslash(g, p):
    a, b = slash_pts(p, True)
    diag(g, p, a, b, w=0.95)


@glyph("fraction", 0x2044)
def fraction(g, p):
    a, b = diag_between(p, p.R + p.S * 0.3, p.CAP, p.L - p.S * 0.3, 0, -1, 1, w=0.85)
    diag(g, p, a, b, w=0.85)


# ------------------------------------------------------------------ brackets
def paren_path(p, x_end, x_bulge, top, bot):
    mid = (top + bot) / 2
    h = top - bot
    return (
        Path((x_end, top), 0.82)
        .C((x_end + (x_bulge - x_end) * 0.55, top - h * 0.12), (x_bulge, mid + h * 0.26), (x_bulge, mid), 1.0)
        .C((x_bulge, mid - h * 0.26), (x_end + (x_bulge - x_end) * 0.55, bot + h * 0.12), (x_end, bot), 0.82)
    )


@glyph("parenleft", 0x28)
def parenleft(g, p):
    xe = p.R - p.S * 0.4 - (p.R - p.L) * 0.08
    xb = p.L + p.S / 2 + (p.R - p.L) * 0.12
    g.stroke(paren_path(p, xe, xb, p.BT, p.BB), start="butt", end="butt")


@glyph("parenright", 0x29)
def parenright(g, p):
    parenleft(g, p)
    g.mirror_x()


@glyph("bracketleft", 0x5B)
def bracketleft(g, p):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + (p.R - p.L) * 0.14
    xe = p.R - (p.R - p.L) * 0.1
    vstem(g, p, xs, p.BB, p.BT)
    g.rect(xs - S / 2, p.BT - Hb, xe, p.BT)
    g.rect(xs - S / 2, p.BB, xe, p.BB + Hb)


@glyph("bracketright", 0x5D)
def bracketright(g, p):
    bracketleft(g, p)
    g.mirror_x()


@glyph("braceleft", 0x7B)
def braceleft(g, p):
    S, H = p.S, p.H
    xc = p.M - S * 0.05
    xr = p.R - (p.R - p.L) * 0.08
    xl = p.L + (p.R - p.L) * 0.06
    yt, yb = p.BT - H / 2, p.BB + H / 2
    mid = (p.BT + p.BB) / 2
    r = min((xr - xc) * 0.85, (yt - mid) * 0.3)
    r2 = min((xc - xl) * 0.8, (yt - mid) * 0.2)
    up = Path((xr, yt)).L((xc + r, yt)).hv((xc, yt - r)).L((xc, mid + r2)).vh((xc - r2, mid)).L((xl, mid))
    g.stroke(up)
    lo = Path((xr, yb)).L((xc + r, yb)).hv((xc, yb + r)).L((xc, mid - r2)).vh((xc - r2, mid)).L((xl, mid))
    g.stroke(lo)


@glyph("braceright", 0x7D)
def braceright(g, p):
    braceleft(g, p)
    g.mirror_x()


# ------------------------------------------------------------------ operators
def op_hw(p):
    return (p.R - p.L) * 0.42


@glyph("plus", 0x2B)
def plus(g, p):
    hw = op_hw(p)
    hbar(g, p, p.M - hw, p.M + hw, p.AX, sy=p.S * 0.95)
    vstem(g, p, p.M, p.AX - hw, p.AX + hw, sx=p.S * 0.95)


def eq_gap(p):
    return max(p.S * 1.35, 90) + p.S * 0.3


@glyph("equal", 0x3D)
def equal(g, p):
    hw = op_hw(p)
    gap = eq_gap(p)
    hbar(g, p, p.M - hw, p.M + hw, p.AX + gap / 2, sy=p.S * 0.92)
    hbar(g, p, p.M - hw, p.M + hw, p.AX - gap / 2, sy=p.S * 0.92)


def angle_pts(p, hh=None, hw=None):
    hw = op_hw(p) * 0.92 if hw is None else hw
    hh = (p.R - p.L) * 0.42 if hh is None else hh
    return hw, hh


@glyph("less", 0x3C)
def less(g, p):
    hw, hh = angle_pts(p)
    path = Path((p.M + hw, p.AX + hh), 0.95).L((p.M - hw, p.AX), 0.95).L((p.M + hw, p.AX - hh), 0.95)
    g.stroke(path)


@glyph("greater", 0x3E)
def greater(g, p):
    less(g, p)
    g.mirror_x()


@glyph("asciitilde", 0x7E)
def asciitilde(g, p):
    hw = op_hw(p) * 0.95
    a = p.S * 0.35 + 34
    x0, x1 = p.M - hw, p.M + hw
    w = x1 - x0
    path = (
        Path((x0, p.AX - a * 0.45))
        .C((x0 + w * 0.12, p.AX + a * 1.1), (p.M - w * 0.2, p.AX + a * 0.9), (p.M, p.AX))
        .C((p.M + w * 0.2, p.AX - a * 0.9), (x1 - w * 0.12, p.AX - a * 1.1), (x1, p.AX + a * 0.45))
    )
    g.stroke(path, pen=Pen(p.S * 0.95, p.S * 0.95))


@glyph("asciicircum", 0x5E)
def asciicircum(g, p):
    hw = (p.R - p.L) * 0.36
    top = p.CAP
    a, b = diag_between(p, p.M, top, p.M - hw, p.CAP * 0.5, 0, 0, w=0.9)
    diag(g, p, a, b, w=0.9)
    c, d = diag_between(p, p.M, top, p.M + hw, p.CAP * 0.5, 0, 0, w=0.9)
    diag(g, p, c, d, w=0.9)


@glyph("asterisk", 0x2A)
def asterisk(g, p):
    r = (p.R - p.L) * 0.4
    cy = p.AX + p.S * 0.05
    for ang in (90, 210, 330):
        a = math.radians(ang)
        tip = (p.M + r * math.cos(a), cy + r * math.sin(a))
        g.stroke(Path((p.M, cy), 1.0).L(tip, 0.82), pen=Pen(p.S * 0.95, p.S * 0.95), start="butt", end="butt")
        a2 = math.radians(ang + 180)
        tip2 = (p.M + r * math.cos(a2), cy + r * math.sin(a2))
        g.stroke(Path((p.M, cy), 1.0).L(tip2, 0.82), pen=Pen(p.S * 0.95, p.S * 0.95), start="butt", end="butt")


@glyph("multiply", 0xD7)
def multiply(g, p):
    r = op_hw(p) * 0.78
    pen = Pen(p.S * 0.95, p.S * 0.95)
    g.stroke(Path((p.M - r, p.AX - r)).L((p.M + r, p.AX + r)), pen=pen)
    g.stroke(Path((p.M - r, p.AX + r)).L((p.M + r, p.AX - r)), pen=pen)


@glyph("divide", 0xF7)
def divide(g, p):
    hw = op_hw(p)
    hbar(g, p, p.M - hw, p.M + hw, p.AX, sy=p.S * 0.92)
    d = pdot_d(p) * 0.9
    gap = eq_gap(p) * 0.6 + d / 2
    dot(g, p, p.M, p.AX + gap, d=d, k=0.66)
    dot(g, p, p.M, p.AX - gap, d=d, k=0.66)


@glyph("plusminus", 0xB1)
def plusminus(g, p):
    hw = op_hw(p)
    y = p.AX + hw * 0.35
    hbar(g, p, p.M - hw, p.M + hw, y, sy=p.S * 0.92)
    vstem(g, p, p.M, y - hw * 0.85, y + hw * 0.85, sx=p.S * 0.92)
    hbar(g, p, p.M - hw, p.M + hw, y - hw * 1.25, sy=p.S * 0.92)


@glyph("logicalnot", 0xAC)
def logicalnot(g, p):
    hw = op_hw(p)
    hbar(g, p, p.M - hw, p.M + hw, p.AX + p.S * 0.5, sy=p.S * 0.92)
    g.rect(p.M + hw - p.S * 0.92, p.AX + p.S * 0.5, p.M + hw, p.AX - hw * 0.6)


# ------------------------------------------------------------------ number sign etc.
@glyph("numbersign", 0x23)
def numbersign(g, p):
    S = p.S * 0.9
    top, bot = p.CAP - 20, 20
    ox = (p.R - p.L) * 0.2
    oy = p.CAP * 0.17
    sl = (top - bot) * 0.08
    pen = Pen(S, p.H * 0.9)
    for dx in (-ox, ox):
        g.stroke(Path((p.M + dx - sl, bot)).L((p.M + dx + sl, top)), pen=pen, start=0, end=0)
    for dy in (-oy, oy):
        hbar(g, p, p.L, p.R, p.CAP / 2 + dy, sy=p.H * 0.92)


@glyph("dollar", 0x24)
def dollar(g, p):
    inset = p.S * 0.1
    s_shape(g, p, p.L + inset, p.R - inset, 40, p.CAP - 40, te_f=0.25, be_f=0.24)
    vstem(g, p, p.M, -110, p.CAP + 110, sx=p.S * 0.8)


@glyph("percent", 0x25)
def percent(g, p):
    S = p.S * 0.85
    pen_h = p.H * 0.85
    rw = (p.R - p.L) * 0.42
    rh = p.CAP * 0.36
    oval(g, p, p.L, p.L + rw, p.CAP - rh, p.CAP, sx=S, sy=pen_h)
    oval(g, p, p.R - rw, p.R, 0, rh, sx=S, sy=pen_h)
    a, b = diag_between(p, p.R, p.CAP, p.L, 0, -1, 1, w=0.85)
    diag(g, p, a, b, w=0.85)


@glyph("perthousand", 0x2030)
def perthousand(g, p):
    S = p.S * 0.7
    pen_h = p.H * 0.7
    rw = (p.R - p.L) * 0.34
    rh = p.CAP * 0.3
    oval(g, p, p.L, p.L + rw, p.CAP - rh, p.CAP, sx=S, sy=pen_h)
    oval(g, p, p.R - 2 * rw - S * 0.2, p.R - rw - S * 0.2, 0, rh, sx=S, sy=pen_h)
    oval(g, p, p.R - rw, p.R, 0, rh, sx=S, sy=pen_h)
    a, b = diag_between(p, p.R - rw * 0.5, p.CAP, p.L + rw * 0.5, 0, -1, 1, w=0.7)
    diag(g, p, a, b, w=0.7)


@glyph("ampersand", 0x26)
def ampersand(g, p):
    S = min(p.S, (p.R - p.L) * 0.24)
    H = p.H * S / p.S
    x0, x1 = p.L, p.R
    xl, xr = x0 + S / 2, x1 - S / 2
    yt = p.CAP + p.OV - H / 2
    yb = -p.OV + H / 2
    # upper loop
    ul, ur = xl + (xr - xl) * 0.12, xl + (xr - xl) * 0.68
    ucx = (ul + ur) / 2
    yu = p.CAP * 0.74
    path = (
        Path((xr + S * 0.1, yb - H / 2 + 1))
        .C((xr - (xr - xl) * 0.35, p.CAP * 0.25), (ul, yu - (yt - yu) * 0.9), (ul, yu))
        .vh((ucx, yt))
        .hv((ur, yu))
        .C((ur, yu - (yt - yu) * 0.8), (xl, p.CAP * 0.48), (xl, p.CAP * 0.26))
        .vh(((xl + xr) / 2 - S * 0.1, yb))
        .C((xr - S * 0.3, yb), (xr, p.CAP * 0.2), (xr, p.CAP * 0.42))
    )
    g.stroke(path, pen=Pen(S, H), start=0, end=0)


@glyph("at", 0x40)
def at(g, p):
    S = min(p.S * 0.82, (p.R - p.L + p.S * 0.3) / 7.2)
    H = p.H * S / p.S
    pen = Pen(S, H)
    x0, x1 = p.L - p.S * 0.15, p.R + p.S * 0.15
    yb, yt = p.DESC * 0.55, p.CAP + p.OV
    # inner a: bowl + stem
    xs = x1 - (x1 - x0) * 0.28 - S / 2
    ib0, ib1 = p.XH * 0.08 - p.OV, p.XH * 0.98 + p.OV
    il = x0 + (x1 - x0) * 0.28
    tmp = Glyph("tmp", p)
    from .parts import bowl_side

    bowl_side(g, p, xs, il, ib0, ib1, sx=S, sy=H)
    # outer arc continues from the stem down then around
    xl, xr = x0 + S / 2, x1 - S / 2
    ytc, ybc = yt - H / 2, yb + H / 2
    cx = (xl + xr) / 2
    ry = arc_h(p, (xr - xl) / 2, (ytc - ybc) / 2, f=0.95)
    path = (
        Path((xs, ib1 - H * 0.3))
        .L((xs, ib0 + 40))
        .vh((xs + (xr - xs) * 0.5, ib0 + H / 2))
        .hv((xr, ib0 + 90))
        .L((xr, ytc - ry))
        .vh((cx, ytc))
        .hv((xl, ytc - ry))
        .L((xl, ybc + ry))
        .vh((cx, ybc))
        .hv((xr - S * 0.4, ybc + ry * 0.35))
    )
    g.stroke(path, pen=pen, start=0)


@glyph("section", 0xA7)
def section(g, p):
    S = p.S * 0.9
    H = p.H * 0.9
    pen = Pen(S, H)
    x0, x1 = p.L + p.S * 0.25, p.R - p.S * 0.25
    xl, xr = x0 + S / 2, x1 - S / 2
    cx = (xl + xr) / 2
    yt, yb = p.CAP + p.OV - H / 2, p.DESC * 0.45 + H / 2
    h = yt - yb
    r = (xr - xl) * 0.42
    # upper s-curve: terminal top-right, around left, sweep down to right middle
    y1 = yt - h * 0.3
    path = (
        Path((xr, yt - r * 0.7))
        .vh((cx, yt))
        .hv((xl, yt - r))
        .C((xl, yt - r * 1.9), (xr, yt - h * 0.38), (xr, yt - h * 0.55))
        .vh((cx, yb + h * 0.3))
    )
    g.stroke(path, pen=pen)
    path = (
        Path((xl, yb + r * 0.7))
        .vh((cx, yb))
        .hv((xr, yb + r))
        .C((xr, yb + r * 1.9), (xl, yb + h * 0.38), (xl, yb + h * 0.55))
        .vh((cx, yt - h * 0.3))
    )
    g.stroke(path, pen=pen)


@glyph("paragraph", 0xB6)
def paragraph(g, p):
    S = p.S * 0.9
    xs2 = p.R - S / 2 - p.S * 0.1
    xs1 = xs2 - (p.R - p.L) * 0.32
    vstem(g, p, xs2, p.DESC * 0.6, p.CAP, sx=S)
    vstem(g, p, xs1, p.DESC * 0.6, p.CAP, sx=S)
    # filled bowl
    yb = p.CAP * 0.38
    top = p.CAP
    xl = p.L
    r = (top - yb) / 2
    c = Contour(
        (xs1, top),
        [
            ("L", (xs1, yb)),
            ("L", (xl + r, yb)),
            ("C", (xl + r * 0.4, yb), (xl, yb + r * 0.45), (xl, yb + r)),
            ("C", (xl, top - r * 0.45), (xl + r * 0.4, top), (xl + r, top)),
            ("L", (xs1, top)),
        ],
    )
    g.add(c.clockwise())
    g.rect(xs1, top - p.Hb * 0.9, xs2 + S / 2, top)


@glyph("degree", 0xB0)
def degree(g, p):
    r = (p.R - p.L) * 0.24
    cy = p.CAP - r
    t = max(p.S * 0.75, 20)
    ring_circle(g, p.M, cy, r, r - t)


@glyph("dagger", 0x2020)
def dagger(g, p):
    vstem(g, p, p.M, p.DESC * 0.5, p.CAP, sx=p.S * 0.9)
    hbar(g, p, p.L + p.S * 0.2, p.R - p.S * 0.2, p.CAP * 0.66, sy=p.Hb * 0.95)


@glyph("daggerdbl", 0x2021)
def daggerdbl(g, p):
    vstem(g, p, p.M, p.DESC * 0.5, p.CAP, sx=p.S * 0.9)
    hbar(g, p, p.L + p.S * 0.2, p.R - p.S * 0.2, p.CAP * 0.7, sy=p.Hb * 0.95)
    hbar(g, p, p.L + p.S * 0.2, p.R - p.S * 0.2, p.CAP * 0.1, sy=p.Hb * 0.95)


# ------------------------------------------------------------------ primes
def prime_stroke(g, p, x, w=1.0):
    top = p.CAP + 20
    a = (x + (p.R - p.L) * 0.06, top)
    b = (x - (p.R - p.L) * 0.06, top - p.CAP * 0.32)
    g.stroke(Path(a, 0.95 * w).L(b, 0.6 * w), start=0, end="butt")


@glyph("minute", 0x2032)
def minute(g, p):
    prime_stroke(g, p, p.M)


@glyph("second", 0x2033)
def second(g, p):
    o = (p.R - p.L) * 0.2
    prime_stroke(g, p, p.M - o, 0.85)
    prime_stroke(g, p, p.M + o, 0.85)


@glyph("uni2034", 0x2034)
def third(g, p):
    o = (p.R - p.L) * 0.3
    for dx in (-o, 0, o):
        prime_stroke(g, p, p.M + dx, 0.7)


@glyph("uni2057", 0x2057)
def fourth(g, p):
    o = (p.R - p.L) * 0.22
    for dx in (-1.5 * o, -0.5 * o, 0.5 * o, 1.5 * o):
        prime_stroke(g, p, p.M + dx, 0.55)


@glyph("uni2035", 0x2035)
def revprime(g, p):
    minute(g, p)
    g.mirror_x()


@glyph("uni2036", 0x2036)
def revsecond(g, p):
    second(g, p)
    g.mirror_x()


@glyph("uni2037", 0x2037)
def revthird(g, p):
    third(g, p)
    g.mirror_x()


# ------------------------------------------------------------------ misc
@glyph("exclamdbl", 0x203C)
def exclamdbl(g, p):
    o = (p.R - p.L) * 0.2
    d = pdot_d(p) * 0.85
    for dx in (-o, o):
        g.stroke(Path((p.M + dx, p.CAP), 0.95).L((p.M + dx, d + p.CAP * 0.2), 0.7))
        dot(g, p, p.M + dx, d / 2, d=d, k=0.66)


@glyph("interrobang", 0x203D)
def interrobang(g, p):
    question_body(g, p)
    g.stroke(Path((p.M, p.CAP), 0.9).L((p.M, pdot_d(p) + p.CAP * 0.2), 0.7))


@glyph("uni203B", 0x203B)
def referencemark(g, p):
    r = (p.R - p.L) * 0.42
    pen = Pen(p.S * 0.8, p.S * 0.8)
    g.stroke(Path((p.M - r, p.AX - r)).L((p.M + r, p.AX + r)), pen=pen)
    g.stroke(Path((p.M - r, p.AX + r)).L((p.M + r, p.AX - r)), pen=pen)
    d = pdot_d(p) * 0.75
    for dx, dy in ((0, r * 1.05), (0, -r * 1.05), (r * 1.05, 0), (-r * 1.05, 0)):
        dot(g, p, p.M + dx, p.AX + dy, d=d, k=0.66)


@glyph("currency", 0xA4)
def currency(g, p):
    r = (p.R - p.L) * 0.3
    t = p.S * 0.85
    ring_circle(g, p.M, p.AX, r, r - t)
    pen = Pen(p.S * 0.85, p.S * 0.85)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        a = (p.M + sx * r * 0.62, p.AX + sy * r * 0.62)
        b = (p.M + sx * r * 1.25, p.AX + sy * r * 1.25)
        g.stroke(Path(a).L(b), pen=pen)


@glyph("copyright", 0xA9)
def copyright(g, p):
    r = (p.R - p.L) * 0.5 + p.S * 0.1
    cy = p.CAP / 2
    t = p.S * 0.62
    ring_circle(g, p.M, cy, r, r - t)
    rr = r * 0.52
    c_shape(g, p, p.M - rr, p.M + rr * 0.95, cy - rr * 1.05, cy + rr * 1.05, cy + rr * 0.45, cy - rr * 0.45,
            sx=t, sy=t * 0.95)


@glyph("registered", 0xAE)
def registered(g, p):
    r = (p.R - p.L) * 0.5 + p.S * 0.1
    cy = p.CAP / 2
    t = p.S * 0.62
    ring_circle(g, p.M, cy, r, r - t)
    xs = p.M - r * 0.38
    top, bot = cy + r * 0.52, cy - r * 0.52
    g.rect(xs - t / 2, bot, xs + t / 2, top)
    xr = p.M + r * 0.4
    xm = (xs + xr) / 2
    ym = cy - r * 0.02
    path = Path((xs, top - t / 2)).L((xm, top - t / 2)).hv((xr, (top + ym) / 2)).vh((xm, ym)).L((xs, ym))
    g.stroke(path, pen=Pen(t, t * 0.95))
    g.stroke(Path((xm, ym)).L((xr + t * 0.2, bot)), pen=Pen(t, t * 0.95), start="butt", end=0)


@glyph("ordfeminine", 0xAA)
def ordfeminine(g, p):
    from .latin_lower import a as draw_a
    from ..glyph import Params

    tmp = Glyph("tmp", p)
    sp = superior_params(p)
    draw_a(tmp, sp)
    tmp.translate(0, p.CAP - sp.XH)
    g.add(tmp.contours)
    g.rect(p.M - (p.R - p.L) * 0.32, p.CAP - sp.XH - 90 - p.Hb * 0.7, p.M + (p.R - p.L) * 0.32, p.CAP - sp.XH - 90)


@glyph("ordmasculine", 0xBA)
def ordmasculine(g, p):
    from .latin_lower import o as draw_o

    tmp = Glyph("tmp", p)
    sp = superior_params(p)
    draw_o(tmp, sp)
    tmp.translate(0, p.CAP - sp.XH)
    g.add(tmp.contours)
    g.rect(p.M - (p.R - p.L) * 0.32, p.CAP - sp.XH - 90 - p.Hb * 0.7, p.M + (p.R - p.L) * 0.32, p.CAP - sp.XH - 90)


def superior_params(p, f=0.62, wf=0.8):
    from .scaled import derive

    return derive(p, f, f * 1.05, wf)


@glyph("cent", 0xA2)
def cent(g, p):
    from .latin_lower import c as draw_c

    draw_c(g, p)
    vstem(g, p, p.M + p.S * 0.1, -100, p.XH + 100, sx=p.S * 0.8)


@glyph("sterling", 0xA3)
def sterling(g, p):
    S, H = p.S, p.H
    x0, x1 = p.L + S * 0.1, p.R
    xs = p.L + (p.R - p.L) * 0.3 + S / 2
    yt = p.CAP + p.OV - H / 2
    xr = x1 - S / 2 - S * 0.1
    cx = (xs + xr) / 2
    r = (xr - xs) * 0.6
    path = Path((xs, p.CAP * 0.15)).L((xs, yt - r)).vh((cx, yt)).hv((xr, yt - r * 0.8))
    g.stroke(path)
    hbar(g, p, x0 + S * 0.2, xr, p.CAP * 0.45)
    hbar(g, p, x0, x1, p.Hb / 2)
    g.stroke(Path((xs, p.CAP * 0.2)).C((xs, p.CAP * 0.08), (xs - S * 0.4, p.Hb), (x0 + S * 0.1, p.Hb * 0.5)), end="butt")


@glyph("yen", 0xA5)
def yen(g, p):
    ym = p.CAP * 0.46
    a, b = diag_between(p, p.L, p.CAP, p.M, ym, 1, 0)
    diag(g, p, a, (p.M, ym), end="butt")
    c, d = diag_between(p, p.R, p.CAP, p.M, ym, -1, 0)
    diag(g, p, c, (p.M, ym), end="butt")
    vstem(g, p, p.M, 0, ym + p.S * 0.1)
    hw = (p.R - p.L) * 0.38
    hbar(g, p, p.M - hw, p.M + hw, p.CAP * 0.36, sy=p.Hb * 0.9)
    hbar(g, p, p.M - hw, p.M + hw, p.CAP * 0.18, sy=p.Hb * 0.9)


@glyph("Euro", 0x20AC)
def euro(g, p):
    S = p.S
    te, be = p.CAP * 0.76, p.CAP * 0.24
    c_shape(g, p, p.L + (p.R - p.L) * 0.14, p.R, -p.OV, p.CAP + p.OV, te, be)
    hbar(g, p, p.L - S * 0.1, p.R - (p.R - p.L) * 0.2, p.CAP * 0.58, sy=p.Hb * 0.85)
    hbar(g, p, p.L - S * 0.1, p.R - (p.R - p.L) * 0.28, p.CAP * 0.4, sy=p.Hb * 0.85)
