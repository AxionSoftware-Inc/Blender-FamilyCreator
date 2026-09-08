# Blender Family Creator Roadmap

## Product goal

Convert large numbers of existing Blender assets into reusable BIM families with as little manual cleanup as possible.

The project should optimize for **library throughput**, not for reproducing every Revit Family Editor feature.

## v0.1 — Object-level family MVP

Status: implemented.

- Family root created from selected Blender objects.
- Width / Depth / Height parameters.
- Per-member X/Y/Z behavior: Stretch / Move / Fixed.
- Smart bounding-box rule inference.
- Preserve selected asset parent/child hierarchy.
- Family Types.
- Custom numeric parameters.
- Driver binding to Blender RNA properties and modifiers.
- `.family.json` metadata export.
- baked `.glb` export for mobile/runtime use.

## v0.2 — Asset Auto-Prepare

This is the next critical milestone for converting hundreds of downloaded Blender models.

- Detect meshes made from disconnected islands.
- Optional non-destructive split of loose parts into family members.
- Detect repeated/symmetric parts (legs, handles, hinges, wheels).
- Infer left/right/front/back/top/bottom anchors.
- Detect the dominant local axes even if an imported asset is rotated.
- Normalize family origin and ground plane.
- Detect suspicious transforms and unapplied scale.
- Add one-click `Prepare Asset -> Create Family -> Analyze` workflow.
- Preview deformation before committing.
- Quality score: green / yellow / red based on likely family behavior.

## v0.3 — Smart Stretch Zones

Object-level rules are not enough for single connected meshes. This milestone adds vertex/zone-level deformation.

- Reference planes on X/Y/Z.
- Fixed end zones + stretch middle zone.
- Vertex weights for deformation influence.
- Auto-generated Lattice or Geometry Nodes deformation graph.
- Keep hardware thickness while changing overall family dimensions.
- Example: door frame corners remain fixed while rails stretch.
- Example: cabinet handles preserve their dimensions while cabinet width changes.
- Example: sofa arms preserve thickness while the center cushion zone grows.

## v0.4 — BIM Semantics

- Category templates: Door, Window, Furniture, Plumbing Fixture, Equipment, Generic Model.
- Host behavior: free, floor-hosted, wall-hosted, face-hosted.
- Insertion point and facing direction.
- Door/window opening dimensions and wall-cut metadata.
- 2D plan/symbolic representation.
- Material parameters.
- Visibility parameters.
- Nested families.
- Formula parameters and min/max constraints.

## v0.5 — Runtime / Mobile BIM package

- Versioned Axion Family schema.
- Per-type geometry strategy: runtime-parametric where possible, baked variants otherwise.
- LOD0/LOD1/LOD2.
- collision proxy.
- thumbnail/preview.
- material manifest.
- optional compressed GLB/meshopt pipeline.
- native importer for the Axion mobile BIM engine.
- library index and search metadata.

## v0.6 — Batch Library Factory

- Folder import of `.blend`, `.fbx`, `.obj`, `.glb` assets.
- Automated conversion queue.
- rule templates per category.
- automatic type generation from dimension ranges.
- validation screenshots / thumbnails.
- reject queue for assets that need manual repair.
- bulk export of hundreds of `.family` packages.

## Design principle

The automated path should handle the easy 70–90% of assets quickly and clearly flag the remaining difficult models rather than silently producing broken families.
