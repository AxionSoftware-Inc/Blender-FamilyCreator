# Real Asset Hardening

This milestone validates Blender Family Creator against real downloaded/vendor assets after the deterministic Blender 5.2 runtime suite has passed.

The goal is not to add features quickly. The goal is to measure where real assets break the current classifier, preparation, generator and import/export assumptions, then strengthen the highest-frequency failure modes.

## Baseline already proven

The deterministic Blender 5.2 suite currently covers all registered Family Classes and validates registration, semantic analysis, generators, GLB round-trip, baked Types, thumbnails, runtime proxy metadata, batch conversion, AUTO_FOLDER, cleanup and failure transactions.

Real Asset Hardening begins from that baseline rather than replacing it.

The first real BlenderKit corpus baselines are recorded in:

```text
docs/hardening/2026-09-09-blenderkit-baseline.md
docs/hardening/2026-09-09-blenderkit-rerun-1.md
```

That corpus contains 7 `.blend` assets across BED, TABLE and WINDOW. All 7 convert successfully, but semantic coverage remains the main review bottleneck. Hardening therefore focuses on class-specific semantic understanding rather than relaxing quality thresholds.

## Recommended corpus

Use assets that may legally be tested locally. Keep third-party source models out of this repository unless their license explicitly permits redistribution.

First useful corpus target:

- SOFA: 20–30 assets
- TABLE: 15–20 assets
- CHAIR / BED: 10–15 each
- DOOR: 15–20 assets
- WINDOW: 15–20 assets
- CABINET / WARDROBE / SHELF / KITCHEN: 20+ combined
- STAIR: 10+ assets
- TOILET / SINK / BATHTUB: 10+ combined

Formats should intentionally be mixed:

- `.blend`
- `.fbx`
- `.obj`
- `.glb` / `.gltf`

Include more than one vendor/source style when possible. A corpus of 100 similar models exported by one tool is less useful than a smaller mixed corpus.

## Folder layout

AUTO_FOLDER expects recognizable semantic folders:

```text
real-assets/
  sofas/
  tables/
  chairs/
  beds/
  cabinets/
  wardrobes/
  shelves/
  kitchen_base/
  kitchen_wall/
  doors/
  windows/
  stairs/
  toilets/
  sinks/
  bathtubs/
```

Unknown folders are rejected rather than silently converted to GENERIC.

## Run command

From the repository root on the validated Blender 5.2 installation:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_real_assets.py -- `
  --input D:\real-assets `
  --output D:\axion-family-hardening `
  --family-class AUTO_FOLDER
```

Useful options:

```text
--family-class SOFA
--no-glb
--no-baked-types
--no-thumbnail
--no-auto-split
--stop-on-error
--max-loose-islands 64
```

## Outputs

The normal Batch Factory outputs remain:

```text
batch-report.json
review-queue.json
library-index.json
```

The hardening runner additionally writes:

```text
hardening-report.json
```

The hardening report contains:

- conversion success rate;
- automatic acceptance rate;
- class-by-class score and semantic-role coverage;
- class-by-class average generic-object-name share;
- format-by-format conversion / acceptance results;
- normalized review reasons;
- semantic refinement frequency;
- per-asset semantic refinement counts;
- unresolved UNKNOWN member samples with normalized span/center values;
- generator changed/message diagnostics;
- example source files for the most common reasons.

Normalized reasons include:

```text
LOW_ROLE_COVERAGE
MISSING_REQUIRED_ROLE:<roles>
MISSING_RECOMMENDED_ROLE:<roles>
GENERIC_OBJECT_NAMES
MIXED_SCENE_SUSPECTED
NON_UNIFORM_SCALE
UNAPPLIED_SCALE
MIRRORED_TRANSFORM
SHAPE_KEYS
ARMATURE
HEAVY_GEOMETRY
SUSPICIOUS_UNITS_OR_ORIENTATION
EXPORT_WARNING
GENERATOR_PARAMETER_AUTO
GENERATOR_MISSING_SEMANTICS
GENERATOR_AUTO_OR_MISSING_SEMANTICS
GENERATOR_NO_CHANGE
CONVERSION_FAILED
```

`GENERIC_OBJECT_NAMES` is only reported when generic names coincide with low semantic coverage. A family is not rejected merely because its objects are named `Cube.001` if geometry-based semantics are otherwise strong.

`MIXED_SCENE_SUSPECTED` is currently a conservative review signal, not an automatic deletion/filter step. For example, a `table-chair-set` should remain reviewable until explicit multi-item isolation logic can prove which objects belong to the table family.

Generator no-change diagnostics are descriptive only. `GENERATOR_PARAMETER_AUTO` means source geometry was intentionally preserved because a semantic parameter is still Auto/zero. `GENERATOR_MISSING_SEMANTICS` means the generator could not find the role it needs. When a generator message itself combines both possibilities, `GENERATOR_AUTO_OR_MISSING_SEMANTICS` preserves that ambiguity rather than inventing certainty.

## Family-level second-pass refinement

Per-object role classification remains the first pass. Some real assets require comparison across the entire family, so class modules may optionally run a second-pass refinement after every source member has been measured.

Current second-pass refinements are intentionally narrow:

- **BED**: when no MATTRESS exists, compare broad horizontal BASE/UNKNOWN candidates and promote only the strongest relative upper slab when the candidate separation is sufficiently confident. Explicit structural/decor names remain protected, and a lone BASE is not silently relabeled.
- **WINDOW**: preserve existing confident roles, explicit sash semantics and GLASS, then fill only missing frame-edge roles from UNKNOWN or generic sash candidates whose edge position and dominant orientation provide enough confidence. Near-tied candidates remain unresolved/reviewable.

Refined members are tagged diagnostically with values such as:

```text
BED_MATTRESS_CANDIDATE
WINDOW_FRAME_EDGE_CANDIDATE
```

These tags do not lower quality thresholds. They exist so corpus deltas can prove whether a new family-level heuristic actually caused an improvement.

## Triage rule

Do not optimize for one unusual asset first.

After each corpus run:

1. Sort `reviewReasons` by count.
2. Inspect the top reason and its example assets.
3. Inspect `refinementFrequency` to see whether second-pass logic actually fired.
4. For unresolved semantics, inspect each asset's `unknownMemberSamples` before widening classifier thresholds.
5. Inspect generator messages when a generator did not change geometry.
6. Decide whether the problem belongs to importer compatibility, preparation, role classification, generator logic, preflight policy or source quality.
7. Make the smallest class-specific/general fix that addresses the repeated pattern.
8. Add a deterministic regression case when practical.
9. Rerun the Blender 5.2 synthetic suite and focused refinement smoke test.
10. Rerun the **same real corpus** before adding new assets.
11. Compare acceptance and failure rates before/after.
12. Only then expand the corpus/formats.

A fix should improve the corpus without making unrelated classes less reliable.

## Initial targets

These are engineering targets, not claims about the current real-asset corpus:

- conversion success: >= 95% for supported, non-corrupt source files;
- automatic acceptance: >= 80% for reasonably prepared assets in the core classes;
- no silent Generic fallback in AUTO_FOLDER;
- no batch memory/object growth across long runs;
- no partial package left after a failed export;
- every automaticReady package passes schema validation;
- every exported GLB/thumbnail URI resolves from the library index.

An asset can convert successfully and still be routed to review. That is preferable to silently accepting a broken BIM family.

## What to fix first

Priority order:

1. crashes / failed imports / partial exports;
2. wrong family origin, units or transforms;
3. missing required semantic roles;
4. generators producing invalid geometry;
5. high-frequency UNKNOWN-role patterns;
6. excessive false-positive preflight reviews;
7. vendor-specific material / hierarchy quirks;
8. low-value cosmetic issues.

## Current policy decisions

- Generic vendor names should be handled by geometry fallback where possible, not by lowering semantic thresholds.
- Global quality thresholds are not reduced merely to improve automaticReady percentages.
- Non-uniform scale remains a review signal; it is not auto-applied because modifiers, children and rigged assets can make transform application destructive.
- Heavy geometry remains reviewable until the LOD/mobile-budget phase provides a deliberate simplification pipeline.
- Mixed furniture sets are flagged rather than silently trimmed to one item.
- Ambiguous second-pass candidates remain UNKNOWN rather than being force-classified.

## Exit criteria

Real Asset Hardening is considered mature enough to move focus to mobile LOD/budget work when:

- a mixed corpus of at least ~100 representative assets can be run repeatedly;
- top review reasons are understood and stable;
- core classes meet acceptable conversion/automaticReady rates;
- FBX, OBJ, GLB and BLEND have each been exercised with real assets;
- no recurring cleanup leak appears during long batch runs;
- remaining failures are mostly truly ambiguous or source-specific rather than systemic.

After this milestone, the next primary workstream is LOD0/LOD1/LOD2 generation, polygon/texture budgets and optional mobile geometry compression.
