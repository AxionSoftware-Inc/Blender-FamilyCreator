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
--json-summary D:\reports\summary.json
```

Mobile LOD generation is opt-in with `--lods` until the Blender runtime validation gate for the LOD pipeline is completed.

## GPU-safe operation

Semantic conversion, GLB export, mobile cost measurement, LOD Decimate derivatives and library audit do not intentionally require CUDA/OptiX rendering.

When another AI workload owns the GPU, use:

```text
--no-thumbnails
```

The thumbnail renderer is the part of the normal family-factory flow that creates a Blender render. Do not run thumbnail validation in parallel with a GPU workload you do not want disturbed.

## Outputs

Each run writes family packages plus:

```text
batch-report.json
review-queue.json
library-index.json
library-audit.json
```

The batch report contains:

- discovered / converted / failed counts;
- automaticReady / review counts;
- exact Family Class counts;
- thumbnail and LOD warning counts;
- mobile-budget status counts;
- library-index path and family count;
- missing-asset / integrity warning counts;
- library-audit path and completion state.

## Exit/failure behavior

Default behavior continues after individual asset failures and records them in the report/review queue.

With `--stop-on-error`, the first failed asset aborts the conversion loop after the partial batch report/catalog/audit have been finalized as far as possible.

Optional derivative failures (thumbnail or individual LOD level) are warnings when the primary family package remains valid.

## Library integrity check

The batch already creates `library-audit.json`. It can also be rerun independently without Blender:

```powershell
python tools/audit_library.py `
  --library 'D:\axion-family-library' `
  --fail-on-warning
```

## Recommended production sequence

1. Run pure-Python regressions after code changes.
2. Run the Blender synthetic runtime harness.
3. Run a small golden real-asset corpus.
4. Run the larger source library headlessly.
5. Inspect review queue and mobile budget distributions.
6. Require a clean `library-audit.json` before publishing/copying a library to the mobile runtime.
