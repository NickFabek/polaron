# Polaron

Polaron is a parametric monospace type family generated entirely from Python.
It comes in **Sans** and **Serif** styles, each with true **italics**, and as
**variable fonts** with two axes:

| axis | range | default |
|------|-------|---------|
| `wght` Weight | 100 (Thin) – 900 (Heavy) | 400 |
| `wdth` Width  | 80 (Condensed) – 120 (Expanded) | 100 |

One cell is `5.5 × wdth` units wide (440 / 550 / 660 at UPM 1000). Every glyph
advances 0 (combining marks), 1 cell, or 2 cells (East-Asian wide/fullwidth
characters such as CJK and Hangul), so the grid is never broken — including by
ligatures.

## Coverage

* Latin: Basic, Latin-1, Extended-A, most of Extended-B, Latin Extended
  Additional (Vietnamese, etc.), IPA, spacing modifier letters, small capitals
* Greek and Coptic + polytonic Greek Extended (breathing/accent pairs drawn
  side by side)
* Cyrillic + common extended letters (Ukrainian, Belarusian, Serbian,
  Macedonian, Kazakh, Tatar, Bashkir, Uzbek, Azerbaijani …), with Russian
  italic forms (и т п д)
* Combining diacritics U+0300–036F and combining marks for symbols
  U+20D0–20F0 (vector arrows, enclosing circle/keycap, overlays) with GPOS
  `mark`/`mkmk` anchors; marks are drawn over the preceding cell so they also
  look right in terminals that skip GPOS; capitals get flatter `.case` marks
* Mathematical operators, supplemental operators, arrows, letterlike symbols
  (ℕ ℤ ℚ ℝ ℂ …), number forms, super/subscripts, math alphanumerics
* Box drawing (complete), block elements, shades, Braille, Symbols for Legacy
  Computing (sextants, octants, wedges), Powerline, geometric shapes
* Currency, keyboard and technical symbols (⌘ ⌥ ⌫ ⏎ ⏻ …), card suits,
  enclosed alphanumerics
* Arabic, Hebrew, Thai, and Indic scripts (Devanagari, Bengali, Gurmukhi,
  Gujarati, Oriya, Tamil, Telugu, Kannada, Malayalam, Sinhala), and CJK
  (Han, Kana, Hangul) — these are derived from the OFL **Noto** fonts and
  refitted to the cell grid (see below)

## OpenType features

* `calt` — programming ligatures that keep every cell:
  `-> <- <-> --> <-- <--> ->> <<- => <=> ==> <== <==> =>> ~> <~ ~~> <~~`
  `== === != !== =/= <= >= :: ::: := ::= || // /// << >> <<< >>> |> <| <|>`
  (turn off with `calt` = 0)
* `zero` — slashed zero; `cv01` plain zero; `cv02` slashed zero
* `cv03` single-story `a` · `cv04` double-story `g` (Sans) · `cv05` slab `l` ·
  `cv06` tailed `i` · `cv07` raised `*`
* `ccmp` — dotless i/j under accents, flat capital accents
* `mark`, `mkmk` — combining mark positioning

## Building

Built fonts are not checked in; build them yourself (or grab them from the
GitHub Releases page when one is published). Requires
[uv](https://docs.astral.sh/uv/) and Python 3.12+. From the repository root:

```bash
uv run python build.py
```

writes `dist/PolaronSans[wdth,wght].ttf`, `dist/PolaronSans-Italic[wdth,wght].ttf`,
`dist/PolaronSerif[wdth,wght].ttf`, `dist/PolaronSerif-Italic[wdth,wght].ttf`
and WOFF2 copies in `dist/web/`.

Useful flags:

* `--no-cjk` – skip CJK (the fonts become a few MB instead of tens of MB)
* `--no-foreign` – skip Arabic/Hebrew/Thai/Indic
* `--styles sans` / `--italic no` – build a subset

The first full build downloads the Noto source fonts from the
`google/fonts` repository into `sources/` (OFL-licensed).

Developer tools: `dev.py` / `zoom.py` / `myzoom.py` (quick static proofs),
`sheet.py` (every glyph), `vfproof.py` (variable font at several instances,
with HarfBuzz shaping), `tests/foreign/` (pipeline and proofing scripts for the
Noto-derived scripts), and `specimen/index.html` (open in a browser after a
build). Proof images go to `proofs/`, intermediates to `build/`; both are
git-ignored.

## Source layout

```
polaron/
  config.py       axes, masters, metrics
  geom.py         Bézier / contour utilities
  stroke.py       skeleton → outline stroker (elliptical pen, superelliptic arcs)
  glyph.py        design parameters (Params), Glyph surface, registry
  master.py       draws all glyphs per master, compatible cu2qu, writes TTFs
  features.py     FEA: GDEF, ccmp, mark/mkmk, alternates, calt
  assemble.py     varLib build, STAT, names, CJK insertion, WOFF2
  glyphs/         the designs (latin, greek, cyrillic, marks, math, arrows,
                  box, blocks, symbols, ligatures, …)
  foreign/        Noto import + monospace refitting for CJK/Arabic/Indic/…
```

## License

SIL Open Font License 1.1 — see `OFL.txt`. Glyphs for Arabic, Hebrew, Thai,
Indic scripts and CJK are derived from Noto (OFL), so the whole family is OFL.
