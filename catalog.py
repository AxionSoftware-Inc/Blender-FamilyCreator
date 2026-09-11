import json
from collections import Counter
from pathlib import Path


CATALOG_SCHEMA = "axion.family.library"
CATALOG_VERSION = 1


def _relative_uri(path, root):
    return Path(path).relative_to(root).as_posix()


def _resolve_manifest_uri(manifest_path, root, uri):
    uri_path = Path(str(uri))
    if uri_path.is_absolute():
        return None
    resolved = (Path(manifest_path).parent / uri_path).resolve()
    try:
        return resolved.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None


def _resolved_path(manifest_path, root, uri):
    relative = _resolve_manifest_uri(manifest_path, root, uri)
    if relative is None:
        return None, None
    return relative, Path(root).resolve() / relative


def _load_manifest(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "manifest root is not an object"
    if data.get("schema") != "axion.family" or data.get("schemaVersion") != 2:
        return None, "unsupported family manifest schema"
    family_id = data.get("familyId")
    if not isinstance(family_id, str) or not family_id.strip():
        return None, "familyId missing"
    return data, None


def _asset_warning(code, asset_type, uri, **extra):
    warning = {"code": code, "assetType": asset_type, "uri": uri}
    warning.update(extra)
    return warning


def _entry_from_manifest(path, root, data):
    quality = data.get("quality", {}) if isinstance(data.get("quality"), dict) else {}
    profile = data.get("familyProfile", {}) if isinstance(data.get("familyProfile"), dict) else {}
    variants = data.get("geometryVariants", {}) if isinstance(data.get("geometryVariants"), dict) else {}
    materials = data.get("materials", []) if isinstance(data.get("materials"), list) else []
    warnings = []

    resolved_variants = {}
    for type_name, variant in variants.items():
        if not isinstance(type_name, str) or not isinstance(variant, dict):
            continue
        uri = variant.get("uri")
        if not isinstance(uri, str) or not uri.strip():
            warnings.append(_asset_warning("INVALID_URI", "geometryVariant", uri, typeName=type_name))
            continue
        resolved, resolved_path = _resolved_path(path, root, uri)
        if resolved is None:
            warnings.append(_asset_warning("UNSAFE_URI", "geometryVariant", uri, typeName=type_name))
            continue
        resolved_variants[type_name] = resolved
        if not resolved_path.is_file():
            warnings.append(_asset_warning("MISSING_FILE", "geometryVariant", uri, typeName=type_name))

    entry = {
        "familyId": data["familyId"],
        "name": data.get("name", ""),
        "familyKind": data.get("familyKind", "GENERIC"),
        "category": data.get("category", profile.get("category", "Generic Model")),
        "group": profile.get("group", "Generic"),
        "manifest": _relative_uri(path, root),
        "activeType": data.get("activeType", "Default"),
        "typeNames": list(data.get("types", {}).keys()) if isinstance(data.get("types"), dict) else [],
        "dimensions": data.get("dimensions", {}),
        "automaticReady": bool(quality.get("automaticReady", False)),
        "qualityScore": int(quality.get("score", 0) or 0),
        "materialCount": len(materials),
        "geometryVariants": resolved_variants,
    }

    runtime_proxy = data.get("runtimeProxy")
    if isinstance(runtime_proxy, dict):
        selection = runtime_proxy.get("selection")
        if isinstance(selection, dict) and isinstance(selection.get("size"), list):
            entry["proxySize"] = selection.get("size")
        footprint = runtime_proxy.get("planFootprint")
        if isinstance(footprint, dict):
            entry["planFootprint"] = {
                "min": footprint.get("min"),
                "max": footprint.get("max"),
            }

    runtime_cost = data.get("runtimeCost")
    if isinstance(runtime_cost, dict):
        entry["runtimeCost"] = {
            "triangles": int(runtime_cost.get("triangles", 0) or 0),
            "vertices": int(runtime_cost.get("vertices", 0) or 0),
            "materialSlots": int(runtime_cost.get("materialSlots", 0) or 0),
            "memberCount": int(runtime_cost.get("memberCount", 0) or 0),
        }

    mobile_budget = data.get("mobileBudget")
    if isinstance(mobile_budget, dict):
        entry["mobileBudget"] = {
            "status": mobile_budget.get("status"),
            "suggestedLod1Ratio": mobile_budget.get("suggestedLod1Ratio"),
            "suggestedLod2Ratio": mobile_budget.get("suggestedLod2Ratio"),
        }

    hosting = data.get("hosting")
    if isinstance(hosting, dict):
        entry["hostType"] = hosting.get("hostType")

    thumbnail = data.get("thumbnail")
    if isinstance(thumbnail, dict) and "uri" in thumbnail:
        uri = thumbnail.get("uri")
        if not isinstance(uri, str) or not uri.strip():
            warnings.append(_asset_warning("INVALID_URI", "thumbnail", uri))
        else:
            resolved, resolved_path = _resolved_path(path, root, uri)
            if resolved is None:
                warnings.append(_asset_warning("UNSAFE_URI", "thumbnail", uri))
            else:
                entry["thumbnail"] = resolved
                if not resolved_path.is_file():
                    warnings.append(_asset_warning("MISSING_FILE", "thumbnail", uri))

    source = data.get("source")
    if isinstance(source, dict) and source.get("key"):
        entry["sourceKey"] = source.get("key")

    entry["assetsComplete"] = not warnings
    if warnings:
        entry["assetWarnings"] = warnings
    return entry


def discover_family_manifests(root_directory):
    root = Path(root_directory)
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.family.json") if path.is_file())


def build_library_index(root_directory):
    root = Path(root_directory)
    root.mkdir(parents=True, exist_ok=True)

    entries = []
    rejected = []
    ids = set()
    for path in discover_family_manifests(root):
        data, error = _load_manifest(path)
        if error:
            rejected.append({"manifest": _relative_uri(path, root), "error": error})
            continue

        family_id = data["familyId"]
        if family_id in ids:
            rejected.append({
                "manifest": _relative_uri(path, root),
                "error": f"duplicate familyId: {family_id}",
            })
            continue
        ids.add(family_id)
        entries.append(_entry_from_manifest(path, root, data))

    entries.sort(key=lambda item: (item.get("familyKind", ""), item.get("name", "").lower(), item["familyId"]))
    class_counts = Counter(item.get("familyKind", "GENERIC") for item in entries)
    ready_count = sum(1 for item in entries if item.get("automaticReady"))
    asset_warnings = [warning for item in entries for warning in item.get("assetWarnings", [])]
    missing_asset_count = sum(1 for warning in asset_warnings if warning.get("code") == "MISSING_FILE")
    mobile_status_counts = Counter(
        (item.get("mobileBudget") or {}).get("status")
        for item in entries
        if (item.get("mobileBudget") or {}).get("status")
    )

    payload = {
        "schema": CATALOG_SCHEMA,
        "schemaVersion": CATALOG_VERSION,
        "familyCount": len(entries),
        "automaticReady": ready_count,
        "needsReview": len(entries) - ready_count,
        "classCounts": dict(sorted(class_counts.items())),
        "assetWarningCount": len(asset_warnings),
        "missingAssetCount": missing_asset_count,
        "familiesWithAssetWarnings": sum(1 for item in entries if item.get("assetWarnings")),
        "mobileBudgetStatusCounts": dict(sorted(mobile_status_counts.items())),
        "families": entries,
        "rejectedManifests": rejected,
    }

    path = root / "library-index.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path, payload
