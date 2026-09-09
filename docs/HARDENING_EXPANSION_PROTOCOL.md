# BED / WINDOW hardening corpus expansion protocol

This protocol follows the 7-asset BlenderKit rerun-3 golden baseline.

The purpose is to determine whether the current BED and WINDOW semantic rules generalize to new vendor assets rather than continuing to optimize the same seven files.

## Golden overlap corpus

Keep the existing seven staging assets in the expanded corpus unchanged and with the same filenames:

```text
beds/bed.blend
beds/bed2.blend
tables/metal-table-chair-set.blend
tables/table-chair-set.blend
windows/window.blend
windows/window2.blend
windows/windowcurved.blend
```

These are the no-regression overlap set.

Do not rename these seven files during expansion. The comparison tool matches overlap assets by `FamilyClass + filename`.

## New-asset target

First expansion target:

- at least 5 new BED assets;
- at least 5 new WINDOW assets;
- preferred: 10 new BED + 10 new WINDOW assets;
- at least two vendors/source styles when practical;
- intentionally include more than `.blend` when available.

Format priority for this phase:

1. `.blend`
2. `.fbx`
3. `.glb` / `.gltf`
4. `.obj`

The first expanded run should exercise at least one non-BLEND format if suitable assets are available. Do not convert files manually just to manufacture format diversity; use genuinely obtained source formats.

## Staging filenames

New staging copies must have unique filenames within their Family Class.

Good:

```text
beds/blenderkit_modern_bed_01.blend
beds/vendorb_platform_bed_01.fbx
windows/blenderkit_casement_01.blend
windows/vendorb_arch_window_01.glb
```

Avoid:

```text
beds/vendor_a/bed.blend
beds/vendor_b/bed.blend
```

Duplicate `FamilyClass + filename` keys make baseline comparison ambiguous. `hardening_compare.py` detects these collisions and fails the no-regression gate instead of silently picking one.

Renaming a staging copy is allowed. Never rename or modify the original downloaded/vendor asset.

## Before running the expanded corpus

From repository root:

```powershell
python -m unittest discover -s tests -v
```

Then run Blender 5.2 deterministic validation:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_all.py
```

Focused semantic checks:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_refinement_smoke.py

& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_window_capability_smoke.py
```

Do not proceed to corpus interpretation if deterministic tests regress.

## Run the expanded corpus

Example:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_real_assets.py -- `
  --input 'C:\Users\shaxz\OneDrive\Dokumenty\_bfc-real-assets-staging-expanded' `
  --output 'C:\Users\shaxz\OneDrive\Dokumenty\_bfc-real-assets-output-expanded-1' `
  --family-class AUTO_FOLDER
```

The expanded staging folder should contain the original seven overlap assets plus the new BED/WINDOW assets.

## Compare against rerun-3

Use rerun-3 as the golden baseline:

```text
C:\Users\shaxz\OneDrive\Dokumenty\_bfc-real-assets-output-rerun-3\hardening-report.json
```

Compare:

```powershell
python tools/compare_hardening.py `
  --baseline 'C:\Users\shaxz\OneDrive\Dokumenty\_bfc-real-assets-output-rerun-3\hardening-report.json' `
  --candidate 'C:\Users\shaxz\OneDrive\Dokumenty\_bfc-real-assets-output-expanded-1\hardening-report.json' `
  --output 'C:\Users\shaxz\OneDrive\Dokumenty\_bfc-real-assets-output-expanded-1\hardening-compare.json'
```

The compare report separates:

- overlap assets;
- new assets;
- removed assets;
- overlap improvements;
- overlap regressions;
- new-asset automatic acceptance;
- new-asset average role coverage;
- class deltas;
- source-format results;
- reason-frequency deltas;
- duplicate comparison-key collisions.

## Mandatory no-regression gate

The expanded run passes the golden-overlap gate only when:

```text
gate.passesNoRegressionGate == true
```

This requires:

- no previous automaticReady overlap asset becomes review-only;
- no overlap asset loses conversion;
- no overlap asset loses more than 5 percentage points of role coverage;
- no overlap asset loses more than 10 score points without an even stronger readiness signal;
- no duplicate FamilyClass+filename comparison keys.

A failed gate does not mean the new corpus is bad. It means production behavior changed for the already-proven overlap corpus and must be investigated before accepting another classifier patch.

## How to interpret new assets

Do not judge the expansion only from the total auto-acceptance percentage because the golden and new corpus sizes differ.

Inspect specifically:

```text
newAssets.count
newAssets.converted
newAssets.failed
newAssets.automaticReady
newAssets.autoAcceptanceRate
newAssets.averageRoleCoverage
newAssets.reasonFrequency
newAssets.byClass.BED
newAssets.byClass.WINDOW
```

For every new review asset, inspect its original hardening-report entry:

- `roleCoverage`
- `roleCounts`
- `semanticCapabilities`
- `unknownMemberSamples`
- `generator.reasonCode`
- `generator.message`
- `reasons`
- `detailedReasons`

## Policy during the first expanded measurement

Do not modify classifier heuristics in the same run merely because a new asset fails.

First return a clean measurement.

Keep these existing safety policies:

- no global threshold relaxation;
- no automatic non-uniform-scale application;
- no automatic deletion of mixed-scene furniture;
- no destructive source edits;
- no source-asset redistribution in the repository;
- no GitHub Actions;
- no license changes.

A new semantic alias or geometry refinement should only be proposed after the expanded report shows a repeated pattern across more than one representative asset, unless the issue is an unambiguous runtime bug.

## First expansion success criteria

Required:

- deterministic test suites pass;
- golden overlap no-regression gate passes;
- supported/non-corrupt conversion success remains at least 95%;
- original/source hashes remain unchanged;
- no cleanup leak appears;
- no partial packages remain after failures.

Evidence target rather than a hard pass/fail threshold:

- at least 10 genuinely new BED/WINDOW assets;
- preferably 20;
- at least one non-BLEND format exercised;
- new-asset review reasons are sufficiently repeated to guide the next hardening patch.

Do not chase an arbitrary automaticReady percentage before the new corpus is representative. The purpose of expansion-1 is to discover generalization gaps without losing the rerun-3 golden behavior.
