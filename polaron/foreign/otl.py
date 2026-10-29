"""Helpers for walking and rewriting OpenType layout tables (GSUB/GPOS/GDEF).

Everything here is structural: nothing depends on coordinate values, so the
same operations applied to every master yield structurally identical tables.
"""

from __future__ import annotations

import io
import re
from typing import Callable, Iterable, Iterator

import fontTools.subset  # noqa: F401  (registers prune/subset helpers on otTables)
from fontTools.misc.xmlWriter import XMLWriter
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

EXT_TYPE = {"GSUB": 7, "GPOS": 9}

_RULE_SETS = (
    ("SubRuleSet", "SubRule"),
    ("SubClassSet", "SubClassRule"),
    ("ChainSubRuleSet", "ChainSubRule"),
    ("ChainSubClassSet", "ChainSubClassRule"),
    ("PosRuleSet", "PosRule"),
    ("PosClassSet", "PosClassRule"),
    ("ChainPosRuleSet", "ChainPosRule"),
    ("ChainPosClassSet", "ChainPosClassRule"),
)
_REC_NAMES = ("SubstLookupRecord", "PosLookupRecord")


def iter_subtables(lookup, tag: str) -> Iterator[tuple[object, int]]:
    """Yield ``(subtable, lookup_type)`` with Extension subtables unwrapped."""
    for st in lookup.SubTable:
        if lookup.LookupType == EXT_TYPE[tag]:
            yield st.ExtSubTable, st.ExtensionLookupType
        else:
            yield st, lookup.LookupType


def lookup_type(lookup, tag: str) -> int:
    if lookup.LookupType == EXT_TYPE[tag] and lookup.SubTable:
        return lookup.SubTable[0].ExtensionLookupType
    return lookup.LookupType


def iter_lookup_records(st) -> Iterator[object]:
    """Yield every Subst/PosLookupRecord of a (chain)context subtable."""
    for name in _REC_NAMES:
        for r in getattr(st, name, None) or []:
            yield r
    for set_name, rule_name in _RULE_SETS:
        for rs in getattr(st, set_name, None) or []:
            if rs is None:
                continue
            for rule in getattr(rs, rule_name, None) or []:
                for name in _REC_NAMES:
                    for r in getattr(rule, name, None) or []:
                        yield r


def nested_lookups(lookup, tag: str) -> set[int]:
    out = set()
    for st, _t in iter_subtables(lookup, tag):
        for r in iter_lookup_records(st):
            out.add(r.LookupListIndex)
    return out


def feature_lookups(table) -> dict[str, set[int]]:
    """Feature tag -> set of lookup indices referenced directly by it."""
    out: dict[str, set[int]] = {}
    if table.FeatureList:
        for fr in table.FeatureList.FeatureRecord:
            out.setdefault(fr.FeatureTag, set()).update(fr.Feature.LookupListIndex)
    return out


def keep_lookups(font: TTFont, tag: str, keep: Iterable[int]) -> None:
    """Retain only the given lookups (remapping indices), then prune features."""
    t = font[tag]
    t.subset_lookups(sorted(set(keep)))
    t.prune_lookups()
    t.prune_features()


# --------------------------------------------------------------------------
# GPOS anchor / value ownership


def iter_anchor_slots(st, typ: int) -> Iterator[tuple[str, object, str]]:
    """Yield ``(owner_glyph, container, attribute_or_index)`` for every anchor.

    ``container`` is either an object (attribute name given) or a list
    (integer index given).  Callers replace the anchor in place.
    """
    if typ == 3:
        for g, rec in zip(st.Coverage.glyphs, st.EntryExitRecord):
            yield g, rec, "EntryAnchor"
            yield g, rec, "ExitAnchor"
    elif typ == 4:
        for g, rec in zip(st.MarkCoverage.glyphs, st.MarkArray.MarkRecord):
            yield g, rec, "MarkAnchor"
        for g, rec in zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord):
            for i in range(len(rec.BaseAnchor)):
                yield g, rec.BaseAnchor, i
    elif typ == 5:
        for g, rec in zip(st.MarkCoverage.glyphs, st.MarkArray.MarkRecord):
            yield g, rec, "MarkAnchor"
        for g, att in zip(st.LigatureCoverage.glyphs, st.LigatureArray.LigatureAttach):
            for comp in att.ComponentRecord:
                for i in range(len(comp.LigatureAnchor)):
                    yield g, comp.LigatureAnchor, i
    elif typ == 6:
        for g, rec in zip(st.Mark1Coverage.glyphs, st.Mark1Array.MarkRecord):
            yield g, rec, "MarkAnchor"
        for g, rec in zip(st.Mark2Coverage.glyphs, st.Mark2Array.Mark2Record):
            for i in range(len(rec.Mark2Anchor)):
                yield g, rec.Mark2Anchor, i


def _get(container, key):
    return container[key] if isinstance(key, int) else getattr(container, key)


def _set(container, key, value):
    if isinstance(key, int):
        container[key] = value
    else:
        setattr(container, key, value)


def new_anchor(x: float, y: float, point: int | None = None) -> ot.Anchor:
    a = ot.Anchor()
    if point is None:
        a.Format = 1
    else:
        a.Format = 2
        a.AnchorPoint = point
    a.XCoordinate = int(round(x))
    a.YCoordinate = int(round(y))
    return a


def transform_anchors(st, typ: int, fn: Callable[[str, float, float, str], tuple[float, float]]) -> None:
    """Replace every anchor of a GPOS subtable with ``fn(owner, x, y, role)``.

    ``role`` is "entry"/"exit" for cursive anchors, else "attach".
    Anchors are always replaced by fresh objects (never mutated) so shared
    objects cannot leak transforms between owners.  Device tables are dropped
    (our masters are static); contour-point anchors keep their point index.
    """
    for owner, cont, key in iter_anchor_slots(st, typ):
        a = _get(cont, key)
        if a is None:
            continue
        role = "attach"
        if key == "EntryAnchor":
            role = "entry"
        elif key == "ExitAnchor":
            role = "exit"
        x, y = fn(owner, a.XCoordinate, a.YCoordinate, role)
        point = a.AnchorPoint if a.Format == 2 else None
        _set(cont, key, new_anchor(x, y, point))


# ValueFormat bits
VF_XPLA, VF_YPLA, VF_XADV, VF_YADV = 0x1, 0x2, 0x4, 0x8
VF_XPLADEV, VF_YPLADEV, VF_XADVDEV, VF_YADVDEV = 0x10, 0x20, 0x40, 0x80
VF_PLACEMENT = VF_XPLA | VF_YPLA | VF_XPLADEV | VF_YPLADEV


def new_value(fmt: int, xpla: float = 0, ypla: float = 0) -> ot.ValueRecord:
    """ValueRecord with the fields of ``fmt`` (advances always zero, no devices)."""
    v = ot.ValueRecord()
    if fmt & VF_XPLA:
        v.XPlacement = int(round(xpla))
    if fmt & VF_YPLA:
        v.YPlacement = int(round(ypla))
    if fmt & VF_XADV:
        v.XAdvance = 0
    if fmt & VF_YADV:
        v.YAdvance = 0
    return v


# --------------------------------------------------------------------------
# Coverage ordering
#
# After merging fonts, glyphs shared between scripts (and our glyphs that
# replace foreign helpers) can sit at lower glyph IDs than the rest of a
# coverage, so coverages must be re-sorted together with the arrays that are
# indexed by coverage index.


def _sort_cov(cov, gid) -> list[int]:
    """Sort a Coverage in place; return the permutation (new -> old index)."""
    if cov is None:
        return []
    glyphs = cov.glyphs
    perm = sorted(range(len(glyphs)), key=lambda i: gid[glyphs[i]])
    if perm != list(range(len(glyphs))):
        cov.glyphs = [glyphs[i] for i in perm]
    return perm


def _sort_parallel(cov, arr_owner, arr_name, gid):
    perm = _sort_cov(cov, gid)
    if arr_owner is None:
        return
    arr = getattr(arr_owner, arr_name)
    if perm and perm != list(range(len(perm))):
        setattr(arr_owner, arr_name, [arr[i] for i in perm])


def sort_coverages(font: TTFont) -> None:
    """Make every Coverage sorted by glyph ID, keeping parallel arrays aligned."""
    gid = {g: i for i, g in enumerate(font.getGlyphOrder())}
    for tag in ("GSUB", "GPOS"):
        if tag not in font:
            continue
        for lk in font[tag].table.LookupList.Lookup:
            for st, t in iter_subtables(lk, tag):
                ctx = (tag == "GSUB" and t in (5, 6)) or (tag == "GPOS" and t in (7, 8))
                if ctx:
                    fmt = st.Format
                    if fmt == 1:
                        name = {5: "SubRuleSet", 6: "ChainSubRuleSet", 7: "PosRuleSet",
                                8: "ChainPosRuleSet"}[t]
                        _sort_parallel(st.Coverage, st, name, gid)
                    elif fmt == 2:
                        _sort_cov(st.Coverage, gid)
                    for name in ("Coverage", "InputCoverage", "BacktrackCoverage", "LookAheadCoverage"):
                        v = getattr(st, name, None)
                        if isinstance(v, list):
                            for c in v:
                                _sort_cov(c, gid)
                    continue
                if tag == "GSUB":
                    if t == 8:
                        _sort_parallel(st.Coverage, st, "Substitute", gid)
                        for c in (st.BacktrackCoverage or []) + (st.LookAheadCoverage or []):
                            _sort_cov(c, gid)
                    continue
                if t == 1:
                    if st.Format == 2:
                        _sort_parallel(st.Coverage, st, "Value", gid)
                    else:
                        _sort_cov(st.Coverage, gid)
                elif t == 2:
                    if st.Format == 1:
                        _sort_parallel(st.Coverage, st, "PairSet", gid)
                        for ps in st.PairSet:
                            ps.PairValueRecord.sort(key=lambda r: gid[r.SecondGlyph])
                    else:
                        _sort_cov(st.Coverage, gid)
                elif t == 3:
                    _sort_parallel(st.Coverage, st, "EntryExitRecord", gid)
                elif t == 4:
                    _sort_parallel(st.MarkCoverage, st.MarkArray, "MarkRecord", gid)
                    _sort_parallel(st.BaseCoverage, st.BaseArray, "BaseRecord", gid)
                elif t == 5:
                    _sort_parallel(st.MarkCoverage, st.MarkArray, "MarkRecord", gid)
                    _sort_parallel(st.LigatureCoverage, st.LigatureArray, "LigatureAttach", gid)
                elif t == 6:
                    _sort_parallel(st.Mark1Coverage, st.Mark1Array, "MarkRecord", gid)
                    _sort_parallel(st.Mark2Coverage, st.Mark2Array, "Mark2Record", gid)
    if "GDEF" in font:
        g = font["GDEF"].table
        if g.LigCaretList:
            _sort_parallel(g.LigCaretList.Coverage, g.LigCaretList, "LigGlyph", gid)
        if g.AttachList:
            _sort_parallel(g.AttachList.Coverage, g.AttachList, "AttachPoint", gid)
        if getattr(g, "MarkGlyphSetsDef", None):
            for c in g.MarkGlyphSetsDef.Coverage:
                _sort_cov(c, gid)


# --------------------------------------------------------------------------
# Glyph renaming


def renamed_font(font: TTFont, mapping: Callable[[str], str]) -> TTFont:
    """Return a copy of ``font`` with every glyph renamed via ``mapping``.

    Uses a binary round trip: tables are compiled with glyph IDs, then the
    copy is decompiled with the new glyph order, so every table follows.
    """
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    new = TTFont(buf)
    order = new.getGlyphOrder()
    new_order = [mapping(g) for g in order]
    if len(set(new_order)) != len(new_order):
        raise ValueError("glyph rename produced duplicate names")
    new.setGlyphOrder(new_order)
    if "post" in new:
        post = new["post"]
        post.formatType = 2.0
        post.extraNames = []
        post.mapping = {}
    # force decompilation of everything now, with the new names
    for tag in new.keys():
        if tag != "GlyphOrder":
            new[tag]
    return new


# --------------------------------------------------------------------------
# Structural signature (for cross-master compatibility checks)

_NUM_ATTRS = (
    "XCoordinate|YCoordinate|XPlacement|YPlacement|XAdvance|YAdvance|Coordinate"
)
_RE_VALUE_TAG = re.compile(rf'<({_NUM_ATTRS}) value="-?\d+"/>')
_RE_VALUE_ATTR = re.compile(rf'\b({_NUM_ATTRS})="-?\d+"')


def otl_signature(font: TTFont, tag: str) -> str:
    """XML of an OTL table with all coordinate/placement numbers blanked."""
    if tag not in font:
        return ""
    buf = io.StringIO()
    w = XMLWriter(buf, newlinestr="\n")
    font[tag].toXML(w, font)
    s = buf.getvalue()
    s = _RE_VALUE_TAG.sub(r"<\1/>", s)
    s = _RE_VALUE_ATTR.sub(r'\1=""', s)
    return s
