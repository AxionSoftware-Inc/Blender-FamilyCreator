# Headless Batch Family Factory

`batch_cli.py` is the production command-line entry point for converting folders of assets without opening the Blender UI.

## Basic command

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python batch_cli.py -- `
  --input 'D:\assets' `
  --output 'D:\axion-family-library' `
  --class AUTO_FOLDER `
  --recursive
```

`AUTO_FOLDER` resolves exact Family Classes from recognized parent folders. Unknown folders are rejected; there is no Generic fallback.

## Supported source formats

```text
.blend
.fbx
.glb
.gltf
.obj
```

## Options

```text
--class SOFA|TABLE|...|AUTO_FOLDER
--recursive
--non-recursive
--no-glb
--no-baked-types
--no-thumbnails
--lods
--no-auto-split
--max-loose-islands 32
--stop-on-error
--strict
--json-summary D:\reports\summary.json
```

Mobile LOD generation is opt-in with `--lods` until the current Blender runtime validation gate for the LOD pipeline is completed.

`--strict` is intended for production/publish jobs. It exits non-zero when the run leaves conversion failures, cleanup problems, missing package assets, an incomplete library audit, stale packages from removed sources, or a failed refresh that left the previous package in the library.

## GPU-safe operation

Semantic conversion, GLB export, mobile cost measurement, LOD Decimate derivatives and library audit do not intentionally require CUDA/OptiX rendering.

When another AI workload owns the GPU, use:

```text
--no-thumbnails
```

The thumbnail renderer is the part of the normal family-factory flow that creates a Blender render. Do not run thumbnail validation in parallel with a GPU workload you do not want disturbed.

## Validate-before-overwrite package export

Each family package is built in a sibling same-filesystem staging directory first. The new manifest is schema-validated before the destination package is touched.

During commit:

- existing target files are moved to temporary backups;
- new primary/variant/LOD/thumbnail files are promoted;
- the new family manifest is promoted last;
- a normal commit failure restores the previous package;
- an incomplete rollback is surfaced as an explicit export failure rather than being hidden.

This means a failed re-export should not silently destroy a previously valid family package.

## Outputs

Each completed run writes family packages plus:

```text
batch-report.json
review-queue.json
library-index.json
library-audit.json
batch-source-index.json
```

The batch report contains:

- discovered / converted / failed counts;
- automaticReady / review counts;
- exact Family Class counts;
- thumbnail and LOD warning counts;
- cleanup warnings and leftover datablock counts;
- mobile-budget status counts;
- library-index path and family count;
- missing-asset / integrity warning counts;
- library-audit path and completion state;
- source-index comparability;
- `stale_output_count` for packages whose source disappeared/was renamed since the previous comparable run;
- `failed_refresh_count` for current sources whose refresh failed while an older package remains present.

## Source provenance and stale-output diagnostics

`batch-source-index.json` records the input root, requested Family Class, source paths, resolved family IDs and conversion status.

Stale comparison is only enabled when the previous source index has the same normalized input root and the same requested Family Class. This avoids flagging packages produced by unrelated batch jobs that share one library root.

The factory does **not** delete stale packages automatically. It reports them so a human or publishing layer can decide whether removal is appropriate.

A removed/renamed source counts as stale only when that family ID still exists in the current library catalog. A source that failed in a previous run and never produced a package is not reported as stale merely because it later disappears.

## Exit/failure behavior

Default behavior continues after individual asset failures and records them in the report/review queue.

With `--stop-on-error`, the first failed asset aborts the conversion loop after the partial batch report/catalog/audit have been finalized as far as possible. An aborted run does not replace the canonical previous `batch-source-index.json`, because it is not a complete view of the input corpus.

Optional derivative failures (thumbnail or individual LOD level) are warnings when the primary family package remains valid.

With `--strict`, any unresolved production-integrity issue described above causes a non-zero exit code.

## Library integrity check

The batch already creates `library-audit.json`. It can also be rerun independently without Blender:

```powershell
python tools/audit_library.py `
  --library 'D:\axion-family-library' `
  --fail-on-warning
```

## Unified local validation

The preferred pre-publish developer gate is:

```powershell
python tools/validate_local.py --full --keep-going
```

Default `validate_local.py` mode runs pure-Python tests plus focused GPU-free Blender smoke tests. `--full` additionally runs the broad Blender runtime suite, including thumbnail/render coverage.

An optional real corpus can be added with `--real-input`, `--real-output` and `--baseline-hardening`; the hardening comparison is run in fail-on-regression mode when a baseline is supplied.

The runner writes a machine-readable `tests/blender_runtime/artifacts/local-validation.json` summary unless another path is requested with `--report`.

## Recommended production sequence

1. Run `python tools/validate_local.py --full --keep-going` after code changes when the GPU is available for thumbnail validation.
2. Run a small golden real-asset corpus and compare against its hardening baseline.
3. Run the larger source library headlessly, preferably with `--strict`.
4. Inspect review queue, stale/failed-refresh diagnostics and mobile budget distributions.
5. Require a clean `library-audit.json` before publishing/copying a library to the mobile runtime.
