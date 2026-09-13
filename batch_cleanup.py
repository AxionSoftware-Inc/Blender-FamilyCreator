"""Leak-resistant cleanup helpers for long Blender batch sessions.

The batch pipeline must not use a global orphan purge because the user's open
scene may contain unrelated zero-user datablocks. Instead we snapshot known
Blender ID collections before importing one asset and only remove datablocks
created after that snapshot.
"""

from __future__ import annotations

import bpy


# Keep this list broad enough for vendor assets while remaining version-safe:
# `_collection()` simply ignores names not exposed by the running Blender build.
# Objects themselves are removed separately by batch.py before this dependency
# cleanup runs.
DATA_COLLECTION_NAMES = (
    "meshes",
    "curves",
    "metaballs",
    "pointclouds",
    "materials",
    "images",
    "textures",
    "armatures",
    "cameras",
    "lights",
    "lattices",
    "shape_keys",
    "node_groups",
    "actions",
    "fonts",
    "speakers",
    "volumes",
    "worlds",
    "grease_pencils",
    "particles",
    "movieclips",
    "masks",
    "collections",
)


def _collection(name):
    return getattr(bpy.data, name, None)


def _pointer(datablock):
    try:
        return int(datablock.as_pointer())
    except Exception:
        return id(datablock)


def snapshot_datablocks():
    """Capture identity of Blender IDs that existed before one asset import."""
    snapshot = {}
    for name in DATA_COLLECTION_NAMES:
        collection = _collection(name)
        if collection is None:
            continue
        try:
            snapshot[name] = {_pointer(item) for item in collection}
        except Exception:
            snapshot[name] = set()
    return snapshot


def _new_items(snapshot, name):
    collection = _collection(name)
    if collection is None:
        return []
    before = snapshot.get(name, set())
    try:
        return [item for item in collection if _pointer(item) not in before]
    except Exception:
        return []


def _remove_empty_new_collections(snapshot):
    collection_data = _collection("collections")
    if collection_data is None:
        return 0

    candidates = _new_items(snapshot, "collections")
    # Leaves first. Parent collection child counts are re-read as earlier leaf
    # candidates are removed, so nested empty trees usually collapse in one pass.
    candidates.sort(
        key=lambda collection: len(getattr(collection, "children_recursive", ())),
        reverse=False,
    )
    removed = 0
    for collection in candidates:
        try:
            if len(collection.objects) or len(collection.children):
                continue
            collection_data.remove(collection, do_unlink=True)
            removed += 1
        except Exception:
            continue
    return removed


def cleanup_new_datablocks(snapshot, max_passes=8):
    """Remove only post-snapshot zero-user IDs, iterating dependency layers.

    Example dependency chain after deleting imported objects:
      Mesh -> Material -> NodeGroup/Image

    Collections participate in the same progress loop. This matters for nested
    imported collections where deleting a leaf makes its parent eligible only
    after Blender updates the hierarchy. The loop stops only when neither an ID
    nor a collection was removed during a pass.
    """
    removed_by_type = {}
    passes = 0

    for _ in range(max(1, int(max_passes))):
        passes += 1
        progress = 0

        collection_removed = _remove_empty_new_collections(snapshot)
        if collection_removed:
            removed_by_type["collections"] = removed_by_type.get("collections", 0) + collection_removed
            progress += collection_removed

        removable = []
        removable_types = {}
        for name in DATA_COLLECTION_NAMES:
            if name == "collections":
                continue
            for datablock in _new_items(snapshot, name):
                try:
                    if int(datablock.users) != 0:
                        continue
                except Exception:
                    continue
                pointer = _pointer(datablock)
                removable.append(datablock)
                removable_types[pointer] = name

        if removable:
            typed_candidates = [
                (datablock, removable_types.get(_pointer(datablock), "unknown"))
                for datablock in removable
            ]

            removed_this_pass = 0
            try:
                bpy.data.batch_remove(ids=removable)
                for _datablock, name in typed_candidates:
                    removed_by_type[name] = removed_by_type.get(name, 0) + 1
                    removed_this_pass += 1
            except Exception:
                for datablock, name in typed_candidates:
                    collection = _collection(name)
                    if collection is None:
                        continue
                    try:
                        collection.remove(datablock)
                        removed_by_type[name] = removed_by_type.get(name, 0) + 1
                        removed_this_pass += 1
                    except Exception:
                        continue
            progress += removed_this_pass

        # Removing meshes/materials can release collections indirectly; give the
        # hierarchy another chance within the same pass and count that work too.
        collection_removed_after = _remove_empty_new_collections(snapshot)
        if collection_removed_after:
            removed_by_type["collections"] = (
                removed_by_type.get("collections", 0) + collection_removed_after
            )
            progress += collection_removed_after

        if progress == 0:
            break

    leftovers = {}
    for name in DATA_COLLECTION_NAMES:
        items = _new_items(snapshot, name)
        if items:
            leftovers[name] = len(items)

    return {
        "passes": passes,
        "removed": dict(sorted(removed_by_type.items())),
        "removedCount": sum(removed_by_type.values()),
        "leftovers": dict(sorted(leftovers.items())),
        "leftoverCount": sum(leftovers.values()),
        "complete": not leftovers,
    }
