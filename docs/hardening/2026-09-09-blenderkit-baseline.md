# BlenderKit Real-Asset Hardening Baseline — 2026-09-09

This is the first recorded real downloaded-asset corpus baseline after the deterministic Blender 5.2 runtime suite passed.

The original third-party BlenderKit source assets are **not** stored in this repository. They were tested from a local staging copy and left unchanged.

## Corpus

- 7 real assets
- all source files were `.blend`
- Family Classes: BED (2), TABLE (2), WINDOW (3)
- Batch mode: `AUTO_FOLDER`

## Baseline result

```text
Discovered:        7
Converted:         7
Failed:            0
Automatic ready:   0
Needs review:      7
Conversion rate:   100%
Auto acceptance:   0%
```

## Baseline reason frequency

```text
LOW_ROLE_COVERAGE:          6
MISSING_REQUIRED_ROLE:      5
NON_UNIFORM_SCALE:          2
HEAVY_GEOMETRY:             1
CONVERSION_FAILED:          0
```

## Class observations

### BED — 2 assets

- both converted successfully;
- semantic coverage was low;
- one asset did not detect a required `MATTRESS` role;
- real vendor envelope/part placement showed that the previous mattress geometry fallback was too strict when a tall headboard shifts the normalized Z center.

### TABLE — 2 assets

- both converted successfully;
- one source was very heavy geometry;
- both filenames/scenes represented table + seating sets rather than a clean isolated table;
- one also contained non-uniform scale;
- these should remain review candidates until multi-item family isolation is explicitly implemented rather than silently discarding chairs.

### WINDOW — 3 assets

- all converted successfully;
- required frame roles were frequently missing;
- generic Blender object names such as `Cube`/`Cube.###` made name-based semantics ineffective;
- frame geometry fallback thresholds were too strict for vendor casing/frame profiles.

## Hardening response

The first hardening pass intentionally does **not** lower the quality threshold merely to improve the acceptance number.

Changes after this baseline focus on:

1. broader but still geometry-constrained BED mattress/base/headboard detection;
2. broader opening frame fallback using edge position + dominant orientation;
3. horizontal and vertical `MULLION` support with orientation-aware rules;
4. generic-name diagnostics when semantic coverage is already low;
5. explicit `MIXED_SCENE_SUSPECTED` reporting for table+seating source sets;
6. leaving non-uniform scale as review-only instead of automatically applying transforms.

## Next rerun target

Rerun the **same 7 staged assets** before adding more corpus files.

A useful improvement is:

- conversion remains 7/7;
- `MISSING_REQUIRED_ROLE` decreases from 5;
- `LOW_ROLE_COVERAGE` decreases from 6;
- BED and WINDOW improve without changing quality thresholds;
- table+chair sets remain reviewable under `MIXED_SCENE_SUSPECTED`;
- non-uniform scale and heavy geometry remain explicit source-risk reasons.

Only after the same-corpus delta is understood should the corpus expand to FBX/OBJ/GLB and more classes.
