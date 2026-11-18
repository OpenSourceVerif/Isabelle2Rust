"""Guard large fallback scopes against repeated whole-inventory work."""
import _paths
import copy
import unittest
from unittest.mock import patch

import dependency_plan as dp
import plan_recovery as recovery
from scan_store import digest
import test_plan_selection_receipts as selection_fixture


class FallbackScalingTests(unittest.TestCase):
    def test_failure_inventory_is_hashed_once_for_all_frozen_singletons(self):
        context = {"id": "context", "entry": "E", "input": "frozen", "session": "E",
                   "parents": ["E.Main", *dp.SETUPS]}
        declarations = [{"source": "Main.thy", "owner": "E.Main", "name": "Main.f" + str(i)}
                        for i in range(1000)]
        failures = [{"phase": "user_deferred", "roots": [dp.declaration_id(d) for d in declarations]}]
        calls = []
        def observe(value):
            if value is failures:
                calls.append("full inventory")
            return digest(value)
        with patch.object(recovery, "digest", side_effect=observe):
            groups = recovery.singleton_requests(context, declarations, failures)
        self.assertEqual(calls, ["full inventory"])
        self.assertEqual(len(groups), len(declarations))
        self.assertEqual({g["trigger"] for g in groups}, {digest(failures)})
        self.assertEqual({g["declaration"] for g in groups}, {dp.declaration_id(d) for d in declarations})
        self.assertTrue(all("coverage" not in g for g in groups))

    def test_selection_membership_uses_exact_identities_without_repeated_list_scans(self):
        fixture = selection_fixture.SelectionReceiptTests()
        fixture.setUp()
        root = fixture.receipt(failed=False)
        class IndexedInventory(list):
            def __contains__(self, value):
                raise AssertionError("quadratic membership scan of original inventory")
        fixture.expected["declarations"] = IndexedInventory(fixture.expected["declarations"])
        self.assertEqual(len(fixture.parse(root)[0]["declarations"]), 2)
        changed = copy.deepcopy(root)
        changed.find("context/declaration").set("source", "different-owner.thy")
        with self.assertRaisesRegex(ValueError, "Foreign declaration"):
            fixture.parse(changed)


if __name__ == "__main__":
    unittest.main()
