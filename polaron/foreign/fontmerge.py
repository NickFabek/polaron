"""Glyph-level merge of static TrueType fonts with (mostly) disjoint glyph names.

Used to combine the per-script foreign fonts into one foreign master and to
merge that with one of our own masters.  Rules:

* glyph order = first font's order, then each later font's glyphs that are
  not already present (a name present in an earlier font is *shared*: the
  earlier outline/metrics win and later layout tables simply reference it);
* cmap: earlier fonts win on conflicts;
* GSUB/GPOS: lookup lists and feature lists are concatenated (indices of
  later fonts are offset, including nested contextual lookup references and
  mark filtering sets); scripts/langsys with the same tag are unioned;
  records are sorted by tag as the spec requires;
* GDEF: class definitions are unioned (earlier wins), mark glyph sets are
  concatenated, ligature carets are unioned.

The result is deterministic, so merging masters that are structurally
identical produces merged masters that are structurally identical too.
"""

from __future__ import annotations

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from . import otl


def _gdef(font):
    return font["GDEF"].table if "GDEF" in font else None


def _empty_otl(tag: str):
    t = newTable(tag)
    tbl = getattr(ot, tag)()
    tbl.Version = 0x00010000
    tbl.ScriptList = ot.ScriptList()
    tbl.ScriptList.ScriptRecord = []
    tbl.FeatureList = ot.FeatureList()
    tbl.FeatureList.FeatureRecord = []
    tbl.LookupList = ot.LookupList()
    tbl.LookupList.Lookup = []
    t.table = tbl
    return t


def build_cmap(mapping: dict[int, str], uvs_subtable=None):
    """(3,1) format 4 + (0,3) format 4, plus (3,10)/(0,4) format 12 if needed."""
    cmap = newTable("cmap")
    cmap.tableVersion = 0
    cmap.tables = []
    bmp = {cp: g for cp, g in mapping.items() if cp <= 0xFFFF}
    for pid, eid in ((0, 3), (3, 1)):
        st = CmapSubtable.newSubtable(4)
        st.platformID, st.platEncID, st.language = pid, eid, 0
        st.cmap = dict(bmp)
        cmap.tables.append(st)
    if any(cp > 0xFFFF for cp in mapping):
        for pid, eid in ((0, 4), (3, 10)):
            st = CmapSubtable.newSubtable(12)
            st.platformID, st.platEncID, st.language = pid, eid, 0
            st.cmap = dict(mapping)
            cmap.tables.append(st)
    if uvs_subtable is not None:
        cmap.tables.append(uvs_subtable)
    cmap.tables.sort(key=lambda s: (s.platformID, s.platEncID, s.language))
    return cmap


def _remap_lookup(lookup, tag: str, lk_off: int, ms_off: int) -> None:
    for st, _t in otl.iter_subtables(lookup, tag):
        for rec in otl.iter_lookup_records(st):
            rec.LookupListIndex += lk_off
    if lookup.LookupFlag & 0x0010 and ms_off:
        lookup.MarkFilteringSet += ms_off


def _merge_langsys(dst, src, f_off: int):
    if src is None:
        return dst
    if dst is None:
        dst = ot.LangSys()
        dst.LookupOrder = None
        dst.ReqFeatureIndex = 0xFFFF
        dst.FeatureIndex = []
    idx = set(dst.FeatureIndex)
    idx.update(i + f_off for i in src.FeatureIndex)
    dst.FeatureIndex = sorted(idx)
    if dst.ReqFeatureIndex == 0xFFFF and src.ReqFeatureIndex != 0xFFFF:
        dst.ReqFeatureIndex = src.ReqFeatureIndex + f_off
    dst.FeatureCount = len(dst.FeatureIndex)
    return dst


def _merge_otl(dst_font: TTFont, fonts: list[TTFont], tag: str, ms_offsets: list[int]) -> None:
    if not any(tag in f for f in fonts):
        return
    lookups, features = [], []
    scripts: dict[str, ot.Script] = {}
    for k, f in enumerate(fonts):
        if tag not in f:
            continue
        t = f[tag].table
        if getattr(t, "FeatureVariations", None):
            raise ValueError(f"{tag} FeatureVariations not supported in merge")
        lk_off, f_off = len(lookups), len(features)
        for lk in (t.LookupList.Lookup if t.LookupList else []):
            # (later fonts are consumed by the merge, so no copy is needed)
            _remap_lookup(lk, tag, lk_off, ms_offsets[k])
            lookups.append(lk)
        for fr in (t.FeatureList.FeatureRecord if t.FeatureList else []):
            fr2 = ot.FeatureRecord()
            fr2.FeatureTag = fr.FeatureTag
            fr2.Feature = ot.Feature()
            fr2.Feature.FeatureParams = fr.Feature.FeatureParams if k == 0 else None
            fr2.Feature.LookupListIndex = [i + lk_off for i in fr.Feature.LookupListIndex]
            fr2.Feature.LookupCount = len(fr2.Feature.LookupListIndex)
            features.append(fr2)
        for sr in (t.ScriptList.ScriptRecord if t.ScriptList else []):
            s = scripts.get(sr.ScriptTag)
            if s is None:
                s = ot.Script()
                s.DefaultLangSys = None
                s.LangSysRecord = []
                scripts[sr.ScriptTag] = s
            s.DefaultLangSys = _merge_langsys(s.DefaultLangSys, sr.Script.DefaultLangSys, f_off)
            by_tag = {r.LangSysTag: r for r in s.LangSysRecord}
            for lr in sr.Script.LangSysRecord:
                r = by_tag.get(lr.LangSysTag)
                if r is None:
                    r = ot.LangSysRecord()
                    r.LangSysTag = lr.LangSysTag
                    r.LangSys = None
                    s.LangSysRecord.append(r)
                    by_tag[lr.LangSysTag] = r
                r.LangSys = _merge_langsys(r.LangSys, lr.LangSys, f_off)
    # sort features by tag (stable), remap indices
    order = sorted(range(len(features)), key=lambda i: (features[i].FeatureTag, i))
    remap = {old: new for new, old in enumerate(order)}
    features = [features[i] for i in order]

    def fix(ls):
        if ls is None:
            return
        ls.FeatureIndex = sorted(remap[i] for i in ls.FeatureIndex)
        ls.FeatureCount = len(ls.FeatureIndex)
        if ls.ReqFeatureIndex != 0xFFFF:
            ls.ReqFeatureIndex = remap[ls.ReqFeatureIndex]

    script_records = []
    for stag in sorted(scripts):
        s = scripts[stag]
        fix(s.DefaultLangSys)
        s.LangSysRecord.sort(key=lambda r: r.LangSysTag)
        for r in s.LangSysRecord:
            fix(r.LangSys)
        s.LangSysCount = len(s.LangSysRecord)
        sr = ot.ScriptRecord()
        sr.ScriptTag = stag
        sr.Script = s
        script_records.append(sr)

    out = _empty_otl(tag)
    tbl = out.table
    tbl.ScriptList.ScriptRecord = script_records
    tbl.ScriptList.ScriptCount = len(script_records)
    tbl.FeatureList.FeatureRecord = features
    tbl.FeatureList.FeatureCount = len(features)
    tbl.LookupList.Lookup = lookups
    tbl.LookupList.LookupCount = len(lookups)
    dst_font[tag] = out


def _merge_gdef(dst_font: TTFont, fonts: list[TTFont]) -> list[int]:
    """Merge GDEF; returns the mark-glyph-set offset of each font."""
    offsets = []
    gdefs = [_gdef(f) for f in fonts]
    if not any(gdefs):
        return [0] * len(fonts)
    out = newTable("GDEF")
    g = ot.GDEF()
    g.Version = 0x00010000
    g.GlyphClassDef = ot.GlyphClassDef()
    g.GlyphClassDef.classDefs = {}
    g.AttachList = None
    g.LigCaretList = None
    g.MarkAttachClassDef = None
    g.MarkGlyphSetsDef = None
    lig_glyphs: dict[str, object] = {}
    mark_sets = []
    for gd in gdefs:
        offsets.append(len(mark_sets))
        if gd is None:
            continue
        if gd.GlyphClassDef:
            for k, v in gd.GlyphClassDef.classDefs.items():
                g.GlyphClassDef.classDefs.setdefault(k, v)
        if gd.MarkAttachClassDef:
            if g.MarkAttachClassDef is None:
                g.MarkAttachClassDef = ot.MarkAttachClassDef()
                g.MarkAttachClassDef.classDefs = {}
            for k, v in gd.MarkAttachClassDef.classDefs.items():
                g.MarkAttachClassDef.classDefs.setdefault(k, v)
        if gd.LigCaretList:
            for name, lg in zip(gd.LigCaretList.Coverage.glyphs, gd.LigCaretList.LigGlyph):
                lig_glyphs.setdefault(name, lg)
        if getattr(gd, "MarkGlyphSetsDef", None):
            mark_sets.extend(gd.MarkGlyphSetsDef.Coverage)
    if lig_glyphs:
        order = {n: i for i, n in enumerate(dst_font.getGlyphOrder())}
        names = sorted(lig_glyphs, key=lambda n: order[n])
        lcl = ot.LigCaretList()
        lcl.Coverage = ot.Coverage()
        lcl.Coverage.glyphs = names
        lcl.LigGlyph = [lig_glyphs[n] for n in names]
        lcl.LigGlyphCount = len(names)
        g.LigCaretList = lcl
    if mark_sets:
        g.Version = 0x00010002
        mgs = ot.MarkGlyphSetsDef()
        mgs.MarkSetTableFormat = 1
        mgs.Coverage = mark_sets
        mgs.MarkSetCount = len(mark_sets)
        g.MarkGlyphSetsDef = mgs
    out.table = g
    dst_font["GDEF"] = out
    return offsets


def merge_fonts(fonts: list[TTFont], shared_ok=lambda name: False) -> TTFont:
    """Merge ``fonts`` into ``fonts[0]`` (modified in place and returned).

    A glyph name occurring in more than one font is allowed only for
    ``.notdef`` and names for which ``shared_ok(name)`` is true.
    """
    base = fonts[0]
    order = list(base.getGlyphOrder())
    seen = set(order)
    glyf = base["glyf"]
    hmtx = base["hmtx"]
    mapping = dict(base.getBestCmap() or {})
    uvs = None
    for st in base["cmap"].tables:
        if st.format == 14:
            uvs = st
    for f in fonts[1:]:
        fg = f["glyf"]
        fh = f["hmtx"]
        for name in f.getGlyphOrder():
            if name in seen:
                if name != ".notdef" and not shared_ok(name):
                    raise ValueError(f"glyph name collision in merge: {name}")
                continue
            seen.add(name)
            order.append(name)
            glyf.glyphs[name] = fg[name]
            hmtx.metrics[name] = fh.metrics[name]
        for cp, name in (f.getBestCmap() or {}).items():
            mapping.setdefault(cp, name)
    if len(order) > 0xFFFF:
        raise ValueError(f"merged font would have {len(order)} glyphs (> 65535)")
    # per-glyph tables we do not merge: drop hinting caches, pad vmtx
    for tag in ("hdmx", "LTSH", "VDMX"):
        if tag in base:
            del base[tag]
    if "vmtx" in base:
        vm = base["vmtx"].metrics
        upm = base["head"].unitsPerEm
        for name in order:
            vm.setdefault(name, (upm, 0))
    base.setGlyphOrder(order)
    glyf.glyphOrder = order
    base["maxp"].numGlyphs = len(order)
    base["cmap"] = build_cmap(mapping, uvs)
    ms_offsets = _merge_gdef(base, fonts)
    for tag in ("GSUB", "GPOS"):
        _merge_otl(base, fonts, tag, ms_offsets)
    if "post" in base:
        base["post"].formatType = 2.0
        base["post"].extraNames = []
        base["post"].mapping = {}
    otl.sort_coverages(base)
    if "OS/2" in base:
        base["OS/2"].recalcUnicodeRanges(base)
    return base
