"""Spacing accents (` ´ ¨ ¸ ˆ ˇ …) and Spacing Modifier Letters U+02B0–02FF."""

from __future__ import annotations

from ..glyph import REGISTRY, Glyph, register
from ..stroke import Path, Pen
from . import marks as M
from .parts import dot, hbar, vstem
from .scaled import draw_scaled


def zone_top(p):
    return M.Z(p, p.CAP - 70, M.MH, p.M)


def zone_low(p):
    return M.Z(p, -M.GAP_B - M.MH_B, M.MH_B, p.M, below=True)


def spacing(name, uni, fn, low=False):
    def full(g, p):
        z = zone_low(p) if low else zone_top(p)
        fn(g, p, z)

    register(name, full, uni)


for _n, _u, _f in [
    ("grave", 0x60, M.gravecomb), ("acute", 0xB4, M.acutecomb), ("dieresis", 0xA8, M.dieresiscomb),
    ("circumflex", 0x2C6, M.circumflexcomb), ("caron", 0x2C7, M.caroncomb), ("breve", 0x2D8, M.brevecomb),
    ("dotaccent", 0x2D9, M.dotaccentcomb), ("ring", 0x2DA, M.ringcomb), ("tilde", 0x2DC, M.tildecomb),
    ("hungarumlaut", 0x2DD, M.hungarumlautcomb), ("uni02C9", 0x2C9, M.macroncomb),
    ("uni02CA", 0x2CA, M.acutecomb), ("uni02CB", 0x2CB, M.gravecomb), ("uni02D8.alt", None, M.brevecomb),
    ("uni1FBF", 0x1FBF, M.commaabove), ("uni1FFE", 0x1FFE, M.reversedcommaabove), ("uni1FC0", 0x1FC0, M.perispomenicomb),
    ("uni1FED", 0x1FED, M.dialytikavaria), ("uni1FEE", 0x1FEE, M.dialytikatonoscomb),
    ("uni1FC1", 0x1FC1, M.dialytikaperispomeni),
]:
    spacing(_n, _u, _f)

for _n, _u, _f in [
    ("cedilla", 0xB8, M.cedillacomb), ("ogonek", 0x2DB, M.ogonekcomb), ("uni02CD", 0x2CD, M.macronbelow),
    ("uni02CE", 0x2CE, M.gravebelow), ("uni02CF", 0x2CF, M.acutebelow), ("uni02F7", 0x2F7, M.tildebelow),
    ("uni1FBE", 0x1FBE, M.ypogegrammenicomb),
]:
    spacing(_n, _u, _f, low=True)


def _mod(name, uni, fn):
    register(name, fn, uni)


def apostrophe_like(turned=False, reversed_=False, size=1.0, low=False):
    def fn(g, p):
        tmp = Glyph("tmp", p)
        y = (p.CAP + 20) if not low else 40
        M.comma_shape(tmp, p, p.M, y, size=size * 1.25, turned=turned)
        if reversed_:
            tmp.mirror_x()
        g.add(tmp.contours)

    return fn


_mod("uni02BC", 0x2BC, apostrophe_like())  # ʼ modifier apostrophe
_mod("uni02BB", 0x2BB, apostrophe_like(turned=True))  # ʻ
_mod("uni02BD", 0x2BD, apostrophe_like(reversed_=True))  # ʽ
_mod("uni02BE", 0x2BE, apostrophe_like(size=0.8))
_mod("uni02BF", 0x2BF, apostrophe_like(size=0.8, reversed_=True))


def prime_fn(n):
    def fn(g, p):
        from .punct import prime_stroke

        if n == 1:
            prime_stroke(g, p, p.M)
        else:
            o = (p.R - p.L) * 0.2
            prime_stroke(g, p, p.M - o, 0.85)
            prime_stroke(g, p, p.M + o, 0.85)

    return fn


_mod("uni02B9", 0x2B9, prime_fn(1))
_mod("uni02BA", 0x2BA, prime_fn(2))


def tick(vertical_low=False):
    def fn(g, p):
        t = p.S * 0.9
        if vertical_low:
            g.rect(p.M - t / 2, -180, p.M + t / 2, -20)
        else:
            g.rect(p.M - t / 2, p.CAP - 170, p.M + t / 2, p.CAP + 30)

    return fn


_mod("uni02C8", 0x2C8, tick())
_mod("uni02CC", 0x2CC, tick(True))


def colon_tri(half=False):
    def fn(g, p):
        d = min(p.S * 1.5 + 20, (p.R - p.L) * 0.38)
        hw = d * 0.6
        y1 = p.XH
        g.poly((p.M - hw, y1), (p.M + hw, y1), (p.M, y1 - d * 1.05))
        if not half:
            g.poly((p.M - hw, 0), (p.M, d * 1.05), (p.M + hw, 0))

    return fn


_mod("uni02D0", 0x2D0, colon_tri())
_mod("uni02D1", 0x2D1, colon_tri(True))


def arrowhead(direction, low=False):
    def fn(g, p):
        hw = (p.R - p.L) * 0.24
        cy = p.CAP * 0.62 if not low else p.CAP * 0.1
        pen = Pen(p.S * 0.85, p.S * 0.85)
        d = {"<": (-1, 0), ">": (1, 0), "^": (0, 1), "v": (0, -1)}[direction]
        if d[1] == 0:
            path = Path((p.M - d[0] * hw, cy + hw * 1.2)).L((p.M + d[0] * hw, cy)).L((p.M - d[0] * hw, cy - hw * 1.2))
        else:
            path = Path((p.M - hw * 1.2, cy - d[1] * hw)).L((p.M, cy + d[1] * hw)).L((p.M + hw * 1.2, cy - d[1] * hw))
        g.stroke(path, pen=pen)

    return fn


for _n, _u, _d, _low in [("uni02C2", 0x2C2, "<", False), ("uni02C3", 0x2C3, ">", False), ("uni02C4", 0x2C4, "^", False),
                         ("uni02C5", 0x2C5, "v", False), ("uni02F1", 0x2F1, "<", True), ("uni02F2", 0x2F2, ">", True),
                         ("uni02F0", 0x2F0, "^", True), ("uni02EF", 0x2EF, "v", True)]:
    _mod(_n, _u, arrowhead(_d, _low))


def tone_letter(level):
    """˥˦˧˨˩: vertical bar with a horizontal tick at a level (1=top..5)."""

    def fn(g, p):
        t = p.S * 0.85
        top, bot = p.CAP, 0
        x = p.R - p.S * 0.4
        g.rect(x - t / 2, bot, x + t / 2, top)
        y = top - (level - 1) * (top - bot) / 4
        y = min(top - t / 2, max(bot + t / 2, y))
        g.rect(p.L, y - t / 2, x, y + t / 2)

    return fn


for _i, _u in enumerate(range(0x2E5, 0x2EA), 1):
    _mod(f"uni{_u:04X}", _u, tone_letter(_i))


def modplusminus(sym):
    def fn(g, p):
        t = p.S * 0.85
        hw = (p.R - p.L) * 0.24
        cy = -80
        g.rect(p.M - hw, cy - t / 2, p.M + hw, cy + t / 2)
        if sym == "+":
            g.rect(p.M - t / 2, cy - hw, p.M + t / 2, cy + hw)

    return fn


_mod("uni02D6", 0x2D6, modplusminus("+"))
_mod("uni02D7", 0x2D7, modplusminus("-"))


def rhotic(g, p):
    pen = Pen(p.S * 0.8, p.S * 0.8)
    path = Path((p.L + p.S * 0.3, p.XH * 0.7)).vh((p.M, p.XH * 0.95)).hv((p.R - p.S * 0.4, p.XH * 0.75))
    g.stroke(path, pen=pen)


_mod("uni02DE", 0x2DE, rhotic)


# Superscript modifier letters (ʰ ʲ ʳ ʷ ʸ ˡ ˢ ˣ ˠ ˤ) drawn small from the letters.
def sup_letter(src, low=False):
    def fn(g, p):
        f = 0.62
        dy = p.CAP - p.XH * f - (p.CAP * 0.02)
        draw_scaled(g, p, src, f, f, 0.78, dy=dy)

    return fn


for _u, _src in [(0x2B0, "h"), (0x2B1, "uni0266"), (0x2B2, "j"), (0x2B3, "r"), (0x2B4, "uni0279"),
                 (0x2B7, "w"), (0x2B8, "y"), (0x2E1, "l"), (0x2E2, "s"), (0x2E3, "x"), (0x2E0, "uni0263"),
                 (0x2E4, "uni0295"), (0x1D43, "a"), (0x1D47, "b"), (0x1D48, "d"), (0x1D49, "e"), (0x1D4D, "g"),
                 (0x1D4F, "k"), (0x1D50, "m"), (0x1D52, "o"), (0x1D56, "p"), (0x1D57, "t"), (0x1D58, "u"),
                 (0x1D5B, "v"), (0x1D9C, "c"), (0x1DA0, "f"), (0x1DBB, "z"), (0x1D9E, "eth"), (0x1D4A, "schwa"),
                 (0x1D45, "uni0251"), (0x1D4B, "uni025B"), (0x1D5D, "beta"), (0x1D5E, "gamma"), (0x1D5F, "delta"),
                 (0x1D60, "phi"), (0x1D61, "chi"), (0x1DBF, "theta"), (0x1D2C, "A"), (0x1D2E, "B"), (0x1D30, "D"),
                 (0x1D31, "E"), (0x1D33, "G"), (0x1D34, "H"), (0x1D35, "I"), (0x1D36, "J"), (0x1D37, "K"),
                 (0x1D38, "L"), (0x1D39, "M"), (0x1D3A, "N"), (0x1D3C, "O"), (0x1D3E, "P"), (0x1D3F, "R"),
                 (0x1D40, "T"), (0x1D41, "U"), (0x1D42, "W"), (0x2C7D, "V")]:
    if _u >= 0x1D2C and _u <= 0x1D42 or _u == 0x2C7D:
        def _capfn(src):
            def fn(g, p):
                f = 0.5
                draw_scaled(g, p, src, 0.62, f, 0.78, dy=p.CAP - p.CAP * f + 30)
            return fn
        _mod(f"uni{_u:04X}", _u, _capfn(_src))
    else:
        _mod(f"uni{_u:04X}", _u, sup_letter(_src))


# Zero-width & special spaces (mono: every space is one cell, format chars 0)
def _empty(g, p):
    pass


def _zero(g, p):
    g.adv = 0


for _u in list(range(0x2000, 0x200B)) + [0x202F, 0x205F, 0x3000 - 0x3000 + 0x2007]:
    if f"uni{_u:04X}" not in REGISTRY:
        register(f"uni{_u:04X}", _empty, _u, kind="space")
for _u in (0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0xFEFF, 0x34F,
           0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x180E):
    register(f"uni{_u:04X}", _zero, _u, kind="mark" if _u == 0x34F else "space")
