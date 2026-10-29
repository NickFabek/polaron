"""Render proofs + grid audit for the final test VFs built by run_pipeline.py.

    uv run python tests/foreign/proof.py [sans|serif ...]

PNGs go to proofs/foreign/<style>/<group>-w<wght>-d<wdth>.png; every line
is drawn on its cell grid (green ticks = pen position on the grid).  The
audit checks, with HarfBuzz at many (wght, wdth) locations including
intermediate ones, that *every* glyph advance is 0 or a multiple of the
cell, and writes proofs/foreign/<style>/audit.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import uharfbuzz as hb  # noqa: E402

from polaron import config  # noqa: E402
from polaron.foreign import cache  # noqa: E402
from proofing import Shaper, render_lines  # noqa: E402
from samples import SAMPLES  # noqa: E402

PROOF_DIR = ROOT / "proofs" / "foreign"
INSTANCES = [(400, 100), (100, 80), (900, 120), (700, 90), (250, 110)]
AUDIT_LOCATIONS = [(w, d) for w in (100, 250, 400, 650, 900) for d in (80, 90, 100, 110, 120)]
GROUPS = {
    "rtl": ["arab", "hebr"],
    "indic-north": ["deva", "beng", "guru", "gujr", "orya"],
    "indic-south": ["taml", "telu", "knda", "mlym", "sinh"],
    "thai-cjk": ["thai", "cjk"],
}
MIXED = [("mixed", "abc = مرحبا; x = नमस्ते; // 汉字 한글")]


def audit(path: Path) -> dict:
    face = hb.Face(hb.Blob.from_file_path(str(path)))
    n = face.glyph_count
    bad = []
    for w, d in AUDIT_LOCATIONS:
        font = hb.Font(face)
        font.set_variations({"wght": w, "wdth": d})
        cell = 5.5 * d  # == config.cell_width(d) at integer-cell wdth values
        for gid in range(n):
            adv = font.get_glyph_h_advance(gid)
            k = adv / cell
            if adv and abs(k - round(k)) * cell > 0.51:
                bad.append((w, d, gid, adv))
    return {"glyphs": n, "locations": len(AUDIT_LOCATIONS), "violations": len(bad),
            "examples": bad[:20]}


def proof_style(style: str) -> dict:
    vf = cache.BUILD_DIR / "test" / style / f"PolaronTest-{style}-VF.ttf"
    if not vf.exists():
        vf = cache.BUILD_DIR / "test" / style / f"PolaronTest-{style}-noCJK-VF.ttf"
    out = PROOF_DIR / style
    out.mkdir(parents=True, exist_ok=True)
    shaper = Shaper(vf)
    stats = {}
    for w, d in INSTANCES:
        for group, keys in GROUPS.items():
            lines = []
            for k in keys:
                lines += SAMPLES[k]
            if group == "rtl":
                lines += MIXED
            png = out / f"{group}-w{w}-d{d}.png"
            st = render_lines(shaper, lines, png, size=40, variations={"wght": w, "wdth": d},
                              cell=config.cell_width(d),
                              title=f"Polaron foreign test ({style}) wght {w} wdth {d}: {group}")
            stats[png.name] = st
    rep = {"font": str(vf), "render": stats, "audit": audit(vf)}
    (out / "audit.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


if __name__ == "__main__":
    styles = sys.argv[1:] or list(config.STYLES)
    for st in styles:
        r = proof_style(st)
        bad = sum(v["off_grid"] for v in r["render"].values())
        print(st, "off-grid pen positions:", bad, "audit:", r["audit"]["violations"], "violations /",
              r["audit"]["glyphs"], "glyphs x", r["audit"]["locations"], "locations")
