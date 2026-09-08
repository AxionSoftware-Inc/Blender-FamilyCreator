# Axion Family Package — Draft v2

This document defines the interchange format produced by Blender Family Creator v0.3.

The package is designed so Axion's mobile BIM engine can begin with baked GLB geometry while retaining enough semantic authoring information for progressively richer runtime-parametric behavior later.

## Package

A family export contains:

```text
family_name.family.json
family_name.glb
```

`family.json` contains BIM/family semantics and authoring metadata. `glb` contains the currently evaluated exportable geometry.

Procedural source templates are intentionally excluded from GLB. Generated geometry is included.

## Schema version

```json
{
  "schema": "axion.family",
  "schemaVersion": 2
}
```

The mobile BIM importer should reject unsupported schema versions explicitly rather than guessing compatibility.

## Manifest example

```json
{
  "schema": "axion.family",
  "schemaVersion": 2,
  "name": "Sofa A",
  "category": "Furniture",
  "familyKind": "SOFA",
  "activeType": "3-seat",
  "baseDimensions": {
    "width": 2.1,
    "depth": 0.9,
    "height": 0.82
  },
  "dimensions": {
    "width": 2.1,
    "depth": 0.9,
    "height": 0.82
  },
  "semanticParameters": {
    "seat_height": 0.44,
    "arm_width": 0.18,
    "seat_count": 3
  },
  "types": {
    "3-seat": {
      "width": 2.1,
      "depth": 0.9,
      "height": 0.82,
      "semanticParameters": {
        "seat_height": 0.44,
        "arm_width": 0.18,
        "seat_count": 3
      }
    }
  },
  "generator": {
    "supported": true,
    "revision": 2
  },
  "quality": {
    "ready": true,
    "score": 94,
    "sourceMembers": 11,
    "roleCoverage": 0.91,
    "roleCounts": {
      "SEAT": 3,
      "ARM_LEFT": 1,
      "ARM_RIGHT": 1,
      "BACK": 3,
      "LEG": 3
    },
    "missingRoleGroups": [],
    "warnings": [],
    "errors": []
  },
  "members": [
    {
      "name": "Sofa_A_Seat_01",
      "type": "MESH",
      "role": "SEAT",
      "generated": true,
      "generatorGroup": "SOFA_SEATS",
      "rules": {
        "x": "MOVE",
        "y": "FIXED",
        "z": "FIXED"
      }
    }
  ],
  "templates": [
    {
      "name": "Seat_Cushion_Source",
      "role": "SEAT",
      "generatorGroup": "SOFA_SEATS"
    }
  ],
  "customParameters": {},
  "familyProfile": {
    "label": "Sofa",
    "group": "Furniture",
    "category": "Furniture",
    "strategy": "SOFA",
    "logicModule": "family_types.sofa",
    "editableAxes": ["X"],
    "axisParameters": {
      "X": "width",
      "Y": "depth",
      "Z": "height"
    },
    "axisAnchors": {
      "X": "CENTER",
      "Y": "CENTER",
      "Z": "MIN"
    },
    "parameters": [
      "width",
      "depth",
      "height",
      "seat_height",
      "arm_width",
      "seat_count"
    ]
  }
}
```

Blender distance values are exported in meters.

## Family Class

`familyKind` identifies the exact semantic behavior contract used by the authoring pipeline.

Examples:

```text
SOFA
TABLE
CHAIR
BED
CABINET
WARDROBE
SHELF
KITCHEN_BASE
KITCHEN_WALL
DOOR
WINDOW
STAIR
TOILET
SINK
BATHTUB
GENERIC
```

The runtime should not assume that two different `familyKind` values share the same parameter/deformation semantics even when their geometry looks similar.

## Family Types / Variants

`types` stores named parameter snapshots inside one family.

A type contains the overall dimensions plus class-specific `semanticParameters`.

Example:

```json
{
  "types": {
    "2-seat": {
      "width": 1.6,
      "depth": 0.9,
      "height": 0.82,
      "semanticParameters": {
        "seat_count": 2,
        "seat_height": 0.44,
        "arm_width": 0.18
      }
    },
    "3-seat": {
      "width": 2.1,
      "depth": 0.9,
      "height": 0.82,
      "semanticParameters": {
        "seat_count": 3,
        "seat_height": 0.44,
        "arm_width": 0.18
      }
    }
  }
}
```

Applying a saved Type in Blender also runs the class-specific generator when that class supports procedural geometry.

## Semantic parameters

`semanticParameters` are stable BIM-oriented parameter IDs rather than arbitrary UI labels.

Examples:

- Sofa: `seat_height`, `arm_width`, `seat_count`
- Table: `top_thickness`
- Chair: `seat_height`
- Bed: `mattress_height`
- Casework: `panel_thickness`
- Shelf: `panel_thickness`, `shelf_count`
- Door: `frame_width`, `panel_thickness`
- Window: `frame_width`, `sill_height`
- Stair: `total_run`, `total_rise`, `tread_depth`, `riser_height`, `step_count`

A future runtime-parametric implementation should use these IDs instead of parsing human-readable labels.

## Member roles

Each exportable member can include a semantic `role` assigned by its Family Class.

Examples:

```text
SEAT
ARM_LEFT
TOP
LEG
FRAME_LEFT
GLASS
SHELF
TREAD
RISER
```

The same generic member rule can mean different things in different roles/classes, so `familyKind + role + semanticParameters` is the preferred semantic key.

## Member rules

Every family member can react independently to a dimension axis:

- `STRETCH`: resize geometry on the axis and move with its family anchor.
- `MOVE`: preserve geometry size while its family-relative position follows the changing boundary.
- `FIXED`: preserve size and position on that family axis.

Example:

```json
{
  "name": "Table_Leg_FL",
  "role": "LEG",
  "rules": {
    "x": "MOVE",
    "y": "MOVE",
    "z": "STRETCH"
  }
}
```

These rules are authoring metadata. A runtime that only consumes baked GLB does not need to reproduce them.

## Semantic axis anchors

`familyProfile.axisAnchors` describes where overall dimensional changes are anchored.

Supported draft values:

```text
CENTER
MIN
MAX
```

Examples:

- Door Z = `MIN`: door remains on its floor/base plane as height changes.
- Table Z = `MIN`: legs grow upward from the floor.
- Stair Y/Z = `MIN`: run/rise begin at the stair start rather than expanding around the center.

## Procedural templates and generated members

Repeated geometry uses nondestructive template/source objects.

Template records are included in JSON authoring metadata but are excluded from GLB:

```json
{
  "templates": [
    {
      "name": "Shelf_Source",
      "role": "SHELF",
      "generatorGroup": "SHELF_LEVELS"
    }
  ]
}
```

Generated members identify their source generator group:

```json
{
  "generated": true,
  "generatorGroup": "SHELF_LEVELS"
}
```

The runtime does not need the original template object if it consumes baked geometry. Template metadata is retained so authoring/debugging tools can reconstruct how the family was built.

## Generator metadata

```json
{
  "generator": {
    "supported": true,
    "revision": 4
  }
}
```

`revision` is an authoring rebuild counter, not a schema compatibility version.

## Quality report

Every converted family can carry a quality report:

```json
{
  "quality": {
    "ready": false,
    "score": 61,
    "roleCoverage": 0.72,
    "missingRoleGroups": [
      ["FRAME_LEFT", "FRAME_RIGHT", "FRAME_HEAD"]
    ],
    "warnings": [],
    "errors": [
      "Missing required role: FRAME_LEFT or FRAME_RIGHT or FRAME_HEAD"
    ]
  }
}
```

This is primarily library-production metadata. The mobile BIM runtime may ignore it after an asset has been approved, but ingestion/library tooling should be able to reject or quarantine `ready=false` families.

## Custom parameters

`customParameters` remains available for advanced author-defined numeric values/drivers that are not part of the stable class semantic contract.

Runtime code should prefer class-defined `semanticParameters` whenever possible.

## Runtime strategy

Two execution modes are intentionally supported.

### Baked family geometry

The exported GLB is the evaluated family geometry for the active Type.

Advantages:

- simplest mobile runtime;
- deterministic visuals;
- Blender-specific generation code does not have to be reimplemented.

### Runtime-parametric family

The engine uses `familyKind`, semantic parameters, anchors, roles and rules to regenerate simple supported classes itself.

Advantages:

- continuous parameter editing inside the mobile BIM app;
- fewer baked geometry variants.

Recommended migration path:

1. ingest baked GLB + semantic JSON;
2. support runtime width/height/depth for simple classes;
3. implement selected semantic generators such as Sofa seat count and Stair step generation;
4. keep complex/unsupported families baked.

## Fields planned for later versions

- `familyId`
- `categoryId`
- `manufacturer`
- `modelNumber`
- `hostType`
- `placementOrigin`
- `facingDirection`
- `cutOpening`
- `materials`
- `materialParameters`
- `connectors`
- `lods`
- `collision`
- `planRepresentation`
- `thumbnail`
- `units`
- `constraints`
- `formulas`
- `nestedFamilies`
- `sourceLicense`
- `sourceAttribution`

## Compatibility rule

The mobile BIM importer must treat `schemaVersion` as an explicit compatibility boundary. Unknown versions should be rejected or routed through a migration layer rather than parsed heuristically.
