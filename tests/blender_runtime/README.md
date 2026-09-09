# Blender 5.2 runtime harness

This harness runs the addon inside the installed Blender runtime. It creates
deterministic synthetic assets, exercises the exact-class generators, exports
and re-imports GLB packages, renders thumbnails, tests variants and batch
conversion, and writes a machine-readable result file under `artifacts/`.

Run the deterministic regression harness from the repository root:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python tests/blender_runtime/run_all.py
```

Family-level BED/WINDOW second-pass refinement has a focused Blender smoke test:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_refinement_smoke.py
```

Baked Window validity versus separate-frame edit capability has its own smoke test:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_window_capability_smoke.py
```

Expected focused smoke results:

```text
SEMANTIC_REFINEMENT_SMOKE: PASS
WINDOW_CAPABILITY_SMOKE: PASS
```

The script intentionally does not use normal system Python for Blender-facing
checks. Pure-Python regression tests remain:

```powershell
python -m unittest discover -s tests -v
```

## Real Asset Hardening

After the deterministic suite is green, use `run_real_assets.py` against a local
mixed corpus of downloaded/vendor models. Keep third-party source assets out of
this repository unless their licenses permit redistribution.

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
`library-index.json`), the real-asset runner writes `hardening-report.json` with
conversion/automatic-acceptance rates, class/format metrics, normalized review
reasons, semantic refinement frequency, semantic capability flags, unresolved
member samples and generator messages for hardening diagnostics.
