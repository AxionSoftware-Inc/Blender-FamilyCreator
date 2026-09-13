"""Batch-source provenance and stale-output diagnostics.

A production library root can contain packages from multiple independent batch
jobs. The persisted `batch-source-index.json` therefore stores a registry of
per-scope snapshots keyed logically by normalized input root + requested Family
Class. This preserves stale/failed-refresh detection across alternating jobs
such as A -> B -> A.

Schema-v1 single-scope files remain readable and are upgraded to the v2 registry
format on the next successful write.

Removed-source packages are only called *stale outputs* when the corresponding
familyId still exists in the current library catalog. This avoids flagging a
source that failed before ever producing a package.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


SOURCE_INDEX_SCHEMA = "axion.family.batch-source-index"
SOURCE_INDEX_VERSION = 1
SOURCE_REGISTRY_VERSION = 2
SOURCE_INDEX_FILENAME = "batch-source-index.json"


def _normalized_path(value):
    if not value:
        return ""
    try:
        return os.path.normcase(os.path.abspath(os.path.expanduser(str(value))))
    except Exception:
        return str(value)


def _source_record(item, converted):
    item = item if isinstance(item, dict) else {}
    return {
        "source": str(item.get("source", "") or ""),
        "outputKey": item.get("output_key"),
        "familyKind": item.get("family_kind"),
        "familyId": item.get("family_id"),
        "converted": bool(converted),
        "error": None if converted else str(item.get("error", "") or "") or None,
    }


def build_source_index(report):
    """Build one scope snapshot from a batch report.

    The returned object intentionally remains schema v1. `write_source_index`
    persists snapshots inside the schema-v2 multi-scope registry.
    """
    report = report if isinstance(report, dict) else {}
    records = []
    records.extend(_source_record(item, True) for item in (report.get("results", ()) or ()))
    records.extend(_source_record(item, False) for item in (report.get("errors", ()) or ()))
    records.sort(key=lambda item: (str(item.get("source", "")).lower(), str(item.get("familyId", ""))))

    return {
        "schema": SOURCE_INDEX_SCHEMA,
        "schemaVersion": SOURCE_INDEX_VERSION,
        "inputDirectory": str(report.get("input_directory", "") or ""),
        "requestedFamilyKind": str(report.get("family_kind", "") or ""),
        "aborted": bool(report.get("aborted", False)),
        "sourceCount": len(records),
        "resolvedFamilyCount": sum(1 for item in records if item.get("familyId")),
        "convertedCount": sum(1 for item in records if item.get("converted")),
        "failedCount": sum(1 for item in records if not item.get("converted")),
        "sources": records,
    }


def _is_scope_snapshot(data):
    return (
        isinstance(data, dict)
        and data.get("schema") == SOURCE_INDEX_SCHEMA
        and data.get("schemaVersion") == SOURCE_INDEX_VERSION
        and isinstance(data.get("sources", []), list)
    )


def _is_scope_registry(data):
    return (
        isinstance(data, dict)
        and data.get("schema") == SOURCE_INDEX_SCHEMA
        and data.get("schemaVersion") == SOURCE_REGISTRY_VERSION
        and isinstance(data.get("scopes", []), list)
    )


def source_index_scope_matches(previous, current):
    if not _is_scope_snapshot(previous) or not _is_scope_snapshot(current):
        return False
    return (
        _normalized_path(previous.get("inputDirectory")) == _normalized_path(current.get("inputDirectory"))
        and str(previous.get("requestedFamilyKind", "")).upper()
        == str(current.get("requestedFamilyKind", "")).upper()
    )


def _registry_scopes(data):
    if _is_scope_snapshot(data):
        return [data]
    if _is_scope_registry(data):
        return [scope for scope in data.get("scopes", ()) if _is_scope_snapshot(scope)]
    return []


def _matching_previous_scope(previous, current):
    for scope in reversed(_registry_scopes(previous)):
        if source_index_scope_matches(scope, current):
            return scope
    return None


def compare_source_indexes(previous, current, catalog_family_ids=None):
    catalog_available = catalog_family_ids is not None
    catalog_ids = (
        {str(value) for value in (catalog_family_ids or ()) if value}
        if catalog_available
        else set()
    )
    previous_scope = _matching_previous_scope(previous, current)
    comparable = previous_scope is not None
    result = {
        "comparable": comparable,
        "catalogAvailable": catalog_available,
        "staleFamilyIds": [],
        "unverifiedStaleCandidateFamilyIds": [],
        "failedRefreshFamilyIds": [],
        "staleCount": 0,
        "unverifiedStaleCandidateCount": 0,
        "failedRefreshCount": 0,
    }
    if not comparable:
        return result

    previous_ids = {
        str(item.get("familyId"))
        for item in (previous_scope.get("sources", ()) or ())
        if isinstance(item, dict) and item.get("familyId")
    }
    current_records = [item for item in (current.get("sources", ()) or ()) if isinstance(item, dict)]
    current_ids = {str(item.get("familyId")) for item in current_records if item.get("familyId")}

    stale_candidates = previous_ids - current_ids
    if catalog_available:
        stale = sorted(stale_candidates & catalog_ids)
        unverified = []
    else:
        stale = []
        unverified = sorted(stale_candidates)

    failed_refresh = sorted(
        {
            str(item.get("familyId"))
            for item in current_records
            if item.get("familyId")
            and not item.get("converted")
            and catalog_available
            and str(item.get("familyId")) in catalog_ids
        }
    )

    result.update({
        "staleFamilyIds": stale,
        "unverifiedStaleCandidateFamilyIds": unverified,
        "failedRefreshFamilyIds": failed_refresh,
        "staleCount": len(stale),
        "unverifiedStaleCandidateCount": len(unverified),
        "failedRefreshCount": len(failed_refresh),
    })
    return result


def load_source_index(path):
    """Load either a legacy v1 snapshot or the v2 multi-scope registry."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if _is_scope_snapshot(data) or _is_scope_registry(data):
        return data
    return None


def _registry_payload(existing, current):
    if not _is_scope_snapshot(current):
        raise ValueError("Current batch source index must be a valid scope snapshot")

    scopes = list(_registry_scopes(existing))
    replaced = False
    for index, scope in enumerate(scopes):
        if source_index_scope_matches(scope, current):
            scopes[index] = current
            replaced = True
            break
    if not replaced:
        scopes.append(current)

    scopes.sort(key=lambda scope: (
        _normalized_path(scope.get("inputDirectory")),
        str(scope.get("requestedFamilyKind", "")).upper(),
    ))

    return {
        "schema": SOURCE_INDEX_SCHEMA,
        "schemaVersion": SOURCE_REGISTRY_VERSION,
        "scopeCount": len(scopes),
        "latestScope": current,
        "scopes": scopes,
    }


def write_source_index(output_directory, payload):
    """Merge one scope snapshot into the persisted multi-scope registry."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / SOURCE_INDEX_FILENAME
    existing = load_source_index(path)
    registry = _registry_payload(existing, payload)
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
