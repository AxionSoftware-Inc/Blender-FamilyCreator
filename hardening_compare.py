from collections import Counter, defaultdict


COMPARE_SCHEMA = "axion.family.hardening.compare"
COMPARE_VERSION = 1


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _asset_key(asset):
    source = str(asset.get("source", "") or "").replace("\\", "/")
    filename = source.rsplit("/", 1)[-1].lower()
    family_kind = str(asset.get("familyKind", "") or "").upper()
    return f"{family_kind}:{filename}"


def _asset_index(report):
    result = {}
    collisions = defaultdict(list)
    for asset in report.get("assets", ()) or ():
        if not isinstance(asset, dict):
            continue
        key = _asset_key(asset)
        if not key:
            continue
        if key in result:
            if not collisions[key]:
                collisions[key].append(str(result[key].get("source", "") or ""))
            collisions[key].append(str(asset.get("source", "") or ""))
            continue
        result[key] = asset
    return result, {key: values for key, values in sorted(collisions.items())}


def _summary(report):
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    return {
        "discovered": _integer(summary.get("discovered")),
        "converted": _integer(summary.get("converted")),
        "failed": _integer(summary.get("failed")),
        "automaticReady": _integer(summary.get("automaticReady")),
        "needsReview": _integer(summary.get("needsReview")),
        "conversionSuccessRate": _number(summary.get("conversionSuccessRate")),
        "autoAcceptanceRate": _number(summary.get("autoAcceptanceRate")),
    }


def _delta(before, after):
    return round(_number(after) - _number(before), 4)


def _class_delta(baseline, candidate):
    before = baseline.get("byClass", {}) if isinstance(baseline.get("byClass"), dict) else {}
    after = candidate.get("byClass", {}) if isinstance(candidate.get("byClass"), dict) else {}
    result = {}
    for family_kind in sorted(set(before) | set(after)):
        old = before.get(family_kind, {}) or {}
        new = after.get(family_kind, {}) or {}
        result[family_kind] = {
            "baseline": {
                "converted": _integer(old.get("converted")),
                "automaticReady": _integer(old.get("automaticReady")),
                "autoAcceptanceRate": _number(old.get("autoAcceptanceRate")),
                "averageScore": _number(old.get("averageScore")),
                "averageRoleCoverage": _number(old.get("averageRoleCoverage")),
            },
            "candidate": {
                "converted": _integer(new.get("converted")),
                "automaticReady": _integer(new.get("automaticReady")),
                "autoAcceptanceRate": _number(new.get("autoAcceptanceRate")),
                "averageScore": _number(new.get("averageScore")),
                "averageRoleCoverage": _number(new.get("averageRoleCoverage")),
            },
            "delta": {
                "converted": _integer(new.get("converted")) - _integer(old.get("converted")),
                "automaticReady": _integer(new.get("automaticReady")) - _integer(old.get("automaticReady")),
                "autoAcceptanceRate": _delta(old.get("autoAcceptanceRate"), new.get("autoAcceptanceRate")),
                "averageScore": _delta(old.get("averageScore"), new.get("averageScore")),
                "averageRoleCoverage": _delta(old.get("averageRoleCoverage"), new.get("averageRoleCoverage")),
            },
        }
    return result


def _format_delta(baseline, candidate):
    before = baseline.get("byFormat", {}) if isinstance(baseline.get("byFormat"), dict) else {}
    after = candidate.get("byFormat", {}) if isinstance(candidate.get("byFormat"), dict) else {}
    result = {}
    for source_format in sorted(set(before) | set(after)):
        old = before.get(source_format, {}) or {}
        new = after.get(source_format, {}) or {}
        result[source_format] = {
            "baselineDiscovered": _integer(old.get("discovered")),
            "candidateDiscovered": _integer(new.get("discovered")),
            "candidateConverted": _integer(new.get("converted")),
            "candidateFailed": _integer(new.get("failed")),
            "candidateConversionSuccessRate": _number(new.get("conversionSuccessRate")),
            "candidateAutoAcceptanceRate": _number(new.get("autoAcceptanceRate")),
        }
    return result


def _reason_delta(baseline, candidate):
    before = baseline.get("reasonFrequency", {}) if isinstance(baseline.get("reasonFrequency"), dict) else {}
    after = candidate.get("reasonFrequency", {}) if isinstance(candidate.get("reasonFrequency"), dict) else {}
    return {
        reason: {
            "baseline": _integer(before.get(reason)),
            "candidate": _integer(after.get(reason)),
            "delta": _integer(after.get(reason)) - _integer(before.get(reason)),
        }
        for reason in sorted(set(before) | set(after))
    }


def _subset_metrics(assets):
    assets = list(assets)
    converted = [asset for asset in assets if bool(asset.get("converted", False))]
    automatic = [asset for asset in converted if bool(asset.get("automaticReady", False))]
    coverage_total = sum(_number(asset.get("roleCoverage")) for asset in converted)
    score_total = sum(_number(asset.get("score")) for asset in converted)
    reasons = Counter()
    by_class = defaultdict(lambda: {"count": 0, "automaticReady": 0, "coverageTotal": 0.0})
    for asset in converted:
        for reason in asset.get("reasons", ()) or ():
            reasons[str(reason)] += 1
        family_kind = str(asset.get("familyKind", "UNKNOWN") or "UNKNOWN")
        entry = by_class[family_kind]
        entry["count"] += 1
        entry["automaticReady"] += int(bool(asset.get("automaticReady", False)))
        entry["coverageTotal"] += _number(asset.get("roleCoverage"))
    normalized_classes = {}
    for family_kind, entry in sorted(by_class.items()):
        count = entry["count"]
        normalized_classes[family_kind] = {
            "count": count,
            "automaticReady": entry["automaticReady"],
            "autoAcceptanceRate": round(entry["automaticReady"] / count, 4) if count else 0.0,
            "averageRoleCoverage": round(entry["coverageTotal"] / count, 4) if count else 0.0,
        }
    return {
        "count": len(assets),
        "converted": len(converted),
        "failed": len(assets) - len(converted),
        "automaticReady": len(automatic),
        "autoAcceptanceRate": round(len(automatic) / len(converted), 4) if converted else 0.0,
        "averageScore": round(score_total / len(converted), 2) if converted else 0.0,
        "averageRoleCoverage": round(coverage_total / len(converted), 4) if converted else 0.0,
        "reasonFrequency": dict(sorted(reasons.items())),
        "byClass": normalized_classes,
    }


def _overlap_changes(baseline_assets, candidate_assets):
    improvements = []
    regressions = []
    stable = []
    for key in sorted(set(baseline_assets) & set(candidate_assets)):
        old = baseline_assets[key]
        new = candidate_assets[key]
        old_ready = bool(old.get("automaticReady", False))
        new_ready = bool(new.get("automaticReady", False))
        old_coverage = _number(old.get("roleCoverage"))
        new_coverage = _number(new.get("roleCoverage"))
        old_score = _number(old.get("score"))
        new_score = _number(new.get("score"))
        entry = {
            "assetKey": key,
            "baselineAutomaticReady": old_ready,
            "candidateAutomaticReady": new_ready,
            "scoreDelta": round(new_score - old_score, 2),
            "roleCoverageDelta": round(new_coverage - old_coverage, 4),
            "baselineReasons": list(old.get("reasons", ()) or ()),
            "candidateReasons": list(new.get("reasons", ()) or ()),
        }
        if old_ready and not new_ready:
            entry["regression"] = "AUTOMATIC_READY_LOST"
            regressions.append(entry)
        elif bool(old.get("converted", True)) and not bool(new.get("converted", False)):
            entry["regression"] = "CONVERSION_LOST"
            regressions.append(entry)
        elif new_coverage < old_coverage - 0.05:
            entry["regression"] = "ROLE_COVERAGE_DROP"
            regressions.append(entry)
        elif new_score < old_score - 10.0:
            entry["regression"] = "SCORE_DROP"
            regressions.append(entry)
        elif (not old_ready and new_ready) or new_coverage > old_coverage + 0.05 or new_score > old_score + 10.0:
            improvements.append(entry)
        else:
            stable.append(entry)
    return improvements, regressions, stable


def compare_hardening_reports(baseline, candidate):
    baseline_summary = _summary(baseline)
    candidate_summary = _summary(candidate)
    baseline_assets, baseline_collisions = _asset_index(baseline)
    candidate_assets, candidate_collisions = _asset_index(candidate)

    overlap_keys = sorted(set(baseline_assets) & set(candidate_assets))
    new_keys = sorted(set(candidate_assets) - set(baseline_assets))
    removed_keys = sorted(set(baseline_assets) - set(candidate_assets))
    improvements, regressions, stable = _overlap_changes(baseline_assets, candidate_assets)
    collision_count = len(baseline_collisions) + len(candidate_collisions)

    return {
        "schema": COMPARE_SCHEMA,
        "schemaVersion": COMPARE_VERSION,
        "baseline": baseline_summary,
        "candidate": candidate_summary,
        "overallDelta": {
            "discovered": candidate_summary["discovered"] - baseline_summary["discovered"],
            "converted": candidate_summary["converted"] - baseline_summary["converted"],
            "failed": candidate_summary["failed"] - baseline_summary["failed"],
            "automaticReady": candidate_summary["automaticReady"] - baseline_summary["automaticReady"],
            "needsReview": candidate_summary["needsReview"] - baseline_summary["needsReview"],
            "conversionSuccessRate": _delta(baseline_summary["conversionSuccessRate"], candidate_summary["conversionSuccessRate"]),
            "autoAcceptanceRate": _delta(baseline_summary["autoAcceptanceRate"], candidate_summary["autoAcceptanceRate"]),
        },
        "corpus": {
            "overlapCount": len(overlap_keys),
            "newCount": len(new_keys),
            "removedCount": len(removed_keys),
            "overlapAssetKeys": overlap_keys,
            "newAssetKeys": new_keys,
            "removedAssetKeys": removed_keys,
            "baselineKeyCollisions": baseline_collisions,
            "candidateKeyCollisions": candidate_collisions,
        },
        "overlap": {
            "improvements": improvements,
            "regressions": regressions,
            "stable": stable,
        },
        "newAssets": _subset_metrics(candidate_assets[key] for key in new_keys),
        "classDelta": _class_delta(baseline, candidate),
        "formatDelta": _format_delta(baseline, candidate),
        "reasonDelta": _reason_delta(baseline, candidate),
        "gate": {
            "overlapRegressionCount": len(regressions),
            "assetKeyCollisionCount": collision_count,
            "passesNoRegressionGate": len(regressions) == 0 and collision_count == 0,
        },
    }
