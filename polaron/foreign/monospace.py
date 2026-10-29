"""Refit Noto scripts to Polaron's monospace cell grid (non-CJK scripts).

Pipeline per style and script (all intermediate files cached under
``build/foreign/<style>/<script>/``):

1. **subset** the source VF once: the script's code points, shaping features
   only, the script's OpenType script tags only (``layout_closure`` keeps
   every glyph reachable through GSUB).  FeatureVariations are removed first
   so GSUB is identical at every weight.
2. **instance** the subset VF at each needed weight (clamped to the source
   range) and at one source width per script (``src_wdth``; condensed when
   that fits the cell better), then rename glyphs (``<script>.<name>``) and
   decompose composites.
3. **plan** (decided once, from the default master): which glyphs are marks
   (advance 0), how many cells every spacing glyph gets, which glyphs get
   joining bars (Arabic) or headline extensions (Devanagari, Bengali,
   Gurmukhi), plus the script's vertical scale.
4. **refit** each master: per-glyph affine transform ``x' = sx*x + tx``,
   ``y' = sy*y + ty`` so the ink sits centered in its cells; bars are added
   as extra contours (present at every master, so outlines stay
   point-compatible); every GPOS anchor gets the same transform as the glyph
   that owns it; kerning/cursive spacing/advance adjustments are removed.
5. **merge** all scripts of a master into one static TTF.

Public entry point: :func:`build_foreign_masters`.
"""

from __future__ import annotations

import json
import logging
import statistics
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont, newTable
from fontTools.varLib import instancer
from fontTools.varLib.instancer import OverlapMode

from .. import config
from . import cache, fetch, fontmerge, otl
from . import geometry as geo
from .scripts import GPOS_FEATURES, GSUB_FEATURES, SCRIPTS, SHARED, ScriptSpec

log = logging.getLogger("polaron.foreign")

CODE_FILES = ("monospace.py", "scripts.py", "otl.py", "geometry.py", "fontmerge.py", "cache.py")
# Bump when subset_vf()/instance_path() change behaviour (their cache keys do
# not hash the whole code base, so plan tweaks do not re-instance sources).
SUBSET_VERSION = 1

SRC_WDTH_STEPS = (62.5, 75.0, 87.5, 100.0)
NARROW_TARGET = 0.80   # auto src_wdth: widest width whose median letter ink <= this * cell(100)
MARGIN = 0.04          # minimum side margin, fraction of one cell
MAX_STRETCH = 1.12     # never widen glyphs more than this (relative to sy)
BAR_OUT = 4            # joining bars poke this far past the cell edge (avoids AA seams)
CELL_BIAS = 0.15       # n = round(natural_advance / natural_cell + CELL_BIAS), capped
SHARED_NAMES = set(SHARED.values())

NON_SPACING_CATS = {"Mn", "Me", "Cf"}
NO_HEADLINE_CATS = {"Nd", "No", "Po", "Ps", "Pe", "Pd", "Pc", "Pi", "Pf", "So", "Sc", "Sk", "Sm"}


def code_key() -> str:
    return cache.code_hash(*CODE_FILES)


def _script_dir(style: str, spec: ScriptSpec) -> Path:
    d = cache.BUILD_DIR / style / spec.key
    d.mkdir(parents=True, exist_ok=True)
    return d


def _axes(font: TTFont) -> dict[str, tuple[float, float, float]]:
    if "fvar" not in font:
        return {}
    return {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in font["fvar"].axes}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# --------------------------------------------------------------------------
# 1. subset


def subset_vf(spec: ScriptSpec, style: str) -> tuple[Path, str]:
    """Subset the source VF to the script; returns (path, cache key)."""
    src = fetch.font_path(style, spec.family[style])
    if not src.exists():
        fetch.fetch_sources((style,))
    out = _script_dir(style, spec) / "subset.ttf"
    sig = [spec.family[style], spec.ranges, spec.extra, spec.ot_scripts, spec.drop_features,
           sorted(SHARED), sorted(GSUB_FEATURES), sorted(GPOS_FEATURES)]
    key = cache.make_key(["subset", fetch.source_sha256(src), sig, style, SUBSET_VERSION])
    if cache.fresh(out, key):
        return out, key
    font = TTFont(src)
    for tag in ("GSUB", "GPOS"):
        if tag in font:
            t = font[tag].table
            if getattr(t, "FeatureVariations", None) is not None:
                t.FeatureVariations = None
                t.Version = 0x00010000
    opts = subset.Options()
    opts.layout_features = sorted((GSUB_FEATURES | GPOS_FEATURES) - set(spec.drop_features))
    opts.layout_scripts = list(spec.ot_scripts)
    opts.layout_closure = True
    opts.glyph_names = True
    opts.notdef_outline = True
    opts.notdef_glyph = True
    opts.hinting = False
    opts.legacy_kern = False
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.drop_tables += ["vmtx", "vhea", "VVAR", "MVAR", "STAT", "meta", "BASE",
                         "gasp", "DSIG", "kern", "VORG", "hdmx", "LTSH", "VDMX"]
    opts.prune_unicode_ranges = True
    wanted = spec.codepoints()
    unicodes = sorted(cp for cp in font.getBestCmap() if cp in wanted)
    s = subset.Subsetter(opts)
    s.populate(unicodes=unicodes)
    s.subset(font)
    font.save(out)
    cache.mark(out, key)
    return out, key


# --------------------------------------------------------------------------
# 2. instances


def _ref_letters(font: TTFont, spec: ScriptSpec) -> list[str]:
    """Glyph names of the script's plain letters (Lo, not marks)."""
    cmap = font.getBestCmap()
    gdef = font["GDEF"].table.GlyphClassDef.classDefs if "GDEF" in font else {}
    out = []
    for cp, g in sorted(cmap.items()):
        if 0xFB00 <= cp <= 0xFEFF:  # presentation forms are not typical letters
            continue
        if spec.owns(cp) and unicodedata.category(chr(cp)) == "Lo" and gdef.get(g) != 3:
            out.append(g)
    return out


def _median_ink(font: TTFont, names: list[str]) -> float:
    glyf = font["glyf"]
    ws = []
    for g in names:
        c, _, _ = geo.glyph_arrays(glyf, g)
        if len(c):
            ws.append(float(c[:, 0].max() - c[:, 0].min()))
    return statistics.median(ws) if ws else 500.0


def choose_src_wdth(spec: ScriptSpec, style: str) -> float | None:
    """Source width used for every master of this script (None: no wdth axis)."""
    sub, skey = subset_vf(spec, style)
    vf = TTFont(sub)
    axes = _axes(vf)
    if "wdth" not in axes:
        return None
    lo, dflt, hi = axes["wdth"]
    explicit = spec.src_wdth.get(style)
    if explicit is not None:
        return float(_clamp(explicit, lo, hi))
    memo = sub.with_name("src_wdth.json")
    key = cache.make_key(["srcw", skey, NARROW_TARGET])
    if memo.exists():
        d = json.loads(memo.read_text())
        if d.get("key") == key:
            return d["src_wdth"]
    wl, wd, wh = axes["wght"]
    target = NARROW_TARGET * config.cell_width(100) / spec.vscale.get(style, 1.0)
    steps = sorted({w for w in SRC_WDTH_STEPS if lo <= w <= hi} | {lo})
    best, meds = steps[0], {}
    for w in steps:
        inst = instancer.instantiateVariableFont(
            TTFont(sub), {"wght": _clamp(400, wl, wh), "wdth": w}, updateFontNames=False)
        med = _median_ink(inst, _ref_letters(inst, spec))
        meds[w] = med
        if med <= target:
            best = w
    memo.write_text(json.dumps({"key": key, "src_wdth": best, "median_ink": meds}, indent=1))
    return best


def instance_path(spec: ScriptSpec, style: str, wght: float, src_wdth: float | None) -> Path:
    sub, skey = subset_vf(spec, style)
    vf = TTFont(sub)
    axes = _axes(vf)
    w = float(_clamp(wght, *axes["wght"][::2])) if "wght" in axes else None
    name = f"inst-w{w:g}" + (f"-d{src_wdth:g}" if src_wdth is not None else "") + ".ttf"
    out = sub.with_name(name)
    key = cache.make_key(["inst", skey, w, src_wdth])
    if cache.fresh(out, key):
        return out
    loc = {}
    if w is not None:
        loc["wght"] = w
    if src_wdth is not None:
        loc["wdth"] = src_wdth
    for tag in axes:
        if tag not in loc:
            loc[tag] = axes[tag][1]
    inst = instancer.instantiateVariableFont(
        vf, loc, inplace=True, overlap=OverlapMode.KEEP_AND_SET_FLAGS, updateFontNames=False)
    for tag in ("STAT", "avar"):
        if tag in inst:
            del inst[tag]
    inst.save(out)
    cache.mark(out, key)
    return out


def load_instance(spec: ScriptSpec, style: str, wght: float, src_wdth: float | None) -> TTFont:
    """Instance at (wght, src_wdth), glyphs renamed with the script prefix and decomposed."""
    f = TTFont(instance_path(spec, style, wght, src_wdth))
    cmap = f.getBestCmap()
    shared = {cmap[cp]: name for cp, name in SHARED.items() if cp in cmap}

    def rename(g):
        if g == ".notdef":
            return g
        return shared.get(g, spec.prefix + g)

    f = otl.renamed_font(f, rename)
    geo.decompose_all(f)
    return f


# --------------------------------------------------------------------------
# 3. plan


def _gsub_edges(font: TTFont):
    """(lookup index, kind, inputs, outputs) for every GSUB rule."""
    if "GSUB" not in font:
        return []
    edges = []
    for i, lk in enumerate(font["GSUB"].table.LookupList.Lookup):
        for st, t in otl.iter_subtables(lk, "GSUB"):
            if t == 1:
                for a, b in st.mapping.items():
                    edges.append((i, "single", [a], [b]))
            elif t == 2:
                for a, bs in st.mapping.items():
                    edges.append((i, "single" if len(bs) == 1 else "multi", [a], list(bs)))
            elif t == 3:
                for a, alts in st.alternates.items():
                    for b in alts:
                        edges.append((i, "single", [a], [b]))
            elif t == 4:
                for first, ligs in st.ligatures.items():
                    for lg in ligs:
                        edges.append((i, "lig", [first] + list(lg.Component), [lg.LigGlyph]))
            elif t == 8:
                for a, b in zip(st.Coverage.glyphs, st.Substitute):
                    edges.append((i, "single", [a], [b]))
    return edges


def _cp_components(cp: int) -> int:
    """Number of spacing code points a single code point stands for."""
    ch = chr(cp)
    if unicodedata.category(ch) in NON_SPACING_CATS:
        return 0
    dec = unicodedata.decomposition(ch)
    if dec:
        parts = dec.split()
        if parts[0].startswith("<"):
            if parts[0] not in ("<isolated>", "<initial>", "<medial>", "<final>", "<compat>"):
                return 1
            parts = parts[1:]
        n = sum(1 for p in parts if unicodedata.category(chr(int(p, 16))) not in NON_SPACING_CATS)
        return max(1, n)
    return 1


def _fixpoint(update, rounds=20):
    for _ in range(rounds):
        if not update():
            return


@dataclass
class Plan:
    """Decisions made once (default master) and applied at every master."""

    script: str
    style: str
    src_wdth: float | None
    sy: float
    ty: float
    natural_cell: float
    zero: list = field(default_factory=list)          # 0-advance glyphs
    cells: dict = field(default_factory=dict)         # spacing glyph -> n cells
    ref: list = field(default_factory=list)           # glyphs defining the typical ink width
    bars: dict = field(default_factory=dict)          # glyph -> [[side, point index], ...]
    band: dict = field(default_factory=dict)          # how to measure the bar band per master
    pairs: list = field(default_factory=list)         # [[visual left, visual right]] refitted jointly
    hang: list = field(default_factory=list)          # 0-advance glyphs hanging over the previous cell
    over: dict = field(default_factory=dict)          # glyph -> cells its hook reaches over (i-matra)
    stats: dict = field(default_factory=dict)


def _glyph_info(font: TTFont, spec: ScriptSpec):
    """Per-glyph spacing components, Unicode category and (Arabic) join flags."""
    order = font.getGlyphOrder()
    hmtx = font["hmtx"]
    gdef = font["GDEF"].table.GlyphClassDef.classDefs if "GDEF" in font else {}
    cmap = font.getBestCmap()
    # Advance 0 in the source <=> advance 0 here.  (Some Indic fonts class
    # spacing vowel signs as GDEF marks *with* an advance; HarfBuzz keeps that
    # advance for Indic scripts, so they stay spacing.)
    zero = {g for g in order if hmtx[g][0] == 0}
    comp: dict[str, int] = {}
    cat: dict[str, str] = {}
    for cp, g in cmap.items():
        comp[g] = max(comp.get(g, 0), _cp_components(cp))
        c = unicodedata.category(chr(cp))
        if g not in cat or (c.startswith("L") and not cat[g].startswith("L")):
            cat[g] = c
    edges = _gsub_edges(font)

    def spacing(g):
        return g not in zero

    def cval(g):
        return comp.get(g, 1 if spacing(g) else 0)

    def upd_comp():
        ch = False
        for _i, kind, ins, outs in edges:
            if kind == "single":
                v = cval(ins[0])
                if comp.get(outs[0], -1) < v:
                    comp[outs[0]] = v
                    ch = True
            elif kind == "multi":
                for b in outs:
                    v = 1 if spacing(b) else 0
                    if comp.get(b, -1) < v:
                        comp[b] = v
                        ch = True
            else:
                v = sum(cval(c) for c in ins)
                if comp.get(outs[0], -1) < v:
                    comp[outs[0]] = v
                    ch = True
        return ch

    def upd_cat():
        ch = False
        for _i, kind, ins, outs in edges:
            src = next((cat[c] for c in ins if c in cat and cat[c].startswith("L")), None)
            if src is None:
                src = next((cat[c] for c in ins if c in cat), None)
            if src is None:
                continue
            for b in outs:
                if b not in cat or (src.startswith("L") and not cat[b].startswith("L")):
                    cat[b] = src
                    ch = True
        return ch

    _fixpoint(upd_comp)
    _fixpoint(upd_cat)

    join: dict[str, int] = {}  # bit 1: joins left (to next letter), bit 2: joins right
    if spec.joining == "arabic":
        fl = otl.feature_lookups(font["GSUB"].table)
        seeds = {"init": 1, "medi": 3, "fina": 2}
        for feat, bits in seeds.items():
            for _i, kind, ins, outs in edges:
                if _i in fl.get(feat, ()) and kind == "single":
                    join[outs[0]] = join.get(outs[0], 0) | bits
        tat = cmap.get(0x0640)
        if tat:
            join[tat] = 3

        def upd_join():
            ch = False
            for _i, kind, ins, outs in edges:
                if kind == "single":
                    v = join.get(ins[0], 0)
                elif kind == "lig":
                    sp = [c for c in ins if spacing(c)] or ins
                    v = (join.get(sp[0], 0) & 2) | (join.get(sp[-1], 0) & 1)
                else:
                    continue
                if v and (join.get(outs[0], 0) | v) != join.get(outs[0], 0):
                    join[outs[0]] = join.get(outs[0], 0) | v
                    ch = True
            return ch

        _fixpoint(upd_join)
        for g in order:  # naming fallback
            if g not in join and spacing(g):
                if ".init" in g:
                    join[g] = 1
                elif ".medi" in g:
                    join[g] = 3
                elif ".fina" in g:
                    join[g] = 2
        join = {g: v for g, v in join.items() if spacing(g)}
    pairs = _rlig_pairs(font, join) if spec.joining == "arabic" else []
    return zero, comp, cat, join, pairs


def _rlig_pairs(font: TTFont, join: dict) -> list[list[str]]:
    """Two-glyph lam-alef style pairs: [visual left, visual right].

    Noto Arabic fonts form lam-alef with a contextual 'rlig' rule that
    substitutes *both* glyphs (lam -> lam.rlig, alef -> alef.rlig); the two
    results are drawn to be read as one shape and must be refitted together.
    """
    gsub = font["GSUB"].table
    lookups = gsub.LookupList.Lookup
    fl = otl.feature_lookups(gsub)

    def single_map(i):
        m = {}
        for st, t in otl.iter_subtables(lookups[i], "GSUB"):
            if t == 1:
                m.update(st.mapping)
            elif t == 2:
                m.update({a: b[0] for a, b in st.mapping.items() if len(b) == 1})
        return m

    pairs, used = [], set()
    for i in sorted(fl.get("rlig", ())):
        for st, t in otl.iter_subtables(lookups[i], "GSUB"):
            if t not in (5, 6) or st.Format != 3:
                continue
            covs = st.Coverage if t == 5 else st.InputCoverage
            recs = {r.SequenceIndex: r.LookupListIndex for r in st.SubstLookupRecord}
            if len(covs) != 2 or set(recs) != {0, 1}:
                continue
            m0, m1 = single_map(recs[0]), single_map(recs[1])
            for g0 in covs[0].glyphs:
                for g1 in covs[1].glyphs:
                    first, second = m0.get(g0), m1.get(g1)
                    if not first or not second or first in used or second in used:
                        continue
                    # logical first joins left (to the next), second joins right
                    if join.get(first, 0) & 1 and join.get(second, 0) & 2:
                        pairs.append([second, first])
                        used.update((first, second))
    return pairs


def _band_points(coords, flags, y0, y1, tol):
    on = np.array([bool(f & 1) for f in flags])
    idx = np.where(on & (coords[:, 1] >= y0 - tol) & (coords[:, 1] <= y1 + tol))[0]
    return idx


def _headline(font: TTFont, ref: str):
    """Headline band of the reference consonant: (bottom, top, top_pts, bottom_pts)."""
    glyf = font["glyf"]
    c, e, f = geo.glyph_arrays(glyf, ref)
    mask, x0, y0, sc = geo.raster(geo.flatten(c, e, f), scale=0.5)
    cols = mask.any(axis=0)
    width = cols.sum()
    cover = mask.sum(axis=1) / max(width, 1)
    rows = np.where(mask.any(axis=1))[0]
    r = rows.max()
    top_r = r
    while r >= 0 and cover[r] >= 0.8:
        r -= 1
    bot_r = r + 1
    top = y0 + (top_r + 1) / sc
    bot = y0 + bot_r / sc
    t = top - bot
    ys = c[:, 1]
    top_pts = [int(i) for i in np.where(np.abs(ys - top) <= max(4, 0.12 * t))[0]]
    bot_pts = [int(i) for i in np.where(np.abs(ys - bot) <= max(4, 0.12 * t))[0]]
    return bot, top, top_pts, bot_pts


def _headline_slanted(c, e, f, bot, top) -> bool:
    """True when the reference glyph's headline ends are slanted."""
    t = top - bot
    mask, x0, y0, sc = geo.raster(geo.flatten(c, e, f), scale=0.5)
    ycent = y0 + (np.arange(mask.shape[0]) + 0.5) / sc
    rows = np.where((ycent >= bot + 0.1 * t) & (ycent <= top - 0.1 * t))[0]
    shifts = []
    for side in (0, 1):
        edge = []
        for r in rows:
            cols = np.where(mask[r])[0]
            if len(cols):
                edge.append(cols.min() if side == 0 else cols.max())
        if edge:
            shifts.append((max(edge) - min(edge)) / sc)
    return bool(shifts) and bool(max(shifts) > 0.3 * t)


def _headline_sides(c, e, f, bot, top, relaxed: bool = False):
    """Which sides of a glyph carry the headline; returns [[side, point index]].

    A side carries the headline when, close to the glyph's ink edge, a run of
    columns fully covers the core of the headline band.  With ``relaxed``
    (fonts whose headline ends are slanted parallelograms) a side may also
    qualify with partly covered columns, provided that part of the headline
    is a free-standing flag (no ink right below the band, which rejects the
    round loop tops of letters like dha/bha).
    """
    t = top - bot
    if len(c) == 0:
        return []
    mask, x0, y0, sc = geo.raster(geo.flatten(c, e, f), scale=0.5)
    ycent = y0 + (np.arange(mask.shape[0]) + 0.5) / sc
    core = (ycent >= bot + 0.2 * t) & (ycent <= top - 0.2 * t)
    below = (ycent >= bot - 0.8 * t) & (ycent <= bot - 0.15 * t)
    ink = np.where(mask.any(axis=0))[0]
    if not core.any() or len(ink) == 0:
        return []
    cmin, cmax = ink.min(), ink.max()
    slack = max(0.25 * (cmax - cmin), 1.5 * t * sc)
    strict_cols = mask[core].all(axis=0)
    loose_cols = mask[core].mean(axis=0) >= 0.55
    below_ink = mask[below].mean(axis=0) if below.any() else np.zeros(mask.shape[1])

    def runs(cols, run):
        win = np.convolve(cols.astype(int), np.ones(run, int), mode="valid") == run
        return np.where(win)[0]

    def side_col(side):
        """Column where the headline ends on ``side`` (or None)."""
        run = max(int(round(1.2 * t * sc)), 4)
        st = runs(strict_cols, run)
        if len(st):
            col = st.min() if side == "L" else st.max() + run - 1
            if (col - cmin if side == "L" else cmax - col) <= slack:
                return col
        if not relaxed:
            return None
        run = max(int(round(0.9 * t * sc)), 4)
        st = runs(loose_cols, run)
        if not len(st):
            return None
        first = st.min() if side == "L" else st.max()
        col = first if side == "L" else first + run - 1
        if (col - cmin if side == "L" else cmax - col) > slack:
            return None
        span = slice(first, first + run)
        if below_ink[span].mean() > 0.15:
            return None
        return col

    on = np.array([bool(v & 1) for v in f])
    band_idx = np.where(on & (c[:, 1] >= bot - 0.3 * t) & (c[:, 1] <= top + 0.3 * t))[0]
    if len(band_idx) == 0:
        return []
    out = []
    for side in ("L", "R"):
        col = side_col(side)
        if col is None:
            continue
        x = x0 + (col + 0.5) / sc
        bias = 0.001 * c[band_idx, 0] * (1 if side == "L" else -1)
        p = band_idx[np.argmin(np.abs(c[band_idx, 0] - x) + bias)]
        out.append([side, int(p)])
    return out


def make_plan(spec: ScriptSpec, style: str) -> Plan:
    """Analyse the default master and decide cells/bars (cached as JSON)."""
    src_wdth = choose_src_wdth(spec, style)
    _sub, skey = subset_vf(spec, style)
    memo = _script_dir(style, spec) / f"plan-{src_wdth}.json"
    key = cache.make_key(["plan", skey, src_wdth, code_key()])
    if memo.exists():
        d = json.loads(memo.read_text(encoding="utf-8"))
        if d.get("_key") == key:
            d.pop("_key")
            return Plan(**d)
    font = load_instance(spec, style, config.DEFAULT[0], src_wdth)
    order = font.getGlyphOrder()
    glyf, hmtx = font["glyf"], font["hmtx"]
    zero, comp, cat, join, pairs = _glyph_info(font, spec)
    sy = spec.vscale.get(style, 1.0)
    ty = spec.voffset.get(style, 0.0)
    arrays = {g: geo.glyph_arrays(glyf, g) for g in order}
    letters = [g for g in _ref_letters(font, spec) if g not in zero]
    nat = statistics.median(hmtx[g][0] for g in letters) if letters else 600.0
    gdef = font["GDEF"].table.GlyphClassDef.classDefs if "GDEF" in font else {}
    hang, over = [], {}
    if spec.overhang:
        for g in order:
            c = arrays[g][0]
            if g in zero or not len(c) or g == ".notdef":
                continue
            x0, x1, a = float(c[:, 0].min()), float(c[:, 0].max()), hmtx[g][0]
            w = x1 - x0
            if gdef.get(g) == 3 and -x0 > 0.5 * w and x1 < 0.6 * nat:
                hang.append(g)          # subscript / i-sign drawn over the previous glyph
            elif x1 - a > 0.35 * nat and x0 > -0.15 * nat:
                over[g] = max(1, int(round((x1 - a) / nat)))   # i-matra hook
        zero = zero | set(hang)
    # glyphs defining the typical ink width (plain letters and their forms)
    ref = [g for g in order if g not in zero and comp.get(g, 1) <= 1 and len(arrays[g][0])
           and cat.get(g, "Lo")[0] in "LM" and g != ".notdef"]
    cells = {}
    for g in order:
        if g in zero:
            continue
        k = max(1, comp.get(g, 1))
        cells[g] = int(_clamp(round(hmtx[g][0] / nat + CELL_BIAS), 1, k))
    bars: dict[str, list] = {}
    band: dict = {}
    if spec.joining == "arabic":
        tat = font.getBestCmap()[0x0640]
        tc = arrays[tat][0]
        b0, b1 = float(tc[:, 1].min()), float(tc[:, 1].max())
        band = {"kind": "tatweel", "glyph": tat}
        tol = 0.3 * (b1 - b0)
        for g, bits in join.items():
            c, e, f = arrays[g]
            idx = _band_points(c, f, b0, b1, tol)
            if len(idx) == 0:
                continue
            sides = []
            if bits & 1:
                sides.append(["L", int(idx[np.argmin(c[idx, 0])])])
            if bits & 2:
                sides.append(["R", int(idx[np.argmax(c[idx, 0])])])
            bars[g] = sides
        for left, right in pairs:  # the pair joins through its own shapes
            bars[left] = [b for b in bars.get(left, []) if b[0] != "R"]
            bars[right] = [b for b in bars.get(right, []) if b[0] != "L"]
            for g in (left, right):
                if not bars[g]:
                    del bars[g]
    elif spec.joining == "headline":
        ref_g = font.getBestCmap()[ord(spec.headline_ref)]
        bot, top, tp, bp = _headline(font, ref_g)
        # are the headline ends vertical, or slanted (serif parallelograms)?
        relaxed = _headline_slanted(*arrays[ref_g], bot, top)
        band = {"kind": "headline", "glyph": ref_g, "top": tp, "bot": bp,
                "default": [bot, top], "relaxed": relaxed}
        for g in order:
            if g in zero or cat.get(g, "Lo") in NO_HEADLINE_CATS or g == ".notdef":
                continue
            sides = _headline_sides(*arrays[g], bot, top, relaxed)
            if sides:
                bars[g] = sides
    plan = Plan(
        script=spec.key, style=style, src_wdth=src_wdth, sy=sy, ty=ty,
        natural_cell=float(nat), zero=sorted(zero), cells=cells, ref=ref,
        bars=bars, band=band, pairs=pairs, hang=hang, over=over,
        stats={
            "glyphs": len(order),
            "marks": len(zero),
            "multi_cell": sum(1 for v in cells.values() if v > 1),
            "with_bars": len(bars),
            "hanging": len(hang),
            "overhanging": len(over),
        },
    )
    d = asdict(plan)
    d["_key"] = key
    memo.write_text(json.dumps(d, indent=0, ensure_ascii=False), encoding="utf-8")
    return plan


# --------------------------------------------------------------------------
# 4. refit


def _band_at_master(font: TTFont, plan: Plan, arrays) -> tuple[float, float] | None:
    b = plan.band
    if not b:
        return None
    c = arrays[b["glyph"]][0]
    if b["kind"] == "tatweel":
        return float(c[:, 1].min()), float(c[:, 1].max())
    top = float(np.median(c[b["top"], 1])) if b["top"] else b["default"][1]
    bot = float(np.median(c[b["bot"], 1])) if b["bot"] else b["default"][0]
    return bot, top


def refit(font: TTFont, spec: ScriptSpec, plan: Plan, cell: int) -> dict:
    """Refit one renamed+decomposed instance to ``cell`` in place.

    Returns per-glyph transforms ``{glyph: (sx, tx)}`` (``sy``/``ty`` are
    script-wide).
    """
    glyf, hmtx = font["glyf"], font["hmtx"]
    order = font.getGlyphOrder()
    sy, ty = plan.sy, plan.ty
    zero = set(plan.zero)
    arrays = {g: geo.glyph_arrays(glyf, g) for g in order}
    inks = [float(np.ptp(arrays[g][0][:, 0])) for g in plan.ref if len(arrays[g][0])]
    med = statistics.median(inks) if inks else cell
    # typical x scale: natural proportions at wdth 100, following the cell
    # width elsewhere (capped), and never more than `fill` of a cell for the
    # median glyph.
    s_typ = min(spec.fill * cell / med, sy * min(cell / config.cell_width(100), MAX_STRETCH))
    margin = MARGIN * cell
    band = _band_at_master(font, plan, arrays)
    T: dict[str, tuple[float, float]] = {}
    adv: dict[str, int] = {}
    fixed = {}
    for left, right in plan.pairs:
        # natural layout: right glyph's origin = left glyph's advance
        cl, cr = arrays[left][0], arrays[right][0]
        al = hmtx[left][0]
        lo = min(cl[:, 0].min(), cr[:, 0].min() + al)
        hi = max(cl[:, 0].max(), cr[:, 0].max() + al)
        n = plan.cells[left] + plan.cells[right]
        sx = min(s_typ, (n * cell - 2 * margin) / max(hi - lo, 1))
        tx = n * cell / 2 - sx * (lo + hi) / 2
        fixed[left] = (sx, tx)
        fixed[right] = (sx, tx + sx * al - plan.cells[left] * cell)
    # right-side gap of a typical centered glyph (where hanging glyphs start)
    gap = max(margin, (cell - s_typ * med) / 2)
    hang = set(plan.hang)
    for g in order:
        c, e, f = arrays[g]
        old_adv = hmtx[g][0]
        if g in fixed:
            a = plan.cells[g] * cell
            sx, tx = fixed[g]
        elif g in hang:
            sx, tx, a = s_typ, -gap, 0
        elif g in zero:
            sx, tx, a = s_typ, 0.0, 0
        elif g in plan.over and len(c):
            # i-matra: hook ends over the right edge of the next glyph's ink
            a = plan.cells[g] * cell
            k = plan.over[g]
            x0, x1 = float(c[:, 0].min()), float(c[:, 0].max())
            sx = s_typ
            reach = min(sx * (x1 - old_adv), k * cell - 2 * margin)
            end = a + (k * cell + reach) / 2
            if end - sx * (x1 - x0) < margin:
                sx = (end - margin) / max(x1 - x0, 1)
            tx = end - sx * x1
        else:
            a = plan.cells[g] * cell
            b = geo.bounds(c)
            if b is None:
                sx = s_typ
                tx = (a - sx * old_adv) / 2
            else:
                w = b[2] - b[0]
                sx = s_typ if w <= 1 else min(s_typ, (a - 2 * margin) / w)
                tx = a / 2 - sx * (b[0] + b[2]) / 2
        T[g], adv[g] = (sx, tx), a
        if len(c) == 0:
            hmtx[g] = (a, 0)
            continue
        nc = np.empty_like(c)
        nc[:, 0] = sx * c[:, 0] + tx
        nc[:, 1] = sy * c[:, 1] + ty
        ends = list(e)
        flags = bytearray(f)
        if band and g in plan.bars:
            by0, by1 = sy * band[0] + ty, sy * band[1] + ty
            ov = max(0.5 * (by1 - by0), 12.0)
            for side, p in plan.bars[g]:
                xe = nc[p, 0]
                if side == "L":
                    x0, x1 = -BAR_OUT, max(xe + ov, ov)
                else:
                    x0, x1 = min(xe - ov, a - ov), a + BAR_OUT
                rc, rf = geo.rect_contour(x0, by0, x1, by1)
                nc = np.vstack([nc, rc])
                flags += rf
                ends.append(len(nc) - 1)
        glyf[g] = geo.make_simple_glyph(nc, ends, flags)
        glyf[g].recalcBounds(glyf)
        hmtx[g] = (a, glyf[g].xMin)
    _fix_gpos(font, T, adv, sy, ty)
    _fix_gdef(font, T)
    return T


def _fix_gpos(font: TTFont, T, adv, sy, ty) -> None:
    if "GPOS" not in font:
        return
    lookups = font["GPOS"].table.LookupList.Lookup
    drop = set()
    for i, lk in enumerate(lookups):
        t = otl.lookup_type(lk, "GPOS")
        if t == 2:
            drop.add(i)
        elif t == 1 and all((st.ValueFormat & otl.VF_PLACEMENT) == 0
                            for st, _ in otl.iter_subtables(lk, "GPOS")):
            drop.add(i)

    def upd():
        ch = False
        for i, lk in enumerate(lookups):
            if i in drop or otl.lookup_type(lk, "GPOS") not in (7, 8):
                continue
            nested = otl.nested_lookups(lk, "GPOS")
            if nested <= drop:
                drop.add(i)
                ch = True
        return ch

    _fixpoint(upd, rounds=100)

    def anchor_fn(owner, x, y, role):
        sx, tx = T[owner]
        ny = sy * y + ty
        if role == "entry":   # cursive: keep vertical relation, no horizontal change
            return 0, ny
        if role == "exit":
            return adv[owner], ny
        return sx * x + tx, ny

    for i, lk in enumerate(lookups):
        if i in drop:
            continue
        for st, t in otl.iter_subtables(lk, "GPOS"):
            if t in (3, 4, 5, 6):
                otl.transform_anchors(st, t, anchor_fn)
            elif t == 1:
                fmt = st.ValueFormat & 0x0F
                glyphs = st.Coverage.glyphs
                vals = [st.Value] * len(glyphs) if st.Format == 1 else st.Value
                new = []
                for g, v in zip(glyphs, vals):
                    sx = T[g][0]
                    xp = getattr(v, "XPlacement", 0) or 0 if v is not None else 0
                    yp = getattr(v, "YPlacement", 0) or 0 if v is not None else 0
                    new.append(otl.new_value(fmt, sx * xp, sy * yp))
                st.Format = 2
                st.ValueFormat = fmt
                st.Value = new
                st.ValueCount = len(new)
    otl.keep_lookups(font, "GPOS", [i for i in range(len(lookups)) if i not in drop])


def _fix_gdef(font: TTFont, T) -> None:
    if "GDEF" not in font:
        return
    g = font["GDEF"].table
    if getattr(g, "VarStore", None) is not None:
        g.VarStore = None
        g.Version = 0x00010002 if getattr(g, "MarkGlyphSetsDef", None) else 0x00010000
    if g.LigCaretList:
        for name, lg in zip(g.LigCaretList.Coverage.glyphs, g.LigCaretList.LigGlyph):
            sx, tx = T[name]
            for cv in lg.CaretValue:
                if cv.Format in (1, 3):
                    cv.Coordinate = int(round(sx * cv.Coordinate + tx))
                    cv.Format = 1
                    if hasattr(cv, "DeviceTable"):
                        del cv.DeviceTable


# --------------------------------------------------------------------------
# 5. masters


def set_vertical_metrics(font: TTFont) -> None:
    hhea, os2 = font["hhea"], font["OS/2"]
    hhea.ascent, hhea.descent, hhea.lineGap = config.TYPO_ASC, config.TYPO_DESC, config.LINE_GAP
    os2.sTypoAscender, os2.sTypoDescender = config.TYPO_ASC, config.TYPO_DESC
    os2.sTypoLineGap = config.LINE_GAP
    os2.usWinAscent, os2.usWinDescent = config.TYPO_ASC, -config.TYPO_DESC
    os2.sxHeight, os2.sCapHeight = config.XHEIGHT, config.CAP
    os2.fsSelection |= 1 << 7  # USE_TYPO_METRICS
    font["post"].isFixedPitch = 0


NOTO_COPYRIGHT = ("Foreign scripts derived from Noto fonts, Copyright 2022 The Noto "
                  "Project Authors (https://github.com/notofonts), SIL Open Font License 1.1.")


def _set_names(font: TTFont, style: str) -> None:
    name = newTable("name")
    name.names = []
    fam = f"Polaron Foreign {style.title()}"
    for nid, s in ((0, NOTO_COPYRIGHT), (1, fam), (2, "Regular"), (3, f"{fam};{config.VERSION}"),
                   (4, fam), (5, f"Version {config.VERSION}"), (6, fam.replace(" ", "")),
                   (13, "This Font Software is licensed under the SIL Open Font License, Version 1.1."),
                   (14, "https://openfontlicense.org")):
        name.setName(s, nid, 3, 1, 0x409)
    font["name"] = name


def build_script_master(spec: ScriptSpec, style: str, wght: int, wdth: int, plan: Plan) -> TTFont:
    font = load_instance(spec, style, wght, plan.src_wdth)
    refit(font, spec, plan, config.cell_width(wdth))
    return font


def _master_name(style: str, wght: int, wdth: int) -> str:
    return f"PolaronForeign-{style}-wght{wght}-wdth{wdth}.ttf"


def build_foreign_masters(style: str, out_dir, masters=config.MASTERS, scripts=None) -> dict:
    """Build one merged static TTF per master with all non-CJK foreign scripts.

    Returns ``{(wght, wdth): Path}``.  Cached: a master is rebuilt only when
    its inputs (sources, parameters, code) changed.  After building, all
    masters are verified to be point- and layout-compatible.
    """
    from . import checks

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = [s for s in SCRIPTS if scripts is None or s.key in scripts]
    plans = {s.key: make_plan(s, style) for s in specs}
    plan_keys = [cache.make_key(asdict(plans[s.key])) for s in specs]
    result = {}
    rebuilt = False
    for wght, wdth in masters:
        path = out_dir / _master_name(style, wght, wdth)
        key = cache.make_key(["master", style, wght, wdth, plan_keys, code_key()])
        result[(wght, wdth)] = path
        if cache.fresh(path, key):
            continue
        log.info("building foreign master %s %s/%s", style, wght, wdth)
        fonts = [build_script_master(s, style, wght, wdth, plans[s.key]) for s in specs]
        merged = fontmerge.merge_fonts(fonts, shared_ok=lambda n: n in SHARED_NAMES)
        set_vertical_metrics(merged)
        _set_names(merged, style)
        merged.save(path)
        cache.mark(path, key)
        rebuilt = True
    report = out_dir / f"PolaronForeign-{style}.report.json"
    if rebuilt or not report.exists():
        fonts = {m: TTFont(p) for m, p in result.items()}
        checks.assert_compatible(fonts)
        for (w, d), f in fonts.items():
            checks.assert_grid(f, config.cell_width(d))
        report.write_text(json.dumps({
            "scripts": {k: {**p.stats, "src_wdth": p.src_wdth, "natural_cell": p.natural_cell}
                        for k, p in plans.items()},
            "glyphs": len(next(iter(fonts.values())).getGlyphOrder()),
            "sizes": {f"{w},{d}": p.stat().st_size for (w, d), p in result.items()},
        }, indent=1), encoding="utf-8")
    return result
