import json
from collections import Counter
from pathlib import Path

try:
    from .package_assets import PACKAGE_RECOVERY_PREFIX, safe_relative_asset_uri
except ImportError:  # Pure-Python tests import this module from repo root.
    from package_assets import PACKAGE_RECOVERY_PREFIX, safe_relative_asset_uri


AUDIT_SCHEMA = "axion.family.library.audit"
AUDIT_VERSION = 1


def _lexical_relative(path, root):
    try:
        return Path(path).relative_to(Path(root)).as_posix()
    except Exception:
        return str(path)


def _relative(path, root):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError):
        return None


def _inside_recovery_tree(path, root):
    try:
        relative = Path(path).relative_to(Path(root))
    except ValueError:
        return False
    return any(str(part).startswith(PACKAGE_RECOVERY_PREFIX) for part in relative.parts)


def _recovery_directories(root):
    return sorted(
        path
        for path in Path(root).rglob(f"{PACKAGE_RECOVERY_PREFIX}*")
        if path.is_dir()
    )


def _resolve_uri(manifest_path, root, uri):
    safe_uri = safe_relative_asset_uri(uri)
    if safe_uri is None:
        return None
    resolved = (Path(manifest_path).parent / Path(safe_uri)).resolve()
    try:
        resolved.relative_to(Path(root).resolve())
    except ValueError:
        return None
    return resolved


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def _warning(code, manifest, **extra):
    item = {"code": code, "manifest": manifest}
    item.update(extra)
    return item


def _check_uri(manifest_path, root, manifest_rel, uri, *, kind, label=None):
    label_fields = {"label": str(label)} if label is not None else {}
    upper = str(kind).upper()
    if not isinstance(uri, str) or not uri.strip():
        return _warning(f"INVALID_{upper}_URI", manifest_rel, uri=uri, **label_fields)
    resolved = _resolve_uri(manifest_path, root, uri)
    if resolved is None:
        return _warning(f"UNSAFE_{upper}_URI", manifest_rel, uri=uri, **label_fields)
    if not resolved.is_file():
        return _warning(f"MISSING_{upper}_FILE", manifest_rel, uri=uri, **label_fields)
    return None


def _manifest_asset_warnings(manifest_path, root, data):
    manifest_rel = _relative(manifest_path, root)
    if manifest_rel is None:
        return [_warning("UNSAFE_MANIFEST_PATH", _lexical_relative(manifest_path, root))]
    warnings = []

    variants = data.get("geometryVariants", {}) if isinstance(data.get("geometryVariants"), dict) else {}
    for type_name, variant in variants.items():
        if not isinstance(variant, dict):
            continue
        warning = _check_uri(
            manifest_path,
            root,
            manifest_rel,
            variant.get("uri"),
            kind="GEOMETRY",
            label=type_name,
        )
        if warning:
            warning["typeName"] = str(type_name)
            warnings.append(warning)

    lods = data.get("geometryLods", {}) if isinstance(data.get("geometryLods"), dict) else {}
    for level, record in lods.items():
        if not isinstance(record, dict):
            continue
        warning = _check_uri(
            manifest_path,
            root,
            manifest_rel,
            record.get("uri"),
            kind="LOD",
            label=level,
        )
        if warning:
            warning["lodLevel"] = str(level)
            warnings.append(warning)

    thumbnail = data.get("thumbnail")
    if isinstance(thumbnail, dict) and "uri" in thumbnail:
        warning = _check_uri(
            manifest_path,
            root,
            manifest_rel,
            thumbnail.get("uri"),
            kind="THUMBNAIL",
        )
        if warning:
            warnings.append(warning)

    return warnings


def audit_library(root_directory):
    root = Path(root_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)

    recovery_directories = _recovery_directories(root)
    manifests = sorted(
        path
        for path in root.rglob("*.family.json")
        if path.is_file() and not _inside_recovery_tree(path, root)
    )
    warnings = [
        _warning(
            "RECOVERY_DIRECTORY_PRESENT",
            "",
            path=_lexical_relative(path, root),
        )
        for path in recovery_directories
    ]
    families = []
    ids = {}

    for manifest_path in manifests:
        manifest_rel = _relative(manifest_path, root)
        if manifest_rel is None:
            warnings.append(_warning(
                "UNSAFE_MANIFEST_PATH",
                _lexical_relative(manifest_path, root),
            ))
            continue

        data, error = _load_json(manifest_path)
        if error:
            warnings.append(_warning("INVALID_MANIFEST_JSON", manifest_rel, detail=error))
            continue
        if not isinstance(data, dict):
            warnings.append(_warning("INVALID_MANIFEST_ROOT", manifest_rel))
            continue
        if data.get("schema") != "axion.family" or data.get("schemaVersion") != 2:
            warnings.append(_warning("UNSUPPORTED_MANIFEST_SCHEMA", manifest_rel))
            continue

        family_id = data.get("familyId")
        if not isinstance(family_id, str) or not family_id.strip():
            warnings.append(_warning("MISSING_FAMILY_ID", manifest_rel))
            continue

        if family_id in ids:
            warnings.append(_warning(
                "DUPLICATE_FAMILY_ID",
                manifest_rel,
                familyId=family_id,
                firstManifest=ids[family_id],
            ))
        else:
            ids[family_id] = manifest_rel

        asset_warnings = _manifest_asset_warnings(manifest_path, root, data)
        warnings.extend(asset_warnings)
        families.append({
            "familyId": family_id,
            "manifest": manifest_rel,
            "familyKind": data.get("familyKind", "GENERIC"),
            "automaticReady": bool((data.get("quality") or {}).get("automaticReady", False)),
            "assetWarnings": asset_warnings,
            "assetsComplete": not asset_warnings,
        })

    warning_counts = Counter(item["code"] for item in warnings)
    missing_file_count = sum(
        count for code, count in warning_counts.items()
        if code in {"MISSING_GEOMETRY_FILE", "MISSING_LOD_FILE", "MISSING_THUMBNAIL_FILE"}
    )
    unsafe_uri_count = sum(
        count for code, count in warning_counts.items()
        if code in {
            "UNSAFE_MANIFEST_PATH",
            "UNSAFE_GEOMETRY_URI",
            "UNSAFE_LOD_URI",
            "UNSAFE_THUMBNAIL_URI",
        }
    )

    payload = {
        "schema": AUDIT_SCHEMA,
        "schemaVersion": AUDIT_VERSION,
        "root": str(root),
        "manifestCount": len(manifests),
        "validFamilyCount": len(families),
        "familyIdsUnique": len(ids),
        "recoveryDirectoryCount": len(recovery_directories),
        "familiesWithAssetWarnings": sum(1 for item in families if item["assetWarnings"]),
        "assetWarningCount": sum(len(item["assetWarnings"]) for item in families),
        "missingAssetCount": missing_file_count,
        "unsafeUriCount": unsafe_uri_count,
        "warningCount": len(warnings),
        "warningCounts": dict(sorted(warning_counts.items())),
        "complete": len(warnings) == 0,
        "families": families,
        "warnings": warnings,
    }
    return payload


def write_library_audit(root_directory, filename="library-audit.json"):
    root = Path(root_directory).resolve()
    payload = audit_library(root)
    path = root / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path, payload
