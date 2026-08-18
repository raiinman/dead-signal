import unittest

from weapon_identity_spine import discover_weapon_identities


def item(item_type=1, subtype=3, name="Weapon", **extra):
    return {"type": item_type, "sub_type": subtype, "name": name, "temp_item": 0, "private_server_item": 0, "item_belonge_tab": 2 if item_type == 2 else 10, **extra}


def equip(blueprint=0, origin=1, art=1, gun=99):
    return {"blueprint_no": blueprint, "equip_origin_id": origin, "art_lv": art, "equip_lv": 1, "gun_no": gun}


class WeaponIdentitySpineTests(unittest.TestCase):
    def test_standard_nonstandard_and_special_are_derived(self):
        items = {"1001": item(), "2001": item(), "3001": item(subtype=21)}
        equipment = {"1001": equip(5001), "2001": equip(5002), "3001": equip(0, gun=100)}
        origins = {"1": {"gun_preset_attack": 10}}
        achievements = {
            "1001": {"attrs": ["arms_gun_submachinegun", "arms_gun_lv1"]},
            "2001": {"attrs": ["arms_gun_submachinegun", "arms_gun_lv1"]},
            "3001": {"attrs": ["arms_gun_pistolgun", "arms_gun_lv1"]},
        }
        blueprints = {
            "5001": {"gun_item_no": 1001, "blueprint_template_no": 10, "corr_forge_no": [1,2,3,4,5], "corr_forge_lv": [1,2,3,4,5]},
            "5002": {"gun_item_no": 2001, "blueprint_template_no": 10},
        }
        rows, _ = discover_weapon_identities(items, equipment, origins, achievements, blueprints, {k:k for k in items})
        self.assertEqual(["standard-blueprint", "nonstandard-blueprint", "special-equipped"], [r["identity_state"] for r in rows])
        self.assertEqual(1, rows[2]["weapon_type_code"])
        self.assertEqual("unresolved-scenario-availability", rows[2]["availability_state"])

    def test_missing_blueprint_owner_uses_only_exact_tier_one_identity(self):
        items = {"4001": item(), "4002": item()}
        equipment = {"4001": equip(9000, art=1), "4002": equip(9000, art=2)}
        origins = {"1": {}}
        achievements = {k:{"attrs":["arms_gun_submachinegun","arms_gun_lv1"]} for k in items}
        rows, _ = discover_weapon_identities(items, equipment, origins, achievements, {}, {k:k for k in items})
        self.assertEqual([4001], [r["item_id"] for r in rows])
        self.assertEqual("referenced-owner-missing", rows[0]["blueprint_owner_state"])

    def test_tier_duplicates_variants_and_explicit_tests_do_not_leak(self):
        items = {
            "5001": item(),
            "5002": item(),
            "6001": item(),
            "7001": item(name="FPP Test Weapon"),
        }
        equipment = {"5001": equip(8001), "5002": equip(8001, art=2), "6001": equip(8002), "7001": equip(8003)}
        origins = {"1": {}}
        achievements = {
            "5001":{"attrs":["arms_gun_submachinegun","arms_gun_lv1"]},
            "5002":{"attrs":["arms_gun_submachinegun","arms_gun_lv1"]},
            "6001":{"attrs":["arms_gun_submachinegun","arms_gun_lv0"]},
            "7001":{"attrs":["arms_gun_submachinegun","arms_gun_lv1"]},
        }
        blueprints = {
            "8001":{"gun_item_no":5001,"blueprint_template_no":10},
            "8002":{"gun_item_no":6001,"blueprint_template_no":10},
            "8003":{"gun_item_no":7001,"blueprint_template_no":10},
        }
        rows, exclusions = discover_weapon_identities(items, equipment, origins, achievements, blueprints, {k:v["name"] for k,v in items.items()})
        self.assertEqual([5001], [r["item_id"] for r in rows])
        self.assertEqual(1, exclusions["non-player-level-zero-weapon"])
        self.assertEqual(1, exclusions["explicit-test-record"])

    def test_temporary_private_and_wrong_template_are_excluded(self):
        items = {"8001":item(temp_item=1), "9001":item(private_server_item=1), "10001":item()}
        equipment = {k:equip(int(k)+100) for k in items}
        origins={"1":{}}
        achievements={k:{"attrs":["arms_gun_submachinegun","arms_gun_lv1"]} for k in items}
        blueprints={str(int(k)+100):{"gun_item_no":int(k),"blueprint_template_no":20} for k in items}
        rows, exclusions=discover_weapon_identities(items,equipment,origins,achievements,blueprints,{k:k for k in items})
        self.assertEqual([],rows)
        self.assertEqual(1,exclusions["temporary-item"])
        self.assertEqual(1,exclusions["private-server-item"])
        self.assertEqual(1,exclusions["non-current-blueprint-template"])

    def test_special_duplicate_gun_owner_and_tab_mismatch_are_excluded(self):
        items={"11001":item(),"12001":item(),"13001":item(item_type=2,item_belonge_tab=10)}
        equipment={"11001":equip(21001),"12001":{**equip(0),"gun_no":99},"13001":{**equip(0),"gun_no":101}}
        origins={"1":{}}
        achievements={"11001":{"attrs":["arms_gun_lv1"]},"12001":{"attrs":["arms_gun_lv1"]},"13001":{"attrs":["arms_hand"]}}
        blueprints={"21001":{"gun_item_no":11001,"blueprint_template_no":10}}
        rows,exclusions=discover_weapon_identities(items,equipment,origins,achievements,blueprints,{k:k for k in items})
        self.assertEqual([11001],[r["item_id"] for r in rows])
        self.assertEqual(1,exclusions["duplicate-exact-gun-owner"])
        self.assertEqual(1,exclusions["weapon-tab-family-mismatch"])

    def test_handoff_identity_cohorts_and_aliases_remain_source_derived(self):
        omitted = [10219901, 10351101, 10341101, 10241101, 10561101, 10361101]
        special = [12621401, 12131101, 12311401, 10912000, 12321101, 12411401]
        local = [10451101, 10451401, 10742201, 10641201, 10511101, 10512301]
        aliases = {10211301: "Dual Fury", 10361401: "FP9 - Additional Rules"}
        all_ids = omitted + special + local + list(aliases)
        items = {str(i): item(item_type=2 if i == 10912000 else 1, name=aliases.get(i, str(i))) for i in all_ids}
        equipment = {}
        blueprints = {}
        for i in omitted:
            blueprint = i + 3000000
            equipment[str(i)] = equip(blueprint, gun=i)
            if i in omitted[:3]:
                blueprints[str(blueprint)] = {"gun_item_no": i, "blueprint_template_no": 10}
        for i in special:
            equipment[str(i)] = equip(i + 3000000 if i == 10912000 else 0, gun=i)
        for i in local + list(aliases):
            blueprint = i + 3000000
            equipment[str(i)] = equip(blueprint, gun=i)
            blueprints[str(blueprint)] = {"gun_item_no": i, "blueprint_template_no": 10, "corr_forge_no": [1,2,3,4,5], "corr_forge_lv": [1,2,3,4,5]}
        achievements = {str(i): {"attrs": ["arms_hand"] if i == 10912000 else ["arms_gun_lv1", "arms_gun_submachinegun"]} for i in all_ids}
        rows, _ = discover_weapon_identities(items, equipment, {"1": {}}, achievements, blueprints, {str(i): aliases.get(i, str(i)) for i in all_ids})
        by_item = {row["item_id"]: row for row in rows}
        self.assertEqual(set(all_ids), set(by_item))
        self.assertTrue(all(by_item[i]["identity_state"] == "nonstandard-blueprint" for i in omitted))
        self.assertTrue(all(by_item[i]["identity_state"] == "special-equipped" for i in special))
        self.assertTrue(all(by_item[i]["identity_state"] == "standard-blueprint" for i in local))
        self.assertEqual(aliases, {i: by_item[i]["name"] for i in aliases})


if __name__ == "__main__":
    unittest.main()
