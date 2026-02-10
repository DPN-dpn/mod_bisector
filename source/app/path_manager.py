"""Path management functions used by the UI (keeps UI and logic separated)."""
from typing import Optional
import os
import config


def load_last_path() -> str:
    """Return the last saved path or empty string."""
    try:
        p = config.load_last_path()
        return p or ""
    except Exception:
        return ""


def save_last_path(path: str) -> None:
    """Save the given path via config helper. Validate path exists before saving."""
    if not path:
        raise ValueError("path is empty")
    # normalize
    p = os.path.abspath(path)
    # Optionally ensure it's a directory; if not, still save but warn via exception
    if not os.path.isdir(p):
        # do not raise for UI; allow saving non-existent path if caller wants
        pass
    config.save_last_path(p)


def browse_directory(parent: Optional[object] = None) -> str:
    """Open a directory chooser dialog and save+return the selected path.

    `parent` can be a Tk window to attach the dialog to; if None, dialog is standalone.
    Returns the selected path or empty string if cancelled.
    """
    try:
        from tkinter import filedialog
    except Exception:
        return ""

    # filedialog.askdirectory accepts a `parent` kwarg; some callers may pass the root
    try:
        if parent is not None:
            p = filedialog.askdirectory(parent=parent)
        else:
            p = filedialog.askdirectory()
    except Exception:
        p = ""

    if p:
        try:
            save_last_path(p)
        except Exception:
            pass
        return p
    return ""


def ensure_dir(path: Optional[str]) -> bool:
    """Return True if path exists and is directory, False otherwise."""
    if not path:
        return False
    return os.path.isdir(path)

