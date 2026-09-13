# v0.7 Local Validation Gate

This document freezes the acceptance criteria for the current **Axion Family Creator v0.7 candidate** before any further feature work.

Current candidate line:

- addon metadata: `0.7.0`
- target validation runtime: Blender `5.2.x`
- validation entry point: `tools/validate_local.py`
- GitHub Actions intentionally absent
- LOD generation remains default OFF until the full gate is green

The validation report is machine-readable and records the tested Git commit, repository dirty state, Python executable, Blender executable/version, mode, command results, exit codes, marker checks and output tails.

For a release-candidate run, pin the validator to the exact checked-out commit and require a clean worktree:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py --expect-commit $sha --require-clean --keep-going
```

`--expect-commit` accepts a full SHA or an abbreviated SHA of at least seven characters. `--require-clean` fails when uncommitted changes exist.

## Gate A — GPU-safe candidate validation

Use this while the NVIDIA GPU is reserved for AI training:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py `
  --expect-commit $sha `
  --require-clean `
  --keep-going
```

This must run:

1. exact candidate-commit guard;
2. clean-worktree guard;
3. pure-Python `unittest` discovery;
4. semantic refinement smoke;
5. Window capability smoke;
6. transform/shear safety smoke;
7. batch cleanup/leak smoke;
8. export state + transaction smoke;
9. mobile LOD smoke;
10. repeated-batch source provenance smoke.

Although LOD geometry processing is included, thumbnail/render validation is not included in this mode.

### GPU-safe acceptance

All gates must return exit code `0` and the final validation report must show:

```text
passed = true
failedCount = 0
```

No gate may be waived silently. If one fails, keep the JSON report and fix the concrete failure before claiming the candidate is GPU-safe validated.

## Gate B — Full Blender 5.2 validation

Run only when the GPU can safely be used by Blender:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py `
  --full `
  --expect-commit $sha `
  --require-clean `
  --keep-going
```

This repeats Gate A and additionally runs the full Blender runtime harness, including thumbnail/render validation.

### Full acceptance

The v0.7 candidate is considered **locally runtime validated** only when:

- candidate-commit guard passes;
- clean-worktree guard passes;
- all pure-Python tests pass;
- all focused GPU-free Blender smokes pass;
- `tests/blender_runtime/run_all.py` exits successfully;
- the validation report records the intended candidate commit;
- no cleanup leak, partial package, incomplete rollback, schema failure, missing runtime asset or stale provenance condition is present in the tested paths.

After this gate is green, documentation may change from `validation pending` to a concrete tested Blender/Python baseline.

## Gate C — Golden real-asset regression

After Gate B, rerun the seven-asset BlenderKit golden corpus with thumbnails optional according to GPU availability.

The established golden behavior must not regress:

- 7/7 sources convert;
- no conversion failure;
- `bed.blend` remains automatic-ready with one valid `MATTRESS`;
- `window.blend` remains automatic-ready;
- `window2.blend` remains automatic-ready without requiring separate frame meshes;
- `windowcurved.blend` keeps complete Window semantics and may remain review-only for non-uniform scale;
- mixed table-chair sources remain non-destructive review cases;
- source/staging assets remain unchanged.

Use `tools/compare_hardening.py --fail-on-regression` when a golden baseline report is available.

The unified validator can also run a GPU-safe real-corpus pass and golden comparison:

```powershell
$sha = (git rev-parse HEAD).Trim()
python tools/validate_local.py `
  --expect-commit $sha `
  --require-clean `
  --real-input 'C:\path\to\staging' `
  --real-output 'C:\path\to\validation-output' `
  --real-family-class AUTO_FOLDER `
  --baseline-hardening 'C:\path\to\golden\hardening-report.json' `
  --keep-going
```

The real-corpus runner uses `--no-thumbnail` in this path.

## Gate D — Expanded real-asset generalization

Only after the golden overlap is stable, test genuinely new assets.

Minimum useful expansion:

- 5 new BED;
- 5 new WINDOW;
- preferably 10 + 10;
- multiple vendor/source styles;
- genuine FBX/OBJ/GLB/GLTF where available rather than self-converted format duplicates.

Do **not** tune classifiers during the measurement run. Collect repeated failure patterns first.

Generalization targets remain:

- conversion success >=95% for supported non-corrupt sources;
- automatic acceptance >=80% for reasonably prepared core-class assets;
- no regression on the golden overlap corpus;
- no silent Generic fallback;
- no destructive source mutation;
- no batch cleanup growth;
- no incomplete runtime package accepted as healthy.

## Release blockers

Any of the following blocks a v0.7 validated/release claim:

- candidate-commit mismatch;
- dirty worktree during a release-candidate gate;
- pure-Python regression;
- Blender registration/runtime failure;
- focused smoke failure;
- new transform shear on rotated/off-axis members;
- cleanup leftovers that accumulate across assets;
- failed overwrite damaging the previous valid package;
- rollback failure hidden instead of reported;
- manifest/GLB/LOD/thumbnail asset-integrity mismatch;
- stale or failed-refresh package ignored by strict production mode;
- source provenance baseline overwritten after an aborted/catalog-failed batch;
- schema accepting invalid mobile optimization metadata;
- golden real-asset regression.

## Non-blocking review conditions

These may legitimately remain review-only and do not by themselves mean the converter failed:

- source non-uniform scale;
- source canonical shear;
- suspected multiple unrelated assets in one source;
- mixed furniture sets;
- heavy geometry/mobile over-budget status;
- missing optional/recommended semantic roles;
- fused/baked Window frame geometry when runtime semantics are otherwise valid;
- texture/material optimization recommendations.

Semantic validity and mobile runtime cost remain separate decisions.

## After the gate is green

Do not immediately add another broad feature set. First:

1. record the exact green commit and Blender/Python versions;
2. mark v0.7 runtime validation status in README/ROADMAP;
3. run the golden real corpus;
4. expand the real corpus;
5. only then proceed to v0.8 native Axion runtime integration or evidence-driven semantic hardening.
