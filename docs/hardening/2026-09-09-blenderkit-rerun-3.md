# BlenderKit real-asset hardening — rerun 3 golden baseline

Date: 2026-09-09

Validated production state: `main` through `ad4a728` for the measurement fixture correction. The production semantic changes being measured were already on `main`; `ad4a728` only changed the synthetic Window capability smoke depth so it did not intentionally trigger preflight.

## Validation

- Pure Python: 63 passed, 0 failed
- Blender 5.2 runtime suite: 15 passed, 0 failed
- Semantic refinement smoke: PASS
- Window capability smoke: PASS
- Real assets discovered: 7
- Converted: 7
- Failed: 0
- automaticReady: 3
- needsReview: 4
- Conversion success: 100%
- Automatic acceptance: 42.86%

## Review-frequency snapshot

```text
LOW_ROLE_COVERAGE: 3
MISSING_REQUIRED_ROLE: 1
NON_UNIFORM_SCALE: 2
HEAVY_GEOMETRY: 1
MIXED_SCENE_SUSPECTED: 2
MISSING_RECOMMENDED_ROLE: 2
GENERATOR_PARAMETER_AUTO: 1
```

Zero in this run:

```text
GENERATOR_AUTO_OR_MISSING_SEMANTICS
GENERATOR_NO_CHANGE
GENERIC_OBJECT_NAMES
CONVERSION_FAILED
```

## Class snapshot

### BED

- 2 converted
- 1 automaticReady
- average score: 87.5
- average role coverage: 85.38%

`bed.blend`:

- score 99
- role coverage 98.04%
- automaticReady true
- HEADBOARD 1
- BASE 25
- DECOR 23
- MATTRESS 1
- UNKNOWN 1
- piping/welt-style parts now classify as DECOR
- misspelled `mattres` is recognized as MATTRESS

`bed2.blend`:

- score 76
- role coverage 72.73%
- automaticReady false
- existing MATTRESS remains correct
- BedCover parts classify as DECOR
- missing recommended BASE remains a review reason

### WINDOW

- 3 converted
- 2 automaticReady
- average score: 96.67
- average role coverage: 100%

`window.blend`:

- score 100
- role coverage 100%
- automaticReady true
- FRAME_LEFT 1
- WINDOW_SASH 4
- HARDWARE 8
- separateFrame true
- separateGlass false
- parametricFrameWidth true
- materialAddressableGlass false

`window2.blend`:

- score 100
- role coverage 100%
- automaticReady true
- WINDOW_SASH 3
- GLASS 2
- separateFrame false
- separateGlass true
- parametricFrameWidth false
- materialAddressableGlass true
- generator reasonCode: `NO_SEPARATE_FRAME`
- baked source geometry is accepted instead of treating absent separate frame objects as invalid semantics

`windowcurved.blend`:

- score 90
- role coverage 100%
- automaticReady false only because of non-uniform scale review
- WINDOW_SASH 3
- GLASS 1
- FRAME_RIGHT 1
- FRAME_LEFT 1
- `L fram _Part_02` -> FRAME_RIGHT
- `L fram _Part_03` -> FRAME_LEFT
- generator changed true and applied frame geometry to two members

### TABLE

No intentional behavior change.

`metal-table-chair-set.blend`:

- score 0
- role coverage 0%
- automaticReady false
- mixed scene remains review-only
- non-uniform scale remains review-only and is not auto-applied

`table-chair-set.blend`:

- score 51
- role coverage 14.63%
- automaticReady false
- heavy source geometry remains flagged (~682k polygons in this corpus)
- table/chair scene remains intact and review-only

## Integrity

- All 7 staging assets remained SHA-256 identical to their original BlenderKit files.
- No source assets were modified.
- No GitHub Actions were added.
- No production threshold relaxation was made as part of the rerun measurement.
- Runtime cleanup remained stable.

## Interpretation

This run is the first useful golden mini-corpus baseline:

- transport/export remains 100% successful;
- BED semantic hardening produced a real automaticReady asset;
- WINDOW semantic/capability separation produced 2/3 automaticReady assets;
- the remaining curved Window is semantically complete and held only by the deliberate non-uniform-scale review policy;
- TABLE mixed scenes remain intentionally unresolved rather than being destructively trimmed.

Do not continue optimizing only these seven assets. The next validation stage is an expanded BED/WINDOW corpus from additional models, vendors and formats. Use the hardening comparison tool to preserve these seven as a no-regression overlap gate while measuring the new assets separately.
