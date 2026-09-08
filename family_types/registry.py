FAMILY_TYPES = {
    "GENERIC": {
        "label": "Generic Model",
        "group": "Generic",
        "category": "Generic Model",
        "description": "Fallback profile when no dedicated family logic exists.",
        "editable_axes": ("X", "Y", "Z"),
        "strategy": "GENERIC",
        "parameters": ("width", "depth", "height"),
    },
    "SOFA": {
        "label": "Sofa",
        "group": "Furniture",
        "category": "Furniture",
        "description": "Width-driven upholstered seating. Arms move, center upholstery stretches.",
        "editable_axes": ("X",),
        "strategy": "SOFA",
        "parameters": ("width", "depth", "height", "seat_height", "arm_width", "seat_count"),
    },
    "TABLE": {
        "label": "Table",
        "group": "Furniture",
        "category": "Furniture",
        "description": "Table top stretches in plan; legs preserve section and move to corners.",
        "editable_axes": ("X", "Y", "Z"),
        "strategy": "TABLE",
        "parameters": ("width", "depth", "height", "top_thickness"),
    },
    "CHAIR": {
        "label": "Chair",
        "group": "Furniture",
        "category": "Furniture",
        "description": "Seat/back can resize while legs and frame members preserve thickness.",
        "editable_axes": ("X", "Y", "Z"),
        "strategy": "CHAIR",
        "parameters": ("width", "depth", "height", "seat_height"),
    },
    "BED": {
        "label": "Bed",
        "group": "Furniture",
        "category": "Furniture",
        "description": "Mattress/body changes width and length while head/foot details anchor to ends.",
        "editable_axes": ("X", "Y"),
        "strategy": "BED",
        "parameters": ("width", "length", "height", "mattress_height"),
    },
    "CABINET": {
        "label": "Cabinet",
        "group": "Casework",
        "category": "Casework",
        "description": "Casework profile with fixed panel thickness and movable edge panels.",
        "editable_axes": ("X", "Y", "Z"),
        "strategy": "CASEWORK",
        "parameters": ("width", "depth", "height", "panel_thickness"),
    },
    "WARDROBE": {
        "label": "Wardrobe",
        "group": "Casework",
        "category": "Casework",
        "description": "Tall casework with width/height driven carcass logic.",
        "editable_axes": ("X", "Y", "Z"),
        "strategy": "CASEWORK",
        "parameters": ("width", "depth", "height", "panel_thickness"),
    },
    "SHELF": {
        "label": "Shelf / Bookcase",
        "group": "Casework",
        "category": "Casework",
        "description": "Shelving with fixed board thickness and scalable overall envelope.",
        "editable_axes": ("X", "Y", "Z"),
        "strategy": "CASEWORK",
        "parameters": ("width", "depth", "height", "panel_thickness", "shelf_count"),
    },
    "KITCHEN_BASE": {
        "label": "Kitchen Base Cabinet",
        "group": "Casework",
        "category": "Casework",
        "description": "Base cabinet with strong width logic and mostly standardized depth/height.",
        "editable_axes": ("X",),
        "strategy": "CASEWORK",
        "parameters": ("width", "depth", "height", "toe_kick_height", "panel_thickness"),
    },
    "KITCHEN_WALL": {
        "label": "Kitchen Wall Cabinet",
        "group": "Casework",
        "category": "Casework",
        "description": "Wall cabinet with width/height driven carcass logic.",
        "editable_axes": ("X", "Z"),
        "strategy": "CASEWORK",
        "parameters": ("width", "depth", "height", "panel_thickness"),
    },
    "DOOR": {
        "label": "Door",
        "group": "Openings",
        "category": "Doors",
        "description": "Opening family: width and height vary, frame depth/thickness stay controlled.",
        "editable_axes": ("X", "Z"),
        "strategy": "OPENING",
        "parameters": ("width", "height", "frame_depth", "frame_width", "panel_thickness"),
    },
    "WINDOW": {
        "label": "Window",
        "group": "Openings",
        "category": "Windows",
        "description": "Opening family: frame edge pieces move while central glazing stretches.",
        "editable_axes": ("X", "Z"),
        "strategy": "OPENING",
        "parameters": ("width", "height", "frame_depth", "frame_width", "sill_height"),
    },
    "STAIR": {
        "label": "Stair",
        "group": "Circulation",
        "category": "Stairs",
        "description": "Discrete stair profile. Width can resize now; run/rise/step generation is type-specific.",
        "editable_axes": ("X",),
        "strategy": "STAIR",
        "parameters": ("width", "total_run", "total_rise", "tread_depth", "riser_height", "step_count"),
    },
    "TOILET": {
        "label": "Toilet",
        "group": "Plumbing",
        "category": "Plumbing Fixtures",
        "description": "Sanitary fixture with mostly fixed proportions and connection metadata.",
        "editable_axes": (),
        "strategy": "FIXED_FIXTURE",
        "parameters": ("width", "depth", "height", "connector_height"),
    },
    "SINK": {
        "label": "Sink / Basin",
        "group": "Plumbing",
        "category": "Plumbing Fixtures",
        "description": "Basin can vary in plan while bowl/drain details stay protected.",
        "editable_axes": ("X", "Y"),
        "strategy": "BASIN",
        "parameters": ("width", "depth", "height", "drain_diameter"),
    },
    "BATHTUB": {
        "label": "Bathtub",
        "group": "Plumbing",
        "category": "Plumbing Fixtures",
        "description": "Tub length/width profile with protected rim and drain details.",
        "editable_axes": ("X", "Y"),
        "strategy": "BASIN",
        "parameters": ("width", "length", "height", "rim_thickness"),
    },
}


AXIS_PARAMETERS = {
    "GENERIC": {"X": "width", "Y": "depth", "Z": "height"},
    "SOFA": {"X": "width", "Y": "depth", "Z": "height"},
    "TABLE": {"X": "width", "Y": "depth", "Z": "height"},
    "CHAIR": {"X": "width", "Y": "depth", "Z": "height"},
    "BED": {"X": "width", "Y": "length", "Z": "height"},
    "CABINET": {"X": "width", "Y": "depth", "Z": "height"},
    "WARDROBE": {"X": "width", "Y": "depth", "Z": "height"},
    "SHELF": {"X": "width", "Y": "depth", "Z": "height"},
    "KITCHEN_BASE": {"X": "width", "Y": "depth", "Z": "height"},
    "KITCHEN_WALL": {"X": "width", "Y": "depth", "Z": "height"},
    "DOOR": {"X": "width", "Y": "frame_depth", "Z": "height"},
    "WINDOW": {"X": "width", "Y": "frame_depth", "Z": "height"},
    "STAIR": {"X": "width", "Y": "total_run", "Z": "total_rise"},
    "TOILET": {"X": "width", "Y": "depth", "Z": "height"},
    "SINK": {"X": "width", "Y": "depth", "Z": "height"},
    "BATHTUB": {"X": "width", "Y": "length", "Z": "height"},
}


AXIS_ANCHORS = {
    "GENERIC": {"X": "CENTER", "Y": "CENTER", "Z": "CENTER"},
    "SOFA": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "TABLE": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "CHAIR": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "BED": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "CABINET": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "WARDROBE": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "SHELF": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "KITCHEN_BASE": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "KITCHEN_WALL": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "DOOR": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "WINDOW": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "STAIR": {"X": "CENTER", "Y": "MIN", "Z": "MIN"},
    "TOILET": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "SINK": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
    "BATHTUB": {"X": "CENTER", "Y": "CENTER", "Z": "MIN"},
}


for _type_id, _spec in FAMILY_TYPES.items():
    _spec["logic_module"] = f"family_types.{_type_id.lower()}"
    _spec["axis_parameters"] = AXIS_PARAMETERS[_type_id]
    _spec["axis_anchors"] = AXIS_ANCHORS[_type_id]


def get_family_type(type_id):
    return FAMILY_TYPES.get(type_id, FAMILY_TYPES["GENERIC"])


def family_type_items(_self=None, _context=None):
    items = []
    for type_id, spec in FAMILY_TYPES.items():
        label = f"{spec['group']} · {spec['label']}"
        items.append((type_id, label, spec["description"]))
    return items
