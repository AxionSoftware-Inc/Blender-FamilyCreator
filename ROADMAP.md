# Blender Family Creator Roadmap

## Product goal

Convert large numbers of existing Blender/FBX/OBJ/GLB assets into reusable BIM families with as little manual cleanup as possible.

The project optimizes for **library throughput + trustworthy automatic conversion**, not for reproducing every Revit Family Editor feature.

A difficult or ambiguous asset should be routed to review rather than silently exported as a broken family.

## Current validated baseline — v0.5

Status: **implemented and Blender 5.2 runtime validated** on deterministic synthetic assets.

The reusable runtime harness is under `tests/blender_runtime/` and the detailed baseline is recorded in `BLENDER_5_2_TEST_REPORT.md`.

Current capabilities include:

- typed Family Classes instead of one universal scaler;
- semantic member-role classification;
- per-class MOVE / STRETCH / FIXED rules;
- CENTER / MIN / MAX family-axis anchors;
- immutable canonical transforms;
- class-specific semantic parameters;
- procedural/semantic generators for the main registered classes;
- Family Types / parameter snapshots;
- baked GLB geometry variants per saved Type;
- Door / Window wall hosting, opening and plan metadata;
- plumbing semantics;
- evaluated/modifier-aware bounding boxes;
- hierarchy preservation for Empty/Armature helper parents;
- conservative Auto Prepare / loose-parts splitting;
- semantic Quality Gate + source Preflight;
- thumbnail generation;
- runtime selection/collision/plan proxy metadata;
- material/PBR metadata;
- schema v2 validation;
- collision-safe Family IDs;
- exact-class Batch Factory;
- mixed AUTO_FOLDER conversion with no silent Generic fallback;
- `batch-report.json`;
- `review-queue.json`;
- cross-class `library-index.json`;
- transactional cleanup after export failures;
- Blender 5.2 registration, GLB round-trip, variants, thumbnails, batch and cleanup runtime tests.

The deterministic Blender 5.2 baseline passed all registered Family Classes at the time of validation. This does **not** yet prove behavior across arbitrary downloaded/vendor topology and importer quirks.

---

## Current milestone — v0.6 Real Asset Hardening

Status: **in progress**.

Purpose: measure and fix the highest-frequency problems found in real downloaded/vendor assets before adding another large feature layer.

See `docs/REAL_ASSET_HARDENING.md`.

### Tooling

- `tests/blender_runtime/run_real_assets.py`
- `hardening.py`
- `hardening-report.json`

The hardening report aggregates:

- conversion success rate;
- automatic acceptance rate;
- results by Family Class;
- results by source format;
- average quality score;
- average semantic-role coverage;
- normalized review/failure reasons;
- example source files for repeated failure patterns.

### Initial corpus target

Build a mixed local corpus containing representative:

- Sofa / Table / Chair / Bed;
- Door / Window;
- Cabinet / Wardrobe / Shelf / Kitchen;
- Stair;
- Toilet / Sink / Bathtub;
- BLEND / FBX / OBJ / GLB/GLTF sources;
- multiple vendor/source styles.

The source models should remain local unless their licenses permit redistribution.

### Hardening priorities

1. importer/runtime crashes and partial exports;
2. wrong units, roots, transforms or hierarchy;
3. missing required semantic roles;
4. generator geometry failures;
5. repeated UNKNOWN-role patterns;
6. excessive false-positive review flags;
7. vendor-specific material/hierarchy quirks;
8. cosmetic issues.

### Target gates

Engineering targets for supported, reasonably prepared assets:

- >= 95% conversion success;
- >= 80% automatic acceptance in core classes;
- no recurring batch cleanup leak;
- no partial package after failed export;
- every automaticReady manifest passes schema validation;
- library-index URIs resolve correctly;
- FBX, OBJ, GLB and BLEND each exercised with real assets.

These are targets for the hardening corpus, not claims about current unknown third-party assets.

---

## v0.7 — Mobile LOD and Geometry Budgets

Start after the real-asset pipeline is stable enough that geometry optimization is not hiding classifier/import bugs.

Planned:

- LOD0 / LOD1 / LOD2 strategy;
- per-class polygon budgets;
- optional automatic mesh simplification;
- preserve silhouette / openings / thin hardware where possible;
- texture resolution budgets;
- material consolidation diagnostics;
- library metadata for triangle/vertex/texture cost;
- selection/collision proxy refinement;
- optional meshopt / glTF compression path;
- mobile-oriented validation thresholds;
- batch report fields for runtime cost.

The high-quality source family remains the authoring truth; LOD output is a runtime derivative.

---

## v0.8 — Native Axion Runtime Integration

Planned:

- native Axion family importer;
- `library-index.json` ingestion;
- thumbnail/search/category browser;
- baked Type switching;
- runtime material replacement;
- hosted Door/Window insertion into walls;
- opening cuts;
- plan representation;
- runtime proxy selection/culling;
- placement/facing/hand-flip semantics;
- package migration when schema versions evolve.

Progressively enable true runtime-parametric generation only for classes where it is simpler/safer than switching baked geometry.

---

## v0.9 — Advanced Parametric Deformation

The original "Smart Stretch Zones" concept remains useful, but it is intentionally deferred until real-asset data shows where object-level rules are insufficient.

Potential work:

- vertex/zone-level deformation;
- fixed end zones + stretch middle zones;
- reference planes;
- deformation weights;
- Geometry Nodes/Lattice based deformation where appropriate;
- hardware-preserving deformation for single connected meshes;
- formula parameters;
- min/max constraints;
- nested families.

Examples:

- a single connected door-frame mesh whose corners must remain rigid while rails stretch;
- a monolithic cabinet whose handle/profile thickness must stay constant;
- a one-piece sofa whose arms remain fixed while only the center region grows.

This should be driven by measured hardening failures, not implemented universally in advance.

---

## Later library-production work

Possible later milestones:

- automatic type generation from dimension ranges;
- manufacturer/model metadata;
- tags and search synonyms;
- bulk material normalization;
- source-license/attribution metadata;
- validation contact sheets;
- optional human approval states;
- large library migrations;
- CLI/headless farm processing;
- content deduplication / near-duplicate detection.

## Design principles

1. **Exact Family Class first.** Sofa, Door, Stair and Sink do not share one deformation contract.
2. **Measure before generalizing.** Real corpus failure frequency decides what gets fixed first.
3. **Never silently guess dangerous semantics.** Review is preferable to a plausible-looking broken BIM family.
4. **Canonical source state must not drift.** Rebuilds and Type switching must remain idempotent.
5. **Batch work must be transactional and leak-resistant.** Hundreds of assets should not pollute the Blender process.
6. **Mobile runtime cost is a derivative concern.** First make the family semantically correct, then optimize LOD/runtime geometry.
7. **Keep Blender-specific generation out of the mobile engine when baked variants are sufficient.** Implement runtime-parametric behavior only where it clearly pays off.
