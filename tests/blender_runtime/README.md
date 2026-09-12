# Blender 5.2 runtime harness

This harness runs the addon inside the installed Blender runtime. It creates
deterministic synthetic assets, exercises exact-class generators, exports and
re-imports GLB packages, renders thumbnails, tests variants and batch conversion,
and writes machine-readable output under `artifacts/` where applicable.

## Main deterministic suite

Run from the repository root:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_all.py
```

This remains the broad registration/class/generator/export/thumbnail/batch
regression suite.

## Post-hardening GPU-free gates

The following focused tests do **not** render thumbnails and are safe to run in
background mode without GPU rendering.

### Rotated transform + source isolation safety

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_transform_safety.py
```

Checks:

- rotated/off-axis `STRETCH` does not introduce matrix shear;
- canonical rotation remains stable;
- repeated `apply_family()` is idempotent;
- 90-degree local/family axis mapping is correct;
- source canonical shear is detected by Preflight;
- separated multi-asset spatial clusters are routed to review.

Expected final line:

```text
TRANSFORM_SAFETY: PASS
```

### Snapshot-based batch cleanup

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_cleanup_smoke.py
```

Checks:

- Mesh -> Material -> Image cleanup dependencies;
- newly-created loose datablocks;
- imported temporary Collections;
- zero post-import leftovers;
- pre-existing zero-user data survives, proving no global orphan purge is used.

Expected final line:

```text
CLEANUP_SMOKE: PASS
```

### Non-destructive mobile LOD

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_lod_smoke.py
```

Checks:

- primary LOD0 GLB exists;
- LOD1/LOD2 reduce evaluated triangle count;
- source mesh/datablock remains unchanged;
- no temporary LOD object/mesh leak;
- LOD files resolve through `library-index.json` and `library-audit.json`.

Expected final line:

```text
LOD_SMOKE: PASS
```

LOD generation remains **opt-in/default OFF** until this gate and the main suite
are green on the target Blender 5.2 installation.

## Focused semantic smoke tests

Family-level BED/WINDOW second-pass refinement:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_refinement_smoke.py
```

Baked Window validity versus separate-frame edit capability:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_window_capability_smoke.py
```

Expected final lines:

```text
SEMANTIC_REFINEMENT_SMOKE: PASS
WINDOW_CAPABILITY_SMOKE: PASS
```

## Pure-Python regressions

Blender-facing checks intentionally do not use normal system Python. Pure logic,
schema, catalog, hardening and mobile-budget tests remain:

```powershell
python -m unittest discover -s tests -v
```

Important newer coverage includes:

- mobile budget policy v2;
- runtime texture/draw-call schema validation;
- library runtime-cost aggregation;
- LOD/catalog/audit integrity;
- hardening reasons for shear and multi-asset spatial clusters.

## Headless production factory smoke

After focused gates pass, run a small disposable AUTO_FOLDER corpus through the
actual production entry point before testing hundreds of assets:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python batch_cli.py -- `
  --input D:\bfc-smoke-assets `
  --output D:\bfc-smoke-library `
  --class AUTO_FOLDER `
  --lods `
  --no-thumbnails `
  --json-summary D:\bfc-smoke-library\summary.json
```

For a clean run verify:

- failed = 0 for supported synthetic/smoke assets;
- cleanup warnings = 0;
- cleanup leftover datablocks = 0;
- missing library assets = 0;
- library audit complete = true.

## Real Asset Hardening

After the deterministic and post-hardening suites are green, use
`run_real_assets.py` against a local mixed corpus of downloaded/vendor models.
Keep third-party source assets out of this repository unless their licenses
permit redistribution.

Recommended AUTO_FOLDER layout and the complete hardening process are documented
in `docs/REAL_ASSET_HARDENING.md`.

Example:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_real_assets.py -- `
  --input D:\real-assets `
  --output D:\axion-family-hardening `
  --family-class AUTO_FOLDER
```

In addition to normal batch outputs (`batch-report.json`, `review-queue.json`,
`library-index.json`, `library-audit.json`), the real-asset runner writes
`hardening-report.json` with conversion/automatic-acceptance rates,
class/format metrics, normalized review reasons, semantic refinement frequency,
semantic capability flags, unresolved member samples and generator messages.

Do not tune role-classifier heuristics further from synthetic tests alone. New
classifier changes should be driven by repeated patterns in the expanded real
asset corpus.
