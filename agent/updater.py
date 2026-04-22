"""Self-update via GitHub Releases.

Agent polls the /releases/latest endpoint, compares semver, downloads
the Windows exe, verifies a SHA256 from a companion .sha256 asset, and
restarts. On non-Windows (dev/CI) apply_update is a no-op that logs.
"""
from __future__ import annotations

import hashlib
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

try:
    import semver
except ImportError:  # pragma: no cover — optional in dev
    semver = None  # type: ignore[assignment]

from agent import __version__
from agent.config import AppConfig
from agent.instance_lock import release_registered_lock


logger = logging.getLogger(__name__)

REPO = "sentania-labs/manalog"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET_EXE = "Manalog.exe"
ASSET_SHA = "Manalog.exe.sha256"


def _strip_v(tag: str) -> str:
    return tag.lstrip("vV")


def current_version() -> str:
    return _strip_v(__version__ or "") or "0.0.0"


def _is_newer(latest: str, current: str) -> bool:
    if semver is not None:
        try:
            return semver.VersionInfo.parse(latest).compare(current) > 0
        except ValueError:
            pass
    # Naive fallback: lexicographic segment compare.
    latest_parts = [int(p) for p in latest.split(".") if p.isdigit()]
    current_parts = [int(p) for p in current.split(".") if p.isdigit()]
    return latest_parts > current_parts


def _auth_headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def check_for_update(config: AppConfig) -> tuple[str, str] | None:
    token = config.updates.github_token or None
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(API_LATEST, headers=_auth_headers(token))
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Failed to query GitHub Releases")
            return None
        release = resp.json()

    tag = release.get("tag_name", "")
    if not tag:
        return None
    if release.get("prerelease") and not config.updates.include_prereleases:
        return None

    latest = _strip_v(tag)
    if not _is_newer(latest, current_version()):
        return None

    download_url: str | None = None
    for asset in release.get("assets", []):
        if asset.get("name") == ASSET_EXE:
            download_url = asset.get("browser_download_url")
            break
    if not download_url:
        logger.warning("Release %s has no %s asset", tag, ASSET_EXE)
        return None

    return tag, download_url


def _expected_sha_url(exe_url: str) -> str:
    return exe_url.rsplit("/", 1)[0] + "/" + ASSET_SHA


async def download_and_verify(url: str, token: str | None) -> Path | None:
    dest = Path(tempfile.gettempdir()) / "Manalog_update.exe"
    headers = _auth_headers(token)

    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        try:
            exe_resp = await client.get(url, headers=headers)
            exe_resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Download failed: %s", url)
            return None
        dest.write_bytes(exe_resp.content)

        try:
            sha_resp = await client.get(_expected_sha_url(url), headers=headers)
            sha_resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Could not fetch checksum for %s", url)
            return None

    expected = sha_resp.text.strip().split()[0].lower()
    actual = hashlib.sha256(dest.read_bytes()).hexdigest().lower()
    if actual != expected:
        logger.error("Checksum mismatch: expected %s got %s", expected, actual)
        try:
            dest.unlink()
        except OSError:
            pass
        return None

    return dest


def apply_update(new_exe: Path) -> None:
    if sys.platform != "win32":
        logger.info("Would restart with %s (non-Windows, skipping)", new_exe)
        return
    # Release the instance lock before launching the replacement, otherwise
    # the new process sees the still-live parent PID in the lock file and
    # bails. The parent's cleanup handlers run after SystemExit propagates,
    # which is too late.
    release_registered_lock()
    subprocess.Popen([str(new_exe)], close_fds=True)  # noqa: S603 — trusted path
    raise SystemExit(0)


__all__ = [
    "REPO",
    "apply_update",
    "check_for_update",
    "current_version",
    "download_and_verify",
]
