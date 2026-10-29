"""Programmatic checks: grid advances and cross-master compatibility."""

from __future__ import annotations

import hashlib

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otBase, otTables as ot

# fields whose numeric value may differ between masters
VARYING = {"XCoordinate", "YCoordinate", "XPlacement", "YPlacement",
           "XAdvance", "YAdvance", "Coordinate"}


def grid_violations(font: TTFont, cell: int, glyphs=None) -> list[tuple[str, int]]:
    hmtx = font["hmtx"]
    names = glyphs if glyphs is not None else font.getGlyphOrder()
    return [(g, hmtx[g][0]) for g in names if hmtx[g][0] % cell != 0]


def assert_grid(font: TTFont, cell: int, glyphs=None) -> None:
    bad = grid_violations(font, cell, glyphs)
    if bad:
        raise AssertionError(f"{len(bad)} glyph advances not a multiple of {cell}: {bad[:10]}")


def _sig(obj, h, depth=0):
    if isinstance(obj, (otBase.BaseTable, ot.ValueRecord)):
        h.update(type(obj).__name__.encode())
        for k in sorted(vars(obj)):
            if k.startswith("_") or k in ("reader", "ttFont"):
                continue
            h.update(k.encode())
            if k in VARYING:
                continue
            _sig(getattr(obj, k), h, depth + 1)
    elif isinstance(obj, (list, tuple)):
        h.update(b"[%d" % len(obj))
        for v in obj:
            _sig(v, h, depth + 1)
    elif isinstance(obj, dict):
        h.update(b"{%d" % len(obj))
        for k in sorted(obj, key=str):
            h.update(str(k).encode())
            _sig(obj[k], h, depth + 1)
    else:
        h.update(repr(obj).encode())


def layout_signature(font: TTFont, tag: str) -> str:
    """Hash of a layout table's structure (coordinates/placements ignored)."""
    if tag not in font:
        return "-"
    t = font[tag].table
    # make sure lazily loaded subtables are expanded
    t.ensureDecompiled(recurse=True)
    h = hashlib.sha256()
    _sig(t, h)
    return h.hexdigest()


def outline_signature(font: TTFont) -> str:
    glyf = font["glyf"]
    h = hashlib.sha256()
    for g in font.getGlyphOrder():
        gl = glyf[g]
        h.update(g.encode())
        if gl.isComposite():
            h.update(b"C" + ",".join(c.glyphName for c in gl.components).encode())
        elif gl.numberOfContours > 0:
            h.update(bytes(gl.flags[i] & 1 for i in range(len(gl.flags))))
            h.update(",".join(map(str, gl.endPtsOfContours)).encode())
    return h.hexdigest()


def compat_report(fonts: dict) -> dict:
    """Signature of every master; equal values mean compatible masters."""
    out = {}
    for key, f in fonts.items():
        out[key] = {
            "order": hashlib.sha256("\n".join(f.getGlyphOrder()).encode()).hexdigest(),
            "outlines": outline_signature(f),
            "cmap": hashlib.sha256(repr(sorted(f.getBestCmap().items())).encode()).hexdigest(),
            "GSUB": layout_signature(f, "GSUB"),
            "GPOS": layout_signature(f, "GPOS"),
            "GDEF": layout_signature(f, "GDEF"),
        }
    return out


def assert_compatible(fonts: dict) -> None:
    rep = compat_report(fonts)
    keys = list(rep)
    ref = rep[keys[0]]
    for k in keys[1:]:
        diff = [field for field in ref if rep[k][field] != ref[field]]
        if diff:
            raise AssertionError(f"master {k} incompatible with {keys[0]} in {diff}")
