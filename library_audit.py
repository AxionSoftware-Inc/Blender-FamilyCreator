import json
from collections import Counter
from pathlib import Path


AUDIT_SCHEMA = "axion.family.library.audit"
AUDIT_VERSION = 1


def _relative(path, root):
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def _resolve_uri(manifest_path, root, uri):
    try:
        uri_path = Path(str(uri))
    except Exception:
        return None
    if uri_path.is_absolute():
        return None
    resolved = (Path(manifest_path).parent / uri_path).resolve()
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


def _manifest_asset_warnings(manifest_path, root, data):
    manifest_rel = _relative(manifest_path, root)
    warnings = []

    variants = data.get("geometryVariants", {}) if isinstance(data.get("geometryVariants"), dict) else {}
    for type_name, variant in variants.items():
        if not isinstance(variant, dict):
            continue
        uri = variant.get("uri")
        if not isinstance(uri, str) or not uri.strip():
            warnings.append(_warning(
                "INVALID_GEOMETRY_URI",
                manifest_rel,
                typeName=str(type_name),
                uri=uri,
            ))
            continue
        resolved = _resolve_uri(manifest_path, root, uri)
        if resolved is None:
            warnings.append(_warning(
                "UNSAFE_GEOMETRY_URI",
                manifest_rel,
                typeName=str(type_name),
                uri=uri,
            ))
        elif not resolved.is_file():
            warnings.append(_warning(
                "MISSING_GEOMETRY_FILE",
                manifest_rel,
                typeName=str(type_name),
                uri=uri,
            ))

    thumbnail = data.get("thumbnail")
    if isinstance(thumbnail, dict) and "uri" in thumbnail:
        uri = thumbnail.get("uri")
        if not isinstance(uri, str) or not uri.strip():
            warnings.append(_warning("INVALID_THUMBNAIL_URI", manifest_rel, uri=uri))
        else:
            resolved = _resolve_uri(manifest_path, root, uri)
            if resolved is None:
                warnings.append(_warning("UNSAFE_THUMBNAIL_URI", manifest_rel, uri=uri))
            elif not resolved.is_file():
                warnings.append(_warning("MISSING_THUMBNAIL_FILE", manifest_rel, uri=uri))

    return warnings


def audit_library(root_directory):
    root = Path(root_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)

    manifests = sorted(path for path in root.rglob("*.family.json") if path.is_file())
    warnings = []
    families = []
    ids = {}

    for manifest_path in manifests:
        manifest_rel = _relative(manifest_path, root)
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
        if code in {"MISSING_GEOMETRY_FILE", "MISSING_THUMBNAIL_FILE"}
    )
    unsafe_uri_count = sum(
        count for code, count in warning_counts.items()
        if code in {"UNSAFE_GEOMETRY_URI", "UNSAFE_THUMBNAIL_URI"}
    )

    payload = {
        "schema": AUDIT_SCHEMA,
        "schemaVersion": AUDIT_VERSION,
        "root": str(root),
        "manifestCount": len(manifests),
        "validFamilyCount": len(families),
        "familyIdsUnique": len(ids),
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
