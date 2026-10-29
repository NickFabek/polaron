"""Other important symbols: currency, keyboard/technical, power, card suits,
music, warning, enclosed alphanumerics."""

from __future__ import annotations

import math

from ..geom import Contour
from ..glyph import REGISTRY, Glyph, glyph, register
from ..stroke import Path, Pen
from .latin_lower import diag_between
from .parts import c_shape, diag, disc, dot, hbar, oval, ring_circle, vstem
from .scaled import derive


def draw(g, p, name, q=None):
    tmp = Glyph("tmp", q or p)
    tmp.adv = g.adv
    REGISTRY[name].fn(tmp, q or p)
    g.add(tmp.contours)
    return tmp


def thin(p, f=0.8):
    return Pen(p.S * f, p.S * f)


# ------------------------------------------------------------------ currency
def letter_with(name, uni, base, extra):
    def fn(g, p):
        draw(g, p, base)
        extra(g, p)

    register(name, fn, uni)


def _bars(ys, x0f=0.08, x1f=0.92, t=0.8):
    def ex(g, p):
        for y in ys:
            hbar(g, p, p.L + (p.R - p.L) * x0f - p.S * 0.3, p.L + (p.R - p.L) * x1f + p.S * 0.3, y(p), sy=p.Hb * t)

    return ex


def _vline(xf=0.5, t=0.75, lo=-100, hi=100):
    def ex(g, p):
        x = p.L + (p.R - p.L) * xf
        vstem(g, p, x, lo, p.CAP + hi, sx=p.S * t)

    return ex


letter_with("uni20A6", 0x20A6, "N", _bars([lambda p: p.CAP * 0.62, lambda p: p.CAP * 0.38]))  # ₦
letter_with("uni20A9", 0x20A9, "W", _bars([lambda p: p.CAP * 0.62, lambda p: p.CAP * 0.4]))  # ₩
letter_with("uni20B1", 0x20B1, "P", _bars([lambda p: p.CAP * 0.82, lambda p: p.CAP * 0.66], 0.0, 1.0))  # ₱
letter_with("uni20B2", 0x20B2, "G", _vline(0.52, 0.7))  # ₲
letter_with("uni20B5", 0x20B5, "C", _vline(0.5, 0.7))  # ₵
letter_with("colonmonetary", 0x20A1, "C", lambda g, p: [g.stroke(Path((p.M - (p.R - p.L) * 0.18 + dx, -100)).L((p.M + (p.R - p.L) * 0.05 + dx, p.CAP + 100)),
                                                                    pen=thin(p, 0.7)) for dx in (-p.S * 0.4, p.S * 0.9)] and None)
letter_with("franc", 0x20A3, "F", _bars([lambda p: p.CAP * 0.22], 0.0, 0.55))
letter_with("uni20AD", 0x20AD, "K", _bars([lambda p: p.CAP * 0.5], 0.0, 0.85))  # ₭
letter_with("uni20AE", 0x20AE, "T", lambda g, p: [g.stroke(Path((p.M - (p.R - p.L) * 0.28, y - 70)).L((p.M + (p.R - p.L) * 0.28, y + 70)), pen=thin(p, 0.75)) for y in (p.CAP * 0.45, p.CAP * 0.25)] and None)
letter_with("uni20B4", 0x20B4, "S", _bars([lambda p: p.CAP * 0.6, lambda p: p.CAP * 0.4]))  # ₴ (approximation)
letter_with("uni20B8", 0x20B8, "T", _bars([lambda p: p.CAP * 0.8], 0.0, 1.0))  # ₸
letter_with("uni20BD", 0x20BD, "P", _bars([lambda p: p.CAP * 0.2], -0.05, 0.6))  # ₽
letter_with("uni20BF", 0x20BF, "B", lambda g, p: [vstem(g, p, p.L + (p.R - p.L) * f, -110, p.CAP + 110, sx=p.S * 0.7) for f in (0.22, 0.48)] and None)
letter_with("lira", 0x20A4, "sterling", _bars([lambda p: p.CAP * 0.3], 0.05, 0.6))


@glyph("uni20B9", 0x20B9)
def rupee(g, p):
    S, Hb = p.S, p.Hb
    x0, x1 = p.L, p.R
    hbar(g, p, x0, x1, p.CAP - Hb / 2)
    hbar(g, p, x0, x1, p.CAP * 0.66, sy=Hb * 0.9)
    xm = x0 + (x1 - x0) * 0.32
    r = p.CAP * 0.2
    path = Path((x0, p.CAP * 0.45)).L((xm, p.CAP * 0.45)).hv((x1 - S * 0.6, p.CAP * 0.66 + 4)).vh((xm, p.CAP - Hb / 2))
    g.stroke(path, pen=Pen(S * 0.92, p.H * 0.92), start="butt", end="butt")
    a, b = diag_between(p, x0 + (x1 - x0) * 0.25, p.CAP * 0.45, x1, 0, 0, -1)
    diag(g, p, a, b, start="butt")


@glyph("uni20AA", 0x20AA)
def sheqel(g, p):
    S = p.S * 0.82
    pen = Pen(S, p.H * 0.82)
    L, R = p.L - p.S * 0.1, p.R + p.S * 0.1
    xl = L + S / 2
    xr = R - S / 2
    xm1 = L + (R - L) * 0.38
    xm2 = L + (R - L) * 0.62
    yt = p.CAP * 0.85
    g.stroke(Path((xl, 0)).L((xl, yt)).L((xm2 - S * 0.5, yt)).hv((xm2, yt - 80)).L((xm2, p.CAP * 0.3)), pen=pen, start=0)
    g.stroke(Path((xr, yt)).L((xr, S / 2)).L((xm1 + S * 0.5, S / 2)).hv((xm1, 80)).L((xm1, p.CAP * 0.55)), pen=pen, start=0)


@glyph("uni20BA", 0x20BA)
def lira_turkish(g, p):
    S = p.S
    xs = p.L + (p.R - p.L) * 0.32
    path = Path((xs, p.CAP)).L((xs, p.H / 2)).L((p.M, p.H / 2)).C((p.R - S * 0.3, p.H / 2), (p.R - S * 0.4, p.CAP * 0.25), (p.R - S * 0.5, p.CAP * 0.5))
    g.stroke(path, start=0, end=0)
    for y in (p.CAP * 0.62, p.CAP * 0.45):
        g.stroke(Path((p.L, y - 60)).L((p.R - S * 0.8, y + 60)), pen=thin(p, 0.8))


@glyph("uni20BC", 0x20BC)
def manat(g, p):
    S, H = p.S, p.H
    xl, xr = p.L + S / 2, p.R - S / 2
    top = p.CAP * 0.8
    r = (xr - xl) / 2
    path = Path((xl, 0)).L((xl, top - r)).vh((p.M, top)).hv((xr, top - r)).L((xr, 0))
    g.stroke(path, start=0, end=0)
    vstem(g, p, p.M, 0, p.CAP, sx=S * 0.8)


@glyph("uni20BE", 0x20BE)
def lari(g, p):
    S = p.S
    te = p.CAP * 0.4
    xl, xr = p.L + S / 2, p.R - S / 2
    yt = p.CAP * 0.82
    path = Path((xr, te)).L((xr, yt * 0.45)).vh((p.M, yt)).hv((xl, yt * 0.45)).L((xl, yt * 0.4)).vh((p.M, p.Hb * 1.5))
    g.stroke(path)
    hbar(g, p, p.L, p.R, p.Hb / 2)
    for f in (0.42, 0.62):
        vstem(g, p, p.L + (p.R - p.L) * f, yt * 0.85, p.CAP, sx=S * 0.7)


@glyph("uni20A8", 0x20A8)
def rupeesign(g, p):
    q = derive(p, 0.56, 1.0, 0.8, cx=p.L + (p.R - p.L) * 0.27)
    draw(g, p, "R", q)
    q2 = derive(p, 0.56, 0.72, 0.8, cx=p.R - (p.R - p.L) * 0.24)
    draw(g, p, "s", q2)


@glyph("peseta", 0x20A7)
def peseta(g, p):
    q = derive(p, 0.56, 1.0, 0.8, cx=p.L + (p.R - p.L) * 0.27)
    draw(g, p, "P", q)
    q2 = derive(p, 0.56, 0.72, 0.8, cx=p.R - (p.R - p.L) * 0.24)
    draw(g, p, "t", q2)


@glyph("uni20AB", 0x20AB)
def dong(g, p):
    draw(g, p, "dcroat")
    hbar(g, p, p.L, p.R, p.DESC * 0.45, sy=p.Hb * 0.85)


@glyph("uni20C0", 0x20C0)
def som(g, p):
    draw(g, p, "C")
    vstem(g, p, p.M, -80, p.CAP * 0.5, sx=p.S * 0.8)


# ------------------------------------------------------------------ keyboard & technical
def keycap_square(g, p, cx, cy, r, t):
    g.rect(cx - r, cy - r, cx + r, cy + r)
    g.add(Contour.polygon([(cx - r + t, cy - r + t), (cx + r - t, cy - r + t), (cx + r - t, cy + r - t),
                           (cx - r + t, cy + r - t)]).counterclockwise())


@glyph("uni2318", 0x2318)
def command(g, p):
    t = p.S * 0.72
    c = (p.M, p.AX + 40)
    a = (p.R - p.L) * 0.17
    lr = (p.R - p.L) * 0.17
    pen = Pen(t, t)
    for sx in (-1, 1):
        g.rect(c[0] - a - t / 2, c[1] + sx * a - t / 2, c[0] + a + t / 2, c[1] + sx * a + t / 2)
        g.rect(c[0] + sx * a - t / 2, c[1] - a - t / 2, c[0] + sx * a + t / 2, c[1] + a + t / 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = c[0] + sx * (a + lr * 0.5 + t * 0.5), c[1] + sy * (a + lr * 0.5 + t * 0.5)
            ring_circle(g, cx, cy, lr * 0.5 + t * 0.5, lr * 0.5 - t * 0.5)


@glyph("uni2325", 0x2325)
def option(g, p):
    t = p.S * 0.85
    y1, y0 = p.CAP * 0.7, p.CAP * 0.15
    xa = p.L + (p.R - p.L) * 0.32
    xb = p.L + (p.R - p.L) * 0.62
    g.rect(p.L - p.S * 0.1, y1 - t / 2, xa, y1 + t / 2)
    g.stroke(Path((xa, y1)).L((xb, y0)), pen=Pen(t, t))
    g.rect(xb - t * 0.1, y0 - t / 2, p.R + p.S * 0.1, y0 + t / 2)
    g.rect(p.L + (p.R - p.L) * 0.62, y1 - t / 2, p.R + p.S * 0.1, y1 + t / 2)


@glyph("uni2303", 0x2303)
def controlup(g, p):
    hw = (p.R - p.L) * 0.38
    g.stroke(Path((p.M - hw, p.CAP * 0.45)).L((p.M, p.CAP * 0.85)).L((p.M + hw, p.CAP * 0.45)), pen=thin(p, 0.9))


@glyph("uni2304", 0x2304)
def controldown(g, p):
    hw = (p.R - p.L) * 0.38
    g.stroke(Path((p.M - hw, p.CAP * 0.45)).L((p.M, p.CAP * 0.05)).L((p.M + hw, p.CAP * 0.45)), pen=thin(p, 0.9))


@glyph("uni238B", 0x238B)
def escape(g, p):
    r = (p.R - p.L) * 0.45
    t = p.S * 0.7
    cy = p.AX + 30
    ring_circle(g, p.M, cy, r, r - t)
    a = r * 0.75
    pen = Pen(t, t)
    g.stroke(Path((p.M - a * 1.25, cy + a * 1.25)).L((p.M + a * 0.1, cy - a * 0.1)), pen=pen)
    g.rect(p.M - a * 1.25 - t / 2, cy + a * 1.25 - t / 2, p.M - a * 0.35, cy + a * 1.25 + t / 2)
    g.rect(p.M - a * 1.25 - t / 2, cy + a * 0.35, p.M - a * 1.25 + t / 2, cy + a * 1.25 + t / 2)


@glyph("uni232B", 0x232B)
def deleteleft(g, p):
    t = p.S * 0.75
    y0, y1 = p.AX - p.CAP * 0.28, p.AX + p.CAP * 0.28
    x0, x1 = p.L - p.S * 0.1, p.R + p.S * 0.1
    xn = x0 + (y1 - y0) * 0.45
    outer = [(x0, p.AX), (xn, y1), (x1, y1), (x1, y0), (xn, y0)]
    g.poly(*outer)
    k = t * 1.0
    inner = [(x0 + k * 1.6, p.AX), (xn + k * 0.55, y1 - k), (x1 - k, y1 - k), (x1 - k, y0 + k), (xn + k * 0.55, y0 + k)]
    g.add(Contour.polygon(inner).counterclockwise())
    cx = (xn + x1) / 2 + k * 0.3
    a = (y1 - y0) * 0.2
    pen = Pen(t * 0.85, t * 0.85)
    g.stroke(Path((cx - a, p.AX - a)).L((cx + a, p.AX + a)), pen=pen)
    g.stroke(Path((cx - a, p.AX + a)).L((cx + a, p.AX - a)), pen=pen)


@glyph("uni2326", 0x2326)
def deleteright(g, p):
    deleteleft(g, p)
    g.mirror_x()


@glyph("uni23CE", 0x23CE)
def returnsym(g, p):
    t = p.S * 0.85
    xr = p.R - t / 2
    y = p.AX - p.CAP * 0.12
    g.rect(xr - t / 2, y, xr + t / 2, p.CAP * 0.85)
    g.rect(p.L + t * 0.4, y - t / 2, xr + t / 2, y + t / 2)
    hh = (p.R - p.L) * 0.24
    x0 = p.L - p.S * 0.05
    g.stroke(Path((x0 + hh, y + hh)).L((x0, y)).L((x0 + hh, y - hh)), pen=Pen(t, t))


@glyph("uni23CF", 0x23CF)
def eject(g, p):
    hw = (p.R - p.L) * 0.45
    g.poly((p.M - hw, p.AX - 10), (p.M, p.CAP * 0.85), (p.M + hw, p.AX - 10))
    g.rect(p.M - hw, 0, p.M + hw, p.Hb * 1.2)


@glyph("uni2324", 0x2324)
def enter_arrowhead(g, p):
    hw = (p.R - p.L) * 0.42
    pen = thin(p, 0.85)
    g.stroke(Path((p.M - hw, p.CAP * 0.5)).L((p.M, p.CAP * 0.85)).L((p.M + hw, p.CAP * 0.5)), pen=pen)
    for y in (p.CAP * 0.35, p.CAP * 0.2):
        hbar(g, p, p.M - hw, p.M + hw, y, sy=p.S * 0.8)


@glyph("uni2300", 0x2300)
def diameter(g, p):
    r = (p.R - p.L) * 0.42
    t = p.S * 0.85
    ring_circle(g, p.M, p.AX, r, r - t)
    g.stroke(Path((p.M - r * 1.15, p.AX - r * 1.15)).L((p.M + r * 1.15, p.AX + r * 1.15)), pen=Pen(t, t))


@glyph("uni2302", 0x2302)
def house(g, p):
    t = p.S * 0.8
    hw = (p.R - p.L) * 0.45
    y0, ym, y1 = 0, p.CAP * 0.45, p.CAP * 0.85
    outer = [(p.M - hw, y0), (p.M - hw, ym), (p.M, y1), (p.M + hw, ym), (p.M + hw, y0)]
    g.poly(*outer)
    k = t
    inner = [(p.M - hw + k, y0 + k), (p.M + hw - k, y0 + k), (p.M + hw - k, ym - k * 0.4), (p.M, y1 - k * 1.4), (p.M - hw + k, ym - k * 0.4)]
    g.add(Contour.polygon(inner).counterclockwise())


@glyph("uni2328", 0x2328)
def keyboard(g, p):
    t = p.S * 0.6
    x0, x1 = p.L - p.S * 0.2, p.R + p.S * 0.2
    y0, y1 = p.AX - p.CAP * 0.26, p.AX + p.CAP * 0.26
    keycap = Contour.polygon([(x0 + t, y0 + t), (x1 - t, y0 + t), (x1 - t, y1 - t), (x0 + t, y1 - t)]).counterclockwise()
    g.rect(x0, y0, x1, y1)
    g.add(keycap)
    d = t * 1.1
    for i in range(4):
        for j in range(2):
            cx = x0 + (x1 - x0) * (0.2 + i * 0.2)
            cy = y0 + (y1 - y0) * (0.62 + j * -0.24) + (0.1 * (y1 - y0) if j == 0 else 0)
            g.rect(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2)
    hbar(g, p, x0 + (x1 - x0) * 0.25, x1 - (x1 - x0) * 0.25, y0 + (y1 - y0) * 0.22, sy=d)


@glyph("uni2387", 0x2387)
def alternative(g, p):
    t = p.S * 0.8
    y = p.CAP * 0.65
    xa = p.L + (p.R - p.L) * 0.35
    g.rect(p.L - p.S * 0.1, y - t / 2, xa, y + t / 2)
    g.stroke(Path((xa, y)).L((p.R - p.S * 0.4, p.CAP * 0.15)), pen=Pen(t, t))
    g.rect(p.L + (p.R - p.L) * 0.6, y - t / 2, p.R + p.S * 0.1, y + t / 2)


@glyph("uni2388", 0x2388)
def helm(g, p):
    r = (p.R - p.L) * 0.3
    t = p.S * 0.7
    ring_circle(g, p.M, p.AX, r, r - t)
    pen = Pen(t, t)
    for k in range(4):
        a = math.radians(45 * k)
        dx, dy = math.cos(a) * r * 1.5, math.sin(a) * r * 1.5
        g.stroke(Path((p.M - dx, p.AX - dy)).L((p.M + dx, p.AX + dy)), pen=pen)


# power symbols (IEC 5009 etc.)
def power_ring(g, p, gap=True):
    r = (p.R - p.L) * 0.42
    t = p.S * 0.85
    cy = p.AX + 20
    pen = Pen(t, t)
    a0 = math.radians(60)
    # open ring as a stroked arc from 60° clockwise to 120°
    pts = []
    n = 6
    span = 2 * math.pi - 2 * math.radians(30) if gap else 2 * math.pi
    start = math.radians(90 + 30) if gap else 0
    path = Path((p.M + r * math.cos(start), cy + r * math.sin(start)))
    k = 4 / 3 * math.tan(span / (4 * n))
    for i in range(n):
        a1 = start + span * i / n
        a2 = start + span * (i + 1) / n
        c1 = (p.M + r * (math.cos(a1) - k * math.sin(a1)), cy + r * (math.sin(a1) + k * math.cos(a1)))
        c2 = (p.M + r * (math.cos(a2) + k * math.sin(a2)), cy + r * (math.sin(a2) - k * math.cos(a2)))
        path.C(c1, c2, (p.M + r * math.cos(a2), cy + r * math.sin(a2)))
    g.stroke(path, pen=pen, start="round", end="round")
    return r, t, cy


@glyph("uni23FB", 0x23FB)
def powersym(g, p):
    r, t, cy = power_ring(g, p)
    g.stroke(Path((p.M, cy + r * 1.15)).L((p.M, cy + r * 0.05)), pen=Pen(t, t), start="round", end="round")


@glyph("uni23FC", 0x23FC)
def poweronoff(g, p):
    r, t, cy = power_ring(g, p, gap=False)
    vstem(g, p, p.M, cy - r * 0.55, cy + r * 1.2, sx=t)


@glyph("uni23FD", 0x23FD)
def poweron(g, p):
    vstem(g, p, p.M, p.AX - (p.R - p.L) * 0.5, p.AX + (p.R - p.L) * 0.6, sx=p.S * 0.85)


@glyph("uni23FE", 0x23FE)
def sleep(g, p):
    r = (p.R - p.L) * 0.45
    cy = p.AX + 20
    disc(g, p.M, cy, r)
    c = Contour((p.M + r * 0.95, cy + r * 0.4), [
        ("C", (p.M + r * 0.25, cy + r * 0.55), (p.M - r * 0.05, cy + r * 0.0), (p.M + r * 0.15, cy - r * 0.55)),
        ("C", (p.M + r * 0.55, cy - r * 0.95), (p.M + r * 1.2, cy - r * 0.3), (p.M + r * 0.95, cy + r * 0.4)),
    ])
    g.add(c.counterclockwise())


# ------------------------------------------------------------------ suits, music, misc
def heart_pts(cx, cy, r):
    return Contour(
        (cx, cy - r * 1.05),
        [
            ("C", (cx - r * 0.55, cy - r * 0.45), (cx - r * 1.05, cy - r * 0.05), (cx - r * 1.0, cy + r * 0.42)),
            ("C", (cx - r * 0.95, cy + r * 0.95), (cx - r * 0.25, cy + r * 1.1), (cx, cy + r * 0.62)),
            ("C", (cx + r * 0.25, cy + r * 1.1), (cx + r * 0.95, cy + r * 0.95), (cx + r * 1.0, cy + r * 0.42)),
            ("C", (cx + r * 1.05, cy - r * 0.05), (cx + r * 0.55, cy - r * 0.45), (cx, cy - r * 1.05)),
        ],
    )


def suit_r(p):
    return (p.R - p.L) * 0.48


@glyph("heart", 0x2665)
def heart(g, p):
    g.add(heart_pts(p.M, p.AX, suit_r(p)).clockwise())


@glyph("uni2661", 0x2661)
def heartwhite(g, p):
    r = suit_r(p)
    g.add(heart_pts(p.M, p.AX, r).clockwise())
    k = r - p.S * 0.8
    g.add(heart_pts(p.M, p.AX + (r - k) * 0.25, k).counterclockwise())


@glyph("spade", 0x2660)
def spade(g, p):
    r = suit_r(p)
    t = heart_pts(p.M, p.AX + r * 0.15, r * 0.92)
    t = t.map(lambda q: (q[0], 2 * (p.AX + r * 0.15) - q[1]))
    g.add(t.clockwise())
    g.poly((p.M - r * 0.45, p.AX - r * 1.05), (p.M, p.AX - r * 0.2), (p.M + r * 0.45, p.AX - r * 1.05))


@glyph("uni2664", 0x2664)
def spadewhite(g, p):
    r = suit_r(p)
    cy = p.AX + r * 0.15
    t = heart_pts(p.M, cy, r * 0.92).map(lambda q: (q[0], 2 * cy - q[1]))
    g.add(t.clockwise())
    k = r * 0.92 - p.S * 0.8
    t2 = heart_pts(p.M, cy - (r * 0.92 - k) * 0.25, k).map(lambda q: (q[0], 2 * cy - q[1]))
    g.add(t2.counterclockwise())
    g.poly((p.M - r * 0.45, p.AX - r * 1.05), (p.M, p.AX - r * 0.6), (p.M + r * 0.45, p.AX - r * 1.05))


@glyph("diamond", 0x2666)
def diamondsuit(g, p):
    r = suit_r(p)
    g.add(Contour((p.M, p.AX + r * 1.15), [
        ("C", (p.M + r * 0.3, p.AX + r * 0.5), (p.M + r * 0.6, p.AX + r * 0.2), (p.M + r * 0.85, p.AX)),
        ("C", (p.M + r * 0.6, p.AX - r * 0.2), (p.M + r * 0.3, p.AX - r * 0.5), (p.M, p.AX - r * 1.15)),
        ("C", (p.M - r * 0.3, p.AX - r * 0.5), (p.M - r * 0.6, p.AX - r * 0.2), (p.M - r * 0.85, p.AX)),
        ("C", (p.M - r * 0.6, p.AX + r * 0.2), (p.M - r * 0.3, p.AX + r * 0.5), (p.M, p.AX + r * 1.15)),
    ]).clockwise())


@glyph("uni2662", 0x2662)
def diamondwhite(g, p):
    r = suit_r(p)
    t = p.S * 0.8
    g.poly((p.M, p.AX + r * 1.15), (p.M + r * 0.85, p.AX), (p.M, p.AX - r * 1.15), (p.M - r * 0.85, p.AX))
    k = 1.0
    g.add(Contour.polygon([(p.M, p.AX + r * 1.15 - t * 1.6), (p.M + r * 0.85 - t * 1.25, p.AX),
                           (p.M, p.AX - r * 1.15 + t * 1.6), (p.M - r * 0.85 + t * 1.25, p.AX)]).counterclockwise())


@glyph("club", 0x2663)
def club(g, p):
    r = suit_r(p) * 0.42
    cy = p.AX + r * 0.4
    disc(g, p.M, cy + r * 1.05, r)
    disc(g, p.M - r * 1.05, cy - r * 0.35, r)
    disc(g, p.M + r * 1.05, cy - r * 0.35, r)
    g.poly((p.M - r * 1.05, cy - r * 2.9), (p.M - r * 0.12, cy), (p.M + r * 0.12, cy), (p.M + r * 1.05, cy - r * 2.9))


@glyph("uni2667", 0x2667)
def clubwhite(g, p):
    r = suit_r(p) * 0.42
    t = min(p.S * 0.7, r * 0.6)
    cy = p.AX + r * 0.4
    for dx, dy in ((0, r * 1.05), (-r * 1.05, -r * 0.35), (r * 1.05, -r * 0.35)):
        ring_circle(g, p.M + dx, cy + dy, r, r - t)
    g.poly((p.M - r * 1.05, cy - r * 2.9), (p.M - t / 2, cy - r * 0.2), (p.M + t / 2, cy - r * 0.2), (p.M + r * 1.05, cy - r * 2.9))


@glyph("musicalnote", 0x266A)
def eighthnote(g, p):
    S = p.S * 0.85
    rx, ry = (p.R - p.L) * 0.24, (p.R - p.L) * 0.17
    cx, cy = p.M - rx * 0.5, p.CAP * 0.15
    head = Contour((cx + rx, cy), [
        ("C", (cx + rx, cy + ry * 0.9), (cx - rx * 0.2, cy + ry * 1.2), (cx - rx, cy + ry * 0.3)),
        ("C", (cx - rx * 1.2, cy - ry * 0.6), (cx + rx * 0.2, cy - ry * 1.3), (cx + rx, cy)),
    ])
    g.add(head.clockwise())
    xs = cx + rx - S / 2
    vstem(g, p, xs, cy, p.CAP, sx=S)
    g.stroke(Path((xs, p.CAP)).C((xs + rx * 0.5, p.CAP * 0.85), (p.R + p.S * 0.1, p.CAP * 0.75), (p.R - rx * 0.2, p.CAP * 0.45)),
             pen=Pen(S, S), start="butt", end="butt")


@glyph("musicalnotedbl", 0x266B)
def beamednotes(g, p):
    S = p.S * 0.75
    rx, ry = (p.R - p.L) * 0.16, (p.R - p.L) * 0.12
    for cx, top in ((p.L + rx * 1.1, p.CAP * 0.92), (p.R - rx * 1.0, p.CAP * 0.98)):
        cy = p.CAP * 0.12
        head = Contour((cx + rx, cy), [
            ("C", (cx + rx, cy + ry * 0.9), (cx - rx * 0.2, cy + ry * 1.2), (cx - rx, cy + ry * 0.3)),
            ("C", (cx - rx * 1.2, cy - ry * 0.6), (cx + rx * 0.2, cy - ry * 1.3), (cx + rx, cy)),
        ])
        g.add(head.clockwise())
        vstem(g, p, cx + rx - S / 2, cy, top, sx=S)
    x0 = p.L + rx * 2.1 - S
    x1 = p.R - S / 2
    g.poly((x0, p.CAP * 0.92), (x0, p.CAP * 0.92 - S * 1.3), (x1, p.CAP * 0.98 - S * 1.3), (x1, p.CAP * 0.98))


@glyph("uni26A0", 0x26A0)
def warning(g, p):
    hw = (p.R - p.L) * 0.55
    t = min(p.S * 0.8, hw * 0.16)
    y0, y1 = -10, p.CAP * 0.92
    g.poly((p.M - hw, y0), (p.M, y1), (p.M + hw, y0))
    k = t * 1.8
    g.add(Contour.polygon([(p.M - hw + k * 1.05, y0 + t), (p.M + hw - k * 1.05, y0 + t), (p.M, y1 - k * 1.25)]).counterclockwise())
    vstem(g, p, p.M, y0 + (y1 - y0) * 0.3, y0 + (y1 - y0) * 0.68, sx=t)
    dot(g, p, p.M, y0 + (y1 - y0) * 0.18, d=t * 1.3)


@glyph("uni26A1", 0x26A1)
def lightning(g, p):
    x0, x1 = p.L, p.R
    g.poly((p.M + (x1 - x0) * 0.15, p.CAP), (x0 + (x1 - x0) * 0.1, p.CAP * 0.42), (p.M + (x1 - x0) * 0.02, p.CAP * 0.42),
           (p.M - (x1 - x0) * 0.15, -60), (x1 - (x1 - x0) * 0.08, p.CAP * 0.55), (p.M + (x1 - x0) * 0.02, p.CAP * 0.55))


@glyph("uni2726", 0x2726)
def fourpointstar(g, p):
    r = (p.R - p.L) * 0.55
    k = r * 0.18
    c = (p.M, p.AX)
    g.poly((c[0], c[1] + r), (c[0] + k, c[1] + k), (c[0] + r, c[1]), (c[0] + k, c[1] - k), (c[0], c[1] - r),
           (c[0] - k, c[1] - k), (c[0] - r, c[1]), (c[0] - k, c[1] + k))


@glyph("uni263A", 0x263A)
def smiley(g, p):
    r = (p.R - p.L) * 0.55
    t = p.S * 0.7
    cy = p.AX + 30
    ring_circle(g, p.M, cy, r, r - t)
    d = t * 1.5
    dot(g, p, p.M - r * 0.35, cy + r * 0.25, d=d)
    dot(g, p, p.M + r * 0.35, cy + r * 0.25, d=d)
    g.stroke(Path((p.M - r * 0.5, cy - r * 0.15)).vh((p.M, cy - r * 0.55)).hv((p.M + r * 0.5, cy - r * 0.15)), pen=Pen(t, t))


@glyph("uni2615", 0x2615)
def hotbeverage(g, p):
    t = p.S * 0.75
    x0, x1 = p.L, p.R - (p.R - p.L) * 0.2
    y0, y1 = 0, p.CAP * 0.5
    r = (x1 - x0) * 0.25
    path = Path((x0 + t / 2, y1)).L((x0 + t / 2, y0 + r)).vh(((x0 + x1) / 2, y0 + t / 2)).hv((x1 - t / 2, y0 + r)).L((x1 - t / 2, y1))
    g.stroke(path, pen=Pen(t, t))
    hbar(g, p, x0, x1, y1 - t / 2, sy=t)
    g.stroke(Path((x1 - t / 2, y1 * 0.8)).L((p.R, y1 * 0.8)).L((p.R, y1 * 0.4)).L((x1 - t / 2, y1 * 0.35)), pen=Pen(t * 0.8, t * 0.8))
    for dx in (-r * 0.6, r * 0.6):
        g.stroke(Path(((x0 + x1) / 2 + dx, y1 + 40)).C(((x0 + x1) / 2 + dx - r * 0.5, y1 + 120), ((x0 + x1) / 2 + dx + r * 0.5, y1 + 200),
                                                         ((x0 + x1) / 2 + dx, p.CAP)), pen=Pen(t * 0.75, t * 0.75))


# ------------------------------------------------------------------ enclosed alphanumerics
def circled(src_names, cps, size=0.5, fill=False, sq=False):
    for name, cp in zip(src_names, cps):
        def fn(g, p, name=name):
            r = min(p.W * 0.48, p.CAP * 0.55)
            t = max(p.S * 0.55, 14)
            cy = p.CAP * 0.45
            if sq:
                g.rect(p.M - r, cy - r, p.M + r, cy + r)
                if not fill:
                    g.add(Contour.polygon([(p.M - r + t, cy - r + t), (p.M + r - t, cy - r + t), (p.M + r - t, cy + r - t),
                                           (p.M - r + t, cy + r - t)]).counterclockwise())
            elif fill:
                disc(g, p.M, cy, r)
            else:
                ring_circle(g, p.M, cy, r, r - t)
            gd = REGISTRY[name]
            q = derive(p, size * 0.9, size * 0.95, 0.62)
            tmp = Glyph("tmp", q)
            tmp.adv = g.adv
            gd.fn(tmp, q)
            hgt = q.CAP if name[0].isupper() or name in DIGITS else q.XH
            tmp.translate(0, cy - hgt / 2)
            if fill:
                for c in tmp.contours:
                    g.add(c.reversed())
            else:
                g.add(tmp.contours)

        register(f"uni{cp:04X}", fn, cp)


DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
circled(DIGITS[1:], range(0x2460, 0x2469))
circled(["zero"], [0x24EA])
circled([chr(c) for c in range(ord("A"), ord("Z") + 1)], range(0x24B6, 0x24D0))
circled([chr(c) for c in range(ord("a"), ord("z") + 1)], range(0x24D0, 0x24EA))
circled([chr(c) for c in range(ord("A"), ord("Z") + 1)], range(0x1F130, 0x1F14A), sq=True)
