# BlenderKit Real Asset Hardening — Rerun 2

Date: 2026-09-09

Corpus: unchanged 7 local BlenderKit `.blend` staging assets across BED, TABLE and WINDOW.

Source assets remained SHA-256 identical to the originals. No GitHub Actions or license changes were made.

## Validation baseline

- Pure Python: 56 passed, 0 failed
- Blender 5.2 deterministic runtime: 15 passed, 0 failed
- Semantic refinement smoke: PASS
- Real assets discovered: 7
- Converted: 7
- Failed: 0
- automaticReady: 0
- needsReview: 7

## Reason frequency

```text
LOW_ROLE_COVERAGE: 6
MISSING_REQUIRED_ROLE: 3
NON_UNIFORM_SCALE: 2
HEAVY_GEOMETRY: 1
MIXED_SCENE_SUSPECTED: 2
MISSING_RECOMMENDED_ROLE: 2
GENERATOR_PARAMETER_AUTO: 1
GENERATOR_AUTO_OR_MISSING_SEMANTICS: 2
GENERIC_OBJECT_NAMES: 0
GENERATOR_NO_CHANGE: 0
CONVERSION_FAILED: 0
```

Compared with rerun-1, `MISSING_REQUIRED_ROLE` improved from 4 to 3.

## BED

`bed.blend` improved materially:

- score: 48 -> 88
- MATTRESS: 0 -> 1
- BASE: 25 -> 24
- missing required MATTRESS: resolved
- refinement: `BED_MATTRESS_CANDIDATE = 1`
- generator changed successfully and applied mattress height

`bed2.blend` preserved its existing MATTRESS semantics.

Rerun-2 also exposed low-risk vendor naming patterns that remain useful for coverage hardening: `mattres`, `piping_*`, and `BedCover_*`.

## WINDOW

`window.blend`:

- role coverage: 38.46%
- FRAME_LEFT: 1
- WINDOW_SASH: 4
- many remaining unknown parts are tiny bolt/clip-like geometry

`window2.blend`:

- role coverage: 100%
- WINDOW_SASH: 3
- GLASS: 2
- unknown members: 0
- no separately modeled frame members

This is now treated as a product-policy distinction: a Window may be a valid baked/runtime family without independently editable frame meshes. Separate frame objects control `parametricFrameWidth` capability, not base family validity.

`windowcurved.blend`:

- role coverage: 66.67%
- WINDOW_SASH: 3
- GLASS: 1
- two unresolved parts:
  - `L fram _Part_02`, span `[0.3267, 0.1663, 0.5301]`, center `[0.3243, 0.0122, -0.3265]`
  - `L fram _Part_03`, span `[0.3267, 0.1663, 0.5301]`, center `[-0.3405, 0.0122, -0.3274]`

These are strong real-vendor frame-name candidates and motivate a narrow `fram` alias plus semantic-name-weighted frame position rule rather than globally lowering geometry thresholds.

## TABLE

Both mixed table-chair scenes remain intentionally review-only.

- `metal-table-chair-set.blend`: 0% role coverage, 26 non-uniform scale members, missing TOP
- `table-chair-set.blend`: 682,546 polygons, mixed scene, TOP/LEG detected but low overall coverage

No chair/stool deletion or automatic scale application is permitted yet.

## Next patch hypothesis

1. Recognize low-risk BED aliases (`mattres`, piping/welt/cover) to improve coverage without threshold relaxation.
2. Treat tiny opening bolts/clips as HARDWARE.
3. Use stronger name evidence for truncated frame names such as `L fram`, while leaving generic geometry edge thresholds conservative.
4. Separate Window validity from separate-frame parameterization capability.
5. Keep mixed TABLE scenes and non-uniform scale review-only.
