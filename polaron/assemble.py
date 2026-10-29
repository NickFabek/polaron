"""Assemble variable fonts: masters -> (merge foreign scripts) -> varLib ->
(insert CJK) -> STAT / names / flags -> dist/."""

from __future__ import annotations

import time
from pathlib import Path

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, InstanceDescriptor, SourceDescriptor
from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont
from fontTools import varLib

from . import config as C
from .features import build_fea
from .master import build_master_fonts, family_names


def _axis(tag):
    lo, df, hi = C.AXES[tag]
    a = AxisDescriptor()
    a.tag = tag
    a.name = C.AXIS_NAMES[tag]
    a.minimum, a.default, a.maximum = lo, df, hi
    return a


def instance_name(w, d, italic):
    parts = []
    if d != 100:
        parts.append(C.WIDTH_NAMES[d])
    if w != 400 or not parts:
        parts.append(C.WEIGHT_NAMES[w])
    name = " ".join(parts)
    if italic:
        name = "Italic" if name == "Regular" else f"{name} Italic"
    return name


def designspace(paths: dict, style, italic):
    ds = DesignSpaceDocument()
    ds.addAxis(_axis("wght"))
    ds.addAxis(_axis("wdth"))
    fam, _ = family_names(style, italic)
    for (w, d), path in paths.items():
        s = SourceDescriptor()
        s.path = str(path)
        s.name = f"master_{w}_{d}"
        s.familyName = fam
        s.location = {"Weight": w, "Width": d}
        if (w, d) == C.DEFAULT:
            s.copyInfo = s.copyLib = s.copyGroups = s.copyFeatures = True
        ds.addSource(s)
    for d in sorted(C.WIDTH_NAMES):
        for w in sorted(C.WEIGHT_NAMES):
            inst = InstanceDescriptor()
            inst.familyName = fam
            inst.styleName = instance_name(w, d, italic)
            inst.location = {"Weight": w, "Width": d}
            ds.addInstance(inst)
    return ds


def add_stat(font, italic):
    axes = [
        dict(
            tag="wght",
            name="Weight",
            values=[
                dict(value=w, name=n, **({"flags": 0x2, "linkedValue": 700} if w == 400 else {}))
                for w, n in sorted(C.WEIGHT_NAMES.items())
            ],
        ),
        dict(
            tag="wdth",
            name="Width",
            values=[dict(value=d, name=n, **({"flags": 0x2} if d == 100 else {})) for d, n in sorted(C.WIDTH_NAMES.items())],
        ),
        dict(
            tag="ital",
            name="Italic",
            values=[dict(value=1, name="Italic")] if italic else [dict(value=0, name="Roman", flags=0x2, linkedValue=1)],
        ),
    ]
    buildStatTable(font, axes, elidedFallbackName="Regular")


def set_overlap_flags(font):
    from fontTools.ttLib.tables._g_l_y_f import OVERLAP_COMPOUND, flagOverlapSimple

    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite():
            g.components[0].flags |= OVERLAP_COMPOUND
        elif g.numberOfContours > 0:
            g.flags[0] |= flagOverlapSimple


def fix_names(font, style, italic):
    fam, sub = family_names(style, italic)
    name = font["name"]
    ps = f"{fam.replace(' ', '')}-{sub}"
    for rec in list(name.names):
        if rec.nameID in (1, 2, 3, 4, 6, 16, 17):
            name.removeNames(nameID=rec.nameID)
    name.setName(fam, 1, 3, 1, 0x409)
    name.setName(sub, 2, 3, 1, 0x409)
    name.setName(f"{C.VERSION};PLRN;{ps}", 3, 3, 1, 0x409)
    name.setName(f"{fam} {sub}" if italic else fam, 4, 3, 1, 0x409)
    name.setName(ps, 6, 3, 1, 0x409)
    name.setName(f"{fam.replace(' ', '')}", 25, 3, 1, 0x409)  # variations PS name prefix
    # OS/2 + head style bits
    os2 = font["OS/2"]
    os2.fsSelection = (os2.fsSelection & ~0x61) | (0x01 if italic else 0x40) | 0x80
    font["head"].macStyle = 0x02 if italic else 0


def file_stem(style, italic):
    fam, _ = family_names(style, italic)
    return fam.replace(" ", "") + ("-Italic" if italic else "")


def build_family(style, italic, foreign=None, cjk_part=None, out_dir=None, log=print, masters=None,
                 save_masters=True, woff2=True):
    """Build one variable font. foreign: optional callable(style) ->
    {(w, d): path} of foreign-script master TTFs to merge in; cjk_part:
    optional path of a CJK part VF to insert."""
    t0 = time.time()
    masters = masters or C.MASTERS
    out_dir = Path(out_dir or C.DIST)
    work = C.BUILD / "masters" / file_stem(style, italic)
    work.mkdir(parents=True, exist_ok=True)
    log(f"[{style}{' italic' if italic else ''}] drawing {len(masters)} masters")
    fonts, _ = build_master_fonts(style, italic, masters, fea_fn=build_fea, log=log)
    paths = {}
    fmasters = foreign(style) if foreign else None
    for (w, d), f in zip(masters, fonts):
        pth = work / f"{w}-{d}.ttf"
        if fmasters:
            ours = work / f"ours-{w}-{d}.ttf"
            f.save(ours)
            from .foreign.merge import merge_with_ours

            merge_with_ours(ours, fmasters[(w, d)], pth)
        else:
            f.save(pth)
        paths[(w, d)] = pth
    log(f"  masters written in {time.time() - t0:.1f}s")
    check_grid(paths, log)
    ds = designspace(paths, style, italic)
    vf, _, _ = varLib.build(ds, optimize=True)
    log(f"  varLib done in {time.time() - t0:.1f}s")
    if cjk_part:
        from .foreign.cjk import insert_vf_glyphs

        insert_vf_glyphs(vf, TTFont(cjk_part))
        log(f"  CJK inserted in {time.time() - t0:.1f}s")
    fix_names(vf, style, italic)
    add_stat(vf, italic)
    set_overlap_flags(vf)
    finalize_os2(vf)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{file_stem(style, italic)}[wdth,wght].ttf"
    vf.save(out)
    log(f"  wrote {out} ({out.stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.1f}s")
    if woff2:
        vf.flavor = "woff2"
        wout = out_dir / "web" / f"{file_stem(style, italic)}[wdth,wght].woff2"
        wout.parent.mkdir(parents=True, exist_ok=True)
        vf.save(wout)
        log(f"  wrote {wout} ({wout.stat().st_size / 1e6:.1f} MB)")
    return out


def finalize_os2(font):
    os2 = font["OS/2"]
    os2.xAvgCharWidth = C.cell_width(C.DEFAULT[1])  # monospace cell, not the CJK-skewed mean
    try:
        os2.recalcUnicodeRanges(font)
        os2.recalcCodePageRanges(font)
    except Exception:  # pragma: no cover - older fontTools
        pass
    if os2.version < 4:
        os2.version = 4
    gl = font["glyf"]
    ys = [(gl[n].yMin, gl[n].yMax) for n in font.getGlyphOrder() if hasattr(gl[n], "yMax") and gl[n].numberOfContours]
    if ys:
        # cover tall marks/scripts against GDI clipping, but stay bounded so
        # apps that use win metrics for line height don't explode
        os2.usWinAscent = min(1150, max(C.TYPO_ASC, max(y[1] for y in ys)))
        os2.usWinDescent = min(400, max(-C.TYPO_DESC, -min(y[0] for y in ys)))


def export_statics(vf_path, style, italic, out_dir, weights=(400, 700), wdth=100, log=print):
    """Static TTFs (overlaps removed) for apps without variable-font support."""
    from fontTools.varLib.instancer import OverlapMode, instantiateVariableFont

    fam, _ = family_names(style, italic)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    for w in weights:
        vf = TTFont(vf_path)
        inst = instantiateVariableFont(vf, {"wght": w, "wdth": wdth}, overlap=OverlapMode.REMOVE_AND_IGNORE_ERRORS,
                                       updateFontNames=False)
        sub = {400: "Regular", 700: "Bold"}.get(w, C.WEIGHT_NAMES[w])
        if italic:
            sub = "Italic" if sub == "Regular" else f"{sub} Italic"
        name = inst["name"]
        rib = sub in ("Regular", "Bold", "Italic", "Bold Italic")
        fam1 = fam if rib else f"{fam} {C.WEIGHT_NAMES[w]}"
        sub1 = sub if rib else ("Italic" if italic else "Regular")
        for nid in (1, 2, 3, 4, 6, 16, 17, 25):
            name.removeNames(nameID=nid)
        ps = f"{fam.replace(' ', '')}-{sub.replace(' ', '')}"
        name.setName(fam1, 1, 3, 1, 0x409)
        name.setName(sub1, 2, 3, 1, 0x409)
        name.setName(f"{C.VERSION};PLRN;{ps}", 3, 3, 1, 0x409)
        name.setName(f"{fam} {sub}", 4, 3, 1, 0x409)
        name.setName(ps, 6, 3, 1, 0x409)
        if not rib:
            name.setName(fam, 16, 3, 1, 0x409)
            name.setName(sub, 17, 3, 1, 0x409)
        os2 = inst["OS/2"]
        os2.usWeightClass = w
        bold = w == 700
        os2.fsSelection = (os2.fsSelection & ~0x61) | (0x01 if italic else 0) | (0x20 if bold else 0) | (
            0x40 if not italic and not bold else 0)
        inst["head"].macStyle = (0x01 if bold else 0) | (0x02 if italic else 0)
        if "STAT" in inst:
            del inst["STAT"]
        out = out_dir / f"{ps}.ttf"
        inst.save(out)
        outs.append(out)
        log(f"  static {out.name}")
    return outs


def check_grid(paths, log=print):
    """Every advance must be 0, 1 or 2 cells in every master."""
    bad = []
    for (w, d), pth in paths.items():
        cell = C.cell_width(d)
        f = TTFont(pth, lazy=True)
        for name, (adv, _) in f["hmtx"].metrics.items():
            if adv not in (0, cell, 2 * cell):
                bad.append((w, d, name, adv))
    if bad:
        log(f"  GRID WARNING: {len(bad)} advances off-grid, e.g. {bad[:8]}")
    else:
        log("  grid check: all advances are 0, 1 or 2 cells")
    return bad
