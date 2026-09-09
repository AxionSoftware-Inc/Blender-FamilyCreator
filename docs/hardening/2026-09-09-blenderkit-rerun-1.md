# BlenderKit real-asset hardening — rerun 1

Date: 2026-09-09

This is the first before/after rerun of the same seven local BlenderKit-derived staging assets after the initial BED/WINDOW classifier hardening. Third-party source files are not stored in this repository.

## Validation

- Pure Python: **49/49 passed**
- Blender 5.2 runtime: **15/15 passed**
- Real assets discovered: **7**
- Converted: **7**
- Failed: **0**
- automaticReady: **0**
- needsReview: **7**

## Review reason frequency

```text
LOW_ROLE_COVERAGE: 6
MISSING_REQUIRED_ROLE: 4
NON_UNIFORM_SCALE: 2
HEAVY_GEOMETRY: 1
MIXED_SCENE_SUSPECTED: 2
MISSING_RECOMMENDED_ROLE: 2
GENERATOR_NO_CHANGE: 4
GENERIC_OBJECT_NAMES: 0
SUSPICIOUS_UNITS_OR_ORIENTATION: 0
CONVERSION_FAILED: 0
```

The important delta from the initial baseline is:

```text
MISSING_REQUIRED_ROLE: 5 -> 4
```

Conversion remained 7/7 with no threshold relaxation.

## BED

- `bed.blend`: `MATTRESS` is still missing; remains LOW_ROLE_COVERAGE + MISSING_REQUIRED_ROLE.
- `bed2.blend`: mattress remains correctly detected; still LOW_ROLE_COVERAGE.

The next BED change should therefore use family-level candidate comparison rather than globally widening the single-member bbox threshold.

## WINDOW

- `window.blend`: role coverage improved **23.1% -> 38.5%** and `FRAME_LEFT` is now detected.
- `window2.blend`: `GLASS` improved from zero to two detected parts; required frame semantics remain missing.
- `windowcurved.blend`: role coverage improved **50% -> 66.7%**; required frame semantics remain incomplete.

The direction is useful, but frame detection still needs family-level edge candidate comparison. The next pass should preserve explicit sash/glass semantics and fill only missing frame edges when the geometry evidence is sufficiently strong.

## TABLE

Both table-chair sets remain review-only, intentionally:

- `metal-table-chair-set.blend`: MIXED_SCENE_SUSPECTED + NON_UNIFORM_SCALE + missing TOP.
- `table-chair-set.blend`: MIXED_SCENE_SUSPECTED + HEAVY_GEOMETRY.

No chair/stool geometry was automatically deleted and non-uniform scale was not automatically applied.

## Regression fixed during rerun

The first WINDOW hardening accidentally allowed an explicitly named `sash` to be reclassified as `GLASS`. This was fixed narrowly in commit:

`95b8d91` — Preserve explicit window sash semantics

Only generic object names may use the geometry-only glazing fallback now.

## Next comparison target

Keep the same seven staging assets unchanged and measure the next second-pass refinement against this rerun.

Primary desired deltas:

- keep conversion at 7/7;
- reduce `MISSING_REQUIRED_ROLE` below 4 without lowering quality thresholds;
- resolve `bed.blend` mattress only if family-level candidate evidence is strong;
- improve WINDOW frame coverage without repurposing explicit sash/glass;
- keep both mixed TABLE sets in review;
- inspect `GENERATOR_NO_CHANGE` only after semantic coverage improves.
