from pathlib import Path


FOLDER_CLASS_ALIASES = {
    "sofa": "SOFA",
    "sofas": "SOFA",
    "couch": "SOFA",
    "couches": "SOFA",
    "table": "TABLE",
    "tables": "TABLE",
    "chair": "CHAIR",
    "chairs": "CHAIR",
    "bed": "BED",
    "beds": "BED",
    "cabinet": "CABINET",
    "cabinets": "CABINET",
    "wardrobe": "WARDROBE",
    "wardrobes": "WARDROBE",
    "shelf": "SHELF",
    "shelves": "SHELF",
    "bookcase": "SHELF",
    "bookcases": "SHELF",
    "kitchen_base": "KITCHEN_BASE",
    "kitchen-base": "KITCHEN_BASE",
    "base_cabinet": "KITCHEN_BASE",
    "base-cabinet": "KITCHEN_BASE",
    "kitchen_wall": "KITCHEN_WALL",
    "kitchen-wall": "KITCHEN_WALL",
    "wall_cabinet": "KITCHEN_WALL",
    "wall-cabinet": "KITCHEN_WALL",
    "door": "DOOR",
    "doors": "DOOR",
    "window": "WINDOW",
    "windows": "WINDOW",
    "stair": "STAIR",
    "stairs": "STAIR",
    "staircase": "STAIR",
    "staircases": "STAIR",
    "toilet": "TOILET",
    "toilets": "TOILET",
    "wc": "TOILET",
    "sink": "SINK",
    "sinks": "SINK",
    "basin": "SINK",
    "basins": "SINK",
    "bathtub": "BATHTUB",
    "bathtubs": "BATHTUB",
    "bath": "BATHTUB",
    "baths": "BATHTUB",
}


def normalize_folder_name(value):
    return str(value).strip().lower().replace(" ", "_")


def resolve_family_class_from_path(filepath, root_directory):
    filepath = Path(filepath)
    root = Path(root_directory)
    try:
        relative = filepath.relative_to(root)
    except ValueError:
        relative = Path(filepath.name)

    # Walk from the closest parent outward so nested category folders such as
    # furniture/sofas/model.glb still resolve to SOFA instead of FURNITURE.
    folder_parts = list(relative.parts[:-1])
    for part in reversed(folder_parts):
        family_kind = FOLDER_CLASS_ALIASES.get(normalize_folder_name(part))
        if family_kind:
            return family_kind
    return None
