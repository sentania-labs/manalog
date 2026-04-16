"""Agent config — load/save to a platform-appropriate location.

On Windows: %APPDATA%\\MTGOMatchTracker\\config.toml
On other platforms (dev/CI): ~/.config/mtgo-match-tracker/config.toml

Writes are atomic (.tmp then rename). Never store user passwords — only
the api_token issued by the server at registration time.
"""
from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path


CONFIG_FILENAME = "config.toml"
APP_DIR_NAME_WIN = "MTGOMatchTracker"
APP_DIR_NAME_POSIX = "mtgo-match-tracker"


@dataclass
class ServerConfig:
    url: str = "https://mtgo.int.sentania.net"
    tls_verify: bool | str = True


@dataclass
class AgentConfig:
    agent_id: str = ""
    api_token: str = ""
    machine_name: str = ""


@dataclass
class MtgoConfig:
    log_dir: str = ""


@dataclass
class UpdatesConfig:
    check_interval_hours: int = 1
    include_prereleases: bool = False
    github_token: str = ""


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    mtgo: MtgoConfig = field(default_factory=MtgoConfig)
    updates: UpdatesConfig = field(default_factory=UpdatesConfig)


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME_WIN
        return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME_WIN
    override = os.environ.get("MTGO_AGENT_CONFIG_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / APP_DIR_NAME_POSIX


def get_config_path() -> Path:
    return _config_dir() / CONFIG_FILENAME


def get_log_dir() -> Path:
    cfg = load_config()
    if cfg.mtgo.log_dir:
        return Path(cfg.mtgo.log_dir)
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", "")) / "Apps" / "2.0"
    return _config_dir() / "mtgo-logs"


def _parse_toml(path: Path) -> AppConfig:
    with path.open("rb") as fh:
        data = tomllib.load(fh)

    server_raw = data.get("server", {}) or {}
    tls_verify_raw = server_raw.get("tls_verify", True)
    if isinstance(tls_verify_raw, str) and tls_verify_raw.lower() in {"true", "false"}:
        tls_verify: bool | str = tls_verify_raw.lower() == "true"
    else:
        tls_verify = tls_verify_raw

    agent_raw = data.get("agent", {}) or {}
    mtgo_raw = data.get("mtgo", {}) or {}
    updates_raw = data.get("updates", {}) or {}

    return AppConfig(
        server=ServerConfig(
            url=server_raw.get("url", ServerConfig.url),
            tls_verify=tls_verify,
        ),
        agent=AgentConfig(
            agent_id=agent_raw.get("agent_id", ""),
            api_token=agent_raw.get("api_token", ""),
            machine_name=agent_raw.get("machine_name", ""),
        ),
        mtgo=MtgoConfig(log_dir=mtgo_raw.get("log_dir", "")),
        updates=UpdatesConfig(
            check_interval_hours=int(updates_raw.get("check_interval_hours", 1)),
            include_prereleases=bool(updates_raw.get("include_prereleases", False)),
            github_token=updates_raw.get("github_token", ""),
        ),
    )


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or get_config_path()
    if not cfg_path.exists():
        return AppConfig()
    return _parse_toml(cfg_path)


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _serialize(config: AppConfig) -> str:
    tls_verify = config.server.tls_verify
    if isinstance(tls_verify, bool):
        tls_verify_str = "true" if tls_verify else "false"
    else:
        tls_verify_str = f'"{_toml_escape(str(tls_verify))}"'

    lines = [
        "[server]",
        f'url = "{_toml_escape(config.server.url)}"',
        f"tls_verify = {tls_verify_str}",
        "",
        "[agent]",
        f'agent_id = "{_toml_escape(config.agent.agent_id)}"',
        f'api_token = "{_toml_escape(config.agent.api_token)}"',
        f'machine_name = "{_toml_escape(config.agent.machine_name)}"',
        "",
        "[mtgo]",
        f'log_dir = "{_toml_escape(config.mtgo.log_dir)}"',
        "",
        "[updates]",
        f"check_interval_hours = {int(config.updates.check_interval_hours)}",
        f"include_prereleases = {'true' if config.updates.include_prereleases else 'false'}",
        f'github_token = "{_toml_escape(config.updates.github_token)}"',
        "",
    ]
    return "\n".join(lines)


def save_config(config: AppConfig, path: Path | None = None) -> None:
    cfg_path = path or get_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cfg_path.with_suffix(cfg_path.suffix + ".tmp")
    tmp_path.write_text(_serialize(config), encoding="utf-8")
    os.replace(tmp_path, cfg_path)


def config_as_dict(config: AppConfig) -> dict:
    return asdict(config)
