# Axion Family Library — Catalog and Integrity

A library root combines independently exported family packages into one runtime catalog.

## Files

```text
library/
  sofa/...
  table/...
  window/...
  batch-report.json
  review-queue.json
  library-index.json
  library-audit.json
```

`library-index.json` is rebuilt by Batch Family Factory. `library-audit.json` verifies that files referenced by manifests actually exist inside the same library root.

## Library index

Current index contract:

```json
{
  "schema": "axion.family.library",
  "schemaVersion": 1,
  "familyCount": 42,
  "automaticReady": 35,
  "needsReview": 7,
  "classCounts": {"SOFA": 12, "TABLE": 10, "WINDOW": 20},
  "assetWarningCount": 0,
  "missingAssetCount": 0,
  "familiesWithAssetWarnings": 0,
  "familiesWithLods": 18,
  "mobileBudgetStatusCounts": {
    "WITHIN_TARGET": 30,
    "OVER_TARGET": 10,
    "OVER_HARD_LIMIT": 2
  },
  "families": []
}
```

Each family entry can include:

- stable `familyId`;
- display `name`;
- exact `familyKind`;
- category/group;
- root-relative manifest URI;
- active Type and saved Type names;
- current dimensions;
- semantic quality score / `automaticReady`;
- material count;
- root-relative baked `geometryVariants`;
- root-relative `geometryLods` metadata when generated;
- optional thumbnail URI;
- host type for hosted families;
- selection-proxy size and plan footprint;
- runtime triangle/vertex/material-slot cost;
- mobile budget status and suggested LOD ratios;
- source key for batch traceability;
- `assetsComplete` and optional `assetWarnings`.

All runtime asset paths are library-root-relative. A manifest URI that resolves outside the library root is never surfaced as a usable catalog asset.

## Asset warnings

A valid semantic manifest is not discarded merely because a copied library package is incomplete. Instead the entry remains discoverable and exposes warnings such as:

```json
{
  "assetsComplete": false,
  "assetWarnings": [
    {
      "code": "MISSING_FILE",
      "assetType": "lod",
      "uri": "lod/lod2.glb",
      "lodLevel": "LOD2"
    }
  ]
}
```

This lets production tooling distinguish semantic rejection from packaging/copy failures.

## Rejected manifests

`rejectedManifests` contains manifests that cannot become catalog entries, for example:

- invalid JSON;
- unsupported schema/version;
- missing family ID;
- duplicate `familyId`.

Duplicate IDs are rejected rather than silently selecting the last file.

## Library audit

`library_audit.py` performs a second, read-only integrity pass over all family manifests.

Output:

```json
{
  "schema": "axion.family.library.audit",
  "schemaVersion": 1,
  "manifestCount": 42,
  "validFamilyCount": 42,
  "familyIdsUnique": 42,
  "familiesWithAssetWarnings": 0,
  "assetWarningCount": 0,
  "missingAssetCount": 0,
  "unsafeUriCount": 0,
  "warningCount": 0,
  "complete": true
}
```

The audit checks:

- duplicate family IDs;
- malformed/unsupported manifests;
- missing primary/variant GLBs;
- missing generated/aliased LOD files;
- missing thumbnails;
- URI path traversal outside the library root.

It never deletes or repairs files automatically.

## Command-line audit

```powershell
python tools/audit_library.py `
  --library 'D:\axion-family-library' `
  --fail-on-warning
```

Without `--fail-on-warning`, warnings are reported but the command remains informational.

## Mobile runtime usage

Recommended runtime flow:

1. load `library-index.json` once;
2. filter by Family Class, quality/capabilities and user search;
3. read proxy/footprint for lightweight preview/placement;
4. choose LOD URI according to device/distance;
5. load the selected family manifest only when richer semantic detail is needed;
6. surface review/incomplete-package state to production tools, not end users.

The index is a discovery cache; the family manifest remains the authoritative per-family semantic contract.
