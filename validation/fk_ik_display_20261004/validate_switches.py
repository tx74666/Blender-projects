"""Isolated Cosha display validation and paired-source switch measurements."""
import sys
from pathlib import Path
ARGS = sys.argv[sys.argv.index('--') + 1:]
SOURCE = Path(ARGS[0]).resolve()
LABEL = ARGS[1]
OLD_VALIDATOR = Path(__file__).resolve().parent.parent / 'native_fk_controls_20261004' / 'validate_native_fk.py'
prefix = OLD_VALIDATOR.read_text(encoding='utf-8').split('\ndef main(')[0]
prefix = prefix.replace("CANONICAL = Path(r'D:\\MyRepository\\Blender-addons-by-Randy\\addons')", 'CANONICAL = Path(' + repr(str(SOURCE)) + ')')
exec(compile(prefix, str(OLD_VALIDATOR), 'exec'), globals())
from character_designer import bone_collections, limb_fk_visuals, bone_display


def display(rig, inventory, mode):
    facts = {}
    for key, item in inventory['rigs'].items():
        chain = [rig.pose.bones[name] for name in item['chain']]
        pole = rig.pose.bones[item['pole'].name]
        target = rig.pose.bones[item['target'].name]
        facts[str(key)] = {'native': {pb.name: {'shape': pb.custom_shape.name if pb.custom_shape else None,
            'hide': pb.bone.hide, 'pose_hide': getattr(pb, 'hide', False),
            'hide_select': pb.bone.hide_select,
            'effective_collection': any(c.is_visible_effectively for c in pb.bone.collections)} for pb in chain},
            'pole_hidden': pole.bone.hide or getattr(pole, 'hide', False),
            'target_hidden': target.bone.hide or getattr(target, 'hide', False)}
        if LABEL.startswith('new'):
            if mode == 'FK':
                for pb in chain:
                    if pb.bone.hide or getattr(pb, 'hide', False) or pb.bone.hide_select:
                        raise RuntimeError('FK source is still hidden: ' + pb.name)
                    if not any(c.is_visible_effectively for c in pb.bone.collections):
                        raise RuntimeError('FK source has no visible collection: ' + pb.name)
                for pb in chain[:2]:
                    if pb.custom_shape is not None:
                        raise RuntimeError('Owned FK ring still replaces native bone: ' + pb.name)
                if not facts[str(key)]['pole_hidden'] or not facts[str(key)]['target_hidden']:
                    raise RuntimeError('IK helpers remain visible in FK')
            elif facts[str(key)]['pole_hidden'] or facts[str(key)]['target_hidden'] or pole.custom_shape is None:
                raise RuntimeError('IK cone/target is still hidden')
    return facts


def run():
    if not bpy.app.background:
        raise RuntimeError('Background only')
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(FOLDER / 'X_live_input.blend'), load_ui=False, use_scripts=False)
    rig = bpy.data.objects['CoshaRig']
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    limb_ik._settings(bpy.context).armature = rig
    limb_ik_fk._update(bpy.context, rig)
    inventory = limb_ik._validate_inventory(rig)
    rest_names = tuple(control_pose_assets.native_rest(rig))
    surfaces = body_setup_removal._bound_surfaces(bpy.context, rig)
    before = states(rig, set(), set(), rest_names)
    facts = {'label': LABEL, 'runtime': bpy.app.version_string, 'source': character_designer.__file__,
             'version': list(character_designer.bl_info['version']), 'measurements': [],
             'initial_mode': limb_ik_fk_batch.mode_for_keys(rig, inventory), 'input_state': before}
    # Identical checkpoint, one warm-up round, then three rounds in each run.
    # Two old/new runs in reversed order provide six samples per direction.
    for cycle in range(4):
        cycle_checkpoint = limb_ik_fk_batch._checkpoint(bpy.context, rig, None)
        for mode in ('IK', 'FK'):
            start = time.perf_counter()
            value = limb_ik_fk_batch.switch_all(bpy.context, rig, mode, keyframe=False)
            seconds = time.perf_counter() - start
            if cycle:
                facts['measurements'].append({'mode': mode, 'seconds': seconds})
            # Verification is outside the timed region.
            limb_ik_fk._update(bpy.context, rig)
            pose = matrix_errors(before['pose'], native_pose(rig, rest_names))
            surface = surface_errors(rig, surfaces)
            if pose['maximum'] > POSE_TOLERANCE or surface['maximum'] > SURFACE_TOLERANCE:
                facts['failed_round'] = {'cycle': cycle, 'mode': mode, 'pose': pose, 'surface': surface}
                (FOLDER / (LABEL + '.json')).write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
                raise RuntimeError(f"A switch changed evaluated pose/surface: cycle={cycle}, mode={mode}, pose={pose['maximum']}, surface={surface['maximum']}")
            facts.setdefault('rounds', []).append({'cycle': cycle, 'mode': mode,
                'pose_error': pose['maximum'], 'surface_error': surface['maximum'],
                'display': display(rig, inventory, mode)})
        if cycle < 3:
            limb_ik_fk_batch._rollback(bpy.context, rig, cycle_checkpoint, set())
    check_preserved(facts, 'final', rig, before, surfaces, set(), set(), rest_names)
    if LABEL == 'new1':
        # Actual saved FK authorization survives an isolated native reopen.
        candidate = FOLDER / 'X_display_candidate.blend'
        result = bpy.ops.wm.save_as_mainfile(filepath=str(candidate), check_existing=False)
        if result != {'FINISHED'}: raise RuntimeError('Candidate save failed')
        bpy.ops.wm.open_mainfile(filepath=str(candidate), load_ui=False, use_scripts=False)
        reopened = bpy.data.objects['CoshaRig']
        facts['reopened_display'] = display(reopened, limb_ik._validate_inventory(reopened), 'FK')
    facts['passed'] = True
    (FOLDER / (LABEL + '.json')).write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
    print('COSHA_SWITCH_VALIDATED', LABEL, facts['measurements'], flush=True)


try:
    run()
except Exception:
    (FOLDER / (LABEL + '_error.txt')).write_text(traceback.format_exc(), encoding='utf-8')
    raise
