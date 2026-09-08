CUSTOM_PARAMETER_SPECS = {
    "GENERIC": {},
    "SOFA": {
        "seat_height": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Seat height; 0 means auto-detect from source asset."},
        "arm_width": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Arm width; 0 means auto-detect."},
        "seat_count": {"type": "INT", "default": 0, "min": 0, "description": "Seat/cushion count; 0 means auto-detect."},
    },
    "TABLE": {
        "top_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Table-top thickness; 0 means auto-detect."},
    },
    "CHAIR": {
        "seat_height": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Seat height; 0 means auto-detect."},
    },
    "BED": {
        "mattress_height": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Mattress thickness/height; 0 means auto-detect."},
    },
    "CABINET": {
        "panel_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Carcass panel thickness; 0 means auto-detect."},
    },
    "WARDROBE": {
        "panel_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Carcass panel thickness; 0 means auto-detect."},
    },
    "SHELF": {
        "panel_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Board thickness; 0 means auto-detect."},
        "shelf_count": {"type": "INT", "default": 0, "min": 0, "description": "Shelf count; 0 means use source asset count."},
    },
    "KITCHEN_BASE": {
        "toe_kick_height": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Toe-kick height; 0 means auto-detect."},
        "panel_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Carcass panel thickness; 0 means auto-detect."},
    },
    "KITCHEN_WALL": {
        "panel_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Carcass panel thickness; 0 means auto-detect."},
    },
    "DOOR": {
        "frame_width": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Visible frame/jamb width; 0 means auto-detect."},
        "panel_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Door-leaf thickness; 0 means source thickness."},
    },
    "WINDOW": {
        "frame_width": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Frame profile width; 0 means auto-detect."},
        "sill_height": {"type": "LENGTH", "default": 0.9, "min": 0.0, "description": "Placement sill height for BIM hosting."},
    },
    "STAIR": {
        "total_run": {"type": "LENGTH", "default_axis": "Y", "min": 0.001, "description": "Horizontal run of the procedural stair."},
        "total_rise": {"type": "LENGTH", "default_axis": "Z", "min": 0.001, "description": "Vertical rise of the procedural stair."},
        "tread_depth": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Tread depth; 0 derives it from total run and step count."},
        "riser_height": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Riser height; 0 derives it from total rise and step count."},
        "step_count": {"type": "INT", "default": 0, "min": 0, "description": "Repeated stair modules; 0 auto-calculates from total rise."},
    },
    "TOILET": {
        "connector_height": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Primary plumbing connector height."},
    },
    "SINK": {
        "drain_diameter": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Drain connector diameter; 0 means unspecified."},
    },
    "BATHTUB": {
        "rim_thickness": {"type": "LENGTH", "default": 0.0, "min": 0.0, "description": "Tub rim thickness; 0 means auto-detect."},
    },
}


def get_parameter_specs(type_id):
    return CUSTOM_PARAMETER_SPECS.get(type_id, {})


def property_name(parameter_name):
    return f"bfc_sem_{parameter_name}"
