from lib.run import run

from sys import stderr
from typing import Optional


def log(*args: object, end: Optional[str] = None):
    print(*args, flush=True, file=stderr, end=end)


def get_pid(app_id: str) -> Optional[int]:
    code, pid = run("adb shell pidof", app_id, capture=True, fail_ok=True)
    if code == 0 and pid:
        try:
            return int(pid)
        except:
            pass
    return None


def kill_app(app_id: str) -> None:
    run("adb shell am force-stop", app_id)


def start_unity_app(app_id: str) -> None:
    activities = run(
        "adb shell cmd package resolve-activity --brief", app_id, capture=True
    ).splitlines()
    activity = next(
        (activity for activity in activities if "UnityPlayer" in activity),
        f"{app_id}/com.unity3d.player.UnityPlayerActivity",
    )
    run("adb shell am start", activity)


__all__ = ["log", "get_pid", "kill_app", "start_unity_app"]
