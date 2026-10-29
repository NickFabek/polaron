"""CJK for Polaron: a glyph-only "part" variable font plus a glyph-level insert.

CJK is too big to go through the 9-master varLib build, and needs no
layout, so it is handled separately:

* :func:`build_cjk_part` makes a variable TTF with exactly Polaron's axes
  (``config.AXES``) whose masters sit at ``config.SPARSE_MASTERS``: weight
  variation comes from instancing the Noto CJK VF at 100/400/900 (clamped to
  the source range), width variation is an affine x-fit per wdth.  The gvar
  table is written directly (one TupleVariation per sparse master, IUP
  optimised); corners are reached additively.  East-Asian Wide/Fullwidth
  characters get 2 cells, halfwidth (and other) characters 1 cell, zero-width
  sources (combining kana marks) stay 0.  No GSUB/GPOS/GDEF.
* :func:`insert_vf_glyphs` copies the glyphs of such a part (outlines, gvar,
  hmtx, cmap) into an already built main VF and rebuilds HVAR.

Glyph names are ``cjk.uXXXX`` (lowest code point mapped to the glyph); glyph
order follows code points so the format-4 cmap stays compact.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path

import numpy as np
from fontTools import subset
from fontTools.fontBuilder import FontBuilder
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib import instancer
from fontTools.varLib.hvar import add_HVAR
from fontTools.varLib.instancer import OverlapMode
from fontTools.varLib.iup import iup_delta_optimize

from .. import config
from . import cache, fetch, fontmerge
from . import geometry as geo

log = logging.getLogger("polaron.foreign.cjk")

PART_VERSION = 2
MAX_GLYPHS = 42000
X_STRETCH_MAX = 1.08        # never widen CJK more than this
NATURAL_CELL = 550          # Noto's 1000-unit em corresponds to 2 cells of 550
IUP_TOLERANCE = 1.0      # width deltas are exact up to rounding

SOURCES = {
    "sans": ("notosanssc", "notosanskr"),
    "serif": ("notoserifsc", "notoserifkr"),
}

# Priority-ordered code point groups; the glyph budget is filled in order.
GROUPS = [
    ("symbols+kana", [(0x2E80, 0x2EFF), (0x2F00, 0x2FDF), (0x2FF0, 0x2FFF), (0x3000, 0x303F),
                      (0x3040, 0x309F), (0x30A0, 0x30FF), (0x3100, 0x312F), (0x3130, 0x318F),
                      (0x3190, 0x319F), (0x31A0, 0x31BF), (0x31C0, 0x31EF), (0x31F0, 0x31FF),
                      (0x3200, 0x32FF), (0x3300, 0x33FF), (0xFE10, 0xFE1F), (0xFE30, 0xFE4F),
                      (0xFE50, 0xFE6F), (0xFF01, 0xFF60), (0xFF61, 0xFFDC), (0xFFE0, 0xFFE6),
                      (0xFFE8, 0xFFEE), (0x1F200, 0x1F2FF)]),
    ("han", [(0x4E00, 0x9FFF)]),
    ("hangul", [(0xAC00, 0xD7A3), (0x1100, 0x11FF), (0xA960, 0xA97F), (0xD7B0, 0xD7FF)]),
    ("compat-ideographs", [(0xF900, 0xFAFF)]),
    ("han-ext-a", [(0x3400, 0x4DBF)]),
]
HANGUL = [(0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F), (0xAC00, 0xD7AF),
          (0xD7B0, 0xD7FF), (0xFFA0, 0xFFDC)]

AXIS_TAGS = tuple(config.AXES)  # ("wght", "wdth")


def _in(cp, ranges):
    return any(lo <= cp <= hi for lo, hi in ranges)


def cells_for(cp: int) -> int:
    """Cells for a CJK code point (East Asian Width W/F -> 2, else 1)."""
    return 2 if unicodedata.east_asian_width(chr(cp)) in ("W", "F") else 1


def _part_dir(style: str) -> Path:
    d = cache.BUILD_DIR / style / "cjk"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------
# sources: assignment, subset, instances


def assign_codepoints(style: str) -> tuple[dict[int, int], dict]:
    """Map code point -> source index (0 = SC, 1 = KR) within the glyph budget."""
    fetch.fetch_sources((style,))
    cmaps = []
    for fam in SOURCES[style]:
        cmaps.append(TTFont(fetch.font_path(style, fam), lazy=True).getBestCmap())
    chosen: dict[int, int] = {}
    glyph_keys: set = set()
    report = {}
    for name, ranges in GROUPS:
        cps = []
        for lo, hi in ranges:
            cps.extend(range(lo, hi + 1))
        add = {}
        new_glyphs = set()
        for cp in cps:
            order = (1, 0) if _in(cp, HANGUL) else (0, 1)
            src = next((i for i in order if cp in cmaps[i]), None)
            if src is None:
                continue
            add[cp] = src
            new_glyphs.add((src, cmaps[src][cp]))
        new_glyphs -= glyph_keys
        if len(glyph_keys) + len(new_glyphs) > MAX_GLYPHS:
            report[name] = f"skipped ({len(new_glyphs)} glyphs would exceed {MAX_GLYPHS})"
            continue
        chosen.update(add)
        glyph_keys |= new_glyphs
        report[name] = len(new_glyphs)
    report["total_glyphs"] = len(glyph_keys)
    return chosen, report


def _subset_source(style: str, idx: int, cps: list[int]) -> tuple[Path, str]:
    fam = SOURCES[style][idx]
    src = fetch.font_path(style, fam)
    out = _part_dir(style) / f"{fam}.subset.ttf"
    key = cache.make_key(["cjk-subset", fetch.source_sha256(src), cache.make_key(cps), PART_VERSION])
    if cache.fresh(out, key):
        return out, key
    log.info("subsetting %s (%d code points)", fam, len(cps))
    font = TTFont(src)
    opts = subset.Options()
    opts.layout_features = []
    opts.layout_closure = False
    opts.glyph_names = True
    opts.notdef_outline = True
    opts.hinting = False
    opts.name_IDs = ["*"]
    opts.drop_tables += ["GSUB", "GPOS", "GDEF", "BASE", "vmtx", "vhea", "VORG", "VVAR",
                         "MVAR", "STAT", "gasp", "DSIG", "meta", "kern"]
    s = subset.Subsetter(opts)
    s.populate(unicodes=cps)
    s.subset(font)
    font.save(out)
    cache.mark(out, key)
    return out, key


def _recentered(sub: Path, skey: str) -> Path:
    """Source subset VF with its wght axis limited to Polaron's range and the
    default moved to 400 (fontTools "L3" instancing).  Its gvar then holds the
    weight deltas relative to wght 400 directly, IUP-optimised by the source
    compiler.  avar is dropped: Polaron's normalization is linear between the
    sparse masters (extremes and default are exact either way)."""
    lo, d, hi = config.AXES["wght"]
    vf = TTFont(sub)
    ax = next(a for a in vf["fvar"].axes if a.axisTag == "wght")
    lim = (max(lo, ax.minValue), d, min(hi, ax.maxValue))
    out = sub.with_name(sub.stem.replace(".subset", "") + ".recentered.ttf")
    key = cache.make_key(["cjk-l3", skey, lim, PART_VERSION])
    if cache.fresh(out, key):
        return out
    log.info("re-centering %s on wght %s", sub.name, lim)
    inst = instancer.instantiateVariableFont(vf, {"wght": lim}, inplace=True,
                                             overlap=OverlapMode.KEEP_AND_SET_FLAGS,
                                             updateFontNames=False)
    if "avar" in inst:
        del inst["avar"]
    inst.save(out)
    cache.mark(out, key)
    return out


# --------------------------------------------------------------------------
# part VF


def _fit(coords: np.ndarray, src_adv: int, n: int, wdth: float) -> np.ndarray:
    """Affine x-fit of a glyph into n cells at ``wdth`` (centered on the
    source advance box, so CJK punctuation keeps its position in the em)."""
    cell = config.cell_width(wdth)
    s = min(X_STRETCH_MAX, cell / NATURAL_CELL)
    out = coords.copy()
    out[:, 0] = s * (coords[:, 0] - src_adv / 2) + n * cell / 2
    return np.round(out)


def _norm(axis: str, value: float) -> float:
    lo, d, hi = config.AXES[axis]
    if value < d:
        return (value - d) / (d - lo)
    return (value - d) / (hi - d)


def build_cjk_part(style: str, out_path=None) -> Path:
    """Build (or reuse) the CJK part VF for ``style``; returns its path.

    Weight: the source's own gvar deltas (re-centered on wght 400) are copied
    verbatim -- at wdth 100 the x-fit is a pure translation, which leaves
    deltas unchanged.  Width: one tuple per wdth extreme with the affine fit's
    deltas (IUP compresses those to a handful of points per contour).
    """
    out = Path(out_path) if out_path else _part_dir(style) / f"PolaronCJK-{style}-part.ttf"
    chosen, report = assign_codepoints(style)
    by_src = {i: sorted(cp for cp, s in chosen.items() if s == i) for i in (0, 1)}
    subs = {i: _subset_source(style, i, cps) for i, cps in by_src.items() if cps}
    key = cache.make_key(["cjk-part", [subs[i][1] for i in sorted(subs)], style, PART_VERSION,
                          cache.code_hash("cjk.py"), config.SPARSE_MASTERS])
    if cache.fresh(out, key):
        return out
    src = {i: TTFont(_recentered(*subs[i])) for i in subs}
    _dw, dd = config.DEFAULT
    if min(X_STRETCH_MAX, config.cell_width(dd) / NATURAL_CELL) != 1:
        raise AssertionError("default-width CJK fit must be a pure translation")
    widths = sorted({d for _w, d in config.SPARSE_MASTERS if d != dd})

    entries = {}  # (src, srcname) -> [cps]
    for i in subs:
        cmap = src[i].getBestCmap()
        for cp in by_src[i]:
            if cp in cmap:
                entries.setdefault((i, cmap[cp]), []).append(cp)
    items = sorted(entries.items(), key=lambda kv: min(kv[1]))
    order = [".notdef"]
    cmap_out, meta = {}, {".notdef": (min(subs), ".notdef", [])}
    for (i, src_name), cps in items:
        name = f"cjk.u{min(cps):04X}"
        order.append(name)
        meta[name] = (i, src_name, cps)
        for cp in cps:
            cmap_out[cp] = name

    glyphs, advances, variations = {}, {}, {}
    for name in order:
        i, src_name, cps = meta[name]
        f = src[i]
        src_adv = f["hmtx"][src_name][0]
        n = max((cells_for(cp) for cp in cps), default=1) if src_adv else 0
        c0, ends, flags = geo.glyph_arrays(f["glyf"], src_name)
        base_adv = n * config.cell_width(dd)
        d0 = _fit(c0, src_adv, n, dd) if len(c0) else c0
        glyphs[name] = geo.make_simple_glyph(d0, ends, flags)
        advances[name] = base_adv
        npts = len(c0)
        tvs = []
        # weight: copy the source deltas (advance never varies with weight)
        for tv in f["gvar"].variations.get(src_name, []):
            coords = list(tv.coordinates[:npts]) + [None] * 4
            if any(c is not None and c != (0, 0) for c in coords):
                tvs.append(TupleVariation(dict(tv.axes), coords))
        # width: affine fit deltas
        orig = [tuple(p) for p in d0.astype(int).tolist()] + [(0, 0), (base_adv, 0), (0, 0), (0, 0)]
        for d in widths:
            md = _fit(c0, src_adv, n, d) if npts else c0
            delta = [tuple(v) for v in (md - d0).astype(int).tolist()]
            delta += [(0, 0), (n * config.cell_width(d) - base_adv, 0), (0, 0), (0, 0)]
            if not any(dx or dy for dx, dy in delta):
                continue
            opt = iup_delta_optimize(delta, orig, list(ends), tolerance=IUP_TOLERANCE)
            p = _norm("wdth", d)
            tvs.append(TupleVariation({"wdth": (min(p, 0), p, max(p, 0))}, list(opt)))
        variations[name] = tvs

    fb = FontBuilder(config.UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap_out)
    fb.setupGlyf(glyphs, validateGlyphFormat=False)
    glyf = fb.font["glyf"]
    fb.setupHorizontalMetrics({g: (advances[g], glyf[g].xMin if glyf[g].numberOfContours else 0)
                               for g in order})
    fb.setupHorizontalHeader(ascent=config.TYPO_ASC, descent=config.TYPO_DESC)
    fam = f"Polaron CJK {style.title()}"
    fb.setupNameTable({"familyName": fam, "styleName": "Regular",
                       "copyright": "Derived from Noto CJK, Copyright 2014-2021 Adobe "
                                    "(http://www.adobe.com/), SIL Open Font License 1.1."})
    fb.setupOS2(sTypoAscender=config.TYPO_ASC, sTypoDescender=config.TYPO_DESC, sTypoLineGap=0,
                usWinAscent=config.TYPO_ASC, usWinDescent=-config.TYPO_DESC,
                sxHeight=config.XHEIGHT, sCapHeight=config.CAP)
    fb.setupPost()
    fb.setupFvar([(tag, *config.AXES[tag], config.AXIS_NAMES[tag]) for tag in AXIS_TAGS], [])
    fb.setupGvar(variations)
    font = fb.font
    font["OS/2"].recalcUnicodeRanges(font)
    font["OS/2"].recalcCodePageRanges(font)
    add_HVAR(font)
    font.save(out)
    cache.mark(out, key)
    rep = out.with_name(out.stem + ".report.json")
    rep.write_text(json.dumps({"groups": report, "glyphs": len(order),
                               "size": out.stat().st_size}, indent=1), encoding="utf-8")
    return out


# --------------------------------------------------------------------------
# insert into a main VF


def insert_vf_glyphs(main_vf: TTFont, part_vf: TTFont) -> None:
    """Glyph-level merge of ``part_vf`` into ``main_vf`` (in place).

    Copies outlines (+gvar), hmtx and cmap entries (the main font's existing
    cmap entries win), updates glyph order, maxp, OS/2 ranges and rebuilds
    HVAR.  Both fonts must have the same fvar axes.  Raises ``ValueError`` if
    a glyph name collides or the result would exceed 65535 glyphs.
    """
    ax_main = [(a.axisTag, a.minValue, a.defaultValue, a.maxValue) for a in main_vf["fvar"].axes]
    ax_part = [(a.axisTag, a.minValue, a.defaultValue, a.maxValue) for a in part_vf["fvar"].axes]
    if ax_main != ax_part:
        raise ValueError(f"fvar axes differ: {ax_main} vs {ax_part}")
    if main_vf["head"].unitsPerEm != part_vf["head"].unitsPerEm:
        raise ValueError("unitsPerEm differs")
    main_order = list(main_vf.getGlyphOrder())
    have = set(main_order)
    new = [g for g in part_vf.getGlyphOrder() if g != ".notdef"]
    clash = [g for g in new if g in have]
    if clash:
        raise ValueError(f"glyph names already in main font: {clash[:10]}")
    total = len(main_order) + len(new)
    if total > 0xFFFF:
        raise ValueError(
            f"glyph limit exceeded: main font has {len(main_order)} glyphs, CJK part adds "
            f"{len(new)} -> {total} > 65535; lower cjk.MAX_GLYPHS or drop scripts")
    glyf, pglyf = main_vf["glyf"], part_vf["glyf"]
    hmtx, phmtx = main_vf["hmtx"], part_vf["hmtx"]
    gvar, pgvar = main_vf["gvar"], part_vf["gvar"]
    order = main_order + new
    for g in new:
        glyf.glyphs[g] = pglyf[g]
        hmtx.metrics[g] = phmtx.metrics[g]
        gvar.variations[g] = pgvar.variations.get(g, [])
    main_vf.setGlyphOrder(order)
    glyf.glyphOrder = order
    main_vf["maxp"].numGlyphs = len(order)
    mapping = dict(main_vf.getBestCmap())
    for cp, g in part_vf.getBestCmap().items():
        if g != ".notdef":
            mapping.setdefault(cp, g)
    uvs = next((st for st in main_vf["cmap"].tables if st.format == 14), None)
    main_vf["cmap"] = fontmerge.build_cmap(mapping, uvs)
    if "post" in main_vf and main_vf["post"].formatType == 2.0:
        main_vf["post"].extraNames = []
        main_vf["post"].mapping = {}
    if "vmtx" in main_vf:
        for g in new:
            main_vf["vmtx"].metrics[g] = (config.UPM, 0)
    for tag in ("hdmx", "LTSH", "VDMX"):
        if tag in main_vf:
            del main_vf[tag]
    os2 = main_vf["OS/2"]
    os2.recalcUnicodeRanges(main_vf)
    os2.recalcCodePageRanges(main_vf)
    add_HVAR(main_vf)
