import json
import tempfile
import unittest
from pathlib import Path

from catalog import _resolve_manifest_uri, build_library_index
from library_audit import _resolve_uri, audit_library


class ManifestPathSafetyTests(unittest.TestCase):
    def _escaped_manifest_link(self, root):
        outside = root.parent / "outside"
        outside.mkdir(parents=True, exist_ok=True)
        target = outside / "escaped.family.json"
        target.write_text(
            json.dumps({
                "schema": "axion.family",
                "schemaVersion": 2,
                "familyId": "axion:generic:escaped",
                "familyKind": "GENERIC",
                "name": "Escaped",
                "quality": {"automaticReady": True},
            }),
            encoding="utf-8",
        )
        link = root / "escaped.family.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Filesystem does not permit symlink fixture: {exc}")
        return link

    def _minimal_manifest(self, family_id, name):
        return {
            "schema": "axion.family",
            "schemaVersion": 2,
            "familyId": family_id,
            "familyKind": "GENERIC",
            "name": name,
            "quality": {"automaticReady": True},
        }

    def test_catalog_rejects_manifest_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "library"
            root.mkdir()
            self._escaped_manifest_link(root)

            _path, payload = build_library_index(root)
            self.assertEqual(payload["familyCount"], 0)
            self.assertEqual(len(payload["rejectedManifests"]), 1)
            self.assertIn("resolves outside library root", payload["rejectedManifests"][0]["error"])

    def test_library_audit_reports_manifest_symlink_escape_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "library"
            root.mkdir()
            self._escaped_manifest_link(root)

            payload = audit_library(root)
            self.assertFalse(payload["complete"])
            self.assertEqual(payload["validFamilyCount"], 0)
            self.assertEqual(payload["warningCounts"].get("UNSAFE_MANIFEST_PATH"), 1)
            self.assertEqual(payload["unsafeUriCount"], 1)

    def test_catalog_and_audit_reject_dot_segment_asset_uris(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            package = root / "family"
            package.mkdir(parents=True)
            manifest = package / "family.family.json"
            manifest.write_text("{}", encoding="utf-8")

            for uri in ("nested/../asset.glb", "./asset.glb", "nested/./asset.glb"):
                self.assertIsNone(_resolve_manifest_uri(manifest, root, uri), uri)
                self.assertIsNone(_resolve_uri(manifest, root, uri), uri)

            self.assertEqual(
                _resolve_manifest_uri(manifest, root, "nested/asset.glb"),
                "family/nested/asset.glb",
            )
            self.assertEqual(
                _resolve_uri(manifest, root, "nested/asset.glb"),
                package / "nested" / "asset.glb",
            )

    def test_recovery_manifests_are_not_published_but_block_clean_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            published = root / "generic" / "published"
            published.mkdir(parents=True)
            published_manifest = published / "published.family.json"
            published_manifest.write_text(
                json.dumps(self._minimal_manifest("axion:generic:published", "Published")),
                encoding="utf-8",
            )

            recovery = root / "generic" / ".bfc-package-recovery-test"
            staged = recovery / "package"
            backup = recovery / "__bfc_backup__"
            staged.mkdir(parents=True)
            backup.mkdir(parents=True)
            (staged / "staged.family.json").write_text(
                json.dumps(self._minimal_manifest("axion:generic:staged", "Staged Recovery")),
                encoding="utf-8",
            )
            (backup / "old.family.json").write_text(
                json.dumps(self._minimal_manifest("axion:generic:old", "Backup Recovery")),
                encoding="utf-8",
            )

            _catalog_path, catalog = build_library_index(root)
            self.assertEqual(catalog["familyCount"], 1)
            self.assertEqual(
                [item["familyId"] for item in catalog["families"]],
                ["axion:generic:published"],
            )

            audit = audit_library(root)
            self.assertEqual(audit["manifestCount"], 1)
            self.assertEqual(audit["validFamilyCount"], 1)
            self.assertEqual(audit["recoveryDirectoryCount"], 1)
            self.assertEqual(audit["warningCounts"].get("RECOVERY_DIRECTORY_PRESENT"), 1)
            self.assertFalse(audit["complete"])


if __name__ == "__main__":
    unittest.main()
