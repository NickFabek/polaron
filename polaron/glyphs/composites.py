"""Precomposed letters generated from Unicode canonical decompositions.

Imported last: it looks at every glyph registered so far and creates
composite glyphs (base + positioned marks) for each decomposable code point
whose pieces exist.
"""

from __future__ import annotations

import unicodedata

from fontTools import agl

from ..glyph import REGISTRY, register
from .marks import GREEK_COMBOS, MARKS

RANGES = [
    (0x00C0, 0x024F),
    (0x0370, 0x03FF),
    (0x0400, 0x052F),
    (0x1E00, 0x1EFF),
    (0x1F00, 0x1FFF),
    (0x2000, 0x2BFF),
    (0x2C60, 0x2C7F),
    (0xA720, 0xA7FF),
    (0xAB30, 0xAB6F),
    (0xFB00, 0xFB4F),
]

SOFT_DOTTED = {0x69: "dotlessi", 0x6A: "dotlessj", 0x456: "dotlessi", 0x458: "dotlessj"}
LATVIAN = {0x4B, 0x6B, 0x4C, 0x6C, 0x4E, 0x6E, 0x52, 0x72}
ASCENDERS = set(map(ord, "bdfhklþ")) | {0x452, 0x45B, 0x431}
VIET = {(0x302, 0x301): "circumflexacutecomb", (0x302, 0x300): "circumflexgravecomb",
        (0x302, 0x309): "circumflexhookcomb"}
CARON_ALT = {0x64, 0x6C, 0x74, 0x4C}

POS_ANCHOR = {"top": "top", "bottom": "bottom", "center": "center", "ogonek": "ogonek", "horn": "horn",
              "double": "top", "doublebelow": "bottom"}


def glyph_name(cp):
    n = agl.UV2AGL.get(cp) if cp < 0x370 else None
    if n:
        return n
    return f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"


def full_decomp(cp):
    d = unicodedata.decomposition(chr(cp))
    if not d or d.startswith("<"):
        return [cp]
    parts = [int(x, 16) for x in d.split()]
    out = full_decomp(parts[0])
    for q in parts[1:]:
        out.extend(full_decomp(q))
    return out


def build():
    cmap = {}
    for name, gd in REGISTRY.items():
        for u in gd.unicodes:
            cmap.setdefault(u, name)
    mark_by_cp = {}
    for name, gd in REGISTRY.items():
        if gd.kind == "mark":
            for u in gd.unicodes:
                mark_by_cp[u] = name
    made = 0
    for lo, hi in RANGES:
        for cp in range(lo, hi + 1):
            if cp in cmap:
                continue
            seq = full_decomp(cp)
            if len(seq) < 2:
                continue
            base, marks = seq[0], seq[1:]
            if base not in cmap:
                continue
            if any(unicodedata.combining(chr(m)) == 0 and m not in mark_by_cp for m in marks):
                continue
            # merge Greek breathing+accent pairs
            merged = []
            i = 0
            while i < len(marks):
                if i + 1 < len(marks) and (marks[i], marks[i + 1]) in GREEK_COMBOS:
                    merged.append(GREEK_COMBOS[(marks[i], marks[i + 1])])
                    i += 2
                elif i + 1 < len(marks) and (marks[i], marks[i + 1]) in VIET:
                    merged.append(VIET[(marks[i], marks[i + 1])])
                    i += 2
                else:
                    if marks[i] not in mark_by_cp:
                        merged = None
                        break
                    merged.append(mark_by_cp[marks[i]])
                    i += 1
            if merged is None:
                continue
            upper = unicodedata.category(chr(base)) in ("Lu", "Lt") or base in ASCENDERS
            bname = cmap[base]
            spec = []
            has_top = any(MARKS.get(m) == "top" for m in merged)
            if has_top and base in SOFT_DOTTED:
                bname = SOFT_DOTTED[base]
            for m in merged:
                pos = MARKS.get(m, "top")
                anc = POS_ANCHOR[pos]
                if m == "cedillacomb" and base in LATVIAN:
                    m = "commaaccentcomb"
                if m == "cedillacomb" and base == 0x67:
                    m, anc = "uni0312", "top"
                if m == "caroncomb" and base in CARON_ALT:
                    m, anc = "caroncomb.alt", "caron"
                elif upper and pos == "top" and (m + ".case") in REGISTRY:
                    m = m + ".case"
                if (unicodedata.category(chr(base)) in ("Lu", "Lt") and pos == "top" and _is_greek(base)):
                    anc = "tonos"
                spec.append((m, anc))
            _register(glyph_name(cp), cp, bname, spec)
            made += 1
    return made


def _is_greek(cp):
    return 0x370 <= cp <= 0x3FF or 0x1F00 <= cp <= 0x1FFF


def _register(name, cp, base, spec):
    def fn(g, p, base=base, spec=spec):
        g.compose = [base] + list(spec)

    register(name, fn, cp)


COUNT = build()
