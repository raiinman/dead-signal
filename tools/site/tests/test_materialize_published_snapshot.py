from __future__ import annotations

import importlib.util
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "materialize-published-snapshot.py"
SPEC = importlib.util.spec_from_file_location("materialize_published_snapshot", SCRIPT)
assert SPEC and SPEC.loader
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


class FakeMaterializers:
    def __init__(self, fail_category: str | None = None):
        self.fail_category = fail_category
        self.weapons = types.SimpleNamespace(
            resolve_source=lambda root: root / "web" / "weapons.json",
            load_and_validate=self._validate_weapons,
            write_browser_payload=lambda _source, output, _payload: output.write_text("weapons-new\n", encoding="utf-8"),
        )
        self.armor = types.SimpleNamespace(
            resolve_source=lambda root: root / "web" / "armor.json",
            load_and_validate=self._validate_armor,
            write_browser_payload=lambda _source, output, _payload: output.write_text("armor-new\n", encoding="utf-8"),
        )
        self.extended = types.SimpleNamespace(
            CATEGORIES={
                category: (f"dead-signal-{category}", f"{category}.json", f"DS_{category.upper()}_WEB", "unused.js", "attachments" if category == "attachments" else "families")
                for category in snapshot.EXTENDED_CATEGORIES
            },
            resolve_source=lambda root, filename: root / "web" / filename,
            load_and_validate=self._validate_extended,
            materialize=self._materialize_extended,
        )

    def modules(self):
        return self.weapons, self.armor, self.extended

    def _maybe_fail(self, category: str):
        if self.fail_category == category:
            raise ValueError(f"forced {category} validation failure")

    def _validate_weapons(self, _path):
        self._maybe_fail("weapons")
        return {"schema": "dead-signal-weapons", "schema_version": 1, "weapons": [{"canonical_id": "w1"}]}

    def _validate_armor(self, _path):
        self._maybe_fail("armor")
        return {
            "schema": "dead-signal-armor",
            "schema_version": 1,
            "armor_sets": [{"pieces": [{"canonical_id": "a1"}]}],
            "key_armor": [{"canonical_id": "ka1"}],
        }

    def _validate_extended(self, _path, category, _schema, collection):
        self._maybe_fail(category)
        payload = {
            "schema": f"dead-signal-{category}",
            "schema_version": 2 if category == "calibrations" else 1,
        }
        payload[collection] = [{"canonical_id": f"{category}-1"}]
        return payload

    def _materialize_extended(self, category, _published, output):
        output.write_text(f"{category}-new\n", encoding="utf-8")
        return output


class SnapshotMaterializerTests(unittest.TestCase):
    def _fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        repo = root / "repo"
        published = root / "published"
        (published / "web").mkdir(parents=True)
        repo.mkdir()
        for name in ("weapons", "armor", *snapshot.EXTENDED_CATEGORIES):
            (published / "web" / f"{name}.json").write_text(f'{{"fixture":"{name}"}}\n', encoding="utf-8")
        return temp, repo, published

    def _seed_outputs(self, repo: Path, value: str = "old\n"):
        for relative in snapshot.FINAL_OUTPUTS.values():
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")

    def test_dry_run_validates_all_contracts_without_replacing_outputs(self):
        temp, repo, published = self._fixture()
        self.addCleanup(temp.cleanup)
        self._seed_outputs(repo)
        fake = FakeMaterializers()
        with mock.patch.object(snapshot, "_load_materializers", return_value=fake.modules()):
            report = snapshot.ingest_snapshot(published, repository_root=repo, dry_run=True)

        self.assertEqual("validated-dry-run", report["status"])
        self.assertFalse(report["outputs_replaced"])
        self.assertEqual(set(snapshot.FINAL_OUTPUTS), set(report["contracts"]))
        for relative in snapshot.FINAL_OUTPUTS.values():
            self.assertEqual("old\n", (repo / relative).read_text(encoding="utf-8"))

    def test_validation_failure_leaves_repository_payloads_untouched(self):
        temp, repo, published = self._fixture()
        self.addCleanup(temp.cleanup)
        self._seed_outputs(repo)
        fake = FakeMaterializers(fail_category="armor")
        with mock.patch.object(snapshot, "_load_materializers", return_value=fake.modules()):
            with self.assertRaisesRegex(ValueError, "forced armor validation failure"):
                snapshot.ingest_snapshot(published, repository_root=repo)

        for relative in snapshot.FINAL_OUTPUTS.values():
            self.assertEqual("old\n", (repo / relative).read_text(encoding="utf-8"))

    def test_success_replaces_all_seven_payloads_together(self):
        temp, repo, published = self._fixture()
        self.addCleanup(temp.cleanup)
        self._seed_outputs(repo)
        fake = FakeMaterializers()
        with mock.patch.object(snapshot, "_load_materializers", return_value=fake.modules()):
            report = snapshot.ingest_snapshot(published, repository_root=repo)

        self.assertEqual("materialized", report["status"])
        self.assertTrue(report["outputs_replaced"])
        self.assertEqual("weapons-new\n", (repo / snapshot.FINAL_OUTPUTS["weapons"]).read_text(encoding="utf-8"))
        self.assertEqual("armor-new\n", (repo / snapshot.FINAL_OUTPUTS["armor"]).read_text(encoding="utf-8"))
        for category in snapshot.EXTENDED_CATEGORIES:
            self.assertEqual(f"{category}-new\n", (repo / snapshot.FINAL_OUTPUTS[category]).read_text(encoding="utf-8"))

    def test_mid_commit_failure_rolls_back_already_replaced_files(self):
        temp, repo, _published = self._fixture()
        self.addCleanup(temp.cleanup)
        self._seed_outputs(repo, "before\n")
        staged_root = Path(temp.name) / "staged"
        staged = {}
        for category, relative in snapshot.FINAL_OUTPUTS.items():
            path = staged_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{category}-after\n", encoding="utf-8")
            staged[category] = path

        original_copyfile = snapshot.shutil.copyfile
        calls = 0

        def flaky_copyfile(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("forced commit failure")
            return original_copyfile(source, destination)

        with mock.patch.object(snapshot.shutil, "copyfile", side_effect=flaky_copyfile):
            with self.assertRaisesRegex(OSError, "forced commit failure"):
                snapshot._commit_staged(repo, staged)

        for relative in snapshot.FINAL_OUTPUTS.values():
            self.assertEqual("before\n", (repo / relative).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
