"""Prepared native QA for persistent Original edits over a sealed Dress cache.

Import from the isolated actual-surface motion runner after bake/seek and its
existing frozen_delta_tests/original_roundtrip, before probe cleanup and save.
This module does not launch Blender, bake/reset a cache, save, or run on import.
It requires that runner's private synthetic Action and independently saved QA
candidate. A public Original -> edit -> Controls transition must create the
correction; writing internal metadata is used only to restore the QA checkpoint.

Preparation alone is not native execution or an artist/Unity quality pass.
"""

import ast
import math
from pathlib import Path

import bpy
from mathutils import Matrix


HERE = Path(__file__).resolve().parent
TRANSFORMS = frozenset(("location", "rotation_euler", "rotation_quaternion",
                        "rotation_axis_angle", "scale", "rotation_mode"))
LOCKS = ("lock_location", "lock_rotation", "lock_rotation_w",
         "lock_rotations_4d", "lock_scale")


def _require(condition, message):
    if not condition:
        raise RuntimeError("Original refinement QA: " + message)


def _clone(value):
    """Preserve native ID references; copy mutable ID-property containers."""
    if isinstance(value, bpy.types.ID):
        return value
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if hasattr(value, "items"):
        return {key: _clone(item) for key, item in value.items()}
    if hasattr(value, "to_list"):
        return [_clone(item) for item in value.to_list()]
    if isinstance(value, (tuple, list)):
        return [_clone(item) for item in value]
    raise TypeError("Unsupported native checkpoint property: " + type(value).__name__)


def _property(owner, name):
    return (name in owner, _clone(owner.get(name)))


def _restore_property(owner, name, saved):
    present, value = saved
    if present:
        owner[name] = value
    else:
        owner.pop(name, None)


def _path_identity(path):
    """Native quoted-name aliases compare as syntax, never execute as code."""
    try:
        return ast.dump(ast.parse(path, mode="eval").body, include_attributes=False)
    except (SyntaxError, ValueError, TypeError):
        return None


def _transform_on(path, root):
    try:
        value = ast.parse(path, mode="eval").body
    except (SyntaxError, ValueError, TypeError):
        return False
    # Transform vectors can be addressed either by FCurve.array_index or a
    # literal subscript. A '.constraints[...]' path is not a native transform.
    if isinstance(value, ast.Subscript):
        value = value.value
    return (isinstance(value, ast.Attribute) and value.attr in TRANSFORMS
            and ast.dump(value.value, include_attributes=False) == _path_identity(root))


def _action_curves(action):
    result = []
    if action is None:
        return result
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                result.extend(bag.fcurves)
    if getattr(action, "is_action_legacy", False):
        result.extend(getattr(action, "fcurves", ()))
    return result


def _bound_actions(animation):
    result = {animation.action} if animation and animation.action else set()
    pending = [strip for track in animation.nla_tracks for strip in track.strips] if animation else []
    while pending:
        strip = pending.pop()
        if strip.action is not None:
            result.add(strip.action)
        pending.extend(getattr(strip, "strips", ()))
    return result


def _choose_def(source, rig, record):
    animation = rig.animation_data
    curves = list(animation.drivers) if animation else []
    for action in _bound_actions(animation):
        curves.extend(_action_curves(action))
    occupied = []
    for chain in record["chains"]:
        for name in reversed(chain["def"]):
            bone = rig.pose.bones[name]
            group = source.vertex_groups.get(name)
            if group is None or not any(item.group == group.index and item.weight > 1.e-8
                                        for vertex in source.data.vertices for item in vertex.groups):
                continue
            if any(_transform_on(curve.data_path, bone.path_from_id()) for curve in curves):
                occupied.append(name)
                continue
            return bone, occupied
    raise RuntimeError("Original refinement QA: no weighted Dress DEF without existing transform curves/drivers; "
                       "no author curve was replaced (occupied: " + ", ".join(occupied) + ")")


def _curve_collection(action, slot):
    if getattr(action, "is_action_legacy", False):
        return action.fcurves
    _require(slot is not None, "the private layered Action has no assigned slot")
    bags = [bag for layer in action.layers for strip in layer.strips
            for bag in getattr(strip, "channelbags", ()) if bag.slot_handle == slot.handle]
    _require(len(bags) == 1, "the synthetic Action must already have exactly one matching channelbag; "
             "QA does not create layers, strips, slots, channelbags or groups")
    return bags[0].fcurves


def _pose_checkpoint(rig, qa):
    animation = rig.animation_data
    return {"rig": rig, "channels": qa.pose_channels(rig), "basis": rig.matrix_basis.copy(),
            "object_mode": rig.rotation_mode,
            "animation_present": animation is not None,
            "action": animation.action if animation else None,
            "slot": animation.action_slot if animation else None,
            "locks": {bone.name: {key: list(getattr(bone, key)) if hasattr(getattr(bone, key), "__len__")
                                   else getattr(bone, key) for key in LOCKS} for bone in rig.pose.bones},
            "properties": {bone.name: {key: value for key, value in bone.items()
                                      if type(value) in (bool, int, float, str)} for bone in rig.pose.bones},
            "constraints": {bone.name: [(item, item.as_pointer(), item.name, item.type,
                                         item.mute, item.influence, getattr(item, "mix_mode", None))
                                        for item in bone.constraints] for bone in rig.pose.bones}}


def _restore_pose(saved, qa):
    rig = saved["rig"]
    _require(set(rig.pose.bones.keys()) == set(saved["channels"]), "pose-bone inventory changed during cleanup")
    for name, entries in saved["constraints"].items():
        constraints = list(rig.pose.bones[name].constraints)
        _require(len(entries) == len(constraints) and all(actual == item and actual.as_pointer() == pointer
                 and actual.name == label and actual.type == kind
                 for actual, (item, pointer, label, kind, _mute, _influence, _mix) in zip(constraints, entries)),
                 "native constraint identity changed during cleanup: " + name)
        for item, _pointer, _label, _kind, mute, influence, mix in entries:
            item.mute, item.influence = mute, influence
            if mix is not None:
                item.mix_mode = mix
    for name, values in saved["properties"].items():
        bone = rig.pose.bones[name]
        for key, value in list(bone.items()):
            if type(value) in (bool, int, float, str) and key not in values:
                del bone[key]
        for key, value in values.items():
            bone[key] = value
    for name, fields in saved["locks"].items():
        for key, value in fields.items():
            setattr(rig.pose.bones[name], key, value)
    # Unlike the whole-motion runner's restore_channels, this checkpoint must
    # not create AnimationData or detach an attached Hair/display rig's Action.
    # Only the main rig's explicitly marked synthetic Action is detached by
    # this test. Restore native fields without touching other bindings.
    rig.rotation_mode = saved["object_mode"]
    rig.matrix_basis = saved["basis"]
    for name, values in saved["channels"].items():
        bone = rig.pose.bones[name]
        bone.rotation_mode = values["mode"]
        bone.location, bone.scale = values["location"], values["scale"]
        bone.rotation_quaternion = values["quaternion"]
        bone.rotation_euler = values["euler"]
        bone.rotation_axis_angle = values["axis_angle"]
    rig.update_tag(refresh={"OBJECT"})
    bpy.context.view_layer.update()


def _constraint_state(rig):
    return {bone.name: [(item.as_pointer(), item.name, item.type, item.mute, item.influence,
                         getattr(item, "mix_mode", None)) for item in bone.constraints] for bone in rig.pose.bones}


def _expected_constraints(saved):
    return {name: [(pointer, label, kind, mute, influence, mix)
                   for _item, pointer, label, kind, mute, influence, mix in entries]
            for name, entries in saved["constraints"].items()}


def _pose_restored(saved, qa):
    rig = saved["rig"]
    animation = rig.animation_data
    now = _pose_checkpoint(rig, qa)
    return (now["channels"] == saved["channels"] and now["locks"] == saved["locks"]
            and now["properties"] == saved["properties"] and rig.rotation_mode == saved["object_mode"]
            and max((abs(a-b) for row_a, row_b in zip(rig.matrix_basis, saved["basis"])
                     for a, b in zip(row_a, row_b)), default=0.) <= 1.e-7
            and _constraint_state(rig) == _expected_constraints(saved)
            and (animation is not None) == saved["animation_present"]
            and (animation.action if animation else None) == saved["action"]
            and (animation.action_slot if animation else None) == saved["slot"])


def _restore_context(saved, rig, qa):
    qa.skirt._activate(bpy.context, rig, "OBJECT")
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for name in saved["selected"]:
        _require(bpy.context.view_layer.objects.get(name) is not None, "a selected object disappeared")
        bpy.context.view_layer.objects[name].select_set(True)
    active = bpy.data.objects.get(saved["active"]) if saved["active"] else None
    bpy.context.view_layer.objects.active = active
    if active is not None and saved["mode"] != "OBJECT":
        status = bpy.ops.object.mode_set(mode=saved["mode"])
        _require("FINISHED" in status, "native context mode restoration failed")


def verify_sealed_original_refinement(source, rig, actual, cloth, neutral, body,
                                     result, qa, surface, workflow, meters, *, exercise_keys=True):
    """Run public persistent posing plus optional new-only three-frame curves.

    The caller supplies its already validated native objects and existing QA
    helpers. All comparisons are native evaluated exact-index geometry. Pass
    here concerns correction composition over this sealed cache, not physical
    clearance, production movement, rendered appearance, Unity or Magica.
    """
    from character_designer import bone_display, body_original_mode, skirt_original_mode

    _require(bpy.app.background, "run only in a private background motion QA session")
    candidate = Path(bpy.data.filepath).resolve()
    ownership = result.get("cache_ownership", {})
    _require(bool(bpy.data.filepath) and candidate.is_file() and candidate.suffix.casefold() == ".blend"
             and candidate.is_relative_to(HERE) and candidate.parent != HERE
             and candidate == Path(ownership.get("candidate", "")).resolve(),
             "the current file is not this runner's exact independently saved QA candidate")
    _require(0. < meters < math.inf and not body_original_mode.active(rig),
             "use finite positive metres and begin in Controls without an Original session")
    record, checked_rig, checked_actual, checked_cloth, checked_neutral = workflow.motion_objects(source, qa, surface)
    native = record["physics"]["surface"]
    _require((checked_rig, checked_actual, checked_cloth, checked_neutral) == (rig, actual, cloth, neutral)
             and bpy.data.objects.get(native["body"]) == body
             and bpy.context.scene.name == native["home_scene"], "the exact native source/home Scene/Body differs")
    cache = cloth.point_cache
    _require(cache.is_baked and not cache.is_baking and not cache.use_external and cache.use_disk_cache
             and record["physics"].get("baked_range") == [cache.frame_start, cache.frame_end]
             and cache.frame_step == 1, "a sealed private unit-step local cache is required; QA never resets or bakes")
    _require(Path(bpy.path.abspath(cache.filepath)).resolve().is_relative_to(candidate.parent),
             "the native cache filepath is outside this QA case")
    _require(not bpy.context.scene.tool_settings.use_keyframe_insert_auto, "disable auto key in the private motion runner first")
    animation = rig.animation_data
    action, slot = (animation.action, animation.action_slot) if animation else (None, None)
    _require(action is not None and action.get("CD_QA_SyntheticInput") is True
             and bpy.data.actions.get(action.name) == action and not action.library,
             "only the runner's declared local synthetic Action may be detached or extended")
    selected, occupied = _choose_def(source, rig, record)
    # The public coordinator can affect another attached Dress. This narrow
    # fixture refuses that scope rather than invisibly mutating a second source.
    dresses = skirt_original_mode._inventory(bpy.context, rig)
    _require(set(dresses) == {record["owner"]} and dresses[record["owner"]][:2] == (rig, source),
             "this prepared fixture supports exactly one proved shared Dress source")
    collection = _curve_collection(action, slot) if exercise_keys else None
    action_pointer, action_before = action.as_pointer(), qa.digest(qa.action_content(action))
    existing_curves = {curve.as_pointer() for curve in _action_curves(action)}
    cache_files = {Path(item["path"]).resolve(): {key: item[key] for key in ("bytes", "mtime_ns", "sha256")}
                   for item in ownership.get("observed_native_cache_files", ())}
    _require(cache_files and all(path.is_relative_to(candidate.parent) and path.is_file() for path in cache_files),
             "the sealed motion run has no complete observed QA-local cache-file receipt")
    _require(set(candidate.parent.rglob("*.bphys")) == set(cache_files)
             and all(qa.file_state(path) == value for path, value in cache_files.items()),
             "observed native cache content/inventory changed before refinement")

    scene = bpy.context.scene
    context_before = workflow.context_content(bpy.context)
    anchor = scene.frame_current
    _require(cache.frame_start <= anchor <= cache.frame_end and scene.frame_subframe == 0.,
             "begin on a whole sealed-cache frame")
    start = min(anchor, cache.frame_end - 2)
    frames = [start, start + 1, start + 2]
    _require(frames[0] >= cache.frame_start, "the sealed cache has fewer than three available frames")
    guard = qa.geometry_guard(meters)
    protection = qa.Protection()  # Captures all original raw meshes/rest/Actions before the copied S probe exists.
    inventory_before = workflow.inventory()
    affected = list(dict.fromkeys([rig] + list(bone_display._affected(bpy.context, rig))
                 + [target for part in body_original_mode._native_groups(bpy.context, rig).values() for target in part]))
    _require(not any(body_original_mode.active(target) for target in affected), "an attached rig already has an Original session")
    display_before = bone_display._checkpoint(affected)
    poses_before = [_pose_checkpoint(target, qa) for target in affected]
    metadata_before = [(target, name, _property(target, name)) for target in affected
                       for name in (body_original_mode.SESSION, body_original_mode.DISPLAY_REFS, body_original_mode.DISPLAY_OWNER)]
    correction_before = _property(source, skirt_original_mode.CORRECTIONS)
    correction_entries_before = skirt_original_mode._corrections(source, record)["bones"]
    record_before, profile_before = source[qa.skirt.RECORD_KEY], _property(source, qa.profiles.PROFILE_KEY)
    cache_before = workflow.cache_content(cloth, qa, surface)
    drivers_before = surface._drivers(rig)
    holder, _identifier, _path = qa.skirt.physics_control(source)
    influence_before = float(holder["physics_influence"])
    overlay = source.modifiers[native["overlay"]]
    overlay_flags = (overlay.show_viewport, overlay.show_render)
    report = {"status": "RUNNING", "bone": selected.name, "frames": frames,
              "rotation_radians": .10, "key_rotation_offsets_radians": [0., .04, -.04] if exercise_keys else [],
              "guard_m": guard, "synthetic_action": action.name, "occupied_candidates_skipped": occupied,
              "checks": [], "persistent_edit_created_by": "public body_original_mode Original/edit/Controls",
              "metadata_writes_for_success": False, "production_effect_accepted": False,
              "scope": "One weighted Dress DEF and three frames over the already sealed private cache. "
                       "No cloth re-simulation or artist/Unity/Magica acceptance."}
    result["sealed_original_refinement"] = report
    skin, created, baseline, persistent = None, [], {}, {}
    failure, cleanup_errors = None, []

    def check(name, condition, **facts):
        workflow.motion_check(report, qa, name, condition, **facts)

    def update():
        rig.update_tag(refresh={"OBJECT"})
        bpy.context.view_layer.update()

    def snapshots():
        graph = bpy.context.evaluated_depsgraph_get()
        values = {key: qa.world_mesh(obj, graph)["points"] for key, obj in
                  (("O", source), ("S", skin), ("C", actual), ("H0", neutral), ("Body", body))}
        _require(len(values["O"]) == len(values["S"]) == 3040 and len(values["C"]) == len(values["H0"]) == 800
                 and values["Body"] and all(qa.finite(points) for points in values.values()),
                 "nonfinite or changed native exact-index geometry layout")
        return values

    def errors(before, after, keys=("O", "S", "C", "H0", "Body")):
        return {key: workflow.point_error(before[key], after[key], meters) for key in keys}

    def delta_error(before, after):
        return workflow.point_error([a-b for a, b in zip(after["O"], before["O"])],
                                    [a-b for a, b in zip(after["S"], before["S"])], meters)

    def protected(allow_synthetic=False):
        value = protection.verify()
        permitted = [action.name] if allow_synthetic else []
        ok = (not value["missing"] and not value["changed"]["meshes"] and not value["changed"]["rest"]
              and not value["changed"]["nla_assets"] and set(value["changed"]["actions"]) <= set(permitted)
              and tuple(bpy.data.actions) == protection.action_refs)
        return ok, value

    def sealed():
        return (workflow.cache_content(cloth, qa, surface) == cache_before
                and set(candidate.parent.rglob("*.bphys")) == set(cache_files)
                and all(path.is_file() and qa.file_state(path) == value for path, value in cache_files.items())
                and source[qa.skirt.RECORD_KEY] == record_before
                and _property(source, qa.profiles.PROFILE_KEY) == profile_before
                and float(holder["physics_influence"]) == influence_before
                and (overlay.show_viewport, overlay.show_render) == overlay_flags
                and surface._drivers(rig) == drivers_before)

    def reattach():
        _require(bpy.data.actions.get(action.name) == action and action.as_pointer() == action_pointer,
                 "the private synthetic Action changed identity")
        animation.action = action
        if slot is not None:
            animation.action_slot = slot

    def remove_curves():
        if collection is None:
            return
        for curve, pointer, path, index in reversed(created):
            found = next((item for item in collection if item.as_pointer() == pointer), None)
            _require(found is not None and found == curve and found.data_path == path and found.array_index == index
                     and pointer not in existing_curves, "a new QA curve changed identity or acquired an existing curve's identity")
            collection.remove(found)
        created.clear()

    try:
        skin = workflow.motion_probe(source, scene, "Persistent Original Refinement", lambda item: item.type != "NODES")
        for frame in sorted(set(frames + [anchor])):
            scene.frame_set(frame)
            baseline[frame] = snapshots()
        scene.frame_set(anchor)
        before = snapshots()
        # Detach only this synthetic Action, preserving every author Action/NLA
        # asset. Public Original's native animation safety gate remains enabled.
        animation.action = None
        qa.skirt._activate(bpy.context, rig, "POSE")
        qa.public_switch(bpy.ops.character_designer.body_original_mode, action="ORIGINAL")
        _require(body_original_mode.active(rig), "public Original did not establish a native session")
        workflow.motion_objects(source, qa, surface)
        entered = snapshots()
        enter_errors = errors(before, entered)
        check("persistent_original_public_enter_no_jump", max(enter_errors.values()) <= guard and sealed(), errors_m=enter_errors)
        selected.matrix_basis = selected.matrix_basis.copy() @ Matrix.Rotation(.10, 4, "X")
        update()
        edited = snapshots()
        edit_errors = errors(entered, edited)
        ok, assets = protected()
        check("persistent_original_native_edit_composes_with_S", edit_errors["O"] > 1.e-5
              and delta_error(entered, edited) <= guard
              and max(edit_errors[key] for key in ("C", "H0", "Body")) <= guard and sealed() and ok,
              errors_m=edit_errors, O_delta_minus_S_delta_m=delta_error(entered, edited), original_assets=assets)

        # Deliberately keep the edit in place. Reverting the bone before this
        # operator would prove only no-edit switching, not persistent refinement.
        qa.public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS")
        _require(not body_original_mode.active(rig), "public Controls left an active Original session")
        workflow.motion_objects(source, qa, surface)
        correction = skirt_original_mode._corrections(source, qa.skirt.read_record(source))
        copied = selected.constraints.get("Skirt manual pose")
        returned = snapshots()
        return_errors = errors(edited, returned)
        check("persistent_original_public_controls_stores_correction", selected.name in correction["bones"]
              and (selected.name in correction_entries_before
                   or _property(source, skirt_original_mode.CORRECTIONS) != correction_before)
              and all(correction["bones"].get(name) == entry for name, entry in correction_entries_before.items())
              and copied is not None and copied.mix_mode == "BEFORE_FULL"
              and max(return_errors.values()) <= guard and sealed(), errors_m=return_errors,
              correction_bones=sorted(correction["bones"]), preexisting_correction_preserved=selected.name in correction_entries_before,
              copy_mix_mode=copied.mix_mode if copied else None)
        correction_after = _property(source, skirt_original_mode.CORRECTIONS)
        reattach()
        for frame in frames:
            scene.frame_set(frame)
            after = snapshots()
            persistent[frame] = after
            drift = errors(baseline[frame], after)
            check("persistent_original_after_action_and_seek_" + str(frame), drift["O"] > 1.e-5
                  and delta_error(baseline[frame], after) <= guard
                  and max(drift[key] for key in ("C", "H0", "Body")) <= guard and sealed()
                  and _property(source, skirt_original_mode.CORRECTIONS) == correction_after,
                  errors_m=drift, O_delta_minus_S_delta_m=delta_error(baseline[frame], after))
        ok, assets = protected()
        check("persistent_original_preserves_raw_rest_existing_actions", ok, details=assets)

        if exercise_keys:
            scene.frame_set(frames[0])
            basis = selected.matrix_basis.copy()
            mode = selected.rotation_mode
            prop = "rotation_quaternion" if mode == "QUATERNION" else "rotation_axis_angle" if mode == "AXIS_ANGLE" else "rotation_euler"
            path = selected.path_from_id(prop)
            values = []
            for offset in (0., .04, -.04):
                _location, quaternion, _scale = (basis @ Matrix.Rotation(offset, 4, "X")).decompose()
                if mode == "QUATERNION":
                    values.append(tuple(quaternion))
                elif mode == "AXIS_ANGLE":
                    axis, angle = quaternion.to_axis_angle()
                    values.append((angle, *axis))
                else:
                    values.append(tuple(quaternion.to_euler(mode)))
            _require(not any(_transform_on(curve.data_path, selected.path_from_id()) for curve in _action_curves(action)),
                     "the selected DEF acquired an existing Action transform curve before key insertion")
            _require(all(math.isfinite(value) for channel in values for value in channel), "nonfinite native rotation key proposal")
            for index in range(len(values[0])):
                curve = collection.new(data_path=path, index=index)
                pointer = curve.as_pointer()
                _require(pointer not in existing_curves, "native curve creation returned an existing Action curve")
                created.append((curve, pointer, path, index))
                curve.keyframe_points.add(3)
                for key, frame, channel in zip(curve.keyframe_points, frames, values):
                    key.co = (float(frame), channel[index])
                    key.interpolation = "LINEAR"
                curve.update()
            action.update_tag()
            key_errors = []
            for frame in frames:
                scene.frame_set(frame)
                workflow.motion_objects(source, qa, surface)
                keyed = snapshots()
                drift = errors(persistent[frame], keyed)
                key_errors.append(drift["O"])
                ok, assets = protected(allow_synthetic=True)
                check("persistent_original_new_only_key_" + str(frame), delta_error(persistent[frame], keyed) <= guard
                      and max(drift[key] for key in ("C", "H0", "Body")) <= guard and sealed() and ok
                      and _property(source, skirt_original_mode.CORRECTIONS) == correction_after,
                      errors_m=drift, O_delta_minus_S_delta_m=delta_error(persistent[frame], keyed), original_assets=assets)
            check("persistent_original_new_keys_have_visible_effect", min(key_errors[1:]) > 1.e-5,
                  output_delta_m=key_errors, curve_count=len(created), mode=mode, property=prop)
            remove_curves()
            action.update_tag()
            selected.matrix_basis = basis
            update()
            check("persistent_original_new_curves_removed_action_exact", qa.digest(qa.action_content(action)) == action_before
                  and {curve.as_pointer() for curve in _action_curves(action)} == existing_curves)
            for frame in frames:
                scene.frame_set(frame)
                drift = errors(persistent[frame], snapshots())
                check("persistent_original_unkeyed_refinement_restored_" + str(frame), max(drift.values()) <= guard
                      and sealed(), errors_m=drift)
        report["keys_exercised"] = bool(exercise_keys)
    except Exception as exc:
        failure = exc
        report["failure"] = str(exc)
    finally:
        # Cleanup attempts are independent: a public failure must not skip the
        # exact pose/metadata restore or leave this synthetic Action extended.
        def attempt(label, function):
            try:
                function()
            except Exception as exc:
                cleanup_errors.append({"step": label, "error": str(exc)})

        attempt("remove_exact_new_curves", remove_curves)
        if body_original_mode.active(rig):
            attempt("public_return_to_controls", lambda: qa.public_switch(
                bpy.ops.character_designer.body_original_mode, action="CONTROLS"))
        attempt("detach_synthetic_for_checkpoint_restore", lambda: setattr(animation, "action", None))
        # This internal write restores the before-test checkpoint only. It
        # neither creates nor substitutes for the public persistence assertion.
        attempt("restore_original_correction_metadata", lambda: _restore_property(source, skirt_original_mode.CORRECTIONS, correction_before))
        for saved in poses_before:
            attempt("restore_native_pose_" + saved["rig"].name, lambda saved=saved: _restore_pose(saved, qa))
        for target, name, saved in metadata_before:
            attempt("restore_public_session_metadata_" + target.name + ":" + name,
                    lambda target=target, name=name, saved=saved: _restore_property(target, name, saved))
        attempt("reattach_exact_synthetic_action_and_slot", reattach)
        attempt("reevaluate_original_frame", lambda: scene.frame_set(anchor, subframe=context_before["subframe"]))
        attempt("restore_native_display_checkpoint", lambda: bone_display._rollback(display_before))
        attempt("restore_native_context", lambda: _restore_context(context_before, rig, qa))
        attempt("native_final_update", update)
        if skin is not None and anchor in baseline:
            def restored_geometry():
                drift = errors(baseline[anchor], snapshots())
                ok, assets = protected()
                check("persistent_original_cleanup_native_geometry_cache_assets", max(drift.values()) <= guard
                      and sealed() and ok and _property(source, skirt_original_mode.CORRECTIONS) == correction_before
                      and qa.digest(qa.action_content(action)) == action_before
                      and _constraint_state(rig) == _expected_constraints(poses_before[0])
                      and qa.pose_channels(rig) == poses_before[0]["channels"],
                      errors_m=drift, original_assets=assets, cache_unchanged=sealed())
            attempt("compare_native_restored_checkpoint", restored_geometry)
        if skin is not None:
            attempt("remove_exact_independent_S_mesh_and_Key", lambda: workflow.remove_motion_probe(skin))
        attempt("native_update_after_probe_removal", update)
        attempt("native_final_source_proof", lambda: workflow.motion_objects(source, qa, surface))
        def restored_state():
            state_ok = (workflow.inventory() == inventory_before
                        and workflow.context_content(bpy.context) == context_before
                        and tuple(bpy.data.actions) == protection.action_refs
                        and _property(source, skirt_original_mode.CORRECTIONS) == correction_before
                        and {curve.as_pointer() for curve in _action_curves(action)} == existing_curves
                        and action.as_pointer() == action_pointer and animation.action == action
                        and animation.action_slot == slot and qa.digest(qa.action_content(action)) == action_before
                        and all(_pose_restored(saved, qa) for saved in poses_before)
                        and all(_property(target, name) == saved for target, name, saved in metadata_before)
                        and all(bone_display._snapshot(target) == view for target, view, _raw, _refs in display_before)
                        and all(target.data.get(bone_display.VIEW_KEY) == raw
                                and dict(target.data.get(bone_display.REFS_KEY, {})) == refs
                                for target, _view, raw, refs in display_before)
                        and scene.tool_settings.use_keyframe_insert_auto is False
                        and not body_original_mode.active(rig) and sealed())
            check("persistent_original_cleanup_exact_inventory_action_context", state_ok,
                  inventories_sha256={"before": qa.digest(inventory_before), "after": qa.digest(workflow.inventory())})
        attempt("compare_exact_final_state", restored_state)
        report["cleanup_errors"] = cleanup_errors
        report["cleanup_complete"] = not cleanup_errors
        report["status"] = "PASS" if failure is None and not cleanup_errors else "FAIL"
        report["success"] = report["status"] == "PASS"
    if failure is not None or cleanup_errors:
        detail = str(failure) if failure is not None else "native checkpoint cleanup failed"
        if cleanup_errors:
            detail += "; cleanup: " + "; ".join(item["step"] + ": " + item["error"] for item in cleanup_errors)
        raise RuntimeError("Original refinement QA failed: " + detail) from failure
    return report
