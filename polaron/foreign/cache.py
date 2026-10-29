"""Tiny content-hash cache for intermediate build products.

An output file ``x.ttf`` is considered fresh when ``x.ttf.key`` contains the
key computed from all of its inputs (source hashes, parameters, code hash).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .. import config

BUILD_DIR = config.BUILD / "foreign"
_PKG = Path(__file__).resolve().parent


def code_hash(*names: str) -> str:
    """Hash of the given module files of this package (plus config.py)."""
    h = hashlib.sha256()
    for n in sorted(names) + ["../config.py"]:
        p = (_PKG / n).resolve()
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def make_key(obj) -> str:
    data = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(data).hexdigest()


def _keyfile(out: Path) -> Path:
    return out.with_name(out.name + ".key")


def fresh(out: Path, key: str) -> bool:
    kf = _keyfile(out)
    return out.exists() and kf.exists() and kf.read_text(encoding="utf-8").strip() == key


def mark(out: Path, key: str) -> None:
    _keyfile(out).write_text(key, encoding="utf-8")


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
