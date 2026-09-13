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
  batch-source-index.json
```

`library-index.json` is rebuilt by Batch Family Factory. `library-audit.json`
verifies that files referenced by manifests actually exist inside the same
library root. `batch-source-index.json` is a production provenance registry for
safe stale/failed-refresh diagnostics across repeated batch scopes.

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
  "mobileOptimizationReasonCounts": {
    "DRAW_CALLS": 4,
    "TEXTURE_DIMENSION": 7,
    "TEXTURE_MEMORY": 3,
    "TRIANGLES": 8
  },
  "familiesRecommendedForGeometryLod": 8,
  "familiesRecommendedForMaterialOptimization": 4,
  "familiesRecommendedForTextureOptimization": 7,
  "familiesOverMobileTarget": 10,
  "familiesOverMobileHardLimit": 2,
  "runtimeCostSummary": {
    "measuredFamilies": 42,
    "totalTriangles": 6200000,
    "maxFamilyTriangles": 580000,
    "totalDrawCallEstimate": 310,
    "maxFamilyDrawCallEstimate": 24,
    "totalEstimatedTextureMemoryMiB": 1240.5,
    "maxFamilyEstimatedTextureMemoryMiB": 128.0,
    "maxTextureDimension": 8192
  },
  "families": []
}
```

`runtimeCostSummary` is a production-planning diagnostic. Summing texture memory
across an entire library does **not** mean every texture will be resident at the
same time on a device; it is useful for comparing library revisions and finding
heavy outliers.

The recommendation counters let the mobile/content pipeline distinguish three
separate optimization jobs:

- geometry/LOD reduction;
- material-slot/draw-call consolidation;
- texture-resolution/memory optimization.

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
- unique material count and estimated draw calls;
- texture count, maximum texture dimension and estimated uncompressed RGBA texture memory;
- mobile budget policy/status, optimization reasons/recommendations and suggested geometry LOD ratios;
- source key for batch traceability;
- `assetsComplete` and optional `assetWarnings`.

Example compact runtime cost entry:

```json
{
  "runtimeCost": {
    "triangles": 124000,
    "vertices": 68000,
    "materialSlots": 7,
    "uniqueMaterials": 5,
    "drawCallEstimate": 9,
    "textureCount": 6,
    "maxTextureDimension": 4096,
    "estimatedTextureMemoryMiB": 80.0,
    "memberCount": 12
  },
  "mobileBudget": {
    "policyVersion": 2,
    "status": "OVER_TARGET",
    "sourceTriangles": 124000,
    "sourceDrawCallEstimate": 9,
    "sourceMaxTextureDimension": 4096,
    "sourceTextureMemoryMiB": 80.0,
    "optimizationReasons": ["TEXTURE_DIMENSION", "TEXTURE_MEMORY"],
    "geometryLodRecommended": false,
    "materialOptimizationRecommended": false,
    "textureOptimizationRecommended": true,
    "suggestedLod1Ratio": 1.0,
    "suggestedLod2Ratio": 0.0806
  }
}
```

Mobile status is intentionally separate from semantic readiness. A family can be
`automaticReady=true` while `mobileBudget.status=OVER_TARGET` because its
geometry, material/draw-call cost, texture resolution or estimated texture
memory needs runtime optimization.

LOD ratios address **geometry only**. A family that is over budget only because
of textures/materials can legitimately have `geometryLodRecommended=false` and
a suggested LOD1 ratio of `1.0`; the fix in that case is texture/material
optimization rather than mesh decimation.

## Path and asset safety

All runtime asset paths are library-root-relative and use the same safe-relative
contract as schema v2.

Catalog and audit reject:

- absolute asset paths;
- `.` or `..` URI segments even when normalization would remain inside the root;
- asset symlinks/physical paths that resolve outside the library root;
- manifest files whose own physical/symlink target resolves outside the library root.

An unsafe manifest is rejected from `library-index.json` and reported by
`library-audit.json` instead of being read as a normal family package.

## LOD catalog records

When present, each LOD record can expose:

```json
{
  "LOD1": {
    "uri": "chair/A/lod/lod1.glb",
    "generated": true,
    "triangles": 39000,
    "targetTriangles": 40000,
    "meetsTarget": true
  }
}
```

This lets the mobile browser make a lightweight choice without opening every
family manifest.

## Asset warnings

A valid semantic manifest is not discarded merely because a copied library
package is incomplete. Instead the entry remains discoverable and exposes
warnings such as:

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

This lets production tooling distinguish semantic rejection from packaging/copy
failures.

## Rejected manifests

`rejectedManifests` contains manifests that cannot become catalog entries, for
example:

- invalid JSON;
- unsupported schema/version;
- missing family ID;
- duplicate `familyId`;
- a manifest path that physically resolves outside the library root.

Duplicate IDs are rejected rather than silently selecting the last file.

## Library audit

`library_audit.py` performs a second, read-only integrity pass over all family
manifests.

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
- manifest physical-root containment;
- missing primary/variant GLBs;
- missing generated/aliased LOD files;
- missing thumbnails;
- unsafe absolute/dot-segment/path-traversal/symlink asset URIs.

It never deletes or repairs files automatically.

## Repeated-batch source provenance

`batch-source-index.json` is separate from the runtime library index. Persisted
files now use **schema version 2** as a multi-scope registry. Each stored scope is
a schema-v1 source snapshot containing:

- normalized input-directory scope;
- requested exact/AUTO_FOLDER Family Class;
- source path;
- output key;
- resolved Family Class and family ID;
- converted/failed state.

A library can therefore retain provenance for several independent batch jobs.
Alternating runs such as A -> B -> A preserve A's old baseline while B becomes
the latest scope. On the next A run the comparator finds the previous matching A
scope by normalized input root + requested Family Class.

Legacy schema-v1 single-scope files remain readable and are upgraded into the v2
registry on the next successful write.

Two important diagnostics are written into the batch report:

- `stale_output_count`: a source from the previous comparable scope is now gone or renamed, while its family ID is still present in the current library catalog;
- `failed_refresh_package_count`: the source still exists and this run failed to refresh it, while the old family package is still present.

Neither condition triggers automatic deletion. Production tooling should review
or explicitly clean stale packages. `batch_cli.py --strict` treats both as a
publish-gate failure.

An aborted `--stop-on-error` run does not replace provenance. A run whose
`library-index.json` cannot be built also preserves the previous registry because
present-family IDs cannot be verified safely.

## Batch cleanup health

`batch-report.json` additionally exposes cleanup health from the Blender batch
process:

- `cleanup_warnings` — converted assets whose post-import cleanup left IDs in use or whose cleanup diagnostic itself failed;
- `cleanup_leftover_datablocks` — total remaining post-snapshot Blender IDs;
- per-result `cleanup` records with removed/leftover counts by datablock type.

Cleanup is snapshot-scoped. It does **not** run Blender's global orphan purge, so
unrelated zero-user data that existed before an asset conversion is not deleted.
Common vendor/import ID collections including mesh/curve/point-cloud,
material/image/node-group, armature/action, volume, collection and related media
IDs are tracked when the running Blender version exposes them.

## Command-line audit

```powershell
python tools/audit_library.py `
  --library 'D:\axion-family-library' `
  --fail-on-warning
```

Without `--fail-on-warning`, warnings are reported but the command remains
informational.

## Mobile runtime usage

Recommended runtime flow:

1. load `library-index.json` once;
2. filter by Family Class, semantic quality/capabilities and user search;
3. use runtime-cost/mobile recommendation summaries to avoid loading unsuitable heavy candidates;
4. read proxy/footprint for lightweight preview/placement;
5. choose an LOD URI according to device, screen size and distance only when geometry optimization is recommended;
6. route material/texture recommendations to content optimization rather than treating them as semantic errors;
7. load the selected family manifest only when richer semantic detail is needed;
8. surface review/incomplete-package/stale state to production tools, not end users.

The index is a discovery cache; the family manifest remains the authoritative
per-family semantic contract.
