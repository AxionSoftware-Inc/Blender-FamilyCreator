"""Leak-resistant cleanup helpers for long Blender batch sessions.

The batch pipeline must not use a global orphan purge because the user's open
scene may contain unrelated zero-user datablocks. Instead we snapshot known
Blender ID collections before importing one asset and only remove datablocks
created after that snapshot.
"""

from __future__ import annotations

import bpy


DATA_COLLECTION_NAMES = (
    "meshes",
    "curves",
    "metaballs",
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
    The first pass removes the mesh/material; a later pass can then remove the
    image or node group once its user count reaches zero.
    """
    removed_by_type = {}
    passes = 0

    _remove_empty_new_collections(snapshot)

    for _ in range(max(1, int(max_passes))):
        passes += 1
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

        if not removable:
            break

        typed_candidates = [
            (datablock, removable_types.get(_pointer(datablock), "unknown"))
            for datablock in removable
        ]

        try:
            bpy.data.batch_remove(ids=removable)
            for _datablock, name in typed_candidates:
                removed_by_type[name] = removed_by_type.get(name, 0) + 1
        except Exception:
            for datablock, name in typed_candidates:
                collection = _collection(name)
                if collection is None:
                    continue
                try:
                    collection.remove(datablock)
                    removed_by_type[name] = removed_by_type.get(name, 0) + 1
                except Exception:
                    continue

        _remove_empty_new_collections(snapshot)

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
