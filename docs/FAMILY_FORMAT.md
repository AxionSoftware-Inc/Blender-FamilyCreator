# Axion Family Package — Schema v2

Blender Family Creator v0.4 exports a baked glTF/GLB representation plus a versioned BIM manifest for Axion's mobile BIM engine.

## Package

```text
family_name.family.json
family_name.glb
```

- `.family.json` is the semantic/runtime contract.
- `.glb` is the currently evaluated exportable geometry.
- procedural source templates are retained in Blender authoring state but excluded from GLB.
- generated instances are included in GLB.

Before a package is finalized the addon validates the manifest against the schema-v2 invariants implemented in `schema.py`. Invalid partial `.family.json/.glb` output is removed.

## Identity and compatibility

```json
{
  "schema": "axion.family",
  "schemaVersion": 2,
  "familyId": "axion:sofa:vendor_a/sofa_01",
  "familyKind": "SOFA",
  "name": "Sofa 01"
}
```

`familyId` is the stable runtime/library identity. Batch conversion derives it from Family Class plus source-relative path, avoiding collisions between same-named assets in different folders.

The importer must reject unknown `schemaVersion` values or route them through an explicit migration layer.

## Units and coordinate systems

```json
{
  "units": {
    "length": "meter"
  },
  "coordinateSystems": {
    "family": "RIGHT_HANDED_Z_UP",
    "geometry": "GLTF_RIGHT_HANDED_Y_UP"
  }
}
```

Family semantic axes use Blender-style right-handed Z-up coordinates. Exported GLB uses the standard glTF right-handed Y-up convention because `export_yup` is enabled. Runtime code must not silently mix the two spaces.

## Dimensions and Types

```json
{
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
  "activeType": "3-seat",
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
  }
}
```

All dimensions are positive meters. A Family Type is a named snapshot of overall dimensions plus semantic parameters.

## Family Classes

Current schema-v2 authoring classes:

```text
GENERIC
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
```

Different `familyKind` values are separate behavior contracts even where they share low-level transform primitives.

## Semantic parameters

Examples:

```text
SOFA          seat_height, arm_width, seat_count
TABLE         top_thickness
CHAIR         seat_height
BED           mattress_height
CABINET       panel_thickness
WARDROBE      panel_thickness
SHELF         panel_thickness, shelf_count
KITCHEN_BASE  panel_thickness, toe_kick_height
KITCHEN_WALL  panel_thickness
DOOR          frame_width, panel_thickness
WINDOW        frame_width, sill_height
STAIR         total_run, total_rise, tread_depth, riser_height, step_count
TOILET        connector_height
SINK          drain_diameter
BATHTUB       rim_thickness
```

These IDs are stable semantic keys. Runtime code should never derive behavior by parsing the UI label.

## Member semantics

Each exportable member contains its class role plus axis behavior:

```json
{
  "name": "Table_Leg_FL",
  "type": "MESH",
  "role": "LEG",
  "generated": false,
  "generatorGroup": "",
  "rules": {
    "x": "MOVE",
    "y": "MOVE",
    "z": "STRETCH"
  }
}
```

Supported rules:

- `STRETCH`: resize on that family axis and follow the class anchor.
- `MOVE`: retain part size while following the changing boundary.
- `FIXED`: do not react to that axis.

Typical roles include `SEAT`, `ARM_LEFT`, `TOP`, `LEG`, `FRAME_LEFT`, `GLASS`, `SHELF`, `TREAD`, `RISER`, `BASIN`, `DRAIN`, `BOWL` and `CONNECTOR`.

## Class profile and anchors

```json
{
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
    "parameters": ["width", "depth", "height", "seat_height", "arm_width", "seat_count"],
    "roleCounts": {
      "SEAT": 3,
      "ARM_LEFT": 1,
      "ARM_RIGHT": 1
    }
  }
}
```

Draft anchor values are `CENTER`, `MIN`, and `MAX`. A Door with Z=`MIN`, for example, remains on its threshold/floor plane while height changes.

## Templates and generated members

Procedural repetition is nondestructive. Original source modules become hidden authoring templates, while generated copies carry a generator group.

```json
{
  "templates": [
    {
      "name": "Seat_Source",
      "role": "SEAT",
      "generatorGroup": "SOFA_SEATS"
    }
  ],
  "generator": {
    "supported": true,
    "revision": 4
  }
}
```

Template object subtrees are duplicated with linked mesh data where possible, preserving child details/materials without duplicating the mesh payload in Blender memory.

`generator.revision` is an authoring rebuild counter, not a schema compatibility version.

## Hosted Door / Window semantics

Hosted opening families add a `hosting` record:

```json
{
  "hosting": {
    "hostType": "WALL",
    "cutHost": true,
    "opening": {
      "shape": "RECTANGLE",
      "width": 0.9,
      "height": 2.1,
      "depth": 0.15
    },
    "insertionPoint": "THRESHOLD_CENTER",
    "placementOriginLocal": [0.0, 0.0, -1.05],
    "elevationFromLevel": 0.0,
    "facingDirection": [0.0, 1.0, 0.0],
    "upDirection": [0.0, 0.0, 1.0],
    "canFlipFacing": true,
    "canFlipHand": true,
    "planRepresentation": {
      "type": "DOOR_SWING",
      "openingWidth": 0.9,
      "leafLength": 0.9,
      "hingeSide": "LEFT",
      "swingAngleDegrees": 90.0,
      "swingDirection": "UNKNOWN"
    }
  }
}
```

Window uses `SILL_CENTER`, exports `elevationFromLevel` from `sill_height`, and uses a `WINDOW_OPENING` plan representation.

Door hinge side is inferred from `HINGE` role location, with handle location as fallback. Swing direction remains `UNKNOWN` when it cannot be inferred safely.

## Materials

GLB remains the source of geometry, textures and actual render material payloads. JSON adds stable material identification and lightweight PBR metadata for runtime search/replacement:

```json
{
  "materials": [
    {
      "id": "oak",
      "name": "Oak",
      "pbr": {
        "baseColorFactor": [0.5, 0.3, 0.15, 1.0],
        "metallicFactor": 0.0,
        "roughnessFactor": 0.55,
        "alphaFactor": 1.0
      },
      "usages": [
        {"member": "TableTop", "slot": 0}
      ]
    }
  ]
}
```

Material IDs are slugged and collision-safe within one family.

## Quality and preflight

```json
{
  "quality": {
    "ready": true,
    "automaticReady": false,
    "reviewRecommended": true,
    "score": 86,
    "roleCoverage": 0.95,
    "missingRoleGroups": [],
    "missingRecommendedRoleGroups": [],
    "preflight": {
      "reviewRecommended": true,
      "stats": {
        "meshPolygons": 620000,
        "nonUniformScaleMembers": 0
      },
      "warnings": ["Heavy source geometry: 620,000 polygons"],
      "severe": []
    },
    "warnings": ["Heavy source geometry: 620,000 polygons"],
    "errors": []
  }
}
```

- `ready`: required semantic class roles are present.
- `automaticReady`: family can enter the library without manual review.
- `reviewRecommended`: conversion succeeded, but semantics/preflight recommend inspection.

Preflight currently checks source polygon count, canonical scale, non-uniform scale, mirrored transforms, shape keys, armatures and suspicious class dimensions/unit scale.

## Source traceability

Batch-generated packages can include:

```json
{
  "source": {
    "asset": "/source/vendor_a/sofa_01.glb",
    "key": "vendor_a/sofa_01"
  }
}
```

This is library-production metadata and is not required for runtime rendering.

## Advanced custom parameters

`customParameters` remains available for author-defined numeric values and Blender driver bindings outside the stable class contract. Mobile/runtime implementations should prefer `semanticParameters` for known class behavior.

## Runtime adoption path

Recommended mobile-engine rollout:

1. ingest baked GLB + schema-v2 JSON;
2. index by `familyId`, `familyKind`, Types and materials;
3. implement Wall-host placement/cutting for Door/Window;
4. support direct width/height/depth editing for simple classes;
5. port selected semantic generators such as Sofa seat count and straight Stair generation;
6. leave complex/unsupported deformation baked until a matching runtime generator exists.

## Future schema candidates

Potential later-version fields include:

- `categoryId`
- `manufacturer`
- `modelNumber`
- richer connector definitions
- LODs
- collision meshes
- thumbnails
- constraints/formulas
- nested families
- source licensing/attribution
- richer material parameters and texture references

Adding incompatible semantics requires a new schema version or an explicit backward-compatible extension rule.
