# Blender Family Creator

Convert ordinary Blender assets into **typed, semantic, hosted and parameter-driven BIM family libraries** for Axion's mobile BIM stack.

Family Creator is deliberately not a universal XYZ scaler. Sofa, Table, Door, Window, Cabinet, Stair and plumbing fixtures each have different geometry rules, so every asset is routed through an exact **Family Class** and dedicated class logic.

## v0.5 pipeline

```text
Downloaded / authored Blender asset
  -> Auto Prepare
  -> exact Family Class
  -> semantic member roles
  -> class-specific deformation rules
  -> semantic parameter inference
  -> procedural / semantic rebuild
  -> preflight + quality gate
  -> saved Family Types
  -> baked Type GLB variants
  -> hosted/runtime metadata
  -> schema-v2 validation
  -> family package
  -> library-index.json
```

The goal is a fast library factory: automatically accept straightforward assets and send only questionable ones to a small review queue.

## Family Class, Type and Member Role

- **Family Class** = behavior contract: `SOFA`, `TABLE`, `DOOR`, `WINDOW`, `STAIR`, etc.
- **Family Type / Variant** = saved parameter state: `900x2100`, `2-seat`, `3-seat`, etc.
- **Member Role** = semantic part: `SEAT`, `ARM_LEFT`, `TOP`, `LEG`, `FRAME_LEFT`, `GLASS`, `TREAD`, `DRAIN`, etc.

Current exact classes:

```text
Furniture
  SOFA
  TABLE
  CHAIR
  BED

Casework
  CABINET
  WARDROBE
  SHELF
  KITCHEN_BASE
  KITCHEN_WALL

Hosted openings
  DOOR
  WINDOW

Circulation
  STAIR

Plumbing
  TOILET
  SINK
  BATHTUB

Fallback
  GENERIC
```

See `docs/FAMILY_CLASSES.md` for class contracts.

## Semantic analysis

`Analyze by Family Class` uses object names plus normalized evaluated geometry. Blender's evaluated dependency graph is used when possible, so modifier output such as Array, Solidify and Bevel is represented by the measured bounding box.

Examples:

- Sofa: `ARM_LEFT`, `ARM_RIGHT`, `SEAT`, `BACK`, `LEG`, `BASE`
- Table: `TOP`, `LEG`, `APRON`, `SUPPORT`
- Bed: `MATTRESS`, `BASE`, `HEADBOARD`, `FOOTBOARD`, `SLAT`
- Casework: side/top/bottom/back/shelf/door/drawer/handle/toe-kick roles
- Door/Window: frame, leaf/panel, glass, mullion, handle, hinge and hardware
- Stair: tread, riser, stringer, landing, handrail and baluster roles
- Plumbing: basin/tub/bowl, rim, drain, faucet, tank, seat and connector roles

Generic names such as `Object.001` can still receive geometry-based fallback roles.

## Auto Prepare

Downloaded models often store multiple disconnected physical parts inside one Mesh. **Prepare Selection** and Batch **Auto Split Loose Parts** can conservatively separate manageable loose islands before analysis.

Safety rules:

- shape-key meshes are not split;
- armature-driven meshes are not split;
- single-island meshes are untouched;
- very fragmented meshes are untouched;
- default maximum loose-part count is configurable.

Empty and Armature transform parents are preserved as hierarchy helpers while semantic analysis remains geometry-only.

## Class geometry and semantic parameters

Per-member X/Y/Z behavior:

| Rule | Meaning |
|---|---|
| `STRETCH` | Resize on a family axis |
| `MOVE` | Preserve size but move with the changing family boundary |
| `FIXED` | Preserve size and position |

Family axes also have semantic anchors such as `CENTER`, `MIN` and `MAX`. Door/table/casework height, for example, can grow from the floor instead of scaling around object center.

Current semantic parameters include:

- Sofa: `seat_height`, `arm_width`, `seat_count`
- Table: `top_thickness`
- Chair: `seat_height`
- Bed: `mattress_height`
- Cabinet/Wardrobe: `panel_thickness`
- Shelf: `panel_thickness`, `shelf_count`
- Kitchen Base: `panel_thickness`, `toe_kick_height`
- Door: `frame_width`, `panel_thickness`
- Window: `frame_width`, `sill_height`
- Stair: `total_run`, `total_rise`, `tread_depth`, `riser_height`, `step_count`
- Toilet: `connector_height`
- Sink: `drain_diameter`
- Bathtub: `rim_thickness`

Saved Family Types include semantic parameter values as well as overall dimensions.

## Procedural generators

`generators/` contains isolated class-specific geometry logic.

Current behavior includes:

- Sofa repeated seat modules, arm width and seat height
- Table top thickness
- Chair seat height with leg adjustment
- Bed mattress thickness
- Cabinet/Wardrobe/Kitchen panel geometry
- Shelf repeated shelf levels
- Door frame/leaf geometry
- Window frame geometry
- Straight Stair tread/riser generation
- Toilet connector elevation
- Sink drain diameter
- Bathtub rim thickness

Repeated modules clone full child subtrees with linked mesh data. Source templates are hidden and excluded from export. Canonical source transforms remain immutable so switching Types does not accumulate transform drift.

## Hosted Door / Window families

Door and Window manifests include:

- `WALL` host type;
- rectangular host cut dimensions;
- threshold/sill insertion point;
- local placement origin;
- family +Y facing and +Z up directions;
- facing/hand flip capability;
- Window sill elevation;
- lightweight plan representation;
- Door hinge-side inference from hinge/handle roles where possible.

Unknown handing is explicitly left unknown rather than guessed.

## Quality + preflight

Every converted family has two states:

- `ready`: required class semantics exist;
- `automaticReady`: semantic checks pass and source preflight finds no reason for manual review.

Preflight checks include semantic coverage, required/recommended roles, polygon count, canonical object scale, negative/mirrored transforms, shape keys, armatures and suspicious source units/dimensions.

Batch uses `automaticReady` to decide whether an asset goes straight to the library or into `review-queue.json`.

## Baked Family Type geometry variants

The mobile BIM engine does not need to reproduce every Blender generator immediately.

When **Bake All Saved Types** is enabled:

```text
family/
  sofa_a.family.json
  sofa_a.glb                 # active Type
  variants/
    2_seat.glb
    3_seat.glb
    4_seat.glb
```

The manifest contains:

```json
{
  "geometryStrategy": {
    "mode": "BAKED_TYPE_VARIANTS",
    "activeType": "3-seat",
    "variantCount": 3
  },
  "geometryVariants": {
    "3-seat": {"uri": "sofa_a.glb", "baked": true, "primary": true},
    "2-seat": {"uri": "variants/2_seat.glb", "baked": true, "primary": false},
    "4-seat": {"uri": "variants/4_seat.glb", "baked": true, "primary": false}
  }
}
```

Variant export temporarily applies each Type, rebuilds procedural geometry, bakes GLB, then restores the original authoring state and generator revision. Export is transactional: failed variants/schema validation do not leave a half-valid package.

## Batch Family Factory

### One exact class

```text
Asset Folder = /downloaded/sofas
Family Class = SOFA
Build Family Library
```

### Mixed library by exact folder names

Choose **Auto by Folder** and organize assets like:

```text
assets/
  sofas/
  tables/
  chairs/
  doors/
  windows/
  stairs/
  sinks/
```

Nested structures such as `furniture/tables/vendor_a/model.glb` also work. Recognized folder aliases resolve to an exact class. Unknown folders are rejected instead of silently guessed.

Supported source formats:

```text
.blend
.fbx
.glb
.gltf
.obj
```

Batch output preserves source-relative paths and creates collision-safe Family IDs.

## Library output

A production root can contain multiple class batches:

```text
library/
  sofa/...
  table/...
  door/...
  window/...
  batch-report.json
  review-queue.json
  library-index.json
```

### `batch-report.json`

Contains discovered/converted/ready/review/failed counts, resolved class counts, generator/preflight details and source/output paths.

### `review-queue.json`

Contains only assets that need human review plus failed conversions.

### `library-index.json`

Cross-class runtime catalog automatically rebuilt after every batch. It contains:

- `familyId`;
- name and exact Family Class;
- category/group;
- root-relative manifest URI;
- saved Type names;
- root-relative baked geometry variant URIs;
- dimensions;
- quality score and `automaticReady`;
- host type when applicable;
- material count;
- optional future thumbnail URI.

This lets the mobile BIM app load one compact catalog instead of recursively scanning every family folder.

## Schema v2 export

Each family package uses `axion.family` schema version 2 and includes:

- stable `familyId`;
- exact `familyKind`;
- meter units;
- family Z-up vs glTF Y-up coordinate metadata;
- dimensions and named Types;
- semantic parameters;
- class profile and axis anchors;
- member roles/rules;
- generator/template metadata;
- material IDs, usages and basic PBR metadata;
- quality/preflight report;
- hosting/plan metadata where applicable;
- baked geometry variants when GLB export is enabled.

`schema.py` validates exported packages before they are accepted. See `docs/FAMILY_FORMAT.md`.

## Project structure

```text
family_types/           exact class contracts and semantic analysis
generators/             class-specific procedural/semantic geometry
core.py                 family storage, canonical transforms and base export
typed.py                typed pipeline, manifest enrichment and validation
variants.py             baked Family Type geometry export
geometry_export.py      reusable GLB geometry exporter
prepare.py              conservative source preparation
preflight.py            source-risk inspection
quality.py              semantic + preflight quality gate
hosting.py              Door/Window hosting and plan semantics
materials.py            runtime material metadata
family_path.py          exact folder -> Family Class resolver
catalog.py              cross-class library-index builder
batch.py                folder -> family library + review queue + index
schema.py               Axion Family schema-v2 validation
operators.py            Blender operators
ui.py                   3D View Sidebar UI
tests/                   pure-Python regression coverage
```

## Development status

**v0.5.0 — Mobile Family Library Factory**

The addon now goes beyond single-family authoring: it can build exact-class and mixed-folder libraries, bake saved Family Types into mobile-ready GLB variants, quarantine questionable assets, and rebuild a cross-class runtime catalog.

The next essential validation layer remains representative real-world assets inside Blender 4.x. There is intentionally no GitHub Actions workflow in this repository; pure-Python regression tests remain available for local execution.
