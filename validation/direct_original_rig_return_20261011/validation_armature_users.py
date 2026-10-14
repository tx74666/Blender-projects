"""Native read-only control gates and reversible foreign-reference fixtures."""
import importlib

import bpy


def guard_entrypoints(context, rig, *, require_accepted=True):
    target = importlib.import_module('character_designer.animation_worklist_target')
    display = importlib.import_module('character_designer.bone_display')
    collections = importlib.import_module('character_designer.bone_collections')
    limb = importlib.import_module('character_designer.limb_ik')
    feet = importlib.import_module('character_designer.foot_controls')
    torso = importlib.import_module('character_designer.torso_controls')
    if context.object is not rig:
        raise AssertionError('Native control guard QA requires the exact active Main Rig.')
    settings = limb._settings(context)
    bool_entries = {
        'target.single_armature_user': target.single_armature_user(rig),
        'bone_collections._single_data_user': collections._single_data_user(rig),
        'limb_ik._single_armature_user': limb._single_armature_user(rig),
    }
    if any(value is not require_accepted for value in bool_entries.values()):
        raise AssertionError('Native single-data-user proof disagrees: ' + str(bool_entries))
    calls = {
        'bone_display._editable': lambda: display._editable(rig),
        'limb_ik._require_active_armature': lambda: limb._require_active_armature(context, settings, analyzed=False),
        'foot_controls._active': lambda: feet._active(context, rig),
        'torso_controls._active': lambda: torso._active(context, rig),
    }
    entries = {}
    for name, operation in calls.items():
        try:
            value = operation()
        except ValueError as exc:
            if require_accepted:
                raise AssertionError('Native controller entry rejected authenticated Main Rig: ' + name + ': ' + str(exc)) from exc
            entries[name] = {'rejected': True, 'message': str(exc)}
        else:
            if not require_accepted:
                raise AssertionError('Native controller entry accepted a foreign user: ' + name)
            if name == 'limb_ik._require_active_armature' and value is not rig:
                raise AssertionError('Native Limb guard returned another Armature.')
            entries[name] = {'accepted': True}
    return {'raw_data_users': rig.data.users,
            'actual_bound_objects': sorted(obj.name for obj in bpy.data.objects
                                            if obj.type == 'ARMATURE' and obj.data is rig.data),
            'single_user_helper_results': bool_entries, 'entrypoints': entries}


def legitimate_guards(context, rig):
    result = guard_entrypoints(context, rig)
    collections = importlib.import_module('character_designer.bone_collections')
    original = importlib.import_module('character_designer.body_original_mode')
    try:
        collections._structural_edit_guard(rig)
    except ValueError as exc:
        if not original.active(rig):
            raise AssertionError('Active controls failed the unchanged Collection structural guard: ' + str(exc)) from exc
        result['collection_structural_guard'] = {'blocked_by_preserved_original_mode': True, 'message': str(exc)}
    else:
        if original.active(rig):
            raise AssertionError('Collection structural edits were accepted during Original mode.')
        result['collection_structural_guard'] = {'accepted_controls_mode': True}
    return result


def native_guard_fixtures(context, scene, rig):
    """Exercise real Object and exact ID-ref ownership without editing assets."""
    results = [{'case': 'authenticated_retained_refs_one_actual_rig',
                'proof': legitimate_guards(context, rig)}]
    objects_before = {obj.as_pointer() for obj in bpy.data.objects}
    actions_before = {action.as_pointer() for action in bpy.data.actions}
    data_before = rig.data

    def rejected(name, create, remove):
        value = create()
        try:
            results.append({'case': name, 'proof': guard_entrypoints(context, rig, require_accepted=False)})
        finally:
            remove(value)
        legitimate_guards(context, rig)

    def foreign_object():
        obj = bpy.data.objects.new('QA foreign shared Armature object', rig.data)
        scene.collection.objects.link(obj)
        return obj

    rejected('second_actual_object_sharing_armature', foreign_object,
             lambda obj: bpy.data.objects.remove(obj, do_unlink=True))

    def foreign_action():
        action = bpy.data.actions.new('QA foreign Armature ID reference')
        action['qa_foreign_armature_reference'] = rig.data
        return action

    rejected('foreign_action_id_reference', foreign_action,
             lambda action: bpy.data.actions.remove(action))
    key = 'qa_foreign_armature_reference'
    for owner, name in ((scene, 'foreign_scene_id_reference'), (rig, 'foreign_reference_on_exact_rig')):
        if key in owner:
            raise AssertionError('QA fixture property already exists: ' + owner.name)
        rejected(name, lambda owner=owner: owner.__setitem__(key, rig.data),
                 lambda _value, owner=owner: owner.__delitem__(key))
    saved = scene.character_designer_animation_worklist
    customs = [item.custom_action for item in saved.items if item.rig is rig and item.custom_action]
    if not customs:
        raise AssertionError('Native refs fixture needs retained Custom ownership proof.')
    custom = customs[0]
    if key in custom:
        raise AssertionError('QA fixture property already exists on retained Custom.')
    rejected('foreign_extra_reference_on_exact_owned_custom', lambda: custom.__setitem__(key, rig.data),
             lambda _value: custom.__delitem__(key))
    if ({obj.as_pointer() for obj in bpy.data.objects} != objects_before
            or {action.as_pointer() for action in bpy.data.actions} != actions_before
            or rig.data is not data_before):
        raise AssertionError('Native guard fixture cleanup changed Object/Action/data identities.')
    return {'cases': results, 'object_action_data_identities_restored': True}
