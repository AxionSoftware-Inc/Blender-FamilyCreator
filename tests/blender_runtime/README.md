# Blender 5.2 runtime harness

This harness runs Blender Family Creator inside the installed Blender runtime.
It combines the original deterministic suite with focused post-hardening gates
for installed-package imports, transforms, export transactions, rollback
recovery, cleanup, LOD and repeated batch provenance.

There is intentionally no GitHub Actions workflow. Local Blender 5.2 is the
runtime authority.

## Recommended entry point

From the repository root, run:

```powershell
python tools/validate_local.py
```

Default mode is **GPU-safe**. It runs:

1. pure-Python unittest discovery;
2. installed-package import smoke;
3. BED/WINDOW semantic refinement smoke;
4. Window capability smoke;
5. rotated-transform/source-isolation smoke;
6. snapshot batch-cleanup smoke;
7. export-state + staged-overwrite transaction smoke;
8. incomplete-rollback recovery smoke;
9. mobile LOD/runtime-cost smoke;
10. repeated-batch provenance/stale-output smoke.

A machine-readable summary is written to:

```text
tests/blender_runtime/artifacts/local-validation.json
```

Use `--keep-going` when you want all failing gates collected in one report.

### Full validation after GPU workloads finish

```powershell
python tools/validate_local.py --full
```

`--full` adds `tests/blender_runtime/run_all.py`, which includes thumbnail
rendering. Do not use the full mode when another workload owns the GPU if you
want to avoid render-side GPU contention.

## Main deterministic suite

Direct invocation remains available:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_all.py
```

This is the broad registration/class/generator/GLB/variant/thumbnail/batch
regression suite. It raises on failure; the validation runner trusts its exit
code rather than a hard-coded test count.

## GPU-free focused gates

### Installed-package import semantics

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_package_import_smoke.py
```

This removes the repository root from `sys.path`, changes the working directory
and loads the addon only as a package. Catalog, library audit, package-assets and
schema helpers must resolve through package-relative imports rather than an
accidental repository-root import.

Expected marker: `PACKAGE_IMPORT_SMOKE: PASS`

### Semantic refinement

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_refinement_smoke.py
```

Expected marker: `SEMANTIC_REFINEMENT_SMOKE: PASS`

### Window capability policy

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_window_capability_smoke.py
```

Expected marker: `WINDOW_CAPABILITY_SMOKE: PASS`

### Rotated transform + source isolation safety

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_transform_safety.py
```

Checks include:

- off-axis `STRETCH` does not introduce new matrix shear;
- canonical source shear is preserved and routed to review;
- repeated `apply_family()` is idempotent;
- 90-degree local/family axis mapping is stable;
- separated multi-asset spatial clusters are routed to review.

Expected marker: `TRANSFORM_SAFETY: PASS`

### Snapshot-based batch cleanup

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_cleanup_smoke.py
```

Checks include:

- Mesh -> Material -> Image dependency cleanup;
- nested imported Collections;
- pre-existing zero-user sentinels survive;
- partial importer failures are cleaned;
- cleanup diagnostics cannot mask a successful conversion.

Expected marker: `CLEANUP_SMOKE: PASS`

### State-safe transactional package export

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_export_state_smoke.py
```

Checks include:

- selection/active object restoration;
- viewport/render/`hide_set()` restoration;
- primary GLB creation;
- pre-commit failures leave a new destination empty;
- failed overwrite preserves an old valid manifest/GLB byte-for-byte;
- commit-time failure rolls back the old package.

Expected marker: `EXPORT_STATE_SMOKE: PASS`

### Incomplete rollback recovery isolation

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_rollback_recovery_smoke.py
```

Checks include:

- incomplete rollback raises an explicit recovery error;
- staged/backup files are preserved for manual recovery;
- recovery manifests are never published into the runtime catalog;
- library audit marks a recovery directory as incomplete rather than silently
  treating the library as healthy.

Expected marker: `ROLLBACK_RECOVERY_SMOKE: PASS`

### Non-destructive mobile LOD + runtime cost

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_lod_smoke.py
```

Checks include:

- LOD1/LOD2 reduce evaluated triangle count;
- source mesh/datablock remains unchanged;
- no temporary LOD object/mesh leak;
- unused vendor material slots do not inflate draw-call estimates;
- LOD files resolve through catalog and library audit.

Expected marker: `LOD_SMOKE: PASS`

LOD remains **opt-in/default OFF** until this gate and the broader local suite
are green on the target Blender 5.2 installation.

### Repeated-batch source provenance

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_batch_provenance_smoke.py
```

Checks include:

- `batch-source-index.json` is written atomically after a complete run;
- removed source -> stale package diagnostic without auto-delete;
- failed current refresh -> previous valid package is retained and reported as
  `failedRefresh` rather than silently treated as current output;
- alternating input scopes retain independent provenance history;
- catalog-build failure or rejected manifests do not advance the canonical
  source baseline;
- corrupt/invalid provenance is reported and preserved byte-for-byte instead of
  being silently overwritten;
- registry `latestScope` must equal an exact stored snapshot, not merely share
  the same input/class key.

Expected marker: `BATCH_PROVENANCE_SMOKE: PASS`

## Pure-Python regressions

```powershell
python -m unittest discover -s tests -v
```

Important newer coverage includes:

- mobile budget policy v2 and optimization-reason flags;
- runtime texture/draw-call resource metadata;
- full schema-v2 validation before catalog/audit publication;
- cross-field runtimeCost/mobileBudget/LOD/variant consistency;
- library runtime-cost aggregation and rejected-manifest accounting;
- recovery-directory isolation from runtime discovery;
- LOD/catalog/audit integrity;
- hardening reasons for shear and spatial multi-assets;
- scoped stale-output / failed-refresh source provenance;
- atomic/corrupt provenance handling;
- golden-overlap hardening comparison.

## Headless production factory smoke

After focused gates pass, run a small disposable AUTO_FOLDER corpus through the
actual production entry point:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python batch_cli.py -- `
  --input D:\bfc-smoke-assets `
  --output D:\bfc-smoke-library `
  --class AUTO_FOLDER `
  --lods `
  --no-thumbnails `
  --strict `
  --json-summary D:\bfc-smoke-library\summary.json
```

A clean strict run should have:

- conversion failures = 0;
- cleanup warnings/leftovers = 0;
- stale packages = 0;
- failed-refresh retained packages = 0;
- rejected runtime manifests = 0;
- missing runtime assets = 0;
- source-index errors = none;
- complete library audit.

`batch-source-index.json` is scoped to the same input root + requested Family
Class. It does not auto-delete stale output and an unreadable canonical index is
never silently replaced.

## Real Asset Hardening

The unified runner can optionally execute a GPU-safe real corpus pass:

```powershell
python tools/validate_local.py `
  --real-input 'D:\real-assets' `
  --real-output 'D:\axion-family-hardening' `
  --real-family-class AUTO_FOLDER
```

To enforce the golden-overlap regression gate at the same time:

```powershell
python tools/validate_local.py `
  --real-input 'D:\real-assets' `
  --real-output 'D:\axion-family-hardening' `
  --real-family-class AUTO_FOLDER `
  --baseline-hardening 'D:\golden\hardening-report.json'
```

The real-asset path always uses `--no-thumbnail` through the validator. Keep
third-party source assets out of this repository unless their licenses permit
redistribution.

See `docs/REAL_ASSET_HARDENING.md` and
`docs/HARDENING_EXPANSION_PROTOCOL.md`. Do not tune role classifiers further
from synthetic tests alone; new semantic changes should be driven by repeated
patterns in an expanded real corpus.
