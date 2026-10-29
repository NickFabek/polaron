"""Run the glyph generator for a set of masters and write static master TTFs.

Cubic outlines are converted to quadratic per segment *across all masters at
once* (cu2qu's compatible mode), so the master TTFs stay point-compatible and
can be fed straight into fontTools.varLib.
"""

from __future__ import annotations

import math
import time
from pathlib import Path as FsPath

from fontTools.cu2qu import curves_to_quadratic
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from . import config as C
from .glyph import REGISTRY, Glyph, Params

CU2QU_TOL = 1.0


class GlyphError(Exception):
    pass


def load_glyph_modules():
    from . import glyphs  # noqa: F401  (registers everything)
    from .glyphs import composites  # noqa: F401  (must come last)


def default_anchors(g, p):
    """Fill in anchors a base glyph did not define, from its bounding box."""
    if g.kind not in ("base",) or not g.contours:
        return
    from .geom import bounds_of

    xmin, ymin, xmax, ymax = bounds_of(g.contours)
    a = g.anchors
    a.setdefault("top", (p.M, max(ymax, p.XH)))
    a.setdefault("bottom", (p.M, min(ymin, 0)))
    a.setdefault("center", (p.M, (max(ymin, 0) + ymax) / 2))
    a.setdefault("ogonek", (xmax - p.S * 0.55, 0))
    a.setdefault("horn", (xmax - p.S * 0.5, min(ymax, p.CAP) - 10))
    a.setdefault("tonos", (xmin - p.S * 0.4, ymax))
    a.setdefault("caron", (xmax + 30, max(ymax, p.XH) - (ymax - p.XH if ymax > p.XH else 0)))


def run_glyphs(p: Params, only=None) -> dict:
    """Draw every registered glyph for one master."""
    load_glyph_modules()
    out = {}
    for name, gd in REGISTRY.items():
        if only is not None and name not in only:
            continue
        g = Glyph(name, p, list(gd.unicodes), kind=gd.kind, slant=gd.slant)
        if gd.adv is not None:
            g.adv = gd.adv * p.W
        try:
            gd.fn(g, p)
        except Exception as e:  # pragma: no cover - debugging aid
            raise GlyphError(f"while drawing {name}: {e!r}") from e
        default_anchors(g, p)
        out[name] = g
    # italic slant on drawn outlines
    if p.slant:
        sl, pv = p.slant, p.pivot
        f = lambda q: (q[0] + (q[1] - pv) * sl, q[1])  # noqa: E731
        for g in out.values():
            if g.slant:
                g.transform(f)
    resolve_composites(out)
    return out


def resolve_composites(gs: dict):
    """Turn deferred compose specs into positioned components."""
    done = set()

    def resolve(g):
        if g.name in done or not g.compose:
            done.add(g.name)
            return
        base = g.compose[0]
        if base not in gs:
            raise GlyphError(f"{g.name}: missing base {base}")
        bg = gs[base]
        resolve(bg)
        g.components = [(base, 0, 0)]
        anchors = dict(bg.anchors)
        for item in g.compose[1:]:
            mark, anc = item[0], item[1]
            extra = item[2] if len(item) > 2 else (0, 0)
            if mark not in gs:
                raise GlyphError(f"{g.name}: missing mark {mark}")
            mg = gs[mark]
            resolve(mg)
            mk = "_" + anc if "_" + anc in mg.anchors else "_top"
            if anc not in anchors or mk not in mg.anchors:
                raise GlyphError(f"{g.name}: cannot attach {mark} at {anc}")
            bx, by = anchors[anc]
            mx, my = mg.anchors[mk]
            dx, dy = round(bx - mx + extra[0]), round(by - my + extra[1])
            g.components.append((mark, dx, dy))
            # stacking: the mark's own anchor of the same name continues
            if anc in mg.anchors:
                ax, ay = mg.anchors[anc]
                anchors[anc] = (ax + dx, ay + dy)
        for k, v in anchors.items():
            g.anchors.setdefault(k, v)
        done.add(g.name)

    for g in list(gs.values()):
        resolve(g)


# ------------------------------------------------------------------ outlines
def _flatten_components(gs, name, dx=0, dy=0, depth=0):
    """Decompose a glyph into contours (used when contours + components mix)."""
    g = gs[name]
    out = [c.translate(dx, dy) for c in g.contours]
    for cn, cx, cy in g.components:
        out.extend(_flatten_components(gs, cn, dx + cx, dy + cy, depth + 1))
    return out


def _structure(contours):
    return [(len(c.segs), "".join(s[0] for s in c.segs)) for c in contours]


def convert_compatible(master_sets: list[dict]) -> list[dict]:
    """For each glyph, convert all masters' cubic contours to TT pen ops.

    Returns per master: name -> list of contours, each a list of ops
    ('M', p) ('L', p) ('Q', [pts...]).
    """
    names = list(master_sets[0].keys())
    out = [dict() for _ in master_sets]
    for name in names:
        per = []
        for gs in master_sets:
            g = gs[name]
            if g.contours and g.components:
                per.append(_flatten_components(gs, name))
            else:
                per.append(g.contours)
        s0 = _structure(per[0])
        for i, cs in enumerate(per[1:], 1):
            if _structure(cs) != s0:
                raise GlyphError(
                    f"glyph {name} incompatible between master 0 and {i}: {s0} vs {_structure(cs)}"
                )
        ops_per = [[] for _ in per]
        for ci in range(len(per[0])):
            conts = [cs[ci] for cs in per]
            for m, c in enumerate(conts):
                ops_per[m].append([("M", c.start)])
            prev = [c.start for c in conts]
            for si in range(len(conts[0].segs)):
                segs = [c.segs[si] for c in conts]
                if segs[0][0] == "L":
                    for m, s in enumerate(segs):
                        ops_per[m][-1].append(("L", s[1]))
                        prev[m] = s[1]
                else:
                    curves = [(prev[m], s[1], s[2], s[3]) for m, s in enumerate(segs)]
                    quads = curves_to_quadratic(curves, [CU2QU_TOL] * len(curves))
                    for m, q in enumerate(quads):
                        ops_per[m][-1].append(("Q", q[1:]))
                        prev[m] = segs[m][3]
        for m in range(len(per)):
            out[m][name] = ops_per[m]
    return out


def _tt_glyph(ops_list, components, names=None):
    pen = TTGlyphPen(names if names is not None else {})
    if components:
        for cn, dx, dy in components:
            pen.addComponent(cn, (1, 0, 0, 1, dx, dy))
        return pen.glyph()
    for ops in ops_list:
        for op in ops:
            if op[0] == "M":
                pen.moveTo(_r(op[1]))
            elif op[0] == "L":
                pen.lineTo(_r(op[1]))
            else:
                pen.qCurveTo(*[_r(q) for q in op[1]])
        pen.closePath()
    return pen.glyph(dropImpliedOnCurves=False)


def _r(p):
    return (round(p[0]), round(p[1]))


# ------------------------------------------------------------------ font
def family_names(style, italic):
    fam = f"{C.FAMILY} {style.capitalize()}"
    sub = "Italic" if italic else "Regular"
    return fam, sub


def build_master_fonts(style, italic, masters, fea_fn=None, only=None, log=print):
    """Build static TTFonts for the given (wght, wdth) masters."""
    t0 = time.time()
    sets = []
    params = []
    for (w, d) in masters:
        p = Params(style, italic, w, d)
        params.append(p)
        sets.append(run_glyphs(p, only=only))
    log(f"  drew {len(sets[0])} glyphs x {len(masters)} masters in {time.time()-t0:.1f}s")
    t1 = time.time()
    conv = convert_compatible(sets)
    log(f"  cu2qu in {time.time()-t1:.1f}s")
    fonts = []
    for m, (p, gs, ops) in enumerate(zip(params, sets, conv)):
        fonts.append(_make_font(style, italic, p, gs, ops, fea_fn))
    return fonts, sets


def glyph_order(gs):
    names = list(gs.keys())
    first = [n for n in (".notdef", "space") if n in gs]
    return first + [n for n in names if n not in first]


def _make_font(style, italic, p, gs, ops, fea_fn):
    order = glyph_order(gs)
    fam, sub = family_names(style, italic)
    fb = FontBuilder(C.UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {}
    for n in order:
        for u in gs[n].unicodes:
            cmap.setdefault(u, n)
    fb.setupCharacterMap(cmap)
    glyf = {}
    names = {n: None for n in order}
    for n in order:
        g = gs[n]
        comps = g.components if (g.components and not g.contours) else None
        glyf[n] = _tt_glyph(ops[n], comps, names)
    fb.setupGlyf(glyf)
    gt = fb.font["glyf"]
    metrics = {}
    for n in order:
        tg = gt[n]
        tg.recalcBounds(gt)
        lsb = getattr(tg, "xMin", 0) if tg.numberOfContours != 0 else 0
        metrics[n] = (max(0, round(gs[n].adv)), lsb)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=C.TYPO_ASC, descent=C.TYPO_DESC, lineGap=C.LINE_GAP)
    ps = f"{fam.replace(' ', '')}-{sub}"
    fb.setupNameTable(
        {
            "familyName": fam,
            "styleName": sub,
            "uniqueFontIdentifier": f"{C.VERSION};{ps}",
            "fullName": f"{fam} {sub}",
            "psName": ps,
            "version": f"Version {C.VERSION}",
            "copyright": "Copyright 2026 The Polaron Project Authors",
            "licenseDescription": "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
            "licenseInfoURL": "https://openfontlicense.org",
        }
    )
    fb.setupOS2(
        sTypoAscender=C.TYPO_ASC,
        sTypoDescender=C.TYPO_DESC,
        sTypoLineGap=C.LINE_GAP,
        usWinAscent=C.TYPO_ASC,
        usWinDescent=-C.TYPO_DESC,
        sxHeight=C.XHEIGHT,
        sCapHeight=C.CAP,
        usWeightClass=p.wght,
        usWidthClass=_width_class(p.wdth),
        fsSelection=(0x01 if italic else 0x40) | 0x80,  # ITALIC/REGULAR + USE_TYPO_METRICS
        achVendID="PLRN",
        panose=_panose(style),
    )
    fb.setupPost(isFixedPitch=1, italicAngle=-p.angle, underlinePosition=-150, underlineThickness=round(p.H))
    fb.setupHead(unitsPerEm=C.UPM)
    fb.font["head"].macStyle = 0x02 if italic else 0
    fb.setupMaxp()
    fb.font["gasp"] = _gasp()
    fea = fea_fn(p, gs) if fea_fn else ""
    if fea:
        from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

        addOpenTypeFeaturesFromString(fb.font, fea)
    return fb.font


def _width_class(wdth):
    table = [(50, 1), (62.5, 2), (75, 3), (87.5, 4), (100, 5), (112.5, 6), (125, 7), (150, 8), (200, 9)]
    best = min(table, key=lambda t: abs(t[0] - wdth))
    return best[1]


def _panose(style):
    from fontTools.ttLib.tables.O_S_2f_2 import Panose

    pa = Panose()
    pa.bFamilyType = 2
    pa.bSerifStyle = 11 if style == "sans" else 2
    pa.bWeight = 5
    pa.bProportion = 9  # monospaced
    pa.bContrast = 2
    pa.bStrokeVariation = 2
    pa.bArmStyle = 2
    pa.bLetterForm = 2
    pa.bMidline = 2
    pa.bXHeight = 4
    return pa


def _gasp():
    from fontTools.ttLib import newTable

    t = newTable("gasp")
    t.version = 1
    t.gaspRange = {0xFFFF: 0x0A}  # symmetric smoothing at all sizes
    return t
