# Blender Family Creator

Turn ordinary Blender asset models into **parameter-driven BIM families** for Axion's mobile BIM stack.

The goal is not to clone Revit's editor UI. The goal is to exploit Blender's enormous model ecosystem and convert existing assets into reusable, typed, parameterized families quickly.

## Why this exists

A BIM engine without a starting library is painful: doors, windows, chairs, tables, sanitary fixtures, trees, equipment and hundreds of other assets all have to be modeled and parameterized manually.

Blender already has millions of reusable models. Family Creator adds a BIM-oriented layer on top:

- Create a family from one or many selected Blender objects.
- Generate Width / Depth / Height family parameters.
- Smart-analyze each member with per-axis **Stretch / Move / Fixed** behavior.
- Save multiple family **Types** such as `900x2100`, `1200x2100`, etc.
- Add arbitrary float family parameters.
- Bind custom parameters to Blender RNA properties/modifiers using drivers.
- Export a `.family.json` manifest plus a baked `.glb` for the mobile BIM engine.

## The key idea: don't blindly scale everything

Naive XYZ scaling destroys many models. A chair leg becomes thicker, a handle stretches, hinges deform, and detailed assets become unusable.

Family Creator gives every child object a rule on every family axis:

| Rule | Meaning | Typical use |
|---|---|---|
| `STRETCH` | resize geometry on that family axis | tabletop, door leaf, frame rail |
| `MOVE` | preserve geometry size but move with the family edge | legs, handles, hinges |
| `FIXED` | preserve size and position on that axis | centered detail, fixed hardware |

`Smart Analyze` guesses these rules from each object's bounding-box span and location. The artist can override them in the sidebar.

## Current MVP workflow

1. Import or open a Blender asset.
2. Select all objects that belong to one asset.
3. Open **3D Viewport → Sidebar → Family**.
4. Enter a family name and click **Create Family from Selection**.
5. Change Width / Depth / Height and inspect the result.
6. Select individual members and correct X/Y/Z rules where needed.
7. Save useful dimensions as Family Types.
8. Export the family package.

## Custom parameter drivers

Family Creator can create an arbitrary numeric parameter on the family root and drive an RNA property on a selected member.

Examples:

- Bevel width
- Array count/offset (numeric properties)
- Solidify thickness
- object transform channels
- Geometry Nodes modifier inputs exposed as animatable properties

The advanced binding panel accepts an RNA data path and optional array index. The driver's variable is named `p`, so expressions can be `p`, `p*0.5`, `max(p, 0.02)`, etc.

## Export format

The initial package is intentionally simple and engine-friendly:

```text
my_family.family.json
my_family.glb
```

The JSON contains family metadata, dimensions, types, custom parameters, member rules and schema version. GLB is exported with modifiers applied and Blender custom properties included as glTF extras.

Future versions should add:

- batch GLB generation for every saved Type;
- material parameter mappings;
- host/placement rules (wall-hosted, floor-hosted, face-hosted);
- connectors and MEP ports;
- 2D symbolic representation / plan proxy;
- LOD generation;
- collision proxy generation;
- category templates (Door, Window, Furniture, Plumbing, Equipment...);
- formula graph and constrained reference planes;
- automatic repeated-part detection;
- semantic "smart stretch" using deform zones instead of object-level transforms;
- direct export adapter for the Axion mobile BIM engine's native family format.

## Development status

**v0.1.0 MVP** — architecture and first usable family-conversion pipeline.

This is deliberately a foundation rather than a toy one-file script. The next milestone is to test it against a representative set of real Blender assets (chair, table, door, window, sink, tree, cabinet) and improve the inference rules based on failures.
