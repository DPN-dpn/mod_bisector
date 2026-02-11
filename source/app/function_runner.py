"""Runner helpers used by the UI.

Provides small wrappers around core functions so the UI stays thin.
"""
from typing import Dict, List
import os
import sys
import subprocess


def find_hash_results(path: str, hash_str: str) -> List[Dict[str, str]]:
    """Return list of matches from `search_hash.find_files_with_hash`.

    Raises whatever underlying function raises (kept simple; UI will catch).
    """
    from app.function.search_hash import find_files_with_hash

    return find_files_with_hash(path, hash_str)


def find_duplicate_hashes(path: str) -> Dict[str, List[str]]:
    """Return duplicate-hash map from `duplicate_hash.find_duplicate_hashes`.

    Raises underlying exceptions to be handled by callers.
    """
    from app.function.duplicate_hash import find_duplicate_hashes

    return find_duplicate_hashes(path)


def launch_binary_search(path: str, state_file: str) -> subprocess.Popen:
    """Launch the interactive `binary_search_mod` run in a separate process.

    Returns the `Popen` object for the spawned process. The function will
    create the parent directory for `state_file` if necessary.
    """
    # ensure parent dir exists
    d = os.path.dirname(state_file)
    if d:
        os.makedirs(d, exist_ok=True)

    cmd = [sys.executable, "-m", "source.app.function.binary_search_mod", "run", path, "--state", state_file]

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    if creationflags:
        proc = subprocess.Popen(cmd, creationflags=creationflags)
    else:
        proc = subprocess.Popen(cmd)
    return proc


def recover_state(state_file: str) -> int:
    """Recover entries from the given state file using module logic.

    Returns number of items restored. Raises exceptions on unexpected errors.
    """
    # import and call recover_from_state directly to avoid spawning a process
    from app.function.binary_search_mod import recover_from_state

    return recover_from_state(state_file)
