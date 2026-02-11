import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog, messagebox, filedialog
import json
from typing import Optional
import os

from app import path_manager
from app.function_runner import (
    find_hash_results,
    find_duplicate_hashes,
    launch_binary_search,
    recover_state,
)


def build_ui(root: tk.Tk) -> tk.StringVar:
    """Build the main window layout into the given root.

    Returns the `StringVar` that holds the selected folder path.
    """
    # 상단: 폴더 경로 입력 + 찾아보기
    top = ttk.Frame(root, padding=(12, 8))
    top.pack(fill="x")

    path_var = tk.StringVar()

    lbl = ttk.Label(top, text="Mods :")
    lbl.pack(side="left")

    entry = ttk.Entry(top, textvariable=path_var, state="readonly")
    entry.pack(side="left", padx=8, expand=True, fill="x")

    browse_btn = ttk.Button(top, text="찾아보기...", command=lambda: _on_browse())
    browse_btn.pack(side="left")

    # 상태 파일 경로: 워크스페이스의 temp 폴더 아래로 고정
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    state_dir = os.path.join(workspace_root, "temp")
    state_file = os.path.join(state_dir, "binary_search_state.json")

    # 본문 자리 (추후 컴포넌트 추가)
    content = ttk.Frame(root, padding=(12, 0))
    content.pack(fill="both", expand=True)

    # 작업 버튼 (핸들러는 아래에 정의되어 있습니다)
    btn_find_hash = ttk.Button(content, text="해시 찾기", command=lambda: on_find_hash())
    btn_find_hash.pack(fill="x", pady=(8, 6), ipady=8)

    btn_find_duplicates = ttk.Button(content, text="중복 해시 찾기", command=lambda: on_find_duplicates())
    btn_find_duplicates.pack(fill="x", pady=(8, 6), ipady=8)

    # Binary search and recover buttons in a single horizontal row
    actions_row = ttk.Frame(content)
    actions_row.pack(fill="x", pady=(8, 8))

    btn_binary_search = ttk.Button(actions_row, text="모드 이진 탐색", command=lambda: on_binary_search())
    btn_binary_search.pack(side="left", fill="x", expand=True, ipady=8)

    # 복원 버튼은 기본적으로 숨김; 상태 파일이 있으면 보이도록 함
    btn_recover = ttk.Button(actions_row, text="복원", command=lambda: on_recover())
    if os.path.exists(state_file):
        btn_recover.pack(side="left", padx=(8, 0), ipadx=8, ipady=8)

    # --- 핸들러 및 헬퍼 함수들 (UI 구성 아래에 모아둠) ---
    def _show_text_window(title: str, text: str) -> None:
        w = tk.Toplevel(root)
        w.title(title)
        txt = tk.Text(w, wrap="none")
        txt.insert("1.0", text)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True)

    def _ensure_valid_path() -> Optional[str]:
        p = path_var.get()
        if not path_manager.ensure_dir(p):
            messagebox.showerror("오류", "유효한 폴더 경로를 설정하세요.")
            return None
        return p

    def _on_browse() -> None:
        p = path_manager.browse_directory(root)
        if p:
            path_var.set(p)

    def on_find_hash() -> None:
        p = _ensure_valid_path()
        if not p:
            return
        h = simpledialog.askstring(
            "해시 검색",
            "찾을 해시값을 입력하세요 :",
        )
        if not h:
            return
        try:
            matches = find_hash_results(p, h)
            if not matches:
                _show_text_window("해시 검색 결과", "검색 결과가 없습니다.")
            else:
                lines = [f"검색 결과: {len(matches)} 파일"]
                for m in matches:
                    # m may be a dict with 'file' key or a string
                    file = m.get("file") if isinstance(m, dict) else m
                    lines.append(f"- {file}")
                _show_text_window("해시 검색 결과", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("오류", f"검색 중 오류가 발생했습니다: {e}")

    def on_find_duplicates() -> None:
        p = _ensure_valid_path()
        if not p:
            return
        try:
            dups = find_duplicate_hashes(p)
            if not dups:
                _show_text_window("중복 해시 결과", "중복 해시를 찾지 못했습니다.")
            else:
                lines = []
                for h, paths in sorted(dups.items()):
                    lines.append(f"해시: {h}")
                    for q in paths:
                        lines.append(f"  - {q}")
                    lines.append("")
                _show_text_window("중복 해시 결과", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("오류", f"검색 중 오류가 발생했습니다: {e}")

    def on_binary_search() -> None:
        p = _ensure_valid_path()
        if not p:
            return
        try:
            launch_binary_search(p, state_file)
            # enable recover button because run may create state file
            if os.path.exists(state_file):
                # show recover button if state file was created
                if not btn_recover.winfo_ismapped():
                    btn_recover.pack(side="left", padx=(8, 0), ipadx=8, ipady=8)
        except Exception as e:
            messagebox.showerror("오류", f"이진 탐색 실행에 실패했습니다: {e}")

    def on_recover() -> None:
        # Call recover logic and report result
        if not os.path.exists(state_file):
            messagebox.showinfo("복원", "복원할 상태 파일이 없습니다.")
            btn_recover.state(["disabled"])
            return
        try:
            n = recover_state(state_file)
            messagebox.showinfo("복원 완료", f"복구 시도 완료: {n} 항목 복구됨")
            # hide recover button after successful recovery
            try:
                if btn_recover.winfo_ismapped():
                    btn_recover.pack_forget()
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("오류", f"복원 중 오류가 발생했습니다: {e}")

    # 초기값 설정 (저장된 경로가 있으면 불러오기)
    try:
        last = path_manager.load_last_path()
        if last:
            path_var.set(last)
    except Exception:
        pass

    return path_var
