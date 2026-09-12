# Blender Family Creator Roadmap

## Product goal

Convert large numbers of existing Blender/FBX/OBJ/GLB assets into reusable BIM families with as little manual cleanup as possible.

The project optimizes for **library throughput + trustworthy automatic conversion**, not for reproducing every Revit Family Editor feature. Ambiguous assets should be routed to review rather than silently accepted as broken BIM families.

## Validated foundation — v0.5

Status: **implemented and Blender 5.2 runtime validated** on deterministic synthetic assets.

The reusable runtime harness is under `tests/blender_runtime/`; the detailed baseline is recorded in `BLENDER_5_2_TEST_REPORT.md`.

Validated foundation includes:

- exact Family Classes and semantic roles;
- class-specific MOVE / STRETCH / FIXED rules;
- CENTER / MIN / MAX axis anchors;
- immutable canonical transforms;
- semantic parameters and class generators;
- saved Family Types;
- baked GLB variants;
- Door/Window host/plan metadata;
- evaluated/modifier-aware bounds;
- hierarchy preservation;
- conservative Auto Prepare;
- semantic Quality Gate + source Preflight;
- thumbnails;
- runtime selection/collision proxy;
- material metadata;
- schema v2;
- collision-safe Family IDs;
- exact and AUTO_FOLDER batch conversion;
- review queue + cross-class library index;
- transactional cleanup.

The original Blender 5.2 validation covered registration, GLB round-trip, variants, thumbnails, batch processing, cleanup and all registered Family Classes.

---

## v0.6 — Real Asset Hardening

Status: **active and substantially improved**.

Real BlenderKit mini-corpus history is stored in `docs/hardening/`. The golden seven-asset corpus reached:

- 7/7 conversion success;
- 3/7 automaticReady;
- BED and WINDOW semantic coverage substantially improved without lowering global thresholds;
- baked Window validity separated from separate-frame edit capability;
- non-uniform scale and mixed furniture sets remain conservative review conditions.

Hardening tooling now includes:

- `tests/blender_runtime/run_real_assets.py`;
- `hardening.py` / `hardening-report.json`;
- golden-overlap vs expanded-corpus comparison;
- duplicate corpus-key detection;
- normalized review/failure reasons;
- unknown-member geometry samples;
- semantic capability reporting;
- canonical transform-shear diagnostics;
- spatial multi-asset/multi-cluster review diagnostics.

Next semantic hardening work is **corpus expansion**, not more tuning of the same seven assets:

- additional BED/WINDOW from different vendors;
- broader SOFA/TABLE/CHAIR/CASEWORK/PLUMBING/STAIR samples;
- genuine BLEND / FBX / OBJ / GLB/GLTF sources;
- repeated-pattern fixes only after evidence from multiple new assets.

Engineering target remains >=95% conversion success and >=80% automatic acceptance for reasonably prepared core-class assets, while preserving a no-regression golden corpus.

---

## v0.7 — Mobile Cost, LOD and Production Integrity

Status: **implemented on `main`, opt-in / unvalidated until the next consolidated local Blender 5.2 gate passes**.

Implemented on `main`:

- evaluated triangulated `runtimeCost` metadata;
- used-material draw-call estimation instead of counting unused vendor slots as draw calls;
- unique material and recursive node-tree texture discovery;
- texture count, maximum texture dimension and conservative uncompressed RGBA8 memory estimates;
- per-class triangle/material/draw-call/texture budgets;
- `WITHIN_TARGET` / `OVER_TARGET` / `OVER_HARD_LIMIT` diagnostics;
- machine-readable optimization reasons for geometry, materials/draw calls and textures;
- independent `geometryLodRecommended`, `materialOptimizationRecommended` and `textureOptimizationRecommended` flags;
- suggested LOD1 / LOD2 ratios;
- non-destructive temporary LOD copies;
- Blender Decimate-based LOD1/LOD2 GLB derivatives;
- conservative protection for small hardware/connectors and shape-key/low-poly members;
- LOD target/meetsTarget metadata;
- partial LOD/thumbnail/variant file cleanup;
- catalog indexing of LOD/resource-cost metadata;
- library-wide triangle/draw-call/texture-memory summaries;
- missing/unsafe asset detection;
- `library-audit.json`;
- standalone library audit CLI;
- production headless `batch_cli.py` with strict integrity mode;
- leak-resistant per-asset Blender datablock snapshots instead of global orphan purge;
- partial-import failure cleanup;
- rollback-safe staged package overwrite with the new manifest committed last;
- old valid package preservation when a re-export fails;
- `batch-source-index.json` provenance for same-root reruns;
- stale-output and failed-refresh package diagnostics without automatic deletion;
- rotated/off-axis family stretch hardening that does not introduce new transform shear;
- focused GPU-safe Blender smokes for LOD, transform safety, cleanup, export transaction/state and batch provenance;
- unified `tools/validate_local.py` validation runner.

LOD remains **disabled by default** in Blender UI and batch settings until the consolidated local Blender 5.2 runtime smoke/regression pass is green.

Still planned after validation/data:

- actual material consolidation/atlas tooling, beyond current cost diagnostics;
- texture resize/transcode derivatives, beyond current texture budget diagnostics;
- silhouette-aware or class-aware simplification beyond generic Decimate;
- optional glTF mesh compression / meshopt path;
- better device/distance LOD switching policy based on real Axion tablet profiling;
- optional dedicated collision meshes.

The high-quality source family remains the authoring truth; every LOD is a runtime derivative.

---

## v0.8 — Native Axion Runtime Integration

Planned:

- native family manifest importer;
- `library-index.json` ingestion;
- thumbnail/search/category browser;
- baked Type switching;
- LOD selection based on distance/device budget;
- runtime material replacement;
- hosted Door/Window insertion and host cuts;
- plan representation;
- runtime proxy selection/culling;
- facing/hand-flip semantics;
- schema migration support.

Progressively enable true runtime-parametric generation only where it is safer/smaller than switching baked geometry.

---

## v0.9 — Advanced Parametric Deformation

Deferred until expanded real-asset data proves object-level rules are insufficient.

Possible work:

- vertex/zone-level deformation;
- fixed end zones + stretch middle zones;
- reference planes;
- deformation weights;
- Geometry Nodes/Lattice support;
- hardware-preserving deformation for monolithic meshes;
- formulas and min/max constraints;
- nested families.

This must be driven by measured failure patterns rather than implemented universally.

---

## Later library-production work

- automatic Type generation from dimension ranges;
- manufacturer/model metadata;
- tags/search synonyms;
- bulk material normalization;
- source-license/attribution metadata;
- validation contact sheets;
- approval states;
- large library migrations;
- content deduplication / near-duplicate detection;
- distributed/headless farm orchestration on top of the existing CLI.

## Design principles

1. **Exact Family Class first.** Sofa, Door, Stair and Sink do not share one deformation contract.
2. **Measure before generalizing.** Real-corpus failure frequency decides what gets fixed first.
3. **Never silently guess dangerous semantics.** Review is preferable to plausible-looking broken BIM data.
4. **Canonical source state must not drift.** Rebuilds and Type switching must remain idempotent.
5. **Batch work must be transactional and leak-resistant.** Hundreds of assets should not pollute Blender state.
6. **Semantic validity and mobile runtime cost are separate concerns.** A good family can still need LOD/material/texture optimization.
7. **LOD is derivative.** Source authoring geometry is never destructively simplified.
8. **Do not destroy previous good output on a failed refresh.** New packages validate in staging before overwrite.
9. **Do not auto-delete stale packages.** Detect and report source provenance drift first; pruning must be explicit.
10. **Keep Blender-only generation out of the mobile engine when baked geometry is sufficient.**
