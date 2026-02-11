"""Search .ini files under a folder for a specific hex hash value.

Usage:
  python -m source.app.function.search_hash <path> <hexhash>

Output:
  Prints a JSON array of objects describing matching files. Each object
  contains at least the file path under key "file".
"""
from __future__ import annotations

import os
import argparse
import json
import re
from typing import List, Dict, Optional


def normalize_hash(s: str) -> str:
    return s.strip().lower().lstrip("0x")


def find_files_with_hash(start_path: str, target_hash: str) -> List[Dict[str, str]]:
    start_path = os.path.abspath(start_path)
    if not os.path.isdir(start_path):
        return []

    target = normalize_hash(target_hash)
    pattern = re.compile(r"^\s*hash\s*=\s*([0-9a-fA-Fx]+)\s*$", flags=re.IGNORECASE)

    results: List[Dict[str, str]] = []
    for dirpath, _, files in os.walk(start_path):
        for fn in files:
            if not fn.lower().endswith('.ini'):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        m = pattern.match(line)
                        if m:
                            found = normalize_hash(m.group(1))
                            if found == target:
                                results.append({"file": os.path.abspath(path)})
                                # once matched, no need to check more lines in this file
                                raise StopIteration
            except StopIteration:
                continue
            except Exception:
                # ignore unreadable files
                continue

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description='Search .ini files for a given hex hash')
    parser.add_argument('path', help='Start folder to search')
    parser.add_argument('hash', help='Hex hash value to look for')
    args = parser.parse_args()

    matches = find_files_with_hash(args.path, args.hash)
    # Human-friendly text output
    if not matches:
        print("검색 결과가 없습니다.")
        return
    print(f"검색 결과: {len(matches)} 파일")
    for m in matches:
        file = m.get("file") if isinstance(m, dict) else m
        print(f"- {file}")


if __name__ == '__main__':
    main()
