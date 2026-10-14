"""Source snippet for an owned clone's temporary public Body display gesture.

Merge temporary_body_display into the next native harness. This file has no
automatic entry, native execution, product changes, capture or save operation.
"""
from contextlib import contextmanager


@contextmanager
def temporary_body_display(bpy, ctx, rig, package, session, report, label):
    """Reveal through the existing BODY button; restore every affected display."""
    def check(value, message):
        if not value:
            raise RuntimeError(message)

    display, native = package.bone_display, package.unity_animation_rigging
    original = __import__(package.__name__ + '.body_original_mode', fromlist=['body_original_mode'])
    pair = session['original_inputs']

    def input_motions():
        # Reuse the existing bounded Input20 fingerprint. No Body scan,
        # backend validation, capture sampling, file read or frame seek.
        return tuple((int(pair[side + '_action'].as_pointer()), pair[side + '_slot'],
                      native._motion(pair[side + '_action'], pair[side + '_slot']))
                     for side in ('source', 'custom'))

    check(ctx.active_object == rig and rig.mode == 'POSE'
          and not original.active(rig),
          'Use the existing Main Rig in Pose/Controls mode for temporary Body display.')
    collections = display._control_collections(ctx, rig, 'BODY')
    check(len(collections) == 1 and collections[0][0] == rig,
          'Temporary Body display needs the one existing owned Body collection.')
    affected = display._affected(ctx, rig)
    checkpoint = display._checkpoint(affected)
    entry_frame = (ctx.scene.frame_current, ctx.scene.frame_subframe)
    observation = {'label': label, 'completed': False,
        'affected_rigs': [target.name for target in affected],
        'public_operator': 'character_designer.bone_display', 'action': 'BODY',
        'public_operator_executed': False, 'display_restored_exactly': False,
        'Source20_Custom20_unchanged_by_show': False,
        'Source20_Custom20_unchanged_by_restore': False}
    report.setdefault('temporary_Body_display_scopes', []).append(observation)
    primary = None
    try:
        before_show = input_motions()
        if not display._controls_visible(collections):
            # BODY is a toggle. Call it only when its current group is hidden,
            # so this is the artist's normal Show Body gesture, never Hide Body.
            observation['public_operator_executed'] = True
            result = bpy.ops.character_designer.bone_display('EXEC_DEFAULT', action='BODY')
            observation['operator_result'] = sorted(result)
            check(result == {'FINISHED'}, 'The public Body display operator did not finish.')
        check(display._controls_visible(collections), 'The existing Body controls are still not visible.')
        check(input_motions() == before_show, 'Showing Body changed a Source20 or Custom20 Action/slot/input.')
        check((ctx.scene.frame_current, ctx.scene.frame_subframe) == entry_frame,
              'Showing Body changed the current native key frame.')
        observation['Source20_Custom20_unchanged_by_show'] = True
        yield
        observation['completed'] = True
    except Exception as error:
        primary = error
        observation['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if observation.get('operator_result') == ['FINISHED']:
            report['public_UI_operators_executed'] = True
            called = report.setdefault('actual_public_UI_operator_ids', [])
            if observation['public_operator'] not in called:
                called.append(observation['public_operator'])
        try:
            before_restore, input_error = None, None
            try:
                before_restore = input_motions()
            except Exception as error:
                # A broken input proof must not prevent restoring the display.
                input_error = error
            # BODY can clear solo flags on Main and Dress rigs. The official
            # complete checkpoint also retains temporary VIEW/REFS ownership.
            display._rollback(checkpoint)
            check(display._checkpoint(affected) == checkpoint,
                  'Temporary Body display did not restore the exact Main/Dress snapshots and VIEW/REFS.')
            observation['display_restored_exactly'] = True
            if input_error is not None:
                raise RuntimeError('Input20 proof was unavailable before display restore.') from input_error
            check(input_motions() == before_restore,
                  'Restoring Body display changed a Source20 or Custom20 Action/slot/input.')
            check((ctx.scene.frame_current, ctx.scene.frame_subframe) == entry_frame,
                  'Temporary Body display changed the same-frame edit/restore scope.')
            observation['Source20_Custom20_unchanged_by_restore'] = True
        except Exception as error:
            observation['completed'] = False
            observation['restore_error'] = type(error).__name__ + ': ' + str(error)
            if primary is None:
                raise
            primary.add_note('Temporary Body display restore failed: ' + str(error))
