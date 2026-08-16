from __future__ import annotations

import json
import marshal
import py_compile
from pathlib import Path

from dead_signal_data_proxy_architecture import run_data_proxy_architecture_audit


def _snapshot(root: Path, source: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "snapshot.json").write_text(
        json.dumps({"source_root": str(source)}, indent=2), encoding="utf-8"
    )
    return root


def _compile(source_root: Path, relative: str, text: str) -> Path:
    py = source_root / relative.replace(".pyc", ".py")
    py.parent.mkdir(parents=True, exist_ok=True)
    py.write_text(text, encoding="utf-8")
    pyc = source_root / relative
    py_compile.compile(str(py), cfile=str(pyc), doraise=True)
    py.unlink()
    return pyc


def test_data_proxy_architecture_maps_all_three_proxies(tmp_path: Path) -> None:
    source = tmp_path / "source"
    env = _compile(
        source,
        "dcs_core/Env.pyc",
        """
class Env:
    _DATA_PROXY = {}
    common_data = None
    client_data = None
    server_data = None

    @classmethod
    def set_data_proxy(cls, proxy):
        cls._DATA_PROXY['common_data'] = proxy
        cls._DATA_PROXY['client_data'] = proxy
        cls._DATA_PROXY['server_data'] = proxy
""",
    )
    datamgr = _compile(
        source,
        "game_common/helper/DataMgr.pyc",
        """
class DataMgr:
    common_data = None
    client_data = None
    server_data = None

    def load_data(self):
        return self.common_data, self.client_data, self.server_data

    def get_data_proxy_name(self):
        return 'common_data'
""",
    )
    _compile(
        source,
        "game_common/guncore/WeaponConsumer.pyc",
        """
WEAPON_PROTOTYPE_TABLE = 'WEAPON_PROTOTYPE_TABLE'
gun_preview_param_data = 'gun_preview_param_data'
server_weapon_rule_data = 'server_weapon_rule_data'

def common_lookup(Env):
    return Env.common_data, WEAPON_PROTOTYPE_TABLE

def client_lookup(Env):
    return Env.client_data, gun_preview_param_data

def server_lookup(Env):
    return Env.server_data, server_weapon_rule_data
""",
    )
    base = _snapshot(tmp_path / "base", source)
    current = _snapshot(tmp_path / "current", source)
    reports = tmp_path / "reports"

    report = run_data_proxy_architecture_audit(base, current, reports)

    counts = report["record_counts"]
    assert counts["pyc_files_scanned"] == 3
    assert counts["proxy_hit_modules"] == 3
    assert counts["target_env_datamgr_modules"] == 2
    assert counts["proxy_code_object_counts"]["common_data"] >= 1
    assert counts["proxy_code_object_counts"]["client_data"] >= 1
    assert counts["proxy_code_object_counts"]["server_data"] >= 1

    ownership = {row["symbol"]: row for row in report["symbol_proxy_ownership"]}
    assert ownership["WEAPON_PROTOTYPE_TABLE"]["proxy_classification"] == "exact-common_data-cooccurrence"
    assert ownership["gun_preview_param_data"]["proxy_classification"] == "exact-client_data-cooccurrence"
    assert ownership["server_weapon_rule_data"]["proxy_classification"] == "exact-server_data-cooccurrence"

    targets = {row["relative_path"]: row for row in report["central_modules_full_static_audit"]}
    assert "dcs_core/Env.pyc" in targets
    assert "game_common/helper/DataMgr.pyc" in targets
    assert any(row["co_name"] == "set_data_proxy" for row in targets["dcs_core/Env.pyc"]["code_objects"])
    assert any(row["co_name"] == "load_data" for row in targets["game_common/helper/DataMgr.pyc"]["code_objects"])

    assert env.is_file() and datamgr.is_file()
    assert (reports / "data-proxy-architecture-static-audit.json").is_file()
