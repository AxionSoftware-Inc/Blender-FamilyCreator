import json
import tempfile
import unittest
from pathlib import Path

from batch_source_index import (
    SOURCE_INDEX_SCHEMA,
    SOURCE_REGISTRY_VERSION,
    build_source_index,
    compare_source_indexes,
    load_source_index,
    source_index_scope_matches,
    write_source_index,
)


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

    def test_registry_preserves_scope_history_across_alternating_jobs(self):
        scope_a_first = build_source_index(self._report(
            input_directory="D:/assets-a",
            family_kind="AUTO_FOLDER",
            results=[
                {"source": "D:/assets-a/beds/a.blend", "family_id": "axion:bed:beds/a", "family_kind": "BED"},
                {"source": "D:/assets-a/beds/b.blend", "family_id": "axion:bed:beds/b", "family_kind": "BED"},
            ],
        ))
        scope_b = build_source_index(self._report(
            input_directory="D:/assets-b",
            family_kind="WINDOW",
            results=[
                {"source": "D:/assets-b/window.blend", "family_id": "axion:window:window", "family_kind": "WINDOW"},
            ],
        ))
        scope_a_second = build_source_index(self._report(
            input_directory="D:/assets-a",
            family_kind="AUTO_FOLDER",
            results=[
                {"source": "D:/assets-a/beds/a.blend", "family_id": "axion:bed:beds/a", "family_kind": "BED"},
            ],
        ))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_source_index(root, scope_a_first)
            registry = load_source_index(path)
            self.assertEqual(registry["schema"], SOURCE_INDEX_SCHEMA)
            self.assertEqual(registry["schemaVersion"], SOURCE_REGISTRY_VERSION)
            self.assertEqual(registry["scopeCount"], 1)

            write_source_index(root, scope_b)
            registry = load_source_index(path)
            self.assertEqual(registry["scopeCount"], 2)

            result = compare_source_indexes(
                registry,
                scope_a_second,
                catalog_family_ids={"axion:bed:beds/a", "axion:bed:beds/b", "axion:window:window"},
            )
            self.assertTrue(result["comparable"])
            self.assertEqual(result["staleFamilyIds"], ["axion:bed:beds/b"])

            write_source_index(root, scope_a_second)
            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(updated["scopeCount"], 2)
            matching_a = [
                scope for scope in updated["scopes"]
                if scope.get("inputDirectory") == "D:/assets-a"
            ]
            self.assertEqual(len(matching_a), 1)
            self.assertEqual(matching_a[0]["sourceCount"], 1)

    def test_legacy_v1_file_is_upgraded_without_losing_old_scope(self):
        legacy = build_source_index(self._report(
            input_directory="D:/legacy",
            family_kind="BED",
            results=[{"source": "D:/legacy/a.blend", "family_id": "axion:bed:a", "family_kind": "BED"}],
        ))
        current = build_source_index(self._report(
            input_directory="D:/current",
            family_kind="WINDOW",
            results=[{"source": "D:/current/a.blend", "family_id": "axion:window:a", "family_kind": "WINDOW"}],
        ))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "batch-source-index.json"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            write_source_index(root, current)
            registry = load_source_index(path)
            self.assertEqual(registry["schemaVersion"], SOURCE_REGISTRY_VERSION)
            self.assertEqual(registry["scopeCount"], 2)
            self.assertTrue(compare_source_indexes(registry, legacy, catalog_family_ids={"axion:bed:a"})["comparable"])
            self.assertTrue(compare_source_indexes(registry, current, catalog_family_ids={"axion:window:a"})["comparable"])


if __name__ == "__main__":
    unittest.main()
