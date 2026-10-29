"""Render big proofs of specific text at a few masters: uv run python zoom.py style italic size text..."""
import sys
from pathlib import Path
from polaron.master import build_master_fonts
from polaron.proof import render_lines, stack
style = sys.argv[1]; italic = sys.argv[2] in ("1","i","italic"); size = int(sys.argv[3]); text = sys.argv[4:]
ms = [(400, 100), (900, 100)]
if len(text) and text[0].startswith("@"):
    ms = [tuple(map(int, x.split(","))) for x in text[0][1:].split(";")]; text = text[1:]
fonts, _ = build_master_fonts(style, italic, ms, log=lambda *a: None)
imgs = []
for (w, d), f in zip(ms, fonts):
    fp = Path("build/dev") / f"me-{style}-{w}-{d}.ttf"; f.save(fp)
    imgs.append(render_lines(fp, text, size=size, label=f"{style} {w} {d}"))
stack(imgs, "proofs/me.png")
