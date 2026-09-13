import json
from collections import Counter
from pathlib import Path

from package_assets import safe_relative_asset_uri


CATALOG_SCHEMA = "axion.family.library"
CATALOG_VERSION = 1


def _lexical_relative_uri(path, root):
    try:
        return Path(path).relative_to(Path(root)).as_posix()
    except Exception:
        return str(path)


def _relative_uri(path, root):
    """Return the physical root-relative path, rejecting symlink escapes."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError):
        return None


def _resolve_manifest_uri(manifest_path, root, uri):
    safe_uri = safe_relative_asset_uri(uri)
    if safe_uri is None:
        return None
    resolved = (Path(manifest_path).parent / Path(safe_uri)).resolve()
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


def _resolve_asset(path, root, uri, warnings, asset_type, **extra):
    if not isinstance(uri, str) or not uri.strip():
        warnings.append(_asset_warning("INVALID_URI", asset_type, uri, **extra))
        return None
    resolved, resolved_path = _resolved_path(path, root, uri)
    if resolved is None:
        warnings.append(_asset_warning("UNSAFE_URI", asset_type, uri, **extra))
        return None
    if not resolved_path.is_file():
        warnings.append(_asset_warning("MISSING_FILE", asset_type, uri, **extra))
    return resolved


def _entry_from_manifest(path, root, data, manifest_relative=None):
    quality = data.get("quality", {}) if isinstance(data.get("quality"), dict) else {}
    profile = data.get("familyProfile", {}) if isinstance(data.get("familyProfile"), dict) else {}
    variants = data.get("geometryVariants", {}) if isinstance(data.get("geometryVariants"), dict) else {}
    materials = data.get("materials", []) if isinstance(data.get("materials"), list) else []
    warnings = []

    resolved_variants = {}
    for type_name, variant in variants.items():
        if not isinstance(type_name, str) or not isinstance(variant, dict):
            continue
        resolved = _resolve_asset(
            path,
            root,
            variant.get("uri"),
            warnings,
            "geometryVariant",
            typeName=type_name,
        )
        if resolved is not None:
            resolved_variants[type_name] = resolved

    resolved_lods = {}
    lods = data.get("geometryLods", {}) if isinstance(data.get("geometryLods"), dict) else {}
    for level, record in lods.items():
        if not isinstance(level, str) or not isinstance(record, dict):
            continue
        resolved = _resolve_asset(
            path,
            root,
            record.get("uri"),
            warnings,
            "lod",
            lodLevel=level,
        )
        if resolved is None:
            continue
        resolved_lods[level] = {
            "uri": resolved,
            "generated": bool(record.get("generated", False)),
            "triangles": int(record.get("triangles", 0) or 0),
        }
        if "targetTriangles" in record:
            resolved_lods[level]["targetTriangles"] = int(record.get("targetTriangles", 0) or 0)
        if "meetsTarget" in record:
            resolved_lods[level]["meetsTarget"] = bool(record.get("meetsTarget"))
        if record.get("aliasOf"):
            resolved_lods[level]["aliasOf"] = record.get("aliasOf")

    entry = {
        "familyId": data["familyId"],
        "name": data.get("name", ""),
        "familyKind": data.get("familyKind", "GENERIC"),
        "category": data.get("category", profile.get("category", "Generic Model")),
        "group": profile.get("group", "Generic"),
        "manifest": manifest_relative if manifest_relative is not None else _relative_uri(path, root),
        "activeType": data.get("activeType", "Default"),
        "typeNames": list(data.get("types", {}).keys()) if isinstance(data.get("types"), dict) else [],
        "dimensions": data.get("dimensions", {}),
        "automaticReady": bool(quality.get("automaticReady", False)),
        "qualityScore": int(quality.get("score", 0) or 0),
        "materialCount": len(materials),
        "geometryVariants": resolved_variants,
    }
    if resolved_lods:
        entry["geometryLods"] = resolved_lods

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
            "uniqueMaterials": int(runtime_cost.get("uniqueMaterials", 0) or 0),
            "drawCallEstimate": int(runtime_cost.get("drawCallEstimate", 0) or 0),
            "textureCount": int(runtime_cost.get("textureCount", 0) or 0),
            "maxTextureDimension": int(runtime_cost.get("maxTextureDimension", 0) or 0),
            "estimatedTextureMemoryMiB": round(
                float(runtime_cost.get("estimatedTextureMemoryMiB", 0.0) or 0.0),
                3,
            ),
            "memberCount": int(runtime_cost.get("memberCount", 0) or 0),
        }

    mobile_budget = data.get("mobileBudget")
    if isinstance(mobile_budget, dict):
        reasons = mobile_budget.get("optimizationReasons", [])
        if not isinstance(reasons, list):
            reasons = []
        entry["mobileBudget"] = {
            "policyVersion": int(mobile_budget.get("policyVersion", 0) or 0),
            "status": mobile_budget.get("status"),
            "sourceTriangles": int(mobile_budget.get("sourceTriangles", 0) or 0),
            "sourceDrawCallEstimate": int(mobile_budget.get("sourceDrawCallEstimate", 0) or 0),
            "sourceMaxTextureDimension": int(mobile_budget.get("sourceMaxTextureDimension", 0) or 0),
            "sourceTextureMemoryMiB": round(
                float(mobile_budget.get("sourceTextureMemoryMiB", 0.0) or 0.0),
                3,
            ),
            "optimizationReasons": [str(reason) for reason in reasons],
            "geometryLodRecommended": bool(mobile_budget.get("geometryLodRecommended", False)),
            "materialOptimizationRecommended": bool(
                mobile_budget.get("materialOptimizationRecommended", False)
            ),
            "textureOptimizationRecommended": bool(
                mobile_budget.get("textureOptimizationRecommended", False)
            ),
            "suggestedLod1Ratio": mobile_budget.get("suggestedLod1Ratio"),
            "suggestedLod2Ratio": mobile_budget.get("suggestedLod2Ratio"),
        }

    hosting = data.get("hosting")
    if isinstance(hosting, dict):
        entry["hostType"] = hosting.get("hostType")

    thumbnail = data.get("thumbnail")
    if isinstance(thumbnail, dict) and "uri" in thumbnail:
        resolved = _resolve_asset(path, root, thumbnail.get("uri"), warnings, "thumbnail")
        if resolved is not None:
            entry["thumbnail"] = resolved

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
        manifest_relative = _relative_uri(path, root)
        if manifest_relative is None:
            rejected.append({
                "manifest": _lexical_relative_uri(path, root),
                "error": "manifest resolves outside library root",
            })
            continue

        data, error = _load_manifest(path)
        if error:
            rejected.append({"manifest": manifest_relative, "error": error})
            continue

        family_id = data["familyId"]
        if family_id in ids:
            rejected.append({
                "manifest": manifest_relative,
                "error": f"duplicate familyId: {family_id}",
            })
            continue
        ids.add(family_id)
        entries.append(_entry_from_manifest(path, root, data, manifest_relative=manifest_relative))

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
    optimization_reason_counts = Counter(
        reason
        for item in entries
        for reason in ((item.get("mobileBudget") or {}).get("optimizationReasons") or [])
    )
    lod_recommended_count = sum(
        1 for item in entries if (item.get("mobileBudget") or {}).get("geometryLodRecommended")
    )
    material_optimization_count = sum(
        1
        for item in entries
        if (item.get("mobileBudget") or {}).get("materialOptimizationRecommended")
    )
    texture_optimization_count = sum(
        1
        for item in entries
        if (item.get("mobileBudget") or {}).get("textureOptimizationRecommended")
    )
    lod_family_count = sum(1 for item in entries if item.get("geometryLods"))

    runtime_costs = [item.get("runtimeCost") for item in entries if isinstance(item.get("runtimeCost"), dict)]
    total_triangles = sum(int(cost.get("triangles", 0) or 0) for cost in runtime_costs)
    total_draw_calls = sum(int(cost.get("drawCallEstimate", 0) or 0) for cost in runtime_costs)
    total_texture_memory = sum(float(cost.get("estimatedTextureMemoryMiB", 0.0) or 0.0) for cost in runtime_costs)
    max_family_triangles = max((int(cost.get("triangles", 0) or 0) for cost in runtime_costs), default=0)
    max_family_draw_calls = max((int(cost.get("drawCallEstimate", 0) or 0) for cost in runtime_costs), default=0)
    max_texture_dimension = max((int(cost.get("maxTextureDimension", 0) or 0) for cost in runtime_costs), default=0)
    max_family_texture_memory = max(
        (float(cost.get("estimatedTextureMemoryMiB", 0.0) or 0.0) for cost in runtime_costs),
        default=0.0,
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
        "familiesWithLods": lod_family_count,
        "mobileBudgetStatusCounts": dict(sorted(mobile_status_counts.items())),
        "mobileOptimizationReasonCounts": dict(sorted(optimization_reason_counts.items())),
        "familiesRecommendedForGeometryLod": lod_recommended_count,
        "familiesRecommendedForMaterialOptimization": material_optimization_count,
        "familiesRecommendedForTextureOptimization": texture_optimization_count,
        "familiesOverMobileTarget": int(mobile_status_counts.get("OVER_TARGET", 0)),
        "familiesOverMobileHardLimit": int(mobile_status_counts.get("OVER_HARD_LIMIT", 0)),
        "runtimeCostSummary": {
            "measuredFamilies": len(runtime_costs),
            "totalTriangles": total_triangles,
            "maxFamilyTriangles": max_family_triangles,
            "totalDrawCallEstimate": total_draw_calls,
            "maxFamilyDrawCallEstimate": max_family_draw_calls,
            "totalEstimatedTextureMemoryMiB": round(total_texture_memory, 3),
            "maxFamilyEstimatedTextureMemoryMiB": round(max_family_texture_memory, 3),
            "maxTextureDimension": max_texture_dimension,
        },
        "families": entries,
        "rejectedManifests": rejected,
    }

    path = root / "library-index.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path, payload
