"""Scan INI files under a folder and report duplicate `hash = ...` values.

Usage as module:
    from app.duplicate_hash import find_duplicate_hashes
    dups = find_duplicate_hashes(r"C:\path\to\folder")

CLI:
    python -m source.app.duplicate_hash C:\path\to\folder
"""
from __future__ import annotations
import os
import re
import sys
import json
from typing import Dict, List


_HASH_RE = re.compile(r"^\s*hash\s*=\s*(.+)$", flags=re.IGNORECASE)


def extract_hash_from_file(path: str) -> List[str]:
    """Return all hash values found in the given INI file as strings.

    Looks for lines like `hash = value` (case-insensitive) and returns the
    stripped value(s). If the file can't be read, returns an empty list.
    """
    vals: List[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = _HASH_RE.match(line)
                if m:
                    v = m.group(1).strip()
                    # remove inline comments (e.g. ; comment or # comment or // comment)
                    v = re.split(r"\s*(?:;|#|//)", v, maxsplit=1)[0].strip()
                    # strip optional quotes
                    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                        v = v[1:-1].strip()
                    # ignore empty or purely punctuation values
                    if v and any(ch.isalnum() for ch in v):
                        vals.append(v)
    except Exception:
        # ignore unreadable files
        pass
    return vals


def find_duplicate_hashes(start_path: str) -> Dict[str, List[str]]:
    """Scan `start_path` recursively for .ini files and return duplicates.

    Returns a dict mapping hash -> list of file paths that contain that hash.
    Only hashes that appear in more than one file are included in the result.
    """
    start_path = os.path.abspath(start_path)
    if not os.path.isdir(start_path):
        raise FileNotFoundError(f"Not a directory: {start_path}")

    hash_map: Dict[str, List[str]] = {}

    for dirpath, dirnames, files in os.walk(start_path, topdown=True):
        # remove disabled directories from traversal (prefix match, case-insensitive)
        dirnames[:] = [d for d in dirnames if not d.upper().startswith("DISABLED")]

        # skip this directory entirely if any component starts with DISABLED
        if any(part.upper().startswith("DISABLED") for part in os.path.relpath(dirpath, start_path).split(os.sep)):
            continue

        for fn in files:
            # skip disabled files
            if fn.upper().startswith("DISABLED"):
                continue
            if fn.lower().endswith(".ini"):
                p = os.path.join(dirpath, fn)
                vals = set(extract_hash_from_file(p))
                for v in vals:
                    hash_map.setdefault(v, []).append(p)

    # filter to only duplicates
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return duplicates


def _main(argv: List[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if not argv:
        print("Usage: python -m source.app.duplicate_hash <folder-path>", file=sys.stderr)
        return 2
    start = argv[0]
    try:
        dups = find_duplicate_hashes(start)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Human-friendly text output
    if not dups:
        print("중복 해시를 찾지 못했습니다.")
        return 0

    for h, paths in sorted(dups.items()):
        print(f"해시: {h}")
        for p in paths:
            print(f"  - {p}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
