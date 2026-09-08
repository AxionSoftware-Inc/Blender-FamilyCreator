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
| `STAIR` | Circulation | Dedicated discrete generator; v0.2 only parameterizes safe width |
| `TOILET` | Plumbing | Mostly fixed-proportion fixture |
| `SINK` | Plumbing | Basin plan can resize; drain/faucet details protected |
| `BATHTUB` | Plumbing | Tub length/width profile; rim/drain details protected |
| `GENERIC` | Generic | Fallback bounding-box inference |

## Architecture rule

A new family class is registered in `family_types/registry.py`, then receives its own behavior module. The dispatcher in `family_types/strategies.py` contains no geometry heuristics; it only routes the selected class to the correct module.

Current structure:

```text
family_types/
  registry.py
  strategies.py
  common.py
  sofa.py
  table.py
  chair.py
  bed.py
  cabinet.py
  wardrobe.py
  shelf.py
  kitchen_base.py
  kitchen_wall.py
  door.py
  window.py
  stair.py
  toilet.py
  sink.py
  bathtub.py

  # shared implementation helpers only
  casework_base.py
  opening_base.py
  basin_base.py
  fixture_base.py
```

A class-specific module may reuse a shared helper, but its public behavior remains isolated behind its own file. This means Sofa can later gain seat-count logic, Door can gain frame/leaf/host logic, and Stair can gain a discrete tread generator without coupling those systems together.

## Semantic dimensions

Each class defines what the X/Y/Z envelope means. Examples:

- Bed: `X = width`, `Y = length`, `Z = height`
- Door: `X = width`, `Y = frame_depth`, `Z = height`
- Window: `X = width`, `Y = frame_depth`, `Z = height`
- Stair: `X = width`, `Y = total_run`, `Z = total_rise`

Only axes implemented by the current class strategy are editable. Unsupported dimensions are kept at their base value so exported metadata cannot disagree with the generated geometry.

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

The first seven mostly need deterministic member-role, stretch, move and anchor rules. Stair is deliberately later because it requires discrete geometry generation (`step_count`, `tread_depth`, `riser_height`, landings and railing behavior), not ordinary scaling.

## Terminology

- **Family Class**: semantic kind such as `SOFA` or `DOOR` and its dedicated behavior module.
- **Family Type / Variant**: a saved dimensional variant inside one family, such as `900x2100`, `1200x2100`, `2-seat`, or `3-seat`.
- **Member Rule**: per-object per-axis `STRETCH`, `MOVE`, or `FIXED` behavior.
- **Semantic Parameter Contract**: parameters expected by that family class, such as `seat_height`, `frame_width`, or `step_count`.

Keeping Class and Type separate avoids the ambiguity common in early prototypes.
