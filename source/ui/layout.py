import tkinter as tk
from tkinter import ttk
from app import path_manager, user_settings_backup


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

    browse_btn = ttk.Button(
        top,
        text="찾아보기...",
        command=lambda: (path_var.set(p) if (p := path_manager.browse_directory(root)) else None),
    )
    browse_btn.pack(side="left")

    # 본문 자리 (추후 컴포넌트 추가)
    content = ttk.Frame(root, padding=12)
    content.pack(fill="both", expand=True)

    # 설정 백업/불러오기 버튼 그룹
    backup_frame = ttk.LabelFrame(content, text="설정 백업/불러오기", padding=(8, 8))
    backup_frame.pack(fill="x", pady=0)

    btn_backup = ttk.Button(backup_frame, text="백업", command=user_settings_backup.backup_settings)
    btn_load = ttk.Button(backup_frame, text="불러오기", command=user_settings_backup.load_settings)

    btn_backup.pack(side="left", padx=(0, 8))
    btn_load.pack(side="left")

    # 초기값 설정 (저장된 경로가 있으면 불러오기)
    try:
        last = path_manager.load_last_path()
        if last:
            path_var.set(last)
    except Exception:
        pass

    return path_var

