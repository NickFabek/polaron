"""Quick dev loop: build a few static masters and render proofs.

usage: uv run python dev.py [style] [italic] [text...]
"""
import sys, time
from pathlib import Path
from polaron.master import build_master_fonts
from polaron.proof import render_lines, stack

style = sys.argv[1] if len(sys.argv) > 1 else "sans"
italic = len(sys.argv) > 2 and sys.argv[2] in ("1", "italic", "i")
text = sys.argv[3:] or ["nohmuabdpqgceskrftijlvwxyz", "minimum hamburgefonts", "quick brown fox jumps"]
masters = [(100, 100), (400, 100), (900, 100), (400, 80), (900, 80), (400, 120)]
out = Path("build/dev"); out.mkdir(parents=True, exist_ok=True)
t = time.time()
fonts, sets = build_master_fonts(style, italic, masters)
imgs = []
for (w, d), f in zip(masters, fonts):
    fp = out / f"{style}{'-it' if italic else ''}-{w}-{d}.ttf"
    f.save(fp)
    imgs.append(render_lines(fp, text, size=56, label=f"{style} {'italic ' if italic else ''}wght {w} wdth {d}"))
stack(imgs, Path("proofs") / f"dev-{style}{'-it' if italic else ''}.png")
print("done", time.time() - t)
