"""Design parameters, the Glyph drawing surface and the glyph registry."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import config as C
from .geom import Contour, affine
from .stroke import Path, Pen, Stroker


def _interp_weight(wght, table):
    """Piecewise-linear lookup over master weights."""
    ks = sorted(table)
    if wght <= ks[0]:
        return table[ks[0]]
    for a, b in zip(ks, ks[1:]):
        if wght <= b:
            t = (wght - a) / (b - a)
            return table[a] + (table[b] - table[a]) * t
    return table[ks[-1]]


class Params:
    """All numbers a glyph drawing may depend on, for one master."""

    def __init__(self, style="sans", italic=False, wght=400, wdth=100):
        self.style = style
        self.serif = style == "serif"
        self.sans = not self.serif
        self.italic = italic
        self.wght = wght
        self.wdth = wdth
        self.upm = C.UPM

        W = C.cell_width(wdth)
        self.W = W
        self.M = W / 2
        self.XH = C.XHEIGHT
        self.CAP = C.CAP
        self.ASC = C.ASCENDER
        self.DESC = C.DESCENDER
        self.AX = 322  # math axis (centre of - + = < >)
        self.BT = 860  # bracket top / bottom
        self.BB = -180
        self.BOXT = C.BOX_TOP
        self.BOXB = C.BOX_BOTTOM

        wf = (W / 550) ** 0.35  # narrower cells get slightly lighter stems
        stem = _interp_weight(wght, {100: 24, 400: 76, 900: 144}) * wf
        self.S = stem
        if self.serif:
            ratio = _interp_weight(wght, {100: 0.86, 400: 0.56, 900: 0.48})
        else:
            ratio = _interp_weight(wght, {100: 0.98, 400: 0.88, 900: 0.80})
        self.H = stem * ratio  # horizontal parts of curves
        self.Hb = stem * (ratio if self.serif else ratio * 0.97)  # straight bars
        self.OV = 10 + stem * 0.06
        sb = W * (0.1 if style == "sans" else 0.112) - (stem - 76) * 0.13
        self.SB = sb
        self.L = sb
        self.R = W - sb
        # superness: handle factor of superelliptic quarter arcs
        self.k = 0.66 if self.sans else 0.62
        self.kin = 0.03 if self.sans else 0.05
        self.ovr = 1.0  # arc height / half width of bowls
        self.pen_angle = 12.0 if self.serif else 0.0
        self.pen = Pen(self.S, self.H)
        # serifs
        self.SL = (self.R - self.L) * 0.2  # serif reach beyond the stem
        self.ST = max(self.H * 0.88, 14)  # serif thickness
        self.cellpad = W * 0.03  # serifs never come closer to the cell edge
        # italic
        self.angle = 10.0 if italic else 0.0
        self.slant = math.tan(math.radians(self.angle))
        self.pivot = self.XH / 2
        # dots
        self.dotw = min(stem * 1.32, (self.R - self.L) * 0.42) if stem > 40 else stem * 1.6 + 8

    # convenience ---------------------------------------------------------
    def pen_w(self, f):
        return self.pen.scaled(f)

    def mid(self, a, b, t=0.5):
        return a + (b - a) * t


@dataclass
class Glyph:
    name: str
    p: Params
    unicodes: list = field(default_factory=list)
    contours: list = field(default_factory=list)
    components: list = field(default_factory=list)  # (glyphname, dx, dy)
    anchors: dict = field(default_factory=dict)
    adv: float = None
    kind: str = "base"  # base | mark | ligature | space
    slant: bool = True
    compose: list = None  # deferred: [base, (mark, anchor), ...]

    def __post_init__(self):
        if self.adv is None:
            self.adv = self.p.W

    # ---- drawing ---------------------------------------------------------
    def add(self, cs):
        if isinstance(cs, Contour):
            self.contours.append(cs)
        else:
            self.contours.extend(cs)
        return self

    def stroke(self, path: Path, pen: Pen = None, start="butt", end="butt", k=None, kin=None):
        p = self.p
        pen = pen or p.pen
        if getattr(p, "pen_angle", 0) and pen.ang == 0 and abs(pen.A - pen.B) > 0.5:
            pen = Pen.calibrated(2 * pen.A, 2 * pen.B, p.pen_angle)
        st = Stroker(pen, kin=p.kin if kin is None else kin)
        self.contours.extend(st.stroke(path, k=p.k if k is None else k, start=start, end=end))
        return self

    def line(self, a, b, w=1.0, w1=None, pen=None, start="butt", end="butt"):
        path = Path(a, w).L(b, w if w1 is None else w1)
        return self.stroke(path, pen=pen, start=start, end=end)

    def rect(self, x0, y0, x1, y1):
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        self.contours.append(Contour.polygon([(x0, y0), (x0, y1), (x1, y1), (x1, y0)]))
        return self

    def poly(self, *pts):
        self.contours.append(Contour.polygon(pts).clockwise())
        return self

    def ref(self, name, dx=0, dy=0):
        self.components.append((name, dx, dy))
        return self

    def anchor(self, name, x, y):
        self.anchors[name] = (x, y)
        return self

    # ---- transforms -------------------------------------------------------
    def transform(self, f, flip=False):
        self.contours = [c.map(f) for c in self.contours]
        if flip:
            self.contours = [c.reversed() for c in self.contours]
        self.anchors = {k: f(v) for k, v in self.anchors.items()}
        return self

    def translate(self, dx, dy=0):
        return self.transform(lambda q: (q[0] + dx, q[1] + dy))

    def mirror_x(self, cx=None):
        cx = self.p.M if cx is None else cx
        return self.transform(lambda q: (2 * cx - q[0], q[1]), flip=True)

    def mirror_y(self, cy):
        return self.transform(lambda q: (q[0], 2 * cy - q[1]), flip=True)


# ------------------------------------------------------------------ registry
@dataclass
class GlyphDef:
    name: str
    fn: object
    unicodes: tuple
    kind: str
    slant: bool
    adv: float  # in cells (1 = one cell); None = default


REGISTRY: dict[str, GlyphDef] = {}


def glyph(name, uni=None, kind="base", slant=True, cells=None):
    """Decorator registering a glyph drawing function fn(g, p)."""
    if uni is None:
        unis = ()
    elif isinstance(uni, int):
        unis = (uni,)
    else:
        unis = tuple(uni)

    def deco(fn):
        if name in REGISTRY:
            raise ValueError(f"duplicate glyph {name}")
        REGISTRY[name] = GlyphDef(name, fn, unis, kind, slant, cells)
        return fn

    return deco


def register(name, fn, uni=None, kind="base", slant=True, cells=None):
    glyph(name, uni, kind, slant, cells)(fn)
