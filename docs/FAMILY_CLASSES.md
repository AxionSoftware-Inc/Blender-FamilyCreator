# Family Classes

Family Creator intentionally does **not** use one universal scaling algorithm for every Blender asset.

The conversion pipeline starts by assigning an exact family class. Every class owns its parameter contract and deformation strategy. This keeps the system predictable and lets each class become progressively smarter without destabilizing unrelated families.

## Initial class registry

| Class | Group | Primary behavior |
|---|---|---|
| `SOFA` | Furniture | Width-driven; arms move, center upholstery stretches |
| `TABLE` | Furniture | Top stretches in plan; legs preserve section and move to corners |
| `CHAIR` | Furniture | Seat/back resize; frame and legs preserve thickness |
| `BED` | Furniture | Mattress/body resize; head/foot members stay anchored |
| `CABINET` | Casework | Carcass resizes; thin edge panels preserve thickness |
| `WARDROBE` | Casework | Width/height driven tall casework |
| `SHELF` | Casework | Board thickness protected; envelope resizes |
| `KITCHEN_BASE` | Casework | Primarily width-driven standardized cabinet |
| `KITCHEN_WALL` | Casework | Width/height driven wall cabinet |
| `DOOR` | Openings | Width/height vary; jamb/frame/hardware protected |
| `WINDOW` | Openings | Width/height vary; frame edges move, glazing spans stretch |
| `STAIR` | Circulation | Dedicated discrete generator; v1 only parameterizes safe width |
| `TOILET` | Plumbing | Mostly fixed-proportion fixture |
| `SINK` | Plumbing | Basin plan can resize; drain/faucet details protected |
| `BATHTUB` | Plumbing | Tub length/width profile; rim/drain details protected |
| `GENERIC` | Generic | Fallback bounding-box inference |

## Architecture rule

A new family class should be added to `family_types/registry.py` and its deformation/generation behavior should live in the family type layer, not as special cases scattered across Blender UI or export code.

Current object-level strategies live in `family_types/strategies.py`. More complex classes can graduate to dedicated modules, for example:

```text
family_types/
  sofa.py
  table.py
  door.py
  window.py
  stair.py
```

when their logic becomes large enough.

## Recommended development order

1. Sofa
2. Table
3. Door
4. Window
5. Cabinet / Wardrobe
6. Bed
7. Chair
8. Stair
9. Sink / Bathtub / Toilet

The first seven mostly need deterministic stretch/move/anchor rules. Stair is deliberately later because it requires discrete geometry generation (`step_count`, `tread_depth`, `riser_height`, landings and rail behavior), not ordinary scaling.

## Terminology

- **Family Class**: semantic kind such as `SOFA` or `DOOR` and its dedicated behavior.
- **Family Type / Variant**: a saved dimensional variant inside one family, such as `900x2100` or `1200x2100`.
- **Member Rule**: per-object per-axis `STRETCH`, `MOVE`, or `FIXED` behavior.

Keeping Class and Type separate avoids the ambiguity common in early prototypes.
