# Axion Family Package — Draft v1

This document defines the first interchange format produced by Blender Family Creator.

It is intentionally simple so the mobile BIM engine can integrate it before the Blender authoring side becomes more complex.

## Package

A family export currently contains:

```text
family_name.family.json
family_name.glb
```

`family.json` contains BIM/family semantics. `glb` contains the currently evaluated geometry.

## Manifest example

```json
{
  "schema": "axion.family",
  "schemaVersion": 1,
  "name": "Office Chair A",
  "category": "Furniture",
  "activeType": "600x600",
  "baseDimensions": {
    "width": 0.6,
    "depth": 0.6,
    "height": 0.9
  },
  "dimensions": {
    "width": 0.6,
    "depth": 0.6,
    "height": 0.9
  },
  "types": {
    "600x600": {
      "width": 0.6,
      "depth": 0.6,
      "height": 0.9
    }
  },
  "customParameters": {},
  "members": []
}
```

Blender dimensions are exported in meters.

## Member rules

Every family member can react independently to a dimension axis:

- `STRETCH`: geometry is stretched on the axis and its family-relative position follows the new dimension.
- `MOVE`: geometry keeps its size but its family-relative position follows the new dimension.
- `FIXED`: neither size nor family-relative position reacts to that dimension axis.

Example:

```json
{
  "name": "Leg.FL",
  "type": "MESH",
  "rules": {
    "x": "MOVE",
    "y": "MOVE",
    "z": "FIXED"
  }
}
```

This is authoring metadata. The runtime engine does not have to implement these rules immediately if the exported GLB is already baked.

## Custom parameters

Custom numeric parameters are authored on the Blender family root and can be connected to Blender properties through drivers.

A parameter record includes its human-readable name, Blender property key, default value, and its authoring bindings.

Runtime-compatible semantic parameter IDs should be introduced before the schema is considered stable.

## Runtime strategy

There are two valid future execution modes:

### Baked types

Each saved family Type gets its own pre-evaluated geometry variant.

Advantages:

- simplest mobile runtime;
- no Blender deformation logic has to be reimplemented;
- deterministic visual result.

Disadvantage: more geometry storage.

### Runtime-parametric

The family package contains enough rules/data for the mobile BIM engine to regenerate dimensions itself.

Advantages:

- continuous dimensions;
- fewer stored geometry variants.

Disadvantage: the runtime engine must reproduce every supported deformation behavior exactly.

Recommended path: start with baked type variants, then selectively make simple categories runtime-parametric.

## Fields planned for later schema versions

- `familyId`
- `categoryId`
- `manufacturer`
- `modelNumber`
- `hostType`
- `placementOrigin`
- `facingDirection`
- `cutOpening`
- `materials`
- `connectors`
- `lods`
- `collision`
- `planRepresentation`
- `thumbnail`
- `units`
- `constraints`
- `formulas`
- `nestedFamilies`

## Compatibility rule

The mobile BIM importer should reject an unsupported `schemaVersion` explicitly instead of trying to guess how to load it.
