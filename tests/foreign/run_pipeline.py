"""End-to-end test of the foreign-script pipeline (both styles).

    uv run python tests/foreign/run_pipeline.py [sans|serif ...] [--no-cjk]

For each style:
  1. foreign masters        (polaron.foreign.monospace.build_foreign_masters)
  2. dummy "ours" masters   (tests/foreign/dummy_ours.py)
  3. merge                  (polaron.foreign.merge.merge_with_ours)
  4. fontTools.varLib.build (designspace with the 9 MASTERS, default 400/100)
  5. CJK part VF + insert   (polaron.foreign.cjk)
  6. checks: grid advances at many locations, compatibility, glyph counts,
     sizes -> build/foreign/test/<style>/report.json
Outputs land in build/foreign/test/<style>/.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(Path(__file__).resolve().parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from fontTools import varLib  # noqa: E402

from polaron import config  # noqa: E402
from polaron.foreign import cache, checks, cjk, merge, monospace  # noqa: E402
from dummy_ours import build_dummy_master  # noqa: E402

log = logging.getLogger("pipeline")
TEST_DIR = cache.BUILD_DIR / "test"


def designspace(masters: dict, path: Path) -> DesignSpaceDocument:
    ds = DesignSpaceDocument()
    for tag, (lo, d, hi) in config.AXES.items():
        a = AxisDescriptor()
        a.tag, a.name = tag, config.AXIS_NAMES[tag]
        a.minimum, a.default, a.maximum = lo, d, hi
        ds.addAxis(a)
    for (w, d), p in masters.items():
        s = SourceDescriptor()
        s.path = str(p)
        s.name = f"master.{w}.{d}"
        s.location = {"Weight": w, "Width": d}
        ds.addSource(s)
    ds.write(path)
    return ds


def build_style(style: str, with_cjk: bool = True) -> dict:
    out = TEST_DIR / style
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timings = {}
    fgn = monospace.build_foreign_masters(style, out / "foreign")
    timings["foreign_masters"] = round(time.time() - t0, 1)
    t = time.time()
    merged = {}
    for (w, d), fp in fgn.items():
        ours = build_dummy_master(w, d, out / "ours" / f"ours-{w}-{d}.ttf", style)
        merged[(w, d)] = merge.merge_with_ours(ours, fp, out / "merged" / f"merged-{w}-{d}.ttf")
    timings["merge"] = round(time.time() - t, 1)
    # merged masters must be compatible before varLib sees them
    fonts = {m: TTFont(p) for m, p in merged.items()}
    checks.assert_compatible(fonts)
    for (w, d), f in fonts.items():
        checks.assert_grid(f, config.cell_width(d))
    del fonts
    t = time.time()
    ds_path = out / f"Polaron-{style}.designspace"
    designspace(merged, ds_path)
    vf, _, _ = varLib.build(str(ds_path), optimize=True)
    vf_path = out / f"PolaronTest-{style}-noCJK-VF.ttf"
    vf.save(vf_path)
    timings["varLib.build"] = round(time.time() - t, 1)
    final_path = vf_path
    report = {"style": style}
    if with_cjk:
        t = time.time()
        part = cjk.build_cjk_part(style)
        timings["cjk_part"] = round(time.time() - t, 1)
        t = time.time()
        main = TTFont(vf_path)
        cjk.insert_vf_glyphs(main, TTFont(part))
        final_path = out / f"PolaronTest-{style}-VF.ttf"
        main.save(final_path)
        timings["cjk_insert"] = round(time.time() - t, 1)
        report["cjk_part"] = {"path": str(part), "size": part.stat().st_size,
                              "glyphs": len(TTFont(part).getGlyphOrder())}
    final = TTFont(final_path)
    report.update({
        "final": str(final_path),
        "final_size": final_path.stat().st_size,
        "noCJK_size": vf_path.stat().st_size,
        "glyphs_total": len(final.getGlyphOrder()),
        "glyphs_by_prefix": _count_prefixes(final.getGlyphOrder()),
        "master_sizes": {f"{w}/{d}": p.stat().st_size for (w, d), p in fgn.items()},
        "timings_s": timings,
    })
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def _count_prefixes(order):
    counts = {}
    for g in order:
        head = g.split(".", 1)[0] if "." in g and not g.startswith(".") else "ours"
        counts[head] = counts.get(head, 0) + 1
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    styles = args or list(config.STYLES)
    for st in styles:
        rep = build_style(st, with_cjk="--no-cjk" not in sys.argv)
        print(json.dumps(rep, indent=1))
