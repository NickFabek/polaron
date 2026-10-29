"""Programming ligatures that keep the monospace grid.

Each ligature of n characters is implemented with contextual alternates
(calt): the first n-1 characters become an empty spacer glyph `LIG`
(advance = one cell) and the last character becomes the ligature glyph,
whose drawing reaches back over the previous n-1 cells (negative x).
So the text still advances exactly n cells and the caret/selection math of
editors keeps working.
"""

from __future__ import annotations

import math

from ..glyph import glyph, register
from ..stroke import Path, Pen
from .parts import dot, hbar, vstem
from .punct import angle_pts, eq_gap, op_hw, pdot_d

NAMES = {
    "-": "hyphen", ">": "greater", "<": "less", "=": "equal", "!": "exclam", ":": "colon",
    "|": "bar", "/": "slash", "~": "asciitilde", ".": "period", "&": "ampersand", "*": "asterisk",
    "+": "plus",
}

LIGS = []  # (sequence of glyph names, ligature glyph name)


@glyph("LIG", kind="base")
def lig_spacer(g, p):
    pass


def lig(seq):
    names = [NAMES[c] for c in seq]
    lname = "_".join(names) + ".liga"

    def deco(fn):
        n = len(seq)

        def full(g, p):
            x0 = -(n - 1) * p.W
            fn(g, p, x0, p.W, n)

        register(lname, full, None)
        LIGS.append((names, lname))
        return fn

    return deco


# ------------------------------------------------------------------ primitives
def shaft(g, p, xa, xb, y=None, t=None):
    y = p.AX if y is None else y
    t = p.Hb if t is None else t
    g.rect(min(xa, xb), y - t / 2, max(xa, xb), y + t / 2)


def head(g, p, tip, y, d, hw=None, hh=None, w=0.95):
    """Open chevron arrow head, tip at x=tip pointing in direction d (±1)."""
    hw0, hh0 = angle_pts(p)
    hw = hw0 * 0.85 if hw is None else hw
    hh = hh0 * 0.85 if hh is None else hh
    path = Path((tip - d * hw, y + hh), w).L((tip, y), w).L((tip - d * hw, y - hh), w)
    g.stroke(path)


def dbl_head(g, p, tip, y, d):
    gap = eq_gap(p)
    hw0, hh0 = angle_pts(p)
    hh = gap / 2 + hh0 * 0.62
    head(g, p, tip, y, d, hw=hh * 0.92, hh=hh)


def margin(p):
    return p.L * 0.9


def bars(g, p, xa, xb, k=2, gap=None):
    gap = eq_gap(p) if gap is None else gap
    t = p.S * 0.92
    if k == 2:
        ys = (p.AX + gap / 2, p.AX - gap / 2)
    else:
        gg = gap * 0.78
        ys = (p.AX + gg, p.AX, p.AX - gg)
        t = p.S * 0.85
    for y in ys:
        g.rect(xa, y - t / 2, xb, y + t / 2)


def slash_through(g, p, cx, hh=None):
    hh = (p.R - p.L) * 0.55 if hh is None else hh
    hw = hh * 0.42
    g.stroke(Path((cx - hw, p.AX - hh)).L((cx + hw, p.AX + hh)), pen=Pen(p.S * 0.92, p.S * 0.92), start=0, end=0)


def tilde_wave(g, p, xa, xb, k, y=None):
    y = p.AX if y is None else y
    a = p.S * 0.35 + 34
    w = xb - xa
    # one wave per cell, as a chain of cubic halves
    path = Path((xa, y - a * 0.45))
    step = w / k
    for i in range(k):
        s = xa + i * step
        m = s + step / 2
        e = s + step
        path.C((s + step * 0.12, y + a * 1.1), (m - step * 0.2, y + a * 0.9), (m, y))
        path.C((m + step * 0.2, y - a * 0.9), (e - step * 0.12, y - a * 1.1), (e, y + a * 0.45 if i == k - 1 else y - a * 0.45))
    g.stroke(path, pen=Pen(p.S * 0.95, p.S * 0.95))


# ------------------------------------------------------------------ arrows
def arrow(g, p, x0, x1, left=False, right=True, double=False, heads=1):
    m = margin(p)
    xa, xb = x0 + m, x1 - m
    t = p.Hb
    if double:
        gap = eq_gap(p)
        bars(g, p, xa + (gap * 0.6 if left else 0), xb - (gap * 0.6 if right else 0), 2)
        if right:
            dbl_head(g, p, xb, p.AX, 1)
        if left:
            dbl_head(g, p, xa, p.AX, -1)
        return
    shaft(g, p, xa + (t * 0.4 if left else 0), xb - (t * 0.4 if right else 0))
    hw0, _ = angle_pts(p)
    for i in range(heads):
        off = i * hw0 * 0.7
        if right:
            head(g, p, xb - off, p.AX, 1)
        if left:
            head(g, p, xa + off, p.AX, -1)


@lig("->")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1)


@lig("<-")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True, right=False)


@lig("<->")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True)


@lig("-->")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1)


@lig("<--")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True, right=False)


@lig("<-->")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True)


@lig("->>")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, heads=2)


@lig("<<-")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True, right=False, heads=2)


@lig("=>")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, double=True)


@lig("<=>")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True, double=True)


@lig("==>")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, double=True)


@lig("<==")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True, right=False, double=True)


@lig("<==>")
def _(g, p, x0, x1, n):
    arrow(g, p, x0, x1, left=True, double=True)


@lig("=>>")
def _(g, p, x0, x1, n):
    arrow(g, p, x0 - p.W * 0.0, x1 - angle_pts(p)[0] * 0.75, double=True)
    head(g, p, x1 - margin(p), p.AX, 1, hh=eq_gap(p) / 2 + angle_pts(p)[1] * 0.62,
         hw=(eq_gap(p) / 2 + angle_pts(p)[1] * 0.62) * 0.92)


@lig("~>")
def _(g, p, x0, x1, n):
    m = margin(p)
    tilde_wave(g, p, x0 + m, x1 - m - p.S * 0.4, n - 1)
    head(g, p, x1 - m, p.AX, 1)


@lig("<~")
def _(g, p, x0, x1, n):
    m = margin(p)
    tilde_wave(g, p, x0 + m + p.S * 0.4, x1 - m, n - 1)
    head(g, p, x0 + m, p.AX, -1)


@lig("~~>")
def _(g, p, x0, x1, n):
    m = margin(p)
    tilde_wave(g, p, x0 + m, x1 - m - p.S * 0.4, n - 1)
    head(g, p, x1 - m, p.AX, 1)


@lig("<~~")
def _(g, p, x0, x1, n):
    m = margin(p)
    tilde_wave(g, p, x0 + m + p.S * 0.4, x1 - m, n - 1)
    head(g, p, x0 + m, p.AX, -1)


# ------------------------------------------------------------------ equality
@lig("==")
def _(g, p, x0, x1, n):
    m = margin(p)
    bars(g, p, x0 + m, x1 - m)


@lig("===")
def _(g, p, x0, x1, n):
    m = margin(p)
    bars(g, p, x0 + m, x1 - m, 3)


@lig("!=")
def _(g, p, x0, x1, n):
    m = margin(p)
    bars(g, p, x0 + m, x1 - m)
    slash_through(g, p, (x0 + x1) / 2)


@lig("!==")
def _(g, p, x0, x1, n):
    m = margin(p)
    bars(g, p, x0 + m, x1 - m, 3)
    slash_through(g, p, (x0 + x1) / 2, hh=(p.R - p.L) * 0.62)


@lig("=/=")
def _(g, p, x0, x1, n):
    m = margin(p)
    bars(g, p, x0 + m, x1 - m)
    slash_through(g, p, (x0 + x1) / 2, hh=(p.R - p.L) * 0.62)


def le_ge(g, p, x0, x1, d):
    """≤ (d=-1, opening right) / ≥ (d=1) spanning two cells."""
    cx = (x0 + x1) / 2
    hw = p.W * 0.62
    hh = (p.R - p.L) * 0.38
    y = p.AX + p.S * 0.55 + hh * 0.25
    tip = cx + d * hw
    path = Path((cx - d * hw, y + hh), 0.95).L((tip, y), 0.95).L((cx - d * hw, y - hh), 0.95)
    g.stroke(path)
    yb = y - hh - p.S * 0.9 - p.S * 0.5
    g.rect(cx - hw, yb - p.S * 0.46, cx + hw, yb + p.S * 0.46)


@lig("<=")
def _(g, p, x0, x1, n):
    le_ge(g, p, x0, x1, -1)


@lig(">=")
def _(g, p, x0, x1, n):
    le_ge(g, p, x0, x1, 1)


# ------------------------------------------------------------------ punctuation runs
def colon_pair(g, p, cx):
    d = pdot_d(p)
    gap = eq_gap(p) * 0.62 + d * 0.5
    dot(g, p, cx, p.AX + gap, d=d, k=0.66)
    dot(g, p, cx, p.AX - gap, d=d, k=0.66)


@lig("::")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.3
    colon_pair(g, p, c - o)
    colon_pair(g, p, c + o)


@lig(":::")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.62
    for dx in (-o, 0, o):
        colon_pair(g, p, c + dx)


@lig(":=")
def _(g, p, x0, x1, n):
    colon_pair(g, p, x0 + p.W * 0.62)
    gap = eq_gap(p) * 1.24 + pdot_d(p)
    bars(g, p, x0 + p.W * 0.62 + pdot_d(p) * 0.5 + p.S * 0.6, x1 - margin(p), 2, gap=gap * 0.62)


@lig("::=")
def _(g, p, x0, x1, n):
    colon_pair(g, p, x0 + p.W * 0.7)
    colon_pair(g, p, x0 + p.W * 1.3)
    gap = eq_gap(p) * 1.24 + pdot_d(p)
    bars(g, p, x0 + p.W * 1.3 + pdot_d(p) * 0.5 + p.S * 0.6, x1 - margin(p), 2, gap=gap * 0.62)


@lig("||")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.22
    for dx in (-o, o):
        vstem(g, p, c + dx, p.BB, p.BT)


def slash_at(g, p, cx):
    from .latin_lower import diag_between

    top, bot = p.ASC + 50, p.DESC + 40
    hw = (p.R - p.L) * 0.5 - p.S * 0.1
    a, b = diag_between(p, cx + hw, top, cx - hw, bot, -1, 1, w=0.95)
    g.stroke(Path(a, 0.95).L(b, 0.95), start=0, end=0)


@lig("//")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.3
    for dx in (-o, o):
        slash_at(g, p, c + dx)


@lig("///")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.6
    for dx in (-o, 0, o):
        slash_at(g, p, c + dx)


def chev(g, p, cx, d):
    hw, hh = angle_pts(p)
    path = Path((cx - d * hw, p.AX + hh), 0.95).L((cx + d * hw, p.AX), 0.95).L((cx - d * hw, p.AX - hh), 0.95)
    g.stroke(path)


@lig("<<")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.27
    for dx in (-o, o):
        chev(g, p, c + dx, -1)


@lig(">>")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.27
    for dx in (-o, o):
        chev(g, p, c + dx, 1)


@lig("<<<")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.52
    for dx in (-o, 0, o):
        chev(g, p, c + dx, -1)


@lig(">>>")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    o = p.W * 0.52
    for dx in (-o, 0, o):
        chev(g, p, c + dx, 1)


def triangle(g, p, xa, xb, d):
    """Pipe triangle: vertical edge at xa, apex at xb (d = direction)."""
    hw, hh = angle_pts(p)
    hh *= 1.05
    t = p.S * 0.95
    g.rect(xa - d * t / 2, p.AX - hh, xa + d * t / 2, p.AX + hh)
    path = Path((xa, p.AX + hh), 0.95).L((xb, p.AX), 0.95).L((xa, p.AX - hh), 0.95)
    g.stroke(path)


@lig("|>")
def _(g, p, x0, x1, n):
    triangle(g, p, x0 + p.W * 0.62, x1 - margin(p), 1)


@lig("<|")
def _(g, p, x0, x1, n):
    triangle(g, p, x1 - p.W * 0.62, x0 + margin(p), -1)


@lig("<|>")
def _(g, p, x0, x1, n):
    c = (x0 + x1) / 2
    triangle(g, p, c, x1 - margin(p), 1)
    triangle(g, p, c, x0 + margin(p), -1)


# ------------------------------------------------------------------ FEA
def calt_fea(gs) -> str:
    lines = ["feature calt {"]
    for seq, lname in sorted(LIGS, key=lambda t: -len(t[0])):
        if lname not in gs or any(s not in gs for s in seq):
            continue
        n = len(seq)
        lk = "L_" + lname.replace(".", "_")
        first, last = seq[0], seq[-1]
        lines.append(f"  lookup {lk} {{")
        lines.append(f"    ignore sub {first} {first}' " + " ".join(seq[1:]) + ";")
        lines.append(f"    ignore sub {first}' " + " ".join(seq[1:]) + f" {last};")
        lines.append("    sub " + " ".join(["LIG"] * (n - 1)) + f" {last}' by {lname};")
        for i in range(n - 2, -1, -1):
            before = " ".join(["LIG"] * i)
            after = " ".join(seq[i + 1:])
            lines.append(f"    sub {before} {seq[i]}' {after} by LIG;".replace("sub  ", "sub "))
        lines.append(f"  }} {lk};")
    lines.append("} calt;")
    return "\n".join(lines)


def character_variants(gs):
    """cvXX / ssXX features: name -> [(from, to)]."""
    feats = {}
    if "zero.plain" in gs:
        feats["cv01"] = [("zero", "zero.plain")]
    if "zero.slash" in gs:
        feats["cv02"] = [("zero", "zero.slash")]
    from .alternates import CV

    for tag, pairs in CV.items():
        ok = [(a, b) for a, b in pairs if a in gs and b in gs]
        if ok:
            feats[tag] = ok
    return feats
