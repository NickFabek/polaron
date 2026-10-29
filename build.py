"""Build Polaron variable fonts.

usage: uv run python build.py [--styles sans,serif] [--italic both|no|only] [--no-foreign] [--no-cjk] [--out DIR]
"""
import argparse
import logging
import time

from polaron import config as C
from polaron.assemble import build_family, export_statics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--styles", default="sans,serif")
    ap.add_argument("--italic", default="both", choices=["both", "no", "only"])
    ap.add_argument("--no-foreign", action="store_true", help="skip Arabic/Indic/Hebrew/Thai")
    ap.add_argument("--no-cjk", action="store_true", help="skip CJK")
    ap.add_argument("--out", default=None)
    ap.add_argument("--static", action="store_true", help="also export static Regular/Bold TTFs")
    a = ap.parse_args()
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    italics = {"both": [False, True], "no": [False], "only": [True]}[a.italic]
    foreign = None
    if not a.no_foreign:
        from polaron.foreign import build_foreign_masters
        foreign = lambda style: build_foreign_masters(style, C.BUILD / "foreign" / style)  # noqa: E731
    t = time.time()
    for style in a.styles.split(","):
        cjk = None
        if not a.no_cjk:
            from polaron.foreign.cjk import build_cjk_part
            cjk = build_cjk_part(style)
        for it in italics:
            vf = build_family(style, it, foreign=foreign, cjk_part=cjk, out_dir=a.out)
            if a.static:
                export_statics(vf, style, it, (a.out or C.DIST) + "/static" if a.out else C.DIST / "static")
    print(f"all done in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
