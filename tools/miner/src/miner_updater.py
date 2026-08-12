"""Small out-of-process updater used by packaged Dead Signal Miner builds."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


EXPECTED_EXECUTABLE = "Dead Signal Miner.exe"
MAX_UPDATE_BYTES = 250 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wait_for_process(pid: int, timeout_seconds: int = 120) -> None:
    if os.name != "nt":
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                return
            time.sleep(0.25)
        raise TimeoutError("The running Miner did not close in time")
    synchronize = 0x00100000
    handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
    if not handle:
        return
    try:
        result = ctypes.windll.kernel32.WaitForSingleObject(handle, timeout_seconds * 1000)
        if result == 0x00000102:
            raise TimeoutError("The running Miner did not close in time")
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    result = []
    extracted_size = 0
    for member in archive.infolist():
        path = PurePosixPath(member.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or any(":" in part for part in path.parts):
            raise ValueError(f"Unsafe archive path: {member.filename}")
        unix_mode = (member.external_attr >> 16) & 0o170000
        if unix_mode == 0o120000:
            raise ValueError(f"Symbolic links are not allowed in updates: {member.filename}")
        extracted_size += member.file_size
        if extracted_size > MAX_EXTRACTED_BYTES:
            raise ValueError("Update package expands beyond the allowed size")
        result.append(member)
    return result


def locate_payload_root(staging: Path) -> Path:
    direct = staging / EXPECTED_EXECUTABLE
    if direct.is_file():
        return staging
    candidates = [path.parent for path in staging.rglob(EXPECTED_EXECUTABLE)]
    if len(candidates) != 1:
        raise ValueError("Update package must contain exactly one Dead Signal Miner executable")
    return candidates[0]


def validate_target(target: Path) -> Path:
    target = target.resolve()
    if target == Path(target.anchor) or len(target.parts) < 3:
        raise ValueError(f"Unsafe installation target: {target}")
    if not (target / EXPECTED_EXECUTABLE).is_file():
        raise ValueError(f"Target is not a Dead Signal Miner installation: {target}")
    return target


def apply_update(package: Path, target: Path, expected_sha256: str) -> int:
    package = package.resolve()
    target = validate_target(target)
    if not package.is_file() or package.stat().st_size > MAX_UPDATE_BYTES:
        raise ValueError("Update package is missing or too large")
    actual_sha256 = sha256_file(package)
    if actual_sha256.casefold() != expected_sha256.casefold():
        raise ValueError("Update package SHA-256 verification failed")

    with tempfile.TemporaryDirectory(prefix="DeadSignalMinerApply-") as temporary:
        temporary = Path(temporary)
        staging = temporary / "staging"
        backup = temporary / "backup"
        staging.mkdir()
        backup.mkdir()
        with zipfile.ZipFile(package) as archive:
            members = safe_members(archive)
            archive.extractall(staging, members)
        payload = locate_payload_root(staging)

        copied = []
        try:
            for source in sorted(payload.rglob("*")):
                if not source.is_file():
                    continue
                relative = source.relative_to(payload)
                destination = target / relative
                if destination.exists():
                    backup_file = backup / relative
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup_file)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                copied.append(relative)
        except Exception:
            for relative in reversed(copied):
                backup_file = backup / relative
                destination = target / relative
                if backup_file.exists():
                    shutil.copy2(backup_file, destination)
                else:
                    destination.unlink(missing_ok=True)
            raise
    return len(copied)


def status_path() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return local / "DeadSignalMiner" / "update-status.json"


def write_status(status: str, **details) -> None:
    path = status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"generated_utc": datetime.now(timezone.utc).isoformat(), "status": status, **details},
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--relaunch", type=Path, required=True)
    args = parser.parse_args()
    try:
        wait_for_process(args.parent_pid)
        copied = apply_update(args.package, args.target, args.expected_sha256)
        write_status("complete", files_copied=copied, target=str(args.target))
        subprocess.Popen([str(args.relaunch.resolve())], close_fds=True)
        return 0
    except Exception as error:
        write_status("failed", error=f"{type(error).__name__}: {error}", target=str(args.target))
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(0, str(error), "Dead Signal Miner Update Failed", 0x10)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
