"""Isolated saved-X palette verification; never saves the artist input path.

Run in an isolated Blender process with --disable-autoexec, for example:
  blender --background X.blend --disable-autoexec --python verify_saved_x.py -- \
      --main-rig <name> --expected-dress-native 33

Modes: apply captures a baseline, applies, saves a validation-only copy and
reopens it; capture only records a protected baseline; verify / --post-live
compares the already opened file with that baseline without writing a .blend.
No subprocess is started by this script.
"""
import argparse
from array import array
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time
import traceback

import bpy


OUTPUT_ROOT = Path(__file__).resolve().parent
CANONICAL = Path(r'D:\MyRepository\Blender-addons-by-Randy')
CHANNELS = ('normal', 'select', 'active')
WORLD_LIMIT = 5e-5
COLOR_LIMIT = .5 / 255 + 1e-6
PALETTE_KEYS = {
    'character_designer_bone_color_palette_v1', '_cd_bone_palette_before_v1',
    '_cd_bone_palette_rigs_v1', '_cd_bone_palette_main_v1',
    '_cd_bone_palette_display_before_v1',
}


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def plain(value):
    if isinstance(value, bpy.types.ID):
        return {'id_type': value.bl_rna.identifier, 'name': value.name,
                'library': str(Path(bpy.path.abspath(value.library.filepath)).resolve())
                if value.library else None}
    if hasattr(value, 'to_dict'):
        return {str(key): plain(item) for key, item in value.to_dict().items()}
    if hasattr(value, 'to_list'):
        return [plain(item) for item in value.to_list()]
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Non-finite value in protected scene data.')
        return value
    if hasattr(value, 'bl_rna') and hasattr(value, 'name'):
        owner = getattr(value, 'id_data', None)
        return {'rna': value.bl_rna.identifier, 'name': value.name,
                'owner': plain(owner) if isinstance(owner, bpy.types.ID) else None}
    try:
        return [plain(item) for item in value]
    except TypeError:
        return {'rna': getattr(getattr(value, 'bl_rna', None), 'identifier', type(value).__name__)}


def properties(owner, *, palette=False):
    return {str(key): plain(value) for key, value in owner.items()
            if palette or key not in PALETTE_KEYS}


def rna(owner, *, skip=()):
    """Writable scalar/array/ID fields, excluding derived evaluation outputs."""
    result = {}
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if name == 'rna_type' or name in skip or prop.is_readonly:
            continue
        if prop.type not in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM', 'POINTER'}:
            continue
        value = getattr(owner, name)
        if prop.type == 'POINTER' and value is not None and not isinstance(value, bpy.types.ID):
            continue
        result[name] = plain(value)
    return result


class Digest:
    """Stream exact raw model values instead of retaining all vertex arrays."""
    def __init__(self):
        self.hash = hashlib.sha256()

    def add(self, tag, value):
        raw = json.dumps([tag, plain(value)], ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
        self.hash.update(struct.pack('<Q', len(raw)))
        self.hash.update(raw)

    def value(self):
        return self.hash.hexdigest()

    def buffer(self, tag, collection, field, width=1, kind='f'):
        """Blender bulk reads avoid JSON/RNA inspection per coordinate."""
        self.add(tag + '_metadata', [field, width, kind, len(collection)])
        values = array(kind, [0]) * (len(collection) * width)
        try:
            collection.foreach_get(field, values)
        except (TypeError, ValueError, AttributeError, RuntimeError):
            # Preserve unfamiliar artist attribute data too. The fallback reads
            # only its declared value field instead of inspecting all RNA.
            self.add(tag + '_encoding', 'focused_values')
            for item in collection:
                self.add(tag + '_value', getattr(item, field))
            return
        self.add(tag + '_encoding', 'little_endian_buffer')
        if sys.byteorder != 'little':
            values.byteswap()
        self.hash.update(values)


def attribute_values(digest, attribute):
    formats = {
        'FLOAT': ('value', 1, 'f'), 'INT': ('value', 1, 'i'),
        'FLOAT_VECTOR': ('vector', 3, 'f'), 'FLOAT2': ('vector', 2, 'f'),
        'FLOAT_COLOR': ('color', 4, 'f'), 'BYTE_COLOR': ('color', 4, 'f'),
        'BOOLEAN': ('value', 1, 'b'), 'INT8': ('value', 1, 'b'),
        'INT32_2D': ('value', 2, 'i'), 'QUATERNION': ('value', 4, 'f'),
    }
    if attribute.data_type in formats:
        field, width, kind = formats[attribute.data_type]
        digest.buffer('attribute_values', attribute.data, field, width, kind)
        return
    # String and future artist attributes have no stable bulk numeric buffer.
    # Their writable scalar/vector payloads remain explicitly protected.
    for item in attribute.data:
        digest.add('artist_attribute_item', rna(item))


def mesh_state(obj):
    mesh, digest = obj.data, Digest()
    digest.add('mesh_fields', rna(mesh))
    digest.add('mesh_properties', properties(mesh))
    digest.add('groups', [(g.name, g.index, g.lock_weight) for g in obj.vertex_groups])
    digest.add('materials', [m.name if m else None for m in mesh.materials])
    digest.buffer('vertex_coordinates', mesh.vertices, 'co', 3)
    for vertex in mesh.vertices:
        digest.add('vertex', [vertex.hide, vertex.select,
                             sorted((entry.group, entry.weight) for entry in vertex.groups)])
    for edge in mesh.edges:
        digest.add('edge', [list(edge.vertices), edge.hide, edge.select,
                           edge.use_seam, edge.use_edge_sharp])
    for face in mesh.polygons:
        digest.add('face', [list(face.vertices), face.material_index,
                           face.use_smooth, face.hide, face.select])
    for loop in mesh.loops:
        digest.add('loop', [loop.vertex_index, loop.edge_index])
    for layer in mesh.uv_layers:
        digest.add('uv_layer', [layer.name, layer.active_render, getattr(layer, 'active_clone', None)])
        digest.buffer('uv_coordinates', layer.data, 'uv', 2)
        for loop in layer.data:
            digest.add('uv', [getattr(loop, 'pin_uv', None),
                              getattr(loop, 'select', None), getattr(loop, 'select_edge', None)])
    # Built-in positions/topology and UV coordinates already have exact hashes.
    # Every artist attribute remains protected; its values use fast bulk reads.
    duplicates = {
        'position': ('FLOAT_VECTOR', 'POINT'),
        '.edge_verts': ('INT32_2D', 'EDGE'),
        '.corner_vert': ('INT', 'CORNER'), '.corner_edge': ('INT', 'CORNER'),
        'material_index': ('INT', 'FACE'),
    }
    duplicates.update({layer.name: ('FLOAT2', 'CORNER') for layer in mesh.uv_layers})
    for attribute in mesh.attributes:
        digest.add('attribute', [attribute.name, attribute.data_type, attribute.domain])
        if duplicates.get(attribute.name) == (attribute.data_type, attribute.domain):
            digest.add('attribute_encoding', 'exact_values_already_protected')
        else:
            attribute_values(digest, attribute)
    keys = mesh.shape_keys
    if keys:
        digest.add('keys', [keys.name, keys.use_relative, keys.eval_time, properties(keys)])
        for key in keys.key_blocks:
            digest.add('key', [key.name, key.relative_key.name, key.value, key.mute,
                               key.slider_min, key.slider_max, key.vertex_group,
                               key.interpolation])
            digest.buffer('key_coordinates', key.data, 'co', 3)
    return {'vertices': len(mesh.vertices), 'edges': len(mesh.edges),
            'polygons': len(mesh.polygons), 'shape_keys': len(keys.key_blocks) if keys else 0,
            'sha256': digest.value()}


def curve_state(obj):
    digest = Digest()
    digest.add('curve', [rna(obj.data), properties(obj.data)])
    for spline in obj.data.splines:
        digest.add('spline', rna(spline))
        for point in spline.points:
            digest.add('point', rna(point))
        for point in spline.bezier_points:
            digest.add('bezier', rna(point))
    return digest.value()


def color_state(color):
    return {'palette': color.palette, 'constraints': color.custom.show_colored_constraints,
            **{name: [int(round(float(v) * 255)) for v in getattr(color.custom, name)]
               for name in CHANNELS}}


def constraints(owner):
    return [rna(con) for con in owner.constraints]


def animation_state(owner):
    animation = owner.animation_data
    if animation is None:
        return None
    result = {'fields': rna(animation), 'drivers': [], 'tracks': []}
    for curve in animation.drivers:
        driver = curve.driver
        result['drivers'].append({
            'curve': rna(curve), 'driver': rna(driver),
            'variables': [{'fields': rna(var), 'targets': [rna(target) for target in var.targets]}
                          for var in driver.variables],
            'modifiers': [rna(mod) for mod in curve.modifiers]})
    for track in animation.nla_tracks:
        result['tracks'].append({'fields': rna(track), 'strips': [rna(strip) for strip in track.strips]})
    return result


def action_state(action):
    result, curves = {'name': action.name, 'properties': properties(action)}, []
    if hasattr(action, 'fcurves'):
        curves.extend(action.fcurves)
    for layer in getattr(action, 'layers', ()):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', ()):
                curves.extend(bag.fcurves)
    result['curves'] = []
    seen = set()
    for curve in curves:
        if curve.as_pointer() in seen:
            continue
        seen.add(curve.as_pointer())
        result['curves'].append({'fields': rna(curve),
                                 'keys': [rna(point) for point in curve.keyframe_points],
                                 'samples': [list(point.co) for point in curve.sampled_points],
                                 'modifiers': [rna(mod) for mod in curve.modifiers]})
    return result


def protected_state(allowed_rigs):
    started = time.perf_counter()
    print('[palette-x] Capturing raw geometry, keys, UV, weights, rest, channels and ownership.', flush=True)
    allowed_rigs = set(allowed_rigs)
    result = {'objects': {}, 'armatures': {}, 'meshes': {}, 'curves': {},
              'actions': [action_state(a) for a in bpy.data.actions],
              'collections': {}, 'scene': {}, 'context': {}}
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        fields = {name: plain(getattr(obj, name)) for name in (
            'type', 'location', 'rotation_mode', 'rotation_euler', 'rotation_quaternion',
            'rotation_axis_angle', 'scale', 'matrix_basis', 'matrix_parent_inverse',
            'matrix_world', 'parent_type', 'parent_bone', 'hide_viewport', 'hide_render',
            'hide_select', 'show_in_front', 'display_type')}
        fields.update(parent=plain(obj.parent), data=plain(obj.data),
                      props=properties(obj), constraints=constraints(obj),
                      modifiers=[rna(modifier) for modifier in obj.modifiers],
                      animation=animation_state(obj))
        result['objects'][obj.name] = fields
        if obj.type == 'MESH':
            result['meshes'][obj.name] = mesh_state(obj)
        elif obj.type == 'CURVE':
            result['curves'][obj.name] = curve_state(obj)
        elif obj.type == 'ARMATURE':
            data = obj.data
            state = {'fields': rna(data, skip={'show_bone_colors'}), 'props': properties(data),
                     'animation': animation_state(data), 'bones': {}, 'pose': {},
                     'active_bone': data.bones.active.name if data.bones.active else None,
                     'collections': [], 'active_collection': data.collections.active.name if data.collections.active else None}
            if obj.name not in allowed_rigs:
                state['show_bone_colors'] = data.show_bone_colors
            for collection in data.collections_all:
                state['collections'].append({
                    'name': collection.name, 'parent': collection.parent.name if collection.parent else None,
                    'visible': collection.is_visible, 'solo': collection.is_solo,
                    'expanded': collection.is_expanded, 'props': properties(collection),
                    'bones': sorted(bone.name for bone in collection.bones)})
            for bone in data.bones:
                state['bones'][bone.name] = {
                    'rest': plain(bone.matrix_local), 'head': list(bone.head_local),
                    'tail': list(bone.tail_local), 'parent': bone.parent.name if bone.parent else None,
                    'fields': rna(bone), 'props': properties(bone),
                    'collections': sorted(c.name for c in bone.collections),
                    'native_color': color_state(bone.color)}
            for pb in obj.pose.bones:
                state['pose'][pb.name] = {
                    'channels': {name: plain(getattr(pb, name)) for name in (
                        'location', 'rotation_mode', 'rotation_euler', 'rotation_quaternion',
                        'rotation_axis_angle', 'scale', 'matrix_basis', 'lock_location',
                        'lock_rotation', 'lock_scale', 'lock_rotation_w', 'lock_rotations_4d',
                        'custom_shape', 'custom_shape_transform', 'custom_shape_scale_xyz',
                        'custom_shape_translation', 'custom_shape_rotation_euler',
                        'use_custom_shape_bone_size')},
                    'constraints': constraints(pb), 'props': properties(pb),
                    'selected': pb.select if hasattr(pb, 'select') else pb.bone.select,
                    'hide': pb.hide if hasattr(pb, 'hide') else pb.bone.hide}
            result['armatures'][obj.name] = state
    for collection in bpy.data.collections:
        result['collections'][collection.name] = {
            'objects': sorted(obj.name for obj in collection.objects),
            'children': sorted(child.name for child in collection.children),
            'hide_viewport': collection.hide_viewport, 'hide_render': collection.hide_render,
            'hide_select': collection.hide_select, 'props': properties(collection)}
    scene = bpy.context.scene
    result['scene'] = {'name': scene.name, 'frame': scene.frame_current,
                       'subframe': scene.frame_subframe, 'props': properties(scene),
                       'world': plain(scene.world), 'animation': animation_state(scene),
                       'auto_key': scene.tool_settings.use_keyframe_insert_auto}
    active = bpy.context.view_layer.objects.active
    result['context'] = {'active': active.name if active else None, 'mode': bpy.context.mode,
                         'selected': sorted(obj.name for obj in bpy.context.selected_objects),
                         'view_layer': bpy.context.view_layer.name,
                         'object_visibility': {obj.name: obj.hide_get(view_layer=bpy.context.view_layer)
                                               for obj in bpy.context.view_layer.objects}}
    print(f'[palette-x] Protected snapshot complete: {len(result["meshes"])} meshes, '
          f'{len(result["armatures"])} rigs, {time.perf_counter()-started:.2f}s.', flush=True)
    return result


def world_bones():
    graph = bpy.context.evaluated_depsgraph_get()
    return {obj.name: {pb.name: plain(obj.matrix_world @ pb.matrix) for pb in obj.evaluated_get(graph).pose.bones}
            for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def world_meshes(*, capture=False, expected=None):
    """Stream all evaluated world coordinates to gzip; comparison is bounded."""
    started = time.perf_counter()
    print(f'[palette-x] {"Capturing" if capture else "Comparing"} evaluated world meshes.', flush=True)
    graph, result = bpy.context.evaluated_depsgraph_get(), {}
    for obj in sorted(bpy.context.scene.objects, key=lambda item: item.name):
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            if capture:
                relative = 'world/' + hashlib.sha256(obj.name.encode('utf-8')).hexdigest()[:24] + '.xyz.gz'
                path = safe_output(relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(path, 'wb') as handle:
                    for vertex in mesh.vertices:
                        handle.write(struct.pack('<ddd', *(evaluated.matrix_world @ vertex.co)))
                result[obj.name] = {'count': len(mesh.vertices), 'path': relative, 'sha256': sha_file(path)}
            else:
                before = expected[obj.name]
                if len(mesh.vertices) != before['count']:
                    raise AssertionError(f'Evaluated vertex count changed for {obj.name}.')
                maximum = 0.0
                baseline_file = safe_output(before['path'])
                if sha_file(baseline_file) != before['sha256']:
                    raise AssertionError('The evaluated world-coordinate baseline hash changed.')
                with gzip.open(baseline_file, 'rb') as handle:
                    for vertex in mesh.vertices:
                        stored = handle.read(24)
                        if len(stored) != 24:
                            raise AssertionError('The evaluated world-coordinate baseline is truncated.')
                        old = struct.unpack('<ddd', stored)
                        current = evaluated.matrix_world @ vertex.co
                        maximum = max(maximum, math.sqrt(sum((a-b)**2 for a, b in zip(current, old))))
                    if handle.read(1):
                        raise AssertionError('The evaluated world-coordinate baseline has extra vertices.')
                result[obj.name] = {'count': len(mesh.vertices), 'maximum_position_error': maximum}
                if maximum > WORLD_LIMIT:
                    raise AssertionError(f'Evaluated geometry changed for {obj.name}: {maximum:g}.')
        finally:
            evaluated.to_mesh_clear()
    if not capture and set(result) != set(expected):
        raise AssertionError('The evaluated scene mesh inventory changed.')
    print(f'[palette-x] Evaluated meshes complete: {len(result)} meshes, '
          f'{time.perf_counter()-started:.2f}s.', flush=True)
    return result


def compare(actual, expected, *, tolerance=1e-7, path='scene', differences=None):
    differences = [] if differences is None else differences
    if len(differences) >= 20:
        return differences
    if isinstance(actual, dict) and isinstance(expected, dict):
        for key in sorted(set(actual) | set(expected)):
            if key not in actual or key not in expected:
                differences.append(f'{path}.{key}: presence changed')
            else:
                compare(actual[key], expected[key], tolerance=tolerance,
                        path=f'{path}.{key}', differences=differences)
    elif isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            differences.append(f'{path}: length {len(expected)} -> {len(actual)}')
        for index, (a, b) in enumerate(zip(actual, expected)):
            compare(a, b, tolerance=tolerance, path=f'{path}[{index}]', differences=differences)
    elif isinstance(actual, float) or isinstance(expected, float):
        if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)) or abs(actual-expected) > tolerance:
            differences.append(f'{path}: {expected!r} -> {actual!r}')
    elif actual != expected:
        differences.append(f'{path}: {expected!r} -> {actual!r}')
    return differences


def safe_output(value):
    path = (OUTPUT_ROOT / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    if path != OUTPUT_ROOT and OUTPUT_ROOT not in path.parents:
        raise ValueError('All validation outputs must stay in the palette validation directory.')
    return path


def source_hashes(source):
    files = {path.relative_to(source).as_posix(): sha_file(path)
             for path in sorted((source / 'addons' / 'character_designer').rglob('*.py'))}
    return {'files': files, 'aggregate': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


def pose_colors():
    return {obj.name: {pb.name: color_state(pb.color) for pb in obj.pose.bones}
            for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def palette_records():
    return {obj.name: {'object': {key: plain(obj.get(key)) for key in PALETTE_KEYS if key in obj},
                       'data': {key: plain(obj.data.get(key)) for key in PALETTE_KEYS if key in obj.data},
                       'show_bone_colors': obj.data.show_bone_colors,
                       'pose': {pb.name: {key: plain(pb.get(key)) for key in PALETTE_KEYS if key in pb}
                                for pb in obj.pose.bones}}
            for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def resolve_main(palette, display, requested):
    if requested:
        main = bpy.data.objects.get(requested)
        if main is None or main.type != 'ARMATURE':
            raise ValueError(f'Character armature {requested!r} is missing.')
        return palette.main_for(main)
    main = display.character_rig(bpy.context)
    if main:
        return main
    candidates = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE'
                  and ('character_designer_body_original_mode_v1' in obj
                       or (obj.data.collections_all.get('Original')
                           and obj.data.collections_all['Original'].get('character_designer_simple_bone_group') == 'Original'))]
    if len(candidates) != 1:
        raise ValueError('Use --main-rig to identify exactly one saved-X character.')
    return candidates[0]


def assertions(main, palette, original, expected_native, before_colors=None):
    saved = palette._read(main)
    if not saved or not saved['enabled']:
        raise AssertionError('The character palette preferences are not saved and enabled.')
    membership = palette.members(main, bpy.context)
    native = original._native_groups(bpy.context, main)
    dress_native = {(rig.name, name) for rig, names in native['DRESS'].items() for name in names}
    if expected_native is not None and len(dress_native) != expected_native:
        raise AssertionError(f'Expected {expected_native} native Dress bones, found {len(dress_native)}.')
    if not dress_native:
        raise AssertionError('Saved X has no native Dress targets.')
    for group, bones in membership.items():
        expected = palette.group_colors(main, group)
        group_bytes = set()
        for pb in bones:
            backup = palette._backup(pb)
            if backup['owner'] != saved['id'] or backup['group'] != group:
                raise AssertionError(f'Palette recovery ownership mismatch on {pb.id_data.name}/{pb.name}.')
            actual = color_state(pb.color)
            actual_float = {name: list(getattr(pb.color.custom, name)) for name in CHANNELS}
            # Blender's nearest byte at an exact half-step may be either
            # adjacent byte after float32 conversion. Compare requested floats
            # within half a step; save/reopen below still compares exact bytes.
            if (actual['palette'] != 'CUSTOM' or actual['constraints']
                    or any(abs(a-b) > COLOR_LIMIT for name in CHANNELS
                           for a, b in zip(actual_float[name], expected[name]))):
                raise AssertionError(f'{group} color mismatch on {pb.id_data.name}/{pb.name}: '
                                     f'actual={actual}, actual_float={actual_float}, expected_float={expected}, '
                                     f'half_byte_limit={COLOR_LIMIT}.')
            group_bytes.add(tuple(v for name in CHANNELS for v in actual[name]))
        if len(group_bytes) > 1:
            raise AssertionError(f'{group} members have mixed stored RGB bytes after Apply.')
    arms = membership['ARMS']
    # Verify literal wrist/hand/end sources separately in addition to every
    # mapped arm, forearm and finger on either side.
    native_arms = [pb for pb in arms if pb.name in native.get('BODY', {}).get(pb.id_data, set())]
    hand_wrist = [pb for pb in native_arms if any(word in pb.name.lower() for word in ('wrist', 'hand'))]
    if not native_arms or not hand_wrist:
        raise AssertionError('Saved X native Arm / Hand / Wrist membership was not resolved.')
    dress = palette.group_colors(main, 'DRESS')['normal']
    if not dress[0] > dress[2] > dress[1]:
        raise AssertionError('Saved Dress scheme is not the expected soft pink hue.')
    targets = {(pb.id_data.name, pb.name) for bones in membership.values() for pb in bones}
    foreign = 0
    if before_colors is not None:
        after = pose_colors()
        for rig_name, bones in before_colors.items():
            for name, color in bones.items():
                if (rig_name, name) not in targets:
                    foreign += 1
                    if after[rig_name][name] != color:
                        raise AssertionError(f'Foreign/helper color changed on {rig_name}/{name}.')
    return {'group_counts': {group: len(bones) for group, bones in membership.items()},
            'native_dress_count': len(dress_native), 'native_arms_count': len(native_arms),
            'native_hand_wrist_count': len(hand_wrist), 'native_hand_wrist_names': sorted(pb.name for pb in hand_wrist),
            'foreign_or_helper_bones_unchanged': foreign,
            'dress_native': sorted([list(item) for item in dress_native]),
            'requested_rgb_float': {group: palette.group_colors(main, group) for group in palette.GROUPS},
            'displayed_rgba_bytes': {group: {name: color_state(bones[0].color)[name] + [255]
                                           for name in CHANNELS} if bones else None
                                     for group, bones in membership.items()}}


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--source', type=Path, default=CANONICAL)
    args.add_argument('--main-rig', default='')
    args.add_argument('--mode', choices=('apply', 'capture', 'verify'), default='apply')
    args.add_argument('--post-live', action='store_true')
    args.add_argument('--baseline', default='protected_baseline.json')
    args.add_argument('--candidate', default='X_palette_candidate.blend')
    args.add_argument('--report', default='saved_x_palette_report.json')
    args.add_argument('--expected-dress-native', type=int, default=33)
    opts = args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if opts.post_live:
        opts.mode = 'verify'
    baseline_path, candidate, report_path = (safe_output(value) for value in (opts.baseline, opts.candidate, opts.report))
    source = opts.source.resolve()
    report = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'mode': opts.mode, 'blender_version': bpy.app.version_string,
              'blender_binary': bpy.app.binary_path, 'artist_input': bpy.data.filepath,
              'autoexec_disabled': not bpy.context.preferences.filepaths.use_scripts_auto_execute,
              'script_sha256': sha_file(__file__), 'source': str(source),
              'errors': [], 'limits': {'bone_world_matrix': WORLD_LIMIT,
                                      'evaluated_world_vertex_position': WORLD_LIMIT,
                                      'requested_color_float': COLOR_LIMIT,
                                      'stored_colors': 'exact stored RGB bytes after save/reopen; RGBA alpha 255'}}
    input_path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    input_hash = sha_file(input_path) if input_path and input_path.is_file() else None
    before_source = source_hashes(source)
    report['source_hashes'] = before_source
    try:
        if input_path is None:
            raise ValueError('Open the saved artist X .blend in this isolated process first.')
        if opts.mode == 'apply' and input_path == candidate:
            raise ValueError('The artist input and validation candidate paths must differ.')
        sys.path[:0] = [str(source / 'addons'), str(source / 'tests')]
        import character_designer
        from character_designer import bone_color_palette as palette, bone_display as display, body_original_mode as original
        loaded = Path(character_designer.__file__).resolve()
        if source not in loaded.parents:
            raise ValueError(f'The loaded add-on is not canonical: {loaded}')
        if not hasattr(bpy.types.Object, 'character_designer_body_calibration'):
            character_designer.register()
        main_rig = resolve_main(palette, display, opts.main_rig)
        report['main_rig'] = main_rig.name
        bpy.context.view_layer.update()
        if opts.mode in {'apply', 'capture'}:
            membership = palette.members(main_rig, bpy.context)
            allowed = sorted({pb.id_data.name for bones in membership.values() for pb in bones})
            baseline = {'version': 2, 'fingerprint_format': 'focused_bulk_values_v2',
                        'artist_input': str(input_path), 'artist_sha256': input_hash,
                        'source_hashes': before_source, 'main_rig': main_rig.name,
                        'allowed_color_rigs': allowed, 'protected': protected_state(allowed),
                        'world_bones': world_bones(), 'world_meshes': world_meshes(capture=True),
                        'pose_colors_before': pose_colors()}
            baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')
            if opts.mode == 'capture':
                report['baseline'] = str(baseline_path)
                report['passed'] = True
                return
            report['colored_bones'] = palette.apply_palette(main_rig, bpy.context)
            report['after_apply'] = assertions(main_rig, palette, original, opts.expected_dress_native,
                                               baseline['pose_colors_before'])
            differences = compare(protected_state(allowed), baseline['protected'])
            differences += compare(world_bones(), baseline['world_bones'], tolerance=WORLD_LIMIT, path='world_bones')
            if differences:
                raise AssertionError('Protected artist state changed after Apply: ' + '\n'.join(differences[:20]))
            report['world_meshes_after_apply'] = world_meshes(expected=baseline['world_meshes'])
            baseline['palette_after'] = palette_records()
            baseline['pose_colors_after'] = pose_colors()
            baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')
            # copy=True preserves the input filepath; only this explicit path
            # under OUTPUT_ROOT is writable, and the original input is hashed.
            result = bpy.ops.wm.save_as_mainfile(filepath=str(candidate), copy=True, check_existing=False)
            if result != {'FINISHED'} or not candidate.is_file():
                raise AssertionError('Blender did not confirm saving the isolated candidate copy.')
            report['candidate'] = str(candidate)
            report['candidate_sha256'] = sha_file(candidate)
            report['save_result'] = sorted(result)
            bpy.ops.wm.open_mainfile(filepath=str(candidate), load_ui=False, use_scripts=False)
            bpy.context.view_layer.update()
        else:
            baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
            if baseline.get('fingerprint_format') != 'focused_bulk_values_v2':
                raise ValueError('Capture a fresh protected baseline with this verifier before post-live verification.')
            allowed = baseline['allowed_color_rigs']
        main_rig = bpy.data.objects.get(baseline['main_rig'])
        if main_rig is None:
            raise AssertionError('The baseline character is missing after reopen / live-save verification.')
        report['after_reopen_or_verify'] = assertions(main_rig, palette, original, opts.expected_dress_native,
                                                       baseline['pose_colors_before'])
        differences = compare(protected_state(allowed), baseline['protected'])
        differences += compare(world_bones(), baseline['world_bones'], tolerance=WORLD_LIMIT, path='world_bones')
        if 'palette_after' in baseline:
            differences += compare(palette_records(), baseline['palette_after'], path='saved_palette')
            differences += compare(pose_colors(), baseline['pose_colors_after'], path='saved_rgb_bytes')
        if differences:
            raise AssertionError('Protected / saved palette state changed: ' + '\n'.join(differences[:20]))
        report['world_meshes_after_reopen_or_verify'] = world_meshes(expected=baseline['world_meshes'])
        report['baseline'] = str(baseline_path)
        report['passed'] = True
    except Exception as exc:
        report['passed'] = False
        report['errors'].append(f'{type(exc).__name__}: {exc}')
        report['traceback'] = traceback.format_exc()
    finally:
        report['source_hash_unchanged'] = source_hashes(source) == before_source
        report['input_sha256_before'] = input_hash
        report['input_sha256_after'] = sha_file(input_path) if input_path and input_path.is_file() else None
        report['artist_input_unchanged'] = report['input_sha256_after'] == input_hash
        if not report['source_hash_unchanged'] or not report['artist_input_unchanged']:
            report['passed'] = False
            report['errors'].append('The canonical source or original input changed during validation.')
        report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({key: report.get(key) for key in ('passed', 'main_rig', 'colored_bones', 'errors',
                                                          'candidate', 'source_hash_unchanged', 'artist_input_unchanged')},
                         ensure_ascii=False, indent=2))
    if not report.get('passed'):
        raise RuntimeError(f'Saved-X palette validation failed; see {report_path}')


if __name__ == '__main__':
    main()
