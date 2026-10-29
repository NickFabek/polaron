"""Draw any glyph at a different scale (superscripts, subscripts, small caps).

Instead of scaling outlines (which would thin the strokes), the glyph
function is re-run with derived parameters: smaller frame, proportionally
heavier strokes. Contour structure is unchanged, so masters stay compatible.
"""

from __future__ import annotations

import copy

from ..glyph import REGISTRY, Glyph
from ..stroke import Pen


def derive(p, fx, fy, wf, cx=None):
    q = copy.copy(p)
    cx = p.M if cx is None else cx
    q.M = cx
    q.L = cx - (p.M - p.L) * fx
    q.R = cx + (p.R - p.M) * fx
    for attr in ("XH", "CAP", "ASC", "DESC", "OV", "AX", "BT", "BB"):
        setattr(q, attr, getattr(p, attr) * fy)
    q.S = p.S * wf
    q.H = p.H * wf
    q.Hb = p.Hb * wf
    q.ST = p.ST * wf
    q.SL = p.SL * fx
    q.dotw = p.dotw * (wf + fx) / 2
    q.pen = Pen(q.S, q.H)
    q.pivot = p.pivot
    return q


def draw_scaled(g, p, name, fx, fy, wf, dx=0.0, dy=0.0, cx=None):
    """Run glyph `name` with derived params and add its contours to g.
    Returns the translated anchors of the drawn glyph."""
    q = derive(p, fx, fy, wf, cx=cx)
    gd = REGISTRY[name]
    tmp = Glyph("tmp", q)
    tmp.adv = g.adv
    gd.fn(tmp, q)
    tmp.translate(dx, dy)
    g.add(tmp.contours)
    return tmp.anchors


# Standard positions --------------------------------------------------------
SUP_F = 0.62  # size of superscripts relative to full size
SUP_W = 0.78  # stroke factor


def sup_dy(p):
    return p.CAP - p.CAP * SUP_F * 1.0 + 40


def sub_dy(p):
    return -150


def numr_dy(p):
    return p.CAP - p.CAP * SUP_F


def dnom_dy(p):
    return 0
