import unittest

from batch_source_index import build_source_index, compare_source_indexes, source_index_scope_matches


class BatchSourceIndexTests(unittest.TestCase):
    def _report(self, input_directory="D:/assets", family_kind="AUTO_FOLDER", results=None, errors=None):
        return {
            "input_directory": input_directory,
            "family_kind": family_kind,
            "aborted": False,
            "results": results or [],
            "errors": errors or [],
        }

    def test_builds_records_for_success_and_failure(self):
        index = build_source_index(self._report(
            results=[{
                "source": "D:/assets/beds/a.blend",
                "output_key": "beds/a",
                "family_kind": "BED",
                "family_id": "axion:bed:beds/a",
            }],
            errors=[{
                "source": "D:/assets/windows/b.glb",
                "output_key": "windows/b",
                "family_kind": "WINDOW",
                "family_id": "axion:window:windows/b",
                "error": "import failed",
            }],
        ))
        self.assertEqual(index["sourceCount"], 2)
        self.assertEqual(index["resolvedFamilyCount"], 2)
        self.assertEqual(index["convertedCount"], 1)
        self.assertEqual(index["failedCount"], 1)
        self.assertTrue(index["sources"][0]["converted"])
        self.assertFalse(index["sources"][1]["converted"])

    def test_scope_requires_same_input_root_and_requested_class(self):
        left = build_source_index(self._report(input_directory="D:/assets", family_kind="AUTO_FOLDER"))
        same = build_source_index(self._report(input_directory="D:/assets", family_kind="auto_folder"))
        different_root = build_source_index(self._report(input_directory="D:/other", family_kind="AUTO_FOLDER"))
        different_class = build_source_index(self._report(input_directory="D:/assets", family_kind="BED"))
        self.assertTrue(source_index_scope_matches(left, same))
        self.assertFalse(source_index_scope_matches(left, different_root))
        self.assertFalse(source_index_scope_matches(left, different_class))

    def test_removed_source_becomes_stale_only_for_same_scope_and_existing_package(self):
        previous = build_source_index(self._report(results=[
            {"source": "D:/assets/beds/a.blend", "family_id": "axion:bed:beds/a", "family_kind": "BED"},
            {"source": "D:/assets/beds/b.blend", "family_id": "axion:bed:beds/b", "family_kind": "BED"},
        ]))
        current = build_source_index(self._report(results=[
            {"source": "D:/assets/beds/a.blend", "family_id": "axion:bed:beds/a", "family_kind": "BED"},
        ]))
        result = compare_source_indexes(previous, current, catalog_family_ids={"axion:bed:beds/a", "axion:bed:beds/b"})
        self.assertTrue(result["comparable"])
        self.assertTrue(result["catalogAvailable"])
        self.assertEqual(result["staleFamilyIds"], ["axion:bed:beds/b"])
        self.assertEqual(result["staleCount"], 1)

        no_old_package = compare_source_indexes(previous, current, catalog_family_ids={"axion:bed:beds/a"})
        self.assertEqual(no_old_package["staleFamilyIds"], [])
        self.assertEqual(no_old_package["staleCount"], 0)

        different_scope = build_source_index(self._report(input_directory="D:/other", results=[]))
        unrelated = compare_source_indexes(previous, different_scope, catalog_family_ids={"axion:bed:beds/b"})
        self.assertFalse(unrelated["comparable"])
        self.assertEqual(unrelated["staleFamilyIds"], [])

    def test_previous_failure_without_package_does_not_become_stale(self):
        previous = build_source_index(self._report(errors=[
            {
                "source": "D:/assets/windows/never-built.blend",
                "family_id": "axion:window:windows/never-built",
                "family_kind": "WINDOW",
                "error": "initial conversion failed",
            },
        ]))
        current = build_source_index(self._report(results=[]))
        result = compare_source_indexes(previous, current, catalog_family_ids=set())
        self.assertTrue(result["comparable"])
        self.assertEqual(result["staleCount"], 0)
        self.assertEqual(result["staleFamilyIds"], [])

    def test_missing_catalog_keeps_stale_candidates_unverified(self):
        previous = build_source_index(self._report(results=[
            {"source": "D:/assets/beds/a.blend", "family_id": "axion:bed:beds/a", "family_kind": "BED"},
        ]))
        current = build_source_index(self._report(results=[]))
        result = compare_source_indexes(previous, current, catalog_family_ids=None)
        self.assertFalse(result["catalogAvailable"])
        self.assertEqual(result["staleCount"], 0)
        self.assertEqual(result["unverifiedStaleCandidateFamilyIds"], ["axion:bed:beds/a"])
        self.assertEqual(result["unverifiedStaleCandidateCount"], 1)

    def test_failed_refresh_is_flagged_only_when_old_package_still_exists(self):
        previous = build_source_index(self._report(results=[
            {"source": "D:/assets/windows/a.blend", "family_id": "axion:window:windows/a", "family_kind": "WINDOW"},
        ]))
        current = build_source_index(self._report(errors=[
            {
                "source": "D:/assets/windows/a.blend",
                "family_id": "axion:window:windows/a",
                "family_kind": "WINDOW",
                "error": "new conversion failed",
            },
        ]))
        present = compare_source_indexes(previous, current, catalog_family_ids={"axion:window:windows/a"})
        missing = compare_source_indexes(previous, current, catalog_family_ids=set())
        self.assertEqual(present["failedRefreshFamilyIds"], ["axion:window:windows/a"])
        self.assertEqual(present["failedRefreshCount"], 1)
        self.assertEqual(missing["failedRefreshFamilyIds"], [])


if __name__ == "__main__":
    unittest.main()
