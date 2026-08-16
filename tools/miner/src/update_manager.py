"""Hash-verified update discovery and download for Dead Signal Miner."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


DEFAULT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/raiinman/dead-signal/main/"
    "tools/miner/release/latest.json"
)
ALLOWED_UPDATE_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "raw.githubusercontent.com",
}
MAX_UPDATE_BYTES = 250 * 1024 * 1024


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    update_available: bool
    download_url: str | None
    sha256: str | None
    size: int | None
    notes_url: str | None
    channel: str

    @property
    def installable(self) -> bool:
        return bool(self.update_available and self.download_url and self.sha256 and self.size)


def version_key(value: str) -> tuple[int, ...]:
    text = str(value).strip().lstrip("vV")
    parts = text.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise UpdateError(f"Unsupported version: {value!r}")
    return tuple(int(part) for part in parts)


def _validated_https_url(value: object, *, optional: bool = False) -> str | None:
    if value in (None, "") and optional:
        return None
    if not isinstance(value, str):
        raise UpdateError("Update URL must be a string")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_UPDATE_HOSTS:
        raise UpdateError(f"Update URL is not an allowed GitHub HTTPS URL: {value}")
    return value


def _cache_busted_manifest_url(url: str) -> str:
    """Return the manifest URL with a unique harmless query parameter.

    GitHub/raw edge caches can briefly serve an older latest.json immediately
    after a release. A per-check query parameter plus no-cache headers keeps the
    packaged updater from getting stranded on the previous manifest.
    """
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("dead_signal_check", str(time.time_ns())))
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
    )


def parse_manifest(payload: object, current_version: str) -> UpdateInfo:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise UpdateError("Unsupported update manifest schema")
    latest = str(payload.get("version") or "").strip()
    current_key = version_key(current_version)
    latest_key = version_key(latest)
    update_available = latest_key > current_key
    download_url = _validated_https_url(payload.get("download_url"), optional=True)
    notes_url = _validated_https_url(payload.get("notes_url"), optional=True)
    sha256 = payload.get("sha256")
    size = payload.get("size")
    if sha256 is not None:
        sha256 = str(sha256).casefold()
        if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
            raise UpdateError("Update SHA-256 is invalid")
    if size is not None:
        try:
            size = int(size)
        except (TypeError, ValueError) as error:
            raise UpdateError("Update size is invalid") from error
        if size <= 0 or size > MAX_UPDATE_BYTES:
            raise UpdateError("Update size is outside the allowed range")
    return UpdateInfo(
        current_version=current_version,
        latest_version=latest,
        update_available=update_available,
        download_url=download_url,
        sha256=sha256,
        size=size,
        notes_url=notes_url,
        channel=str(payload.get("channel") or "stable"),
    )


def check_for_updates(
    current_version: str,
    manifest_url: str = DEFAULT_MANIFEST_URL,
    timeout: float = 12.0,
) -> UpdateInfo:
    validated_url = _validated_https_url(manifest_url)
    assert validated_url is not None
    url = _cache_busted_manifest_url(validated_url)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache",
            "User-Agent": f"Dead-Signal-Miner/{current_version}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise UpdateError(f"Update server returned HTTP {response.status}")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > 128 * 1024:
                raise UpdateError("Update manifest is unexpectedly large")
            raw = response.read(128 * 1024 + 1)
    except (OSError, ValueError) as error:
        raise UpdateError(f"Could not check for updates: {error}") from error
    if len(raw) > 128 * 1024:
        raise UpdateError("Update manifest is unexpectedly large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateError("Update manifest is not valid UTF-8 JSON") from error
    return parse_manifest(payload, current_version)


def download_update(
    info: UpdateInfo,
    destination_directory: Path,
    progress: Callable[[int, int], None] | None = None,
    timeout: float = 30.0,
) -> Path:
    if not info.installable:
        raise UpdateError("This update does not have a verified downloadable package")
    assert info.download_url and info.sha256 and info.size
    url = _validated_https_url(info.download_url)
    destination_directory = destination_directory.expanduser().resolve()
    destination_directory.mkdir(parents=True, exist_ok=True)
    destination = destination_directory / f"Dead-Signal-Miner-v{info.latest_version}-Windows.zip"
    partial = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    received = 0
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/octet-stream", "User-Agent": f"Dead-Signal-Miner/{info.current_version}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, partial.open("wb") as output:
            if response.status != 200:
                raise UpdateError(f"Update download returned HTTP {response.status}")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                received += len(block)
                if received > info.size or received > MAX_UPDATE_BYTES:
                    raise UpdateError("Update download exceeded its declared size")
                digest.update(block)
                output.write(block)
                if progress:
                    progress(received, info.size)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    if received != info.size:
        partial.unlink(missing_ok=True)
        raise UpdateError(f"Update size mismatch: expected {info.size}, received {received}")
    if digest.hexdigest().casefold() != info.sha256:
        partial.unlink(missing_ok=True)
        raise UpdateError("Update SHA-256 verification failed")
    partial.replace(destination)
    return destination


def launch_updater(package: Path, expected_sha256: str) -> None:
    if not getattr(sys, "frozen", False):
        raise UpdateError("Self-update installation is available only in the packaged Windows app")
    install_directory = Path(sys.executable).resolve().parent
    bundled_helper = install_directory / "Dead Signal Miner Updater.exe"
    if not bundled_helper.is_file():
        raise UpdateError("The updater helper is missing from this installation")
    temporary_directory = Path(tempfile.mkdtemp(prefix="DeadSignalMinerUpdater-"))
    temporary_helper = temporary_directory / bundled_helper.name
    shutil.copy2(bundled_helper, temporary_helper)
    arguments = [
        str(temporary_helper),
        "--package", str(package.resolve()),
        "--target", str(install_directory),
        "--expected-sha256", expected_sha256,
        "--parent-pid", str(os.getpid()),
        "--relaunch", str(install_directory / "Dead Signal Miner.exe"),
    ]
    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(arguments, close_fds=True, creationflags=creation_flags)
