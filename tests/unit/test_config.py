"""Agent config load/save round-trip tests.

Uses tmp_path to keep all reads/writes out of the real user config dir.
"""
from __future__ import annotations

from pathlib import Path

from agent.config import (
    AgentConfig,
    AppConfig,
    MtgoConfig,
    ServerConfig,
    UpdatesConfig,
    load_config,
    save_config,
)


def test_load_config_defaults(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.toml"
    cfg = load_config(missing)
    assert isinstance(cfg, AppConfig)
    assert cfg.server.url == "https://mtgo.int.sentania.net"
    assert cfg.server.tls_verify is True
    assert cfg.agent.agent_id == ""
    assert cfg.agent.api_token == ""
    assert cfg.mtgo.log_dir == ""
    assert cfg.updates.check_interval_hours == 1
    assert cfg.updates.include_prereleases is False


def test_save_and_reload(tmp_path: Path) -> None:
    cfg = AppConfig(
        server=ServerConfig(url="https://example.test", tls_verify=False),
        agent=AgentConfig(
            agent_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            api_token="secret-token",
            machine_name="laptop-01",
        ),
        mtgo=MtgoConfig(log_dir=r"C:\Users\scott\mtgo-logs"),
        updates=UpdatesConfig(
            check_interval_hours=6,
            include_prereleases=True,
            github_token="ghp_fake",
        ),
    )
    path = tmp_path / "config.toml"
    save_config(cfg, path)
    assert path.exists()

    reloaded = load_config(path)
    assert reloaded.server.url == cfg.server.url
    assert reloaded.server.tls_verify is False
    assert reloaded.agent.agent_id == cfg.agent.agent_id
    assert reloaded.agent.api_token == cfg.agent.api_token
    assert reloaded.agent.machine_name == cfg.agent.machine_name
    assert reloaded.mtgo.log_dir == cfg.mtgo.log_dir
    assert reloaded.updates.check_interval_hours == 6
    assert reloaded.updates.include_prereleases is True
    assert reloaded.updates.github_token == "ghp_fake"


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "deeper" / "config.toml"
    save_config(AppConfig(), nested)
    assert nested.exists()


def test_tls_verify_as_path_string(tmp_path: Path) -> None:
    cfg = AppConfig(server=ServerConfig(tls_verify="/etc/ssl/internal-ca.pem"))
    path = tmp_path / "config.toml"
    save_config(cfg, path)
    reloaded = load_config(path)
    assert reloaded.server.tls_verify == "/etc/ssl/internal-ca.pem"
