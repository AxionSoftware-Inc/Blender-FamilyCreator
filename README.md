# Blender Family Creator

Convert ordinary Blender assets into **typed, semantic, hosted and mobile-aware BIM family libraries** for Axion's BIM stack.

Family Creator is deliberately not a universal XYZ scaler. Sofa, Table, Door, Window, Cabinet, Stair and plumbing fixtures have different semantic/geometry contracts, so assets are routed through exact **Family Classes**.

## Current pipeline

```text
Downloaded / authored asset
  -> conservative Auto Prepare
  -> exact Family Class
  -> semantic member roles + family-level refinement
  -> class-specific MOVE / STRETCH / FIXED rules
  -> semantic parameter inference
  -> procedural / semantic rebuild
  -> semantic quality + source preflight
  -> saved Family Types
  -> baked Type GLB variants
  -> hosting / proxy / capability metadata
  -> evaluated runtime geometry/material/texture cost
  -> mobile optimization diagnostics
  -> optional non-destructive LOD1 / LOD2
  -> schema-v2 validation in sibling staging
  -> rollback-safe package commit
  -> library-index.json
  -> library-audit.json
  -> batch-source-index.json
```

The goal is a high-throughput library factory: automatically accept straightforward assets, preserve ambiguous assets for review, and keep mobile optimization separate from semantic validity.

## Runtime validation status

The v0.5 foundation was validated in **Blender 5.2.0 LTS / Python 3.13.13** with deterministic runtime tests covering registration, all registered Family Classes, hierarchy/preflight, modifiers, Auto Prepare, GLB round-trip, baked Types, thumbnails, schema/runtime proxy, batch/AUTO_FOLDER, cleanup and failure transactions.

Real BlenderKit hardening then moved the seven-asset golden corpus from 0 automatic-ready families to 3/7 without lowering global semantic thresholds. The current golden state includes automatic-ready BED and WINDOW examples, a baked Window with no separate frame mesh, and a curved Window whose semantics are complete but remains review-only because non-uniform scale is deliberately not auto-applied.

The newest v0.7 production/mobile layer is **implemented on `main` but still awaiting the consolidated local Blender 5.2 validation pass**. LOD remains opt-in/default OFF until that gate is green.

## Family Classes

```text
Furniture
  SOFA
  TABLE
  CHAIR
  BED

Casework
  CABINET
  WARDROBE
  SHELF
  KITCHEN_BASE
  KITCHEN_WALL

Hosted openings
  DOOR
  WINDOW

Circulation
  STAIR

Plumbing
  TOILET
  SINK
  BATHTUB

Fallback
  GENERIC
```

See `docs/FAMILY_CLASSES.md` for class contracts.

## Family Class, Type and Role

- **Family Class** — semantic/geometry behavior contract (`SOFA`, `WINDOW`, `STAIR`, ...).
- **Family Type** — saved dimension + semantic parameter state (`2-seat`, `900x2100`, ...).
- **Member Role** — semantic part (`SEAT`, `TOP`, `FRAME_LEFT`, `GLASS`, `DRAIN`, ...).

Per-member axis rules:

| Rule | Meaning |
|---|---|
| `STRETCH` | Resize on the family axis |
| `MOVE` | Keep size but follow the changing boundary |
| `FIXED` | Preserve size/position on that axis |

Family axes also publish `CENTER`, `MIN`, and `MAX` anchors.

Rotated/off-axis source members preserve their canonical basis angles instead of receiving a family-axis scale matrix that can introduce shear. Existing source shear is not silently repaired; Preflight reports it for review.

## Semantic analysis and hardening

Analysis uses names plus normalized evaluated geometry. Modifier-aware bounds use Blender's evaluated dependency graph. Generic vendor names can fall back to geometry, while explicit class aliases and family-level second passes handle repeated real-world patterns conservatively.

Real-asset tooling:

```text
hardening.py
tests/blender_runtime/run_real_assets.py
tools/compare_hardening.py
docs/REAL_ASSET_HARDENING.md
docs/HARDENING_EXPANSION_PROTOCOL.md
```

The compare tool separates:

- regressions on the golden overlap corpus;
- performance on genuinely new assets;
- class/format/review-reason deltas;
- duplicate corpus keys.

Do not tune one unusual downloaded model until a repeated pattern exists.

## Auto Prepare and source-risk safety

Downloaded models frequently contain disconnected physical parts inside one Mesh. Auto Prepare can split manageable loose islands before semantic analysis.

Safety policy:

- no shape-key splitting;
- no armature-driven splitting;
- single islands remain untouched;
- very fragmented meshes remain untouched;
- hierarchy helpers are preserved;
- source transform shear is surfaced to review;
- separated multi-asset spatial clusters are surfaced to review;
- no global orphan purge during batch cleanup.

Batch cleanup snapshots Blender ID collections before each source import and removes only post-snapshot zero-user datablocks. Partial importer failures are covered by a dedicated Blender smoke test.

## Procedural generators

Class-specific generators currently cover Sofa seats/arms, Table top thickness, Chair seat height, Bed mattress, casework panels/shelves, Door/Window frame behavior, straight Stair tread/riser generation, and basic plumbing semantics.

Repeated template subtrees preserve child details. Canonical source transforms remain immutable so repeated rebuild/Type switching does not accumulate drift.

## Hosted Door / Window

Door and Window packages can publish:

- `WALL` hosting;
- rectangular host opening dimensions;
- threshold/sill insertion point;
- facing/up directions;
- flip capability;
- Window sill elevation;
- plan representation;
- Door hinge-side inference when supported by semantics.

Window **validity** is distinct from **separate-frame edit capability**. A baked vendor Window can be semantically valid even when its frame is fused into sash geometry. `quality.semanticCapabilities` exposes that distinction.

## Transactional family package export

Typed family export is validate-before-overwrite:

1. create manifest/primary GLB/variants/LODs/thumbnail in a sibling same-filesystem staging directory;
2. validate the complete manifest;
3. temporarily hide the old manifest from discovery;
4. replace staged runtime assets with `os.replace` while backing up existing targets;
5. commit the new manifest last;
6. restore old files if commit fails.

This prevents a failed refresh from deleting the previous valid family package or leaving a discoverable half-package. Unrelated files in the destination directory are not deleted.

## Baked Type GLB variants

With **Bake All Saved Types** enabled:

```text
family/
  family.family.json
  family.glb
  variants/
    small.glb
    wide.glb
```

Variant export temporarily applies each saved Type, rebuilds supported procedural geometry, exports GLB, then restores the original Type/dimensions/semantic state and generator revision. Partial failed variant files are removed from staging.

## Runtime proxy

`runtimeProxy` publishes:

- active selection AABB;
- coarse collision AABB;
- 2D plan footprint;
- predicted saved-Type bounds.

This lets the mobile app hit-test/cull/place a family without testing every GLB triangle.

## Runtime cost and mobile budget

Every new export measures evaluated geometry and resource pressure after modifiers:

```text
runtimeCost.vertices
runtimeCost.triangles
runtimeCost.materialSlots
runtimeCost.uniqueMaterials
runtimeCost.drawCallEstimate
runtimeCost.textureCount
runtimeCost.maxTextureDimension
runtimeCost.estimatedTextureMemoryMiB
runtimeCost.members[]
```

Draw-call estimation uses **material indices actually used by evaluated polygons**, so vendor files with many unused material slots do not automatically look expensive.

`mobileBudget` policy v2 adds class-specific geometry/material/texture targets and one of:

```text
WITHIN_TARGET
OVER_TARGET
OVER_HARD_LIMIT
```

It also publishes machine-readable optimization reasons and independent flags:

```text
optimizationReasons[]
geometryLodRecommended
materialOptimizationRecommended
textureOptimizationRecommended
```

This does **not** change semantic `automaticReady`. A correct family can be semantically accepted while still needing mobile optimization.

## Optional mobile LODs

**Generate Mobile LODs** is currently opt-in.

LOD generation:

- keeps LOD0/source authoring geometry unchanged;
- uses temporary object/data copies;
- freezes temporary world transforms independently from source hierarchy/constraints;
- appends Decimate after source modifiers;
- protects semantic hardware/connectors with a conservative minimum ratio;
- skips destructive simplification of shape-key / already-low-poly members;
- exports `lod/lod1.glb` and `lod/lod2.glb` where useful;
- aliases LOD0 when the source already meets a target;
- records target vs actual triangle counts;
- removes partial failed derivative files;
- cleans temporary objects/datablocks;
- treats derivative failure as a warning when LOD0 is still valid.

A GPU-render path is not required for LOD generation. Thumbnail rendering is separate.

See `docs/FAMILY_FORMAT.md`.

## Batch Family Factory

Use one exact class or **Auto by Folder**:

```text
assets/
  sofas/
  tables/
  doors/
  windows/
  stairs/
```

Supported source formats:

```text
.blend
.fbx
.glb
.gltf
.obj
```

AUTO_FOLDER rejects unknown folders instead of silently falling back to Generic.

Repeated runs also write `batch-source-index.json`. When the same input root + requested class is rerun, removed/renamed sources are compared with the actual current catalog:

- existing output with no current source -> `stale` diagnostic;
- current conversion failure while an older package still exists -> `failedRefresh` diagnostic.

No stale package is auto-deleted.

## Headless factory

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python batch_cli.py -- `
  --input 'D:\assets' `
  --output 'D:\axion-family-library' `
  --class AUTO_FOLDER `
  --recursive `
  --lods `
  --no-thumbnails `
  --strict
```

`--strict` exits non-zero for conversion failures, cleanup leaks, stale/failed-refresh packages, missing runtime assets, source-index errors or an incomplete library audit.

`--no-thumbnails` is useful when a separate AI training workload owns the GPU. See `docs/HEADLESS_BATCH.md`.

## Library outputs

A completed batch root can include:

```text
batch-report.json
review-queue.json
batch-source-index.json
library-index.json
library-audit.json
```

`library-index.json` is the cross-class runtime discovery catalog. It includes root-relative Type variants, LODs, proxy/footprint metadata, runtime resource cost, mobile optimization reasons, quality, host type and asset-integrity state.

Library-level cost summaries include total/max triangle counts, draw-call estimates, texture memory and counts of families recommended for geometry/material/texture optimization.

`library-audit.json` independently checks family IDs and all referenced primary/variant/LOD/thumbnail assets, including path traversal outside the library root.

Standalone audit:

```powershell
python tools/audit_library.py --library 'D:\axion-family-library' --fail-on-warning
```

See `docs/LIBRARY_FORMAT.md`.

## Local validation

One command runs the current GPU-safe validation gate:

```powershell
python tools/validate_local.py
```

It runs pure-Python regressions plus focused Blender 5.2 smokes for semantics, Window capability, transform safety, batch cleanup, staged export rollback, mobile LOD/runtime cost and batch provenance.

When GPU/render contention is no longer a concern:

```powershell
python tools/validate_local.py --full
```

`--full` additionally runs the broad `run_all.py` suite including thumbnail rendering. Optional real-corpus and golden hardening comparison arguments are documented in `tests/blender_runtime/README.md`.

## Schema v2

`schema.py` validates:

- identity/class/version;
- units/coordinate systems;
- dimensions/Types;
- member roles and rules;
- materials;
- hosting;
- geometry variants;
- thumbnails;
- runtime proxy;
- runtime geometry/resource cost;
- mobile budget metadata;
- optional geometry LODs;
- safe relative runtime asset URIs;
- export warnings.

See `docs/FAMILY_FORMAT.md`.

## Project structure

```text
family_types/              exact class contracts and semantic analysis
generators/                class-specific procedural geometry
core.py                    canonical family transforms/storage/base export
typed.py                   staged typed manifest/export transaction
variants.py                baked saved-Type GLB variants
runtime_proxy.py           selection/collision/plan proxy
runtime_cost.py            evaluated geometry/material/texture cost
mobile_budget.py           class-specific mobile budgets + recommendations
lod.py                     non-destructive LOD derivatives
geometry_export.py         state-safe selected-object GLB export
prepare.py                 conservative loose-part preparation
preflight.py               source-risk inspection
quality.py                 semantic quality gate
hosting.py                 Door/Window hosting/plan semantics
materials.py               runtime material metadata
family_path.py             folder -> exact Family Class resolver
batch_cleanup.py           snapshot-based per-asset Blender cleanup
batch_source_index.py      same-scope batch provenance/stale diagnostics
batch.py                   library conversion/review/index/audit
batch_cli.py               strict headless Blender library factory
catalog.py                 cross-class runtime library index
library_audit.py           package/file integrity audit
schema.py                  Axion family schema-v2 validation
hardening.py               real-asset hardening metrics
hardening_compare.py       golden-vs-expanded corpus comparison
tools/validate_local.py    consolidated local validation gate
tools/                     pure-Python production utilities
tests/                     pure-Python + Blender runtime tests
```

## Development status

The validated v0.5 foundation and seven-model real-asset hardening baseline are stable. The larger v0.7 production/mobile layer — transform hardening, staged overwrite safety, resource budgets, library/source integrity, headless processing and opt-in LOD generation — is implemented on `main` but is **not yet claimed Blender-runtime validated**. Keep LOD default OFF until the planned consolidated local Blender 5.2 pass is green.

There is intentionally **no GitHub Actions workflow** in this repository.
