"""Interactive binary-search-style mod disabler.

Behavior summary:
- Detects mod folders by presence of any `.ini` file.
- Excludes folders already prefixed with `DISABLED ` from the bisection.
- During bisection, keeps only the current test group enabled and
  disables all other candidate mods (records those it disabled).
- On normal exit or signal, re-enables only the folders this program
  disabled during the run.

This file is a cleaned-up, more readable refactor of the original
implementation while preserving behavior.
"""

import argparse
import json
import os
import sys
import threading
from typing import Dict, List, Optional, Set


DISABLED_PREFIX = "DISABLED "

# Tracks folders this program disabled: list of disabled_on_disk_path strings
program_disabled: List[str] = []
# optional path where runtime-disabled entries are saved so recovery is possible
STATE_FILE: Optional[str] = None

# Optional threading.Event set by callers to request an early stop of the
# bisection run. When set the run will exit as soon as it notices the flag.
STOP_EVENT: Optional[threading.Event] = None

# Ask function used for interactive prompts. Can be overridden by callers
# (e.g., UI code) to provide GUI dialogs instead of console input.
ASK_FN = input
# Optional callback used to report the final found mode (string). If set,
# it will be called with the final on-disk path; otherwise the program
# prints to stdout as before.
RESULT_FN = None


def _is_disabled_name(name: str) -> bool:
    return name.startswith(DISABLED_PREFIX)


def _disabled_name_for(path: str) -> str:
    parent = os.path.dirname(path)
    name = os.path.basename(path)
    return os.path.join(parent, DISABLED_PREFIX + name)


def disable_folder(path: str) -> str:
    """Rename `path` to disabled name and return the new path.

    If `path` is already disabled, returns it unchanged.
    """
    name = os.path.basename(path)
    if _is_disabled_name(name):
        return path
    new_path = _disabled_name_for(path)
    # try rename with retry/skip/abort UI if it fails
    ok = _rename_with_retry(path, new_path)
    if ok:
        return new_path
    # skipped or failed -> return original path unchanged
    return path


def enable_folder(disabled_path: str) -> str:
    """Rename a disabled folder back to its original name and return it.

    If `disabled_path` is not a disabled name, returns it unchanged.
    """
    name = os.path.basename(disabled_path)
    if not _is_disabled_name(name):
        return disabled_path
    parent = os.path.dirname(disabled_path)
    orig_name = name[len(DISABLED_PREFIX) :]
    new_path = os.path.join(parent, orig_name)
    ok = _rename_with_retry(disabled_path, new_path)
    if ok:
        return new_path
    return disabled_path


def _rename_with_retry(src: str, dst: str) -> bool:
    """Attempt to rename `src` -> `dst`.

    On failure, prompt the user to: 다시시도(R), 건너뛰기(S), 중단(A).
    Returns True if rename succeeded, False if user skipped.
    Raises an exception if the user chooses to abort or if an unexpected
    exception occurs and the user selects abort.
    """
    while True:
        if STOP_EVENT and STOP_EVENT.is_set():
            raise RuntimeError("사용자 요청으로 탐색 중단됨")
        try:
            os.rename(src, dst)
            return True
        except Exception as e:
            print(f"폴더 이름을 바꾸는 동안 오류가 발생했습니다: {src}")
            print(f"오류: {e}")
            resp = ASK_FN("[R] 다시시도, [S] 건너뛰기, [A] 중단 중 선택: ").strip().lower()
            if not resp:
                continue
            c = resp[0]
            if c == "r":
                # retry loop
                continue
            if c == "s":
                print("건너뛰고 계속합니다.")
                return False
            if c == "a":
                print("작업을 중단합니다.")
                raise RuntimeError("사용자 요청으로 작업 중단됨")
            # unknown input -> re-prompt
            print("유효한 선택이 아닙니다. R, S, A 중에서 선택하세요.")


def find_mod_folders(start_path: Optional[str]) -> List[Dict[str, str]]:
    if not start_path:
        return []
    start_path = os.path.abspath(start_path)
    if not os.path.isdir(start_path):
        return []

    mods: List[Dict[str, str]] = []
    for dirpath, dirnames, files in os.walk(start_path, topdown=True):
        if any(f.lower().endswith(".ini") for f in files):
            mods.append(
                {"name": os.path.basename(dirpath), "path": os.path.abspath(dirpath)}
            )
            dirnames[:] = []
    return mods


def _save_state() -> None:
    """Write `program_disabled` to STATE_FILE (atomic replace)."""
    global STATE_FILE
    if not STATE_FILE:
        return
    # ensure target directory exists
    d = os.path.dirname(STATE_FILE)
    if d:
        os.makedirs(d, exist_ok=True)

    if not program_disabled:
        # remove state file if exists
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        return

    data = list(program_disabled)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def _load_state(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: List[str] = []
    for item in data:
        if isinstance(item, str):
            out.append(item)
    return out


def recover_from_state(path: str, state_file: str) -> int:
    """Recover (enable) entries recorded in state file. Returns number restored.

    State file contains a JSON list of disabled-on-disk paths (strings).
    """
    # Pre-recover: if a backup exists in workspace temp, try to restore it
    restored_backup = False
    try:
        workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        temp_dir = os.path.join(workspace_root, "temp")
        backup_ini = os.path.join(temp_dir, "d3dx_user.ini")
        if os.path.exists(backup_ini):
            if not path:
                print("복원: 원본 위치를 결정할 수 없어 백업을 복원하지 않습니다.", file=sys.stderr)
            else:
                try:
                    src_ini = os.path.normpath(os.path.join(path, os.pardir, "d3dx_user.ini"))
                    tmp_dst = src_ini + ".tmp"
                    with open(backup_ini, "rb") as fr, open(tmp_dst, "wb") as fw:
                        fw.write(fr.read())
                    os.replace(tmp_dst, src_ini)
                    restored_backup = True
                    print(f"복원: 백업을 {src_ini}로 복원했습니다.", file=sys.stderr)
                except Exception as e:
                    print(f"복원 실패: {e}", file=sys.stderr)
            # only remove backup if restore succeeded
            if restored_backup:
                try:
                    os.remove(backup_ini)
                except Exception:
                    pass
    except Exception:
        # ignore failures to locate/restore backups; proceed to normal recover
        pass
    
    restored = 0
    data = _load_state(state_file)
    for disabled in data:
        if os.path.exists(disabled) and _is_disabled_name(os.path.basename(disabled)):
            enable_folder(disabled)
            restored += 1
    # remove state file after attempting recovery
    if os.path.exists(state_file):
        os.remove(state_file)
    return restored


def run_bisection(start_path: str) -> None:
    # Pre-run: backup ..\d3dx_user.ini (relative to `start_path`) into workspace temp
    try:
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        temp_dir = os.path.join(workspace_root, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        src_ini = os.path.normpath(os.path.join(start_path, os.pardir, "d3dx_user.ini"))
        if os.path.exists(src_ini):
            dst = os.path.join(temp_dir, "d3dx_user.ini")
            tmp = dst + ".tmp"
            with open(src_ini, "rb") as fr, open(tmp, "wb") as fw:
                fw.write(fr.read())
            os.replace(tmp, dst)
    except Exception:
        # Do not fail the operation if backup cannot be made; just continue.
        pass

    mods = find_mod_folders(start_path)
    if not mods:
        print("모드를 찾지 못했습니다.")
        return

    # Human-friendly mod list output
    print(f"발견된 모드 수: {len(mods)}")
    for m in mods:
        print(f"- {m.get('name')}: {m.get('path')}")

    # Build candidate list (original, unprefixed paths). Do not include
    # items already prefixed with DISABLED at program start.
    candidates: List[str] = []
    original_disabled_on_disk: Set[str] = set()
    for m in mods:
        name = m["name"]
        disk_path = os.path.abspath(m["path"])
        if _is_disabled_name(name):
            original_disabled_on_disk.add(disk_path)
        else:
            candidates.append(disk_path)

    if not candidates:
        print("활성화된(비활성화되지 않은) 모드가 없습니다.")
        return

    # Helpers to enable/disable only candidates we control
    def ensure_disabled(orig: str) -> None:
        if os.path.exists(orig):
            disabled = disable_folder(orig)
            # only record when we actually renamed to a DISABLED name
            if _is_disabled_name(os.path.basename(disabled)) and os.path.exists(disabled):
                program_disabled.append(disabled)
                # persist runtime-disabled list if requested
                if STATE_FILE:
                    _save_state()

    def ensure_enabled_if_recorded(orig: str) -> None:
        # If we previously disabled this orig during this run, re-enable it.
        d = _disabled_name_for(orig)
        if (
            d in program_disabled
            and os.path.exists(d)
            and _is_disabled_name(os.path.basename(d))
        ):
            newp = enable_folder(d)
            # if original disabled path no longer exists, enable succeeded
            if not os.path.exists(d) and d in program_disabled:
                program_disabled.remove(d)

    def set_active_group(group: List[str]) -> None:
        """Ensure only `group` (subset of `candidates`) is enabled.

        All other candidates will be disabled (if not already) and
        recorded so they can be restored later.
        """
        group_set = set(group)
        for orig in candidates:
            if orig in group_set:
                ensure_enabled_if_recorded(orig)
            else:
                ensure_disabled(orig)

    # Bisection loop: narrow `current` to a single candidate
    current = candidates.copy()
    try:
        while len(current) > 1:
            if STOP_EVENT and STOP_EVENT.is_set():
                print("사용자가 탐색을 중단했습니다.")
                break
            mid = len(current) // 2
            first = current[:mid]
            second = current[mid:]

            # Test first half: enable only `first` and keep others disabled
            set_active_group(first)

            # Output disabled and remaining lists (on-disk paths)
            disabled_list = [
                {"name": os.path.basename(p), "path": p}
                for p in candidates
                if p not in first
            ]
            remaining_list = [{"name": os.path.basename(p), "path": p} for p in first]
            # Print readable summaries
            print("비활성화된 항목:")
            if disabled_list:
                for d in disabled_list:
                    print(f"- {d['name']}: {d['path']}")
            else:
                print("(없음)")
            print("남아있는 항목:")
            if remaining_list:
                for r in remaining_list:
                    print(f"- {r['name']}: {r['path']}")
            else:
                print("(없음)")

            resp = (
                ASK_FN(
                    "이 상태에서 문제(또는 원하는 결과)가 발생합니까?\n인게임에서 F10을 눌러 확인하세요: "
                )
                .strip()
                .lower()
            )
            if resp == "a":
                # user requested abort
                raise RuntimeError("사용자 요청으로 탐색 중단됨")
            if resp == "y":
                # problem occurs when first half alone is enabled => culprit in first
                current = first
            else:
                # problem does not occur with first enabled => culprit in second
                # switch to second as active group
                set_active_group(second)
                current = second

        # Print result if single candidate remains
        if len(current) == 1:
            # determine on-disk path (it may be disabled name or original depending on state)
            on_disk = _disabled_name_for(current[0])
            if os.path.exists(current[0]):
                final = current[0]
            elif os.path.exists(on_disk):
                final = on_disk
            else:
                final = current[0]
            # Report via RESULT_FN if provided (GUI), else print
            if RESULT_FN:
                try:
                    RESULT_FN(final)
                except Exception:
                    print(final)
            else:
                print(final)
        else:
            print("검색이 종료되었습니다.")

    finally:
        # If a state file was provided, use it to recover (enable) entries
        # we persisted during the run. If no state file is set, there is
        # nothing to recover here.
        if STATE_FILE and not (STOP_EVENT and STOP_EVENT.is_set()):
            # Only auto-recover when the run was not aborted by the user.
            recover_from_state(src_ini, STATE_FILE)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Binary search disable mods interactively"
    )
    sub = parser.add_subparsers(dest="cmd")

    runp = sub.add_parser("run", help="Run interactive bisection")
    runp.add_argument("path", nargs="?", help="Start path to search for mods")
    runp.add_argument(
        "--state",
        "-s",
        required=True,
        help="Path to save runtime-disabled list (JSON) (required)",
    )

    rec = sub.add_parser("recover", help="Recover from a saved state file")
    rec.add_argument("state_file", help="State file path to recover from")

    args = parser.parse_args()

    if args.cmd == "recover":
        n = recover_from_state(args.state_file)
        print(f"복구 시도 완료: {n} 항목 복구됨")
        return

    # default to run if no subcommand provided
    state = None
    path = None
    if args.cmd == "run":
        path = args.path
        state = args.state
    else:
        # legacy interactive prompt: require both path and state
        path = input("모드가 들어있는 폴더 경로를 입력하세요: ").strip()
        if not path:
            print("경로가 제공되지 않았습니다.")
            return
        state = input("상태 파일 경로를 입력하세요 (저장할 JSON 파일): ").strip()
        if not state:
            print("상태 파일 경로는 필수입니다.")
            return

    if not path:
        print("경로가 제공되지 않았습니다.")
        return

    if not state:
        print("--state 경로가 필요합니다.")
        return

    global STATE_FILE
    STATE_FILE = os.path.abspath(state)
    # ensure directory for state file exists
    d = os.path.dirname(STATE_FILE)
    if d:
        os.makedirs(d, exist_ok=True)
    try:
        run_bisection(path)
    except Exception as e:
        print(f"오류 발생: {e}")
        # non-zero exit to indicate failure
        sys.exit(1)


if __name__ == "__main__":
    main()
