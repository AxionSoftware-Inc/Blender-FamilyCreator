import math

from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_TREAD = "TREAD"
ROLE_RISER = "RISER"
ROLE_STRINGER = "STRINGER"
ROLE_HANDRAIL = "HANDRAIL"
ROLE_BALUSTER = "BALUSTER"
ROLE_LANDING = "LANDING"


def classify_role(spans, centers, name=""):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "tread", "step"):
        return ROLE_TREAD
    if name_has(name, "riser"):
        return ROLE_RISER
    if name_has(name, "stringer", "string"):
        return ROLE_STRINGER
    if name_has(name, "handrail", "rail"):
        return ROLE_HANDRAIL
    if name_has(name, "baluster", "post", "newel"):
        return ROLE_BALUSTER
    if name_has(name, "landing", "platform"):
        return ROLE_LANDING

    if sx >= 0.55 and sy <= 0.35 and sz <= 0.12:
        return ROLE_TREAD
    if sx >= 0.55 and sy <= 0.18 and sz <= 0.35:
        return ROLE_RISER
    if sx <= 0.25 and sy >= 0.55 and sz >= 0.35 and abs(cx) >= 0.55:
        return ROLE_STRINGER
    if sx >= 0.50 and sy >= 0.45 and sz <= 0.16:
        return ROLE_LANDING
    return ROLE_UNKNOWN


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    # Existing imported stair geometry is width-adjustable only. Run/rise is
    # handled by the procedural contract below instead of unsafe object scaling.
    if axis != "X":
        return "FIXED"

    role = role or ROLE_UNKNOWN
    if role in {ROLE_STRINGER, ROLE_HANDRAIL, ROLE_BALUSTER}:
        return "MOVE" if edge_member(span_ratio, center_ratio) else "FIXED"
    if role in {ROLE_TREAD, ROLE_RISER, ROLE_LANDING}:
        return "STRETCH"
    if name_has(name, "stringer", "handrail") and edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.30 else "FIXED"


def solve_parameters(
    *,
    step_count=None,
    tread_depth=None,
    riser_height=None,
    total_run=None,
    total_rise=None,
    target_riser_height=0.175,
):
    """Return a consistent straight-stair parameter set.

    `step_count` is the number of repeated tread/riser modules. Any missing
    run/rise values are derived deterministically. This pure function is kept
    Blender-independent so it can be tested and reused by the mobile BIM engine.
    """
    if step_count is None:
        if total_rise is None or total_rise <= 0:
            raise ValueError("step_count or positive total_rise is required")
        if target_riser_height <= 0:
            raise ValueError("target_riser_height must be positive")
        step_count = max(1, int(math.ceil(total_rise / target_riser_height)))

    step_count = int(step_count)
    if step_count < 1:
        raise ValueError("step_count must be at least 1")

    if riser_height is None:
        if total_rise is None or total_rise <= 0:
            raise ValueError("riser_height or positive total_rise is required")
        riser_height = float(total_rise) / step_count
    if tread_depth is None:
        if total_run is None or total_run <= 0:
            raise ValueError("tread_depth or positive total_run is required")
        tread_depth = float(total_run) / step_count

    riser_height = float(riser_height)
    tread_depth = float(tread_depth)
    if riser_height <= 0 or tread_depth <= 0:
        raise ValueError("tread_depth and riser_height must be positive")

    solved_total_rise = riser_height * step_count
    solved_total_run = tread_depth * step_count

    return {
        "step_count": step_count,
        "tread_depth": tread_depth,
        "riser_height": riser_height,
        "total_run": solved_total_run,
        "total_rise": solved_total_rise,
    }
