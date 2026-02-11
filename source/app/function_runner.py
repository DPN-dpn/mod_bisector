"""Runner helpers used by the UI.

Provides small wrappers around core functions so the UI stays thin.
"""

from typing import Dict, List
import os
import sys
import subprocess
import threading
import json


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

    cmd = [
        sys.executable,
        "-m",
        "source.app.function.binary_search_mod",
        "run",
        path,
        "--state",
        state_file,
    ]

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    if creationflags:
        proc = subprocess.Popen(cmd, creationflags=creationflags)
    else:
        proc = subprocess.Popen(cmd)
    return proc


def recover_state(path: str, state_file: str) -> int:
    """Recover entries from the given state file using module logic.

    Returns number of items restored. Raises exceptions on unexpected errors.
    """
    # Delegate recovery to the core module which now handles any pre-recover work.
    from app.function.binary_search_mod import recover_from_state

    return recover_from_state(path, state_file)


def run_binary_search_gui(
    path: str, state_file: str, ask_fn, result_fn=None, stop_event=None
) -> threading.Thread:
    """Run binary search in a background thread, using `ask_fn` for prompts.

    `ask_fn` should be a callable that accepts a prompt string and returns
    the user's response string. `result_fn`, if provided, will be used to
    receive the final found mode string. The returned `Thread` is started
    and returned to the caller.
    """
    # NOTE: pre-run backup moved to `binary_search_mod.run_bisection`.

    def target():
        # import here to ensure module is fresh and available
        import app.function.binary_search_mod as mod

        # set module-level state file and ask function
        mod.STATE_FILE = state_file
        mod.ASK_FN = ask_fn
        # set optional result callback
        mod.RESULT_FN = result_fn
        # set optional stop event to allow early termination
        mod.STOP_EVENT = stop_event
        try:
            mod.run_bisection(path)
        except RuntimeError as e:
            # If user requested abort inside the bisection, suppress traceback.
            if "사용자 요청" in str(e) or "중단" in str(e):
                # silent abort
                pass
            else:
                print(f"binary search error: {e}", file=sys.stderr)
        except Exception as e:
            # avoid unhandled exception printing a full traceback from thread
            print(f"binary search unexpected error: {e}", file=sys.stderr)
        finally:
            # leave STATE_FILE/ASK_FN/RESULT_FN as-is; caller may remove state file
            pass

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return t
