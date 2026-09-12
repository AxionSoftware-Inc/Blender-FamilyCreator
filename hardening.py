from collections import Counter, defaultdict
from pathlib import Path


HARDENING_SCHEMA = "axion.family.hardening"
HARDENING_VERSION = 1


def _source_format(source):
    suffix = Path(str(source or "")).suffix.lower().lstrip(".")
    return suffix.upper() if suffix else "UNKNOWN"


def _reason(code, detail=None):
    return code if not detail else f"{code}:{detail}"


def _reason_code(reason):
    return str(reason).split(":", 1)[0]


def _generator_reason(generator):
    if not isinstance(generator, dict):
        return None
    if not generator.get("supported") or generator.get("changed", True):
        return None

    reason_code = str(generator.get("reasonCode", "") or "").strip().upper()
    if reason_code == "NO_SEPARATE_FRAME":
        return None
    if reason_code == "PARAMETER_AUTO":
        return "GENERATOR_PARAMETER_AUTO"
    if reason_code == "NO_EFFECT":
        return "GENERATOR_NO_CHANGE"

    message = str(generator.get("message", "") or "").strip().lower()
    has_auto = "auto/zero" in message or "auto or zero" in message
    has_missing_semantics = (
        ("no " in message and " member" in message)
        or "roles were not detected" in message
        or "role was not detected" in message
        or "role not detected" in message
    )
    if has_auto and has_missing_semantics:
        return "GENERATOR_AUTO_OR_MISSING_SEMANTICS"
    if has_missing_semantics:
        return "GENERATOR_MISSING_SEMANTICS"
    if has_auto:
        return "GENERATOR_PARAMETER_AUTO"
    return "GENERATOR_NO_CHANGE"


def review_reasons(item):
    quality = item.get("quality", {}) if isinstance(item.get("quality"), dict) else {}
    reasons = []

    coverage = float(quality.get("roleCoverage", 0.0) or 0.0)
    if coverage < 0.80:
        reasons.append("LOW_ROLE_COVERAGE")

    for group in quality.get("missingRoleGroups", ()) or ():
        if isinstance(group, (list, tuple)):
            detail = "|".join(str(value) for value in group)
        else:
            detail = str(group)
        reasons.append(_reason("MISSING_REQUIRED_ROLE", detail))

    for group in quality.get("missingRecommendedRoleGroups", ()) or ():
        if isinstance(group, (list, tuple)):
            detail = "|".join(str(value) for value in group)
        else:
            detail = str(group)
        reasons.append(_reason("MISSING_RECOMMENDED_ROLE", detail))

    preflight = quality.get("preflight", {}) if isinstance(quality.get("preflight"), dict) else {}
    stats = preflight.get("stats", {}) if isinstance(preflight.get("stats"), dict) else {}
    if int(stats.get("nonUniformScaleMembers", 0) or 0) > 0:
        reasons.append("NON_UNIFORM_SCALE")
    elif int(stats.get("nonUnitScaleMembers", 0) or 0) > 0:
        reasons.append("UNAPPLIED_SCALE")
    if int(stats.get("shearedTransformMembers", 0) or 0) > 0:
        reasons.append("SHEARED_TRANSFORM")
    if int(stats.get("negativeDeterminantMembers", 0) or 0) > 0:
        reasons.append("MIRRORED_TRANSFORM")
    if int(stats.get("shapeKeyMembers", 0) or 0) > 0:
        reasons.append("SHAPE_KEYS")
    if int(stats.get("armatureMembers", 0) or 0) > 0:
        reasons.append("ARMATURE")

    generic_share = float(stats.get("genericNameShare", 0.0) or 0.0)
    if coverage < 0.80 and generic_share >= 0.50:
        reasons.append("GENERIC_OBJECT_NAMES")
    if bool(stats.get("mixedSceneNameHint", False)):
        reasons.append("MIXED_SCENE_SUSPECTED")

    preflight_messages = list(preflight.get("warnings", ()) or ()) + list(preflight.get("severe", ()) or ())
    lowered = "\n".join(str(message).lower() for message in preflight_messages)
    if "heavy source geometry" in lowered:
        reasons.append("HEAVY_GEOMETRY")
    if "check source units" in lowered or "check source units/orientation" in lowered:
        reasons.append("SUSPICIOUS_UNITS_OR_ORIENTATION")

    if item.get("export_warnings"):
        reasons.append("EXPORT_WARNING")

    generator_reason = _generator_reason(item.get("generator"))
    if generator_reason:
        reasons.append(generator_reason)

    return sorted(set(reasons))


def _rounded_average(total, count):
    return round(float(total) / float(count), 4) if count else 0.0


def _generator_diagnostic(generator):
    if not isinstance(generator, dict):
        return None
    return {
        "supported": bool(generator.get("supported", False)),
        "changed": bool(generator.get("changed", False)),
        "reasonCode": str(generator.get("reasonCode", "") or "") or None,
        "message": str(generator.get("message", "") or ""),
    }


def build_hardening_report(report):
    results = list(report.get("results", ()) or ())
    errors = list(report.get("errors", ()) or ())

    by_class = defaultdict(lambda: {
        "discovered": 0,
        "converted": 0,
        "failed": 0,
        "automaticReady": 0,
        "needsReview": 0,
        "scoreTotal": 0.0,
        "coverageTotal": 0.0,
        "genericNameShareTotal": 0.0,
    })
    by_format = defaultdict(lambda: {
        "discovered": 0,
        "converted": 0,
        "failed": 0,
        "automaticReady": 0,
        "needsReview": 0,
    })
    reason_counts = Counter()
    compact_reason_counts = Counter()
    refinement_counts = Counter()
    reason_examples = defaultdict(list)
    asset_summaries = []

    for item in results:
        family_kind = str(item.get("family_kind", "GENERIC") or "GENERIC")
        quality = item.get("quality", {}) if isinstance(item.get("quality"), dict) else {}
        automatic_ready = bool(quality.get("automaticReady", False))
        source = item.get("source")
        source_format = _source_format(source)
        preflight = quality.get("preflight", {}) if isinstance(quality.get("preflight"), dict) else {}
        preflight_stats = preflight.get("stats", {}) if isinstance(preflight.get("stats"), dict) else {}
        role_refinements = quality.get("roleRefinementCounts", {})
        if not isinstance(role_refinements, dict):
            role_refinements = {}
        semantic_capabilities = quality.get("semanticCapabilities", {})
        if not isinstance(semantic_capabilities, dict):
            semantic_capabilities = {}
        unknown_samples = quality.get("unknownMemberSamples", [])
        if not isinstance(unknown_samples, list):
            unknown_samples = []

        class_stats = by_class[family_kind]
        class_stats["discovered"] += 1
        class_stats["converted"] += 1
        class_stats["automaticReady"] += int(automatic_ready)
        class_stats["needsReview"] += int(not automatic_ready)
        class_stats["scoreTotal"] += float(quality.get("score", 0) or 0)
        class_stats["coverageTotal"] += float(quality.get("roleCoverage", 0.0) or 0.0)
        class_stats["genericNameShareTotal"] += float(preflight_stats.get("genericNameShare", 0.0) or 0.0)

        format_stats = by_format[source_format]
        format_stats["discovered"] += 1
        format_stats["converted"] += 1
        format_stats["automaticReady"] += int(automatic_ready)
        format_stats["needsReview"] += int(not automatic_ready)

        for refinement, count in role_refinements.items():
            try:
                refinement_counts[str(refinement)] += int(count)
            except Exception:
                continue

        item_reasons = review_reasons(item)
        compact_reasons = sorted({_reason_code(reason) for reason in item_reasons})
        asset_summaries.append({
            "source": str(source or ""),
            "format": source_format.lower(),
            "familyKind": family_kind,
            "converted": True,
            "automaticReady": automatic_ready,
            "score": int(quality.get("score", 0) or 0),
            "roleCoverage": float(quality.get("roleCoverage", 0.0) or 0.0),
            "roleRefinements": dict(sorted((str(key), int(value)) for key, value in role_refinements.items())),
            "semanticCapabilities": dict(sorted((str(key), bool(value)) for key, value in semantic_capabilities.items())),
            "unknownMemberSamples": unknown_samples[:12],
            "generator": _generator_diagnostic(item.get("generator")),
            "reasons": compact_reasons,
            "detailedReasons": item_reasons,
        })

        for reason in item_reasons:
            reason_counts[reason] += 1
            compact_reason_counts[_reason_code(reason)] += 1
            if len(reason_examples[reason]) < 5:
                reason_examples[reason].append(str(source or item.get("family") or ""))

    for error in errors:
        source = error.get("source") if isinstance(error, dict) else None
        source_format = _source_format(source)
        family_kind = ""
        if isinstance(error, dict):
            family_kind = str(error.get("family_kind", "") or "").upper()

        if family_kind:
            class_stats = by_class[family_kind]
            class_stats["discovered"] += 1
            class_stats["failed"] += 1

        by_format[source_format]["discovered"] += 1
        by_format[source_format]["failed"] += 1
        reason_counts["CONVERSION_FAILED"] += 1
        compact_reason_counts["CONVERSION_FAILED"] += 1
        if len(reason_examples["CONVERSION_FAILED"]) < 5:
            reason_examples["CONVERSION_FAILED"].append(str(source or ""))

        error_data = error if isinstance(error, dict) else {}
        asset_summaries.append({
            "source": str(source or ""),
            "format": source_format.lower(),
            "familyKind": family_kind or None,
            "converted": False,
            "automaticReady": False,
            "score": 0,
            "roleCoverage": 0.0,
            "roleRefinements": {},
            "semanticCapabilities": {},
            "unknownMemberSamples": [],
            "generator": None,
            "reasons": ["CONVERSION_FAILED"],
            "detailedReasons": ["CONVERSION_FAILED"],
            "error": str(error_data.get("error", "") if isinstance(error, dict) else error),
            "outputKey": error_data.get("output_key"),
            "familyId": error_data.get("family_id"),
        })

    normalized_classes = {}
    for family_kind, stats in sorted(by_class.items()):
        discovered = stats["discovered"]
        converted = stats["converted"]
        normalized_classes[family_kind] = {
            "discovered": discovered,
            "converted": converted,
            "failed": stats["failed"],
            "automaticReady": stats["automaticReady"],
            "needsReview": stats["needsReview"],
            "conversionSuccessRate": _rounded_average(converted, discovered),
            "autoAcceptanceRate": _rounded_average(stats["automaticReady"], converted),
            "averageScore": round(_rounded_average(stats["scoreTotal"], converted), 2),
            "averageRoleCoverage": _rounded_average(stats["coverageTotal"], converted),
            "averageGenericNameShare": _rounded_average(stats["genericNameShareTotal"], converted),
        }

    normalized_formats = {}
    for source_format, stats in sorted(by_format.items()):
        discovered = stats["discovered"]
        normalized_formats[source_format] = {
            **stats,
            "conversionSuccessRate": _rounded_average(stats["converted"], discovered),
            "autoAcceptanceRate": _rounded_average(stats["automaticReady"], stats["converted"]),
        }

    converted = len(results)
    automatic_ready = sum(1 for item in results if bool((item.get("quality") or {}).get("automaticReady", False)))
    discovered = int(report.get("discovered", converted + len(errors)) or (converted + len(errors)))
    failed = len(errors)
    needs_review = converted - automatic_ready

    top_reasons = [
        {
            "reason": reason,
            "count": count,
            "shareOfConverted": _rounded_average(count, converted),
            "exampleSources": reason_examples.get(reason, []),
        }
        for reason, count in sorted(reason_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ]

    summary = {
        "discovered": discovered,
        "converted": converted,
        "failed": failed,
        "automaticReady": automatic_ready,
        "needsReview": needs_review,
        "conversionSuccessRate": _rounded_average(converted, discovered),
        "autoAcceptanceRate": _rounded_average(automatic_ready, converted),
    }

    return {
        "schema": HARDENING_SCHEMA,
        "schemaVersion": HARDENING_VERSION,
        "inputDirectory": report.get("input_directory"),
        "outputDirectory": report.get("output_directory"),
        "requestedFamilyKind": report.get("family_kind"),
        "summary": summary,
        "counts": {
            "discovered": discovered,
            "converted": converted,
            "failed": failed,
            "automaticReady": automatic_ready,
            "needsReview": needs_review,
        },
        "conversionSuccessPercent": round(summary["conversionSuccessRate"] * 100.0, 2),
        "automaticReadyPercent": round(summary["autoAcceptanceRate"] * 100.0, 2),
        "byClass": normalized_classes,
        "byFormat": normalized_formats,
        "reasonFrequency": dict(sorted(compact_reason_counts.items())),
        "refinementFrequency": dict(sorted(refinement_counts.items())),
        "reviewReasons": top_reasons,
        "assets": asset_summaries,
    }
