"""Download the Noto source fonts from google/fonts (OFL).

Only ``https://raw.githubusercontent.com/google/fonts/main/ofl/...`` is used.
Files land in ``sources/noto/<dir>/`` together with each family's ``OFL.txt``;
``sources/noto/manifest.json`` records url, size, sha256 and git blob sha1 of
every file.  Re-running is cheap: files whose sha256 matches the manifest are
not downloaded again.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .. import config

NOTO_DIR = config.SOURCES / "noto"
MANIFEST = NOTO_DIR / "manifest.json"
RAW_BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"

# family directory -> font file, per style.  Verified against the google/fonts
# tree (Oct 2026).  Families listed under "cjk" are only needed by cjk.py.
SOURCES: dict[str, dict[str, str]] = {
    "sans": {
        "notosansarabic": "NotoSansArabic[wdth,wght].ttf",
        "notosanshebrew": "NotoSansHebrew[wdth,wght].ttf",
        "notosansthai": "NotoSansThai[wdth,wght].ttf",
        "notosansdevanagari": "NotoSansDevanagari[wdth,wght].ttf",
        "notosansbengali": "NotoSansBengali[wdth,wght].ttf",
        "notosansgurmukhi": "NotoSansGurmukhi[wdth,wght].ttf",
        "notosansgujarati": "NotoSansGujarati[wdth,wght].ttf",
        "notosansoriya": "NotoSansOriya[wdth,wght].ttf",
        "notosanstamil": "NotoSansTamil[wdth,wght].ttf",
        "notosanstelugu": "NotoSansTelugu[wdth,wght].ttf",
        "notosanskannada": "NotoSansKannada[wdth,wght].ttf",
        "notosansmalayalam": "NotoSansMalayalam[wdth,wght].ttf",
        "notosanssinhala": "NotoSansSinhala[wdth,wght].ttf",
        "notosanssc": "NotoSansSC[wght].ttf",
        "notosanskr": "NotoSansKR[wght].ttf",
    },
    "serif": {
        "notonaskharabic": "NotoNaskhArabic[wght].ttf",
        "notoserifhebrew": "NotoSerifHebrew[wdth,wght].ttf",
        "notoserifthai": "NotoSerifThai[wdth,wght].ttf",
        "notoserifdevanagari": "NotoSerifDevanagari[wdth,wght].ttf",
        "notoserifbengali": "NotoSerifBengali[wdth,wght].ttf",
        "notoserifgurmukhi": "NotoSerifGurmukhi[wght].ttf",
        "notoserifgujarati": "NotoSerifGujarati[wght].ttf",
        "notoseriforiya": "NotoSerifOriya[wght].ttf",
        "notoseriftamil": "NotoSerifTamil[wdth,wght].ttf",
        "notoseriftelugu": "NotoSerifTelugu[wght].ttf",
        "notoserifkannada": "NotoSerifKannada[wght].ttf",
        "notoserifmalayalam": "NotoSerifMalayalam[wght].ttf",
        "notoserifsinhala": "NotoSerifSinhala[wdth,wght].ttf",
        "notoserifsc": "NotoSerifSC[wght].ttf",
        "notoserifkr": "NotoSerifKR[wght].ttf",
    },
}


def source_path(family_dir: str, filename: str) -> Path:
    return NOTO_DIR / family_dir / filename


def font_path(style: str, family_dir: str) -> Path:
    """Local path of the font file for ``family_dir`` in ``style``."""
    return source_path(family_dir, SOURCES[style][family_dir])


def _url(family_dir: str, filename: str) -> str:
    return RAW_BASE + family_dir + "/" + urllib.parse.quote(filename, safe="")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"source": "https://github.com/google/fonts (ofl/)", "files": {}}


def _download(url: str, retries: int = 3) -> bytes:
    if not url.startswith(RAW_BASE):
        raise ValueError(f"refusing to download from untrusted location: {url}")
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "polaron-build"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except Exception as exc:  # pragma: no cover - network flakiness
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"download failed: {url}: {last}")


def fetch_sources(styles=("sans", "serif"), verbose: bool = True) -> dict[str, Path]:
    """Download (if needed) all Noto sources for ``styles``.

    Returns ``{relative path: local Path}`` of every font file.  Idempotent:
    a file is only fetched when missing or when its sha256 differs from the
    manifest entry.
    """
    manifest = _load_manifest()
    files = manifest.setdefault("files", {})
    out: dict[str, Path] = {}
    wanted: list[tuple[str, str]] = []
    for style in styles:
        for fam, fn in SOURCES[style].items():
            wanted.append((fam, fn))
            wanted.append((fam, "OFL.txt"))
    seen = set()
    for fam, fn in wanted:
        if (fam, fn) in seen:
            continue
        seen.add((fam, fn))
        rel = f"{fam}/{fn}"
        path = source_path(fam, fn)
        entry = files.get(rel)
        if path.exists() and entry and entry.get("sha256") == _sha256(path.read_bytes()):
            if fn != "OFL.txt":
                out[rel] = path
            continue
        url = _url(fam, fn)
        if verbose:
            print(f"fetch {url}", file=sys.stderr, flush=True)
        data = _download(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        files[rel] = {
            "url": url,
            "size": len(data),
            "sha256": _sha256(data),
            "git_blob_sha1": _git_blob_sha1(data),
            "license": "OFL-1.1",
        }
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        if fn != "OFL.txt":
            out[rel] = path
    return out


def source_sha256(path: Path) -> str:
    """sha256 recorded in the manifest for a local source file (computed if absent)."""
    rel = path.relative_to(NOTO_DIR).as_posix()
    entry = _load_manifest().get("files", {}).get(rel)
    if entry:
        return entry["sha256"]
    return _sha256(path.read_bytes())


if __name__ == "__main__":  # pragma: no cover
    for k, v in fetch_sources().items():
        print(k, v.stat().st_size)
