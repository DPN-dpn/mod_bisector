"""User settings backup/load helpers separated from path_manager.

These functions present file dialogs to the user and copy files to/from
the application's `config.ini`. They are UI-facing but kept separate
so `path_manager` remains focused on path logic.
"""
from typing import Optional


def backup_settings(parent: Optional[object] = None) -> None:
    """백업 기능은 아직 구현되지 않았습니다 (플레이스홀더).

    실제 백업 동작은 향후 구현될 예정이며, 현재는 호출해도 아무 동작을 하지 않습니다.
    """
    return


def load_settings(parent: Optional[object] = None) -> None:
    """불러오기 기능은 아직 구현되지 않았습니다 (플레이스홀더).

    실제 불러오기 동작은 향후 구현될 예정이며, 현재는 호출해도 아무 동작을 하지 않습니다.
    """
    return
