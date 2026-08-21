from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_domain_adapters import (  # noqa: E402
    AdapterContract,
    EvidenceAdapterRegistry,
    EvidenceDomainAdapter,
)
from dead_signal_entity_registry import DeadSignalEntityRegistry  # noqa: E402


class RegistryWeaponAdapter(EvidenceDomainAdapter):
    contract = AdapterContract(
        entity_type="weapon",
        identity_seeds=("blueprint_id",),
        canonical_owner_tables=("published/web/weapons.json",),
        allowed_outbound_fields=("item_id",),
        typed_destination_tables=(),
        collision_prone_fields=(),
        blocked_generic_fields=("id", "no", "code"),
        terminal_presentation_fields=("name",),
        supported_claims=("weapon.identity",),
        applicability_rules=("test",),
    )

    def graph(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def dependencies(self, identity: object, **kwargs: Any) -> list[str]:
        raise NotImplementedError

    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError


class EvidenceGraphPhaseThreeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        published = self.output / "published" / "web"
        published.mkdir(parents=True)
        (self.output / "last-run.json").write_text(
            json.dumps({"published": str(self.output / "published")}),
            encoding="utf-8",
        )
        (published / "weapons.json").write_text(
            json.dumps({
                "weapons": [
                    {
                        "canonical_id": "weapon-a",
                        "name": "Alpha Rifle",
                        "blueprint_id": 1001,
                        "item_id": 2001,
                        "prototype_id": 301,
                        "category": "AR",
                        "identity_state": "PROVEN",
                        "availability_state": "AVAILABLE",
                        "artwork_reference": "alpha.png",
                    },
                    {
                        "canonical_id": "weapon-b",
                        "name": "Beta SMG",
                        "blueprint_id": 1002,
                        "item_id": 2002,
                        "category": "SMG",
                        "identity_state": "UNRESOLVED",
                    },
                ]
            }),
            encoding="utf-8",
        )
        adapters = EvidenceAdapterRegistry((RegistryWeaponAdapter(),))
        self.registry = DeadSignalEntityRegistry(self.output, adapters)
        self.summary = self.registry.rebuild()

    def tearDown(self):
        self.temp.cleanup()

    def test_rebuild_indexes_only_adapter_backed_entities(self):
        self.assertEqual(2, self.summary["total"])
        self.assertEqual({"weapon": 2}, self.summary["by_entity_type"])
        self.assertEqual(["weapon"], self.summary["adapter_types"])

    def test_search_by_source_proven_name(self):
        results = self.registry.search("alpha")
        self.assertEqual(1, len(results))
        self.assertEqual("weapon-a", results[0]["canonical_id"])
        self.assertIn("Alpha Rifle", results[0]["aliases"])

    def test_search_by_exact_identity_alias(self):
        results = self.registry.search("2001", entity_type="weapon")
        self.assertEqual(1, len(results))
        self.assertEqual("weapon-a", results[0]["canonical_id"])

    def test_unresolved_only_filter(self):
        results = self.registry.search("", unresolved_only=True)
        self.assertEqual(["weapon-b"], [row["canonical_id"] for row in results])

    def test_registry_returns_graph_navigation_target(self):
        entity = self.registry.get("weapon", "weapon-a")
        self.assertEqual(
            {"entity_type": "weapon", "canonical_id": "weapon-a"},
            entity["graph_target"],
        )

    def test_recent_entities_are_deduplicated(self):
        self.registry.get("weapon", "weapon-a")
        self.registry.get("weapon", "weapon-b")
        self.registry.get("weapon", "weapon-a")
        self.assertEqual(
            ["weapon-a", "weapon-b"],
            [row["canonical_id"] for row in self.registry.recent()],
        )

    def test_duplicate_canonical_identity_fails_closed(self):
        path = self.output / "published" / "web" / "weapons.json"
        path.write_text(
            json.dumps({"weapons": [
                {"canonical_id": "same", "name": "One"},
                {"canonical_id": "same", "name": "Two"},
            ]}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "Duplicate canonical entity identity"):
            self.registry.rebuild()


if __name__ == "__main__":
    unittest.main()
