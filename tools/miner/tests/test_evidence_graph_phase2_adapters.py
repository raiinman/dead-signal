from __future__ import annotations

import sys
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
from dead_signal_evidence_contracts import (  # noqa: E402
    ASSESSMENT_SCHEMA_VERSION,
    ENTITY_SCHEMA_VERSION,
    GENERAL_SCHEMA,
    GENERAL_SCHEMA_VERSION,
)
from dead_signal_weapon_adapter import WEAPON_CONTRACT, WeaponAdapter  # noqa: E402


class DummyAdapter(EvidenceDomainAdapter):
    contract = AdapterContract(
        entity_type="dummy",
        identity_seeds=("dummy_id",),
        canonical_owner_tables=("game_common/data/dummy_data.json",),
        allowed_outbound_fields=("target_id",),
        typed_destination_tables=(("target_id", ("game_common/data/target_data.json",)),),
        collision_prone_fields=("target_id",),
        blocked_generic_fields=("id", "no", "code"),
        terminal_presentation_fields=("name",),
        supported_claims=("dummy.identity",),
        applicability_rules=("exact owner required",),
    )

    def graph(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        value = str(identity)
        return {
            "schema": GENERAL_SCHEMA,
            "schema_version": GENERAL_SCHEMA_VERSION,
            "brand": "Dead Signal",
            "entity": {
                "schema_version": ENTITY_SCHEMA_VERSION,
                "entity_type": "dummy",
                "canonical_id": value,
                "name": f"Dummy {value}",
                "classification": "test",
                "identity_state": "UNRESOLVED",
                "source_records": [],
            },
            "claims": [],
            "edges": [],
            "assessment": {
                "schema_version": ASSESSMENT_SCHEMA_VERSION,
                "result": "UNRESOLVED",
                "claim_counts": {
                    "PROVEN": 0,
                    "PARTIAL": 0,
                    "UNRESOLVED": 0,
                    "NOT APPLICABLE": 0,
                    "CONFLICT": 0,
                },
                "missing": [],
                "conflicts": [],
            },
            "compatibility": {},
        }

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        return self.graph(identity)["entity"]

    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        return []

    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        raise KeyError(claim_type)

    def dependencies(self, identity: object, **kwargs: Any) -> list[str]:
        return []

    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        return {"canonical_id": str(identity), "publication_authority": False}


class EvidenceGraphPhaseTwoAdapterTests(unittest.TestCase):
    def test_registry_routes_new_domain_without_core_changes(self):
        registry = EvidenceAdapterRegistry()
        registry.register(DummyAdapter())
        self.assertEqual(("dummy",), registry.entity_types())
        payload = registry.graph("dummy", "123")
        self.assertEqual("dummy", payload["entity"]["entity_type"])
        self.assertEqual("123", payload["entity"]["canonical_id"])

    def test_duplicate_domain_registration_fails_closed(self):
        registry = EvidenceAdapterRegistry((DummyAdapter(),))
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(DummyAdapter())

    def test_unknown_domain_fails_closed(self):
        registry = EvidenceAdapterRegistry()
        with self.assertRaisesRegex(KeyError, "No evidence adapter"):
            registry.get("weapon")

    def test_bare_generic_identity_seed_is_forbidden(self):
        contract = AdapterContract(
            entity_type="bad",
            identity_seeds=("id",),
            canonical_owner_tables=("x.json",),
            allowed_outbound_fields=(),
            typed_destination_tables=(),
            collision_prone_fields=(),
            blocked_generic_fields=("id",),
            terminal_presentation_fields=(),
            supported_claims=("bad.identity",),
            applicability_rules=(),
        )
        self.assertIn("generic identity seed is forbidden: id", contract.validate())

    def test_collision_prone_field_requires_explicit_destination(self):
        contract = AdapterContract(
            entity_type="bad",
            identity_seeds=("thing_id",),
            canonical_owner_tables=("thing.json",),
            allowed_outbound_fields=("target_id",),
            typed_destination_tables=(),
            collision_prone_fields=("target_id",),
            blocked_generic_fields=("id", "no", "code"),
            terminal_presentation_fields=(),
            supported_claims=("bad.identity",),
            applicability_rules=(),
        )
        self.assertIn(
            "collision-prone field requires explicit destination tables: target_id",
            contract.validate(),
        )

    def test_collision_prone_identity_seed_uses_canonical_owner_not_destination(self):
        contract = AdapterContract(
            entity_type="recipe-like",
            identity_seeds=("forge_no", "server_no"),
            canonical_owner_tables=("game_common/data/forge_data.json",),
            allowed_outbound_fields=("output_item_id",),
            typed_destination_tables=(("output_item_id", ("game_common/data/item_data.json",)),),
            collision_prone_fields=("forge_no", "server_no", "output_item_id"),
            blocked_generic_fields=("id", "no", "code"),
            terminal_presentation_fields=(),
            supported_claims=("recipe-like.identity",),
            applicability_rules=("exact compound identity owner required",),
        )
        self.assertEqual([], contract.validate())

    def test_bare_generic_outbound_field_is_forbidden(self):
        contract = AdapterContract(
            entity_type="bad",
            identity_seeds=("thing_id",),
            canonical_owner_tables=("thing.json",),
            allowed_outbound_fields=("code",),
            typed_destination_tables=(),
            collision_prone_fields=(),
            blocked_generic_fields=("id", "no", "code"),
            terminal_presentation_fields=(),
            supported_claims=("bad.identity",),
            applicability_rules=(),
        )
        self.assertIn("bare generic outbound field is forbidden: code", contract.validate())

    def test_weapon_contract_is_valid_and_typed(self):
        self.assertEqual([], WEAPON_CONTRACT.validate())
        self.assertEqual("weapon", WEAPON_CONTRACT.entity_type)
        destinations = WEAPON_CONTRACT.destinations()
        for field in WEAPON_CONTRACT.collision_prone_fields:
            self.assertTrue(destinations[field])

    def test_adapters_have_no_publication_method(self):
        self.assertFalse(hasattr(EvidenceDomainAdapter, "publish"))
        self.assertFalse(hasattr(WeaponAdapter, "publish"))


if __name__ == "__main__":
    unittest.main()
