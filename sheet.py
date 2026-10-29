"""Glyph sheet of every encoded glyph: uv run python sheet.py style italic wght wdth out_prefix [lo-hi hex]"""
import sys, unicodedata
from pathlib import Path
from polaron.master import build_master_fonts
from polaron.proof import render_lines, stack
style, italic, w, d, out = sys.argv[1], sys.argv[2] in ("1", "i"), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
rng = None
if len(sys.argv) > 6:
    lo, hi = sys.argv[6].split("-"); rng = (int(lo, 16), int(hi, 16))
fonts, _ = build_master_fonts(style, italic, [(w, d)], log=lambda *a: None)
fp = Path("build/dev") / f"sheet-{style}-{w}-{d}.ttf"; fonts[0].save(fp)
cps = sorted(c for c in fonts[0].getBestCmap() if (rng is None or rng[0] <= c <= rng[1]))
cps = [c for c in cps if unicodedata.category(chr(c)) not in ("Mn", "Me", "Zs", "Cf", "Cc")]
per = 48
lines = ["".join(chr(c) for c in cps[i:i + per]) for i in range(0, len(cps), per)]
pages = [lines[i:i + 14] for i in range(0, len(lines), 14)]
for k, pg in enumerate(pages):
    render_lines(fp, pg, size=30, out=f"{out}-{k}.png", line_gap=1.3, label=f"{style} {w}/{d} page {k}")
print(len(cps), "glyphs,", len(pages), "pages")
