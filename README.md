# Blender Family Creator

Convert ordinary Blender assets into **typed, semantic, hosted and parameter-driven BIM families** for Axion's mobile BIM stack.

The project is intentionally not a universal XYZ scaler. A sofa, table, door, cabinet and stair have different geometry rules, so conversion begins by choosing an exact **Family Class** and then runs class-specific analysis and generation logic.

## Core pipeline

Blender already has a huge ecosystem of reusable `.blend`, FBX, GLB/GLTF and OBJ models. Family Creator turns those assets into BIM library content through this pipeline:

```text
Imported asset
  -> Auto Prepare
  -> Family Class
  -> Semantic member roles
  -> Class-specific deformation rules
  -> Auto-detected semantic parameters
  -> Procedural / semantic rebuild
  -> Preflight + Quality Gate
  -> Family Types / Variants
  -> Hosted/runtime metadata
  -> .family.json + .glb
```

## Family Class vs Family Type

- **Family Class** = behavior contract such as `SOFA`, `TABLE`, `DOOR`, `WINDOW`, `STAIR`.
- **Family Type / Variant** = one saved parameter set inside a family, such as `900x2100`, `1200x2100`, `2-seat`, `3-seat`.
- **Member Role** = semantic part such as `SEAT`, `ARM_LEFT`, `TOP`, `LEG`, `FRAME_LEFT`, `GLASS`, `SHELF`, `TREAD`, `DRAIN`.

The class determines how geometry is allowed to change. Types store concrete dimensions and semantic parameter values.

## Current family classes

### Furniture
- `SOFA`
- `TABLE`
- `CHAIR`
- `BED`

### Casework
- `CABINET`
- `WARDROBE`
- `SHELF`
- `KITCHEN_BASE`
- `KITCHEN_WALL`

### Hosted openings
- `DOOR`
- `WINDOW`

### Circulation
- `STAIR`

### Plumbing
- `TOILET`
- `SINK`
- `BATHTUB`

### Fallback
- `GENERIC`

See `docs/FAMILY_CLASSES.md` for the class contracts.

## Semantic analysis

`Analyze by Family Class` classifies source members using object names plus normalized evaluated geometry. Bounding boxes are taken from Blender's evaluated dependency graph when possible, so modifiers such as Array, Solidify and Bevel are reflected in analysis.

Examples:

- Sofa: `ARM_LEFT`, `ARM_RIGHT`, `SEAT`, `BACK`, `LEG`, `BASE`, `DECOR`
- Table: `TOP`, `LEG`, `APRON`, `SUPPORT`, `DECOR`
- Chair: `SEAT`, `BACK`, `LEG`, `ARM`, `FRAME`
- Bed: `MATTRESS`, `BASE`, `HEADBOARD`, `FOOTBOARD`, `LEG`, `SLAT`
- Casework: `SIDE_LEFT`, `SIDE_RIGHT`, `TOP`, `BOTTOM`, `BACK`, `SHELF`, `DOOR`, `DRAWER_FRONT`, `HANDLE`, `TOE_KICK`
- Door / Window: frame edges, panel/leaf, glass, mullion, handle, hinge and hardware
- Stair: `TREAD`, `RISER`, `STRINGER`, `HANDRAIL`, `BALUSTER`, `LANDING`
- Sink / Bathtub: `BASIN`/`TUB`, `RIM`, `DRAIN`, `FAUCET`, `CONNECTOR`, `PEDESTAL`
- Toilet: `BOWL`, `TANK`, `SEAT`, `BASE`, `CONNECTOR`, `FLUSH`

Downloaded assets with generic names such as `Object.001` can still receive useful roles from geometry proportions and location.

## Auto Prepare

Many downloaded models store multiple disconnected physical parts in one Mesh object. **Prepare Selection** and Batch **Auto Split Loose Parts** can conservatively separate manageable disconnected islands before semantic analysis.

Safety rules:

- shape-key meshes are not split;
- armature-driven meshes are not split;
- single-island meshes are untouched;
- excessively fragmented meshes are untouched;
- default maximum is 32 loose parts and is configurable.

## Geometry rules and anchors

Every member has an X/Y/Z rule:

| Rule | Meaning |
|---|---|
| `STRETCH` | Resize on this family axis |
| `MOVE` | Keep size but move with the changing family boundary |
| `FIXED` | Preserve size and position on this axis |

Family axes also have semantic anchors. Door/table/chair/casework height uses a `MIN` Z anchor so the object remains on its host/floor plane instead of scaling away from it. Stair run/rise begins from its start point.

## Semantic parameters

Examples:

- Sofa: `seat_height`, `arm_width`, `seat_count`
- Table: `top_thickness`
- Chair: `seat_height`
- Bed: `mattress_height`
- Cabinet / Wardrobe: `panel_thickness`
- Shelf: `panel_thickness`, `shelf_count`
- Kitchen Base: `panel_thickness`, `toe_kick_height`
- Door: `frame_width`, `panel_thickness`
- Window: `frame_width`, `sill_height`
- Stair: `total_run`, `total_rise`, `tread_depth`, `riser_height`, `step_count`
- Toilet: `connector_height`
- Sink: `drain_diameter`
- Bathtub: `rim_thickness`

Most values are inferred when the parameter is still `0 / Auto`. Saved Family Types include semantic parameter values as well as overall dimensions.

## Procedural / semantic generators

`generators/` contains class-specific geometry builders. Source pieces used for repetition become hidden templates and are excluded from export. Repeated modules clone complete object subtrees with linked mesh data, preserving child details and materials without needlessly duplicating mesh memory.

Current behavior includes:

- **Sofa**: arm width, seat height and repeated seat count
- **Table**: tabletop thickness
- **Chair**: seat height with leg adjustment
- **Bed**: mattress thickness
- **Cabinet / Wardrobe / Kitchen**: panel thickness and kitchen toe-kick height
- **Shelf**: panel thickness plus repeated shelf levels
- **Door**: frame width and leaf thickness
- **Window**: frame width
- **Stair**: straight tread/riser generation from solved run/rise parameters
- **Toilet**: connector elevation
- **Sink**: drain diameter
- **Bathtub**: rim profile thickness

Canonical source transforms remain immutable while generated copies keep their own generated bases. This prevents parameter/type switching from accumulating transform drift.

Changing overall dimensions automatically re-applies supported class generators. Applying a saved Family Type also rebuilds procedural geometry.

## Hosted Door / Window families

Door and Window exports contain runtime BIM hosting metadata:

- wall host type;
- rectangular host opening/cut dimensions;
- insertion point (`THRESHOLD_CENTER` or `SILL_CENTER`);
- local placement origin;
- facing +Y / up +Z family directions;
- facing/hand flip capability;
- Window sill elevation;
- lightweight plan representation.

Door hinge side is inferred from `HINGE` roles when possible, with handle position as a fallback. Unknown swing direction is left explicitly unknown instead of being guessed.

## Quality and preflight

Every family gets two related states:

- **ready**: required class semantics were detected;
- **automaticReady**: semantics are valid and source preflight found no reason for manual review.

Checks include:

- semantic role coverage;
- required and recommended roles;
- source polygon count;
- canonical unapplied/non-uniform scale;
- mirrored/negative transforms;
- shape keys and armature usage;
- suspicious family dimensions / probable unit mismatch.

The quality report is embedded in `.family.json` and Batch uses `automaticReady` to decide whether an asset enters the review queue.

## Batch Family Factory

A whole folder can be converted with one exact Family Class.

```text
80 downloaded sofa models
  -> Family Class = SOFA
  -> Auto Prepare
  -> Analyze / Generate / Validate
  -> Build Family Library
```

Supported inputs:

```text
.blend
.fbx
.glb
.gltf
.obj
```

The source relative folder path is preserved in the output and is also used to generate a collision-safe Family ID, so same-named assets in different source folders do not overwrite or identify as each other.

Typical output:

```text
library/
  sofa/
    vendor_a/Sofa_A/
      sofa_a.family.json
      sofa_a.glb
    vendor_b/Sofa_A/
      sofa_a.family.json
      sofa_a.glb
  batch-report.json
  review-queue.json
```

- `batch-report.json`: complete conversion results.
- `review-queue.json`: only questionable families plus failed assets, so an artist can inspect the minority that automation could not confidently accept.

Batch cleanup tracks imported objects/datablocks and only removes owned zero-user data. It does not run a global orphan purge on the user's scene.

## Export package / schema v2

```text
my_family.family.json
my_family.glb
```

The JSON includes:

- stable `familyId`;
- schema version and Family Class;
- meter units;
- explicit family Z-up vs glTF Y-up coordinate-system metadata;
- dimensions and Family Types;
- semantic parameters;
- class profile and anchors;
- member roles/rules and generator metadata;
- material IDs, usage and basic PBR factors;
- quality + preflight report;
- hosted Door/Window placement and plan metadata when applicable.

Textures/geometry remain in GLB; the JSON material section is intended for runtime identification/search/replacement, not duplicating texture payloads.

## Manual workflow

1. Import or open an asset.
2. Select its geometry.
3. Optionally run **Prepare Selection**.
4. Choose the exact **Family Class**.
5. Click **Create Typed Family from Selection**.
6. Inspect Quality and semantic roles.
7. Run **Analyze by Family Class** after cleanup/class changes.
8. Change dimensions and semantic parameters.
9. Rebuild procedural geometry when editing semantic ID-properties.
10. Correct member roles/rules only where automation needs help.
11. Save useful configurations as Family Types.
12. Export `.family.json + .glb`.

## Project structure

```text
family_types/           # exact class contracts, role classifiers, parameter inference
generators/             # class-specific semantic/procedural geometry
core.py                 # family storage, canonical transforms, variants, GLB export
typed.py                # typed pipeline and manifest enrichment
prepare.py              # conservative loose-part preparation
preflight.py            # source asset risk checks
quality.py              # semantic + preflight quality gate
hosting.py              # Door/Window wall hosting and plan semantics
materials.py            # runtime material metadata
batch.py                # folder -> library + review queue
operators.py            # Blender operators
ui.py                   # 3D View Sidebar UI
```

## Development status

**v0.4.0 — Hosted Family Factory**

The addon now has dedicated logic/generation for the main furniture, casework, opening, stair and plumbing classes; hosted Door/Window metadata; conservative source preparation; preflight/quality gates; stable Family IDs; material metadata; and batch conversion with a review queue.

The next essential validation layer is representative real-world assets inside Blender 4.x. The code is deliberately split by Family Class so fixes found in one category can be strengthened without destabilizing unrelated classes.
