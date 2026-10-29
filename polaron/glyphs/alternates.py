"""Stylistic alternates exposed as character variants (cvXX)."""

from __future__ import annotations

import math

from ..glyph import glyph
from ..stroke import Path, Pen
from .latin_lower import a_single, dot, g_double, i_dot_y, serif_head, tail_stem, vstem
from .punct import asterisk


@glyph("a.single")
def a_single_alt(g, p):
    a_single(g, p)


@glyph("g.double")
def g_double_alt(g, p):
    g_double(g, p)


def l_slab_body(g, p):
    S = p.S
    xc = p.M
    vstem(g, p, xc, 0, p.ASC)
    serif_head(g, p, xc, p.ASC, length=(xc - S / 2) - (p.L + S * 0.25), sans=True)
    hw = (p.R - p.L) / 2 - S * 0.05
    g.rect(p.M - hw, 0, p.M + hw, p.Hb if p.sans else p.ST)
    g.anchor("top", xc, p.ASC).anchor("bottom", p.M, 0)


@glyph("l.slab")
def l_slab(g, p):
    l_slab_body(g, p)


def i_tail_body(g, p, with_dot):
    S = p.S
    xc = p.M - (p.R - p.L) * 0.06
    tail_stem(g, p, xc, p.XH, f=1.1)
    serif_head(g, p, xc, p.XH, length=(xc - S / 2) - (p.L + S * 0.15), sans=True)
    if with_dot:
        dot(g, p, xc, i_dot_y(p))
    g.anchor("top", xc, p.XH).anchor("bottom", p.M, 0)


@glyph("i.tail")
def i_tail(g, p):
    i_tail_body(g, p, True)


@glyph("dotlessi.tail")
def dotlessi_tail(g, p):
    i_tail_body(g, p, False)


@glyph("asterisk.raised")
def asterisk_raised(g, p):
    asterisk(g, p)
    g.translate(0, p.CAP - p.AX - (p.R - p.L) * 0.42)


CV = {
    "cv03": [("a", "a.single")],
    "cv04": [("g", "g.double")],
    "cv05": [("l", "l.slab")],
    "cv06": [("i", "i.tail"), ("dotlessi", "dotlessi.tail")],
    "cv07": [("asterisk", "asterisk.raised")],
}
