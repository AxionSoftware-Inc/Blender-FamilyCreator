# Blender 5.2 Runtime Validation Report

Date: 2026-09-09

Repository: `AxionSoftware-Inc/Blender-FamilyCreator`

The checkout was cloned because no local `Blender-FamilyCreator` checkout was
present, then updated with `git pull --ff-only origin main`. The repository was
left on `main`. `.github/workflows` remains absent and no license was added.

## Runtime

| Item | Result |
| --- | --- |
| Blender | 5.2.0 LTS, build `fbe6228777e7` |
| Blender Python | 3.13.13 |
| Executable | `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` |
| Render engine exposed | `BLENDER_EEVEE` |
| GLTF export/import operators | Available and exercised |
| OBJ import operator | Available (`bpy.ops.wm.obj_import`) |
| `bpy.data.batch_remove` | Available |
| `children_recursive` | Available |

The trivial background script successfully imported `bpy`, executed an object
operator, and reported the runtime version and executable path.

## Commands

```powershell
git checkout main
git pull --ff-only origin main

& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --version
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python tests/blender_runtime/run_all.py

python -m unittest discover -s tests -v
```

The reusable Blender command is also documented in
`tests/blender_runtime/README.md`.

## Results

- Addon registration passed: register → unregister → register in one Blender
  process, with no duplicate registration or cleanup errors.
- Blender runtime harness: **15/15 checks passed**.
- Existing pure-Python regression suite: **43/43 tests passed**.
- All actual exported manifests were revalidated with the repository's schema
  validator.

Runtime-tested Family Classes:

`GENERIC`, `SOFA`, `TABLE`, `CHAIR`, `BED`, `CABINET`, `WARDROBE`, `SHELF`,
`KITCHEN_BASE`, `KITCHEN_WALL`, `DOOR`, `WINDOW`, `STAIR`, `TOILET`, `SINK`,
and `BATHTUB`.

The harness covers semantic roles and generator behavior for seats/arms/backs/
legs, table tops/legs, chair seat height, mattress height, casework panel and
shelf repetition, hosted Door/Window metadata, stair tread/riser solving,
fixture-specific plumbing parameters, hierarchy preservation, rotated and
mirrored/unapplied transforms, evaluated Solidify/Array/Bevel bounds, loose
part splitting and all requested split safeguards.

## Export and runtime package checks

- GLB export works in Blender 5.2 using `export_format="GLB"`, selection-only,
  applied transforms, extras, no animation and Y-up settings.
- A family GLB was imported back into Blender and contained exportable members;
  templates were excluded and generated members were included.
- Baked variants work. The sofa test exported `Default`, `2-seat`, `3-seat`
  and `4-seat` variants, verified all files, validated `geometryVariants` and
  `geometryStrategy`, imported every variant, and confirmed dimensions differ.
- Repeated variant export is idempotent for the tested package.
- The active Type, semantic parameters and generator revision were restored
  after variant export.
- Thumbnail rendering works at 512×512 PNG with transparent output. The image
  was loaded back and verified non-blank. Camera, render settings, visibility,
  temporary camera/lights and temporary datablocks were restored/removed.
- Intentional thumbnail failure remained non-fatal and was recorded in
  `exportWarnings`.
- Runtime proxy metadata passed schema validation. Selection/collision bounds,
  type bounds, plan footprint and Door/Table MIN-Z behavior were checked.

## Batch and catalog checks

The harness generated a local deterministic asset library and ran:

1. Exact-class SOFA batch: 1 converted, 0 failed.
2. `AUTO_FOLDER` batch: 6 discovered, 5 converted, 1 rejected unknown asset.

Resolved AUTO_FOLDER counts were:

```text
DOOR: 1
SOFA: 1
STAIR: 1
TABLE: 1
WINDOW: 1
```

The final shared library index contained 6 families, including the prior exact
SOFA batch, with class counts `DOOR=1`, `SOFA=2`, `STAIR=1`, `TABLE=1`, and
`WINDOW=1`. Manifest, thumbnail and variant URIs were library-root-relative,
family IDs were unique, host/proxy/quality fields were present, and all indexed
manifests passed schema validation. Unknown folders were rejected rather than
silently converted to GENERIC. Collision-safe output-key resolution was also
checked.

Batch cleanup left zero objects after each conversion and did not grow the
owned mesh/material/image/camera/light counts across the exact and AUTO_FOLDER
runs. No global orphan purge was used.

Failure transactions were exercised for an invalid export path, an invalid
saved Type, missing required Door roles, an intentional generator failure, and
an intentional thumbnail failure. Partial package files were removed where
appropriate, the batch/library output was preserved, and an unrelated sentinel
file survived.

## Bugs fixed

### Anchored base matrices were captured before Blender's view layer update

`create_family()` could capture world-space member translations as if they were
root-local immediately after creating and positioning the family Empty. This
made MIN-Z families such as TABLE and DOOR move upward on dimension changes.
The fix synchronizes the view layer before and after parenting, before the
canonical matrix capture.

### Generator RNA callbacks could undo generated geometry

Procedural generators update matrices and enum rule properties as one logical
operation. Blender RNA update callbacks could reapply the canonical family
mid-rebuild and silently restore old geometry. Generator rebuilds now run in a
small `bfc_applying` transaction, suppressing intermediate callbacks while
preserving the existing Family Class architecture.

## Commits

- `1f9a9e5` — Fix Blender 5.2 anchored transforms and generator rebuilds
- A second commit adds this report and `tests/blender_runtime/` with the
  reusable harness and instructions.

## Known limitations

- The runtime suite intentionally uses deterministic synthetic Blender assets;
  it does not claim coverage of vendor-specific FBX/OBJ importer quirks or
  downloaded third-party topology.
- The exercised local batch library uses `.blend` and `.glb` inputs. FBX/OBJ
  operator availability was audited, but those formats were not required for
  the deterministic batch result.
- Thumbnail tests run with Blender's available Eevee engine; no separate
  Cycles-only render path was required by this addon.

