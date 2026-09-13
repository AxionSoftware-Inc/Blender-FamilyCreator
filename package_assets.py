"""Pure helpers for family-package managed asset references.

Only files referenced by the family manifest are considered managed package
assets. This lets transactional overwrite remove obsolete variants/LODs/
thumbnails without touching unrelated files placed next to the package.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath


PACKAGE_RECOVERY_PREFIX = ".bfc-package-"


def safe_relative_asset_uri(value):
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("\\", "/")
    if normalized.startswith("/"):
        return None
    first = normalized.split("/", 1)[0]
    if ":" in first:
        return None
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        return None
    return PurePosixPath(*parts).as_posix()


def is_internal_package_recovery_path(path, root):
    """Return True when a path lives inside a preserved package-recovery tree.

    Incomplete rollback intentionally keeps `.bfc-package-*` siblings on disk.
    Those files are recovery material, not published runtime packages, and must
    never be discovered as normal family manifests.
    """
    try:
        relative = Path(path).relative_to(Path(root))
    except (TypeError, ValueError):
        return False
    return any(str(part).startswith(PACKAGE_RECOVERY_PREFIX) for part in relative.parts)


def manifest_asset_uris(data):
    """Return safe relative runtime assets referenced by a family manifest."""
    if not isinstance(data, dict):
        return set()

    uris = set()

    variants = data.get("geometryVariants")
    if isinstance(variants, dict):
        for record in variants.values():
            if not isinstance(record, dict):
                continue
            uri = safe_relative_asset_uri(record.get("uri"))
            if uri:
                uris.add(uri)

    lods = data.get("geometryLods")
    if isinstance(lods, dict):
        for record in lods.values():
            if not isinstance(record, dict):
                continue
            uri = safe_relative_asset_uri(record.get("uri"))
            if uri:
                uris.add(uri)

    thumbnail = data.get("thumbnail")
    if isinstance(thumbnail, dict):
        uri = safe_relative_asset_uri(thumbnail.get("uri"))
        if uri:
            uris.add(uri)

    return uris
