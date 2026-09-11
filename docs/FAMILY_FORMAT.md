# Axion Family Package — Schema v2

Blender Family Creator exports a baked glTF/GLB representation plus a versioned BIM manifest for Axion's mobile BIM runtime. Schema v2 is intentionally extensible: newer optional fields such as runtime proxies, baked Type variants, thumbnails, mobile budgets and LODs do not invalidate older v2 packages that omit them.

## Package layout

A full package can contain:

```text
family_name.family.json
family_name.glb
family_name.thumbnail.png
variants/
  wide.glb
  tall.glb
lod/
  lod1.glb
  lod2.glb
```

- `.family.json` is the semantic/runtime contract.
- the primary `.glb` is the currently evaluated active Type.
- `variants/` contains optional baked saved-Type geometry.
- `lod/` contains optional non-destructive mobile derivatives.
- the thumbnail is optional and a render failure never invalidates an otherwise valid family.
- procedural source templates remain in Blender authoring state but are excluded from exported runtime geometry.

Before finalization the addon validates the manifest with `schema.py`. If a later schema/write error occurs, newly created primary/variant/LOD/thumbnail artifacts belonging to that transaction are cleaned up.

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

`familyId` is the stable runtime/library identity. Batch conversion derives it from exact Family Class plus source-relative path. Runtime importers should reject unknown schema versions or pass them through an explicit migration layer.

## Units and coordinate systems

```json
{
  "units": {"length": "meter"},
  "coordinateSystems": {
    "family": "RIGHT_HANDED_Z_UP",
    "geometry": "GLTF_RIGHT_HANDED_Y_UP"
  }
}
```

Family semantics use Blender-style right-handed Z-up coordinates. GLB geometry is exported with glTF Y-up conversion enabled.

## Dimensions and saved Types

```json
{
  "baseDimensions": {"width": 2.1, "depth": 0.9, "height": 0.82},
  "dimensions": {"width": 2.1, "depth": 0.9, "height": 0.82},
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

All dimensions are positive meters. A saved Family Type is a named snapshot of overall dimensions plus class semantic parameters.

## Family Classes

Current authoring classes:

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

Each class is a separate semantic behavior contract even when classes share low-level geometry primitives.

## Semantic parameters and members

Examples of stable class keys:

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

Each exportable member has a semantic role and axis rules:

```json
{
  "name": "Table_Leg_FL",
  "type": "MESH",
  "role": "LEG",
  "generated": false,
  "rules": {"x": "MOVE", "y": "MOVE", "z": "STRETCH"}
}
```

Rules are `STRETCH`, `MOVE`, or `FIXED`. A member produced by family-level semantic refinement may additionally contain a diagnostic `roleRefinement` string such as `BED_MATTRESS_CANDIDATE`.

## Family profile and axis anchors

`familyProfile` publishes class metadata used by runtime/library UIs:

```json
{
  "familyProfile": {
    "label": "Sofa",
    "group": "Furniture",
    "category": "Furniture",
    "strategy": "SOFA",
    "logicModule": "family_types.sofa",
    "editableAxes": ["X"],
    "axisParameters": {"X": "width", "Y": "depth", "Z": "height"},
    "axisAnchors": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "parameters": ["width", "depth", "height", "seat_height", "arm_width", "seat_count"],
    "roleCounts": {"SEAT": 3, "ARM_LEFT": 1, "ARM_RIGHT": 1}
  }
}
```

Anchor values are `CENTER`, `MIN`, and `MAX`.

## Baked Type geometry

When GLB export is enabled, the active Type is always represented as a baked geometry variant. With “Bake All Saved Types” enabled, every saved Type can receive a GLB:

```json
{
  "geometryVariants": {
    "Default": {"uri": "family.glb", "baked": true, "primary": true},
    "Wide": {"uri": "variants/wide.glb", "baked": true, "primary": false}
  },
  "geometryStrategy": {
    "mode": "BAKED_TYPE_VARIANTS",
    "activeType": "Default",
    "variantCount": 2
  }
}
```

`geometryStrategy.mode` is `BAKED_ACTIVE_TYPE` for one variant or `BAKED_TYPE_VARIANTS` for multiple variants. The primary variant must match `activeType`.

## Runtime selection/collision proxy

`runtimeProxy` supplies cheap hit-testing/coarse collision metadata without reading every GLB triangle:

```json
{
  "runtimeProxy": {
    "coordinateSystem": "RIGHT_HANDED_Z_UP",
    "selection": {
      "shape": "AABB",
      "min": [-0.6, -0.4, 0.0],
      "max": [0.6, 0.4, 0.75],
      "center": [0.0, 0.0, 0.375],
      "size": [1.2, 0.8, 0.75]
    },
    "collision": {
      "shape": "AABB",
      "coarse": true,
      "center": [0.0, 0.0, 0.375],
      "size": [1.2, 0.8, 0.75]
    },
    "planFootprint": {
      "shape": "RECTANGLE",
      "min": [-0.6, -0.4],
      "max": [0.6, 0.4],
      "baseZ": 0.0
    },
    "typeBounds": {}
  }
}
```

The collision proxy is deliberately coarse; it is not a physics-quality collision mesh.

## Runtime geometry cost and mobile budget

Every new export measures the active evaluated family geometry after Blender modifiers:

```json
{
  "runtimeCost": {
    "measurement": "EVALUATED_TRIANGULATED_GEOMETRY",
    "memberCount": 6,
    "meshObjects": 6,
    "nonMeshObjects": 0,
    "vertices": 125000,
    "triangles": 240000,
    "materialSlots": 8,
    "members": []
  }
}
```

`mobileBudget` is a runtime optimization diagnostic, not a semantic validity gate:

```json
{
  "mobileBudget": {
    "policyVersion": 1,
    "familyKind": "BED",
    "status": "OVER_TARGET",
    "sourceTriangles": 240000,
    "sourceMaterialSlots": 8,
    "budget": {
      "lod0TargetTriangles": 250000,
      "lod0HardTriangles": 700000,
      "lod1TargetTriangles": 90000,
      "lod2TargetTriangles": 18000,
      "targetMaterialSlots": 12
    },
    "suggestedLod1Ratio": 0.375,
    "suggestedLod2Ratio": 0.075,
    "warnings": []
  }
}
```

Status values:

- `WITHIN_TARGET`
- `OVER_TARGET`
- `OVER_HARD_LIMIT`

A semantically valid family can remain `automaticReady=true` while its mobile budget says optimization is desirable.

## Mobile LOD derivatives

LOD generation is opt-in until runtime validation is complete. It never edits source family geometry: temporary copies receive Decimate modifiers, are exported, and are removed.

```json
{
  "geometryLods": {
    "LOD0": {
      "uri": "family.glb",
      "generated": false,
      "triangles": 240000,
      "targetTriangles": 250000,
      "meetsTarget": true,
      "ratio": 1.0
    },
    "LOD1": {
      "uri": "lod/lod1.glb",
      "generated": true,
      "triangles": 88000,
      "targetTriangles": 90000,
      "meetsTarget": true,
      "requestedRatio": 0.375,
      "protectedOrSkippedMembers": []
    },
    "LOD2": {
      "uri": "lod/lod2.glb",
      "generated": true,
      "triangles": 17500,
      "targetTriangles": 18000,
      "meetsTarget": true,
      "requestedRatio": 0.075,
      "protectedOrSkippedMembers": []
    }
  },
  "lodStrategy": {
    "mode": "NON_DESTRUCTIVE_DECIMATE",
    "source": "LOD0",
    "levelCount": 3,
    "protectedRoles": ["HARDWARE"]
  }
}
```

When source geometry is already below a level target, that level can alias `LOD0` instead of writing a duplicate file. Small meshes, shape-key meshes, and semantic hardware/connectors are treated conservatively; a derivative can remain above its target and emit a non-fatal export warning.

## Thumbnail

```json
{
  "thumbnail": {
    "uri": "family.thumbnail.png",
    "width": 512,
    "height": 512,
    "format": "PNG",
    "transparent": true
  }
}
```

Thumbnail rendering uses temporary camera/lights/world state and restores the authoring scene. Thumbnail failure is recorded in `exportWarnings` and does not fail the family package.

## Hosted Door / Window semantics

Hosted opening families add `hosting` metadata with wall opening size, insertion point, facing/up axes, flip capabilities and plan representation. Door can publish hinge-side/swing metadata; Window publishes sill elevation.

Window validity is separate from frame-edit capability. A baked vendor Window can be valid without distinct frame meshes. Quality may expose semantic capability flags such as:

```json
{
  "quality": {
    "semanticCapabilities": {
      "separateFrame": false,
      "separateGlass": true,
      "parametricFrameWidth": false,
      "materialAddressableGlass": true,
      "bakedSashOrPanel": true
    }
  }
}
```

## Materials

GLB is the source of actual geometry/textures/render materials. JSON adds stable material IDs, lightweight PBR factors and member-slot usage metadata for runtime search/replacement.

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
      "stats": {"meshPolygons": 620000, "nonUniformScaleMembers": 0},
      "warnings": ["Heavy source geometry: 620,000 polygons"],
      "severe": []
    },
    "warnings": [],
    "errors": []
  }
}
```

- `ready`: required semantic class roles are present.
- `automaticReady`: package can enter the semantic library without manual review.
- `reviewRecommended`: conversion succeeded, but source/semantic checks recommend inspection.

Runtime mobile budget is intentionally separate from these semantic decisions.

## Export warnings

Derivative failures and optional-output failures are non-fatal when the primary family package remains valid:

```json
{
  "exportWarnings": [
    "Thumbnail render failed: ...",
    "LOD: LOD2 has 24000 triangles; target is 18000"
  ]
}
```

## Source traceability

Batch packages can include local production traceability:

```json
{
  "source": {
    "asset": "C:/assets/vendor_a/sofa_01.glb",
    "key": "vendor_a/sofa_01"
  }
}
```

This is not required for runtime rendering.

## Runtime adoption path

Recommended mobile-engine order:

1. ingest manifest + LOD0 GLB;
2. index by `familyId`, class, Types, capabilities and mobile cost;
3. use `runtimeProxy` for selection/coarse collision;
4. choose `geometryLods` based on screen size/distance/device budget;
5. implement Wall-host placement/cutting for Door/Window;
6. support simple dimension edits and selected runtime semantic generators;
7. keep complex unsupported deformation baked.

Incompatible contract changes require a new schema version or an explicitly backward-compatible v2 extension.
