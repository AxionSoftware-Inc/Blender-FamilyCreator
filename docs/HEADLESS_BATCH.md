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

- existing manifest-managed target files are moved to temporary backups;
- new primary/variant/LOD/thumbnail files are promoted;
- files referenced by the previous manifest but omitted by the new manifest are pruned transactionally;
- unrelated files that were never owned by either manifest are left untouched;
- a family-name/manifest-filename change replaces the previous single root manifest rather than leaving two contracts;
- a destination containing multiple pre-existing root manifests is rejected as ambiguous;
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
- `failed_refresh_package_count` for current sources whose refresh failed while an older package remains present.

## Source provenance and stale-output diagnostics

`batch-source-index.json` is a **schema-v2 multi-scope registry**. Each stored scope snapshot records:

- normalized input root;
- requested Family Class / `AUTO_FOLDER` mode;
- source paths;
- resolved family IDs;
- conversion status.

The registry preserves independent histories for multiple jobs sharing one library root. Alternating runs such as `assets-A -> assets-B -> assets-A` therefore still compare the final A run against the previous A snapshot rather than losing provenance when B ran in between.

Legacy schema-v1 single-scope `batch-source-index.json` files remain readable and are upgraded to the v2 registry on the next successful write.

A stale comparison is enabled only when the registry contains a scope with the same normalized input root and requested Family Class. This avoids flagging packages produced by unrelated jobs.

The factory does **not** delete stale packages automatically. It reports them so a human or publishing layer can decide whether removal is appropriate.

A removed/renamed source counts as stale only when that family ID still exists in the current library catalog. A source that failed in a previous run and never produced a package is not reported as stale merely because it later disappears.

If catalog construction fails, the previous provenance registry is preserved instead of replacing a known-good baseline with an unverifiable run.

## Exit/failure behavior

Default behavior continues after individual asset failures and records them in the report/review queue.

With `--stop-on-error`, the first failed asset aborts the conversion loop after the partial batch report/catalog/audit have been finalized as far as possible. An aborted run does not replace the previous provenance registry, because it is not a complete view of the input corpus.

Optional derivative failures (thumbnail or individual LOD level) are warnings when the primary family package remains valid.

With `--strict`, any unresolved production-integrity issue described above causes a non-zero exit code.

## Library integrity check

The batch already creates `library-audit.json`. It can also be rerun independently without Blender:

```powershell
python tools/audit_library.py `
  --library 'D:\axion-family-library' `
  --fail-on-warning
```

Catalog/audit URI resolution uses the same safe-relative-path contract as schema v2: absolute paths, `.`/`..` segments and physical/symlink escapes outside the library root are rejected.

## Unified local validation

Canonical acceptance criteria are in `docs/V0_7_VALIDATION_GATE.md` and the short entrypoint is `VALIDATION.md`.

GPU-safe release-candidate gate:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py `
  --expect-commit $sha `
  --require-clean `
  --expect-blender-prefix 'Blender 5.2' `
  --keep-going
```

Full gate when thumbnail/render validation may use Blender normally:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py `
  --full `
  --expect-commit $sha `
  --require-clean `
  --expect-blender-prefix 'Blender 5.2' `
  --keep-going
```

An optional real corpus can be added with `--real-input`, `--real-output` and `--baseline-hardening`; the hardening comparison is run in fail-on-regression mode when a baseline is supplied.

The runner writes a machine-readable `tests/blender_runtime/artifacts/local-validation.json` summary including exact git commit, dirty-tree state, Python version and Blender version unless another path is requested with `--report`.

## Recommended production sequence

1. Run the pinned clean-worktree local validation gate.
2. Run a small golden real-asset corpus and compare against its hardening baseline.
3. Run the larger source library headlessly, preferably with `--strict`.
4. Inspect review queue, stale/failed-refresh diagnostics and mobile budget distributions.
5. Require a clean `library-audit.json` before publishing/copying a library to the mobile runtime.
