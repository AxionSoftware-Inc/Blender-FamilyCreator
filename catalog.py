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


def _entry_from_manifest(path, root, data):
    quality = data.get("quality", {}) if isinstance(data.get("quality"), dict) else {}
    profile = data.get("familyProfile", {}) if isinstance(data.get("familyProfile"), dict) else {}
    variants = data.get("geometryVariants", {}) if isinstance(data.get("geometryVariants"), dict) else {}
    materials = data.get("materials", []) if isinstance(data.get("materials"), list) else []

    resolved_variants = {}
    for type_name, variant in variants.items():
        if not isinstance(type_name, str) or not isinstance(variant, dict):
            continue
        uri = variant.get("uri")
        if not isinstance(uri, str):
            continue
        resolved = _resolve_manifest_uri(path, root, uri)
        if resolved is not None:
            resolved_variants[type_name] = resolved

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

    hosting = data.get("hosting")
    if isinstance(hosting, dict):
        entry["hostType"] = hosting.get("hostType")

    thumbnail = data.get("thumbnail")
    if isinstance(thumbnail, dict) and isinstance(thumbnail.get("uri"), str):
        resolved_thumbnail = _resolve_manifest_uri(path, root, thumbnail.get("uri"))
        if resolved_thumbnail is not None:
            entry["thumbnail"] = resolved_thumbnail

    source = data.get("source")
    if isinstance(source, dict) and source.get("key"):
        entry["sourceKey"] = source.get("key")
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

    payload = {
        "schema": CATALOG_SCHEMA,
        "schemaVersion": CATALOG_VERSION,
        "familyCount": len(entries),
        "automaticReady": ready_count,
        "needsReview": len(entries) - ready_count,
        "classCounts": dict(sorted(class_counts.items())),
        "families": entries,
        "rejectedManifests": rejected,
    }

    path = root / "library-index.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path, payload
