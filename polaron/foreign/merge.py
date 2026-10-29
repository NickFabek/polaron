"""Merge one of our static masters with the matching foreign master.

``merge_with_ours`` keeps everything of ours (metrics, names, OS/2, hinting
tables, our GSUB/GPOS/GDEF) and adds the foreign glyphs, cmap entries and
layout.  Ours wins every cmap conflict.  Foreign layout that refers to a
shared helper glyph (ZWJ, ZWNJ, dotted circle) is redirected to *our* glyph
when we map the same code point, so e.g. HarfBuzz's inserted dotted circle
still receives the foreign mark anchors.

Because the merge is deterministic and the inputs of every master are
structurally identical, the merged masters can be fed straight to
``fontTools.varLib.build``.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont

from . import fontmerge, otl
from .monospace import NOTO_COPYRIGHT
from .scripts import SCRIPTS, SHARED

# Glyph-name prefixes reserved for foreign glyphs.
FOREIGN_PREFIXES = ("fgn.", "cjk.") + tuple(s.prefix for s in SCRIPTS)


def merge_with_ours(ours_master_ttf, foreign_master_ttf, out_path, *, attribution: bool = True) -> Path:
    """Merge ``ours_master_ttf`` + ``foreign_master_ttf`` into ``out_path``.

    * glyph order: ours, then foreign (foreign ``.notdef`` dropped);
    * cmap: ours wins on conflicts;
    * GSUB/GPOS/GDEF: both kept (ours' lookups first);
    * with ``attribution`` the Noto copyright line is appended to ours'
      copyright string (name ID 0) as the OFL requires.
    """
    ours = TTFont(ours_master_ttf)
    fgn = TTFont(foreign_master_ttf)
    ours_names = set(ours.getGlyphOrder())
    clash = [g for g in fgn.getGlyphOrder() if g in ours_names and g != ".notdef"]
    if clash:
        raise ValueError(f"glyph names present in both fonts: {clash[:10]}")
    bad = [g for g in ours.getGlyphOrder() if g.startswith(FOREIGN_PREFIXES)]
    if bad:
        raise ValueError(f"our font uses reserved foreign glyph-name prefixes: {bad[:10]}")
    ocmap = ours.getBestCmap()
    fgn_names = set(fgn.getGlyphOrder())
    redirect = {name: ocmap[cp] for cp, name in SHARED.items() if cp in ocmap and name in fgn_names}
    if redirect:
        fgn = otl.renamed_font(fgn, lambda g: redirect.get(g, g))
    targets = set(redirect.values())
    merged = fontmerge.merge_fonts([ours, fgn], shared_ok=lambda n: n in targets)
    if attribution and "name" in merged:
        name = merged["name"]
        for rec in list(name.names):
            if rec.nameID == 0:
                s = rec.toUnicode()
                if "Noto" not in s:
                    name.setName(s + " " + NOTO_COPYRIGHT, 0, rec.platformID, rec.platEncID, rec.langID)
        if not any(r.nameID == 0 for r in name.names):
            name.setName(NOTO_COPYRIGHT, 0, 3, 1, 0x409)
    if "OS/2" in merged:
        merged["OS/2"].recalcCodePageRanges(merged)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.save(out_path)
    return out_path
