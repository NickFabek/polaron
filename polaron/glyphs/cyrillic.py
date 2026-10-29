"""Cyrillic (U+0400–04FF basics + common extended letters).

Lowercase letters that are small-cap shaped are drawn by re-running the
capital's function with the cap height set to the x-height (see scaled.py),
so they keep full stroke weight.
"""

from __future__ import annotations

from ..glyph import Glyph, glyph, register
from ..stroke import Path, Pen
from .latin_lower import arch_top, diag_between, inner_serif, junction, ybot, ytop
from .latin_upper import beak, cbot, ctop, d_bowl, feet, heads
from .parts import arc_h, arch, bowl_side, c_shape, diag, hbar, oval, serif_foot, serif_head, vstem  # noqa: F401
from .scaled import derive

CAP_TO_X = None  # computed per params


def ref(uni, base):
    def fn(g, p):
        g.compose = [base]

    register(f"uni{uni:04X}", fn, uni)


for _u, _b in [
    (0x405, "S"), (0x406, "I"), (0x408, "J"), (0x410, "A"), (0x412, "B"), (0x413, "Gamma"), (0x415, "E"),
    (0x41A, "K"), (0x41C, "M"), (0x41D, "H"), (0x41E, "O"), (0x41F, "Pi"), (0x420, "P"), (0x421, "C"),
    (0x422, "T"), (0x425, "X"), (0x424, "Phi"), (0x4AE, "Y"), (0x4C0, "I"),
    (0x430, "a"), (0x435, "e"), (0x43E, "o"), (0x440, "p"), (0x441, "c"), (0x443, "y"), (0x445, "x"),
    (0x455, "s"), (0x456, "i"), (0x458, "j"), (0x4BB, "h"), (0x4CF, "l"),
]:
    ref(_u, _b)


def anchors(g, p, top=None):
    g.anchor("top", p.M, p.CAP if top is None else top).anchor("bottom", p.M, 0)


def small(cap_fn):
    """Lowercase from a capital drawing function: same strokes, x-height tall."""

    def fn(g, p):
        q = derive(p, 1.0, p.XH / p.CAP, 1.0)
        q.XH = p.XH
        q.ASC = p.ASC
        q.DESC = p.DESC
        tmp = Glyph("tmp", q)
        tmp.adv = g.adv
        cap_fn(tmp, q)
        g.add(tmp.contours)
        g.anchor("top", p.M, p.XH).anchor("bottom", p.M, 0)

    return fn


def descender(g, p, x, w=None):
    """Short descender tail (Ц Щ Д Қ …) below the baseline at x (centre)."""
    S = p.S if w is None else w
    g.rect(x - S / 2, -min(170, -p.DESC * 0.75), x + S / 2, 1)


# ------------------------------------------------------------------ capitals
def Be(g, p):
    S, H, Hb = p.S, p.H, p.Hb
    xs = p.L + S / 2 + S * 0.05
    vstem(g, p, xs, 0, p.CAP)
    hbar(g, p, xs - S / 2, p.R - S * 0.15, p.CAP - Hb / 2)
    d_bowl(g, p, xs, p.R - S / 2, H / 2, p.CAP * 0.56, f=1.0)
    beak(g, p, p.R - S * 0.15, p.CAP - Hb, -1, -1)
    feet(g, p, (xs,), inner=0)
    anchors(g, p)


def De(g, p, top=None):
    S, Hb = p.S, p.Hb
    top = p.CAP if top is None else top
    xr = p.R - S / 2 - S * 0.15
    xl_top = p.L + (p.R - p.L) * 0.28
    vstem(g, p, xr, 0, top)
    hbar(g, p, xl_top - S / 2, xr + S / 2, top - Hb / 2)
    path = Path((xl_top, top - Hb / 2)).L((xl_top, top * 0.45)).C((xl_top, top * 0.15), (p.L + S * 0.6, Hb), (p.L + S * 0.1, Hb))
    g.stroke(path, start="butt", end="butt")
    x0, x1 = p.L - S * 0.15, p.R + S * 0.15
    hbar(g, p, x0, x1, Hb / 2)
    for x in (x0 + S * 0.45, x1 - S * 0.45):
        g.rect(x - S * 0.45, -min(170, -p.DESC * 0.75), x + S * 0.45, Hb)
    anchors(g, p)


def Zhe(g, p):
    S = p.S
    f = 0.78
    pen = Pen(S * f, p.H * f)
    vstem(g, p, p.M, 0, p.CAP, sx=S * f)
    L, R = p.L - S * 0.15, p.R + S * 0.15
    ym = p.CAP * 0.46
    for side in (-1, 1):
        xe = L if side < 0 else R
        a, b = diag_between(p, xe, p.CAP, p.M + side * S * 0.3, ym, -side, 0, w=f)
        g.stroke(Path(a).L(b), pen=pen, start=0, end="butt")
        c, d = diag_between(p, p.M + side * S * 0.45, ym + S * 0.2, xe, 0, 0, -side, w=f)
        g.stroke(Path(c).L(d), pen=pen, start="butt", end=0)
    anchors(g, p)


def Ze(g, p):
    from .digits import three

    three(g, p)
    anchors(g, p)


def I_(g, p, top=None):
    S = p.S
    top = p.CAP if top is None else top
    xl, xr = p.L + S / 2, p.R - S / 2
    sn = S * (0.95 if p.sans else 0.75)
    vstem(g, p, xl, 0, top, sx=sn)
    vstem(g, p, xr, 0, top, sx=sn)
    a, b = diag_between(p, p.L, 0, p.R, top, 1, -1, w=0.92)
    diag(g, p, a, b, w=0.92)
    if p.serif:
        inner = inner_serif(p, p.R - p.L - 2 * S)
        for x in (xl, xr):
            serif_foot(g, p, x, 0, sx=sn, ll=inner if x > p.M else None, rl=inner if x < p.M else None)
            serif_foot(g, p, x, top, sx=sn, down=True, ll=inner if x > p.M else None, rl=inner if x < p.M else None)
    anchors(g, p, top)


def El(g, p):
    S, Hb = p.S, p.Hb
    xr = p.R - S / 2
    vstem(g, p, xr, 0, p.CAP)
    xl = p.L + (p.R - p.L) * 0.22
    hbar(g, p, xl - S / 2, xr, p.CAP - Hb / 2)
    path = Path((xl, p.CAP - Hb / 2)).L((xl, p.CAP * 0.4)).C((xl, p.CAP * 0.1), (p.L + S * 0.6, Hb * 0.5), (p.L - S * 0.1, Hb * 0.5))
    g.stroke(path, start="butt", end="butt")
    serif_foot(g, p, xr, 0, ll=p.SL * 0.5)
    anchors(g, p)


def U_(g, p):
    S = p.S
    a, b = diag_between(p, p.R, p.CAP, p.L + S * 0.25, 0, -1, 1)
    diag(g, p, a, b)
    t = 0.62
    m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    c, d = diag_between(p, p.L, p.CAP, m[0], m[1], 1, 0, w=1.0 if p.sans else 0.62)
    diag(g, p, c, m, w=1.0 if p.sans else 0.62, end="butt")
    anchors(g, p)


def Tse(g, p, top=None):
    S, Hb = p.S, p.Hb
    top = p.CAP if top is None else top
    xl, xr = p.L + S / 2, p.R - S / 2 - S * 0.25
    vstem(g, p, xl, 0, top)
    vstem(g, p, xr, 0, top)
    hbar(g, p, xl - S / 2, p.R + S * 0.1, Hb / 2)
    g.rect(p.R + S * 0.1 - S * 0.9, -min(170, -p.DESC * 0.75), p.R + S * 0.1, Hb)
    anchors(g, p, top)


def Che(g, p, top=None):
    S, H = p.S, p.H
    top = p.CAP if top is None else top
    xl, xr = p.L + S / 2, p.R - S / 2
    vstem(g, p, xr, 0, top)
    ym = top * 0.42
    cx = (xl + xr) / 2
    r = (top * 0.5 - ym) + 40
    path = Path((xl, top)).L((xl, ym + H / 2 + r)).vh((cx, ym + H / 2)).L((xr, ym + H / 2))
    g.stroke(path)
    anchors(g, p, top)


def Sha(g, p, top=None, tail=False):
    S = p.S
    top = p.CAP if top is None else top
    sm = min(S * 0.92, (p.R - p.L) * 0.24)
    L, R = p.L - S * 0.12, p.R + S * 0.12 - (S * 0.25 if tail else 0)
    for x in (L + sm / 2, (L + R) / 2, R - sm / 2):
        vstem(g, p, x, 0, top, sx=sm)
    hbar(g, p, L, R + (S * 0.3 if tail else 0), p.Hb * 0.5)
    if tail:
        g.rect(R + S * 0.3 - sm, -min(170, -p.DESC * 0.75), R + S * 0.3, p.Hb)
    anchors(g, p, top)


def soft_bowl(g, p, xs, x1, top_bowl, H=None):
    S = p.S
    H = p.H if H is None else H
    d_bowl(g, p, xs, x1 - S / 2, H / 2, top_bowl, f=1.0)


def Soft(g, p, top=None):
    S = p.S
    top = p.CAP if top is None else top
    xs = p.L + S / 2 + S * 0.15
    vstem(g, p, xs, 0, top)
    soft_bowl(g, p, xs, p.R, top * 0.56)
    anchors(g, p, top)


def Hard(g, p, top=None):
    S, Hb = p.S, p.Hb
    top = p.CAP if top is None else top
    xs = p.L + S / 2 + (p.R - p.L) * 0.2
    vstem(g, p, xs, 0, top)
    hbar(g, p, p.L - S * 0.15, xs, top - Hb / 2)
    soft_bowl(g, p, xs, p.R + S * 0.1, top * 0.54)
    anchors(g, p, top)


def Yeru(g, p, top=None):
    S = p.S
    top = p.CAP if top is None else top
    sm = S * 0.88
    xs = p.L + sm / 2 - S * 0.05
    vstem(g, p, xs, 0, top, sx=sm)
    xr = p.R - sm / 2 + S * 0.1
    vstem(g, p, xr, 0, top, sx=sm)
    d_bowl_thin(g, p, xs, xr - sm / 2 - (p.R - p.L) * 0.1, top * 0.54, sm)
    anchors(g, p, top)


def d_bowl_thin(g, p, xs, xr_outer, top_bowl, sm):
    H = p.H * sm / p.S
    pen = Pen(sm, H)
    xr = xr_outer - sm / 2
    yb, yt = H / 2, top_bowl
    xm = xs + (xr - xs) * 0.45
    ry = arc_h(p, xr - xm, (yt - yb) / 2, f=1.0)
    path = Path((xs, yt)).L((xm, yt)).hv((xr, yt - ry)).L((xr, yb + ry)).vh((xm, yb)).L((xs, yb))
    g.stroke(path, pen=pen)


def E_rev(g, p, top=None):
    S = p.S
    top = p.CAP if top is None else top
    tmp = Glyph("tmp", p)
    te, be = top * 0.74, top * 0.25
    c_shape(tmp, p, p.L + S * 0.05, p.R, -p.OV, top + p.OV, te, be)
    tmp.mirror_x()
    g.add(tmp.contours)
    hbar(g, p, p.L + (p.R - p.L) * 0.3, p.R - S / 2, top / 2)
    anchors(g, p, top)


def Ye(g, p, top=None):
    S = p.S
    top = p.CAP if top is None else top
    te, be = top * 0.74, top * 0.25
    c_shape(g, p, p.L, p.R - S * 0.05, -p.OV, top + p.OV, te, be)
    hbar(g, p, p.L + S / 2, p.R - (p.R - p.L) * 0.3, top / 2)
    anchors(g, p, top)


def Yu(g, p, top=None):
    S = p.S
    top = p.CAP if top is None else top
    sm = S * 0.85
    xs = p.L + sm / 2 - S * 0.1
    vstem(g, p, xs, 0, top, sx=sm)
    hbar(g, p, xs, p.L + (p.R - p.L) * 0.38, top / 2, sy=p.Hb * 0.9)
    oval(g, p, p.L + (p.R - p.L) * 0.32, p.R + S * 0.12, -p.OV, top + p.OV, sx=sm, sy=p.H * 0.9)
    anchors(g, p, top)


def Ya(g, p, top=None):
    S, H = p.S, p.H
    top = p.CAP if top is None else top
    xs = p.R - S / 2 - S * 0.05
    vstem(g, p, xs, 0, top)
    yb = top * 0.45
    tmp = Glyph("tmp", p)
    d_bowl(tmp, p, p.W - xs, p.W - (p.L + S / 2 + S * 0.1), yb, top - H / 2, f=1.0)
    tmp.mirror_x()
    g.add(tmp.contours)
    a, b = diag_between(p, p.M + S * 0.1, yb, p.L, 0, 0, 1)
    diag(g, p, a, b, start="butt")
    anchors(g, p, top)


def Dje(g, p, top=None, hook=True):
    S, H, Hb = p.S, p.H, p.Hb
    top = p.CAP if top is None else top
    xs = p.L + S / 2 + (p.R - p.L) * 0.18
    vstem(g, p, xs, 0, top)
    hbar(g, p, p.L - S * 0.1, p.R - (p.R - p.L) * 0.1, top - Hb / 2)
    xr = p.R - S / 2
    ya = top * 0.55
    if hook:
        path = (
            Path((xs, ya - 30), 0.45)
            .vh(((xs + xr) / 2, ya))
            .hv((xr, ya - (ya * 0.4)))
            .L((xr, 40))
            .C((xr, -60), (xr - S, -120), (p.M, -130))
        )
        g.stroke(path, end="butt")
    else:
        path = Path((xs, ya - 30), 0.45).vh(((xs + xr) / 2, ya)).hv((xr, ya - (ya * 0.4))).L((xr, 0))
        g.stroke(path, end=0)
    anchors(g, p, top)


def Lje(g, p, top=None):
    S, Hb = p.S, p.Hb
    top = p.CAP if top is None else top
    sm = S * 0.82
    pen = Pen(sm, p.H * 0.82)
    L, R = p.L - S * 0.2, p.R + S * 0.2
    xm = L + (R - L) * 0.52
    vstem(g, p, xm, 0, top, sx=sm)
    xl = L + (R - L) * 0.16
    hbar(g, p, xl - sm / 2, xm, top - Hb / 2, sy=Hb * 0.9)
    path = Path((xl, top - Hb / 2)).L((xl, top * 0.4)).C((xl, top * 0.1), (L + sm * 0.5, Hb * 0.5), (L - sm * 0.1, Hb * 0.5))
    g.stroke(path, pen=pen, start="butt", end="butt")
    d_bowl_thin(g, p, xm, R, top * 0.54, sm)
    anchors(g, p, top)


def Nje(g, p, top=None):
    S = p.S
    top = p.CAP if top is None else top
    sm = S * 0.82
    L, R = p.L - S * 0.2, p.R + S * 0.2
    xl = L + sm / 2
    xm = L + (R - L) * 0.52
    vstem(g, p, xl, 0, top, sx=sm)
    vstem(g, p, xm, 0, top, sx=sm)
    hbar(g, p, xl, xm, top * 0.52, sy=p.Hb * 0.9)
    d_bowl_thin(g, p, xm, R, top * 0.54, sm)
    anchors(g, p, top)


def Dzhe(g, p, top=None):
    S, Hb = p.S, p.Hb
    top = p.CAP if top is None else top
    xl, xr = p.L + S / 2, p.R - S / 2
    vstem(g, p, xl, 0, top)
    vstem(g, p, xr, 0, top)
    hbar(g, p, xl - S / 2, xr + S / 2, Hb / 2)
    vstem(g, p, p.M, -min(170, -p.DESC * 0.75), Hb, sx=S * 0.9)
    anchors(g, p, top)


def Ghe_up(g, p, top=None):
    from .greek import gamma_body

    top = p.CAP if top is None else top
    gamma_body(g, p, top)
    S = p.S
    g.rect(p.R - S * 0.05 - S * 0.9, top - p.Hb, p.R - S * 0.05, top + min(150, (p.BT - top) * 0.9))
    anchors(g, p, top)


def Ghe_bar(g, p, top=None):
    from .greek import gamma_body

    top = p.CAP if top is None else top
    gamma_body(g, p, top)
    S = p.S
    xs = p.L + S / 2 + S * 0.25
    hbar(g, p, p.L - S * 0.1, xs + (p.R - p.L) * 0.32, top * 0.47, sy=p.Hb * 0.9)
    anchors(g, p, top)


def with_tail(fn, x_of):
    """Add a descender tail at the right end (Җ Қ Ң Ҷ Ҳ)."""

    def g2(g, p, top=None):
        fn(g, p)
        S = p.S
        x = x_of(p)
        g.rect(x - S * 0.9, -min(170, -p.DESC * 0.75), x, p.Hb)
        hbar(g, p, x - S * 1.2, x, p.Hb / 2)

    return g2


def Ka(g, p):
    from .latin_upper import K

    K(g, p)


def En(g, p):
    from .latin_upper import H

    H(g, p)


def Ha(g, p):
    from .latin_upper import X

    X(g, p)


def Ustraight_bar(g, p):
    from .latin_upper import Y

    Y(g, p)
    hw = (p.R - p.L) * 0.36
    hbar(g, p, p.M - hw, p.M + hw, p.CAP * 0.3, sy=p.Hb * 0.9)


def Shha(g, p, top=None):
    S, H = p.S, p.H
    top = p.CAP if top is None else top
    xs = p.L + S / 2
    vstem(g, p, xs, 0, top)
    arch(g, p, xs, p.R, top * 0.6 + p.OV * 0.5, 0, top * 0.3)
    anchors(g, p, top)


def Schwa(g, p, top=None):
    from .latin_lower import e as draw_e

    top = p.CAP if top is None else top
    q = derive(p, 1.0, top / p.XH, 1.0)
    tmp = Glyph("tmp", q)
    tmp.adv = g.adv
    draw_e(tmp, q)
    W = p.W
    tmp.transform(lambda pt: (W - pt[0], top - pt[1]))
    g.add(tmp.contours)
    anchors(g, p, top)


def Obar(g, p, top=None):
    top = p.CAP if top is None else top
    oval(g, p, p.L, p.R, -p.OV, top + p.OV)
    hbar(g, p, p.L + p.S / 2, p.R - p.S / 2, top / 2)
    anchors(g, p, top)


def Yat(g, p, top=None):
    S, Hb = p.S, p.Hb
    top = p.CAP if top is None else top
    xs = p.L + S / 2 + (p.R - p.L) * 0.12
    vstem(g, p, xs, 0, top * 1.08 if top == p.CAP else top + (p.ASC - p.XH))
    hbar(g, p, p.L - S * 0.1, xs + (p.R - p.L) * 0.38, top * 0.8, sy=Hb * 0.9)
    soft_bowl(g, p, xs, p.R + S * 0.05, top * 0.54)
    anchors(g, p, top)


CAPS = {
    0x411: Be, 0x414: De, 0x416: Zhe, 0x417: Ze, 0x418: I_, 0x41B: El, 0x423: U_, 0x426: Tse, 0x427: Che,
    0x428: Sha, 0x429: lambda g, p, top=None: Sha(g, p, top, tail=True), 0x42A: Hard, 0x42B: Yeru,
    0x42C: Soft, 0x42D: E_rev, 0x42E: Yu, 0x42F: Ya, 0x402: Dje, 0x404: Ye, 0x409: Lje, 0x40A: Nje,
    0x40B: lambda g, p, top=None: Dje(g, p, top, hook=False), 0x40F: Dzhe, 0x490: Ghe_up, 0x492: Ghe_bar,
    0x496: with_tail(Zhe, lambda p: p.R + p.S * 0.35), 0x49A: with_tail(Ka, lambda p: p.R + p.S * 0.3),
    0x4A2: with_tail(En, lambda p: p.R + p.S * 0.3), 0x4B6: with_tail(Che, lambda p: p.R + p.S * 0.3),
    0x4B2: with_tail(Ha, lambda p: p.R + p.S * 0.3), 0x4B0: Ustraight_bar, 0x4BA: Shha, 0x4D8: Schwa,
    0x4E8: Obar, 0x462: Yat,
}

for _u, _fn in CAPS.items():
    register(f"uni{_u:04X}", (lambda f: (lambda g, p: f(g, p)))(_fn), _u)

# lowercase as small caps
SMALL = {
    0x431: None, 0x432: 0x412, 0x433: 0x413, 0x434: 0x414, 0x436: 0x416, 0x437: 0x417, 0x438: 0x418,
    0x43A: 0x41A, 0x43B: 0x41B, 0x43C: 0x41C, 0x43D: 0x41D, 0x43F: 0x41F, 0x442: 0x422, 0x446: 0x426,
    0x447: 0x427, 0x448: 0x428, 0x449: 0x429, 0x44A: 0x42A, 0x44B: 0x42B, 0x44C: 0x42C, 0x44D: 0x42D,
    0x44E: 0x42E, 0x44F: 0x42F, 0x454: 0x404, 0x459: 0x409, 0x45A: 0x40A, 0x45F: 0x40F, 0x491: 0x490,
    0x493: 0x492, 0x497: 0x496, 0x49B: 0x49A, 0x4A3: 0x4A2, 0x4B7: 0x4B6, 0x4B3: 0x4B2, 0x4D9: 0x4D8,
    0x4E9: 0x4E8,
}


def _cap_fn(u):
    from ..glyph import REGISTRY

    name = f"uni{u:04X}"
    if u in CAPS:
        return CAPS[u]
    base = {0x412: "B", 0x413: "Gamma", 0x41A: "K", 0x41C: "M", 0x41D: "H", 0x41F: "Pi", 0x422: "T"}[u]
    return lambda g, p: REGISTRY[base].fn(g, p)


for _l, _c in SMALL.items():
    if _c is None:
        continue
    register(f"uni{_l:04X}", small(_cap_fn(_c)), _l)


@glyph("uni0431", 0x431)
def be(g, p):
    S, H = p.S, p.H
    oval(g, p, p.L, p.R, ybot(p), ytop(p) + p.XH * 0.04)
    xl = p.L + S / 2
    yt = p.ASC + p.OV * 0.3 - H / 2
    path = Path((xl, p.XH * 0.5)).L((xl, p.XH * 0.95)).C((xl, yt - 70), (p.M - S * 0.5, yt), (p.M + S * 0.2, yt))
    path.L((p.R - S * 0.2, yt))
    g.stroke(path, end="butt")
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


@glyph("uni0444", 0x444)
def ef(g, p):
    oval(g, p, p.L - p.S * 0.1, p.R + p.S * 0.1, ybot(p), ytop(p), sx=p.S * 0.88, sy=p.H * 0.9)
    vstem(g, p, p.M, p.DESC, p.ASC)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, p.DESC)


@glyph("uni0452", 0x452)
def dje(g, p):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2
    vstem(g, p, xs, 0, p.ASC)
    hbar(g, p, p.L - S * 0.1, p.M + S * 0.4, p.ASC - (p.ASC - p.XH) * 0.45, sy=Hb * 0.9)
    xr = p.R - S / 2
    path = (
        Path((xs, junction(p)), 0.42)
        .vh(((xs + xr) / 2 + S * 0.12, arch_top(p) - p.H / 2))
        .hv((xr, p.XH * 0.55))
        .L((xr, 20))
        .C((xr, p.DESC * 0.4), (xr - S, p.DESC * 0.75), (p.M, p.DESC * 0.8))
    )
    g.stroke(path, end="butt")
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


@glyph("uni045B", 0x45B)
def tshe(g, p):
    from .latin_lower import n_body

    n_body(g, p, p.ASC)
    hbar(g, p, p.L - p.S * 0.1, p.M + p.S * 0.4, p.ASC - (p.ASC - p.XH) * 0.45, sy=p.Hb * 0.9)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


@glyph("uni04AF", 0x4AF)
def ustraight(g, p):
    from .latin_lower import v as draw_v

    tmp = Glyph("tmp", p)
    draw_v(tmp, p)
    g.add(tmp.contours)
    vstem(g, p, p.M, p.DESC, p.S * 0.2)
    g.anchor("top", p.M, p.XH).anchor("bottom", p.M, p.DESC)


@glyph("uni04B1", 0x4B1)
def ustraightbar(g, p):
    ustraight(g, p)
    hw = (p.R - p.L) * 0.3
    hbar(g, p, p.M - hw, p.M + hw, -p.DESC * -0.0 - 60, sy=p.Hb * 0.9)


@glyph("uni0463", 0x463)
def yat(g, p):
    S, Hb = p.S, p.Hb
    xs = p.L + S / 2 + (p.R - p.L) * 0.12
    vstem(g, p, xs, 0, p.ASC)
    hbar(g, p, p.L - S * 0.1, xs + (p.R - p.L) * 0.38, p.XH * 1.0, sy=Hb * 0.9)
    soft_bowl(g, p, xs, p.R + S * 0.05, p.XH * 0.58)
    g.anchor("top", p.M, p.ASC).anchor("bottom", p.M, 0)


# ------------------------------------------------------------------ italic forms
def _italic_override(uni, latin_name):
    """In italics some Cyrillic lowercase letters take cursive shapes
    (Russian conventions): \u0438 -> u, \u0442 -> m, \u043f -> n, \u0434 -> g."""
    from ..glyph import REGISTRY

    gd = REGISTRY[f"uni{uni:04X}"]
    upright = gd.fn

    def fn(g, p):
        if p.italic:
            REGISTRY[latin_name].fn(g, p)
        else:
            upright(g, p)

    gd.fn = fn


for _u, _l in ((0x438, "u"), (0x442, "m"), (0x43F, "n"), (0x434, "g")):
    _italic_override(_u, _l)


# ------------------------------------------------------------------ serif style for Cyrillic capitals
def _stem_serifs(spec):
    """spec(p, top) -> list of (x, head, foot) for stems that get serifs."""

    def wrap(fn):
        def g2(g, p, top=None):
            fn(g, p) if top is None else fn(g, p, top)
            if not p.serif:
                return
            t = p.CAP if top is None else top
            inner = inner_serif(p, (p.R - p.L) * 0.5 - p.S)
            for x, head, foot in spec(p):
                ll = inner if x > p.M else None
                rl = inner if x < p.M else None
                if head:
                    serif_foot(g, p, x, t, down=True, ll=ll, rl=rl)
                if foot:
                    serif_foot(g, p, x, 0, ll=ll, rl=rl)

        return g2

    return wrap


_SERIFS = {
    0x411: lambda p: [(p.L + p.S / 2 + p.S * 0.05, False, True)],
    0x416: lambda p: [(p.M, True, True)],
    0x426: lambda p: [(p.L + p.S / 2, True, False), (p.R - p.S / 2 - p.S * 0.25, True, False)],
    0x427: lambda p: [(p.L + p.S / 2, True, False), (p.R - p.S / 2, True, True)],
    0x428: lambda p: [(p.L - p.S * 0.12 + min(p.S * 0.92, (p.R - p.L) * 0.24) / 2, True, False),
                      (p.M, True, False), (p.R + p.S * 0.12 - min(p.S * 0.92, (p.R - p.L) * 0.24) / 2, True, False)],
    0x42C: lambda p: [(p.L + p.S / 2 + p.S * 0.15, True, False)],
    0x42B: lambda p: [(p.L + p.S * 0.44 - p.S * 0.05, True, False), (p.R - p.S * 0.44 + p.S * 0.1, True, True)],
    0x42E: lambda p: [(p.L + p.S * 0.425 - p.S * 0.1, True, True)],
    0x42F: lambda p: [(p.R - p.S / 2 - p.S * 0.05, True, True)],
    0x41B: lambda p: [(p.R - p.S / 2, True, False)],
    0x40F: lambda p: [(p.L + p.S / 2, True, False), (p.R - p.S / 2, True, False)],
    0x40A: lambda p: [(p.L - p.S * 0.2 + p.S * 0.41, True, True)],
}

for _u, _spec in _SERIFS.items():
    from ..glyph import REGISTRY as _R

    _gd = _R[f"uni{_u:04X}"]
    _base = CAPS[_u]
    _new = _stem_serifs(_spec)(_base)
    CAPS[_u] = _new
    _gd.fn = (lambda f: (lambda g, p: f(g, p)))(_new)
    # small-cap lowercase follow the capital
    for _l, _c in SMALL.items():
        if _c == _u:
            _R[f"uni{_l:04X}"].fn = small(_new)
