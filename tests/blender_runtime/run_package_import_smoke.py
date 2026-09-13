"""GPU-free smoke for installed-package import semantics.

The repository's pure-Python tests import some helpers as top-level modules, but
Blender installs the addon as a package. This smoke removes the repository root
from sys.path and changes cwd before loading the addon, so local helper imports
must resolve through package-relative imports rather than an accidental working-
directory lookup.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_package_import_smoke"


def _resolved_entry(value):
    try:
        return Path(value or ".").resolve()
    except Exception:
        return None


def main():
    original_cwd = Path.cwd()
    original_sys_path = list(sys.path)
    addon = None

    # Avoid false positives from an earlier accidental top-level import.
    for name in ("package_assets", "catalog", "library_audit"):
        sys.modules.pop(name, None)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            sys.path[:] = [
                entry
                for entry in original_sys_path
                if _resolved_entry(entry) != REPO_ROOT
            ]

            spec = importlib.util.spec_from_file_location(
                ADDON_NAME,
                REPO_ROOT / "__init__.py",
                submodule_search_locations=[str(REPO_ROOT)],
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("Could not build addon package import spec")

            addon = importlib.util.module_from_spec(spec)
            sys.modules[ADDON_NAME] = addon
            spec.loader.exec_module(addon)

            catalog = importlib.import_module(f"{ADDON_NAME}.catalog")
            audit = importlib.import_module(f"{ADDON_NAME}.library_audit")
            package_assets = importlib.import_module(f"{ADDON_NAME}.package_assets")

            if catalog.safe_relative_asset_uri is not package_assets.safe_relative_asset_uri:
                raise AssertionError("catalog did not resolve package-relative package_assets")
            if audit.safe_relative_asset_uri is not package_assets.safe_relative_asset_uri:
                raise AssertionError("library_audit did not resolve package-relative package_assets")
            if "package_assets" in sys.modules:
                raise AssertionError("Top-level package_assets leaked into installed-package import mode")

            addon.register()
            addon.unregister()
            addon = None

        print("PACKAGE_IMPORT_SMOKE: PASS")
    finally:
        if addon is not None:
            try:
                addon.unregister()
            except Exception:
                pass
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path
        for name in list(sys.modules):
            if name == ADDON_NAME or name.startswith(ADDON_NAME + "."):
                sys.modules.pop(name, None)


if __name__ == "__main__":
    main()
