"""Single-instance guard.

Both the tray app and the Windows Service can run simultaneously on a
user session; without a guard they double-submit log files. The lock
file carries the holder's PID — on acquire, a stale PID (no process
under it) is treated as vacant and taken over.

Linux parity uses ~/.local/share/manalog so dev runs on a Linux box can
exercise the same code path.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


LOCK_FILENAME = "instance.lock"
APP_DIR_NAME_WIN = "Manalog"
APP_DIR_NAME_POSIX = "manalog"


logger = logging.getLogger(__name__)


def _lock_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_DIR_NAME_WIN
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME_WIN
    override = os.environ.get("MANALOG_LOCK_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / APP_DIR_NAME_POSIX


def get_lock_path() -> Path:
    return _lock_dir() / LOCK_FILENAME


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class InstanceLock:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_lock_path()
        self._acquired = False

    @property
    def path(self) -> Path:
        return self._path

    def acquire(self) -> bool:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Try atomic create-exclusive twice: first attempt wins outright, or
        # collides with an existing holder. On collision, inspect the PID; if
        # stale, unlink and retry once under O_EXCL so two racers cannot both
        # take over a stale lock. A live holder ends the attempt.
        for attempt in range(2):
            try:
                fd = os.open(
                    str(self._path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
            except FileExistsError:
                try:
                    existing = self._path.read_text(encoding="utf-8").strip()
                    existing_pid = int(existing) if existing else 0
                except (OSError, ValueError):
                    existing_pid = 0

                if existing_pid and _pid_running(existing_pid):
                    logger.info(
                        "Instance lock held by PID %d (%s); not acquiring",
                        existing_pid,
                        self._path,
                    )
                    return False

                if attempt == 0:
                    logger.info(
                        "Stale instance lock at %s (PID %d not running) — taking over",
                        self._path,
                        existing_pid,
                    )
                    try:
                        self._path.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError:
                        logger.exception(
                            "Failed to clear stale lock at %s", self._path
                        )
                        return False
                    continue
                # Second collision: another racer grabbed the stale slot first.
                logger.info(
                    "Instance lock at %s taken over by another process mid-acquire; not acquiring",
                    self._path,
                )
                return False
            except OSError:
                logger.exception("Failed to create instance lock at %s", self._path)
                return False

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(str(os.getpid()))
            except OSError:
                logger.exception("Failed to write PID to instance lock at %s", self._path)
                try:
                    self._path.unlink()
                except OSError:
                    pass
                return False
            self._acquired = True
            return True

        return False

    def release(self) -> None:
        if not self._acquired:
            return
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception("Failed to remove instance lock at %s", self._path)
        self._acquired = False

    def __enter__(self) -> "InstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
