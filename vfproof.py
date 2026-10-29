"""Render a VF at several instances: uv run python vfproof.py font.ttf out.png [lines...]"""
import sys
from polaron.proof import render_lines, stack
font, out = sys.argv[1], sys.argv[2]
lines = sys.argv[3:] or ["a -> b => c == d != e <= f >= g", "x::y || z // w << v >> u ->> <-> <=>",
                         "á ë x⃗ v⃗ í ǰ Á Ȫ q̣̂",
                         "fn main() { let x = 0x1F; }", "|> <| <|> ~> ::= === !== -->"]
insts = [(100, 100), (300, 100), (400, 100), (700, 100), (900, 100), (400, 80), (650, 90), (400, 120)]
imgs = [render_lines(font, lines, size=40, variations={"wght": w, "wdth": d}, label=f"wght {w} wdth {d}") for w, d in insts]
stack(imgs, out)
