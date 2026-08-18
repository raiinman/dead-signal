"""Local, read-only Once Human mining pipeline used by Dead Signal Miner.

The pipeline reads installed NXPK archives, parses data-only bindict payloads from
compiled Python files without executing their bytecode, normalizes supported site
categories, and extracts the display artwork referenced by every covered domain.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Callable, Iterable


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]


def resource_root() -> Path:
    """Return the app resource directory in source and PyInstaller builds."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else Path(__file__).resolve().parent


ROOT = resource_root()
EXTRACTOR_ROOT = ROOT / "extractor"
NEOXTRACTOR_ROOT = ROOT / "neoxtractor"
VENDOR_ROOT = ROOT / "vendor"


def read_app_version() -> str:
    """Read one canonical version in source and packaged layouts."""
    candidates = [ROOT / "VERSION"]
    if not getattr(sys, "frozen", False):
        candidates.append(Path(__file__).resolve().parents[1] / "VERSION")
    for candidate in candidates:
        try:
            value = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    return "0.0.0-dev"


APP_VERSION = read_app_version()

for import_root in (VENDOR_ROOT, EXTRACTOR_ROOT, NEOXTRACTOR_ROOT):
    if import_root.exists() and str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


# These are the current Dead Signal inputs. Full mode ignores this list and
# exports every script table in both layers.
SITE_TABLES = (
    "buff_level_data",
    "bullet_pattern_data",
    "bullet_scatter_data",
    "char_property_data",
    "equip_blueprint_attr_data",
    "equip_blueprint_data",
    "equip_data",
    "equip_origin_data",
    "forge_choice_material_data",
    "forge_data",
    "gun_base_params_data",
    "gun_blueprint_attr_data",
    "gun_blueprint_data",
    "gun_stability_data",
    "item_data",
    "money_material_data",
    "passive_skill_data",
    "suit_data",
    "weapon_prototype_data",
)

BASE_REQUIRED = (
    "suit_data",
    "equip_blueprint_data",
    "equip_blueprint_attr_data",
    "passive_skill_data",
    "forge_data",
    "money_material_data",
    "gun_blueprint_data",
    "gun_blueprint_attr_data",
    "weapon_prototype_data",
    "gun_stability_data",
    "bullet_scatter_data",
    "gun_base_params_data",
)

CURRENT_REQUIRED = (
    "char_property_data",
    "item_data",
    "equip_data",
    "equip_origin_data",
    "buff_level_data",
)


# This is the durable scope contract for game-derived DeadSignalDB content.
# Patterns identify candidate source tables; individual category normalizers
# still decide exact record semantics and base/patch merge behavior.
DEAD_SIGNAL_COVERAGE = {
    "tech": {
        "label": "Tech",
        "source_type": "game",
        "patterns": ("tech", "memetic", "specialization", "invention", "reverse_engineer"),
        "covers": "branches, nodes, unlock costs, prerequisites, effects, and scenario variants",
    },
    "weapons": {
        "label": "Weapons and accessories",
        "source_type": "game",
        "patterns": ("weapon", "gun_", "bullet_", "accessor", "calibration"),
        "covers": "weapons, blueprints, tiers, stats, effects, ammunition, accessories, and recipes",
    },
    "armor": {
        "label": "Armor",
        "source_type": "game",
        "patterns": ("armor", "equip_", "suit_"),
        "covers": "individual pieces, sets, Key Armor, tiers, stats, effects, and recipes",
    },
    "deviants": {
        "label": "Deviants",
        "source_type": "game",
        "patterns": ("deviation", "deviant", "anomaly", "secure_unit"),
        "covers": "identities, abilities, traits, mood, power, containment, and acquisition relationships",
    },
    "enemies_bosses": {
        "label": "Enemies and bosses",
        "source_type": "game",
        "patterns": ("monster", "boss", "enemy", "creature", "npc_combat", "unit_property"),
        "covers": "enemy identities, levels, combat properties, abilities, encounters, and drop links",
    },
    "items_materials": {
        "label": "Items, materials, and currencies",
        "source_type": "game",
        "patterns": ("item_", "material", "currency", "money_", "resource_item"),
        "covers": "all player items, qualities, descriptions, stacks, categories, effects, and currencies",
    },
    "crafting": {
        "label": "Crafting",
        "source_type": "game",
        "patterns": ("forge", "recipe", "formula", "craft", "workbench", "compose", "decompose"),
        "covers": "recipes, selectable inputs, quantities, costs, times, stations, and outputs",
    },
    "mods_build_components": {
        "label": "Mods and build components",
        "source_type": "game",
        "patterns": ("mod_", "affix", "cradle", "keyword", "passive_skill", "buff_", "combat_property"),
        "covers": "mods, affixes, calibrations, cradle effects, keywords, buffs, and combat relationships",
    },
    "maps_locations": {
        "label": "Maps and locations",
        "source_type": "game",
        "patterns": ("map_", "world_", "scene_", "region", "area_", "point_", "poi", "teleport", "location"),
        "covers": "worlds, regions, map markers, POIs, coordinates, teleporters, encounters, and resource links",
    },
    "seasons_events": {
        "label": "Seasons, scenarios, and events",
        "source_type": "game",
        "patterns": ("season", "scenario", "event_", "activity_", "battle_pass", "phase_", "reward"),
        "covers": "scenarios, phases, events, schedules encoded in the client, objectives, and rewards",
    },
    "quests_collections": {
        "label": "Quests, achievements, and collections",
        "source_type": "game",
        "patterns": ("quest", "mission", "task_", "achievement", "collect", "journey", "commission"),
        "covers": "quest definitions, objectives, prerequisites, rewards, achievements, and collectibles",
    },
    "vendors_drops": {
        "label": "Vendors, loot, and acquisition",
        "source_type": "game",
        "patterns": ("shop", "store_", "vendor", "drop", "loot", "award", "access_item", "gain_path"),
        "covers": "shops, costs, loot pools, reward pools, drop relationships, and acquisition hints",
    },
    "building": {
        "label": "Building and furniture",
        "source_type": "game",
        "patterns": ("build_", "building", "furniture", "territory", "facility", "blueprint_house"),
        "covers": "structures, furniture, facilities, territory rules, recipes, power, and production links",
    },
    "consumables": {
        "label": "Food and consumables",
        "source_type": "game",
        "patterns": ("food", "cuisine", "medicine", "drug_", "consum", "drink_"),
        "covers": "food, drinks, medicine, recipes, durations, buffs, and side effects",
    },
    "vehicles": {
        "label": "Vehicles and rides",
        "source_type": "game",
        "patterns": ("vehicle", "motor", "ride_", "mount_"),
        "covers": "vehicles, parts, stats, fuels, upgrades, and crafting relationships",
    },
    "community_builds": {
        "label": "Community builds",
        "source_type": "hybrid",
        "patterns": (),
        "covers": "game-derived equipment and effects plus player-authored loadouts and strategy",
    },
    "guides_news": {
        "label": "Guides and news",
        "source_type": "editorial",
        "patterns": (),
        "covers": "author-written articles supported by mined facts, official sources, and in-game evidence",
    },
    "verification": {
        "label": "In-game verification",
        "source_type": "manual",
        "patterns": (),
        "covers": "dated screenshots and video proving availability, wording, scenario restrictions, and acquisition",
    },
}


@dataclass(slots=True)
class MinerConfig:
    install: Path
    output: Path
    mode: str = "full"
    include_artwork: bool = True

    def normalized(self) -> "MinerConfig":
        return MinerConfig(
            install=self.install.expanduser().resolve(),
            output=self.output.expanduser().resolve(),
            # A packaged Dead Signal harvest is intentionally complete. The
            # former category-limited troubleshooting mode created the false
            # impression that those were the application's real boundaries.
            mode="full",
            include_artwork=True,
        )


class MiningCancelled(RuntimeError):
    """Raised when the user asks the pipeline to stop between safe phases."""


class CallbackWriter:
    """Turn stdout/stderr writes from existing extractors into log callbacks."""

    def __init__(self, callback: LogCallback):
        self.callback = callback
        self.pending = ""

    def write(self, value: str) -> int:
        self.pending += value
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            if line.strip():
                self.callback(line.rstrip())
        return len(value)

    def flush(self) -> None:
        if self.pending.strip():
            self.callback(self.pending.rstrip())
        self.pending = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(path)


def discover_installations() -> list[Path]:
    """Find Once Human in ordinary Steam library locations on Windows."""
    candidates: list[Path] = []
    steam_roots: list[Path] = []

    standard = Path(r"C:\Program Files (x86)\Steam")
    if standard.exists():
        steam_roots.append(standard)

    if os.name == "nt":
        try:
            import winreg  # pylint: disable=import-outside-toplevel

            for hive, key_name in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
            ):
                try:
                    with winreg.OpenKey(hive, key_name) as key:
                        value, _ = winreg.QueryValueEx(key, "SteamPath")
                    steam_roots.append(Path(value))
                except OSError:
                    continue
        except ImportError:
            pass

    library_roots: list[Path] = []
    for steam_root in steam_roots:
        library_roots.append(steam_root)
        library_file = steam_root / "steamapps" / "libraryfolders.vdf"
        if not library_file.exists():
            continue
        text = library_file.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            library_roots.append(Path(match.group(1).replace(r"\\", "\\")))

    seen: set[str] = set()
    for root in library_roots:
        install = root / "steamapps" / "common" / "Once Human"
        key = str(install).casefold()
        if key not in seen and validate_install(install, raise_error=False):
            seen.add(key)
            candidates.append(install.resolve())
    return candidates


def validate_install(install: Path, raise_error: bool = True) -> bool:
    required = (
        install / "script.npk",
        install / "Documents" / "script.npk",
        install / "ONCE_HUMAN.exe",
    )
    missing = [path for path in required if not path.is_file()]
    if missing and raise_error:
        names = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(
            "This does not look like a complete Once Human installation. "
            f"Missing:\n{names}"
        )
    return not missing


def site_match_expression() -> str:
    table_names = "|".join(re.escape(name) for name in SITE_TABLES)
    return (
        rf"^(?:game_common\\data\\(?:{table_names})\.pyc|"
        rf"translate\\translate_data_en(?:_v\d+)?\.pyc)$"
    )


def run_module_main(module_name: str, arguments: Iterable[object], log: LogCallback) -> int:
    """Run one of the proven CLI modules in-process with captured output."""
    module = importlib.import_module(module_name)
    old_argv = sys.argv[:]
    writer = CallbackWriter(log)
    sys.argv = [f"{module_name}.py", *(str(item) for item in arguments)]
    try:
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            result = module.main()
        writer.flush()
        if result not in (None, 0):
            raise RuntimeError(f"{module_name} stopped with exit code {result}")
        return int(result or 0)
    finally:
        writer.flush()
        sys.argv = old_argv


def required_dictionary(archive: Path, executable: Path, dictionary_dir: Path, log: LogCallback) -> Path | None:
    """Locate, validate, and cache the dictionary required by compression flag 10."""
    import zstandard  # type: ignore  # pylint: disable=import-outside-toplevel
    from find_zstd_dicts import scan_file  # pylint: disable=import-outside-toplevel
    from npk_extract import decode_entry, read_archive  # pylint: disable=import-outside-toplevel

    _, entries = read_archive(archive)
    sample = next(
        (entry for entry in entries if entry.encryption == 0 and entry.compression == 10),
        None,
    )
    if sample is None:
        return None

    with archive.open("rb") as source:
        source.seek(sample.offset)
        frame = source.read(sample.compressed_size)
    dict_id = int(zstandard.get_frame_parameters(frame).dict_id)
    dictionary_dir.mkdir(parents=True, exist_ok=True)
    cached = dictionary_dir / f"zstd-{dict_id}.dict"

    candidates = [cached, EXTRACTOR_ROOT / f"once-human-zstd-{dict_id}.dict"]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            dictionary = zstandard.ZstdCompressionDict(candidate.read_bytes())
            if dictionary.dict_id() != dict_id:
                continue
            with archive.open("rb") as source:
                decode_entry(source, sample, dictionary)
            if candidate != cached:
                shutil.copy2(candidate, cached)
            log(f"Validated Zstandard dictionary {dict_id} ({cached.stat().st_size:,} bytes).")
            return cached
        except (OSError, ValueError, zstandard.ZstdError):
            continue

    log(f"Searching ONCE_HUMAN.exe for Zstandard dictionary {dict_id}...")
    offsets = [offset for offset, found_id in scan_file(executable) if found_id == dict_id]
    if not offsets:
        raise RuntimeError(
            f"The base archive requires dictionary {dict_id}, but it was not found in "
            "ONCE_HUMAN.exe. The game format may have changed."
        )

    common_sizes = [
        256 * 1024,
        128 * 1024,
        192 * 1024,
        112 * 1024,
        96 * 1024,
        64 * 1024,
        32 * 1024,
    ]
    aligned_sizes = list(range(4 * 1024, 512 * 1024 + 1, 4 * 1024))
    sizes = list(dict.fromkeys([*common_sizes, *aligned_sizes]))

    for offset in offsets:
        with executable.open("rb") as source:
            source.seek(offset)
            window = source.read(512 * 1024)
        for size in sizes:
            if size > len(window):
                continue
            try:
                candidate_bytes = window[:size]
                dictionary = zstandard.ZstdCompressionDict(candidate_bytes)
                if dictionary.dict_id() != dict_id:
                    continue
                with archive.open("rb") as source:
                    decode_entry(source, sample, dictionary)
                cached.write_bytes(candidate_bytes)
                log(
                    f"Found and validated dictionary {dict_id} at executable offset "
                    f"{offset:,} ({size:,} bytes)."
                )
                return cached
            except (ValueError, zstandard.ZstdError):
                continue

    raise RuntimeError(
        f"Dictionary {dict_id} was found in the executable but no tested boundary "
        "decoded the base archive. The game format may have changed."
    )


def cache_is_complete(raw_dir: Path, mined_dir: Path, archive_sha: str, mode: str, layer: str) -> bool:
    marker = load_json(raw_dir / ".dead-signal-complete.json", {})
    snapshot = load_json(mined_dir / "snapshot.json", {})
    localization = list((mined_dir / "translate").glob("translate_data_en*.json"))
    required = BASE_REQUIRED if layer == "base" else CURRENT_REQUIRED
    required_tables = [
        mined_dir / "game_common" / "data" / f"{name}.json" for name in required
    ]
    return bool(
        marker.get("archive_sha256") == archive_sha
        and marker.get("mode") == mode
        and snapshot
        and localization
        and all(path.is_file() for path in required_tables)
    )


def extract_and_export_layer(
    *,
    layer: str,
    archive: Path,
    raw_dir: Path,
    mined_dir: Path,
    archive_sha: str,
    mode: str,
    dictionary: Path | None,
    log: LogCallback,
) -> None:
    if cache_is_complete(raw_dir, mined_dir, archive_sha, mode, layer):
        log(f"{layer.title()} script layer is unchanged; using its cached snapshot.")
        return

    raw_dir.mkdir(parents=True, exist_ok=True)
    mined_dir.mkdir(parents=True, exist_ok=True)
    inventory = raw_dir / "inventory.json"
    matcher = "." if mode == "full" else site_match_expression()
    arguments: list[object] = [
        archive,
        "--output",
        raw_dir,
        "--match",
        matcher,
        "--inventory",
        inventory,
    ]
    if dictionary:
        arguments.extend(("--zstd-dictionary", dictionary))

    log(f"Extracting {layer} script layer ({mode} mode)...")
    run_module_main("npk_extract", arguments, log)

    log(f"Exporting structured tables from the {layer} layer...")
    run_module_main(
        "export_bindict",
        [
            raw_dir,
            "--output",
            mined_dir,
            "--neoxtractor",
            NEOXTRACTOR_ROOT,
            "--archive",
            archive,
        ],
        log,
    )

    localization_files = sorted(
        (raw_dir / "translate").glob("translate_data_en*.pyc")
    )
    if not localization_files:
        raise RuntimeError(f"No English localization files were extracted from {archive}")
    for pyc_path in localization_files:
        target = mined_dir / "translate" / pyc_path.with_suffix(".json").name
        run_module_main(
            "export_marshaled_bindict",
            [pyc_path, "--output", target, "--neoxtractor", NEOXTRACTOR_ROOT],
            log,
        )

    write_json(
        raw_dir / ".dead-signal-complete.json",
        {
            "created_utc": utc_now(),
            "layer": layer,
            "mode": mode,
            "archive": str(archive),
            "archive_sha256": archive_sha,
        },
    )


def assert_required_tables(base: Path, current: Path) -> None:
    missing: list[Path] = []
    for name in BASE_REQUIRED:
        path = base / "game_common" / "data" / f"{name}.json"
        if not path.is_file():
            missing.append(path)
    for name in CURRENT_REQUIRED:
        path = current / "game_common" / "data" / f"{name}.json"
        if not path.is_file():
            missing.append(path)
    if missing:
        joined = "\n".join(f"  - {path}" for path in missing)
        raise RuntimeError(f"Required normalized-data inputs are missing:\n{joined}")


def table_domains(relative_path: str) -> list[str]:
    """Return coverage domains whose candidate patterns match a table path."""
    lowered = relative_path.casefold().replace("\\", "/")
    stem = Path(lowered).stem
    matches = []
    for domain, definition in DEAD_SIGNAL_COVERAGE.items():
        patterns = definition.get("patterns", ())
        if any(pattern in stem or pattern in lowered for pattern in patterns):
            matches.append(domain)
    return matches


def build_table_catalog(
    base: Path,
    current: Path,
    output_root: Path,
    mode: str,
    log: LogCallback,
) -> dict:
    """Create a queryable catalog over every exported structured table."""
    catalog_dir = output_root / "catalogs"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    database_path = catalog_dir / "structured-tables.sqlite"
    base_snapshot = load_json(base / "snapshot.json", {}) or {}
    current_snapshot = load_json(current / "snapshot.json", {}) or {}
    base_rows = {
        str(row.get("output")): row
        for row in base_snapshot.get("tables", [])
        if row.get("output")
    }
    current_rows = {
        str(row.get("output")): row
        for row in current_snapshot.get("tables", [])
        if row.get("output")
    }
    paths = sorted(set(base_rows) | set(current_rows))

    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tables (
                relative_path TEXT PRIMARY KEY,
                base_json_path TEXT,
                current_json_path TEXT,
                base_records INTEGER,
                current_records INTEGER,
                base_bytes INTEGER,
                current_bytes INTEGER,
                layer_status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS domain_tables (
                domain TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                PRIMARY KEY (domain, relative_path),
                FOREIGN KEY (relative_path) REFERENCES tables(relative_path)
            );
            CREATE INDEX IF NOT EXISTS domain_tables_path_idx
                ON domain_tables(relative_path);
            """
        )
        connection.execute("DELETE FROM tables")
        connection.execute("DELETE FROM domain_tables")
        connection.execute("DELETE FROM metadata")
        table_values = []
        domain_values = []
        for relative in paths:
            base_row = base_rows.get(relative, {})
            current_row = current_rows.get(relative, {})
            if base_row and current_row:
                status = "base-and-current-patch"
            elif current_row:
                status = "current-patch-only"
            else:
                status = "base-only"
            table_values.append(
                (
                    relative,
                    str((base / relative).resolve()) if base_row else None,
                    str((current / relative).resolve()) if current_row else None,
                    base_row.get("records"),
                    current_row.get("records"),
                    base_row.get("bytes"),
                    current_row.get("bytes"),
                    status,
                )
            )
            domain_values.extend(
                (domain, relative) for domain in table_domains(relative)
            )
        connection.executemany(
            """
            INSERT INTO tables (
                relative_path, base_json_path, current_json_path,
                base_records, current_records, base_bytes, current_bytes,
                layer_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            table_values,
        )
        connection.executemany(
            "INSERT INTO domain_tables (domain, relative_path) VALUES (?, ?)",
            domain_values,
        )
        metadata = {
            "schema_version": "1",
            "created_utc": utc_now(),
            "snapshot_mode": mode,
            "base_snapshot": str(base.resolve()),
            "current_snapshot": str(current.resolve()),
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)", metadata.items()
        )
        connection.commit()

        domain_counts = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT domain, COUNT(*) FROM domain_tables GROUP BY domain ORDER BY domain"
            )
        }
        classified_count = connection.execute(
            "SELECT COUNT(DISTINCT relative_path) FROM domain_tables"
        ).fetchone()[0]
    finally:
        connection.close()

    coverage = {}
    for domain, definition in DEAD_SIGNAL_COVERAGE.items():
        coverage[domain] = {
            "label": definition["label"],
            "source_type": definition["source_type"],
            "covers": definition["covers"],
            "candidate_tables": domain_counts.get(domain, 0),
            "captured_in_this_mode": (
                mode == "full"
                if definition["source_type"] == "game"
                else definition["source_type"] != "game"
            ),
        }
    summary = {
        "schema_version": 1,
        "created_utc": utc_now(),
        "snapshot_mode": mode,
        "database": str(database_path.resolve()),
        "base_tables": len(base_rows),
        "current_patch_tables": len(current_rows),
        "distinct_table_paths": len(paths),
        "classified_table_paths": int(classified_count),
        "unclassified_table_paths": len(paths) - int(classified_count),
        "coverage": coverage,
        "important_note": (
            "Candidate matching proves the source table was captured; it does not "
            "make every internal record publishable. Category normalizers apply "
            "patch-aware joins, localization, exclusions, and review queues."
        ),
    }
    write_json(catalog_dir / "coverage-contract.json", summary)
    log(
        f"Cataloged {len(paths):,} structured table paths across "
        f"{len(DEAD_SIGNAL_COVERAGE):,} Dead Signal coverage domains."
    )
    return summary


def build_asset_index(install: Path, output_root: Path, log: LogCallback) -> dict:
    """Index readable resource paths once so future categories avoid rescanning NPKs."""
    from npk_extract import read_archive  # pylint: disable=import-outside-toplevel

    catalog_dir = output_root / "catalogs"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    database_path = catalog_dir / "resource-assets.sqlite"
    skip_kinds = ("shadercache", "mtlgen", "video")
    archives = sorted(
        path
        for path in install.rglob("*.npk")
        if not any(kind in path.name.casefold() for kind in skip_kinds)
    )

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS archives (
            archive_path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            modified_ns INTEGER NOT NULL,
            file_count INTEGER NOT NULL,
            indexed_utc TEXT NOT NULL,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS entries (
            archive_path TEXT NOT NULL,
            entry_index INTEGER NOT NULL,
            internal_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            stem TEXT NOT NULL,
            extension TEXT NOT NULL,
            signature INTEGER NOT NULL DEFAULT 0,
            offset INTEGER NOT NULL DEFAULT 0,
            compressed_size INTEGER NOT NULL DEFAULT 0,
            original_size INTEGER NOT NULL,
            compressed_crc INTEGER NOT NULL DEFAULT 0,
            original_crc INTEGER NOT NULL DEFAULT 0,
            compression INTEGER NOT NULL,
            encryption INTEGER NOT NULL,
            PRIMARY KEY (archive_path, entry_index)
        );
        CREATE INDEX IF NOT EXISTS entries_stem_idx ON entries(stem);
        CREATE INDEX IF NOT EXISTS entries_extension_idx ON entries(extension);
        CREATE INDEX IF NOT EXISTS entries_path_idx ON entries(internal_path);
        """
    )

    # Version 1 indexed names only.  Version 2 also retains the NXPK entry
    # coordinates required to extract any referenced asset without rescanning
    # the archive.  Rebuild an older partial index once instead of leaving rows
    # that point at offset zero.
    required_columns = {
        "signature": "INTEGER NOT NULL DEFAULT 0",
        "offset": "INTEGER NOT NULL DEFAULT 0",
        "compressed_size": "INTEGER NOT NULL DEFAULT 0",
        "compressed_crc": "INTEGER NOT NULL DEFAULT 0",
        "original_crc": "INTEGER NOT NULL DEFAULT 0",
    }
    existing_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(entries)")
    }
    upgraded = False
    for column, definition in required_columns.items():
        if column not in existing_columns:
            connection.execute(f"ALTER TABLE entries ADD COLUMN {column} {definition}")
            upgraded = True
    previous_schema = connection.execute(
        "SELECT value FROM metadata WHERE key = 'schema_version'"
    ).fetchone()
    if upgraded or not previous_schema or previous_schema[0] != "2":
        connection.execute("DELETE FROM entries")
        connection.execute("DELETE FROM archives")
        connection.commit()

    known = {
        row[0]: (row[1], row[2])
        for row in connection.execute(
            "SELECT archive_path, size, modified_ns FROM archives"
        )
    }
    seen: set[str] = set()
    changed = 0
    reused = 0
    errors = 0
    for number, archive in enumerate(archives, start=1):
        relative = str(archive.relative_to(install)).replace("\\", "/")
        seen.add(relative)
        stat = archive.stat()
        if known.get(relative) == (stat.st_size, stat.st_mtime_ns):
            reused += 1
            continue

        changed += 1
        connection.execute("DELETE FROM entries WHERE archive_path = ?", (relative,))
        try:
            metadata, entries = read_archive(archive)
            values = []
            for entry in entries:
                internal = entry.path or f"{entry.signature:08x}.bin"
                filename = PureWindowsPath(internal).name
                file_path = Path(filename)
                values.append(
                    (
                        relative,
                        entry.index,
                        internal,
                        filename,
                        file_path.stem.casefold(),
                        file_path.suffix.casefold(),
                        entry.signature,
                        entry.offset,
                        entry.compressed_size,
                        entry.original_size,
                        entry.compressed_crc,
                        entry.original_crc,
                        entry.compression,
                        entry.encryption,
                    )
                )
            connection.executemany(
                """
                INSERT INTO entries (
                    archive_path, entry_index, internal_path, filename, stem,
                    extension, signature, offset, compressed_size, original_size,
                    compressed_crc, original_crc, compression, encryption
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO archives (
                    archive_path, size, modified_ns, file_count, indexed_utc, error
                ) VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (
                    relative,
                    stat.st_size,
                    stat.st_mtime_ns,
                    int(metadata.get("file_count", len(entries))),
                    utc_now(),
                ),
            )
        except (OSError, ValueError) as error:
            errors += 1
            connection.execute(
                """
                INSERT OR REPLACE INTO archives (
                    archive_path, size, modified_ns, file_count, indexed_utc, error
                ) VALUES (?, ?, ?, 0, ?, ?)
                """,
                (relative, stat.st_size, stat.st_mtime_ns, utc_now(), str(error)),
            )
        connection.commit()
        if number % 50 == 0:
            log(f"Indexed resource archive {number:,} of {len(archives):,}...")

    removed = sorted(set(known) - seen)
    for relative in removed:
        connection.execute("DELETE FROM entries WHERE archive_path = ?", (relative,))
        connection.execute("DELETE FROM archives WHERE archive_path = ?", (relative,))

    metadata_values = {
        "schema_version": "2",
        "updated_utc": utc_now(),
        "install": str(install),
        "skipped_archive_kinds": ",".join(skip_kinds),
    }
    for key, value in metadata_values.items():
        connection.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (key, value),
        )
    connection.commit()
    archive_count = connection.execute("SELECT COUNT(*) FROM archives").fetchone()[0]
    entry_count = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    resource_digest = hashlib.sha256()
    for archive_path, size, modified_ns in connection.execute(
        "SELECT archive_path, size, modified_ns FROM archives ORDER BY archive_path"
    ):
        resource_digest.update(
            f"{archive_path}\0{size}\0{modified_ns}\n".encode("utf-8")
        )
    extension_counts = {
        row[0] or "[none]": row[1]
        for row in connection.execute(
            """
            SELECT extension, COUNT(*) AS amount
            FROM entries GROUP BY extension ORDER BY amount DESC LIMIT 30
            """
        )
    }
    connection.close()

    summary = {
        "schema_version": 2,
        "updated_utc": utc_now(),
        "database": str(database_path.resolve()),
        "archives": int(archive_count),
        "entries": int(entry_count),
        "fingerprint": resource_digest.hexdigest(),
        "changed_archives": changed,
        "reused_archives": reused,
        "removed_archives": len(removed),
        "archive_errors": errors,
        "skipped_archive_kinds": list(skip_kinds),
        "top_extensions": extension_counts,
    }
    write_json(catalog_dir / "resource-assets-summary.json", summary)
    log(
        f"Resource index ready: {entry_count:,} named entries across "
        f"{archive_count:,} archives ({reused:,} unchanged archives reused)."
    )
    return summary


def normalize_site_data(base: Path, current: Path, published: Path, log: LogCallback) -> dict:
    data_dir = published / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    armor_output = data_dir / "armor-sets.json"
    weapons_output = data_dir / "weapons.json"

    log("Building the armor database...")
    run_module_main(
        "normalize_armor",
        ["--base", base, "--current", current, "--output", armor_output],
        log,
    )
    log("Completing canonical Armor Tier I-V series from exact equipment identities...")
    from armor_tier_completion import complete_file  # pylint: disable=import-outside-toplevel
    complete_file(base, current, armor_output, log)
    log("Building the weapon database...")
    run_module_main(
        "normalize_weapons",
        ["--base", base, "--current", current, "--output", weapons_output],
        log,
    )
    log("Building Mods, Calibrations, Ammo, Attachments, Cradles, Deviations, Consumables, Buffs, Statuses, Keywords, Skills, Stats, and Progression...")
    run_module_main(
        "normalize_extended",
        ["--base", base, "--current", current, "--output-dir", data_dir],
        log,
    )
    log("Resolving combat mechanics, logic trees, stats, compatibility, progression, and relationships...")
    run_module_main(
        "combat_resolver",
        ["--base", base, "--current", current, "--published", published],
        log,
    )
    log("Projecting exact Attachment, Calibration, and selectable Ammo relationships for Weapons Build Lab...")
    run_module_main(
        "weapon_build_compatibility",
        ["--base", base, "--current", current, "--published", published],
        log,
    )
    log("Exporting validated static weapon math for every Tier and Blueprint Star combination...")
    weapon_math_output = data_dir / "weapon-math.json"
    run_module_main(
        "export_weapon_math",
        ["--weapons", weapons_output, "--output", weapon_math_output],
        log,
    )
    log("Exporting fail-closed configured-weapon modifier inputs...")
    weapon_configuration_output = data_dir / "weapon-configuration.json"
    run_module_main(
        "export_weapon_configuration",
        ["--data-dir", data_dir, "--output", weapon_configuration_output],
        log,
    )
    log("Exporting canonical item-to-gun profiles and their directly linked parameter tables...")
    gun_profiles_output = data_dir / "gun-profiles.json"
    run_module_main(
        "export_gun_profiles",
        ["--base", base, "--current", current, "--weapons", weapons_output, "--output", gun_profiles_output],
        log,
    )

    armor = load_json(armor_output, {})
    weapons = load_json(weapons_output, {})
    normalized = {
        "armor": armor.get("record_counts", {}),
        "weapons": weapons.get("record_counts", {}),
        "armor_output": str(armor_output),
        "weapons_output": str(weapons_output),
        "weapon_math_output": str(weapon_math_output),
        "weapon_configuration_output": str(weapon_configuration_output),
        "gun_profiles_output": str(gun_profiles_output),
    }
    for path in sorted(data_dir.glob("*.json")):
        if path.name in {"armor-sets.json", "weapons.json", "reference-images.json", "image-coverage.json"}:
            continue
        payload = load_json(path, {})
        normalized[path.stem.replace("-", "_")] = payload.get("record_counts", {})
    return normalized


def link_published_images(published: Path, log: LogCallback) -> dict:
    """Attach extracted artwork paths to all normalized category records."""
    data_dir = published / "data"
    output = data_dir / "image-coverage.json"
    log("Linking every published record to its extracted display artwork...")
    run_module_main(
        "link_published_images",
        [
            "--data-dir",
            data_dir,
            "--manifest",
            data_dir / "reference-images.json",
            "--output",
            output,
        ],
        log,
    )
    return load_json(output, {})


def extract_reference_assets(
    install: Path,
    output_root: Path,
    published: Path,
    base_tables: Path,
    current_tables: Path,
    base_sha: str,
    current_sha: str,
    resource_fingerprint: str,
    dictionary: Path | None,
    log: LogCallback,
) -> dict:
    """Extract display artwork referenced by every classified content table."""
    assets = published / "assets" / "reference-images"
    manifest_path = published / "data" / "reference-images.json"
    audit_path = output_root / "catalogs" / "reference-images.sqlite"
    asset_state_path = output_root / "manifests" / "reference-images-state.json"
    previous = load_json(asset_state_path, {})
    manifest = load_json(manifest_path, {})
    if (
        previous.get("base_script_sha256") == base_sha
        and previous.get("current_script_sha256") == current_sha
        and previous.get("resource_fingerprint") == resource_fingerprint
        and previous.get("converter_version") == 3
        and manifest.get("counts", {}).get("distinct_references", 0) > 0
        and assets.is_dir()
        and audit_path.is_file()
    ):
        log("Game data is unchanged; using the complete cached artwork library.")
        return manifest

    log("Locating and converting referenced artwork for every Dead Signal domain...")
    arguments: list[object] = [
        "--install",
        install,
        "--base",
        base_tables,
        "--current",
        current_tables,
        "--table-catalog",
        output_root / "catalogs" / "structured-tables.sqlite",
        "--resource-index",
        output_root / "catalogs" / "resource-assets.sqlite",
        "--output",
        published,
        "--audit",
        audit_path,
        "--manifest",
        manifest_path,
    ]
    if dictionary:
        arguments.extend(("--zstd-dictionary", dictionary))
    run_module_main(
        "reference_images",
        arguments,
        log,
    )
    write_json(
        asset_state_path,
        {
            "created_utc": utc_now(),
            "base_script_sha256": base_sha,
            "current_script_sha256": current_sha,
            "resource_fingerprint": resource_fingerprint,
            "converter_version": 3,
        },
    )
    return load_json(manifest_path, {})



def check_cancel(cancel: threading.Event | None) -> None:
    if cancel and cancel.is_set():
        raise MiningCancelled("Mining stopped safely after the current phase.")


def run_pipeline(
    config: MinerConfig,
    log: LogCallback,
    progress: ProgressCallback,
    cancel: threading.Event | None = None,
) -> dict:
    """Run the complete local mining pipeline and return its manifest."""
    config = config.normalized()
    validate_install(config.install)
    config.output.mkdir(parents=True, exist_ok=True)
    started = utc_now()

    base_archive = config.install / "script.npk"
    current_archive = config.install / "Documents" / "script.npk"
    executable = config.install / "ONCE_HUMAN.exe"

    progress(2, "Fingerprinting the installed game")
    log("Dead Signal Miner performs read-only extraction; game and anti-cheat files are not modified.")
    log(f"Install: {config.install}")
    log(f"Output:  {config.output}")
    base_sha = sha256_file(base_archive)
    current_sha = sha256_file(current_archive)
    executable_sha = sha256_file(executable)
    log(f"Base script SHA-256:    {base_sha}")
    log(f"Current script SHA-256: {current_sha}")
    log(f"Game executable SHA-256: {executable_sha}")
    check_cancel(cancel)

    progress(7, "Validating compression dictionary")
    dictionary = required_dictionary(
        base_archive, executable, config.output / "dictionaries", log
    )
    check_cancel(cancel)

    snapshot_root = config.output / "snapshots" / config.mode
    base_root = snapshot_root / "base" / base_sha[:16]
    current_root = snapshot_root / "current" / current_sha[:16]
    base_raw, base_mined = base_root / "raw", base_root / "tables"
    current_raw, current_mined = current_root / "raw", current_root / "tables"

    progress(12, "Extracting the base script layer")
    extract_and_export_layer(
        layer="base",
        archive=base_archive,
        raw_dir=base_raw,
        mined_dir=base_mined,
        archive_sha=base_sha,
        mode=config.mode,
        dictionary=dictionary,
        log=log,
    )
    check_cancel(cancel)

    progress(52 if config.mode == "full" else 38, "Extracting the current patch layer")
    extract_and_export_layer(
        layer="current",
        archive=current_archive,
        raw_dir=current_raw,
        mined_dir=current_mined,
        archive_sha=current_sha,
        mode=config.mode,
        dictionary=None,
        log=log,
    )
    check_cancel(cancel)

    progress(68 if config.mode == "full" else 55, "Cataloging structured game data")
    table_catalog = build_table_catalog(
        base_mined, current_mined, config.output, config.mode, log
    )
    check_cancel(cancel)

    progress(73, "Building the reusable resource index")
    asset_catalog = build_asset_index(config.install, config.output, log)
    check_cancel(cancel)

    progress(82 if config.mode == "full" else 65, "Normalizing website records")
    assert_required_tables(base_mined, current_mined)
    published = config.output / "published"
    normalized = normalize_site_data(base_mined, current_mined, published, log)
    check_cancel(cancel)

    progress(89, "Extracting all referenced artwork")
    artwork_manifest = extract_reference_assets(
        config.install,
        config.output,
        published,
        base_mined,
        current_mined,
        base_sha,
        current_sha,
        str(asset_catalog.get("fingerprint", "")),
        dictionary,
        log,
    )
    image_coverage = link_published_images(published, log)
    check_cancel(cancel)

    progress(95, "Publishing website datasets and integrity reports")
    web_publish_output = published / "snapshot-manifest.json"
    run_module_main(
        "publish_web_data",
        [
            "--data-dir", published / "data",
            "--published", published,
            "--miner-version", APP_VERSION,
            "--base-sha256", base_sha,
            "--current-sha256", current_sha,
            "--executable-sha256", executable_sha,
            "--resource-fingerprint", str(asset_catalog.get("fingerprint", "")),
        ],
        log,
    )
    publishing = {
        "snapshot_manifest": load_json(web_publish_output, {}),
        "data_quality": load_json(published / "reports" / "data-quality.json", {}),
        "change_report": load_json(published / "reports" / "change-report.json", {}),
        "web": {
            "weapons": str((published / "web" / "weapons.json").resolve()),
            "armor": str((published / "web" / "armor.json").resolve()),
            "relationship_graph": str((published / "web" / "relationship-graph.json").resolve()),
            "catalog_index": str((published / "web" / "catalog-index.json").resolve()),
        },
    }
    check_cancel(cancel)

    manifest = {
        "app": "Dead Signal Miner",
        "app_version": APP_VERSION,
        "started_utc": started,
        "completed_utc": utc_now(),
        "method": (
            "Read-only NXPK extraction and NeoX bindict parsing; compiled game "
            "scripts were parsed as data and never executed"
        ),
        "config": {
            **asdict(config),
            "install": str(config.install),
            "output": str(config.output),
        },
        "archives": {
            "base": {"path": str(base_archive), "sha256": base_sha},
            "current": {"path": str(current_archive), "sha256": current_sha},
            "executable": {"path": str(executable), "sha256": executable_sha},
        },
        "active_snapshots": {
            "base": str(base_mined),
            "current": str(current_mined),
        },
        "catalogs": {
            "structured_tables": table_catalog,
            "resource_assets": asset_catalog,
        },
        "normalized": normalized,
        "artwork": {
            "scope": artwork_manifest.get("scope"),
            "counts": artwork_manifest.get("counts", {}),
            "manifest": str((published / "data" / "reference-images.json").resolve()),
            "published_record_coverage": image_coverage.get("totals", {}),
            "coverage_report": str((published / "data" / "image-coverage.json").resolve()),
        },
        "publishing": publishing,
        "published": str(published),
    }
    write_json(config.output / "last-run.json", manifest)
    progress(100, "Mining complete")
    log(
        "Mining complete. The complete structured snapshot, referenced artwork, "
        "and reusable indexes are local; website-ready files are in published."
    )
    return manifest


def self_test() -> dict:
    """Perform non-writing dependency and installed-game checks."""
    checks = {
        "app_version": APP_VERSION,
        "python": sys.version,
        "resource_root": str(ROOT),
        "extractor_root": str(EXTRACTOR_ROOT),
        "neoxtractor_root": str(NEOXTRACTOR_ROOT),
        "vendor_root": str(VENDOR_ROOT),
        "resources": {},
        "imports": {},
        "installations": [str(path) for path in discover_installations()],
    }
    resources = (
        EXTRACTOR_ROOT / "npk_extract.py",
        EXTRACTOR_ROOT / "export_bindict.py",
        EXTRACTOR_ROOT / "normalize_armor.py",
        EXTRACTOR_ROOT / "normalize_weapons.py",
        EXTRACTOR_ROOT / "normalize_extended.py",
        EXTRACTOR_ROOT / "link_published_images.py",
        EXTRACTOR_ROOT / "combat_resolver.py",
        EXTRACTOR_ROOT / "weapon_build_compatibility.py",
        EXTRACTOR_ROOT / "weapon_progression.py",
        EXTRACTOR_ROOT / "export_weapon_math.py",
        EXTRACTOR_ROOT / "export_weapon_configuration.py",
        EXTRACTOR_ROOT / "export_gun_profiles.py",
        EXTRACTOR_ROOT / "publish_web_data.py",
        EXTRACTOR_ROOT / "reference_images.py",
        NEOXTRACTOR_ROOT / "core" / "bindict" / "parser.py",
    )
    checks["resources"] = {str(path): path.is_file() for path in resources}
    for module_name in (
        "lz4.block",
        "zstandard",
        "PIL.Image",
        "texture2ddecoder",
        "npk_extract",
        "normalize_armor",
        "normalize_extended",
        "link_published_images",
        "combat_resolver",
        "weapon_build_compatibility",
        "weapon_progression",
        "export_weapon_math",
        "export_weapon_configuration",
        "export_gun_profiles",
        "publish_web_data",
        "reference_images",
    ):
        try:
            module = importlib.import_module(module_name)
            checks["imports"][module_name] = getattr(module, "__version__", "ok")
        except Exception as error:  # pragma: no cover - diagnostic path
            checks["imports"][module_name] = f"ERROR: {type(error).__name__}: {error}"
    checks["ok"] = bool(
        all(checks["resources"].values())
        and all(not str(value).startswith("ERROR") for value in checks["imports"].values())
        and checks["installations"]
    )
    return checks


def format_exception(error: BaseException) -> str:
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))
