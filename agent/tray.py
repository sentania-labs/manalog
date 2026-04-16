"""Tray application — pystray icon + menu + thread orchestration.

The tray event loop is blocking; the watcher runs in a thread and the
updater runs on a periodic schedule. All module imports are guarded so
the module stays importable on Linux CI even when pystray/PIL aren't
available or can't spawn a tray backend.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any

from agent.config import AppConfig, get_config_path
from agent.parser import ParsedMatch
from agent.sender import AgentSender
from agent.updater import (
    apply_update,
    check_for_update,
    download_and_verify,
)
from agent.watcher import MTGOWatcher

try:
    import pystray  # type: ignore[import-untyped]
    from PIL import Image  # type: ignore[import-untyped]
    _TRAY_AVAILABLE = True
except Exception:  # pragma: no cover — pystray picks a display backend at
    # import time on Linux; headless CI raises a display-connection error,
    # not ImportError. Swallow anything so the module stays importable.
    pystray = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    _TRAY_AVAILABLE = False


logger = logging.getLogger(__name__)


def _make_default_icon() -> Any:
    if Image is None:
        return None
    img = Image.new("RGB", (64, 64), color=(30, 80, 200))
    return img


def _load_icon(assets_dir: Path) -> Any:
    if Image is None:
        return None
    ico = assets_dir / "icon.ico"
    if ico.exists():
        try:
            return Image.open(ico)
        except Exception:
            logger.exception("Failed to load %s, using generated icon", ico)
    return _make_default_icon()


class TrayApp:
    def __init__(
        self,
        config: AppConfig,
        sender: AgentSender,
        log_file: Path | None = None,
    ) -> None:
        self._config = config
        self._sender = sender
        self._log_file = log_file
        self._paused = False
        self._stop = threading.Event()
        self._watcher: MTGOWatcher | None = None
        self._icon: Any = None
        self._update_thread: threading.Thread | None = None

    # ---- lifecycle -----------------------------------------------------

    def run(self) -> None:
        if not _TRAY_AVAILABLE:
            logger.warning("pystray/PIL unavailable — tray not started")
            return

        assets_dir = Path(__file__).parent / "assets"
        icon_image = _load_icon(assets_dir)
        menu = self._build_menu()
        self._icon = pystray.Icon("mtgo-match-tracker", icon_image, "MTGO Match Tracker", menu)

        self._start_watcher()
        self._start_update_loop()
        self._icon.run()

    # ---- watcher -------------------------------------------------------

    def _start_watcher(self) -> None:
        log_dir = Path(self._config.mtgo.log_dir) if self._config.mtgo.log_dir else None
        if log_dir is None:
            logger.info("No MTGO log_dir configured — watcher idle")
            return
        self._watcher = MTGOWatcher(log_dir, self._on_match)
        self._watcher.start()

    def _stop_watcher(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

    def _on_match(self, match: ParsedMatch) -> None:
        if self._paused:
            return
        try:
            asyncio.run(self._sender.upload(match))
        except Exception:
            logger.exception("Failed to upload match %s", match.mtgo_match_id)

    # ---- update loop ---------------------------------------------------

    def _start_update_loop(self) -> None:
        interval_hours = max(1, int(self._config.updates.check_interval_hours))
        interval_seconds = interval_hours * 3600

        def _loop() -> None:
            while not self._stop.is_set():
                self._check_updates_once()
                if self._stop.wait(interval_seconds):
                    return

        thread = threading.Thread(target=_loop, name="mtgo-updater", daemon=True)
        thread.start()
        self._update_thread = thread

    def _check_updates_once(self) -> None:
        try:
            result = asyncio.run(check_for_update(self._config))
        except Exception:
            logger.exception("Update check failed")
            return
        if result is None:
            return
        tag, url = result
        token = self._config.updates.github_token or None
        try:
            new_exe = asyncio.run(download_and_verify(url, token))
        except Exception:
            logger.exception("Update download failed")
            return
        if new_exe is None:
            return
        self._notify(f"Update {tag} ready — restart to apply")
        # Fire-and-forget; user confirmation handled via tray menu in real flow.
        try:
            apply_update(new_exe)
        except SystemExit:
            raise

    # ---- menu handlers -------------------------------------------------

    def _build_menu(self) -> Any:
        if not _TRAY_AVAILABLE:
            return None
        MenuItem = pystray.MenuItem  # noqa: N806
        Menu = pystray.Menu  # noqa: N806
        return Menu(
            MenuItem(lambda item: self._status_text(), None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(
                lambda item: "Resume Monitoring" if self._paused else "Pause Monitoring",
                self._on_pause_resume,
            ),
            MenuItem("Open Dashboard", self._on_open_dashboard),
            Menu.SEPARATOR,
            MenuItem("Check for Updates", self._on_check_updates),
            MenuItem("Settings…", self._on_settings),
            MenuItem("Open Log", self._on_open_log),
            Menu.SEPARATOR,
            MenuItem("Quit", self._on_quit),
        )

    def _status_text(self) -> str:
        if not self._config.agent.agent_id:
            return "Status: Not registered"
        if self._paused:
            return "Status: Paused"
        return "Status: Monitoring"

    def _on_pause_resume(self, icon: Any, item: Any) -> None:
        self._paused = not self._paused
        logger.info("Monitoring %s", "paused" if self._paused else "resumed")

    def _on_open_dashboard(self, icon: Any, item: Any) -> None:
        webbrowser.open(self._config.server.url)

    def _on_check_updates(self, icon: Any, item: Any) -> None:
        threading.Thread(target=self._check_updates_once, daemon=True).start()

    def _on_settings(self, icon: Any, item: Any) -> None:
        self._open_in_editor(get_config_path())

    def _on_open_log(self, icon: Any, item: Any) -> None:
        if self._log_file is None:
            return
        self._open_in_editor(self._log_file)

    def _on_quit(self, icon: Any, item: Any) -> None:
        self._stop.set()
        self._stop_watcher()
        try:
            asyncio.run(self._sender.close())
        except Exception:
            logger.exception("Error closing sender")
        if self._icon is not None:
            self._icon.stop()
        sys.exit(0)

    # ---- helpers -------------------------------------------------------

    def _open_in_editor(self, path: Path) -> None:
        if not path.exists():
            logger.warning("Path does not exist: %s", path)
            return
        if sys.platform == "win32":
            import os as _os
            _os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])  # noqa: S603,S607
        else:
            subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607

    def _notify(self, message: str) -> None:
        logger.info("TRAY: %s", message)
        if self._icon is not None and hasattr(self._icon, "notify"):
            try:
                self._icon.notify(message, "MTGO Match Tracker")
            except Exception:
                logger.exception("Failed to show tray notification")
