"""One-click, owner-scoped Arm/Leg IK controls for humanoid deform skeletons.

The module deliberately keeps analysis read-only (WindowManager state only) and
keeps generated controls inside the source Armature.  Constraint ownership is
recorded on PoseBones because Blender constraints do not support ID properties.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass

import bpy
from bpy.props import EnumProperty, FloatProperty, FloatVectorProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Matrix, Vector

from .ui_constants import SIDEBAR_CATEGORY, UI_PAGE_RIG, active_ui_page


OWNER_KEY = "character_designer_owner"
OWNER_VALUE = "limb_ik"
VERSION_KEY = "character_designer_limb_ik_version"
RIG_ID_KEY = "character_designer_limb_ik_rig_id"
ROLE_KEY = "character_designer_limb_ik_role"
KIND_KEY = "character_designer_limb_ik_kind"
SIDE_KEY = "character_designer_limb_ik_side"
CHAIN_KEY = "character_designer_limb_ik_chain"
ARMATURE_ID_KEY = "character_designer_limb_ik_armature_id"
CONSTRAINT_REGISTRY_KEY = "character_designer_limb_ik_constraints"
SCHEMA_KEY = "character_designer_limb_ik_schema"
POLE_DIRECTION_KEY = "character_designer_limb_ik_pole_direction"
RIG_VERSION = 1
LEGACY_SCHEMA = 1
ENHANCED_SCHEMA = 2
CONTROL_COLLECTION_NAME = "Randy Controls"
WIDGET_COLLECTION_NAME = "Randy_Rig_Widgets"
MASTER_NAME = "CTRL_master"
EPSILON = 1.0e-8
POLE_DIRECTION_PARALLEL_RATIO = 1.0e-4
POLE_MIN_REACH_DEFICIT_RATIO = 1.0e-6

SIDES = ("L", "R")
KINDS = ("ARM", "LEG")
ROLES = ("upper", "lower", "end")
SELECTED_LIMBS = {
    "LEFT_ARM": ("ARM", "L"),
    "RIGHT_ARM": ("ARM", "R"),
    "LEFT_LEG": ("LEG", "L"),
    "RIGHT_LEG": ("LEG", "R"),
}
DEFAULT_POLE_DIRECTIONS = {
    ("ARM", "L"): (0.0, -1.0, 0.0),
    ("ARM", "R"): (0.0, -1.0, 0.0),
    ("LEG", "L"): (0.0, 1.0, 0.0),
    ("LEG", "R"): (0.0, 1.0, 0.0),
}

LIMB_SPEC = {
    "ARM": {
        "upper": (("upperarm", 8), ("arm", 5)),
        "lower": (("forearm", 8), ("lowerarm", 8)),
        "end": (("hand", 8), ("wrist", 7)),
        "target": "CTRL_hand_IK.{side}",
        "pole": "CTRL_elbow_pole.{side}",
        "line": "VIS_elbow_pole_line.{side}",
        "display": "MCH_elbow_pole_aim.{side}",
        "target_role": "HAND_IK",
    },
    "LEG": {
        "upper": (("thigh", 8), ("upperleg", 8)),
        "lower": (("shin", 8), ("calf", 8), ("lowerleg", 8)),
        "end": (("foot", 8), ("ankle", 7)),
        "target": "CTRL_foot_IK.{side}",
        "pole": "CTRL_knee_pole.{side}",
        "line": "VIS_knee_pole_line.{side}",
        "display": "MCH_knee_pole_aim.{side}",
        "heel": "CTRL_heel_roll.{side}",
        "solver_target": "MCH_foot_target.{side}",
        "target_role": "FOOT_IK",
    },
}

_EXCLUDED_TOKENS = frozenset(
    {"mch", "org", "ctrl", "vis", "wgt", "ik", "fk", "twist", "helper", "corrective", "tweak"}
)


class LimbIKError(ValueError):
    """An actionable, fail-closed limb-rig problem."""


@dataclass(frozen=True)
class LimbChain:
    kind: str
    side: str
    upper: str
    lower: str
    end: str
    score: float = 0.0
    warning: str = ""

    @property
    def names(self):
        return (self.upper, self.lower, self.end)


@dataclass
class LimbPlan:
    chain: LimbChain
    rig_id: str
    target_name: str
    pole_name: str
    start: Vector
    joint: Vector
    end: Vector
    target_head: Vector
    target_tail: Vector
    target_z: Vector
    pole_head: Vector
    pole_tail: Vector
    pole_angle: float
    pole_warning: str
    pole_direction: Vector
    pole_joint: Vector
    desired_upper_matrix: Matrix
    desired_lower_matrix: Matrix
    desired_end_matrix: Matrix
    target_basis: Matrix
    pole_basis: Matrix
    line_name: str = ""
    display_name: str = ""
    heel_name: str = ""
    solver_target_name: str = ""
    heel_head: Vector | None = None
    heel_tail: Vector | None = None
    heel_z: Vector | None = None
    persist_pole_direction: bool = True
    preserve_pole_angle: bool = False


def _armature_poll(_self, obj):
    return obj is not None and obj.type == "ARMATURE"


def _settings(context):
    return getattr(getattr(context, "window_manager", None), "character_designer_limb_ik", None)


def _set_status(settings, level, message):
    if settings is not None:
        settings.last_level = level
        settings.last_message = message


def _field_name(kind, side, role):
    return f"{'left' if side == 'L' else 'right'}_{kind.lower()}_{role}"


def _pole_direction_field(kind, side):
    return f"{'left' if side == 'L' else 'right'}_{kind.lower()}_pole_direction"


def _finite_direction(value, label="Pole Direction"):
    try:
        components = tuple(float(component) for component in value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise LimbIKError(f"{label} must contain three finite Armature-local XYZ values.") from exc
    if len(components) != 3 or any(not math.isfinite(component) for component in components):
        raise LimbIKError(f"{label} must contain three finite Armature-local XYZ values.")
    direction = Vector(components)
    if direction.length <= EPSILON:
        raise LimbIKError(f"{label} cannot be zero; choose an Armature-local direction.")
    return direction


def _configured_pole_direction(settings, kind, side):
    label = f"{side} {kind.title()} Pole Direction"
    return _finite_direction(getattr(settings, _pole_direction_field(kind, side)), label)


def _rest_pole_direction(armature, kind, side, chain_names=()):
    """Return the modeled rest bend, with a fixed anatomical fallback.

    A clear joint residual relative to the upper-head/lower-tail chord preserves
    the artist's authored bend plane, including its lateral component.  This is
    important on legs whose knees are not centered on a pure local Y plane.
    """
    fallback = Vector(DEFAULT_POLE_DIRECTIONS[(kind, side)])
    if armature is None or getattr(armature, "type", None) != "ARMATURE" or len(chain_names) < 2:
        return fallback, False
    upper = armature.data.bones.get(chain_names[0])
    lower = armature.data.bones.get(chain_names[1])
    if upper is None or lower is None:
        return fallback, False
    start = Vector(upper.head_local)
    joint = Vector(lower.head_local)
    end = Vector(lower.tail_local)
    total = (joint - start).length + (end - joint).length
    residual = _project_perpendicular(joint - start, end - start)
    if total <= EPSILON or residual.length <= max(EPSILON, total * POLE_DIRECTION_PARALLEL_RATIO):
        return fallback, False
    residual.normalize()
    return residual, True


def _hydrate_pole_directions(settings, armature, payload):
    """Load saved generated directions, modeled rest bends, or fallbacks.

    The WindowManager values deliberately remain an edit buffer.  Analyze calls
    this only when its Armature changes, so re-analysis never overwrites XYZ
    values the artist is currently tuning.
    """
    for kind in KINDS:
        for side in SIDES:
            result = payload["limbs"][kind][side]
            chain_names = tuple(result.get(role, "") for role in ROLES)
            value, _used_modeled_bend = _rest_pole_direction(armature, kind, side, chain_names)
            pole_name = LIMB_SPEC[kind]["pole"].format(side=side)
            pole = armature.data.bones.get(pole_name)
            if (
                pole is not None
                and pole.get(OWNER_KEY) == OWNER_VALUE
                and pole.get(KIND_KEY) == kind
                and pole.get(SIDE_KEY) == side
                and POLE_DIRECTION_KEY in pole
            ):
                try:
                    saved = _finite_direction(pole[POLE_DIRECTION_KEY], f"Saved {side} {kind.title()} Pole Direction")
                    saved.normalize()
                    value = saved
                except LimbIKError:
                    # Strict inventory validation will report malformed owned
                    # metadata before any Build/Rebuild mutation.  Analyze stays
                    # useful and read-only by presenting a repairable default.
                    pass
            setattr(settings, _pole_direction_field(kind, side), tuple(value))


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _armature_digest(armature):
    payload = []
    for bone in sorted(armature.data.bones, key=lambda item: item.name):
        if bone.get(OWNER_KEY) == OWNER_VALUE:
            continue
        payload.append(
            (
                bone.name,
                bone.parent.name if bone.parent else "",
                tuple(round(value, 7) for value in bone.head_local),
                tuple(round(value, 7) for value in bone.tail_local),
                tuple(round(float(value), 7) for row in bone.matrix_local for value in row),
                bool(bone.use_deform),
                bool(bone.use_connect),
            )
        )
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _side_from_name(name):
    match = re.search(r"(?:^|[._\-\s])(left|right|l|r)$", name, re.IGNORECASE)
    if match:
        return "L" if match.group(1).lower() in {"left", "l"} else "R"
    if re.match(r"^left(?=[A-Z_.\-\s]|$)", name, re.IGNORECASE):
        return "L"
    if re.match(r"^right(?=[A-Z_.\-\s]|$)", name, re.IGNORECASE):
        return "R"
    return ""


def _name_parts(name):
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    tokens = tuple(token for token in re.split(r"[^a-z0-9]+", expanded.lower()) if token)
    base = "".join(token for token in tokens if token not in {"l", "r", "left", "right", "def"})
    return tokens, base


def _name_score(name, kind, role):
    tokens, base = _name_parts(name)
    if _EXCLUDED_TOKENS.intersection(tokens):
        return -1
    if any(marker in base for marker in ("twist", "helper", "corrective", "tweak")):
        return -1
    for keyword, score in LIMB_SPEC[kind][role]:
        if base == keyword:
            return score
        if base.startswith("def" + keyword) or base.endswith(keyword):
            return score - 1
    return -1


def _candidate_chains(armature, kind, side):
    candidates = []
    source_bones = [bone for bone in armature.data.bones if bone.get(OWNER_KEY) != OWNER_VALUE]
    center_x = sum(float(bone.head_local.x) for bone in source_bones) / max(1, len(source_bones))
    extent_x = max((abs(float(bone.head_local.x) - center_x) for bone in source_bones), default=1.0)
    for upper in armature.data.bones:
        upper_score = _name_score(upper.name, kind, "upper")
        if upper_score < 0 or upper.get(OWNER_KEY) == OWNER_VALUE or not upper.use_deform:
            continue
        for lower in upper.children:
            lower_score = _name_score(lower.name, kind, "lower")
            if lower_score < 0 or not lower.use_deform:
                continue
            for end in lower.children:
                end_score = _name_score(end.name, kind, "end")
                if end_score < 0 or not end.use_deform:
                    continue
                explicit = tuple(filter(None, (_side_from_name(b.name) for b in (upper, lower, end))))
                midpoint_x = sum(float(bone.head_local.x) for bone in (upper, lower, end)) / 3.0
                inferred_side = "L" if midpoint_x > center_x else "R"
                if explicit and any(item != side for item in explicit):
                    continue
                if not explicit and (abs(midpoint_x - center_x) < max(extent_x * 0.08, 1.0e-5) or inferred_side != side):
                    continue
                a = Vector(upper.head_local)
                b = Vector(lower.head_local)
                c = Vector(end.head_local)
                tolerance = max(upper.length, lower.length, end.length, 1.0) * 1.0e-4
                if (Vector(upper.tail_local) - b).length > tolerance or (Vector(lower.tail_local) - c).length > tolerance:
                    continue
                upper_len = (b - a).length
                lower_len = (c - b).length
                if min(upper_len, lower_len) <= EPSILON:
                    continue
                ratio = upper_len / lower_len
                if not 0.2 <= ratio <= 5.0:
                    continue
                delta = c - a
                geometry = 0.0
                if kind == "ARM" and math.hypot(delta.x, delta.y) >= abs(delta.z) * 0.45:
                    geometry += 1.0
                if kind == "LEG" and abs(delta.z) >= math.hypot(delta.x, delta.y) * 1.25:
                    geometry += 1.0
                if all(item == side for item in explicit) and len(explicit) == 3:
                    geometry += 1.0
                elif not explicit:
                    geometry += 0.25
                if end.length <= lower.length * 1.5:
                    geometry += 0.5
                candidates.append(
                    LimbChain(kind, side, upper.name, lower.name, end.name, upper_score + lower_score + end_score + geometry)
                )
    return sorted(candidates, key=lambda item: (-item.score, item.names))


def analyze_armature(armature):
    """Return a deterministic analysis without mutating the Armature datablock."""
    if armature is None or armature.type != "ARMATURE":
        raise LimbIKError("Make one Armature active before Analyze Rig.")
    scaffold_count = sum(bone.name.lower().startswith(("mch-", "org-", "ctrl-", "vis_")) for bone in armature.data.bones)
    if armature.get("rig_id") or armature.data.get("rig_id") or scaffold_count >= 12:
        raise LimbIKError("This looks like a generated control rig, not a clean humanoid Deform Skeleton; analyze the source/metarig instead.")
    results = {kind: {} for kind in KINDS}
    warnings = []
    for kind in KINDS:
        for side in SIDES:
            candidates = _candidate_chains(armature, kind, side)
            if not candidates:
                results[kind][side] = {"status": "MISSING", "warning": "No high-confidence direct chain was found."}
                warnings.append(f"{side} {kind.title()}: not identified")
                continue
            top = candidates[0]
            if top.score < 22.0:
                results[kind][side] = {"status": "LOW_CONFIDENCE", "warning": "Name, hierarchy, and position evidence did not reach the safe threshold."}
                warnings.append(f"{side} {kind.title()}: low confidence")
                continue
            if len(candidates) > 1 and top.score - candidates[1].score < 2.0:
                results[kind][side] = {"status": "AMBIGUOUS", "warning": "Two direct chains scored too closely; choose bones manually."}
                warnings.append(f"{side} {kind.title()}: ambiguous")
                continue
            results[kind][side] = {
                "status": "READY",
                "upper": top.upper,
                "lower": top.lower,
                "end": top.end,
                "score": top.score,
                "warning": "",
            }
    return {
        "version": RIG_VERSION,
        "armature": armature.name,
        "armature_data": armature.data.name,
        "digest": _armature_digest(armature),
        "limbs": results,
        "warnings": warnings,
    }


class CharacterDesignerLimbIKState(PropertyGroup):
    armature: PointerProperty(name="Armature", type=bpy.types.Object, poll=_armature_poll, options={"SKIP_SAVE"})
    analysis_json: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    pole_direction_armature_token: StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    pole_distance_ratio: FloatProperty(name="Pole Distance", default=0.75, min=0.25, max=2.0, subtype="FACTOR", options={"SKIP_SAVE"})
    selected_limb: EnumProperty(
        name="Limb",
        items=(
            ("LEFT_ARM", "Left Arm", "Edit the detected left arm chain"),
            ("RIGHT_ARM", "Right Arm", "Edit the detected right arm chain"),
            ("LEFT_LEG", "Left Leg", "Edit the detected left leg chain"),
            ("RIGHT_LEG", "Right Leg", "Edit the detected right leg chain"),
        ),
        default="LEFT_ARM",
        options={"SKIP_SAVE"},
    )
    left_arm_pole_direction: FloatVectorProperty(
        name="Left Arm Pole Direction",
        description="Armature-local direction from the elbow toward its Pole control",
        size=3,
        subtype="XYZ",
        default=DEFAULT_POLE_DIRECTIONS[("ARM", "L")],
        options={"SKIP_SAVE"},
    )
    right_arm_pole_direction: FloatVectorProperty(
        name="Right Arm Pole Direction",
        description="Armature-local direction from the elbow toward its Pole control",
        size=3,
        subtype="XYZ",
        default=DEFAULT_POLE_DIRECTIONS[("ARM", "R")],
        options={"SKIP_SAVE"},
    )
    left_leg_pole_direction: FloatVectorProperty(
        name="Left Leg Pole Direction",
        description="Armature-local direction from the knee toward its Pole control",
        size=3,
        subtype="XYZ",
        default=DEFAULT_POLE_DIRECTIONS[("LEG", "L")],
        options={"SKIP_SAVE"},
    )
    right_leg_pole_direction: FloatVectorProperty(
        name="Right Leg Pole Direction",
        description="Armature-local direction from the knee toward its Pole control",
        size=3,
        subtype="XYZ",
        default=DEFAULT_POLE_DIRECTIONS[("LEG", "R")],
        options={"SKIP_SAVE"},
    )
    left_arm_upper: StringProperty(options={"SKIP_SAVE"})
    left_arm_lower: StringProperty(options={"SKIP_SAVE"})
    left_arm_end: StringProperty(options={"SKIP_SAVE"})
    right_arm_upper: StringProperty(options={"SKIP_SAVE"})
    right_arm_lower: StringProperty(options={"SKIP_SAVE"})
    right_arm_end: StringProperty(options={"SKIP_SAVE"})
    left_leg_upper: StringProperty(options={"SKIP_SAVE"})
    left_leg_lower: StringProperty(options={"SKIP_SAVE"})
    left_leg_end: StringProperty(options={"SKIP_SAVE"})
    right_leg_upper: StringProperty(options={"SKIP_SAVE"})
    right_leg_lower: StringProperty(options={"SKIP_SAVE"})
    right_leg_end: StringProperty(options={"SKIP_SAVE"})
    last_level: EnumProperty(items=(("NONE", "None", ""), ("INFO", "Info", ""), ("SUCCESS", "Success", ""), ("WARNING", "Warning", ""), ("ERROR", "Error", "")), default="NONE", options={"SKIP_SAVE"})
    last_message: StringProperty(default="", options={"SKIP_SAVE"})


class CHARACTERDESIGNER_OT_limb_ik_analyze(Operator):
    bl_idname = "character_designer.limb_ik_analyze"
    bl_label = "Analyze Rig"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "ARMATURE" and context.mode in {"OBJECT", "POSE"}

    def execute(self, context):
        settings = _settings(context)
        try:
            armature = context.object
            payload = analyze_armature(armature)
            armature_token = str(armature.data.as_pointer())
            armature_changed = settings.armature is not armature or settings.pole_direction_armature_token != armature_token
            if armature_changed:
                _hydrate_pole_directions(settings, armature, payload)
                settings.pole_direction_armature_token = armature_token
            settings.armature = armature
            settings.analysis_json = _canonical_json(payload)
            for kind in KINDS:
                for side in SIDES:
                    result = payload["limbs"][kind][side]
                    for role in ROLES:
                        setattr(settings, _field_name(kind, side, role), result.get(role, ""))
            statuses = [payload["limbs"][kind][side]["status"] for kind in KINDS for side in SIDES]
            ready = sum(status in {"READY", "WARNING"} for status in statuses)
            incomplete = any(status not in {"READY", "WARNING"} for status in statuses)
            message = f"Analyze Rig found {ready}/4 high-confidence limbs."
            if incomplete:
                message += " Low-confidence sides were left blank."
            level = "WARNING" if incomplete else "SUCCESS"
            _set_status(settings, level, message)
            self.report({"WARNING" if level == "WARNING" else "INFO"}, message)
            return {"FINISHED"}
        except (LimbIKError, ReferenceError, RuntimeError, TypeError, ValueError) as exc:
            _set_status(settings, "WARNING", str(exc))
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}


# Build/remove helpers and operators are intentionally below the analysis API so
# tests and future UI variants can use the detector independently.


def _require_active_armature(context, settings, *, analyzed=True):
    armature = context.object
    if armature is None or armature.type != "ARMATURE":
        raise LimbIKError("Make the intended Armature active first.")
    if settings is None:
        raise LimbIKError("Limb IK state is unavailable; reload Character Designer.")
    if analyzed and settings.armature is not armature:
        raise LimbIKError("The active Armature is not the analyzed Armature; run Analyze Rig again.")
    if armature.library is not None or armature.data.library is not None:
        raise LimbIKError("Linked Armatures are read-only; make a local copy before building Limb IK.")
    if armature.override_library is not None or armature.data.override_library is not None:
        raise LimbIKError("Library overrides are not modified by Limb IK; use a local Armature.")
    if armature.data.users != 1:
        raise LimbIKError("The active Armature Data is shared; make it single-user before building Limb IK.")
    memberships = [scene for scene in bpy.data.scenes if scene.objects.get(armature.name) is armature]
    if len(memberships) != 1 or memberships[0] is not context.scene:
        raise LimbIKError("The active Armature must belong only to the current Scene.")
    if context.view_layer.objects.get(armature.name) is not armature:
        raise LimbIKError("The active Armature is excluded from the current View Layer.")
    if abs(armature.matrix_world.to_3x3().determinant()) <= EPSILON:
        raise LimbIKError("The Armature transform is singular; apply a usable non-zero scale first.")
    if analyzed:
        try:
            payload = json.loads(settings.analysis_json)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LimbIKError("Analyze Rig data is missing or corrupt; run Analyze Rig again.") from exc
        if not isinstance(payload, dict) or payload.get("version") != RIG_VERSION:
            raise LimbIKError("Analyze Rig data is stale; run Analyze Rig again.")
        if payload.get("digest") != _armature_digest(armature):
            raise LimbIKError("Bone names, hierarchy, or rest pose changed; run Analyze Rig again.")
    return armature


def _chain_from_settings(settings, armature, kind, side):
    names = tuple(getattr(settings, _field_name(kind, side, role), "") for role in ROLES)
    if not any(names):
        return None
    if not all(names):
        raise LimbIKError(f"{side} {kind.title()} has an incomplete manual bone selection.")
    if len(set(names)) != 3:
        raise LimbIKError(f"{side} {kind.title()} must use three different bones.")
    bones = tuple(armature.data.bones.get(name) for name in names)
    if any(bone is None for bone in bones):
        raise LimbIKError(f"{side} {kind.title()} refers to a bone that no longer exists.")
    upper, lower, end = bones
    if lower.parent is None or lower.parent.name != upper.name or end.parent is None or end.parent.name != lower.name:
        raise LimbIKError(f"{side} {kind.title()} must be one direct upper → lower → end hierarchy.")
    if min((Vector(lower.head_local) - Vector(upper.head_local)).length, (Vector(end.head_local) - Vector(lower.head_local)).length) <= EPSILON:
        raise LimbIKError(f"{side} {kind.title()} contains a zero-length IK segment.")
    scale = max(upper.length, lower.length, end.length, 1.0)
    tolerance = max(scale * 1.0e-4, 1.0e-6)
    if (Vector(upper.tail_local) - Vector(lower.head_local)).length > tolerance or (Vector(lower.tail_local) - Vector(end.head_local)).length > tolerance:
        raise LimbIKError(f"{side} {kind.title()} joints are spatially disconnected.")
    if not all(bone.use_deform for bone in bones):
        raise LimbIKError(f"{side} {kind.title()} includes a non-Deform/scaffold bone.")
    if any(_EXCLUDED_TOKENS.intersection(_name_parts(bone.name)[0]) for bone in bones):
        raise LimbIKError(f"{side} {kind.title()} includes a helper, mechanism, or existing control bone.")
    explicit = tuple(filter(None, (_side_from_name(name) for name in names)))
    if explicit and any(value != side for value in explicit):
        raise LimbIKError(f"{side} {kind.title()} contains an explicit opposite-side bone name.")
    if any(bone.get(OWNER_KEY) == OWNER_VALUE for bone in bones):
        raise LimbIKError(f"{side} {kind.title()} cannot use generated control bones as deform inputs.")
    return LimbChain(kind, side, *names)


def _capture_context(context, armature):
    mode = context.mode
    if mode not in {"OBJECT", "POSE", "EDIT_ARMATURE"}:
        raise LimbIKError("Use Limb IK from Armature Object, Pose, or Edit Mode.")
    snapshot = {
        "mode": mode,
        "active": context.view_layer.objects.active,
        "selected": tuple(obj for obj in context.selected_objects),
        "bone_selection": {},
        "active_bone": "",
    }
    if mode == "EDIT_ARMATURE":
        snapshot["bone_selection"] = {
            bone.name: (bool(bone.select), bool(bone.select_head), bool(bone.select_tail))
            for bone in armature.data.edit_bones
        }
        active = armature.data.edit_bones.active
    else:
        snapshot["bone_selection"] = {bone.name: bool(bone.select) for bone in armature.pose.bones}
        active = armature.data.bones.active
    snapshot["active_bone"] = active.name if active else ""
    return snapshot


def _mode_set(context, armature, mode):
    active = context.view_layer.objects.active
    if context.mode != "OBJECT":
        if bpy.ops.object.mode_set(mode="OBJECT") != {"FINISHED"}:
            raise LimbIKError("Blender could not enter Object Mode for Limb IK.")
    for obj in context.view_layer.objects:
        obj.select_set(False)
    armature.select_set(True)
    context.view_layer.objects.active = armature
    if mode != "OBJECT" and bpy.ops.object.mode_set(mode=mode) != {"FINISHED"}:
        context.view_layer.objects.active = active
        raise LimbIKError(f"Blender could not enter {mode.title()} Mode for Limb IK.")


def _restore_context(context, armature, snapshot):
    if context.mode != "OBJECT" and bpy.ops.object.mode_set(mode="OBJECT") != {"FINISHED"}:
        raise LimbIKError("Blender could not restore Object Mode.")
    for obj in context.view_layer.objects:
        obj.select_set(False)
    selected = [obj for obj in snapshot["selected"] if bpy.data.objects.get(obj.name) is obj and context.view_layer.objects.get(obj.name) is obj]
    for obj in selected:
        obj.select_set(True)
    active = snapshot["active"]
    if active is not None and bpy.data.objects.get(active.name) is active and context.view_layer.objects.get(active.name) is active:
        context.view_layer.objects.active = active
    else:
        context.view_layer.objects.active = armature
        armature.select_set(True)
    original_mode = snapshot["mode"]
    if original_mode == "EDIT_ARMATURE":
        if context.view_layer.objects.active is not armature:
            raise LimbIKError("The original Edit Armature is no longer active.")
        if bpy.ops.object.mode_set(mode="EDIT") != {"FINISHED"}:
            raise LimbIKError("Blender could not restore Armature Edit Mode.")
        for bone in armature.data.edit_bones:
            values = snapshot["bone_selection"].get(bone.name, (False, False, False))
            bone.select, bone.select_head, bone.select_tail = values
        armature.data.edit_bones.active = armature.data.edit_bones.get(snapshot["active_bone"])
    elif original_mode == "POSE":
        if context.view_layer.objects.active is not armature:
            raise LimbIKError("The original Pose Armature is no longer active.")
        if bpy.ops.object.mode_set(mode="POSE") != {"FINISHED"}:
            raise LimbIKError("Blender could not restore Pose Mode.")
        for bone in armature.pose.bones:
            bone.select = snapshot["bone_selection"].get(bone.name, False)
        armature.data.bones.active = armature.data.bones.get(snapshot["active_bone"])
    elif original_mode == "OBJECT":
        for bone in armature.pose.bones:
            bone.select = snapshot["bone_selection"].get(bone.name, False)
        armature.data.bones.active = armature.data.bones.get(snapshot["active_bone"])


def _project_perpendicular(vector, axis):
    axis = Vector(axis)
    if axis.length <= EPSILON:
        return Vector()
    axis.normalize()
    return Vector(vector) - axis * Vector(vector).dot(axis)


def _signed_angle(reference, target, axis):
    reference = _project_perpendicular(reference, axis)
    target = _project_perpendicular(target, axis)
    if reference.length <= EPSILON or target.length <= EPSILON:
        raise LimbIKError("Pole Angle could not be derived from the source bone roll.")
    reference.normalize()
    target.normalize()
    axis = Vector(axis).normalized()
    return math.atan2(axis.dot(reference.cross(target)), max(-1.0, min(1.0, reference.dot(target))))


def _joint_on_direction_plane(start, joint, end, direction):
    start = Vector(start)
    joint = Vector(joint)
    end = Vector(end)
    chain = end - start
    distance = chain.length
    if distance <= EPSILON:
        raise LimbIKError("The limb root and IK endpoint occupy the same position.")
    upper_length = (joint - start).length
    lower_length = (end - joint).length
    along = (upper_length * upper_length - lower_length * lower_length + distance * distance) / (2.0 * distance)
    height_squared = upper_length * upper_length - along * along
    tolerance = max(upper_length * upper_length, lower_length * lower_length, 1.0) * 1.0e-7
    if height_squared < -tolerance:
        raise LimbIKError("The current limb lengths cannot form a reachable two-bone Pole plane.")
    height = math.sqrt(max(0.0, height_squared))
    return start + chain.normalized() * along + Vector(direction) * height


def _pole_solution(start, joint, end, upper_x, pole_direction, distance_ratio):
    chain_axis = Vector(end) - Vector(start)
    if chain_axis.length <= EPSILON:
        raise LimbIKError("The limb root and IK endpoint occupy the same position.")
    total = (Vector(joint) - Vector(start)).length + (Vector(end) - Vector(joint)).length
    if total <= EPSILON:
        raise LimbIKError("The limb has no usable length.")
    configured = _finite_direction(pole_direction)
    direction = _project_perpendicular(configured, chain_axis)
    if direction.length <= max(EPSILON, configured.length * POLE_DIRECTION_PARALLEL_RATIO):
        raise LimbIKError(
            "Pole Direction is parallel to the limb root-to-end axis; choose another Armature-local XYZ direction."
        )
    direction.normalize()
    desired_joint = _joint_on_direction_plane(start, joint, end, direction)
    pole_distance = total * float(distance_ratio)
    pole_head = desired_joint + direction * pole_distance
    plane_normal = chain_axis.cross(pole_head - Vector(start))
    projected_pole_axis = plane_normal.cross(desired_joint - Vector(start))
    pole_angle = -_signed_angle(upper_x, projected_pole_axis, desired_joint - Vector(start))
    return pole_head, pole_angle, direction


def _build_plan(armature, chain, distance_ratio, pole_direction):
    upper = armature.pose.bones[chain.upper]
    lower = armature.pose.bones[chain.lower]
    end_bone = armature.pose.bones[chain.end]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    total = (joint - start).length + (end - joint).length
    reach = (end - start).length
    if total <= EPSILON:
        raise LimbIKError(f"{chain.side} {chain.kind.title()} has no usable length.")
    if total - reach <= max(EPSILON, total * POLE_MIN_REACH_DEFICIT_RATIO):
        bend_name = "elbow" if chain.kind == "ARM" else "knee"
        raise LimbIKError(
            f"{chain.side} {chain.kind.title()} is effectively straight, so Blender cannot keep a stable Pole plane. "
            f"Add a small bend at the {bend_name} in the current pose, then Build IK again."
        )
    pole_head, pole_angle, effective_pole_direction = _pole_solution(
        start,
        joint,
        end,
        upper.x_axis,
        pole_direction,
        distance_ratio,
    )
    pole_joint = _joint_on_direction_plane(start, joint, end, effective_pole_direction)
    size = max(total * 0.14, 1.0e-4)
    end_direction = Vector(end_bone.tail) - Vector(end_bone.head)
    if end_direction.length <= EPSILON:
        end_direction = end - joint
    end_direction.normalize()
    pole_tail_direction = _project_perpendicular(upper.z_axis, end - start)
    if pole_tail_direction.length <= EPSILON:
        pole_tail_direction = Vector((0.0, 0.0, 1.0))
    pole_tail_direction.normalize()
    spec = LIMB_SPEC[chain.kind]
    heel_name = ""
    solver_target_name = spec["target"].format(side=chain.side)
    heel_head = None
    heel_tail = None
    heel_z = None
    if chain.kind == "LEG":
        # A lightweight heel pivot is inferred entirely from the selected Foot
        # bone.  It intentionally remains conservative: behind the ankle along
        # the Foot axis and slightly toward the Shin's down direction.  The
        # internal solver target keeps the visible Foot control free to move
        # this pivot before the artist applies roll/bank.
        foot_vector = Vector(end_bone.tail) - Vector(end_bone.head)
        if foot_vector.length <= EPSILON:
            raise LimbIKError(f"{chain.side} Leg Foot bone has no usable direction for a heel pivot.")
        foot_length = foot_vector.length
        foot_forward = foot_vector.normalized()
        shin_down = end - joint
        if shin_down.length <= EPSILON:
            raise LimbIKError(f"{chain.side} Leg Shin has no usable direction for a heel pivot.")
        shin_down.normalize()
        heel_head = Vector(end_bone.head) - foot_forward * foot_length * 0.22 + shin_down * foot_length * 0.08
        heel_tail = heel_head + foot_forward * max(size * 0.8, foot_length * 0.18)
        heel_z = Vector(end_bone.matrix.to_3x3().col[2])
        heel_name = spec["heel"].format(side=chain.side)
        solver_target_name = spec["solver_target"].format(side=chain.side)
    return LimbPlan(
        chain=chain,
        rig_id=uuid.uuid4().hex,
        target_name=spec["target"].format(side=chain.side),
        pole_name=spec["pole"].format(side=chain.side),
        start=start,
        joint=joint,
        end=end,
        target_head=end.copy(),
        target_tail=end + end_direction * size,
        target_z=Vector(end_bone.matrix.to_3x3().col[2]),
        pole_head=pole_head,
        pole_tail=pole_head + pole_tail_direction * size * 0.65,
        pole_angle=pole_angle,
        pole_warning="",
        pole_direction=effective_pole_direction,
        pole_joint=pole_joint,
        desired_upper_matrix=upper.matrix.copy(),
        desired_lower_matrix=lower.matrix.copy(),
        desired_end_matrix=end_bone.matrix.copy(),
        target_basis=Matrix.Identity(4),
        pole_basis=Matrix.Identity(4),
        line_name=spec["line"].format(side=chain.side),
        display_name=spec["display"].format(side=chain.side),
        heel_name=heel_name,
        solver_target_name=solver_target_name,
        heel_head=heel_head,
        heel_tail=heel_tail,
        heel_z=heel_z,
    )


def _constraint_registry(pose_bone, *, strict=False):
    raw = pose_bone.get(CONSTRAINT_REGISTRY_KEY, "")
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        if strict:
            raise LimbIKError(f"Limb IK registry on bone '{pose_bone.name}' is corrupt.") from exc
        return {}
    if not isinstance(payload, dict):
        if strict:
            raise LimbIKError(f"Limb IK registry on bone '{pose_bone.name}' is invalid.")
        return {}
    return payload


def _write_constraint_registry(pose_bone, registry):
    if registry:
        pose_bone[CONSTRAINT_REGISTRY_KEY] = _canonical_json(registry)
    elif CONSTRAINT_REGISTRY_KEY in pose_bone:
        del pose_bone[CONSTRAINT_REGISTRY_KEY]


def _constraint_name(rig_id, role):
    return f"CDLimbIK_{role}_{rig_id}"


def _tag(target, armature_id, *, role, rig_id="", kind="", side="", chain=()):
    target[OWNER_KEY] = OWNER_VALUE
    target[VERSION_KEY] = RIG_VERSION
    target[ARMATURE_ID_KEY] = armature_id
    target[ROLE_KEY] = role
    if rig_id:
        target[RIG_ID_KEY] = rig_id
    if kind:
        target[KIND_KEY] = kind
    if side:
        target[SIDE_KEY] = side
    if chain:
        target[CHAIN_KEY] = _canonical_json(list(chain))


def _owned(target, armature_id, *, role=None, rig_id=None):
    try:
        return (
            target.get(OWNER_KEY) == OWNER_VALUE
            and target.get(VERSION_KEY) == RIG_VERSION
            and target.get(ARMATURE_ID_KEY) == armature_id
            and (role is None or target.get(ROLE_KEY) == role)
            and (rig_id is None or target.get(RIG_ID_KEY) == rig_id)
        )
    except (AttributeError, ReferenceError):
        return False


def _widget_geometry(kind, *, schema=ENHANCED_SCHEMA):
    """Return small wire widgets in Bone-local coordinates.

    Enhanced Hand/Master/Pole silhouettes are normalized from Rain's controls
    under the attribution and license recorded in ``ATTRIBUTION.md``;
    they are original mesh data recreated as simple line geometry, not linked or
    copied ID datablocks.  FINGER is intentionally geometry-only in this release.
    """
    if schema == LEGACY_SCHEMA:
        if kind == "HAND":
            vertices = ((-0.75, 0, -0.55), (0.75, 0, -0.55), (0.9, 0, -0.35), (0.9, 0, 0.35), (0.75, 0, 0.55), (-0.75, 0, 0.55), (-0.9, 0, 0.35), (-0.9, 0, -0.35))
        elif kind == "FOOT":
            vertices = ((-0.65, -0.9, 0), (0.65, -0.9, 0), (0.82, 0.55, 0), (0.5, 1.0, 0), (-0.5, 1.0, 0), (-0.82, 0.55, 0))
        else:
            count = 12
            vertices = tuple((math.cos(index * math.tau / count), 0, math.sin(index * math.tau / count)) for index in range(count))
        edges = tuple((index, (index + 1) % len(vertices)) for index in range(len(vertices)))
        return vertices, edges

    if kind == "HAND":
        vertices = (
            (0.507616699, 0.071150608, -0.000000215), (0.497480452, 0.085770570, -0.097545192),
            (0.467504233, 0.127871066, -0.191341609), (0.418951690, 0.192710653, -0.277785063),
            (0.353838533, 0.273602426, -0.353553325), (0.274862766, 0.361968160, -0.415734798),
            (0.185380891, 0.445415586, -0.461939752), (0.089344025, 0.506406367, -0.490392625),
            (-0.009000459, 0.527022839, -0.5), (-0.105621733, 0.499436408, -0.490392625),
            (-0.197058186, 0.431743503, -0.461939752), (-0.280352741, 0.342119187, -0.415734798),
            (-0.352816731, 0.248339325, -0.353553295), (-0.411986977, 0.163004369, -0.277784944),
            (-0.455785364, 0.094863214, -0.191341534), (-0.482678682, 0.050729472, -0.097544953),
            (-0.491744846, 0.035423212, 0.000000268), (-0.482678592, 0.050729472, 0.097545460),
            (-0.455785334, 0.094863214, 0.191342041), (-0.411986917, 0.163004413, 0.277785450),
            (-0.352816433, 0.248339400, 0.353553653), (-0.280352324, 0.342119187, 0.415735006),
            (-0.197057813, 0.431743443, 0.461939901), (-0.105621301, 0.499436349, 0.490392774),
            (-0.008999976, 0.527022719, 0.5), (0.089344561, 0.506406069, 0.490392566),
            (0.185381427, 0.445415139, 0.461939573), (0.274863482, 0.361967742, 0.415734470),
            (0.353839159, 0.273601979, 0.353552878), (0.418952167, 0.192710176, 0.277784616),
            (0.467504442, 0.127870739, 0.191341296), (0.497480631, 0.085770361, 0.097544789),
        )
        edges = tuple((index, (index + 1) % len(vertices)) for index in range(len(vertices)))
    elif kind == "MASTER":
        vertices = (
            (-0.461178720, 0, -0.461178720), (0.461178720, 0, -0.461178720),
            (-0.461178720, 0, 0.461178720), (0.461178720, 0, 0.461178720),
            (-0.443159282, 0, 0.443159282), (-0.443159282, 0, -0.443159282),
            (0.443159282, 0, -0.443159282), (0.443159282, 0, 0.443159282),
            (0.480463743, 0, -0.265761197), (0.480463743, 0, 0.265761226),
            (0.5, 0, 0.250185013), (0.5, 0, -0.250184983),
            (-0.265761197, 0, -0.480463743), (0.265761197, 0, -0.480463743),
            (0.250185013, 0, -0.5), (-0.250184983, 0, -0.5),
            (-0.480463743, 0, 0.265761226), (-0.480463743, 0, -0.265761197),
            (-0.5, 0, -0.250185013), (-0.5, 0, 0.250185013),
            (0.265761197, 0, 0.480463743), (-0.265761197, 0, 0.480463743),
            (-0.250185013, 0, 0.5), (0.250184983, 0, 0.5),
        )
        edges = ((8, 11), (10, 9), (12, 15), (14, 13), (16, 19), (18, 17), (20, 23), (22, 21), (7, 9), (10, 3), (8, 6), (1, 11), (6, 13), (14, 1), (12, 5), (0, 15), (5, 17), (18, 0), (16, 4), (2, 19), (4, 21), (22, 2), (20, 7), (3, 23))
    elif kind == "POLE_ARROW":
        vertices = ((-0.474555194, -1, 0.474554807), (-0.474555194, -0.99999994, -0.474555612), (0.474555194, -0.99999994, -0.474555612), (0.474555194, -1, 0.474554807), (0, 0, -0.000000048))
        edges = ((0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4))
    elif kind == "POLE_LINE":
        vertices, edges = ((0, 0, 0), (0, 1, 0)), ((0, 1),)
    elif kind == "FOOT":
        vertices = (
            (0.099234894, 0.871687770, 0.000727093), (0.194205865, -0.071024314, 0.000438197),
            (-0.186365515, 0.825411975, 0.000631400), (-0.007368974, -0.099799521, 0.000472580),
            (0.194076076, 0.578032792, 0.000023564), (-0.278784126, 0.530485034, 0.000021460),
            (-0.159259334, 0.173546672, -0.000034734), (0.210402682, 0.207939595, -0.000031146),
            (0.189964861, 0.628364623, 0.000021308), (0.173066407, 0.732698798, -0.000003148),
            (0.132744923, 0.832533777, -0.000075472), (0.038417019, -0.114003643, -0.000292528),
            (0.101531841, -0.113783777, -0.000094001), (0.160142154, -0.095507771, -0.000294212),
            (-0.120430134, 0.072465695, -0.000068591), (-0.099163838, 0.022602918, -0.000097153),
            (-0.037944019, -0.073271163, 0.000075338), (0.039580546, 0.889435172, -0.000213846),
            (-0.038276959, 0.885206699, -0.000079284), (-0.119038858, 0.861792743, -0.000274932),
            (0.206765726, 0.260585546, -0.000018355), (0.202150643, 0.366447002, 0.000004608),
            (0.199428171, 0.467522144, 0.000018613), (-0.228298619, 0.778306067, -0.000147301),
            (-0.273770511, 0.677303314, -0.000016196), (-0.283078045, 0.578685939, 0.000017398),
            (-0.255540878, 0.424573123, 0.000017627), (-0.221513256, 0.327776104, 0.000002502),
            (-0.179988638, 0.225336537, -0.000021708), (0.211478710, -0.038747311, 0.000076016),
            (0.223457947, 0.059776247, -0.000092626), (0.220201626, 0.108500011, -0.000064606),
            (0.156389371, 0.783612728, -0.000081165), (-0.256016791, 0.727344453, -0.000117335),
            (0.182560578, 0.685647905, 0.000012276), (-0.281778038, 0.633144438, 0.000004574),
            (0.197160974, 0.524336100, 0.000022641), (-0.269585460, 0.479019910, 0.000021530),
            (0.200832501, 0.417848617, 0.000012667), (-0.239865437, 0.377017140, 0.000011302),
            (0.203929767, 0.312606871, -0.000006503), (-0.200427473, 0.276034266, -0.000009422),
            (-0.140166104, 0.122850493, -0.000049585), (0.215601921, 0.158007219, -0.000045798),
            (-0.073479183, -0.023025773, -0.000221944), (0.219749227, 0.007535274, -0.000183419),
        )
        edges = ((4, 8), (34, 9), (32, 10), (10, 0), (3, 11), (11, 12), (12, 13), (13, 1), (42, 14), (14, 15), (44, 16), (16, 3), (0, 17), (17, 18), (18, 19), (19, 2), (7, 20), (40, 21), (38, 22), (36, 4), (2, 23), (33, 24), (35, 25), (25, 5), (37, 26), (39, 27), (41, 28), (28, 6), (1, 29), (45, 30), (30, 31), (43, 7), (9, 32), (23, 33), (8, 34), (24, 35), (22, 36), (5, 37), (21, 38), (26, 39), (20, 40), (27, 41), (6, 42), (31, 43), (15, 44), (29, 45))
    elif kind == "HEEL":
        vertices = (
            (0, 0.499999821, -0.000000231), (0, 0.490392715, -0.097545438), (0, 0.461939812, -0.191342011),
            (0, 0.415734619, -0.277785212), (0, 0.353553355, -0.353553444), (0, 0.277785122, -0.415735066),
            (0, 0.191341475, -0.461939901), (0, 0.097545043, -0.490392804), (0, -0.000000121, -0.500000536),
            (0, -0.097545303, -0.490392804), (0, -0.191341788, -0.461939901), (0, -0.277785420, -0.415735066),
            (0, -0.353553712, -0.353553444), (0, -0.415734977, -0.277785212), (0, -0.461940259, -0.191341788),
            (0, -0.490393072, -0.097545020), (0, -0.500000179, 0.000000198), (0, -0.490393072, 0.097545415),
            (0, -0.461940259, 0.191341937), (0, -0.415734977, 0.277785450), (0, -0.353553712, 0.353553355),
            (0, -0.277785122, 0.415735513), (0, -0.191341430, 0.461940169), (0, 0.391893446, 0.391893089),
            (0, 0.353553981, 0.353552997), (0, 0.415735245, 0.277784556), (0, 0.461940438, 0.191340879),
            (0, 0.490392715, 0.097544335), (0, 0.389615744, -0.000000231), (0, 0.382129461, -0.076010473),
            (0, 0.359958023, -0.149099678), (0, 0.323953897, -0.216459095), (0, 0.275500059, -0.275500298),
            (0, 0.216458902, -0.323954105), (0, 0.149099439, -0.359958321), (0, 0.076010227, -0.382129550),
            (0, -0.000000095, -0.389616102), (0, -0.076010391, -0.382129550), (0, -0.149099603, -0.359958321),
            (0, -0.216459259, -0.323954105), (0, -0.275500417, -0.275500298), (0, -0.323953897, -0.216459095),
            (0, -0.359958380, -0.149099454), (0, -0.382129818, -0.076010257), (0, -0.389616102, 0.000000198),
            (0, -0.382129818, 0.076010436), (0, -0.359958380, 0.149099901), (0, -0.323953897, 0.216459066),
            (0, -0.275500000, 0.275500238), (0, -0.216458946, 0.323954046), (0, -0.149099261, 0.359958261),
            (0, 0.237160593, 0.237160176), (0, 0.275500357, 0.275499642), (0, 0.323953897, 0.216458440),
            (0, 0.359958380, 0.149098799), (0, 0.382129461, 0.076009601), (0, -0.170220375, 0.410949498),
            (0, 0.247122675, 0.369844228),
        )
        edges = ((1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7), (9, 8), (10, 9), (11, 10), (12, 11), (13, 12), (14, 13), (15, 14), (16, 15), (17, 16), (18, 17), (19, 18), (20, 19), (21, 20), (22, 21), (24, 23), (25, 24), (26, 25), (27, 26), (0, 27), (29, 28), (30, 29), (31, 30), (32, 31), (33, 32), (34, 33), (35, 34), (36, 35), (37, 36), (38, 37), (39, 38), (40, 39), (41, 40), (42, 41), (43, 42), (44, 43), (45, 44), (46, 45), (47, 46), (48, 47), (49, 48), (50, 49), (52, 51), (53, 52), (54, 53), (55, 54), (28, 55), (56, 22), (57, 23), (51, 57), (50, 56))
    elif kind == "FINGER":
        points = []
        for index in range(32):
            angle = index * math.tau / 32
            x = -0.409725934 * math.sin(angle)
            z = 0.409725934 * math.cos(angle)
            if index == 8:
                x = -0.5
            elif index == 24:
                x = 0.5
            points.append((x, 0, z))
        vertices = tuple(points)
        edges = tuple((index, (index + 1) % len(vertices)) for index in range(len(vertices)))
    else:
        raise LimbIKError(f"Unknown Limb IK widget kind '{kind}'.")
    return vertices, edges


def _collection_scene_memberships(collection):
    return tuple(scene for scene in bpy.data.scenes if collection is scene.collection or collection in scene.collection.children_recursive)


def _ensure_widget_collection(context, armature_id, transaction):
    matches = [collection for collection in bpy.data.collections if _owned(collection, armature_id, role="WIDGET_COLLECTION")]
    if len(matches) > 1:
        raise LimbIKError("Multiple owned Randy Rig widget collections were found; repair them manually.")
    if matches:
        collection = matches[0]
        if _collection_scene_memberships(collection) != (context.scene,):
            raise LimbIKError("The owned widget collection is linked across Scenes.")
        return collection
    foreign = bpy.data.collections.get(WIDGET_COLLECTION_NAME)
    if foreign is not None:
        raise LimbIKError(f"Collection '{WIDGET_COLLECTION_NAME}' already exists but is not owned by Character Designer.")
    collection = bpy.data.collections.new(WIDGET_COLLECTION_NAME)
    context.scene.collection.children.link(collection)
    _tag(collection, armature_id, role="WIDGET_COLLECTION")
    collection.hide_render = True
    collection.hide_viewport = True
    transaction["collections"].append(collection)
    return collection


def _ensure_widget(context, armature_id, collection, kind, transaction, *, schema=ENHANCED_SCHEMA):
    matches = [obj for obj in bpy.data.objects if _owned(obj, armature_id, role="WIDGET") and obj.get(KIND_KEY) == kind]
    if len(matches) > 1:
        raise LimbIKError(f"Multiple owned {kind.title()} widgets were found.")
    if matches:
        obj = matches[0]
        if obj.type != "MESH" or not _owned(obj.data, armature_id, role="WIDGET_DATA") or obj.data.get(KIND_KEY) != kind:
            raise LimbIKError(f"Owned {kind.title()} widget data is invalid.")
        if tuple(obj.users_collection) != (collection,):
            raise LimbIKError(f"Owned {kind.title()} widget is linked outside its exact collection.")
        return obj
    names = {
        "HAND": "WGT_Randy_HandIK", "FOOT": "WGT_Randy_FootIK", "POLE": "WGT_Randy_Pole",
        "POLE_ARROW": "WGT_Randy_PoleArrow", "POLE_LINE": "WGT_Randy_PoleLine",
        "HEEL": "WGT_Randy_HeelRoll", "MASTER": "WGT_Randy_Master", "FINGER": "WGT_Randy_Finger",
    }
    name = names[kind]
    if bpy.data.objects.get(name) is not None or bpy.data.meshes.get(name) is not None:
        raise LimbIKError(f"Widget name '{name}' is already used by non-owned data.")
    mesh = bpy.data.meshes.new(name)
    vertices, edges = _widget_geometry(kind, schema=schema)
    mesh.from_pydata(vertices, edges, ())
    mesh.update()
    _tag(mesh, armature_id, role="WIDGET_DATA", kind=kind)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    _tag(obj, armature_id, role="WIDGET", kind=kind)
    obj.hide_render = True
    obj.display_type = "WIRE"
    transaction["meshes"].append(mesh)
    transaction["objects"].append(obj)
    return obj


def _ensure_control_collection(armature, armature_id, transaction):
    matches = [collection for collection in armature.data.collections if _owned(collection, armature_id, role="CONTROL_COLLECTION")]
    if len(matches) > 1:
        raise LimbIKError("Multiple owned Randy Controls bone collections were found.")
    if matches:
        return matches[0]
    foreign = armature.data.collections.get(CONTROL_COLLECTION_NAME)
    if foreign is not None:
        raise LimbIKError(f"Bone Collection '{CONTROL_COLLECTION_NAME}' already exists but is not owned by Character Designer.")
    collection = armature.data.collections.new(CONTROL_COLLECTION_NAME)
    _tag(collection, armature_id, role="CONTROL_COLLECTION")
    transaction["bone_collections"].append(collection)
    return collection


def _owned_constraint_records(armature, *, strict=True):
    records = []
    pose = armature.pose
    if pose is None:
        return records
    for pose_bone in pose.bones:
        registry = _constraint_registry(pose_bone, strict=strict)
        for constraint_name, record in registry.items():
            if not isinstance(constraint_name, str) or not isinstance(record, dict):
                raise LimbIKError(f"Limb IK registry on bone '{pose_bone.name}' contains an invalid record.")
            rig_id = record.get("rig_id")
            role = record.get("role")
            role_types = {
                "IK": "IK",
                "END_ROTATION": "COPY_ROTATION",
                "POLE_LINE_STRETCH": "STRETCH_TO",
                "POLE_DISPLAY_TRACK": "DAMPED_TRACK",
                "HEEL_LIMIT": "LIMIT_ROTATION",
                "MASTER_FOLLOW": "COPY_TRANSFORMS",
            }
            if (
                record.get("owner") != OWNER_VALUE
                or record.get("version") != RIG_VERSION
                or not isinstance(rig_id, str)
                or not rig_id
                or role not in role_types
                or constraint_name != _constraint_name(rig_id, role)
            ):
                raise LimbIKError(f"Limb IK registry on bone '{pose_bone.name}' has an unknown ownership fingerprint.")
            matches = [constraint for constraint in pose_bone.constraints if constraint.name == constraint_name]
            if len(matches) != 1:
                raise LimbIKError(f"Owned constraint '{constraint_name}' is missing or duplicated.")
            constraint = matches[0]
            expected_type = role_types[role]
            if constraint.type != expected_type:
                raise LimbIKError(f"Owned constraint '{constraint_name}' changed type.")
            records.append((pose_bone, constraint, record))
    return records


def _record_constraint(pose_bone, constraint, plan, armature_id, role, *, schema=ENHANCED_SCHEMA):
    registry = _constraint_registry(pose_bone, strict=True)
    constraint.name = _constraint_name(plan.rig_id, role)
    if constraint.name in registry:
        raise LimbIKError(f"Constraint registry collision on '{pose_bone.name}'.")
    record = {
        "owner": OWNER_VALUE,
        "version": RIG_VERSION,
        "armature_id": armature_id,
        "rig_id": plan.rig_id,
        "role": role,
        "kind": plan.chain.kind,
        "side": plan.chain.side,
        "chain": list(plan.chain.names),
        "target": plan.target_name,
        "pole": plan.pole_name,
    }
    if schema == ENHANCED_SCHEMA:
        record.update(
            {
                "line": plan.line_name,
                "display": plan.display_name,
                "heel": plan.heel_name,
                "solver_target": plan.solver_target_name,
                "master": MASTER_NAME,
            }
        )
    registry[constraint.name] = record
    _write_constraint_registry(pose_bone, registry)


def _record_master_constraint(pose_bone, constraint, armature_id):
    registry = _constraint_registry(pose_bone, strict=True)
    constraint.name = _constraint_name(armature_id, "MASTER_FOLLOW")
    if constraint.name in registry:
        raise LimbIKError(f"Constraint registry collision on '{pose_bone.name}'.")
    registry[constraint.name] = {
        "owner": OWNER_VALUE,
        "version": RIG_VERSION,
        "armature_id": armature_id,
        "rig_id": armature_id,
        "role": "MASTER_FOLLOW",
        "root": pose_bone.name,
        "target": MASTER_NAME,
    }
    _write_constraint_registry(pose_bone, registry)


def _validate_inventory(armature):
    armature_id = armature.data.get(ARMATURE_ID_KEY, "")
    generated = [bone for bone in armature.data.bones if bone.get(OWNER_KEY) == OWNER_VALUE]
    records = _owned_constraint_records(armature, strict=True)
    if not armature_id:
        if generated or records or SCHEMA_KEY in armature.data:
            raise LimbIKError("Orphaned Limb IK ownership data was found on this Armature.")
        return {"armature_id": "", "schema": 0, "rigs": {}, "records": [], "bones": [], "master": None, "master_records": []}
    if not isinstance(armature_id, str):
        raise LimbIKError("The Limb IK Armature ID is invalid.")
    schema = armature.data.get(SCHEMA_KEY, LEGACY_SCHEMA)
    if schema not in {LEGACY_SCHEMA, ENHANCED_SCHEMA}:
        raise LimbIKError("The Limb IK schema version is unsupported.")
    if not generated and not records:
        return {"armature_id": armature_id, "schema": schema, "rigs": {}, "records": [], "bones": [], "master": None, "master_records": []}
    for pose_bone, constraint, _record in records:
        influence = float(constraint.influence)
        if constraint.mute or not math.isfinite(influence) or abs(influence - 1.0) > 1.0e-6:
            raise LimbIKError(f"Owned constraint '{constraint.name}' on '{pose_bone.name}' was disabled or had its influence edited.")
    rigs = {}
    by_rig = {}
    master_records = []
    for pose_bone, constraint, record in records:
        if record.get("armature_id") != armature_id:
            raise LimbIKError("A Limb IK constraint belongs to a different Armature ID.")
        if record["role"] == "MASTER_FOLLOW":
            master_records.append((pose_bone, constraint, record))
        else:
            rig_id = record["rig_id"]
            by_rig.setdefault(rig_id, []).append((pose_bone, constraint, record))
    expected_bones = set()
    for rig_id, entries in by_rig.items():
        sample = entries[0][2]
        key = (sample.get("kind"), sample.get("side"))
        if key[0] not in KINDS or key[1] not in SIDES or key in rigs:
            raise LimbIKError("Duplicate or invalid Limb IK side ownership was found.")
        limb_roles = {"IK", "END_ROTATION"}
        if schema == ENHANCED_SCHEMA:
            limb_roles.update(("POLE_LINE_STRETCH", "POLE_DISPLAY_TRACK"))
            if key[0] == "LEG":
                limb_roles.add("HEEL_LIMIT")
        if len(entries) != len(limb_roles) or {record["role"] for _pb, _con, record in entries} != limb_roles:
            raise LimbIKError(f"Limb IK rig '{rig_id}' is incomplete.")
        chain_value = sample.get("chain")
        target_name = sample.get("target")
        pole_name = sample.get("pole")
        if (
            not isinstance(chain_value, (list, tuple))
            or len(chain_value) != 3
            or any(not isinstance(name, str) or not name for name in chain_value)
            or len(set(chain_value)) != 3
            or any(armature.data.bones.get(name) is None for name in chain_value)
            or not isinstance(target_name, str)
            or not target_name
            or not isinstance(pole_name, str)
            or not pole_name
            or target_name == pole_name
        ):
            raise LimbIKError(f"Limb IK rig '{rig_id}' registry has an invalid source/control bone schema.")
        chain = tuple(chain_value)
        enhanced_names = {}
        if schema == ENHANCED_SCHEMA:
            enhanced_names = {
                key_name: sample.get(key_name, "")
                for key_name in ("line", "display", "heel", "solver_target", "master")
            }
            required = ("line", "display", "solver_target", "master")
            if any(not isinstance(enhanced_names[name], str) or not enhanced_names[name] for name in required):
                raise LimbIKError(f"Limb IK rig '{rig_id}' has incomplete enhanced controls.")
            if enhanced_names["master"] != MASTER_NAME:
                raise LimbIKError(f"Limb IK rig '{rig_id}' points at an unknown Master control.")
            if key[0] == "LEG" and (not isinstance(enhanced_names["heel"], str) or not enhanced_names["heel"]):
                raise LimbIKError(f"Limb IK rig '{rig_id}' has no Heel Roll control.")
            if key[0] == "ARM" and enhanced_names["heel"]:
                raise LimbIKError(f"Limb IK rig '{rig_id}' has an unexpected Heel Roll control.")
        if any(
            record.get("chain") != list(chain)
            or record.get("target") != target_name
            or record.get("pole") != pole_name
            or record.get("kind") != sample.get("kind")
            or record.get("side") != sample.get("side")
            or record.get("armature_id") != armature_id
            or (schema == ENHANCED_SCHEMA and any(record.get(name, "") != value for name, value in enhanced_names.items()))
            for _pb, _con, record in entries
        ):
            raise LimbIKError(f"Limb IK rig '{rig_id}' has inconsistent registry records.")
        target = armature.data.bones.get(target_name)
        pole = armature.data.bones.get(pole_name)
        if not _owned(target, armature_id, role=LIMB_SPEC[key[0]]["target_role"], rig_id=rig_id) or not _owned(pole, armature_id, role="POLE", rig_id=rig_id):
            raise LimbIKError(f"Limb IK rig '{rig_id}' control bone ownership is invalid.")
        saved_pole_direction = None
        if POLE_DIRECTION_KEY in pole:
            saved_pole_direction = _finite_direction(
                pole[POLE_DIRECTION_KEY],
                f"Saved {key[1]} {key[0].title()} Pole Direction",
            )
            if abs(saved_pole_direction.length - 1.0) > 1.0e-5:
                raise LimbIKError(f"Limb IK rig '{rig_id}' has a non-normalized Pole Direction tag.")
            saved_pole_direction.normalize()
        expected_bones.update((target.name, pole.name))
        ik_entry = next(entry for entry in entries if entry[2]["role"] == "IK")
        end_entry = next(entry for entry in entries if entry[2]["role"] == "END_ROTATION")
        lower_pb, ik, _record = ik_entry
        end_pb, copy_rotation, _record = end_entry
        if lower_pb.name != chain[1] or end_pb.name != chain[2]:
            raise LimbIKError(f"Limb IK rig '{rig_id}' constraints moved to other bones.")
        solver_target = target
        line = display = heel = None
        if schema == ENHANCED_SCHEMA:
            line = armature.data.bones.get(enhanced_names["line"])
            display = armature.data.bones.get(enhanced_names["display"])
            solver_target = armature.data.bones.get(enhanced_names["solver_target"])
            heel = armature.data.bones.get(enhanced_names["heel"]) if enhanced_names["heel"] else None
            if not _owned(line, armature_id, role="POLE_LINE", rig_id=rig_id) or not _owned(display, armature_id, role="POLE_DISPLAY", rig_id=rig_id) or not _owned(solver_target, armature_id, role="FOOT_TARGET" if key[0] == "LEG" else "HAND_IK", rig_id=rig_id):
                raise LimbIKError(f"Limb IK rig '{rig_id}' enhanced bone ownership is invalid.")
            if key[0] == "ARM" and solver_target.name != target.name:
                raise LimbIKError(f"Limb IK rig '{rig_id}' has a separate Arm solver target.")
            if key[0] == "LEG" and not _owned(heel, armature_id, role="HEEL_ROLL", rig_id=rig_id):
                raise LimbIKError(f"Limb IK rig '{rig_id}' Heel Roll ownership is invalid.")
            expected_bones.update((line.name, display.name, solver_target.name))
            if heel is not None:
                expected_bones.add(heel.name)
            master = armature.data.bones.get(MASTER_NAME)
            if (
                master is None
                or target.parent is None or target.parent.name != master.name
                or pole.parent is None or pole.parent.name != master.name
                or line.parent is None or line.parent.name != chain[0]
                or display.parent is None or display.parent.name != pole.name
            ):
                raise LimbIKError(f"Limb IK rig '{rig_id}' generated hierarchy was edited.")
            if key[0] == "LEG" and (
                heel.parent is None or heel.parent.name != target.name
                or solver_target.parent is None or solver_target.parent.name != heel.name
            ):
                raise LimbIKError(f"Limb IK rig '{rig_id}' Foot/Heel hierarchy was edited.")
            line_entry = next(entry for entry in entries if entry[2]["role"] == "POLE_LINE_STRETCH")
            display_entry = next(entry for entry in entries if entry[2]["role"] == "POLE_DISPLAY_TRACK")
            line_pb, stretch, _record = line_entry
            display_pb, track, _record = display_entry
            if line_pb.name != line.name or stretch.target is not armature or stretch.subtarget != pole.name or stretch.target_space != "WORLD" or stretch.owner_space != "WORLD":
                raise LimbIKError(f"Limb IK rig '{rig_id}' Pole line mechanism was edited.")
            if display_pb.name != display.name or track.target is not armature or track.subtarget != chain[1] or track.track_axis != "TRACK_NEGATIVE_Y" or track.target_space != "WORLD" or track.owner_space != "WORLD":
                raise LimbIKError(f"Limb IK rig '{rig_id}' Pole arrow mechanism was edited.")
            if key[0] == "LEG":
                heel_pb, heel_limit, _record = next(entry for entry in entries if entry[2]["role"] == "HEEL_LIMIT")
                if heel_pb.name != heel.name or heel_limit.owner_space != "LOCAL" or not heel_limit.use_limit_x or abs(heel_limit.min_x + math.pi * 0.5) > 1.0e-6 or abs(heel_limit.max_x - math.radians(130.0)) > 1.0e-6:
                    raise LimbIKError(f"Limb IK rig '{rig_id}' Heel Roll limits were edited.")
        if (
            ik.target is not armature
            or ik.subtarget != solver_target.name
            or ik.pole_target is not armature
            or ik.pole_subtarget != pole.name
            or ik.chain_count != 2
            or ik.target_space != "WORLD"
            or ik.owner_space != "WORLD"
            or (hasattr(ik, "use_tail") and not ik.use_tail)
            or (hasattr(ik, "use_stretch") and ik.use_stretch)
        ):
            raise LimbIKError(f"Limb IK rig '{rig_id}' IK settings were edited.")
        if (
            copy_rotation.target is not armature
            or copy_rotation.subtarget != solver_target.name
            or copy_rotation.target_space != "WORLD"
            or copy_rotation.owner_space != "WORLD"
            or getattr(copy_rotation, "mix_mode", "") != "REPLACE"
        ):
            raise LimbIKError(f"Limb IK rig '{rig_id}' end rotation settings were edited.")
        rigs[key] = {
            "rig_id": rig_id,
            "entries": entries,
            "target": target,
            "pole": pole,
            "chain": chain,
            "line": line,
            "display": display,
            "heel": heel,
            "solver_target": solver_target,
            "pole_direction": saved_pole_direction,
        }
    master = None
    if schema == ENHANCED_SCHEMA:
        master = armature.data.bones.get(MASTER_NAME)
        if not _owned(master, armature_id, role="MASTER") or master.parent is not None:
            raise LimbIKError("The enhanced Limb IK Master control is missing or invalid.")
        expected_bones.add(master.name)
        source_roots = {bone.name for bone in armature.data.bones if bone.parent is None and bone.get(OWNER_KEY) != OWNER_VALUE}
        if {pose_bone.name for pose_bone, _constraint, _record in master_records} != source_roots or len(master_records) != len(source_roots):
            raise LimbIKError("Master does not own exactly one follow constraint for every source root.")
        for pose_bone, constraint, record in master_records:
            if record.get("root") != pose_bone.name or record.get("target") != MASTER_NAME:
                raise LimbIKError("A Master follow registry record is invalid.")
            if constraint.target is not armature or constraint.subtarget != MASTER_NAME or constraint.target_space != "POSE" or constraint.owner_space != "POSE" or getattr(constraint, "mix_mode", "") != "BEFORE":
                raise LimbIKError(f"Master follow on source root '{pose_bone.name}' was edited.")
    elif master_records:
        raise LimbIKError("A legacy Limb IK rig contains unexpected Master constraints.")
    if {bone.name for bone in generated} != expected_bones:
        raise LimbIKError("Orphaned or duplicate generated Limb IK control bones were found.")
    return {"armature_id": armature_id, "schema": schema, "rigs": rigs, "records": records, "bones": generated, "master": master, "master_records": master_records}


def _preflight_plans(context, armature, plans, inventory, *, schema=ENHANCED_SCHEMA):
    if inventory["armature_id"] and inventory["schema"] != schema:
        raise LimbIKError("This is a legacy Limb IK rig; use Rebuild Rig to upgrade it before adding limbs.")
    existing_keys = set(inventory["rigs"])
    for plan in plans:
        key = (plan.chain.kind, plan.chain.side)
        if key in existing_keys:
            if tuple(inventory["rigs"][key]["chain"]) != plan.chain.names:
                raise LimbIKError(f"Existing {plan.chain.side} {plan.chain.kind.title()} rig targets a different source chain; use Remove Generated Rig first.")
            continue
        names = {plan.target_name, plan.pole_name}
        if schema == ENHANCED_SCHEMA:
            names.update((plan.line_name, plan.display_name, plan.solver_target_name))
            if plan.heel_name:
                names.add(plan.heel_name)
        for name in names:
            if armature.data.bones.get(name) is not None:
                raise LimbIKError(f"Bone '{name}' already exists and is not this exact generated control.")
        lower = armature.pose.bones[plan.chain.lower]
        end = armature.pose.bones[plan.chain.end]
        if any(constraint.type == "IK" for constraint in lower.constraints):
            raise LimbIKError(f"Bone '{lower.name}' already has an IK constraint; Limb IK will not stack another one.")
        if any(constraint.type == "COPY_ROTATION" for constraint in end.constraints):
            raise LimbIKError(f"Bone '{end.name}' already has Copy Rotation; Limb IK will not stack another one.")
    if not inventory["armature_id"]:
        if schema == ENHANCED_SCHEMA and armature.data.bones.get(MASTER_NAME) is not None:
            raise LimbIKError(f"Bone '{MASTER_NAME}' already exists and is not this exact generated control.")
        if armature.data.collections.get(CONTROL_COLLECTION_NAME) is not None:
            raise LimbIKError(f"Bone Collection '{CONTROL_COLLECTION_NAME}' is occupied by foreign data.")
        if bpy.data.collections.get(WIDGET_COLLECTION_NAME) is not None:
            raise LimbIKError(f"Collection '{WIDGET_COLLECTION_NAME}' is occupied by foreign data.")


def _new_transaction():
    return {
        "constraints": [],
        "registry_before": {},
        "bone_names": [],
        "objects": [],
        "meshes": [],
        "collections": [],
        "bone_collections": [],
        "new_armature_id": False,
        "new_schema": False,
    }


def _remember_registry(transaction, pose_bone):
    if pose_bone.name not in transaction["registry_before"]:
        transaction["registry_before"][pose_bone.name] = pose_bone.get(CONSTRAINT_REGISTRY_KEY, None)


def _rollback_build(context, armature, transaction):
    errors = []
    try:
        _mode_set(context, armature, "POSE")
        for pose_bone, constraint in reversed(transaction["constraints"]):
            try:
                # RNA wrapper identity is not stable across the Edit/Object/Pose
                # boundaries used while adding controls.  Resolve the exact
                # transaction-created UUID name again instead of comparing the
                # short-lived Python proxy with ``is``.
                live_owner = armature.pose.bones.get(pose_bone.name)
                live_constraint = live_owner.constraints.get(constraint.name) if live_owner is not None else None
                if live_constraint is not None:
                    live_owner.constraints.remove(live_constraint)
            except (ReferenceError, RuntimeError) as exc:
                errors.append(str(exc))
        for bone_name, raw in transaction["registry_before"].items():
            pose_bone = armature.pose.bones.get(bone_name)
            if pose_bone is None:
                continue
            try:
                if raw is None:
                    if CONSTRAINT_REGISTRY_KEY in pose_bone:
                        del pose_bone[CONSTRAINT_REGISTRY_KEY]
                else:
                    pose_bone[CONSTRAINT_REGISTRY_KEY] = raw
            except (ReferenceError, RuntimeError) as exc:
                errors.append(str(exc))
        _mode_set(context, armature, "OBJECT")
        armature.data.update_tag()
        armature.update_tag(refresh={"OBJECT"})
        context.view_layer.update()
        _mode_set(context, armature, "EDIT")
        for name in reversed(transaction["bone_names"]):
            bone = armature.data.edit_bones.get(name)
            if bone is not None:
                armature.data.edit_bones.remove(bone)
        _mode_set(context, armature, "OBJECT")
        armature.data.update_tag()
        armature.update_tag(refresh={"OBJECT"})
        context.view_layer.update()
    except (LimbIKError, ReferenceError, RuntimeError) as exc:
        errors.append(str(exc))
    for obj in reversed(transaction["objects"]):
        try:
            if bpy.data.objects.get(obj.name) is obj:
                bpy.data.objects.remove(obj, do_unlink=True)
        except (ReferenceError, RuntimeError) as exc:
            errors.append(str(exc))
    for mesh in reversed(transaction["meshes"]):
        try:
            if bpy.data.meshes.get(mesh.name) is mesh and not mesh.users:
                bpy.data.meshes.remove(mesh)
        except (ReferenceError, RuntimeError) as exc:
            errors.append(str(exc))
    for collection in reversed(transaction["collections"]):
        try:
            if bpy.data.collections.get(collection.name) is collection:
                bpy.data.collections.remove(collection)
        except (ReferenceError, RuntimeError) as exc:
            errors.append(str(exc))
    for collection in reversed(transaction["bone_collections"]):
        try:
            live = armature.data.collections.get(collection.name)
            if live is not None:
                armature.data.collections.remove(live)
        except (ReferenceError, RuntimeError) as exc:
            errors.append(str(exc))
    if transaction["new_armature_id"] and ARMATURE_ID_KEY in armature.data:
        try:
            del armature.data[ARMATURE_ID_KEY]
        except (ReferenceError, RuntimeError) as exc:
            errors.append(str(exc))
    if transaction["new_schema"] and SCHEMA_KEY in armature.data:
        try:
            del armature.data[SCHEMA_KEY]
        except (ReferenceError, RuntimeError) as exc:
            errors.append(str(exc))
    return errors


def _master_bone_size(armature):
    source = [bone for bone in armature.data.bones if bone.get(OWNER_KEY) != OWNER_VALUE]
    if not source:
        return 1.0
    points = [Vector(point) for bone in source for point in (bone.head_local, bone.tail_local)]
    span = max((max(point[index] for point in points) - min(point[index] for point in points) for index in range(3)), default=1.0)
    return max(span * 0.18, 0.1)


def _create_control_bones(context, armature, armature_id, plans, transaction, *, schema=ENHANCED_SCHEMA, create_master=False):
    # Blender's X-Mirror edit option also mirrors programmatic EditBone writes.
    # On an asymmetric/rest-rolled production skeleton, creating the R control
    # after L can silently overwrite L's roll.  This temporary option change is
    # local to the edit transaction and is restored on every exit path.
    master_size = _master_bone_size(armature)
    line_rest_points = {}
    if schema == ENHANCED_SCHEMA:
        for plan in plans:
            upper_data = armature.data.bones[plan.chain.upper]
            rest_from_current_pose = upper_data.matrix_local @ plan.desired_upper_matrix.inverted_safe()
            line_rest_points[plan.rig_id] = (
                rest_from_current_pose @ plan.pole_joint,
                rest_from_current_pose @ plan.pole_head,
            )
    mirror_x = bool(armature.data.use_mirror_x)
    try:
        armature.data.use_mirror_x = False
        _mode_set(context, armature, "EDIT")
        master = armature.data.edit_bones.get(MASTER_NAME)
        if schema == ENHANCED_SCHEMA and create_master:
            master = armature.data.edit_bones.new(MASTER_NAME)
            if master.name != MASTER_NAME:
                raise LimbIKError(f"Blender renamed generated bone '{MASTER_NAME}'; build was rolled back.")
            transaction["bone_names"].append(master.name)
            master.head = (0.0, 0.0, 0.0)
            master.tail = (0.0, master_size, 0.0)
            master.roll = 0.0
            master.parent = None
            master.use_connect = False
            master.use_deform = False
        for plan in plans:
            target = armature.data.edit_bones.new(plan.target_name)
            if target.name != plan.target_name:
                raise LimbIKError(f"Blender renamed generated bone '{plan.target_name}'; build was rolled back.")
            transaction["bone_names"].append(target.name)
            target.head = plan.target_head
            target.tail = plan.target_tail
            target.parent = None
            target.use_connect = False
            target.use_deform = False
            target.align_roll(plan.target_z)

            pole = armature.data.edit_bones.new(plan.pole_name)
            if pole.name != plan.pole_name:
                raise LimbIKError(f"Blender renamed generated bone '{plan.pole_name}'; build was rolled back.")
            transaction["bone_names"].append(pole.name)
            pole.head = plan.pole_head
            pole.tail = plan.pole_tail
            pole.parent = None
            pole.use_connect = False
            pole.use_deform = False

            if schema == ENHANCED_SCHEMA:
                target.parent = master
                pole.parent = master

                line = armature.data.edit_bones.new(plan.line_name)
                if line.name != plan.line_name:
                    raise LimbIKError(f"Blender renamed generated bone '{plan.line_name}'; build was rolled back.")
                transaction["bone_names"].append(line.name)
                line.head, line.tail = line_rest_points[plan.rig_id]
                if (Vector(line.tail) - Vector(line.head)).length <= EPSILON:
                    line.tail = Vector(line.head) + Vector((0.0, max((plan.end - plan.start).length * 0.2, 0.01), 0.0))
                line.parent = armature.data.edit_bones[plan.chain.upper]
                line.use_connect = False
                line.use_deform = False

                display = armature.data.edit_bones.new(plan.display_name)
                if display.name != plan.display_name:
                    raise LimbIKError(f"Blender renamed generated bone '{plan.display_name}'; build was rolled back.")
                transaction["bone_names"].append(display.name)
                display.head = plan.pole_head
                aim = plan.pole_joint - plan.pole_head
                if aim.length <= EPSILON:
                    aim = Vector((0.0, 1.0, 0.0))
                # Rain's helper is authored with local -Y aimed at the joint;
                # matching that rest orientation avoids a 180-degree Damped
                # Track singularity before the constraint is evaluated.
                display.tail = plan.pole_head - aim.normalized() * max((plan.end - plan.start).length * 0.06, 0.01)
                display.parent = pole
                display.use_connect = False
                display.use_deform = False

                if plan.chain.kind == "LEG":
                    heel = armature.data.edit_bones.new(plan.heel_name)
                    if heel.name != plan.heel_name:
                        raise LimbIKError(f"Blender renamed generated bone '{plan.heel_name}'; build was rolled back.")
                    transaction["bone_names"].append(heel.name)
                    heel.head = plan.heel_head
                    heel.tail = plan.heel_tail
                    heel.parent = target
                    heel.use_connect = False
                    heel.use_deform = False
                    heel.align_roll(plan.heel_z)

                    solver = armature.data.edit_bones.new(plan.solver_target_name)
                    if solver.name != plan.solver_target_name:
                        raise LimbIKError(f"Blender renamed generated bone '{plan.solver_target_name}'; build was rolled back.")
                    transaction["bone_names"].append(solver.name)
                    solver.head = plan.target_head
                    solver.tail = plan.target_tail
                    solver.parent = heel
                    solver.use_connect = False
                    solver.use_deform = False
                    solver.align_roll(plan.target_z)

        # Finish the topology edit before restoring the artist's symmetry flag;
        # restoring it while Edit Mode is live can itself mirror the last write.
        _mode_set(context, armature, "OBJECT")
    finally:
        armature.data.use_mirror_x = mirror_x

    # Commit the edited Armature topology through an evaluated Object-mode
    # boundary before PoseBone/constraint access.  Dense production rigs can
    # otherwise keep a stale depsgraph relation for the newly-created controls.
    armature.data.update_tag()
    armature.update_tag(refresh={"OBJECT"})
    context.view_layer.update()
    _mode_set(context, armature, "POSE")
    collection = _ensure_control_collection(armature, armature_id, transaction)
    if schema == ENHANCED_SCHEMA:
        master = armature.data.bones[MASTER_NAME]
        master.use_deform = False
        _tag(master, armature_id, role="MASTER")
        collection.assign(master)
    for plan in plans:
        target = armature.data.bones[plan.target_name]
        pole = armature.data.bones[plan.pole_name]
        target.use_deform = False
        pole.use_deform = False
        _tag(target, armature_id, role=LIMB_SPEC[plan.chain.kind]["target_role"], rig_id=plan.rig_id, kind=plan.chain.kind, side=plan.chain.side, chain=plan.chain.names)
        _tag(pole, armature_id, role="POLE", rig_id=plan.rig_id, kind=plan.chain.kind, side=plan.chain.side, chain=plan.chain.names)
        if plan.persist_pole_direction:
            pole[POLE_DIRECTION_KEY] = [float(component) for component in plan.pole_direction]
        collection.assign(target)
        collection.assign(pole)
        if schema == ENHANCED_SCHEMA:
            line = armature.data.bones[plan.line_name]
            display = armature.data.bones[plan.display_name]
            _tag(line, armature_id, role="POLE_LINE", rig_id=plan.rig_id, kind=plan.chain.kind, side=plan.chain.side, chain=plan.chain.names)
            _tag(display, armature_id, role="POLE_DISPLAY", rig_id=plan.rig_id, kind=plan.chain.kind, side=plan.chain.side, chain=plan.chain.names)
            line.use_deform = display.use_deform = False
            line.hide_select = True
            display.hide = True
            display.hide_select = True
            collection.assign(line)
            collection.assign(display)
            if plan.chain.kind == "LEG":
                heel = armature.data.bones[plan.heel_name]
                solver = armature.data.bones[plan.solver_target_name]
                _tag(heel, armature_id, role="HEEL_ROLL", rig_id=plan.rig_id, kind=plan.chain.kind, side=plan.chain.side, chain=plan.chain.names)
                _tag(solver, armature_id, role="FOOT_TARGET", rig_id=plan.rig_id, kind=plan.chain.kind, side=plan.chain.side, chain=plan.chain.names)
                heel.use_deform = solver.use_deform = False
                solver.hide = True
                solver.hide_select = True
                collection.assign(heel)
                collection.assign(solver)
    # BoneCollection assignment and Bone ID-property writes can invalidate the
    # production depsgraph a second time.  Rebuild it at an Object boundary so
    # IK relation creation sees BONE_DONE nodes for every new control.
    _mode_set(context, armature, "OBJECT")
    armature.data.update_tag()
    armature.update_tag(refresh={"OBJECT"})
    context.view_layer.update()
    context.evaluated_depsgraph_get().update()
    context.scene.frame_set(context.scene.frame_current)
    context.view_layer.update()
    _mode_set(context, armature, "POSE")
    context.view_layer.update()


def _create_constraint_shells(armature, armature_id, plans, transaction, *, schema=ENHANCED_SCHEMA, create_master=False):
    """Create exact constraint references before their future control bones.

    Blender's dense-rig depsgraph only creates same-Armature BONE_DONE nodes
    reliably when those references already exist as Edit Mode commits the new
    bones.  No evaluation is requested until `_create_control_bones` completes.
    """
    for plan in plans:
        lower = armature.pose.bones[plan.chain.lower]
        _remember_registry(transaction, lower)
        ik = lower.constraints.new(type="IK")
        ik.name = _constraint_name(plan.rig_id, "IK")
        ik.target = armature
        ik.subtarget = plan.solver_target_name if schema == ENHANCED_SCHEMA else plan.target_name
        ik.pole_target = armature
        ik.pole_subtarget = plan.pole_name
        ik.chain_count = 2
        ik.pole_angle = plan.pole_angle
        ik.target_space = "WORLD"
        ik.owner_space = "WORLD"
        if hasattr(ik, "use_tail"):
            ik.use_tail = True
        if hasattr(ik, "use_stretch"):
            ik.use_stretch = False
        transaction["constraints"].append((lower, ik))

def _create_constraints_and_shapes(context, armature, armature_id, plans, transaction, *, schema=ENHANCED_SCHEMA, create_master=False):
    widget_collection = _ensure_widget_collection(context, armature_id, transaction)
    if schema == LEGACY_SCHEMA:
        widgets = {"POLE": _ensure_widget(context, armature_id, widget_collection, "POLE", transaction, schema=schema)}
    else:
        widgets = {
            "POLE_ARROW": _ensure_widget(context, armature_id, widget_collection, "POLE_ARROW", transaction, schema=schema),
            "POLE_LINE": _ensure_widget(context, armature_id, widget_collection, "POLE_LINE", transaction, schema=schema),
            "MASTER": _ensure_widget(context, armature_id, widget_collection, "MASTER", transaction, schema=schema),
        }
    if any(plan.chain.kind == "ARM" for plan in plans):
        widgets["ARM"] = _ensure_widget(context, armature_id, widget_collection, "HAND", transaction, schema=schema)
    if any(plan.chain.kind == "LEG" for plan in plans):
        widgets["LEG"] = _ensure_widget(context, armature_id, widget_collection, "FOOT", transaction, schema=schema)
        if schema == ENHANCED_SCHEMA:
            widgets["HEEL"] = _ensure_widget(context, armature_id, widget_collection, "HEEL", transaction, schema=schema)

    pending_records = []
    runtime_constraints = {}
    if schema == ENHANCED_SCHEMA and create_master:
        roots = [bone for bone in armature.data.bones if bone.parent is None and bone.get(OWNER_KEY) != OWNER_VALUE]
        if not roots:
            raise LimbIKError("No unparented source root is available for the Master control.")
        for root in roots:
            pose_root = armature.pose.bones[root.name]
            _remember_registry(transaction, pose_root)
            follow = pose_root.constraints.new(type="COPY_TRANSFORMS")
            follow.name = _constraint_name(armature_id, "MASTER_FOLLOW")
            follow.target = armature
            follow.subtarget = MASTER_NAME
            follow.target_space = "POSE"
            follow.owner_space = "POSE"
            if hasattr(follow, "mix_mode"):
                follow.mix_mode = "BEFORE"
            transaction["constraints"].append((pose_root, follow))
            pending_records.append((pose_root, follow, None, "MASTER_FOLLOW"))
    for plan in plans:
        armature.pose.bones[plan.target_name].matrix_basis = plan.target_basis
        armature.pose.bones[plan.pole_name].matrix_basis = plan.pole_basis
        lower = armature.pose.bones[plan.chain.lower]
        end = armature.pose.bones[plan.chain.end]
        ik_name = _constraint_name(plan.rig_id, "IK")
        ik = lower.constraints.get(ik_name)
        if ik is None or ik.type != "IK":
            raise LimbIKError(f"{plan.chain.side} {plan.chain.kind.title()} IK shell disappeared while creating controls.")
        _remember_registry(transaction, end)
        copy_rotation = end.constraints.new(type="COPY_ROTATION")
        copy_rotation.name = _constraint_name(plan.rig_id, "END_ROTATION")
        copy_rotation.target = armature
        solver_name = plan.solver_target_name if schema == ENHANCED_SCHEMA else plan.target_name
        copy_rotation.subtarget = solver_name
        copy_rotation.target_space = "WORLD"
        copy_rotation.owner_space = "WORLD"
        if hasattr(copy_rotation, "mix_mode"):
            copy_rotation.mix_mode = "REPLACE"
        transaction["constraints"].append((end, copy_rotation))
        extras = []
        if schema == ENHANCED_SCHEMA:
            line = armature.pose.bones[plan.line_name]
            display = armature.pose.bones[plan.display_name]
            _remember_registry(transaction, line)
            stretch = line.constraints.new(type="STRETCH_TO")
            stretch.name = _constraint_name(plan.rig_id, "POLE_LINE_STRETCH")
            stretch.target = armature
            stretch.subtarget = plan.pole_name
            stretch.target_space = "WORLD"
            stretch.owner_space = "WORLD"
            if hasattr(stretch, "volume"):
                stretch.volume = "NO_VOLUME"
            transaction["constraints"].append((line, stretch))
            _remember_registry(transaction, display)
            track = display.constraints.new(type="DAMPED_TRACK")
            track.name = _constraint_name(plan.rig_id, "POLE_DISPLAY_TRACK")
            track.target = armature
            track.subtarget = plan.chain.lower
            track.track_axis = "TRACK_NEGATIVE_Y"
            track.target_space = "WORLD"
            track.owner_space = "WORLD"
            transaction["constraints"].append((display, track))
            extras.extend((stretch, track))
            if plan.chain.kind == "LEG":
                heel = armature.pose.bones[plan.heel_name]
                _remember_registry(transaction, heel)
                heel_limit = heel.constraints.new(type="LIMIT_ROTATION")
                heel_limit.name = _constraint_name(plan.rig_id, "HEEL_LIMIT")
                heel_limit.owner_space = "LOCAL"
                heel_limit.use_limit_x = True
                heel_limit.min_x = -math.pi * 0.5
                heel_limit.max_x = math.radians(130.0)
                transaction["constraints"].append((heel, heel_limit))
                extras.append(heel_limit)
        runtime_constraints[plan.rig_id] = (ik, copy_rotation, *extras)

    # Configure every same-Armature relation first, then rebuild the relation
    # graph once.  Creating and evaluating one side at a time leaves later
    # controls without BONE_DONE nodes on dense production rigs.
    _mode_set(context, armature, "OBJECT")
    armature.data.update_tag()
    armature.update_tag(refresh={"OBJECT"})
    context.scene.update_tag()
    context.view_layer.update()
    context.evaluated_depsgraph_get().update()
    _mode_set(context, armature, "POSE")
    context.view_layer.update()

    def set_shape(pose_bone, shape, scale, *, transform=None, translation=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0), mirror_x=False):
        pose_bone.custom_shape = shape
        pose_bone.custom_shape_transform = transform
        pose_bone.use_custom_shape_bone_size = False
        signed = -float(scale) if mirror_x else float(scale)
        pose_bone.custom_shape_scale_xyz = (signed, float(scale), float(scale))
        pose_bone.custom_shape_translation = translation
        pose_bone.custom_shape_rotation_euler = rotation
        if hasattr(pose_bone, "custom_shape_wire_width"):
            pose_bone.custom_shape_wire_width = 2.0

    if schema == ENHANCED_SCHEMA:
        master_pb = armature.pose.bones[MASTER_NAME]
        set_shape(master_pb, widgets["MASTER"], _master_bone_size(armature) * 2.8, rotation=(math.pi * 0.5, 0.0, 0.0))
    for plan in plans:
        lower = armature.pose.bones[plan.chain.lower]
        end = armature.pose.bones[plan.chain.end]
        target = armature.pose.bones[plan.target_name]
        pole = armature.pose.bones[plan.pole_name]
        chain_length = max((plan.joint - plan.start).length + (plan.end - plan.joint).length, 0.01)
        if schema == LEGACY_SCHEMA:
            target.custom_shape = widgets[plan.chain.kind]
            pole.custom_shape = widgets["POLE"]
            if hasattr(target, "custom_shape_wire_width"):
                target.custom_shape_wire_width = 2.0
                pole.custom_shape_wire_width = 2.0
        else:
            line = armature.pose.bones[plan.line_name]
            display = armature.pose.bones[plan.display_name]
            set_shape(pole, widgets["POLE_ARROW"], chain_length * 0.11, transform=display)
            line.custom_shape = widgets["POLE_LINE"]
            line.use_custom_shape_bone_size = True
            line.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
            if hasattr(line, "custom_shape_wire_width"):
                line.custom_shape_wire_width = 1.5
            pole.lock_rotation = (True, True, True)
            pole.lock_scale = (True, True, True)
            line.lock_location = line.lock_rotation = line.lock_scale = (True, True, True)
            display.lock_location = display.lock_rotation = display.lock_scale = (True, True, True)
            if plan.chain.kind == "ARM":
                set_shape(target, widgets["ARM"], chain_length * 0.24)
            else:
                foot_length = max((Vector(armature.pose.bones[plan.chain.end].tail) - Vector(armature.pose.bones[plan.chain.end].head)).length, chain_length * 0.12)
                set_shape(target, widgets["LEG"], foot_length, translation=(0.0, foot_length * 0.12, -foot_length * 0.08), mirror_x=plan.chain.side == "R")
                heel = armature.pose.bones[plan.heel_name]
                set_shape(heel, widgets["HEEL"], foot_length * 0.55)
                heel.rotation_mode = "XYZ"
                heel.lock_location = (True, True, True)
                heel.lock_scale = (True, True, True)
                heel.lock_rotation = (False, False, True)

        ik, copy_rotation, *extras = runtime_constraints[plan.rig_id]
        ik_name = _constraint_name(plan.rig_id, "IK")
        for index, (owner, constraint) in enumerate(transaction["constraints"]):
            if constraint.name == ik_name:
                transaction["constraints"][index] = (lower, ik)
                break
        if plan.preserve_pole_angle:
            # Transactional recovery must recreate the exact prior solver,
            # including pre-0.27 rigs that have no Pole Direction tag.
            ik.pole_angle = float(plan.pole_angle)
            context.view_layer.update()
        else:
            ik.pole_angle = _calibrate_pole_angle(context, armature, plan, ik)
        pending_records.append((lower, ik, plan, "IK"))

        copy_name = _constraint_name(plan.rig_id, "END_ROTATION")
        for index, (_owner, constraint) in enumerate(transaction["constraints"]):
            if constraint.name == copy_name:
                transaction["constraints"][index] = (end, copy_rotation)
                break
        context.view_layer.update()
        end_position_error = (Vector(end.head) - plan.desired_end_matrix.translation).length
        end_rotation_error = _rotation_error(end.matrix, plan.desired_end_matrix)
        if end_position_error > 2.0e-4 or end_rotation_error > 2.0e-3:
            raise LimbIKError(
                f"{plan.chain.side} {plan.chain.kind.title()} end controller could not preserve "
                f"the current Hand/Foot pose (position {end_position_error:.4g}, rotation {end_rotation_error:.4g})."
            )
        pending_records.append((end, copy_rotation, plan, "END_ROTATION"))
        if schema == ENHANCED_SCHEMA:
            line = armature.pose.bones[plan.line_name]
            display = armature.pose.bones[plan.display_name]
            stretch = next(item for item in extras if item.type == "STRETCH_TO")
            track = next(item for item in extras if item.type == "DAMPED_TRACK")
            pending_records.append((line, stretch, plan, "POLE_LINE_STRETCH"))
            pending_records.append((display, track, plan, "POLE_DISPLAY_TRACK"))
            if plan.chain.kind == "LEG":
                heel = armature.pose.bones[plan.heel_name]
                heel_limit = next(item for item in extras if item.type == "LIMIT_ROTATION")
                pending_records.append((heel, heel_limit, plan, "HEEL_LIMIT"))

    # PoseBone ID-property writes rebuild relation components on dense rigs.
    # Defer every registry write until all solver work and no-pop validation is
    # complete, then cross an Object boundary once before final inventory.
    for pose_bone, constraint, plan, role in pending_records:
        if role == "MASTER_FOLLOW":
            _record_master_constraint(pose_bone, constraint, armature_id)
        else:
            _record_constraint(pose_bone, constraint, plan, armature_id, role, schema=schema)
    _mode_set(context, armature, "OBJECT")
    armature.data.update_tag()
    armature.update_tag(refresh={"OBJECT"})
    context.scene.update_tag()
    context.view_layer.update()
    context.evaluated_depsgraph_get().update()
    _mode_set(context, armature, "POSE")
    context.view_layer.update()


def _rotation_error(matrix, desired):
    angle = float(matrix.to_quaternion().rotation_difference(desired.to_quaternion()).angle)
    if not math.isfinite(angle):
        return float("inf")
    # q and -q encode the same 3D rotation.  Blender may report their
    # difference as 2*pi, so always fold the result to the shortest [0, pi]
    # representative before using it in validation or Pole calibration.
    angle = abs(angle) % math.tau
    return min(angle, math.tau - angle)


def _pole_alignment_measure(armature, plan):
    upper = armature.pose.bones[plan.chain.upper]
    lower = armature.pose.bones[plan.chain.lower]
    pole = armature.pose.bones[plan.pole_name]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    chain_axis = end - start
    if chain_axis.length <= EPSILON:
        return None
    projection = start + chain_axis * (joint - start).dot(chain_axis) / chain_axis.length_squared
    bend = joint - projection
    pole_projection = _project_perpendicular(Vector(pole.head) - projection, chain_axis)
    if min(bend.length, pole_projection.length) <= EPSILON:
        return None
    bend.normalize()
    pole_projection.normalize()
    return max(-1.0, min(1.0, bend.dot(pole_projection)))


def _pole_angle_domain(constraint):
    """Return the finite RNA hard range accepted by IK Pole Angle."""
    fallback = (-math.pi, math.pi)
    try:
        properties = constraint.bl_rna.properties
        try:
            prop = properties.get("pole_angle")
        except AttributeError:
            prop = properties["pole_angle"]
        lower = float(prop.hard_min)
        upper = float(prop.hard_max)
    except (AttributeError, KeyError, TypeError, ValueError):
        return fallback
    if not all(math.isfinite(value) for value in (lower, upper)) or lower >= upper:
        return fallback
    return lower, upper


def _calibrate_pole_angle(context, armature, plan, constraint):
    """Make Blender's evaluated joint bend toward the visible Pole control.

    Pole Angle still has to compensate arbitrary source-bone roll, but it must
    never compensate the control back to a different modeled bend plane.  The
    evaluated solver is therefore optimized for bend/Pole alignment itself.
    """
    lower_limit, upper_limit = _pole_angle_domain(constraint)

    def set_angle(angle):
        requested = max(lower_limit, min(upper_limit, float(angle)))
        constraint.pole_angle = requested
        actual = float(constraint.pole_angle)
        if not math.isfinite(actual):
            raise LimbIKError(f"{plan.chain.side} {plan.chain.kind.title()} Pole Angle became non-finite.")
        return actual

    analytic_angle = set_angle(plan.pole_angle)
    context.view_layer.update()
    analytic_alignment = _pole_alignment_measure(armature, plan)
    target = armature.pose.bones[plan.target_name]
    total = (plan.joint - plan.start).length + (plan.end - plan.joint).length
    target_reach = (Vector(target.head) - plan.start).length
    effectively_extended = total - target_reach <= max(EPSILON, total * 1.0e-6)
    if not effectively_extended and analytic_alignment is not None and analytic_alignment >= 0.999:
        return analytic_angle

    samples = 64
    step = (upper_limit - lower_limit) / samples
    best_angle = analytic_angle
    best_error = float("inf") if analytic_alignment is None else 1.0 - analytic_alignment
    target_basis = target.matrix_basis.copy()
    used_probe = False

    def evaluate(angle):
        actual = set_angle(angle)
        context.view_layer.update()
        alignment = _pole_alignment_measure(armature, plan)
        error = float("inf") if alignment is None else 1.0 - alignment
        return actual, error

    try:
        # A completely extended two-bone chain has no visible residual with
        # which Blender can expose its Pole convention.  Retract the target a
        # tiny amount only for calibration, then restore its exact Pose basis.
        set_angle(plan.pole_angle)
        context.view_layer.update()
        if effectively_extended or _pole_alignment_measure(armature, plan) is None:
            target_matrix = target.matrix.copy()
            toward_root = plan.start - Vector(target.head)
            if toward_root.length <= EPSILON or total <= EPSILON:
                raise LimbIKError(f"{plan.chain.side} {plan.chain.kind.title()} has no usable Pole calibration probe.")
            target_matrix.translation += toward_root.normalized() * total * 0.02
            target.matrix = target_matrix
            context.view_layer.update()
            used_probe = True
            # The objective is now measured on a deliberately different,
            # reachable pose.  Do not compare its candidates with an
            # alignment/error sampled before the temporary retraction.
            best_error = float("inf")

        # Pole Angle is a hard-clamped RNA property, not an unbounded periodic
        # scalar.  Always sample its complete legal interval.  A sweep centered
        # on the analytic seed can silently collapse out-of-range candidates to
        # one boundary and omit the opposite half of the valid domain.
        seen_angles = []
        for index in range(samples + 1):
            requested = lower_limit + index * step
            actual, error = evaluate(requested)
            if any(abs(actual - seen) <= 1.0e-12 for seen in seen_angles):
                continue
            seen_angles.append(actual)
            if error < best_error:
                best_angle, best_error = actual, error
        if not math.isfinite(best_error):
            raise LimbIKError(f"{plan.chain.side} {plan.chain.kind.title()} Pole direction could not be evaluated.")

        # Refine only inside the accepted RNA domain.  Keep the coarse result
        # unless an actually evaluated refinement is better.
        left = max(lower_limit, best_angle - step)
        right = min(upper_limit, best_angle + step)
        golden = (math.sqrt(5.0) - 1.0) * 0.5
        x1 = right - golden * (right - left)
        x2 = left + golden * (right - left)
        a1, f1 = evaluate(x1)
        a2, f2 = evaluate(x2)
        refined_angle, refined_error = best_angle, best_error
        if f1 < refined_error:
            refined_angle, refined_error = a1, f1
        if f2 < refined_error:
            refined_angle, refined_error = a2, f2
        for _index in range(22):
            if f1 <= f2:
                right, x2, a2, f2 = x2, x1, a1, f1
                x1 = right - golden * (right - left)
                a1, f1 = evaluate(x1)
                if f1 < refined_error:
                    refined_angle, refined_error = a1, f1
            else:
                left, x1, a1, f1 = x1, x2, a2, f2
                x2 = left + golden * (right - left)
                a2, f2 = evaluate(x2)
                if f2 < refined_error:
                    refined_angle, refined_error = a2, f2
        if refined_error < best_error:
            best_angle, best_error = refined_angle, refined_error
        set_angle(best_angle)
        calibrated_alignment = _pole_alignment_measure(armature, plan)
        if calibrated_alignment is None or calibrated_alignment < 0.999:
            alignment_label = (
                "undefined" if calibrated_alignment is None else f"{calibrated_alignment:.6f}"
            )
            raise LimbIKError(
                f"{plan.chain.side} {plan.chain.kind.title()} could not align its real joint bend to the "
                f"configured Pole direction (alignment {alignment_label}, analytic {analytic_alignment})."
            )
    finally:
        if used_probe:
            target.matrix_basis = target_basis
        context.view_layer.update()

    final_alignment = _pole_alignment_measure(armature, plan)
    # At exact full extension the restored chain has no meaningful bend plane;
    # tiny evaluated residuals can consequently point anywhere.  The temporary
    # probe was validated strictly above while its plane was measurable.
    if not used_probe and (final_alignment is None or final_alignment < 0.999):
        alignment_label = "undefined" if final_alignment is None else f"{final_alignment:.6f}"
        raise LimbIKError(
            f"{plan.chain.side} {plan.chain.kind.title()} could not align its real joint bend to the configured Pole "
            f"direction (alignment {alignment_label}, analytic {analytic_alignment})."
        )
    return float(constraint.pole_angle)


def _build_plans(context, armature, plans, *, schema=ENHANCED_SCHEMA, desired_source_pose=None):
    inventory = _validate_inventory(armature)
    _preflight_plans(context, armature, plans, inventory, schema=schema)
    missing = [plan for plan in plans if (plan.chain.kind, plan.chain.side) not in inventory["rigs"]]
    if not missing:
        raise LimbIKError("The requested Limb IK rig already exists; use Rebuild Rig to replace it.")
    transaction = _new_transaction()
    armature_id = inventory["armature_id"]
    create_master = schema == ENHANCED_SCHEMA and inventory.get("master") is None
    source_pose_before = desired_source_pose or {
        bone.name: armature.pose.bones[bone.name].matrix.copy()
        for bone in armature.data.bones
        if bone.get(OWNER_KEY) != OWNER_VALUE
    }
    try:
        if not armature_id:
            armature_id = uuid.uuid4().hex
            armature.data[ARMATURE_ID_KEY] = armature_id
            transaction["new_armature_id"] = True
        if schema == ENHANCED_SCHEMA and armature.data.get(SCHEMA_KEY) != ENHANCED_SCHEMA:
            armature.data[SCHEMA_KEY] = ENHANCED_SCHEMA
            transaction["new_schema"] = True
        _create_constraint_shells(armature, armature_id, missing, transaction, schema=schema, create_master=create_master)
        _create_control_bones(context, armature, armature_id, missing, transaction, schema=schema, create_master=create_master)
        _create_constraints_and_shapes(context, armature, armature_id, missing, transaction, schema=schema, create_master=create_master)
        verified = _validate_inventory(armature)
        if verified["schema"] != schema:
            raise LimbIKError("Generated Limb IK schema did not pass ownership verification.")
        for plan in missing:
            if (plan.chain.kind, plan.chain.side) not in verified["rigs"]:
                raise LimbIKError(f"Generated {plan.chain.side} {plan.chain.kind.title()} rig did not pass ownership verification.")
        context.view_layer.update()
        replanned_bones = {
            name
            for plan in missing
            if not plan.preserve_pole_angle
            for name in (plan.chain.upper, plan.chain.lower)
        }
        for name, desired in source_pose_before.items():
            # An explicit Pole direction intentionally re-planes the two-bone
            # joint.  The Hand/Foot endpoint and every unrelated source bone
            # remain protected by the same strict validation as before.
            if name in replanned_bones:
                continue
            current = armature.pose.bones.get(name)
            if current is None:
                raise LimbIKError(f"Source bone '{name}' disappeared while building Limb IK.")
            position_error = (current.matrix.translation - desired.translation).length
            rotation_error = _rotation_error(current.matrix, desired)
            if position_error > 4.0e-4 or rotation_error > 3.0e-3:
                raise LimbIKError(
                    f"Master/IK setup could not preserve source pose on '{name}' "
                    f"(position {position_error:.4g}, rotation {rotation_error:.4g})."
                )
        return missing, transaction
    except (LimbIKError, ReferenceError, RuntimeError, TypeError, ValueError) as exc:
        rollback_errors = _rollback_build(context, armature, transaction)
        if rollback_errors:
            raise LimbIKError(f"{exc} Rollback also reported: {'; '.join(rollback_errors)}") from exc
        raise


def _plans_for_kind(context, armature, settings, kind):
    chains = []
    for side in SIDES:
        chain = _chain_from_settings(settings, armature, kind, side)
        if chain is not None:
            chains.append(chain)
    if not chains:
        raise LimbIKError(f"No complete high-confidence {kind.title()} chain is available; Analyze or choose bones manually.")
    _mode_set(context, armature, "POSE")
    return [
        _build_plan(
            armature,
            chain,
            settings.pole_distance_ratio,
            _configured_pole_direction(settings, chain.kind, chain.side),
        )
        for chain in chains
    ]


def _plans_for_selected(context, armature, settings):
    kind, side = SELECTED_LIMBS.get(settings.selected_limb, ("", ""))
    if kind not in KINDS or side not in SIDES:
        raise LimbIKError("Choose one Arm or Leg before building IK.")
    chain = _chain_from_settings(settings, armature, kind, side)
    if chain is None:
        raise LimbIKError(
            f"No complete {side} {kind.title()} chain is available; Analyze or choose all three bones manually."
        )
    _mode_set(context, armature, "POSE")
    return [
        _build_plan(
            armature,
            chain,
            settings.pole_distance_ratio,
            _configured_pole_direction(settings, chain.kind, chain.side),
        )
    ]


def _plans_for_all(context, armature, settings):
    """Plan every populated limb before the one atomic Build All mutation."""
    chains = []
    for kind in KINDS:
        for side in SIDES:
            # Fully blank, low-confidence chains remain intentionally absent.
            # A partly filled chain raises here, before _build_plans can mutate
            # any Armature data, so Build All always fails closed.
            chain = _chain_from_settings(settings, armature, kind, side)
            if chain is not None:
                chains.append(chain)
    if not chains:
        raise LimbIKError("No complete Arm or Leg chain is available; Analyze or choose bones manually.")
    _mode_set(context, armature, "POSE")
    return [
        _build_plan(
            armature,
            chain,
            settings.pole_distance_ratio,
            _configured_pole_direction(settings, chain.kind, chain.side),
        )
        for chain in chains
    ]


def _plans_for_exact_keys(context, armature, settings, keys):
    """Plan exactly the generated sides requested by Rebuild, never siblings."""
    chains = []
    for kind, side in keys:
        chain = _chain_from_settings(settings, armature, kind, side)
        if chain is None:
            raise LimbIKError(
                f"No complete {side} {kind.title()} chain is available for Rebuild; Analyze or choose all three bones."
            )
        chains.append(chain)
    if not chains:
        raise LimbIKError("No generated Limb IK side is available for Rebuild.")
    _mode_set(context, armature, "POSE")
    return [
        _build_plan(
            armature,
            chain,
            settings.pole_distance_ratio,
            _configured_pole_direction(settings, chain.kind, chain.side),
        )
        for chain in chains
    ]


def _validate_master_build_scale(scale):
    values = tuple(float(value) for value in scale)
    if len(values) != 3 or any(not math.isfinite(value) for value in values):
        raise LimbIKError("Master scale must be finite before adding or rebuilding Limb IK controls.")
    if any(value <= 1.0e-6 for value in values):
        raise LimbIKError("Use a positive, non-zero Master scale before adding or rebuilding Limb IK controls.")
    tolerance = 1.0e-5 * max(1.0, max(abs(value) for value in values))
    if max(values) - min(values) > tolerance:
        raise LimbIKError("Use uniform Master scale before adding or rebuilding Limb IK controls.")


def _neutralize_existing_master(context, armature, *, validate_scale=True):
    """Temporarily remove global transport while deriving new rest controls."""
    inventory = _validate_inventory(armature)
    if inventory.get("schema") != ENHANCED_SCHEMA or inventory.get("master") is None:
        return None
    pose_bone = armature.pose.bones[MASTER_NAME]
    if validate_scale:
        _validate_master_build_scale(pose_bone.scale)
    state = {"rotation_mode": pose_bone.rotation_mode, "matrix_basis": pose_bone.matrix_basis.copy()}
    pose_bone.matrix_basis = Matrix.Identity(4)
    context.view_layer.update()
    return state


def _restore_master_state(context, armature, state):
    if state is None:
        return
    pose_bone = armature.pose.bones.get(MASTER_NAME)
    if pose_bone is None:
        raise LimbIKError("The Master control disappeared while restoring its pose.")
    pose_bone.rotation_mode = state["rotation_mode"]
    pose_bone.matrix_basis = state["matrix_basis"]
    context.view_layer.update()


def _actions_for_id(id_block):
    animation = getattr(id_block, "animation_data", None)
    if animation is None:
        return ()
    actions = []
    if animation.action is not None:
        actions.append(animation.action)
    for track in animation.nla_tracks:
        for strip in track.strips:
            if strip.action is not None:
                actions.append(strip.action)
    return tuple(dict.fromkeys(actions))


def _fcurves_for_action(action):
    if hasattr(action, "fcurves"):
        return tuple(action.fcurves)
    # Blender 4.4+ layered Actions expose channelbags instead of action.fcurves.
    result = []
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                result.extend(channelbag.fcurves)
    return tuple(result)


def _path_mentions_bone(data_path, names):
    return any(f'pose.bones["{name.replace(chr(34), chr(92) + chr(34))}"]' in data_path for name in names)


def _rna_escape(name):
    return name.replace("\\", "\\\\").replace('"', '\\"')


def _owned_constraint_path(pose_bone_name, constraint_name):
    return f'pose.bones["{_rna_escape(pose_bone_name)}"].constraints["{_rna_escape(constraint_name)}"]'


def _constraint_references_controls(constraint, armature, names):
    if getattr(constraint, "target", None) is armature and getattr(constraint, "subtarget", "") in names:
        return True
    if getattr(constraint, "pole_target", None) is armature and getattr(constraint, "pole_subtarget", "") in names:
        return True
    for target in getattr(constraint, "targets", ()):
        if getattr(target, "target", None) is armature and getattr(target, "subtarget", "") in names:
            return True
    return False


def _foreign_dependency_problems(armature, inventory):
    names = {bone.name for bone in inventory["bones"]}
    if not names:
        return []
    owned_constraints = {(armature.as_pointer(), pose_bone.as_pointer(), constraint.as_pointer()) for pose_bone, constraint, _record in inventory["records"]}
    owned_constraint_paths = {
        _owned_constraint_path(pose_bone.name, constraint.name)
        for pose_bone, constraint, _record in inventory["records"]
    }
    problems = []
    for bone in armature.data.bones:
        if bone.name not in names and bone.parent is not None and bone.parent.name in names:
            problems.append(f"bone '{bone.name}' is parented to generated '{bone.parent.name}'")
    for rig_object in (obj for obj in bpy.data.objects if obj.type == "ARMATURE" and obj.pose is not None):
        for pose_bone in rig_object.pose.bones:
            for constraint in pose_bone.constraints:
                if (rig_object.as_pointer(), pose_bone.as_pointer(), constraint.as_pointer()) in owned_constraints:
                    continue
                references = _constraint_references_controls(constraint, armature, names)
                if references or (rig_object is armature and pose_bone.name in names):
                    problems.append(f"foreign constraint '{constraint.name}' on '{rig_object.name}:{pose_bone.name}' references/edits generated controls")
            if not (rig_object is armature and pose_bone.name in names) and pose_bone.custom_shape is not None and _owned(pose_bone.custom_shape, inventory["armature_id"], role="WIDGET"):
                problems.append(f"bone '{rig_object.name}:{pose_bone.name}' uses an owned widget as a foreign Custom Shape")
            if (
                rig_object is armature
                and pose_bone.name not in names
                and pose_bone.custom_shape_transform is not None
                and pose_bone.custom_shape_transform.name in names
            ):
                problems.append(f"bone '{rig_object.name}:{pose_bone.name}' uses a generated control as Custom Shape Transform")
    for obj in bpy.data.objects:
        if obj is not armature and obj.parent is armature and obj.parent_type == "BONE" and obj.parent_bone in names:
            problems.append(f"Object '{obj.name}' is bone-parented to generated control '{obj.parent_bone}'")
        for constraint in obj.constraints:
            if _constraint_references_controls(constraint, armature, names):
                problems.append(f"foreign Object constraint '{constraint.name}' on '{obj.name}' references a generated control")
    for id_block in (armature, armature.data):
        for action in _actions_for_id(id_block):
            for fcurve in _fcurves_for_action(action):
                if _path_mentions_bone(fcurve.data_path, names):
                    problems.append(f"Action '{action.name}' animates a generated control")
                    break
                if any(fcurve.data_path.startswith(path) for path in owned_constraint_paths):
                    problems.append(f"Action '{action.name}' animates an owned Limb IK constraint")
                    break
        animation = getattr(id_block, "animation_data", None)
        for fcurve in getattr(animation, "drivers", ()) if animation else ():
            if _path_mentions_bone(fcurve.data_path, names):
                problems.append("a driver writes to a generated control")
            if any(fcurve.data_path.startswith(path) for path in owned_constraint_paths):
                problems.append("a driver writes to an owned Limb IK constraint")
            for variable in fcurve.driver.variables:
                for target in variable.targets:
                    target_path = getattr(target, "data_path", "")
                    if target.id is armature and (
                        getattr(target, "bone_target", "") in names
                        or _path_mentions_bone(target_path, names)
                        or any(target_path.startswith(path) for path in owned_constraint_paths)
                    ):
                        problems.append("a driver reads a generated control")
    for obj in bpy.data.objects:
        animation = obj.animation_data
        for fcurve in getattr(animation, "drivers", ()) if animation else ():
            for variable in fcurve.driver.variables:
                for target in variable.targets:
                    target_path = getattr(target, "data_path", "")
                    if target.id is armature and (
                        getattr(target, "bone_target", "") in names
                        or _path_mentions_bone(target_path, names)
                        or any(target_path.startswith(path) for path in owned_constraint_paths)
                    ):
                        problems.append(f"driver on '{obj.name}' reads a generated control")
    control_collection = next((collection for collection in armature.data.collections if _owned(collection, inventory["armature_id"], role="CONTROL_COLLECTION")), None)
    if control_collection is not None:
        foreign_members = [bone.name for bone in control_collection.bones if bone.name not in names]
        if foreign_members:
            problems.append(f"Randy Controls contains foreign bones: {', '.join(foreign_members[:3])}")
    return sorted(set(problems))


def _removal_resources(context, armature, inventory):
    """Validate every deletion target before the first destructive operation."""
    armature_id = inventory["armature_id"]
    control_collections = [collection for collection in armature.data.collections if _owned(collection, armature_id, role="CONTROL_COLLECTION")]
    if len(control_collections) != 1:
        raise LimbIKError("Owned Randy Controls bone collection is missing or duplicated.")
    expected_bones = {bone.name for bone in inventory["bones"]}
    if {bone.name for bone in control_collections[0].bones} != expected_bones:
        raise LimbIKError("Randy Controls contains missing or foreign bones.")

    widget_collections = [collection for collection in bpy.data.collections if _owned(collection, armature_id, role="WIDGET_COLLECTION")]
    if len(widget_collections) != 1:
        raise LimbIKError("Owned widget collection is missing or duplicated.")
    widget_collection = widget_collections[0]
    if _collection_scene_memberships(widget_collection) != (context.scene,):
        raise LimbIKError("Owned widget collection is linked outside the current Scene.")
    if tuple(widget_collection.children):
        raise LimbIKError("Owned widget collection contains foreign child collections.")
    widget_objects = [obj for obj in bpy.data.objects if _owned(obj, armature_id, role="WIDGET")]
    if set(widget_collection.objects) != set(widget_objects):
        raise LimbIKError("Owned widget collection contains missing or foreign objects.")
    expected_kinds = {"POLE"} if inventory["schema"] == LEGACY_SCHEMA else {"POLE_ARROW", "POLE_LINE", "MASTER"}
    if any(kind == "ARM" for kind, _side in inventory["rigs"]):
        expected_kinds.add("HAND")
    if any(kind == "LEG" for kind, _side in inventory["rigs"]):
        expected_kinds.add("FOOT")
        if inventory["schema"] == ENHANCED_SCHEMA:
            expected_kinds.add("HEEL")
    if {obj.get(KIND_KEY) for obj in widget_objects} != expected_kinds or len(widget_objects) != len(expected_kinds):
        raise LimbIKError("Owned widget object set does not match the generated Limb rigs.")
    widget_meshes = []
    for obj in widget_objects:
        if tuple(obj.users_collection) != (widget_collection,) or obj.type != "MESH":
            raise LimbIKError(f"Owned widget '{obj.name}' has foreign links or changed type.")
        mesh = obj.data
        if not _owned(mesh, armature_id, role="WIDGET_DATA") or mesh.get(KIND_KEY) != obj.get(KIND_KEY) or mesh.users != 1:
            raise LimbIKError(f"Owned widget data '{mesh.name}' has invalid ownership or foreign users.")
        widget_meshes.append(mesh)
    widget_by_kind = {obj.get(KIND_KEY): obj for obj in widget_objects}
    if inventory["schema"] == ENHANCED_SCHEMA and armature.pose.bones[MASTER_NAME].custom_shape is not widget_by_kind["MASTER"]:
        raise LimbIKError("Generated Master Custom Shape assignment was edited.")
    for (kind, _side), rig in inventory["rigs"].items():
        target_pose = armature.pose.bones[rig["target"].name]
        pole_pose = armature.pose.bones[rig["pole"].name]
        expected_pole = "POLE" if inventory["schema"] == LEGACY_SCHEMA else "POLE_ARROW"
        if target_pose.custom_shape is not widget_by_kind["HAND" if kind == "ARM" else "FOOT"] or pole_pose.custom_shape is not widget_by_kind[expected_pole]:
            raise LimbIKError(f"Generated {kind.title()} Custom Shape assignment was edited.")
        if inventory["schema"] == ENHANCED_SCHEMA:
            transform = pole_pose.custom_shape_transform
            if armature.pose.bones[rig["line"].name].custom_shape is not widget_by_kind["POLE_LINE"] or transform is None or transform.name != rig["display"].name:
                raise LimbIKError(f"Generated {kind.title()} Pole display assignment was edited.")
            if kind == "LEG" and armature.pose.bones[rig["heel"].name].custom_shape is not widget_by_kind["HEEL"]:
                raise LimbIKError("Generated Leg Heel Roll Custom Shape assignment was edited.")
    return {
        "control_collection": control_collections[0],
        "widget_collection": widget_collection,
        "widget_objects": tuple(widget_objects),
        "widget_meshes": tuple(widget_meshes),
    }


def _snapshot_owned_rig(armature, inventory):
    plans = []
    control_pose = {}
    for (kind, side), rig in sorted(inventory["rigs"].items()):
        target = rig["target"]
        pole = rig["pole"]
        upper = armature.pose.bones[rig["chain"][0]]
        lower = armature.pose.bones[rig["chain"][1]]
        end_bone = armature.pose.bones[rig["chain"][2]]
        ik = next(constraint for _pose_bone, constraint, record in rig["entries"] if record["role"] == "IK")
        plans.append(
            LimbPlan(
                chain=LimbChain(kind, side, *rig["chain"]),
                rig_id=rig["rig_id"],
                target_name=target.name,
                pole_name=pole.name,
                start=Vector(upper.head),
                joint=Vector(lower.head),
                end=Vector(lower.tail),
                target_head=Vector(target.head_local),
                target_tail=Vector(target.tail_local),
                target_z=Vector(target.matrix_local.col[2][:3]),
                pole_head=Vector(pole.head_local),
                pole_tail=Vector(pole.tail_local),
                pole_angle=float(ik.pole_angle),
                pole_warning="",
                pole_direction=(
                    rig["pole_direction"].copy()
                    if rig["pole_direction"] is not None
                    else Vector(DEFAULT_POLE_DIRECTIONS[(kind, side)])
                ),
                pole_joint=Vector(lower.head),
                desired_upper_matrix=upper.matrix.copy(),
                desired_lower_matrix=lower.matrix.copy(),
                desired_end_matrix=end_bone.matrix.copy(),
                target_basis=armature.pose.bones[target.name].matrix_basis.copy(),
                pole_basis=armature.pose.bones[pole.name].matrix_basis.copy(),
                line_name=rig["line"].name if rig["line"] is not None else "",
                display_name=rig["display"].name if rig["display"] is not None else "",
                heel_name=rig["heel"].name if rig["heel"] is not None else "",
                solver_target_name=rig["solver_target"].name,
                heel_head=Vector(rig["heel"].head_local) if rig["heel"] is not None else None,
                heel_tail=Vector(rig["heel"].tail_local) if rig["heel"] is not None else None,
                heel_z=Vector(rig["heel"].matrix_local.col[2][:3]) if rig["heel"] is not None else None,
                persist_pole_direction=rig["pole_direction"] is not None,
                preserve_pole_angle=True,
            )
        )
    for bone in inventory["bones"]:
        pose_bone = armature.pose.bones[bone.name]
        control_pose[bone.name] = {
            "matrix_basis": pose_bone.matrix_basis.copy(),
            "rotation_mode": pose_bone.rotation_mode,
        }
    widget_geometry = {}
    for obj in bpy.data.objects:
        if _owned(obj, inventory["armature_id"], role="WIDGET"):
            widget_geometry[obj.get(KIND_KEY)] = {
                "vertices": tuple(tuple(vertex.co) for vertex in obj.data.vertices),
                "edges": tuple(tuple(edge.vertices) for edge in obj.data.edges),
            }
    return {
        "armature_id": inventory["armature_id"],
        "schema": inventory["schema"],
        "plans": plans,
        "control_pose": control_pose,
        "widget_geometry": widget_geometry,
        "constraint_names": {constraint.name for _pose_bone, constraint, _record in inventory["records"]},
        "source_pose": {
            bone.name: armature.pose.bones[bone.name].matrix.copy()
            for bone in armature.data.bones
            if bone.get(OWNER_KEY) != OWNER_VALUE
        },
    }


def _purge_snapshot_owned(context, armature, snapshot):
    """Best-effort exact cleanup used only before transactional recovery."""
    constraint_names = set(snapshot.get("constraint_names", ()))
    armature_id = snapshot["armature_id"]
    purge_ids = {armature_id}
    live_armature_id = armature.data.get(ARMATURE_ID_KEY, "")
    if isinstance(live_armature_id, str) and live_armature_id:
        purge_ids.add(live_armature_id)
    _mode_set(context, armature, "POSE")
    for pose_bone in armature.pose.bones:
        registry = _constraint_registry(pose_bone, strict=False)
        for constraint in tuple(pose_bone.constraints):
            record = registry.get(constraint.name, {})
            if constraint.name in constraint_names or (
                isinstance(record, dict)
                and record.get("owner") == OWNER_VALUE
                and record.get("armature_id") in purge_ids
            ):
                name = constraint.name
                pose_bone.constraints.remove(constraint)
                registry.pop(name, None)
        _write_constraint_registry(pose_bone, registry)
    _mode_set(context, armature, "EDIT")
    for bone in tuple(armature.data.edit_bones):
        if bone.get(OWNER_KEY) == OWNER_VALUE and bone.get(ARMATURE_ID_KEY) in purge_ids:
            armature.data.edit_bones.remove(bone)
    _mode_set(context, armature, "OBJECT")
    for obj in tuple(bpy.data.objects):
        if obj.get(OWNER_KEY) == OWNER_VALUE and obj.get(ARMATURE_ID_KEY) in purge_ids and obj.get(ROLE_KEY) == "WIDGET":
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in tuple(bpy.data.meshes):
        if mesh.get(OWNER_KEY) == OWNER_VALUE and mesh.get(ARMATURE_ID_KEY) in purge_ids and mesh.get(ROLE_KEY) == "WIDGET_DATA" and not mesh.users:
            bpy.data.meshes.remove(mesh)
    for collection in tuple(bpy.data.collections):
        if collection.get(OWNER_KEY) == OWNER_VALUE and collection.get(ARMATURE_ID_KEY) in purge_ids and collection.get(ROLE_KEY) == "WIDGET_COLLECTION":
            bpy.data.collections.remove(collection)
    for collection in tuple(armature.data.collections):
        if collection.get(OWNER_KEY) == OWNER_VALUE and collection.get(ARMATURE_ID_KEY) in purge_ids and collection.get(ROLE_KEY) == "CONTROL_COLLECTION":
            armature.data.collections.remove(collection)
    if ARMATURE_ID_KEY in armature.data:
        del armature.data[ARMATURE_ID_KEY]
    if SCHEMA_KEY in armature.data:
        del armature.data[SCHEMA_KEY]


def _restore_owned_snapshot(context, armature, snapshot):
    _purge_snapshot_owned(context, armature, snapshot)
    armature.data[ARMATURE_ID_KEY] = snapshot["armature_id"]
    if snapshot["schema"] == ENHANCED_SCHEMA:
        armature.data[SCHEMA_KEY] = ENHANCED_SCHEMA
    transaction = None
    try:
        _mode_set(context, armature, "POSE")
        _built, transaction = _build_plans(
            context,
            armature,
            snapshot["plans"],
            schema=snapshot["schema"],
            desired_source_pose=snapshot.get("source_pose"),
        )
        for name, state in snapshot["control_pose"].items():
            pose_bone = armature.pose.bones[name]
            pose_bone.rotation_mode = state["rotation_mode"]
            pose_bone.matrix_basis = state["matrix_basis"]
        for obj in bpy.data.objects:
            if not _owned(obj, snapshot["armature_id"], role="WIDGET"):
                continue
            geometry = snapshot["widget_geometry"].get(obj.get(KIND_KEY))
            if geometry is None:
                continue
            obj.data.clear_geometry()
            obj.data.from_pydata(geometry["vertices"], geometry["edges"], ())
            obj.data.update()
        context.view_layer.update()
        _validate_inventory(armature)
        return transaction
    except Exception:
        if transaction is not None:
            _rollback_build(context, armature, transaction)
        if ARMATURE_ID_KEY in armature.data:
            del armature.data[ARMATURE_ID_KEY]
        if SCHEMA_KEY in armature.data:
            del armature.data[SCHEMA_KEY]
        raise


def _remove_owned(context, armature, *, refuse_dependencies=True):
    inventory = _validate_inventory(armature)
    if not inventory["rigs"]:
        raise LimbIKError("No exactly tagged Limb IK rig exists on the active Armature.")
    if refuse_dependencies:
        problems = _foreign_dependency_problems(armature, inventory)
        if problems:
            raise LimbIKError(f"Remove Generated Rig was refused: {problems[0]}.")
    resources = _removal_resources(context, armature, inventory)
    armature_id = inventory["armature_id"]
    removed_constraints = 0
    _mode_set(context, armature, "POSE")
    for pose_bone, constraint, _record in reversed(inventory["records"]):
        registry = _constraint_registry(pose_bone, strict=True)
        name = constraint.name
        pose_bone.constraints.remove(constraint)
        registry.pop(name, None)
        _write_constraint_registry(pose_bone, registry)
        removed_constraints += 1
    _mode_set(context, armature, "EDIT")
    removed_bones = 0
    for name in [bone.name for bone in inventory["bones"]]:
        edit_bone = armature.data.edit_bones.get(name)
        if edit_bone is not None:
            armature.data.edit_bones.remove(edit_bone)
            removed_bones += 1
    _mode_set(context, armature, "OBJECT")

    widget_objects = resources["widget_objects"]
    widget_meshes = resources["widget_meshes"]
    for obj in widget_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in widget_meshes:
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
    bpy.data.collections.remove(resources["widget_collection"])
    armature.data.collections.remove(resources["control_collection"])
    if ARMATURE_ID_KEY in armature.data:
        del armature.data[ARMATURE_ID_KEY]
    if SCHEMA_KEY in armature.data:
        del armature.data[SCHEMA_KEY]
    return {"constraints": removed_constraints, "bones": removed_bones, "widgets": len(widget_objects)}


def _execute_build(operator, context, scope):
    settings = _settings(context)
    armature = None
    snapshot = None
    transaction = None
    built = ()
    error = None
    master_state = None
    try:
        armature = _require_active_armature(context, settings)
        snapshot = _capture_context(context, armature)
        master_state = _neutralize_existing_master(context, armature)
        if scope == "SELECTED":
            plans = _plans_for_selected(context, armature, settings)
        elif scope == "ALL":
            plans = _plans_for_all(context, armature, settings)
        elif scope in KINDS:
            # Kept for the registered 0.25/0.26 compatibility operators.
            plans = _plans_for_kind(context, armature, settings, scope)
        else:
            raise LimbIKError("Unknown Limb IK build scope.")
        built, transaction = _build_plans(context, armature, plans)
    except (LimbIKError, ReferenceError, RuntimeError, TypeError, ValueError) as exc:
        error = exc
    if master_state is not None and armature is not None:
        try:
            _restore_master_state(context, armature, master_state)
        except (LimbIKError, ReferenceError, RuntimeError, TypeError, ValueError) as restore_master_exc:
            if transaction is not None:
                rollback_errors = _rollback_build(context, armature, transaction)
                transaction = None
                suffix = f" Rollback also reported: {'; '.join(rollback_errors)}" if rollback_errors else ""
                error = LimbIKError(f"Master pose restoration failed, so the generated rig was rolled back: {restore_master_exc}.{suffix}")
            elif error is None:
                error = restore_master_exc
    if snapshot is not None and armature is not None:
        try:
            _restore_context(context, armature, snapshot)
        except (LimbIKError, ReferenceError, RuntimeError) as restore_exc:
            if transaction is not None:
                rollback_errors = _rollback_build(context, armature, transaction)
                try:
                    _restore_context(context, armature, snapshot)
                except (LimbIKError, ReferenceError, RuntimeError) as second_restore:
                    rollback_errors.append(str(second_restore))
                suffix = f" Rollback also reported: {'; '.join(rollback_errors)}" if rollback_errors else ""
                error = LimbIKError(f"Context restoration failed, so the generated rig was rolled back: {restore_exc}.{suffix}")
            elif error is None:
                error = LimbIKError(f"Limb IK context restoration failed: {restore_exc}")
    if error is not None:
        message = str(error)
        level = "ERROR" if "rollback" in message.lower() or "restoration" in message.lower() else "WARNING"
        _set_status(settings, level, message)
        operator.report({"ERROR" if level == "ERROR" else "WARNING"}, message)
        return {"CANCELLED"}
    warnings = [plan.pole_warning for plan in built if plan.pole_warning]
    labels = {"SELECTED": "selected", "ALL": "available"}
    label = labels.get(scope, scope.title())
    message = f"Built {len(built)} {label} IK side{'s' if len(built) != 1 else ''}; targets, Poles, IK(2), and end rotation are ready."
    if warnings:
        message += " " + " ".join(warnings)
    _set_status(settings, "WARNING" if warnings else "SUCCESS", message)
    operator.report({"WARNING" if warnings else "INFO"}, message)
    return {"FINISHED"}


class CHARACTERDESIGNER_OT_limb_ik_build_arm(Operator):
    bl_idname = "character_designer.limb_ik_build_arm"
    bl_label = "Build Arm Rig"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        settings = _settings(context)
        return context.object is not None and context.object.type == "ARMATURE" and settings is not None

    def execute(self, context):
        return _execute_build(self, context, "ARM")


class CHARACTERDESIGNER_OT_limb_ik_build_leg(Operator):
    bl_idname = "character_designer.limb_ik_build_leg"
    bl_label = "Build Leg Rig"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        settings = _settings(context)
        return context.object is not None and context.object.type == "ARMATURE" and settings is not None

    def execute(self, context):
        return _execute_build(self, context, "LEG")


class CHARACTERDESIGNER_OT_limb_ik_build_selected(Operator):
    bl_idname = "character_designer.limb_ik_build_selected"
    bl_label = "Build IK"
    bl_description = "Build only the Arm or Leg currently selected in the dropdown"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        settings = _settings(context)
        return context.object is not None and context.object.type == "ARMATURE" and settings is not None

    def execute(self, context):
        return _execute_build(self, context, "SELECTED")


class CHARACTERDESIGNER_OT_limb_ik_build_all(Operator):
    bl_idname = "character_designer.limb_ik_build_all"
    bl_label = "Build All"
    bl_description = "Build every complete analyzed Arm and Leg in one atomic Undo step"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        settings = _settings(context)
        return context.object is not None and context.object.type == "ARMATURE" and settings is not None

    def execute(self, context):
        return _execute_build(self, context, "ALL")


class CHARACTERDESIGNER_OT_limb_ik_remove(Operator):
    bl_idname = "character_designer.limb_ik_remove"
    bl_label = "Remove Generated Rig"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        settings = _settings(context)
        armature = None
        context_snapshot = None
        rig_snapshot = None
        summary = None
        error = None
        removal_attempted = False
        master_state = None
        try:
            armature = _require_active_armature(context, settings, analyzed=False)
            context_snapshot = _capture_context(context, armature)
            inventory = _validate_inventory(armature)
            _removal_resources(context, armature, inventory)
            problems = _foreign_dependency_problems(armature, inventory)
            if problems:
                raise LimbIKError(f"Remove Generated Rig was refused: {problems[0]}.")
            master_state = _neutralize_existing_master(context, armature, validate_scale=False)
            inventory = _validate_inventory(armature)
            rig_snapshot = _snapshot_owned_rig(armature, inventory)
            if master_state is not None and MASTER_NAME in rig_snapshot["control_pose"]:
                rig_snapshot["control_pose"][MASTER_NAME] = {
                    "rotation_mode": master_state["rotation_mode"],
                    "matrix_basis": master_state["matrix_basis"].copy(),
                }
            removal_attempted = True
            summary = _remove_owned(context, armature, refuse_dependencies=False)
        except (LimbIKError, ReferenceError, RuntimeError, TypeError, ValueError) as exc:
            error = exc
            if removal_attempted and rig_snapshot is not None:
                try:
                    _restore_owned_snapshot(context, armature, rig_snapshot)
                    master_state = None
                except Exception as recovery_exc:
                    error = LimbIKError(f"{exc} Recovery also failed: {recovery_exc}")
            elif master_state is not None and armature is not None:
                try:
                    _restore_master_state(context, armature, master_state)
                    master_state = None
                except Exception as recovery_exc:
                    error = LimbIKError(f"{exc} Master pose recovery also failed: {recovery_exc}")
        if context_snapshot is not None and armature is not None:
            try:
                _restore_context(context, armature, context_snapshot)
            except (LimbIKError, ReferenceError, RuntimeError) as restore_exc:
                if error is None and rig_snapshot is not None:
                    try:
                        _restore_owned_snapshot(context, armature, rig_snapshot)
                        _restore_context(context, armature, context_snapshot)
                        error = LimbIKError(f"Remove was rolled back because context restoration failed: {restore_exc}")
                    except Exception as recovery_exc:
                        error = LimbIKError(f"Context restoration failed after Remove, and rig recovery also failed: {recovery_exc}")
                elif error is None:
                    error = restore_exc
        if error is not None:
            message = str(error)
            level = "ERROR" if "Recovery also failed" in message or "recovery also failed" in message else "WARNING"
            _set_status(settings, level, message)
            self.report({"ERROR" if level == "ERROR" else "WARNING"}, message)
            return {"CANCELLED"}
        settings.analysis_json = ""
        message = f"Removed {summary['bones']} controls, {summary['constraints']} constraints, and {summary['widgets']} widgets. Analyze again before rebuilding."
        _set_status(settings, "SUCCESS", message)
        self.report({"INFO"}, message)
        return {"FINISHED"}


class CHARACTERDESIGNER_OT_limb_ik_rebuild(Operator):
    bl_idname = "character_designer.limb_ik_rebuild"
    bl_label = "Rebuild Rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = _settings(context)
        armature = None
        context_snapshot = None
        rig_snapshot = None
        new_transaction = None
        rebuilt = ()
        error = None
        removal_attempted = False
        master_state = None
        try:
            armature = _require_active_armature(context, settings)
            context_snapshot = _capture_context(context, armature)
            inventory = _validate_inventory(armature)
            rig_keys = sorted(inventory["rigs"])
            if not rig_keys:
                raise LimbIKError("No generated Limb IK rig exists to rebuild.")
            _removal_resources(context, armature, inventory)
            problems = _foreign_dependency_problems(armature, inventory)
            if problems:
                raise LimbIKError(f"Rebuild Rig was refused: {problems[0]}.")
            master_state = _neutralize_existing_master(context, armature)
            inventory = _validate_inventory(armature)
            rig_snapshot = _snapshot_owned_rig(armature, inventory)
            if master_state is not None and MASTER_NAME in rig_snapshot["control_pose"]:
                rig_snapshot["control_pose"][MASTER_NAME] = {
                    "rotation_mode": master_state["rotation_mode"],
                    "matrix_basis": master_state["matrix_basis"].copy(),
                }
            plans = _plans_for_exact_keys(context, armature, settings, rig_keys)
            removal_attempted = True
            _remove_owned(context, armature)
            _mode_set(context, armature, "POSE")
            rebuilt, new_transaction = _build_plans(
                context,
                armature,
                plans,
                desired_source_pose=rig_snapshot["source_pose"],
            )
            _restore_master_state(context, armature, master_state)
            master_state = None
        except (LimbIKError, ReferenceError, RuntimeError, TypeError, ValueError) as exc:
            error = exc
            if new_transaction is not None:
                _rollback_build(context, armature, new_transaction)
                new_transaction = None
            if removal_attempted and rig_snapshot is not None:
                try:
                    _restore_owned_snapshot(context, armature, rig_snapshot)
                    master_state = None
                except Exception as recovery_exc:
                    error = LimbIKError(f"{exc} Old-rig recovery also failed: {recovery_exc}")
            elif master_state is not None and armature is not None:
                try:
                    _restore_master_state(context, armature, master_state)
                    master_state = None
                except Exception as recovery_exc:
                    error = LimbIKError(f"{exc} Master pose recovery also failed: {recovery_exc}")
        if context_snapshot is not None and armature is not None:
            try:
                _restore_context(context, armature, context_snapshot)
            except (LimbIKError, ReferenceError, RuntimeError) as restore_exc:
                if error is None and rig_snapshot is not None:
                    try:
                        if new_transaction is not None:
                            _rollback_build(context, armature, new_transaction)
                            new_transaction = None
                        _restore_owned_snapshot(context, armature, rig_snapshot)
                        _restore_context(context, armature, context_snapshot)
                        error = LimbIKError(f"Rebuild was rolled back because context restoration failed: {restore_exc}")
                    except Exception as recovery_exc:
                        error = LimbIKError(f"Rebuild context restoration failed, and old-rig recovery also failed: {recovery_exc}")
                elif error is None:
                    error = restore_exc
        if error is not None:
            message = str(error)
            _set_status(settings, "ERROR", message)
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        message = f"Rebuilt {len(rebuilt)} Limb IK sides from the current analyzed chains."
        _set_status(settings, "SUCCESS", message)
        self.report({"INFO"}, message)
        return {"FINISHED"}


class CHARACTERDESIGNER_OT_limb_ik_default_pole_direction(Operator):
    bl_idname = "character_designer.limb_ik_default_pole_direction"
    bl_label = "Default Pole Direction"
    bl_description = "Reset only the selected limb to its Armature-local anatomical Pole direction"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return _settings(context) is not None

    def execute(self, context):
        settings = _settings(context)
        kind, side = SELECTED_LIMBS.get(settings.selected_limb, ("", ""))
        if kind not in KINDS or side not in SIDES:
            message = "Choose one Arm or Leg before resetting its Pole Direction."
            _set_status(settings, "WARNING", message)
            self.report({"WARNING"}, message)
            return {"CANCELLED"}
        chain_names = tuple(getattr(settings, _field_name(kind, side, role)) for role in ROLES)
        direction, used_modeled_bend = _rest_pole_direction(settings.armature, kind, side, chain_names)
        setattr(settings, _pole_direction_field(kind, side), tuple(direction))
        source = "modeled rest bend" if used_modeled_bend else "anatomical fallback"
        message = f"Reset {side} {kind.title()} Pole Direction from its {source}."
        _set_status(settings, "SUCCESS", message)
        self.report({"INFO"}, message)
        return {"FINISHED"}


class CHARACTERDESIGNER_OT_limb_ik_flip_pole(Operator):
    bl_idname = "character_designer.limb_ik_flip_pole"
    bl_label = "Flip Pole"
    bl_options = {"REGISTER", "UNDO"}

    kind: EnumProperty(items=(("ARM", "Arm", ""), ("LEG", "Leg", "")))
    side: EnumProperty(items=(("L", "Left", ""), ("R", "Right", "")))

    def execute(self, context):
        settings = _settings(context)
        try:
            armature = _require_active_armature(context, settings, analyzed=False)
            rig = _validate_inventory(armature)["rigs"].get((self.kind, self.side))
            if rig is None:
                raise LimbIKError(f"No generated {self.side} {self.kind.title()} rig exists.")
            ik = next(constraint for _pb, constraint, record in rig["entries"] if record["role"] == "IK")
            ik.pole_angle = math.remainder(ik.pole_angle + math.pi, math.tau)
            message = f"Flipped {self.side} {self.kind.title()} Pole solution by 180°."
            _set_status(settings, "SUCCESS", message)
            self.report({"INFO"}, message)
            return {"FINISHED"}
        except (LimbIKError, ReferenceError, RuntimeError, TypeError, ValueError) as exc:
            _set_status(settings, "WARNING", str(exc))
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}


def _draw_limb_fields(layout, settings, armature, kind, side):
    column = layout.column(align=True)
    for role in ROLES:
        property_name = _field_name(kind, side, role)
        if armature is not None:
            column.prop_search(settings, property_name, armature.data, "bones", text=role.title())
        else:
            column.prop(settings, property_name, text=role.title())


def _active_has_owned_side_rig(context):
    armature = context.object
    if armature is None or armature.type != "ARMATURE":
        return False
    try:
        armature_id = armature.data.get(ARMATURE_ID_KEY, "")
        if not isinstance(armature_id, str) or not armature_id:
            return False
        return any(
            bone.get(OWNER_KEY) == OWNER_VALUE
            and bone.get(ARMATURE_ID_KEY) == armature_id
            and isinstance(bone.get(RIG_ID_KEY), str)
            and bool(bone.get(RIG_ID_KEY))
            for bone in armature.data.bones
        )
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        # Panel drawing must remain cheap and resilient.  The operator itself
        # still performs the strict inventory/dependency validation before it
        # removes anything.
        return False


class CHARACTERDESIGNER_PT_limb_ik(Panel):
    bl_label = "Limb IK"
    bl_idname = "CHARACTERDESIGNER_PT_limb_ik"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = SIDEBAR_CATEGORY
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return active_ui_page(context) == UI_PAGE_RIG

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)
        if settings is None:
            layout.label(text="Limb IK state is unavailable.", icon="ERROR")
            return
        layout.operator("character_designer.limb_ik_analyze", text="Analyze Rig", icon="VIEWZOOM")
        layout.prop(settings, "selected_limb", text="")
        armature = settings.armature
        kind, side = SELECTED_LIMBS.get(settings.selected_limb, ("ARM", "L"))
        _draw_limb_fields(layout, settings, armature, kind, side)
        layout.prop(
            settings,
            _pole_direction_field(kind, side),
            text="Pole Direction (Local)",
        )
        layout.operator(
            "character_designer.limb_ik_default_pole_direction",
            text="Default Direction",
            icon="LOOP_BACK",
        )
        row = layout.row(align=True)
        row.operator("character_designer.limb_ik_build_selected", text="Build IK", icon="CON_KINEMATIC")
        row.operator("character_designer.limb_ik_build_all", text="Build All", icon="ARMATURE_DATA")
        row = layout.row(align=True)
        row.operator("character_designer.limb_ik_rebuild", text="Rebuild Rig", icon="FILE_REFRESH")
        remove = row.row(align=True)
        remove.alert = _active_has_owned_side_rig(context)
        remove.operator("character_designer.limb_ik_remove", text="Remove Generated Rig", icon="TRASH")


LIMB_IK_CLASSES = (
    CharacterDesignerLimbIKState,
    CHARACTERDESIGNER_OT_limb_ik_analyze,
    CHARACTERDESIGNER_OT_limb_ik_build_arm,
    CHARACTERDESIGNER_OT_limb_ik_build_leg,
    CHARACTERDESIGNER_OT_limb_ik_build_selected,
    CHARACTERDESIGNER_OT_limb_ik_build_all,
    CHARACTERDESIGNER_OT_limb_ik_remove,
    CHARACTERDESIGNER_OT_limb_ik_rebuild,
    CHARACTERDESIGNER_OT_limb_ik_default_pole_direction,
    CHARACTERDESIGNER_OT_limb_ik_flip_pole,
    CHARACTERDESIGNER_PT_limb_ik,
)


__all__ = (
    "CharacterDesignerLimbIKState",
    "LIMB_IK_CLASSES",
    "LimbIKError",
    "analyze_armature",
)
