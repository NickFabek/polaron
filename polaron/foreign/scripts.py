"""Per-script configuration for the foreign-script importer.

Each :class:`ScriptSpec` says where a script comes from (Noto family per
style), which code points it owns, which OpenType script tags to keep, and
the few tuning knobs used by the refitter in :mod:`.monospace`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Code points shared by several scripts.  Each per-script font renames its
# glyph for these to the same "fgn." name, so every script's GSUB/GPOS points
# at one glyph after merging (and merge_with_ours can redirect them to ours).
SHARED = {
    0x200C: "fgn.zwnj",
    0x200D: "fgn.zwj",
    0x25CC: "fgn.dottedcircle",
}

# GSUB features needed for shaping.  Anything else (aalt, dlig, salt, ssXX,
# frac, numr, dnom, ordn, pnum, tnum, case, ...) is dropped.
GSUB_FEATURES = {
    "ccmp", "locl", "nukt", "akhn", "rphf", "rkrf", "pref", "blwf", "abvf",
    "half", "pstf", "vatu", "cjct", "cfar", "init", "medi", "fina", "isol",
    "med2", "fin2", "fin3", "rlig", "rclt", "calt", "liga", "pres", "abvs",
    "blws", "psts", "haln", "rtlm", "rvrn", "stch",
}
# GPOS features kept (PairPos and advance-only SinglePos inside them are
# removed later; cursive attachment is kept but neutralised horizontally).
GPOS_FEATURES = {"mark", "mkmk", "abvm", "blwm", "dist", "curs"}


@dataclass(frozen=True)
class ScriptSpec:
    key: str                     # short tag, also the glyph-name prefix
    name: str
    ranges: tuple                # ((lo, hi), ...) inclusive
    ot_scripts: tuple            # OpenType script tags to keep
    family: dict                 # style -> google/fonts ofl directory
    extra: tuple = ()            # extra code points (besides SHARED)
    joining: str | None = None   # None | "arabic" | "headline"
    headline_ref: str | None = None
    # Source width per style: None = choose automatically (see monospace.py)
    src_wdth: dict = field(default_factory=dict)
    vscale: dict = field(default_factory=dict)   # style -> uniform y scale
    voffset: dict = field(default_factory=dict)  # style -> y offset (units)
    drop_features: tuple = ()    # extra GSUB/GPOS features to drop
    # Typical letter ink width as a fraction of one cell.
    fill: float = 0.80
    # Indic-style overhang handling: spacing glyphs whose ink reaches far
    # past their advance (i-matra hooks) keep reaching over the next cell;
    # GDEF marks *with* an advance whose ink hangs left over the previous
    # glyph (subscripts, Tamil/Malayalam i-signs) become 0-advance.
    overhang: bool = False
    rtl: bool = False

    @property
    def prefix(self) -> str:
        return self.key + "."

    def codepoints(self) -> set[int]:
        cps = set(self.extra) | set(SHARED)
        for lo, hi in self.ranges:
            cps.update(range(lo, hi + 1))
        return cps

    def owns(self, cp: int) -> bool:
        return any(lo <= cp <= hi for lo, hi in self.ranges)

    def get(self, attr: str, style: str, default=None):
        return getattr(self, attr).get(style, default)


INDIC_EXTRA = (0x0964, 0x0965)  # dandas (Common-ish, used by all Indic scripts)

SCRIPTS: list[ScriptSpec] = [
    ScriptSpec(
        "arab", "Arabic",
        ranges=((0x0600, 0x06FF), (0x0750, 0x077F), (0x0870, 0x089F),
                (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
                (0x10E60, 0x10E7F)),
        ot_scripts=("arab",),
        family={"sans": "notosansarabic", "serif": "notonaskharabic"},
        joining="arabic",
        drop_features=("liga", "calt"),
        rtl=True,
    ),
    ScriptSpec(
        "hebr", "Hebrew",
        ranges=((0x0591, 0x05FF), (0xFB1D, 0xFB4F)),
        ot_scripts=("hebr",),
        family={"sans": "notosanshebrew", "serif": "notoserifhebrew"},
        rtl=True,
    ),
    ScriptSpec(
        "thai", "Thai",
        ranges=((0x0E01, 0x0E7F),),
        ot_scripts=("thai",),
        family={"sans": "notosansthai", "serif": "notoserifthai"},
    ),
    ScriptSpec(
        "deva", "Devanagari", overhang=True,
        ranges=((0x0900, 0x097F), (0xA8E0, 0xA8FF), (0x1CD0, 0x1CFF), (0x11B00, 0x11B5F)),
        ot_scripts=("dev2", "deva"),
        family={"sans": "notosansdevanagari", "serif": "notoserifdevanagari"},
        joining="headline", headline_ref="क",
    ),
    ScriptSpec(
        "beng", "Bengali", overhang=True,
        ranges=((0x0980, 0x09FF),),
        ot_scripts=("bng2", "beng"),
        family={"sans": "notosansbengali", "serif": "notoserifbengali"},
        extra=INDIC_EXTRA,
        joining="headline", headline_ref="ক",
    ),
    ScriptSpec(
        "guru", "Gurmukhi", overhang=True,
        ranges=((0x0A00, 0x0A7F),),
        ot_scripts=("gur2", "guru"),
        family={"sans": "notosansgurmukhi", "serif": "notoserifgurmukhi"},
        extra=INDIC_EXTRA,
        joining="headline", headline_ref="ਕ",
    ),
    ScriptSpec(
        "gujr", "Gujarati", overhang=True,
        ranges=((0x0A80, 0x0AFF),),
        ot_scripts=("gjr2", "gujr"),
        family={"sans": "notosansgujarati", "serif": "notoserifgujarati"},
        extra=INDIC_EXTRA,
    ),
    ScriptSpec(
        "orya", "Oriya", overhang=True,
        ranges=((0x0B00, 0x0B7F),),
        ot_scripts=("ory2", "orya"),
        family={"sans": "notosansoriya", "serif": "notoseriforiya"},
        extra=INDIC_EXTRA,
    ),
    ScriptSpec(
        "taml", "Tamil", overhang=True,
        ranges=((0x0B80, 0x0BFF), (0x11FC0, 0x11FFF)),
        ot_scripts=("tml2", "taml"),
        family={"sans": "notosanstamil", "serif": "notoseriftamil"},
        extra=INDIC_EXTRA,
    ),
    ScriptSpec(
        "telu", "Telugu", overhang=True,
        ranges=((0x0C00, 0x0C7F),),
        ot_scripts=("tel2", "telu"),
        family={"sans": "notosanstelugu", "serif": "notoseriftelugu"},
        extra=INDIC_EXTRA,
    ),
    ScriptSpec(
        "knda", "Kannada", overhang=True,
        ranges=((0x0C80, 0x0CFF),),
        ot_scripts=("knd2", "knda"),
        family={"sans": "notosanskannada", "serif": "notoserifkannada"},
        extra=INDIC_EXTRA,
    ),
    ScriptSpec(
        "mlym", "Malayalam", overhang=True,
        ranges=((0x0D00, 0x0D7F),),
        ot_scripts=("mlm2", "mlym"),
        family={"sans": "notosansmalayalam", "serif": "notoserifmalayalam"},
        extra=INDIC_EXTRA,
    ),
    ScriptSpec(
        "sinh", "Sinhala", overhang=True,
        ranges=((0x0D80, 0x0DFF), (0x111E0, 0x111FF)),
        ot_scripts=("sinh",),
        family={"sans": "notosanssinhala", "serif": "notoserifsinhala"},
        extra=INDIC_EXTRA,
    ),
]

SCRIPT_BY_KEY = {s.key: s for s in SCRIPTS}
