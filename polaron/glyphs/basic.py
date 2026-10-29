"""Control glyphs: .notdef, space and friends."""

from ..glyph import glyph


@glyph(".notdef", slant=False)
def notdef(g, p):
    t = max(p.S * 0.5, 20)
    x0, x1 = p.L, p.R
    y0, y1 = 0, p.CAP
    g.rect(x0, y0, x1, y1)
    # hole (counter-clockwise)
    from ..geom import Contour

    g.add(Contour.polygon([(x0 + t, y0 + t), (x1 - t, y0 + t), (x1 - t, y1 - t), (x0 + t, y1 - t)]))


@glyph("space", 0x20, kind="space")
def space(g, p):
    pass


@glyph("nbspace", 0xA0, kind="space")
def nbspace(g, p):
    pass
