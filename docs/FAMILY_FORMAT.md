# Axion Family Package — Schema v2

Blender Family Creator exports baked GLB geometry plus a versioned semantic BIM
manifest for Axion's mobile runtime. Schema v2 is intentionally extensible:
newer optional fields such as runtime proxies, baked Type variants, thumbnails,
runtime cost, mobile budgets and LODs do not invalidate older v2 packages that
omit those optional extensions.

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

- `.family.json` is the authoritative semantic/runtime contract.
- the primary `.glb` is the evaluated active Type.
- `variants/` contains optional baked saved-Type geometry.
- `lod/` contains optional non-destructive mobile derivatives.
- the thumbnail is optional and a render failure is non-fatal.
- procedural source templates remain in Blender authoring state and are excluded
  from exported runtime geometry.

Package export is **validate-before-overwrite**. The complete new package is
first generated in a sibling same-filesystem staging directory, including
primary/variant/LOD/thumbnail artifacts. The manifest must pass `schema.py`
before the destination package is touched.

During commit, existing target files are moved into temporary backups and the
new manifest is promoted last. A normal commit failure rolls back replaced files
to the previous package. If the filesystem also prevents a rollback restore,
that secondary failure is surfaced explicitly as an incomplete rollback rather
than being hidden.

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

`familyId` is the stable runtime/library identity. Batch conversion derives it
from exact Family Class plus source-relative path. Runtime importers should
reject unknown schema versions or route them through an explicit migration
layer.

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

Family semantics use Blender-style right-handed Z-up coordinates. GLB geometry
is exported with glTF Y-up conversion enabled.

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

All dimensions are positive meters. A saved Family Type is a named snapshot of
overall dimensions plus class semantic parameters.

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

Each class is a separate behavior contract even when classes share low-level
geometry primitives.

## Semantic parameters and members

Stable class keys include:

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

Rules are `STRETCH`, `MOVE`, or `FIXED`. A member produced by family-level
semantic refinement may additionally contain a diagnostic `roleRefinement`.

## Transform semantics and shear safety

Family `MOVE` operates in Family/root axes. `STRETCH` is applied to the member's
canonical local basis using a one-to-one best-aligned local/family axis mapping.
This preserves canonical rotation and avoids the shear that can occur when an
anisotropic Family-axis scale matrix is multiplied directly into an arbitrarily
rotated object basis.

The captured source transform is still authoritative. If the imported source
already contains canonical matrix shear, Preflight reports
`shearedTransformMembers` and routes the family to review instead of silently
normalizing potentially intentional geometry.

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

When GLB export is enabled, the active Type is represented as a baked geometry
variant. With “Bake All Saved Types” enabled, every saved Type can receive a GLB:

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

The primary variant must match `activeType`. Variant export temporarily applies
a Type, rebuilds supported procedural geometry, exports, then restores authoring
state.

## Runtime selection/collision proxy

`runtimeProxy` supplies cheap hit-testing/coarse collision metadata without
reading every GLB triangle:

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

The collision proxy is deliberately coarse; it is not a physics-quality
collision mesh.

## Runtime cost

Every new export measures active evaluated geometry after Blender modifiers and
also inventories material/texture pressure:

```json
{
  "runtimeCost": {
    "measurement": "EVALUATED_TRIANGULATED_GEOMETRY",
    "textureMemoryEstimate": "UNCOMPRESSED_RGBA8",
    "memberCount": 6,
    "meshObjects": 6,
    "nonMeshObjects": 0,
    "vertices": 125000,
    "triangles": 240000,
    "materialSlots": 8,
    "uniqueMaterials": 6,
    "drawCallEstimate": 10,
    "textureCount": 5,
    "texturePixels": 20971520,
    "maxTextureDimension": 4096,
    "estimatedTextureBytesRGBA": 83886080,
    "estimatedTextureMemoryMiB": 80.0,
    "textures": [
      {
        "name": "Fabric_Albedo",
        "width": 4096,
        "height": 4096,
        "pixels": 16777216,
        "estimatedBytesRGBA": 67108864
      }
    ],
    "members": []
  }
}
```

Texture memory is a conservative **uncompressed RGBA8 estimate**, not the actual
compressed GLB payload size or guaranteed GPU residency. It is meant for
relative mobile-budget diagnostics.

`drawCallEstimate` is derived from material indices actually referenced by
evaluated polygons, so unused vendor material slots do not inflate the estimate.
It is still an estimate, not a renderer-specific measured frame draw count.

## Mobile budget policy v2

`mobileBudget` is a runtime optimization diagnostic, not a semantic validity
gate:

```json
{
  "mobileBudget": {
    "policyVersion": 2,
    "familyKind": "BED",
    "status": "OVER_TARGET",
    "sourceTriangles": 240000,
    "sourceMaterialSlots": 8,
    "sourceDrawCallEstimate": 10,
    "sourceMaxTextureDimension": 4096,
    "sourceTextureMemoryMiB": 80.0,
    "budget": {
      "lod0TargetTriangles": 250000,
      "lod0HardTriangles": 700000,
      "lod1TargetTriangles": 90000,
      "lod2TargetTriangles": 18000,
      "targetMaterialSlots": 12,
      "targetDrawCalls": 18,
      "targetTextureDimension": 2048,
      "hardTextureDimension": 4096,
      "targetTextureMemoryMiB": 96
    },
    "optimizationReasons": ["TEXTURE_DIMENSION"],
    "geometryLodRecommended": false,
    "materialOptimizationRecommended": false,
    "textureOptimizationRecommended": true,
    "suggestedLod1Ratio": 0.375,
    "suggestedLod2Ratio": 0.075,
    "warnings": [
      "Texture dimension reaches 4096px; target is 2048px"
    ]
  }
}
```

Status values:

- `WITHIN_TARGET`
- `OVER_TARGET`
- `OVER_HARD_LIMIT`

Supported machine-readable optimization reasons are:

```text
TRIANGLES
MATERIAL_SLOTS
DRAW_CALLS
TEXTURE_DIMENSION
TEXTURE_MEMORY
```

The three recommendation flags deliberately separate what should happen next:

- `geometryLodRecommended` — reduce mesh cost / generate or select LOD geometry;
- `materialOptimizationRecommended` — reduce material-slot/draw-call pressure;
- `textureOptimizationRecommended` — resize/repack/compress texture resources.

These fields are backward-compatible optional schema-v2 extensions. Older v2
packages that omit them remain valid; when present, `schema.py` validates their
types and reason values.

Policy v2 considers:

- LOD0 triangle count;
- material slots;
- estimated draw calls;
- maximum texture dimension;
- estimated uncompressed RGBA texture memory.

A semantically valid family can remain `automaticReady=true` while its mobile
budget says optimization is desirable. Geometry LOD ratios address geometry
only; texture/material pressure can keep a family `OVER_TARGET` even when its
mesh is already small.

## Mobile LOD derivatives

LOD generation is opt-in/default OFF until the current Blender 5.2 post-hardening
runtime gates are green. It never edits source family geometry: temporary copies
receive Decimate modifiers, are exported, and are removed.

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
    "protectedRoles": ["HARDWARE", "HANDLE", "CONNECTOR"]
  }
}
```

When source geometry is already below a geometry target, that LOD can alias
`LOD0` instead of writing a duplicate file. Small meshes, shape-key meshes and
semantic hardware/connectors are handled conservatively. A derivative can
remain above its target and emit a non-fatal export warning.

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

Thumbnail rendering uses temporary camera/lights/world state and restores the
authoring scene. Thumbnail failure is recorded in `exportWarnings` and does not
fail the family package.

## Hosted Door / Window semantics

Hosted opening families add `hosting` metadata with wall opening size,
insertion point, facing/up axes, flip capabilities and plan representation. Door
can publish hinge-side/swing metadata; Window publishes sill elevation.

Window validity is separate from frame-edit capability. A baked vendor Window
can be valid without distinct frame meshes. Quality may expose semantic
capability flags such as `separateFrame`, `separateGlass`,
`parametricFrameWidth`, `materialAddressableGlass` and `bakedSashOrPanel`.

## Materials

GLB remains the source of actual geometry/textures/render materials. JSON adds
stable material IDs, lightweight PBR factors and member-slot usage metadata for
runtime search/replacement. `runtimeCost` inventories resource pressure without
replacing the GLB material payload.

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
        "nonUniformScaleMembers": 0,
        "shearedTransformMembers": 0,
        "spatialComponentCount": 1
      },
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
- `reviewRecommended`: source/semantic checks recommend inspection.

Preflight can additionally detect source canonical shear and multiple separated
spatial clusters that may indicate several unrelated assets in one source file.
These are source-quality diagnostics; runtime mobile budget remains intentionally
separate.

## Export warnings

Optional/derivative failures are non-fatal when the primary family package
remains valid:

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

This is not required for runtime rendering. Repeated batch runs additionally
write `batch-source-index.json` at the library root so removed sources and
failed package refreshes can be diagnosed without deleting anything
automatically.

## Runtime adoption path

Recommended mobile-engine order:

1. load `library-index.json` and the selected family manifest;
2. use semantic quality and capabilities for authoring behavior;
3. use `runtimeProxy` for selection/coarse collision;
4. use mobile recommendation flags to distinguish geometry vs material vs texture optimization;
5. choose `geometryLods` based on device, distance and screen size when geometry LOD is useful;
6. implement Wall-host placement/cutting for Door/Window;
7. support simple dimension edits and selected runtime semantic generators;
8. keep complex unsupported deformation baked.

Incompatible contract changes require a new schema version or an explicitly
backward-compatible v2 extension.
