"""Shared constants for the Polaron build.

Everything that has to agree between the parametric glyph generator, the
foreign-script importer and the variable-font assembler lives here.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
BUILD = ROOT / "build"
DIST = ROOT / "dist"

FAMILY = "Polaron"
VERSION = "0.1.0"

UPM = 1000

# Axis: (min, default, max)
AXES = {
    "wght": (100, 400, 900),
    "wdth": (80, 100, 120),
}
AXIS_NAMES = {"wght": "Weight", "wdth": "Width"}


def cell_width(wdth: float) -> int:
    """Advance width of one monospace cell at a given wdth value."""
    return round(5.5 * wdth)


WEIGHTS = (100, 400, 900)
WIDTHS = (80, 100, 120)
DEFAULT = (400, 100)  # (wght, wdth)

# Full master grid used for our own glyphs and for scripts with GPOS.
MASTERS = [(w, d) for w in WEIGHTS for d in WIDTHS]
# Axis-extreme masters only; enough for glyphs whose width variation is affine
# (CJK). Corners are reached additively.
SPARSE_MASTERS = [DEFAULT, (100, 100), (900, 100), (400, 80), (400, 120)]

# Vertical metrics (font units, UPM 1000)
XHEIGHT = 536
CAP = 730
ASCENDER = 770  # b d h k l
DESCENDER = -220  # p q y g
TYPO_ASC = 950
TYPO_DESC = -250
LINE_GAP = 0
# Box drawing / block elements span the whole line box.
BOX_TOP = TYPO_ASC
BOX_BOTTOM = TYPO_DESC

STYLES = ("sans", "serif")

# Named instances (fvar) and STAT labels
WEIGHT_NAMES = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
    900: "Heavy",
}
WIDTH_NAMES = {
    80: "Condensed",
    90: "SemiCondensed",
    100: "Normal",
    110: "SemiExpanded",
    120: "Expanded",
}
