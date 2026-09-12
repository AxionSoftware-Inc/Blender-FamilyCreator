"""Batch-source provenance and stale-output diagnostics.

A production library root can contain packages from multiple independent batch
jobs, so merely comparing `library-index.json` against one input directory would
create false stale-package warnings. This module only compares runs when both
input root and requested Family Class match the previous batch-source index.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


SOURCE_INDEX_SCHEMA = "axion.family.batch-source-index"
SOURCE_INDEX_VERSION = 1
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


def source_index_scope_matches(previous, current):
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return False
    if previous.get("schema") != SOURCE_INDEX_SCHEMA or current.get("schema") != SOURCE_INDEX_SCHEMA:
        return False
    if previous.get("schemaVersion") != SOURCE_INDEX_VERSION or current.get("schemaVersion") != SOURCE_INDEX_VERSION:
        return False
    return (
        _normalized_path(previous.get("inputDirectory")) == _normalized_path(current.get("inputDirectory"))
        and str(previous.get("requestedFamilyKind", "")).upper()
        == str(current.get("requestedFamilyKind", "")).upper()
    )


def compare_source_indexes(previous, current, catalog_family_ids=()):
    catalog_ids = {str(value) for value in (catalog_family_ids or ()) if value}
    comparable = source_index_scope_matches(previous, current)
    result = {
        "comparable": comparable,
        "staleFamilyIds": [],
        "failedRefreshFamilyIds": [],
        "staleCount": 0,
        "failedRefreshCount": 0,
    }
    if not comparable:
        return result

    previous_ids = {
        str(item.get("familyId"))
        for item in (previous.get("sources", ()) or ())
        if isinstance(item, dict) and item.get("familyId")
    }
    current_records = [item for item in (current.get("sources", ()) or ()) if isinstance(item, dict)]
    current_ids = {str(item.get("familyId")) for item in current_records if item.get("familyId")}

    stale = sorted(previous_ids - current_ids)
    failed_refresh = sorted(
        {
            str(item.get("familyId"))
            for item in current_records
            if item.get("familyId")
            and not item.get("converted")
            and str(item.get("familyId")) in catalog_ids
        }
    )

    result.update({
        "staleFamilyIds": stale,
        "failedRefreshFamilyIds": failed_refresh,
        "staleCount": len(stale),
        "failedRefreshCount": len(failed_refresh),
    })
    return result


def load_source_index(path):
    path = Path(path)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != SOURCE_INDEX_SCHEMA or data.get("schemaVersion") != SOURCE_INDEX_VERSION:
        return None
    return data


def write_source_index(output_directory, payload):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / SOURCE_INDEX_FILENAME
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
