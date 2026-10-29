"""Combining marks (U+0300–036F, U+20D0–20F0, …) and spacing accents.

Marks have zero advance and are drawn over the *preceding* cell (centred at
x = -W/2), so they also look right in terminals that do no GPOS. Anchors:
  _top / top        above marks (base anchor at x-height, cap height, …)
  _bottom / bottom  below marks
  _center           overlays (strokes, solidus)
  _horn, _ogonek    attached marks
Upper-case variants (.case) are flatter and used after capitals.
"""

from __future__ import annotations

import math

from ..geom import Contour
from ..glyph import Glyph, register
from ..stroke import Path, Pen
from .parts import KC, disc, dot, ring_circle

# vertical layout (relative to the base anchor at x-height / baseline)
GAP = 72
MH = 150
GAP_C = 58
MH_C = 118
GAP_B = 46
MH_B = 118
STACK = 28

MARKS = {}  # name -> position kind


def mpen(p, f=0.92):
    s = p.S * f
    return Pen(s, max(p.H * f, s * 0.82))


def mdot(p):
    return min(p.S * 1.18 + 16, (p.R - p.L) * 0.3)


class Z:
    """Mark zone handed to the drawing function."""

    def __init__(self, p, y0, h, cx, below=False, case=False):
        self.y0, self.h, self.cx = y0, h, cx
        self.y1 = y0 + h
        self.ym = y0 + h / 2
        self.w = (p.R - p.L) * 0.62  # standard mark width
        self.below = below
        self.case = case


def _make(fn, pos, case, ext=None):
    def full(g, p):
        g.adv = 0
        if pos == "top":
            if case:
                z = Z(p, p.XH + GAP_C, MH_C, p.M, case=True)
            else:
                z = Z(p, p.XH + GAP, MH, p.M)
            fn(g, p, z)
            g.anchor("_top", p.M, p.XH)
            g.anchor("top", p.M, z.y1 + STACK - (GAP_C if case else GAP) + 10)
        elif pos == "bottom":
            z = Z(p, -GAP_B - MH_B, MH_B, p.M, below=True)
            fn(g, p, z)
            g.anchor("_bottom", p.M, 0)
            g.anchor("bottom", p.M, z.y0 - STACK + GAP_B)
        elif pos == "center":
            z = Z(p, p.XH * 0.5 - MH / 2, MH, p.M)
            fn(g, p, z)
            g.anchor("_center", p.M, p.XH * 0.5)
        elif pos == "ogonek":
            z = Z(p, -GAP_B - MH_B, MH_B + GAP_B, p.M, below=True)
            fn(g, p, z)
            g.anchor("_ogonek", p.M, 0)
        elif pos == "horn":
            z = Z(p, p.XH, MH, p.M)
            fn(g, p, z)
            g.anchor("_horn", p.M, p.XH)
        elif pos == "double":
            z = Z(p, p.XH + GAP, MH, p.W)
            fn(g, p, z)
            g.anchor("_top", p.M, p.XH)
        elif pos == "doublebelow":
            z = Z(p, -GAP_B - MH_B, MH_B, p.W)
            fn(g, p, z)
            g.anchor("_bottom", p.M, 0)
        g.translate(-p.W)

    return full


def mark(name, uni, pos="top", case=None):
    """Register a mark (and its .case twin for top marks)."""
    if case is None:
        case = pos == "top"

    def deco(fn):
        register(name, _make(fn, pos, False), uni, kind="mark")
        MARKS[name] = pos
        if case:
            register(name + ".case", _make(fn, pos, True), None, kind="mark")
            MARKS[name + ".case"] = pos
        return fn

    return deco


# ------------------------------------------------------------------ primitives
def stroke_line(g, p, a, b, w0=1.0, w1=None, f=0.92, start="butt", end="butt"):
    g.stroke(Path(a, w0).L(b, w0 if w1 is None else w1), pen=mpen(p, f), start=start, end=end)


def acute_shape(g, p, z, cx=None, f=0.92):
    cx = z.cx if cx is None else cx
    hw = z.w * 0.24
    a = (cx - hw, z.y0)
    b = (cx + hw, z.y1)
    if z.case:
        b = (cx + hw * 1.25, z.y1)
    stroke_line(g, p, a, b, 0.62, 1.0, f=f, start="butt", end="butt")


def grave_shape(g, p, z, cx=None, f=0.92):
    cx = z.cx if cx is None else cx
    hw = z.w * 0.24
    a = (cx + hw, z.y0)
    b = (cx - hw * (1.25 if z.case else 1.0), z.y1)
    stroke_line(g, p, a, b, 0.62, 1.0, f=f)


def hat(g, p, z, up=True, f=0.92, hw=None, y0=None, y1=None):
    hw = z.w * 0.42 if hw is None else hw
    y0 = z.y0 if y0 is None else y0
    y1 = z.y1 if y1 is None else y1
    if up:
        path = Path((z.cx - hw, y0)).L((z.cx, y1)).L((z.cx + hw, y0))
    else:
        path = Path((z.cx - hw, y1)).L((z.cx, y0)).L((z.cx + hw, y1))
    g.stroke(path, pen=mpen(p, f), start=0, end=0)


def tilde_shape(g, p, z, f=0.9, hw=None, ym=None, amp=None):
    hw = z.w * 0.5 if hw is None else hw
    ym = z.ym if ym is None else ym
    a = z.h * 0.3 if amp is None else amp
    x0, x1 = z.cx - hw, z.cx + hw
    w = x1 - x0
    path = (
        Path((x0, ym - a * 0.5))
        .C((x0 + w * 0.1, ym + a * 1.0), (z.cx - w * 0.22, ym + a * 1.0), (z.cx, ym))
        .C((z.cx + w * 0.22, ym - a * 1.0), (x1 - w * 0.1, ym - a * 1.0), (x1, ym + a * 0.5))
    )
    g.stroke(path, pen=Pen(p.S * f, p.S * f))


def breve_shape(g, p, z, inverted=False, f=0.9, hw=None, y0=None, y1=None):
    hw = z.w * 0.4 if hw is None else hw
    y0 = z.y0 if y0 is None else y0
    y1 = z.y1 if y1 is None else y1
    pen = mpen(p, f)
    t = pen.B
    if not inverted:
        yb = y0 + t
        path = Path((z.cx - hw, y1)).vh((z.cx, yb)).hv((z.cx + hw, y1))
    else:
        yt = y1 - t
        path = Path((z.cx - hw, y0)).vh((z.cx, yt)).hv((z.cx + hw, y0))
    g.stroke(path, pen=pen, k=0.6)


def ring_shape(g, p, z, f=0.85):
    r = min(z.h * 0.5, z.w * 0.32)
    t = max(p.S * f * 0.8, 16)
    t = min(t, r * 0.62)
    ring_circle(g, z.cx, z.y0 + r, r, r - t)


def macron_shape(g, p, z, hw=None, y=None, f=0.9):
    hw = z.w * 0.45 if hw is None else hw
    y = z.ym if y is None else y
    t = p.Hb * f
    g.rect(z.cx - hw, y - t / 2, z.cx + hw, y + t / 2)


def comma_shape(g, p, cx, y_top, size=1.0, turned=False):
    d = mdot(p) * size
    cy = y_top - d / 2
    tmp = Glyph("tmp", p)
    dot(tmp, p, cx, cy, d=d, k=0.66)
    a = (cx + d * 0.18, cy - d * 0.05)
    b = (cx - d * 0.45, cy - d * 1.45)
    tmp.stroke(Path(a, 1.0).C((cx + d * 0.22, cy - d * 0.6), (cx - d * 0.05, cy - d * 1.1), b, 0.5),
               pen=Pen(d * 0.62, d * 0.62))
    if turned:
        tmp.transform(lambda q: (2 * cx - q[0], 2 * (y_top - d * 0.7) - q[1]))
    g.add(tmp.contours)


def arrow_shape(g, p, z, right=True, left=False, f=0.8, hw=None, y=None, harpoon=None):
    """Horizontal arrow (vector accent). harpoon: 'up'/'down' barb only."""
    hw = z.w * 0.55 if hw is None else hw
    y = z.ym if y is None else y
    pen = Pen(p.S * f, p.S * f)
    t = p.S * f
    x0, x1 = z.cx - hw, z.cx + hw
    g.rect(x0 + (t * 0.3 if left else 0), y - t / 2, x1 - (t * 0.3 if right else 0), y + t / 2)
    head = min(z.h * 0.42, hw * 0.55)
    for on, sgn, xe in ((right, 1, x1), (left, -1, x0)):
        if not on:
            continue
        tip = (xe, y)
        if harpoon != "down":
            g.stroke(Path(tip).L((xe - sgn * head, y + head)), pen=pen, start="butt", end="butt")
        if harpoon != "up":
            g.stroke(Path(tip).L((xe - sgn * head, y - head)), pen=pen, start="butt", end="butt")
        dot(g, p, xe - sgn * t * 0.25, y, d=t * 1.05, k=0.6)


# ------------------------------------------------------------------ above
@mark("gravecomb", 0x300)
def gravecomb(g, p, z):
    grave_shape(g, p, z)


@mark("acutecomb", 0x301)
def acutecomb(g, p, z):
    acute_shape(g, p, z)


@mark("uni0340", 0x340)
def gravetone(g, p, z):
    grave_shape(g, p, z)


@mark("uni0341", 0x341)
def acutetone(g, p, z):
    acute_shape(g, p, z)


@mark("circumflexcomb", 0x302)
def circumflexcomb(g, p, z):
    hat(g, p, z, True)


@mark("caroncomb", 0x30C)
def caroncomb(g, p, z):
    hat(g, p, z, False)


@mark("tildecomb", 0x303)
def tildecomb(g, p, z):
    tilde_shape(g, p, z)


@mark("macroncomb", 0x304)
def macroncomb(g, p, z):
    macron_shape(g, p, z)


@mark("uni0305", 0x305, case=False)
def overlinecomb(g, p, z):
    t = p.Hb * 0.9
    g.rect(0, z.ym - t / 2, p.W, z.ym + t / 2)


@mark("uni033F", 0x33F, case=False)
def dbloverlinecomb(g, p, z):
    t = p.Hb * 0.8
    g.rect(0, z.y0, p.W, z.y0 + t)
    g.rect(0, z.y1 - t, p.W, z.y1)


@mark("brevecomb", 0x306)
def brevecomb(g, p, z):
    breve_shape(g, p, z)


@mark("uni0311", 0x311)
def invertedbrevecomb(g, p, z):
    breve_shape(g, p, z, inverted=True)


@mark("dotaccentcomb", 0x307)
def dotaccentcomb(g, p, z):
    d = mdot(p)
    dot(g, p, z.cx, z.y0 + d / 2 + z.h * 0.05, d=d, k=0.66)


@mark("dieresiscomb", 0x308)
def dieresiscomb(g, p, z):
    d = mdot(p)
    o = max(d * 0.85, z.w * 0.3)
    for dx in (-o, o):
        dot(g, p, z.cx + dx, z.y0 + d / 2 + z.h * 0.05, d=d, k=0.66)


@mark("uni0358", 0x358)
def dotaboveright(g, p, z):
    d = mdot(p)
    dot(g, p, z.cx + z.w * 0.6, z.y0 + d / 2 - z.h * 0.3, d=d, k=0.66)


@mark("uni20DB", 0x20DB)
def threedotsabove(g, p, z):
    d = mdot(p) * 0.8
    o = max(d * 1.25, z.w * 0.36)
    for dx in (-o, 0, o):
        dot(g, p, z.cx + dx, z.y0 + d / 2, d=d, k=0.66)


@mark("uni20DC", 0x20DC)
def fourdotsabove(g, p, z):
    d = mdot(p) * 0.7
    o = max(d * 1.2, z.w * 0.26)
    for dx in (-1.5 * o, -0.5 * o, 0.5 * o, 1.5 * o):
        dot(g, p, z.cx + dx, z.y0 + d / 2, d=d, k=0.66)


@mark("hookabovecomb", 0x309)
def hookabovecomb(g, p, z):
    pen = mpen(p, 0.85)
    x0, x1 = z.cx - z.w * 0.25, z.cx + z.w * 0.25
    yt = z.y1 - pen.B
    cx = (x0 + x1) / 2
    r = (x1 - x0) / 2
    path = Path((x0, yt - r * 0.5)).vh((cx, yt)).hv((x1, yt - r * 0.7)).vh((z.cx, z.y0 + z.h * 0.3)).L((z.cx, z.y0))
    g.stroke(path, pen=pen)


@mark("ringcomb", 0x30A)
def ringcomb(g, p, z):
    ring_shape(g, p, z)


@mark("hungarumlautcomb", 0x30B)
def hungarumlautcomb(g, p, z):
    o = z.w * 0.24
    acute_shape(g, p, z, cx=z.cx - o, f=0.82)
    acute_shape(g, p, z, cx=z.cx + o, f=0.82)


@mark("uni030F", 0x30F)
def dblgravecomb(g, p, z):
    o = z.w * 0.24
    grave_shape(g, p, z, cx=z.cx - o, f=0.82)
    grave_shape(g, p, z, cx=z.cx + o, f=0.82)


@mark("uni030D", 0x30D)
def verticallineabove(g, p, z):
    stroke_line(g, p, (z.cx, z.y0), (z.cx, z.y1))


@mark("uni030E", 0x30E)
def dblverticallineabove(g, p, z):
    o = z.w * 0.18
    stroke_line(g, p, (z.cx - o, z.y0), (z.cx - o, z.y1), f=0.82)
    stroke_line(g, p, (z.cx + o, z.y0), (z.cx + o, z.y1), f=0.82)


@mark("uni0310", 0x310)
def candrabinducomb(g, p, z):
    breve_shape(g, p, z, y1=z.y0 + z.h * 0.55)
    d = mdot(p) * 0.85
    dot(g, p, z.cx, z.y1 - d / 2 + z.h * 0.1, d=d, k=0.66)


@mark("uni0312", 0x312)
def turnedcommaabove(g, p, z):
    comma_shape(g, p, z.cx, z.y1, turned=True)


@mark("uni0313", 0x313)
def commaabove(g, p, z):
    comma_shape(g, p, z.cx, z.y1)


@mark("uni0314", 0x314)
def reversedcommaabove(g, p, z):
    tmp = Glyph("tmp", p)
    comma_shape(tmp, p, z.cx, z.y1)
    tmp.transform(lambda q: (2 * z.cx - q[0], q[1]), flip=True)
    g.add(tmp.contours)


@mark("uni0315", 0x315, case=False)
def commaaboveright(g, p, z):
    comma_shape(g, p, z.cx + z.w * 0.75, z.y1 - z.h * 0.15)


@mark("uni031A", 0x31A)
def leftangleabove(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - z.w * 0.3, z.y0, z.cx + z.w * 0.3, z.y0 + t)
    g.rect(z.cx + z.w * 0.3 - t, z.y0, z.cx + z.w * 0.3, z.y1)


@mark("uni033D", 0x33D)
def xabove(g, p, z):
    r = min(z.h, z.w * 0.6) / 2
    pen = mpen(p, 0.8)
    g.stroke(Path((z.cx - r, z.ym - r)).L((z.cx + r, z.ym + r)), pen=pen)
    g.stroke(Path((z.cx - r, z.ym + r)).L((z.cx + r, z.ym - r)), pen=pen)


@mark("uni033E", 0x33E)
def verticaltilde(g, p, z):
    a = z.w * 0.14
    path = (
        Path((z.cx + a * 0.4, z.y1))
        .C((z.cx - a * 1.3, z.y1 - z.h * 0.12), (z.cx - a * 1.3, z.ym + z.h * 0.2), (z.cx, z.ym))
        .C((z.cx + a * 1.3, z.ym - z.h * 0.2), (z.cx + a * 1.3, z.y0 + z.h * 0.12), (z.cx - a * 0.4, z.y0))
    )
    g.stroke(path, pen=mpen(p, 0.85))


@mark("uni0342", 0x342)
def perispomenicomb(g, p, z):
    tilde_shape(g, p, z, hw=z.w * 0.42)


@mark("uni0343", 0x343)
def koroniscomb(g, p, z):
    comma_shape(g, p, z.cx, z.y1)


@mark("uni0344", 0x344)
def dialytikatonoscomb(g, p, z):
    d = mdot(p)
    o = max(d * 0.95, z.w * 0.36)
    for dx in (-o, o):
        dot(g, p, z.cx + dx, z.y0 + d / 2, d=d, k=0.66)
    stroke_line(g, p, (z.cx - z.w * 0.06, z.y0), (z.cx + z.w * 0.12, z.y1 + z.h * 0.1), 0.6, 1.0, f=0.85)


@mark("uni0346", 0x346)
def bridgeabove(g, p, z):
    t = p.S * 0.8
    hw = z.w * 0.38
    g.rect(z.cx - hw, z.y1 - t, z.cx + hw, z.y1)
    g.rect(z.cx - hw, z.y0, z.cx - hw + t, z.y1)
    g.rect(z.cx + hw - t, z.y0, z.cx + hw, z.y1)


@mark("uni034A", 0x34A)
def nottildeabove(g, p, z):
    tilde_shape(g, p, z, hw=z.w * 0.45)
    stroke_line(g, p, (z.cx - z.w * 0.1, z.y0 - z.h * 0.1), (z.cx + z.w * 0.1, z.y1 + z.h * 0.1), f=0.7)


@mark("uni034B", 0x34B)
def homotheticabove(g, p, z):
    tilde_shape(g, p, z, hw=z.w * 0.45, ym=z.y0 + z.h * 0.3, amp=z.h * 0.18)
    tilde_shape(g, p, z, hw=z.w * 0.45, ym=z.y1 - z.h * 0.2, amp=z.h * 0.18)


@mark("uni034C", 0x34C)
def almostequalabove(g, p, z):
    tilde_shape(g, p, z, hw=z.w * 0.45, ym=z.y0 + z.h * 0.25, amp=z.h * 0.16, f=0.75)
    tilde_shape(g, p, z, hw=z.w * 0.45, ym=z.y1 - z.h * 0.2, amp=z.h * 0.16, f=0.75)


@mark("uni0350", 0x350)
def rightarrowheadabove(g, p, z):
    hw = z.w * 0.2
    path = Path((z.cx - hw, z.y1)).L((z.cx + hw, z.ym)).L((z.cx - hw, z.y0))
    g.stroke(path, pen=mpen(p, 0.85))


@mark("uni0351", 0x351)
def lefthalfringabove(g, p, z):
    r = z.h * 0.45
    path = Path((z.cx + r * 0.3, z.y1)).hv((z.cx - r * 0.5, z.ym)).vh((z.cx + r * 0.3, z.y0))
    g.stroke(path, pen=mpen(p, 0.8))


@mark("uni0357", 0x357)
def righthalfringabove(g, p, z):
    r = z.h * 0.45
    path = Path((z.cx - r * 0.3, z.y1)).hv((z.cx + r * 0.5, z.ym)).vh((z.cx - r * 0.3, z.y0))
    g.stroke(path, pen=mpen(p, 0.8))


@mark("uni0352", 0x352)
def fermatacomb(g, p, z):
    breve_shape(g, p, z, inverted=True)
    d = mdot(p) * 0.8
    dot(g, p, z.cx, z.y0 + d / 2, d=d, k=0.66)


@mark("uni035B", 0x35B)
def zigzagabove(g, p, z):
    hw = z.w * 0.45
    path = Path((z.cx - hw, z.y0)).L((z.cx - hw * 0.33, z.y1)).L((z.cx + hw * 0.33, z.y0)).L((z.cx + hw, z.y1))
    g.stroke(path, pen=mpen(p, 0.75))


@mark("uni20D0", 0x20D0)
def leftharpoonabove(g, p, z):
    arrow_shape(g, p, z, right=False, left=True, harpoon="up")


@mark("uni20D1", 0x20D1)
def rightharpoonabove(g, p, z):
    arrow_shape(g, p, z, right=True, harpoon="up")


@mark("uni20D6", 0x20D6)
def leftarrowabove(g, p, z):
    arrow_shape(g, p, z, right=False, left=True)


@mark("uni20D7", 0x20D7)
def rightarrowabove(g, p, z):
    arrow_shape(g, p, z, right=True)


@mark("uni20E1", 0x20E1)
def leftrightarrowabove(g, p, z):
    arrow_shape(g, p, z, right=True, left=True)


@mark("uni20D4", 0x20D4)
def anticlockwisearrowabove(g, p, z):
    breve_shape(g, p, z, inverted=True, f=0.8)
    hw = z.w * 0.4
    pen = mpen(p, 0.8)
    tip = (z.cx - hw, z.y0)
    g.stroke(Path(tip).L((tip[0] - z.h * 0.3, tip[1] + z.h * 0.35)), pen=pen)
    g.stroke(Path(tip).L((tip[0] + z.h * 0.35, tip[1] + z.h * 0.25)), pen=pen)


@mark("uni20D5", 0x20D5)
def clockwisearrowabove(g, p, z):
    breve_shape(g, p, z, inverted=True, f=0.8)
    hw = z.w * 0.4
    pen = mpen(p, 0.8)
    tip = (z.cx + hw, z.y0)
    g.stroke(Path(tip).L((tip[0] + z.h * 0.3, tip[1] + z.h * 0.35)), pen=pen)
    g.stroke(Path(tip).L((tip[0] - z.h * 0.35, tip[1] + z.h * 0.25)), pen=pen)


@mark("uni20E9", 0x20E9, case=False)
def widebridgeabove(g, p, z):
    t = p.S * 0.8
    g.rect(0, z.y1 - t, p.W, z.y1)
    g.rect(0, z.y0, t, z.y1)
    g.rect(p.W - t, z.y0, p.W, z.y1)


@mark("uni20F0", 0x20F0)
def asteriskabove(g, p, z):
    r = z.h * 0.42
    pen = Pen(p.S * 0.7, p.S * 0.7)
    cy = z.ym
    for ang in (90, 210, 330, 270, 30, 150):
        a = math.radians(ang)
        g.stroke(Path((z.cx, cy)).L((z.cx + r * math.cos(a), cy + r * math.sin(a))), pen=pen)


# Latin small letters above (U+0363–036F) are drawn scaled from the letters.
def _letter_above(letter):
    def fn(g, p, z):
        from .scaled import draw_scaled

        f = 0.36 if not z.case else 0.3
        draw_scaled(g, p, letter, 0.45, f, 0.6, dy=z.y0 + 4)

    return fn


for _cp, _l in zip(range(0x363, 0x370), "aeioucdhmrtvx"):
    mark(f"uni{_cp:04X}", _cp)(_letter_above(_l))


# ------------------------------------------------------------------ below
@mark("dotbelowcomb", 0x323, "bottom")
def dotbelowcomb(g, p, z):
    d = mdot(p)
    dot(g, p, z.cx, z.y1 - d / 2, d=d, k=0.66)


@mark("uni0324", 0x324, "bottom")
def dieresisbelowcomb(g, p, z):
    d = mdot(p)
    o = max(d * 0.85, z.w * 0.3)
    for dx in (-o, o):
        dot(g, p, z.cx + dx, z.y1 - d / 2, d=d, k=0.66)


@mark("uni20E8", 0x20E8, "bottom")
def tripleunderdot(g, p, z):
    d = mdot(p) * 0.8
    o = max(d * 1.25, z.w * 0.36)
    for dx in (-o, 0, o):
        dot(g, p, z.cx + dx, z.y1 - d / 2, d=d, k=0.66)


@mark("uni0325", 0x325, "bottom")
def ringbelowcomb(g, p, z):
    r = min(z.h * 0.45, z.w * 0.3)
    t = min(max(p.S * 0.7, 16), r * 0.6)
    ring_circle(g, z.cx, z.y1 - r, r, r - t)


@mark("uni035A", 0x35A, "bottom")
def dblringbelow(g, p, z):
    r = min(z.h * 0.35, z.w * 0.24)
    t = min(max(p.S * 0.6, 14), r * 0.6)
    for dx in (-r * 1.1, r * 1.1):
        ring_circle(g, z.cx + dx, z.y1 - r, r, r - t)


@mark("commaaccentcomb", 0x326, "bottom")
def commaaccentcomb(g, p, z):
    comma_shape(g, p, z.cx, z.y1 + 6)


@mark("cedillacomb", 0x327, "bottom")
def cedillacomb(g, p, z):
    pen = mpen(p, 0.8)
    t = pen.A
    x = z.cx
    stroke_line(g, p, (x, 30), (x, z.y1 - z.h * 0.15), f=0.8)
    hw = z.w * 0.28
    path = (
        Path((x, z.y1 - z.h * 0.15))
        .L((x + hw * 0.2, z.y1 - z.h * 0.15))
        .hv((x + hw, z.ym - z.h * 0.12))
        .vh((x + hw * 0.1, z.y0 - z.h * 0.05))
        .L((x - hw, z.y0 - z.h * 0.05))
    )
    g.stroke(path, pen=pen)


@mark("ogonekcomb", 0x328, "ogonek")
def ogonekcomb(g, p, z):
    pen = mpen(p, 0.85)
    x = z.cx
    r = z.w * 0.3
    path = (
        Path((x, 30))
        .L((x, z.y0 + r + 10))
        .vh((x + r, z.y0 + pen.B))
        .L((x + r * 1.4, z.y0 + pen.B))
    )
    g.stroke(path, pen=pen, end="butt")


@mark("uni0316", 0x316, "bottom")
def gravebelow(g, p, z):
    grave_shape(g, p, z)


@mark("uni0317", 0x317, "bottom")
def acutebelow(g, p, z):
    acute_shape(g, p, z)


@mark("uni032D", 0x32D, "bottom")
def circumflexbelow(g, p, z):
    hat(g, p, z, True)


@mark("uni032C", 0x32C, "bottom")
def caronbelow(g, p, z):
    hat(g, p, z, False)


@mark("uni032E", 0x32E, "bottom")
def brevebelow(g, p, z):
    breve_shape(g, p, z)


@mark("uni032F", 0x32F, "bottom")
def invertedbrevebelow(g, p, z):
    breve_shape(g, p, z, inverted=True)


@mark("uni0330", 0x330, "bottom")
def tildebelow(g, p, z):
    tilde_shape(g, p, z)


@mark("uni0331", 0x331, "bottom")
def macronbelow(g, p, z):
    macron_shape(g, p, z)


@mark("uni0332", 0x332, "bottom")
def lowlinecomb(g, p, z):
    t = p.Hb * 0.9
    g.rect(0, -130, p.W, -130 + t)


@mark("uni0333", 0x333, "bottom")
def dbllowlinecomb(g, p, z):
    t = p.Hb * 0.8
    g.rect(0, -130, p.W, -130 + t)
    g.rect(0, -130 - t * 2, p.W, -130 - t)


@mark("uni0318", 0x318, "bottom")
def lefttackbelow(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - z.w * 0.25, z.ym - t / 2, z.cx + z.w * 0.25, z.ym + t / 2)
    g.rect(z.cx - z.w * 0.25, z.y0, z.cx - z.w * 0.25 + t, z.y1)


@mark("uni0319", 0x319, "bottom")
def righttackbelow(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - z.w * 0.25, z.ym - t / 2, z.cx + z.w * 0.25, z.ym + t / 2)
    g.rect(z.cx + z.w * 0.25 - t, z.y0, z.cx + z.w * 0.25, z.y1)


@mark("uni031D", 0x31D, "bottom")
def uptackbelow(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - z.w * 0.3, z.y0, z.cx + z.w * 0.3, z.y0 + t)
    g.rect(z.cx - t / 2, z.y0, z.cx + t / 2, z.y1)


@mark("uni031E", 0x31E, "bottom")
def downtackbelow(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - z.w * 0.3, z.y1 - t, z.cx + z.w * 0.3, z.y1)
    g.rect(z.cx - t / 2, z.y0, z.cx + t / 2, z.y1)


@mark("uni031F", 0x31F, "bottom")
def plusbelow(g, p, z):
    t = p.S * 0.8
    r = z.h * 0.45
    g.rect(z.cx - r, z.ym - t / 2, z.cx + r, z.ym + t / 2)
    g.rect(z.cx - t / 2, z.ym - r, z.cx + t / 2, z.ym + r)


@mark("uni0320", 0x320, "bottom")
def minusbelow(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - z.h * 0.45, z.ym - t / 2, z.cx + z.h * 0.45, z.ym + t / 2)


@mark("uni0329", 0x329, "bottom")
def verticallinebelow(g, p, z):
    stroke_line(g, p, (z.cx, z.y0), (z.cx, z.y1))


@mark("uni0348", 0x348, "bottom")
def dblverticallinebelow(g, p, z):
    o = z.w * 0.18
    stroke_line(g, p, (z.cx - o, z.y0), (z.cx - o, z.y1), f=0.82)
    stroke_line(g, p, (z.cx + o, z.y0), (z.cx + o, z.y1), f=0.82)


@mark("uni032A", 0x32A, "bottom")
def bridgebelow(g, p, z):
    t = p.S * 0.8
    hw = z.w * 0.38
    g.rect(z.cx - hw, z.y0, z.cx + hw, z.y0 + t)
    g.rect(z.cx - hw, z.y0, z.cx - hw + t, z.y1)
    g.rect(z.cx + hw - t, z.y0, z.cx + hw, z.y1)


@mark("uni033A", 0x33A, "bottom")
def invertedbridgebelow(g, p, z):
    t = p.S * 0.8
    hw = z.w * 0.38
    g.rect(z.cx - hw, z.y1 - t, z.cx + hw, z.y1)
    g.rect(z.cx - hw, z.y0, z.cx - hw + t, z.y1)
    g.rect(z.cx + hw - t, z.y0, z.cx + hw, z.y1)


@mark("uni033B", 0x33B, "bottom")
def squarebelow(g, p, z):
    t = p.S * 0.75
    hw = z.h * 0.45
    g.rect(z.cx - hw, z.ym - hw, z.cx + hw, z.ym + hw)
    g.add(Contour.polygon([(z.cx - hw + t, z.ym - hw + t), (z.cx + hw - t, z.ym - hw + t),
                           (z.cx + hw - t, z.ym + hw - t), (z.cx - hw + t, z.ym + hw - t)]).counterclockwise())


@mark("uni033C", 0x33C, "bottom")
def seagullbelow(g, p, z):
    hw = z.w * 0.4
    pen = mpen(p, 0.75)
    path = Path((z.cx - hw, z.y1)).vh((z.cx - hw / 2, z.y0 + pen.B)).hv((z.cx, z.y1))
    g.stroke(path, pen=pen)
    path = Path((z.cx, z.y1)).vh((z.cx + hw / 2, z.y0 + pen.B)).hv((z.cx + hw, z.y1))
    g.stroke(path, pen=pen)


@mark("uni032B", 0x32B, "bottom")
def invdblarchbelow(g, p, z):
    hw = z.w * 0.4
    pen = mpen(p, 0.75)
    path = Path((z.cx - hw, z.y0)).vh((z.cx - hw / 2, z.y1 - pen.B)).hv((z.cx, z.y0))
    g.stroke(path, pen=pen)
    path = Path((z.cx, z.y0)).vh((z.cx + hw / 2, z.y1 - pen.B)).hv((z.cx + hw, z.y0))
    g.stroke(path, pen=pen)


@mark("uni031C", 0x31C, "bottom")
def lefthalfringbelow(g, p, z):
    r = z.h * 0.45
    path = Path((z.cx + r * 0.3, z.y1)).hv((z.cx - r * 0.5, z.ym)).vh((z.cx + r * 0.3, z.y0))
    g.stroke(path, pen=mpen(p, 0.8))


@mark("uni0339", 0x339, "bottom")
def righthalfringbelow(g, p, z):
    r = z.h * 0.45
    path = Path((z.cx - r * 0.3, z.y1)).hv((z.cx + r * 0.5, z.ym)).vh((z.cx - r * 0.3, z.y0))
    g.stroke(path, pen=mpen(p, 0.8))


@mark("uni0321", 0x321, "bottom")
def palatalizedhookbelow(g, p, z):
    pen = mpen(p, 0.8)
    x = z.cx - z.w * 0.1
    path = Path((x, 40)).L((x, z.ym)).vh((x + z.w * 0.25, z.y0 + pen.B)).L((x + z.w * 0.4, z.y0 + pen.B))
    g.stroke(path, pen=pen)


@mark("uni0322", 0x322, "bottom")
def retroflexhookbelow(g, p, z):
    pen = mpen(p, 0.8)
    x = z.cx + z.w * 0.1
    path = Path((x, 40)).L((x, z.ym)).vh((x + z.w * 0.25, z.y0 + pen.B)).hv((x + z.w * 0.5, z.ym))
    g.stroke(path, pen=pen)


@mark("uni0347", 0x347, "bottom")
def equalbelow(g, p, z):
    t = p.S * 0.7
    hw = z.w * 0.35
    g.rect(z.cx - hw, z.y0 + z.h * 0.15, z.cx + hw, z.y0 + z.h * 0.15 + t)
    g.rect(z.cx - hw, z.y1 - z.h * 0.15 - t, z.cx + hw, z.y1 - z.h * 0.15)


@mark("uni0349", 0x349, "bottom")
def leftanglebelow(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - z.w * 0.3, z.y1 - t, z.cx + z.w * 0.3, z.y1)
    g.rect(z.cx - z.w * 0.3, z.y0, z.cx - z.w * 0.3 + t, z.y1)


@mark("uni034D", 0x34D, "bottom")
def leftrightarrowbelow(g, p, z):
    arrow_shape(g, p, z, right=True, left=True, f=0.75)


@mark("uni034E", 0x34E, "bottom")
def uparrowbelow(g, p, z):
    pen = mpen(p, 0.75)
    g.stroke(Path((z.cx, z.y0)).L((z.cx, z.y1)), pen=pen)
    hh = z.h * 0.4
    g.stroke(Path((z.cx, z.y1)).L((z.cx - hh, z.y1 - hh)), pen=pen)
    g.stroke(Path((z.cx, z.y1)).L((z.cx + hh, z.y1 - hh)), pen=pen)


@mark("uni0353", 0x353, "bottom")
def xbelow(g, p, z):
    r = min(z.h, z.w * 0.6) / 2
    pen = mpen(p, 0.8)
    g.stroke(Path((z.cx - r, z.ym - r)).L((z.cx + r, z.ym + r)), pen=pen)
    g.stroke(Path((z.cx - r, z.ym + r)).L((z.cx + r, z.ym - r)), pen=pen)


@mark("uni0354", 0x354, "bottom")
def leftarrowheadbelow(g, p, z):
    hw = z.w * 0.2
    g.stroke(Path((z.cx + hw, z.y1)).L((z.cx - hw, z.ym)).L((z.cx + hw, z.y0)), pen=mpen(p, 0.85))


@mark("uni0355", 0x355, "bottom")
def rightarrowheadbelow(g, p, z):
    hw = z.w * 0.2
    g.stroke(Path((z.cx - hw, z.y1)).L((z.cx + hw, z.ym)).L((z.cx - hw, z.y0)), pen=mpen(p, 0.85))


@mark("uni0359", 0x359, "bottom")
def asteriskbelow(g, p, z):
    r = z.h * 0.42
    pen = Pen(p.S * 0.7, p.S * 0.7)
    for ang in (90, 210, 330, 270, 30, 150):
        a = math.radians(ang)
        g.stroke(Path((z.cx, z.ym)).L((z.cx + r * math.cos(a), z.ym + r * math.sin(a))), pen=pen)


@mark("uni0345", 0x345, "bottom")
def ypogegrammenicomb(g, p, z):
    pen = mpen(p, 0.8)
    x = z.cx
    path = Path((x, z.y1)).L((x, z.y0 + z.h * 0.3)).vh((x + z.w * 0.18, z.y0 + pen.B))
    g.stroke(path, pen=pen)


@mark("uni20EC", 0x20EC, "bottom")
def rightharpoondownbelow(g, p, z):
    arrow_shape(g, p, z, right=True, harpoon="down")


@mark("uni20ED", 0x20ED, "bottom")
def leftharpoondownbelow(g, p, z):
    arrow_shape(g, p, z, right=False, left=True, harpoon="down")


@mark("uni20EE", 0x20EE, "bottom")
def leftarrowbelow(g, p, z):
    arrow_shape(g, p, z, right=False, left=True)


@mark("uni20EF", 0x20EF, "bottom")
def rightarrowbelow(g, p, z):
    arrow_shape(g, p, z, right=True)


# ------------------------------------------------------------------ overlays
@mark("uni0334", 0x334, "center")
def tildeoverlay(g, p, z):
    tilde_shape(g, p, z, hw=z.w * 0.55, amp=z.h * 0.22)


@mark("uni0335", 0x335, "center")
def shortstrokeoverlay(g, p, z):
    t = p.Hb * 0.9
    hw = (p.R - p.L) * 0.32
    g.rect(z.cx - hw, z.ym - t / 2, z.cx + hw, z.ym + t / 2)


@mark("uni0336", 0x336, "center")
def longstrokeoverlay(g, p, z):
    t = p.Hb * 0.9
    g.rect(0, z.ym - t / 2, p.W, z.ym + t / 2)


@mark("uni0337", 0x337, "center")
def shortsolidusoverlay(g, p, z):
    hw = (p.R - p.L) * 0.28
    g.stroke(Path((z.cx - hw, z.ym - hw * 1.1)).L((z.cx + hw, z.ym + hw * 1.1)), pen=mpen(p, 0.85))


@mark("uni0338", 0x338, "center")
def longsolidusoverlay(g, p, z):
    hw = (p.R - p.L) * 0.36
    hh = p.CAP * 0.5
    g.stroke(Path((z.cx - hw, z.ym - hh)).L((z.cx + hw, z.ym + hh)), pen=mpen(p, 0.85), start=0, end=0)


@mark("uni20D2", 0x20D2, "center")
def longverticallineoverlay(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - t / 2, z.ym - p.CAP * 0.55, z.cx + t / 2, z.ym + p.CAP * 0.55)


@mark("uni20D3", 0x20D3, "center")
def shortverticallineoverlay(g, p, z):
    t = p.S * 0.8
    g.rect(z.cx - t / 2, z.ym - p.XH * 0.4, z.cx + t / 2, z.ym + p.XH * 0.4)


@mark("uni20E5", 0x20E5, "center")
def reversesolidusoverlay(g, p, z):
    hw = (p.R - p.L) * 0.36
    hh = p.CAP * 0.5
    g.stroke(Path((z.cx + hw, z.ym - hh)).L((z.cx - hw, z.ym + hh)), pen=mpen(p, 0.85), start=0, end=0)


@mark("uni20E6", 0x20E6, "center")
def dblverticalstrokeoverlay(g, p, z):
    t = p.S * 0.7
    o = (p.R - p.L) * 0.12
    for dx in (-o, o):
        g.rect(z.cx + dx - t / 2, z.ym - p.CAP * 0.5, z.cx + dx + t / 2, z.ym + p.CAP * 0.5)


@mark("uni20EB", 0x20EB, "center")
def longdblsolidusoverlay(g, p, z):
    hw = (p.R - p.L) * 0.3
    hh = p.CAP * 0.5
    o = (p.R - p.L) * 0.12
    for dx in (-o, o):
        g.stroke(Path((z.cx + dx - hw, z.ym - hh)).L((z.cx + dx + hw, z.ym + hh)), pen=mpen(p, 0.75), start=0, end=0)


@mark("uni20EA", 0x20EA, "center")
def leftarrowoverlay(g, p, z):
    arrow_shape(g, p, z, right=False, left=True, hw=(p.R - p.L) * 0.55, y=z.ym)


@mark("uni20D8", 0x20D8, "center")
def ringoverlay(g, p, z):
    r = z.h * 0.32
    t = min(max(p.S * 0.7, 14), r * 0.6)
    ring_circle(g, z.cx, z.ym, r, r - t)


@mark("uni20D9", 0x20D9, "center")
def clockwiseringoverlay(g, p, z):
    ringoverlay(g, p, z)


@mark("uni20DA", 0x20DA, "center")
def anticlockwiseringoverlay(g, p, z):
    ringoverlay(g, p, z)


# Enclosing marks: centred on the base glyph's centre.
def _enclose_zone(p, z):
    return z.cx, p.XH * 0.5 + 60


@mark("uni20DD", 0x20DD, "center")
def enclosingcircle(g, p, z):
    r = p.W * 0.62
    t = max(p.S * 0.55, 14)
    ring_circle(g, z.cx, z.ym + 60, r, r - t)


@mark("uni20E0", 0x20E0, "center")
def enclosingcirclebackslash(g, p, z):
    enclosingcircle(g, p, z)
    r = p.W * 0.62 * 0.7
    g.stroke(Path((z.cx - r, z.ym + 60 + r)).L((z.cx + r, z.ym + 60 - r)), pen=Pen(max(p.S * 0.55, 14), max(p.S * 0.55, 14)))


@mark("uni20DE", 0x20DE, "center")
def enclosingsquare(g, p, z):
    r = p.W * 0.55
    t = max(p.S * 0.55, 14)
    cy = z.ym + 60
    g.rect(z.cx - r, cy - r, z.cx + r, cy + r)
    g.add(Contour.polygon([(z.cx - r + t, cy - r + t), (z.cx + r - t, cy - r + t), (z.cx + r - t, cy + r - t),
                           (z.cx - r + t, cy + r - t)]).counterclockwise())


@mark("uni20E3", 0x20E3, "center")
def enclosingkeycap(g, p, z):
    enclosingsquare(g, p, z)


@mark("uni20E2", 0x20E2, "center")
def enclosingscreen(g, p, z):
    enclosingsquare(g, p, z)


@mark("uni20DF", 0x20DF, "center")
def enclosingdiamond(g, p, z):
    r = p.W * 0.75
    t = max(p.S * 0.55, 14) * 1.41
    cy = z.ym + 60
    g.poly((z.cx, cy + r), (z.cx + r, cy), (z.cx, cy - r), (z.cx - r, cy))
    g.add(Contour.polygon([(z.cx, cy + r - t), (z.cx + r - t, cy), (z.cx, cy - r + t),
                           (z.cx - r + t, cy)]).counterclockwise())


@mark("uni20E4", 0x20E4, "center")
def enclosingtriangle(g, p, z):
    r = p.W * 0.72
    t = max(p.S * 0.55, 14)
    cy = z.ym + 30
    a, b, c = (z.cx, cy + r), (z.cx + r * 0.95, cy - r * 0.6), (z.cx - r * 0.95, cy - r * 0.6)
    g.poly(a, b, c)
    s = 1 - t * 3.2 / r
    cxm, cym = (a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3
    inner = [(cxm + (q[0] - cxm) * s, cym + (q[1] - cym) * s) for q in (a, b, c)]
    g.add(Contour.polygon(inner).counterclockwise())


@mark("uni20E7", 0x20E7, "center")
def annuitysymbol(g, p, z):
    t = p.S * 0.7
    g.rect(z.cx - p.W * 0.45, p.XH + 60, z.cx + p.W * 0.45, p.XH + 60 + t)
    g.rect(z.cx + p.W * 0.45 - t, -30, z.cx + p.W * 0.45, p.XH + 60 + t)


# ------------------------------------------------------------------ double (span two cells)
@mark("uni035C", 0x35C, "doublebelow")
def dblbrevebelow(g, p, z):
    breve_shape(g, p, z, hw=p.W * 0.62)


@mark("uni035D", 0x35D, "double")
def dblbreve(g, p, z):
    breve_shape(g, p, z, hw=p.W * 0.62)


@mark("uni035E", 0x35E, "double")
def dblmacron(g, p, z):
    macron_shape(g, p, z, hw=p.W * 0.7)


@mark("uni035F", 0x35F, "doublebelow")
def dblmacronbelow(g, p, z):
    macron_shape(g, p, z, hw=p.W * 0.7)


@mark("uni0360", 0x360, "double")
def dbltilde(g, p, z):
    tilde_shape(g, p, z, hw=p.W * 0.68)


@mark("uni0361", 0x361, "double")
def dblinvertedbreve(g, p, z):
    breve_shape(g, p, z, inverted=True, hw=p.W * 0.62)


@mark("uni0362", 0x362, "doublebelow")
def dblrightarrowbelow(g, p, z):
    arrow_shape(g, p, z, right=True, hw=p.W * 0.7)


# ------------------------------------------------------------------ Greek combos (side by side)
def _breathing(g, p, z, cx, rough):
    tmp = Glyph("tmp", p)
    comma_shape(tmp, p, cx, z.y1, size=0.9)
    if rough:
        tmp.transform(lambda q: (2 * cx - q[0], q[1]), flip=True)
    g.add(tmp.contours)


def _greek_combo(rough, accent):
    def fn(g, p, z):
        bx = z.cx - z.w * 0.32
        _breathing(g, p, z, bx, rough)
        z2 = Z(p, z.y0, z.h, z.cx + z.w * 0.28, case=z.case)
        z2.w = z.w * 0.75
        if accent == "oxia":
            acute_shape(g, p, z2, f=0.85)
        elif accent == "varia":
            grave_shape(g, p, z2, f=0.85)
        else:
            z3 = Z(p, z.y0, z.h, z.cx, case=z.case)
            tilde_shape(g, p, z3, hw=z.w * 0.4, ym=z.y1 + z.h * 0.25, amp=z.h * 0.2, f=0.8)
            _breathing(g, p, Z(p, z.y0 - z.h * 0.25, z.h, z.cx, case=z.case), z.cx, rough)
            return
    return fn


GREEK_COMBOS = {}
for _rough, _bn in ((False, "psili"), (True, "dasia")):
    for _acc in ("oxia", "varia", "perispomeni"):
        _nm = f"{_bn}{_acc}comb"
        mark(_nm, None)(_greek_combo(_rough, _acc))
        GREEK_COMBOS[(0x314 if _rough else 0x313, {"oxia": 0x301, "varia": 0x300, "perispomeni": 0x342}[_acc])] = _nm


@mark("dialytikavariacomb", None)
def dialytikavaria(g, p, z):
    d = mdot(p)
    o = max(d * 0.95, z.w * 0.36)
    for dx in (-o, o):
        dot(g, p, z.cx + dx, z.y0 + d / 2, d=d, k=0.66)
    stroke_line(g, p, (z.cx + z.w * 0.06, z.y0), (z.cx - z.w * 0.12, z.y1 + z.h * 0.1), 0.6, 1.0, f=0.85)


@mark("dialytikaperispomenicomb", None)
def dialytikaperispomeni(g, p, z):
    d = mdot(p)
    o = max(d * 0.95, z.w * 0.36)
    for dx in (-o, o):
        dot(g, p, z.cx + dx, z.y0 + d / 2, d=d, k=0.66)
    tilde_shape(g, p, z, hw=z.w * 0.4, ym=z.y1 + z.h * 0.2, amp=z.h * 0.2, f=0.8)


GREEK_COMBOS[(0x308, 0x301)] = "uni0344"
GREEK_COMBOS[(0x308, 0x300)] = "dialytikavariacomb"
GREEK_COMBOS[(0x308, 0x342)] = "dialytikaperispomenicomb"


# Caron for d ď, l ľ, t ť, L Ľ: apostrophe-like at the right of the stem.
@mark("caroncomb.alt", None, "top", case=False)
def caronalt(g, p, z):
    comma_shape(g, p, z.cx, p.ASC + 10, size=0.95)
    g.anchor("_caron", z.cx, p.XH)


@mark("horncomb", 0x31B, "horn", case=False)
def horncomb(g, p, z):
    pen = mpen(p, 0.85)
    x0 = z.cx - p.S * 0.2
    path = Path((x0, p.XH - p.S * 0.9)).L((x0 + p.S * 0.4, p.XH - p.S * 0.9)).hv((z.cx + z.w * 0.32, p.XH + MH * 0.55))
    g.stroke(path, pen=pen, start="butt", end="round")


def _viet(accent):
    def fn(g, p, z):
        hat(g, p, z, True, hw=z.w * 0.36, y1=z.y0 + z.h * (0.8 if not z.case else 0.85))
        z2 = Z(p, z.y0 + z.h * 0.45, z.h * 0.75, z.cx + z.w * 0.55, case=z.case)
        z2.w = z.w * 0.7
        if accent == "acute":
            acute_shape(g, p, z2, f=0.8)
        elif accent == "grave":
            grave_shape(g, p, z2, f=0.8)
        else:
            pen = mpen(p, 0.75)
            x0, x1 = z2.cx - z2.w * 0.2, z2.cx + z2.w * 0.2
            yt = z2.y1 - pen.B
            path = Path((x0, yt - (x1 - x0) * 0.3)).vh(((x0 + x1) / 2, yt)).hv((x1, yt - (x1 - x0) * 0.4)).vh(
                (z2.cx, z2.y0 + z2.h * 0.25))
            g.stroke(path, pen=pen)
    return fn


for _a in ("acute", "grave", "hook"):
    mark(f"circumflex{_a}comb", None)(_viet(_a))
