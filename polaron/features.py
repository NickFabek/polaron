"""OpenType feature code (FEA) generated per master.

Structure must be identical for every master (only anchor numbers differ),
so everything is driven by glyph names and anchor *names*, never values.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict

ANCHOR_CLASSES = ("top", "bottom", "center", "ogonek", "horn", "caron", "tonos")


def _r(v):
    return int(round(v))


def _cls(names):
    return "[" + " ".join(names) + "]"


def build_fea(p, gs) -> str:
    from .glyphs import ligatures as L  # noqa: F401  (registers ligature data)

    names = list(gs.keys())
    marks = [n for n in names if gs[n].kind == "mark"]
    bases = [n for n in names if gs[n].kind != "mark"]
    out = []
    out.append("languagesystem DFLT dflt;")
    for s in ("latn", "grek", "cyrl"):
        out.append(f"languagesystem {s} dflt;")

    # ---------------- GDEF
    ligs = [n for n in bases if gs[n].kind == "ligature"]
    simple = [n for n in bases if gs[n].kind != "ligature"]
    out.append(f"@GDEF_base = {_cls(simple)};")
    out.append(f"@GDEF_mark = {_cls(marks)};")
    if ligs:
        out.append(f"@GDEF_lig = {_cls(ligs)};")
    out.append(
        "table GDEF { GlyphClassDef @GDEF_base, " + ("@GDEF_lig" if ligs else "") + ", @GDEF_mark, ; } GDEF;"
    )

    # ---------------- ccmp: dotless i/j and .case marks
    top_marks = [n for n in marks if "_top" in gs[n].anchors and not n.endswith(".case")
                 and (n + ".case") in gs]
    top_all = [n for n in marks if "_top" in gs[n].anchors]
    upper = []
    for n in bases:
        us = gs[n].unicodes
        if us and unicodedata.category(chr(us[0])) in ("Lu", "Lt"):
            upper.append(n)
    out.append(f"@TopMarks = {_cls(top_all)};")
    out.append(f"@TopMarksLC = {_cls(top_marks)};")
    out.append(f"@TopMarksUC = {_cls([n + '.case' for n in top_marks])};")
    out.append(f"@Upper = {_cls(upper)};")
    soft = [(a, b) for a, b in (("i", "dotlessi"), ("j", "dotlessj"), ("uni0456", "dotlessi"),
                                ("uni0458", "dotlessj")) if a in gs and b in gs]
    out.append("lookup ccmp_dotless { " + " ".join(f"sub {a} by {b};" for a, b in soft) + " } ccmp_dotless;")
    out.append("lookup ccmp_case { sub @TopMarksLC by @TopMarksUC; } ccmp_case;")
    out.append("feature ccmp {")
    out.append("  lookup ccmp_ctx {")
    out.append("    sub " + _cls([a for a, b in soft]) + "' lookup ccmp_dotless @TopMarks;")
    out.append("    sub @Upper @TopMarksLC' lookup ccmp_case;")
    out.append("    sub @Upper @TopMarksUC @TopMarksLC' lookup ccmp_case;")
    out.append("  } ccmp_ctx;")
    out.append("} ccmp;")

    # ---------------- mark / mkmk
    classes = defaultdict(list)  # anchor -> [(mark, x, y)]
    for n in marks:
        for a in ANCHOR_CLASSES:
            if "_" + a in gs[n].anchors:
                x, y = gs[n].anchors["_" + a]
                classes[a].append((n, x, y))
    for a, items in classes.items():
        for n, x, y in items:
            out.append(f"markClass {n} <anchor {_r(x)} {_r(y)}> @MC_{a};")
    out.append("feature mark {")
    for a in classes:
        out.append(f"  lookup mark_{a} {{")
        groups = defaultdict(list)
        for n in bases:
            if a in gs[n].anchors:
                x, y = gs[n].anchors[a]
                groups[(_r(x), _r(y))].append(n)
        for (x, y), ns in sorted(groups.items()):
            out.append(f"    pos base {_cls(ns)} <anchor {x} {y}> mark @MC_{a};")
        out.append(f"  }} mark_{a};")
    out.append("} mark;")
    out.append("feature mkmk {")
    for a in classes:
        rules = []
        for n in marks:
            if "_" + a in gs[n].anchors and a in gs[n].anchors:
                x, y = gs[n].anchors[a]
                rules.append(f"    pos mark {n} <anchor {_r(x)} {_r(y)}> mark @MC_{a};")
        if rules:
            out.append(f"  lookup mkmk_{a} {{")
            out.extend(rules)
            out.append(f"  }} mkmk_{a};")
    out.append("} mkmk;")

    # ---------------- alternates
    alts = [("zero", "zero.slash", "zero")]
    for src, dst, feat in alts:
        if src in gs and dst in gs:
            out.append(f"feature {feat} {{ sub {src} by {dst}; }} {feat};")
    for feat, pairs in L.character_variants(gs).items():
        out.append(f"feature {feat} {{ " + " ".join(f"sub {a} by {b};" for a, b in pairs) + f" }} {feat};")

    # ---------------- programming ligatures (calt)
    out.append(L.calt_fea(gs))
    return "\n".join(out) + "\n"
