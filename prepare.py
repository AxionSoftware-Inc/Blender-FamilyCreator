import bpy


DEFAULT_MAX_LOOSE_ISLANDS = 32


def count_loose_islands(mesh, stop_after=None):
    vertex_count = len(mesh.vertices)
    if vertex_count == 0:
        return 0

    parent = list(range(vertex_count))
    rank = [0] * vertex_count

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a, b):
        ra = find(a)
        rb = find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            parent[ra] = rb
        elif rank[ra] > rank[rb]:
            parent[rb] = ra
        else:
            parent[rb] = ra
            rank[ra] += 1

    for edge in mesh.edges:
        a, b = edge.vertices
        union(int(a), int(b))

    roots = set()
    for index in range(vertex_count):
        roots.add(find(index))
        if stop_after is not None and len(roots) > stop_after:
            return len(roots)
    return len(roots)


def _can_split(obj, max_islands):
    if obj.type != "MESH" or obj.data is None:
        return False, 0, "not_mesh"
    if getattr(obj.data, "shape_keys", None) is not None:
        return False, 0, "shape_keys"
    if any(modifier.type == "ARMATURE" for modifier in obj.modifiers):
        return False, 0, "armature"

    islands = count_loose_islands(obj.data, stop_after=max_islands)
    if islands < 2:
        return False, islands, "single_island"
    if islands > max_islands:
        return False, islands, "too_many_islands"
    return True, islands, "eligible"


def split_loose_object(context, obj, max_islands=DEFAULT_MAX_LOOSE_ISLANDS):
    eligible, islands, reason = _can_split(obj, max_islands)
    if not eligible:
        return {
            "source": obj.name,
            "split": False,
            "islands": islands,
            "reason": reason,
            "objects": [obj],
        }

    before = set(bpy.data.objects)
    previous_selection = list(context.selected_objects)
    previous_active = context.view_layer.objects.active
    previous_mode = context.mode

    try:
        if previous_mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                pass

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.separate(type="LOOSE")
        bpy.ops.object.mode_set(mode="OBJECT")

        result = [candidate for candidate in bpy.data.objects if candidate not in before]
        if obj.name in bpy.data.objects:
            result.append(obj)

        result = list(dict.fromkeys(result))
        result.sort(key=lambda item: item.name)
        for index, part in enumerate(result, start=1):
            part.name = f"{obj.name}_Part_{index:02d}"

        return {
            "source": obj.name,
            "split": True,
            "islands": islands,
            "reason": "split_loose",
            "objects": result,
        }
    finally:
        try:
            if context.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass

        bpy.ops.object.select_all(action="DESELECT")
        for selected in previous_selection:
            if selected and selected.name in bpy.data.objects:
                selected.select_set(True)
        if previous_active and previous_active.name in bpy.data.objects:
            context.view_layer.objects.active = previous_active


def auto_prepare_objects(context, objects, max_islands=DEFAULT_MAX_LOOSE_ISLANDS):
    prepared = []
    reports = []
    for obj in list(objects):
        if obj is None or obj.name not in bpy.data.objects:
            continue
        report = split_loose_object(context, obj, max_islands=max_islands)
        reports.append({key: value for key, value in report.items() if key != "objects"})
        prepared.extend(report["objects"])

    unique = []
    seen = set()
    for obj in prepared:
        if obj is None or obj in seen or obj.name not in bpy.data.objects:
            continue
        seen.add(obj)
        unique.append(obj)

    return {
        "objects": unique,
        "reports": reports,
        "split_objects": sum(1 for report in reports if report.get("split")),
        "output_objects": len(unique),
    }
