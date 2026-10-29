"""A stand-in for Polaron's own static masters (used only by the tests).

ASCII glyphs are simple box shapes with advance ``cell_width(wdth)``; there is
a combining acute (mark), a dotted circle, a tiny GSUB (``ss01``) and a tiny
GPOS (``kern`` + ``mark``) so all layout tables exist and vary per master.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fontTools.fontBuilder import FontBuilder  # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen  # noqa: E402

from polaron import config  # noqa: E402

ASC_LETTERS = set("bdfhklt")
DESC_LETTERS = set("gjpqy")


def _box(pen, x0, y0, x1, y1, stem):
    # outer (clockwise) + inner (counter-clockwise) => a ring
    pen.moveTo((x0, y0)); pen.lineTo((x0, y1)); pen.lineTo((x1, y1)); pen.lineTo((x1, y0)); pen.closePath()
    ix0, iy0, ix1, iy1 = x0 + stem, y0 + stem, x1 - stem, y1 - stem
    pen.moveTo((ix0, iy0)); pen.lineTo((ix1, iy0)); pen.lineTo((ix1, iy1)); pen.lineTo((ix0, iy1)); pen.closePath()


def _rect(pen, x0, y0, x1, y1):
    pen.moveTo((x0, y0)); pen.lineTo((x0, y1)); pen.lineTo((x1, y1)); pen.lineTo((x1, y0)); pen.closePath()


def build_dummy_master(wght: int, wdth: int, out_path: Path, style: str = "sans") -> Path:
    cell = config.cell_width(wdth)
    stem = round(20 + 0.11 * wght)
    sb = round(0.12 * cell)
    names = [".notdef", "space"]
    cmap = {0x20: "space"}
    for cp in range(0x21, 0x7F):
        n = f"u{cp:04X}"
        names.append(n)
        cmap[cp] = n
    names += ["acutecomb", "dottedcircle", "A.ss01"]
    cmap[0x0301] = "acutecomb"
    cmap[0x25CC] = "dottedcircle"
    glyphs, metrics = {}, {}
    for n in names:
        pen = TTGlyphPen(None)
        if n == ".notdef":
            _box(pen, sb, 0, cell - sb, config.CAP, stem)
        elif n == "space":
            pass
        elif n == "acutecomb":
            _rect(pen, -cell // 2 + sb, 600, -cell // 2 + sb + stem * 2, 600 + stem * 2)
        elif n == "dottedcircle":
            _box(pen, sb, 100, cell - sb, 100 + cell - 2 * sb, stem // 2)
        elif n == "A.ss01":
            _rect(pen, sb, 0, cell - sb, config.CAP)
        else:
            ch = chr(int(n[1:], 16))
            if ch.isupper() or ch.isdigit():
                y0, y1 = 0, config.CAP
            elif ch in ASC_LETTERS:
                y0, y1 = 0, config.ASCENDER
            elif ch in DESC_LETTERS:
                y0, y1 = config.DESCENDER, config.XHEIGHT
            elif ch.islower():
                y0, y1 = 0, config.XHEIGHT
            else:  # punctuation: small box
                y0, y1 = 0, 200 + (ord(ch) % 5) * 60
            _box(pen, sb, y0, cell - sb, y1, stem)
        glyphs[n] = pen.glyph()
        metrics[n] = (0 if n == "acutecomb" else cell, 0)
    fb = FontBuilder(config.UPM, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    for n in names:
        g = fb.font["glyf"][n]
        metrics[n] = (metrics[n][0], getattr(g, "xMin", 0) if g.numberOfContours else 0)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=config.TYPO_ASC, descent=config.TYPO_DESC)
    fam = f"Polaron Dummy {style.title()}"
    fb.setupNameTable({"familyName": fam, "styleName": "Regular",
                       "copyright": "Copyright 2026 The Polaron Project Authors"})
    fb.setupOS2(sTypoAscender=config.TYPO_ASC, sTypoDescender=config.TYPO_DESC, sTypoLineGap=0,
                usWinAscent=config.TYPO_ASC, usWinDescent=-config.TYPO_DESC,
                sxHeight=config.XHEIGHT, sCapHeight=config.CAP, usWeightClass=wght)
    fb.setupPost(isFixedPitch=1)
    top = config.CAP + 40
    fea = f"""
languagesystem DFLT dflt;
languagesystem latn dflt;
markClass acutecomb <anchor {-cell // 2 + sb + stem} 600> @TOP;
feature ss01 {{ sub u0041 by A.ss01; }} ss01;
feature kern {{ pos u0041 u0056 -{stem}; }} kern;
feature mark {{
  pos base [u0041 u0042 u0043 u0061 u0062 u0063] <anchor {cell // 2} {top}> mark @TOP;
}} mark;
table GDEF {{
  GlyphClassDef [u0041 u0042 u0043 u0061 u0062 u0063 dottedcircle], , [acutecomb], ;
}} GDEF;
"""
    fb.addOpenTypeFeatures(fea)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fb.font.save(out_path)
    return out_path


if __name__ == "__main__":
    print(build_dummy_master(400, 100, ROOT / "build" / "foreign" / "test" / "dummy.ttf"))
