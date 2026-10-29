"""Foreign-script support for Polaron.

Polaron does not draw Arabic, Hebrew, Thai, the Indic scripts or CJK itself.
This package derives them from OFL Noto fonts (google/fonts) and refits them
to Polaron's monospace cell grid:

* :mod:`.fetch`      -- download the Noto sources (idempotent, with manifest)
* :mod:`.scripts`    -- per-script configuration (Unicode ranges, sources, tuning)
* :mod:`.monospace`  -- instance + subset + refit the non-CJK scripts into one
                        static TTF per Polaron master
* :mod:`.cjk`        -- build a CJK "part" variable font and insert it into a
                        finished variable font at glyph level
* :mod:`.merge`      -- merge one of our static masters with a foreign master

Every glyph advance produced here is 0 (marks) or an integer number of cells,
``cell = config.cell_width(wdth)``.
"""

from .fetch import fetch_sources  # noqa: F401
