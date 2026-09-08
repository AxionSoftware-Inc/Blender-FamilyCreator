# Blender Family Creator

Turn ordinary Blender assets into **typed, parameter-driven BIM families** for Axion's mobile BIM stack.

The core idea is simple: **do not force every model through one universal scaling algorithm**. A sofa, table, window and stair obey different geometry rules, so Family Creator assigns an exact semantic **Family Class** first and runs dedicated logic for that class.

## Why this exists

A BIM engine without a starting family library is painful: doors, windows, chairs, tables, sanitary fixtures, cabinets and hundreds of other assets have to be modeled and parameterized manually.

Blender already has an enormous reusable model ecosystem. Family Creator adds a BIM-oriented conversion layer on top so existing assets can become reusable families quickly.

## Family Class vs Family Type

These are intentionally separate concepts:

- **Family Class** = semantic behavior such as `SOFA`, `TABLE`, `DOOR`, `WINDOW`, `STAIR`.
- **Family Type / Variant** = saved dimensional configuration inside one family, such as `900x2100`, `1200x2100`, `2-seat`, `3-seat`, etc.

The class determines **how geometry is allowed to change**. The type stores one concrete set of parameter values.

## Current family classes

The v0.2 registry contains:

- Furniture: Sofa, Table, Chair, Bed
- Casework: Cabinet, Wardrobe, Shelf, Kitchen Base Cabinet, Kitchen Wall Cabinet
- Openings: Door, Window
- Circulation: Stair
- Plumbing: Toilet, Sink/Basin, Bathtub
- Generic fallback

See `docs/FAMILY_CLASSES.md` for the exact behavior of each class.

## Dedicated deformation strategies

Every member still exposes per-axis rules:

| Rule | Meaning | Typical use |
|---|---|---|
| `STRETCH` | resize geometry on that family axis | sofa center, tabletop, glazing, cabinet carcass |
| `MOVE` | preserve geometry size but move with the changing boundary | sofa arms, table legs, frame edges, handles |
| `FIXED` | preserve size and position on that axis | protected hardware and fixed details |

But these rules are no longer inferred identically for every model.

Examples:

- **Sofa**: primarily width-driven; side arms move while central upholstery stretches.
- **Table**: tabletop stretches in plan; legs preserve their section and move toward new corners.
- **Door / Window**: width and height vary while depth is protected; edge frame parts move and panel/glazing spans stretch.
- **Casework**: panel thickness should stay stable while the overall carcass changes size.
- **Stair**: ordinary scaling is intentionally limited. Width works in v0.2, while run/rise/step-count will be handled by a dedicated discrete stair generator.

## Current workflow

1. Import or open a Blender asset.
2. Select all objects belonging to that asset.
3. Open **3D Viewport → Sidebar → Family**.
4. Enter a family name.
5. Choose the exact **Family Class**.
6. Click **Create Typed Family from Selection**.
7. Change dimensions and inspect the result.
8. Run **Analyze by Family Class** after geometry cleanup or class changes.
9. Override individual member rules only when necessary.
10. Save useful dimensional variants as Family Types.
11. Export the family package.

## Export format

The initial package remains engine-friendly:

```text
my_family.family.json
my_family.glb
```

The JSON now includes the semantic `familyKind`, family profile, editable axes, expected class parameters, dimensions, saved variants, custom parameters and member rules.

## Architecture

```text
family_types/
  registry.py      # exact BIM family classes and parameter contracts
  strategies.py    # per-class object-level deformation rules

typed.py           # routes create/analyze/export through the selected class
core.py            # shared family storage, transforms, types and GLB export
```

As one class becomes more sophisticated, its logic can move into a dedicated module (`sofa.py`, `door.py`, `stair.py`, etc.) without affecting unrelated families.

## Development direction

The priority is not adding hundreds of generic heuristics. It is making a small set of high-value family classes extremely reliable, then converting many existing Blender assets through those deterministic pipelines.

Recommended order:

1. Sofa
2. Table
3. Door
4. Window
5. Cabinet / Wardrobe
6. Bed
7. Chair
8. Stair
9. Plumbing fixtures

After these are strong enough, batch conversion can turn large Blender model collections into an Axion-ready starting library very quickly.

## Development status

**v0.2.0 — Typed Family Architecture**

The addon now has explicit family classification and separate deformation strategies. Runtime validation inside Blender with representative real assets is the next test layer.
