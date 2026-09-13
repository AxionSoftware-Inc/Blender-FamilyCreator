# Local Validation

Axion Family Creator intentionally does not use GitHub Actions. Local validation is the release gate.

Canonical acceptance criteria:

`docs/V0_7_VALIDATION_GATE.md`

## GPU-safe gate

Use while another workload owns the GPU:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py `
  --expect-commit $sha `
  --require-clean `
  --expect-blender-prefix 'Blender 5.2' `
  --keep-going
```

This runs pure-Python tests plus focused Blender smokes without the broad thumbnail/render suite.

## Full gate

Run when Blender may safely render thumbnails:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py `
  --full `
  --expect-commit $sha `
  --require-clean `
  --expect-blender-prefix 'Blender 5.2' `
  --keep-going
```

A v0.7 runtime-validation claim requires the full gate to be green. Keep LOD default OFF until that happens.

The machine-readable result is written by default to:

`tests/blender_runtime/artifacts/local-validation.json`
