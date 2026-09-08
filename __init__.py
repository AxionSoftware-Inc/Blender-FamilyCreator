bl_info = {
    "name": "Axion Family Creator",
    "author": "AxionSoftware-Inc",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Family",
    "description": "Turn Blender assets into typed parameter-driven BIM family packages",
    "category": "Object",
}

import bpy

from .operators import CLASSES as OPERATOR_CLASSES
from .properties import register_properties, unregister_properties
from .ui import CLASSES as UI_CLASSES

CLASSES = OPERATOR_CLASSES + UI_CLASSES


def register():
    register_properties()
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    unregister_properties()
