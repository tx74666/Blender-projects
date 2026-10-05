"""Isolated saved-X Hair validation; never run in the artist GUI session.

Use --background --factory-startup --disable-autoexec and an explicit saved X.
CD_WIGGLE_TEST_ROOT points to the isolated official Wiggle 1.1.2 package.
Writes only two source metadata properties and an independent copy=True .blend.
No install, baking, new keys, subprocess, GUI or Unity operation is performed.
"""
import array
import ast
import collections
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import struct
import sys
import time

import bpy
from mathutils import Matrix, Vector

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
from character_designer import hair_bones_rig as hair
from character_designer import hair_strand_registry as registry
from character_designer import hair_motion_profiles as profiles
from character_designer import hair_wiggle_adapter as adapter

EXPECTED_UID = '331afdb7e5154ae1aaa39603a4f61768'
ALLOWED_METADATA = {registry.REGISTRY_KEY, profiles.PROFILE_KEY}
ROTATION_FIELDS = {'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'rotation_mode',
                   'matrix', 'matrix_basis', 'matrix_world'}
OBJECT_FIELDS = ROTATION_FIELDS | {'location', 'scale', 'delta_location', 'delta_rotation_euler',
                                 'delta_rotation_quaternion', 'delta_scale'}
OUTPUT = Path(os.environ.get('CD_HAIR_VALIDATION_OUTPUT', str(DIRECTORY / 'real_hair_preview_validation.json')))


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encode(value, *, portable=False):
    if isinstance(value, bpy.types.ID):
        result = {'id_type': value.bl_rna.identifier, 'name': value.name_full,
                  'library': value.library.filepath if value.library else None}
        if not portable:
            result['pointer'] = value.as_pointer()
        return result
    if isinstance(value, dict):
        return {str(key): encode(item, portable=portable) for key, item in value.items()}
    if isinstance(value, (tuple, list, array.array)):
        return [encode(item, portable=portable) for item in value]
    return value


class Digests:
    def __init__(self):
        self.native = hashlib.sha256()
        self.portable = hashlib.sha256()

    def update(self, data):
        self.native.update(data)
        self.portable.update(data)


def without_native_pointer_tokens(value, pointer_names):
    # _rna_snapshot represents ID references as (pointer, name_full).
    if (isinstance(value, (tuple, list)) and len(value) == 2
            and isinstance(value[0], int) and isinstance(value[1], str)):
        identity = pointer_names.get((value[0], value[1]))
        if identity is not None:
            return identity
    if isinstance(value, (tuple, list)):
        return [without_native_pointer_tokens(item, pointer_names) for item in value]
    return value


def feed(digest, value):
    for target, portable in ((digest.native, False), (digest.portable, True)):
        serialized = encode(value, portable=portable)
        if portable:
            serialized = without_native_pointer_tokens(serialized, digest.pointer_names)
        target.update(json.dumps(serialized, sort_keys=True, ensure_ascii=False,
                                separators=(',', ':'), allow_nan=False).encode('utf8'))


def coordinates(digest, items, field, width, code='f'):
    data = array.array(code, [0]) * (len(items) * width)
    if data:
        items.foreach_get(field, data)
        digest.update(data.tobytes())
    return len(data) * data.itemsize


def asset_fingerprint(source):
    """Sequential raw data hashing, one coordinate block at a time."""
    began = time.perf_counter()
    digest = Digests()
    digest.pointer_names = {(item.as_pointer(), item.name_full): encode(item, portable=True)
        for group in (bpy.data.actions, bpy.data.objects, bpy.data.meshes, bpy.data.armatures,
                      bpy.data.shape_keys, bpy.data.scenes, bpy.data.materials, bpy.data.collections,
                      bpy.data.node_groups, bpy.data.images) for item in group}
    counts = collections.Counter()
    for mesh in sorted(bpy.data.meshes, key=lambda item: item.name_full):
        feed(digest, (mesh.name_full, len(mesh.vertices), len(mesh.edges), len(mesh.polygons)))
        counts['meshes'] += 1
        counts['vertices'] += len(mesh.vertices)
        counts['coordinate_bytes'] += coordinates(digest, mesh.vertices, 'co', 3)
        coordinates(digest, mesh.edges, 'vertices', 2, 'i')
        coordinates(digest, mesh.loops, 'vertex_index', 1, 'i')
        coordinates(digest, mesh.polygons, 'loop_start', 1, 'i')
        coordinates(digest, mesh.polygons, 'loop_total', 1, 'i')
        coordinates(digest, mesh.polygons, 'material_index', 1, 'i')
        feed(digest, list(mesh.materials))
        for layer in mesh.uv_layers:
            feed(digest, (layer.name, layer.active_render, getattr(layer, 'active_clone', False)))
            if hasattr(layer, 'uv'):
                counts['uv_bytes'] += coordinates(digest, layer.uv, 'vector', 2)
            else:
                counts['uv_bytes'] += coordinates(digest, layer.data, 'uv', 2)
            counts['uv_layers'] += 1
        if mesh.shape_keys:
            feed(digest, (mesh.shape_keys.name_full, mesh.shape_keys.use_relative,
                          mesh.shape_keys.eval_time))
            for key in mesh.shape_keys.key_blocks:
                counts['shape_keys'] += 1
                feed(digest, (key.name, key.value, key.mute, key.slider_min, key.slider_max,
                              key.relative_key.name if key.relative_key else None))
                counts['coordinate_bytes'] += coordinates(digest, key.data, 'co', 3)
    for ob in sorted(bpy.data.objects, key=lambda item: item.name_full):
        custom = {key: adapter._clone(ob[key]) for key in ob.keys()
                  if ob != source or key not in ALLOWED_METADATA}
        feed(digest, (ob.name_full, ob.type, custom, ob.data, ob.parent, ob.parent_type, ob.parent_bone,
                      [list(row) for row in ob.matrix_parent_inverse],
                      [(slot.link, slot.material) for slot in ob.material_slots]))
        if ob.animation_data:
            feed(digest, adapter._rna_snapshot(ob.animation_data))
        for modifier in ob.modifiers:
            if modifier.type == 'ARMATURE':
                feed(digest, (ob.name_full, adapter._rna_snapshot(modifier)))
                counts['armature_modifiers'] += 1
        if ob.type == 'MESH':
            feed(digest, [(group.name, group.index, group.lock_weight) for group in ob.vertex_groups])
            for vertex in ob.data.vertices:
                for entry in vertex.groups:
                    digest.update(struct.pack('<IId', vertex.index, entry.group, entry.weight))
                    counts['weight_assignments'] += 1
        if ob.type == 'ARMATURE':
            for bone in ob.data.bones:
                feed(digest, (bone.name, adapter._bone_proof(bone),
                              {key: adapter._clone(bone[key]) for key in bone.keys()}))
                counts['rest_bones'] += 1
    for action in sorted(bpy.data.actions, key=lambda item: item.name_full):
        feed(digest, (action.name_full, adapter._rna_snapshot(action),
                      {key: adapter._clone(action[key]) for key in action.keys()}))
        counts['actions'] += 1
    return {'sha256': digest.native.hexdigest(), 'portable_sha256': digest.portable.hexdigest(),
            'counts': dict(counts),
            'elapsed_seconds': time.perf_counter() - began,
            'method': 'raw foreach_get coordinate/UV arrays + streamed weights/Rest + material/parent/Armature modifier/Action proof',
            'portable_method': 'ID references use RNA type/name/library; byte data is unchanged; compare only the same fingerprint schema'}


def pose_snapshot():
    scene = bpy.context.scene
    result = {'channels': [], 'custom': [adapter._pose_custom(scene)], 'raw': [adapter._raw_snapshot(scene)],
              'shapes': [], 'frame': scene.frame_current, 'subframe': scene.frame_subframe,
              'autokey': scene.tool_settings.use_keyframe_insert_auto}
    for ob in scene.objects:
        result['channels'].append(adapter._channels(ob, True))
        result['custom'].append(adapter._pose_custom(ob))
        if ob.type == 'ARMATURE':
            result['raw'].append(adapter._raw_snapshot(ob))
            for bone in ob.pose.bones:
                result['channels'].append(adapter._channels(bone))
                result['custom'].append(adapter._pose_custom(bone))
                result['raw'].append(adapter._raw_snapshot(bone))
        if ob.type == 'MESH' and ob.data.shape_keys:
            keys = ob.data.shape_keys
            result['shapes'].append((keys, keys.eval_time, [(key, key.value) for key in keys.key_blocks]))
    return result


def check_pose(saved):
    maximum = 0.0
    for owner, mode, channels in saved['channels']:
        require(owner.rotation_mode == mode, 'Rotation mode changed: ' + owner.name)
        for name, values in channels.items():
            error = max((abs(a - b) for a, b in zip(getattr(owner, name), values)), default=0.0)
            require(math.isfinite(error), 'Nonfinite restored channel: ' + owner.name)
            maximum = max(maximum, error)
    require(maximum <= 1e-6, 'Pose channels were not restored within native float tolerance.')
    for owner, values in saved['custom']:
        require(all(adapter._clone(owner[key]) == value for key, value in values.items()),
                'A numeric author pose property changed: ' + owner.name)
    for owner, existed, value in saved['raw']:
        require(owner.is_property_set('wiggle') == existed, 'Native Wiggle presence changed: ' + owner.name)
        if existed:
            require(adapter._clone(owner.wiggle) == value, 'Native Wiggle values changed: ' + owner.name)
    for keys, evaluation, values in saved['shapes']:
        require(keys.eval_time == evaluation and all(key.value == value for key, value in values),
                'Author Shape Key values changed: ' + keys.name)
    scene = bpy.context.scene
    require((scene.frame_current, scene.frame_subframe) == (saved['frame'], saved['subframe']),
            'Author frame/subframe changed.')
    require(scene.tool_settings.use_keyframe_insert_auto == saved['autokey'], 'AutoKey changed.')
    return {'ok': True, 'maximum_channel_error': maximum, 'channels_tolerance': 1e-6,
            'native_pg_exact': True, 'shape_values_exact': True, 'custom_pose_exact': True, 'frame_exact': True}


def paths(armature):
    return adapter._driver_paths(armature) + adapter._animated_paths(armature)


def rotation_conflicts(armature, bone):
    prefix = bone.path_from_id() + '.'
    return [path for path in paths(armature)
            if path.startswith(prefix) and path[len(prefix):].split('.', 1)[0] in ROTATION_FIELDS]


def custom_property_address(path):
    """Parse only ID[scalar] or ID.pose.bones[name][scalar], without eval."""
    text = 'owner' + path if path.startswith('[') else 'owner.' + path
    expression = ast.parse(text, mode='eval').body
    if not isinstance(expression, ast.Subscript) or not isinstance(expression.slice, ast.Constant):
        raise ValueError('Driver source must be a complete custom scalar property address.')
    key = expression.slice.value
    if not isinstance(key, str):
        raise ValueError('Driver source custom property key must be a string.')
    holder = expression.value
    if isinstance(holder, ast.Name) and holder.id == 'owner':
        return None, key
    if (isinstance(holder, ast.Subscript) and isinstance(holder.slice, ast.Constant)
            and isinstance(holder.slice.value, str) and isinstance(holder.value, ast.Attribute)
            and holder.value.attr == 'bones' and isinstance(holder.value.value, ast.Attribute)
            and holder.value.value.attr == 'pose' and isinstance(holder.value.value.value, ast.Name)
            and holder.value.value.value.id == 'owner'):
        return holder.slice.value, key
    raise ValueError('Transform, nested, indexed or arbitrary RNA driver source is unsupported.')


def pure_arithmetic(expression, values):
    """Interpret a bounded numeric AST; never execute a Python expression."""
    tree = ast.parse(expression, mode='eval')
    if len(expression) > 256 or sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError('Driver arithmetic exceeds this proof scope.')

    def number(node):
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            result = float(node.value)
        elif isinstance(node, ast.Name) and node.id in values:
            result = values[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result = number(node.operand) * (-1.0 if isinstance(node.op, ast.USub) else 1.0)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = number(node.left), number(node.right)
            if isinstance(node.op, ast.Add):
                result = a + b
            elif isinstance(node.op, ast.Sub):
                result = a - b
            elif isinstance(node.op, ast.Mult):
                result = a * b
            else:
                result = a / b
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {'min', 'max'} and 2 <= len(node.args) <= 8 and not node.keywords):
            args = [number(item) for item in node.args]
            result = min(args) if node.func.id == 'min' else max(args)
        else:
            raise ValueError('Driver has arbitrary names, functions, attributes or unsupported operations.')
        if not math.isfinite(result):
            raise ValueError('Driver arithmetic is not finite.')
        return result

    return number(tree.body)


def curve_mapping_snapshot(curve):
    return {'extrapolation': curve.extrapolation,
        'keyframe_points': [adapter._rna_snapshot(point) for point in curve.keyframe_points],
        'sampled_points': [adapter._rna_snapshot(point) for point in curve.sampled_points],
        'modifiers': [adapter._rna_snapshot(modifier) for modifier in curve.modifiers]}


def native_curve_mapping_proof(curve):
    """Native mappings have no scene target or Python callback dependencies."""
    if (len(curve.keyframe_points) > 1024 or len(curve.sampled_points) > 4096 or len(curve.modifiers) > 16):
        raise ValueError('Native driver mapping exceeds the bounded snapshot proof scope.')
    if curve.extrapolation not in {'CONSTANT', 'LINEAR'}:
        raise ValueError('Unknown native driver extrapolation.')
    interpolation = {'CONSTANT', 'LINEAR', 'BEZIER', 'SINE', 'QUAD', 'CUBIC', 'QUART', 'QUINT',
                     'EXPO', 'CIRC', 'BACK', 'BOUNCE', 'ELASTIC'}
    easing = {'AUTO', 'EASE_IN', 'EASE_OUT', 'EASE_IN_OUT'}
    handles = {'FREE', 'VECTOR', 'ALIGNED', 'AUTO', 'AUTO_CLAMPED'}
    for point in curve.keyframe_points:
        if (point.interpolation not in interpolation or point.easing not in easing
                or point.handle_left_type not in handles or point.handle_right_type not in handles):
            raise ValueError('Unknown native keyframe interpolation/handle mapping.')
    native_modifiers = {'GENERATOR': 'FModifierGenerator', 'FNGENERATOR': 'FModifierFunctionGenerator',
        'ENVELOPE': 'FModifierEnvelope', 'CYCLES': 'FModifierCycles', 'NOISE': 'FModifierNoise',
        'LIMITS': 'FModifierLimits', 'STEPPED': 'FModifierStepped'}
    for modifier in curve.modifiers:
        if native_modifiers.get(modifier.type) != modifier.bl_rna.identifier:
            raise ValueError('Unknown/custom driver modifier implementation.')
        if any(prop.type == 'POINTER' and prop.identifier not in {'rna_type'}
               for prop in modifier.bl_rna.properties):
            raise ValueError('Driver modifier has an unproven external pointer dependency.')
        if modifier.type == 'FNGENERATOR' and modifier.function_type not in {'SIN', 'COS', 'TAN', 'SQRT', 'LN', 'SINC'}:
            raise ValueError('Unknown native function-generator operation.')
    result = curve_mapping_snapshot(curve)

    def finite(value):
        if isinstance(value, (tuple, list)):
            return all(finite(item) for item in value)
        if isinstance(value, dict):
            return all(finite(item) for item in value.values())
        return not isinstance(value, (int, float)) or math.isfinite(value)

    if not finite(result):
        raise ValueError('Native mapping coordinates, handles or modifier parameters are not finite.')
    return {**result, 'proved': True,
        'scope': 'finite native FCurve knots/handles/samples and recognized built-in target-free modifiers',
        'identity_mapping_required': False,
        'reason': 'Ancestry independence needs a target-free native mapping, not an identity response.'}


def scalar_driver_proof(curve, armature, hair_names):
    """Prove a native simple SCRIPTED transform driver reads only author scalars."""
    driver = curve.driver
    if (curve.mute or driver.type != 'SCRIPTED' or driver.use_self
            or not getattr(driver, 'is_simple_expression', False) or not driver.is_valid):
        raise ValueError('Driver must be valid native simple SCRIPTED arithmetic without self.')
    mapping = native_curve_mapping_proof(curve)
    values, variables = {}, []
    for variable in driver.variables:
        if (variable.type != 'SINGLE_PROP' or len(variable.targets) != 1
                or not variable.name.isidentifier() or variable.name.startswith('__')
                or variable.name in values or variable.name in {'min', 'max'}):
            raise ValueError('Driver variables must be unique SINGLE_PROP scalar inputs.')
        target = variable.targets[0]
        owner = target.id
        if owner != armature and owner != bpy.context.scene:
            raise ValueError('Driver scalar source must belong to this exact Armature or Scene.')
        if getattr(target, 'use_fallback_value', False):
            raise ValueError('Driver fallback values make the scalar source ambiguous.')
        bone_name, key = custom_property_address(target.data_path)
        property_owner = owner
        if bone_name is not None:
            if owner != armature or bone_name not in armature.pose.bones:
                raise ValueError('Driver pose custom-property owner is missing or foreign.')
            property_owner = armature.pose.bones[bone_name]
            if bone_name in hair_names or property_owner.bone.get(hair.OWNER_KEY) == hair.OWNER_VALUE:
                raise ValueError('A Hair-owned custom property cannot drive this Head closure.')
        if key not in property_owner.keys():
            raise ValueError('Driver scalar property does not exist in native ID storage.')
        value = owner.path_resolve(target.data_path)
        if type(value) not in {int, float} or not math.isfinite(value):
            raise ValueError('Driver source must resolve to a finite numeric scalar.')
        if value != property_owner[key]:
            raise ValueError('Driver source does not resolve to the proven custom-property backing.')
        animation = owner.animation_data
        for upstream in animation.drivers if animation else ():
            try:
                same_address = custom_property_address(upstream.data_path) == (bone_name, key)
            except (ValueError, SyntaxError):
                same_address = False
            if same_address:
                raise ValueError('Another driver controls the scalar input; its feedback is unproven.')
        values[variable.name] = float(value)
        variables.append({'variable': variable.name, 'type': variable.type, 'target_id': encode(owner),
            'target_data_path': target.data_path, 'property_owner': property_owner.name,
            'property_owner_pointer': property_owner.as_pointer(), 'property_key': key, 'value': value})
    if not values:
        raise ValueError('A scalar driver proof needs at least one proven input.')
    try:
        expected = pure_arithmetic(driver.expression, values)
    except (SyntaxError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Driver expression cannot be proved finite: ' + str(exc)) from exc
    output = armature.path_resolve(curve.data_path)
    actual = output[curve.array_index] if hasattr(output, '__len__') else output
    if type(actual) not in {int, float} or not math.isfinite(actual):
        raise ValueError('Native mapped driver output is not a finite numeric scalar.')
    return {'data_path': curve.data_path, 'array_index': curve.array_index, 'type': driver.type,
        'expression': driver.expression, 'native_simple_expression': driver.is_simple_expression,
        'native_valid': driver.is_valid, 'variables': variables, 'expected_output': expected,
        'actual_output': actual, 'native_FCurve_mapping': mapping, 'proved': True,
        'scope': 'finite simple arithmetic of exact non-Hair native custom scalar sources followed by target-free native FCurve mapping; no Python eval'}


def dependency_closure(armature, anchor, data):
    """Prove the actual parent/copy-constraint DAG is disjoint from owned Hair.

    Names identify native nodes only; no constraint is accepted by its CD label.
    Transform drivers require a native custom-scalar arithmetic proof; animated
    or driven constraint fields are refused. Ordinary
    parent animation is known FCurve input, while the chosen input rotation is
    separately required to be unanimated before the pulse is applied.
    """
    hair_names = {name for item in data['strands'] for name in item['bones']}
    driver_paths = adapter._driver_paths(armature)
    driver_curves = tuple(armature.animation_data.drivers) if armature.animation_data else ()
    animated_paths = adapter._animated_paths(armature)
    rest_paths = adapter._driver_paths(armature.data) + adapter._animated_paths(armature.data)
    transform_fields = OBJECT_FIELDS | {'matrix_channel', 'head', 'tail'}
    state, nodes, edges, rejections = {}, [], [], []

    def reject(kind, **details):
        rejections.append({'kind': kind, **details})

    def visit(bone):
        pointer = bone.as_pointer()
        if state.get(pointer) == 'visiting':
            reject('dependency_cycle', bone=bone.name)
            return
        if state.get(pointer) == 'complete':
            return
        state[pointer] = 'visiting'
        prefix = bone.path_from_id() + '.'
        rest_prefix = bone.bone.path_from_id()
        relevant_drivers = [path for path in driver_paths if path.startswith(prefix)
            and path[len(prefix):].split('.', 1)[0].split('[', 1)[0] in transform_fields | {'constraints'}]
        proved_drivers, unproved_drivers = [], []
        for curve in driver_curves:
            if curve.data_path not in relevant_drivers:
                continue
            if curve.data_path[len(prefix):].split('.', 1)[0].split('[', 1)[0] == 'constraints':
                unproved_drivers.append({'path': curve.data_path, 'reason': 'Constraint driver is unsupported.'})
                continue
            try:
                proved_drivers.append(scalar_driver_proof(curve, armature, hair_names))
            except (ValueError, AttributeError, RuntimeError, TypeError, IndexError) as exc:
                unproved_drivers.append({'path': curve.data_path, 'array_index': curve.array_index, 'reason': str(exc),
                                        'native_FCurve_mapping': curve_mapping_snapshot(curve)})
        relevant_rest = [path for path in rest_paths if path.startswith(rest_prefix + '.')]
        node = {'bone': bone.name, 'parent': bone.parent.name if bone.parent else None,
                'owner': bone.bone.get(hair.OWNER_KEY), 'transform_or_constraint_driver_paths': relevant_drivers,
                'proved_scalar_drivers': proved_drivers, 'unproved_drivers': unproved_drivers,
                'rest_driver_or_animation_paths': relevant_rest}
        nodes.append(node)
        if bone.name in hair_names or bone.bone.get(hair.OWNER_KEY) == hair.OWNER_VALUE:
            reject('Hair_owned_dependency', bone=bone.name)
            state[pointer] = 'complete'
            return
        if unproved_drivers:
            reject('unproved_transform_or_constraint_driver', bone=bone.name, drivers=unproved_drivers)
        if relevant_rest:
            reject('Rest_driver_or_animation', bone=bone.name, paths=relevant_rest)
        if bone.parent:
            edges.append({'from': bone.name, 'to': bone.parent.name, 'kind': 'parent'})
            visit(bone.parent)
        for constraint in bone.constraints:
            target = getattr(constraint, 'target', None)
            subtarget = getattr(constraint, 'subtarget', '')
            constraint_prefix = constraint.path_from_id() + '.'
            animated = [path for path in driver_paths + animated_paths if path.startswith(constraint_prefix)]
            edge = {'from': bone.name, 'to': subtarget, 'kind': 'constraint',
                'name': constraint.name, 'type': constraint.type,
                'target_object': target.name if target else None, 'mute': constraint.mute,
                'influence': constraint.influence, 'owner_space': constraint.owner_space,
                'target_space': constraint.target_space, 'animated_or_driven_fields': animated}
            for key in ('mix_mode', 'use_offset', 'use_x', 'use_y', 'use_z', 'invert_x', 'invert_y', 'invert_z'):
                if hasattr(constraint, key):
                    edge[key] = getattr(constraint, key)
            edges.append(edge)
            if constraint.type not in {'COPY_TRANSFORMS', 'COPY_ROTATION', 'COPY_LOCATION'}:
                reject('unsupported_constraint', bone=bone.name, constraint=constraint.name, type=constraint.type)
                continue
            if target != armature or not subtarget or subtarget not in armature.pose.bones:
                reject('foreign_or_missing_constraint_target', bone=bone.name, constraint=constraint.name,
                       target_object=target.name if target else None, target_bone=subtarget)
                continue
            if animated or not math.isfinite(constraint.influence):
                reject('animated_or_driven_constraint', bone=bone.name, constraint=constraint.name, paths=animated)
            if (constraint.owner_space not in {'WORLD', 'POSE', 'LOCAL', 'LOCAL_WITH_PARENT'}
                    or constraint.target_space not in {'WORLD', 'POSE', 'LOCAL', 'LOCAL_WITH_PARENT'}):
                reject('custom_constraint_space', bone=bone.name, constraint=constraint.name)
            visit(armature.pose.bones[subtarget])
        state[pointer] = 'complete'

    visit(anchor)
    ob, seen = armature, set()
    object_nodes = []
    while ob:
        if ob.as_pointer() in seen:
            reject('Object_parent_cycle', object=ob.name)
            break
        seen.add(ob.as_pointer())
        driven = [path for path in adapter._driver_paths(ob)
                  if path.split('.', 1)[0].split('[', 1)[0] in OBJECT_FIELDS]
        object_nodes.append({'object': ob.name, 'parent': ob.parent.name if ob.parent else None,
                             'transform_driver_paths': driven, 'constraint_count': len(ob.constraints)})
        if ob.constraints or driven or ob.parent_type != 'OBJECT':
            reject('unproven_Object_transform_dependency', object=ob.name)
        ob = ob.parent
    return {'proved': not rejections, 'entry_anchor': anchor.name,
            'nodes': nodes, 'edges': edges, 'Object_dependencies': object_nodes, 'rejections': rejections,
            'accepted_constraint_types': ['COPY_TRANSFORMS', 'COPY_ROTATION', 'COPY_LOCATION'],
            'proof_scope': 'native same-Armature parent/copy-constraint DAG, Hair-disjoint, transform drivers only with native custom-scalar arithmetic proof; no constraint drivers'}


def input_strategy(armature, data):
    anchors = {item['anchor']['name'] for item in data['strands'] if item['anchor']}
    require(len(anchors) == 1, 'This validation needs one registry-proven attachment anchor.')
    anchor = armature.pose.bones[next(iter(anchors))]
    current, trace, seen = anchor, [], set()
    reason, proof_diagnostics = '', {}
    while current is not None:
        if current.as_pointer() in seen:
            reason = 'Constraint target cycle.'
            break
        seen.add(current.as_pointer())
        if not current.constraints:
            closure = dependency_closure(armature, anchor, data)
            proof_diagnostics = {'terminal_bone': current.name, 'rotation_driver_or_animation_paths':
                rotation_conflicts(armature, current), 'parent_or_driver_feedback_rejection': closure['rejections'],
                'dependency_closure': closure,
                'terminal_Hair_owned': current.bone.get(hair.OWNER_KEY) == hair.OWNER_VALUE}
            if (not proof_diagnostics['rotation_driver_or_animation_paths'] and closure['proved']
                    and current.bone.get(hair.OWNER_KEY) != hair.OWNER_VALUE):
                return {'kind': 'constraint_target_input' if trace else 'unconstrained_anchor',
                        'anchor': anchor, 'owner': current, 'base': current.matrix_basis.to_quaternion(),
                        'trace': trace, 'fallback_reason': '', 'proof_diagnostics': proof_diagnostics, 'axis': 'X'}
            reason = 'Terminal input is animated/driven, Hair-owned or has unproven parent feedback.'
            break
        active = [constraint for constraint in current.constraints
                  if not constraint.mute and constraint.influence > 1e-8]
        if len(active) != 1:
            reason = 'Attachment has multiple/disabled constraints; no unique rotation input proof.'
            break
        constraint = active[0]
        prefix = constraint.path_from_id() + '.'
        valid = (constraint.type in {'COPY_TRANSFORMS', 'COPY_ROTATION'}
                 and abs(constraint.influence - 1) < 1e-7
                 and constraint.target == armature and constraint.subtarget in armature.pose.bones
                 and constraint.owner_space == 'POSE' and constraint.target_space == 'POSE'
                 and not any(path.startswith(prefix) for path in paths(armature)))
        if constraint.type == 'COPY_TRANSFORMS':
            valid = valid and constraint.mix_mode == 'REPLACE'
        if constraint.type == 'COPY_ROTATION':
            valid = valid and constraint.mix_mode == 'REPLACE' and all(
                getattr(constraint, 'use_' + axis) and not getattr(constraint, 'invert_' + axis)
                for axis in ('x', 'y', 'z'))
        if not valid:
            reason = 'Constraint is not a fully proven same-rig replacement rotation path.'
            break
        trace.append({'owner': current.name, 'constraint': constraint.name, 'type': constraint.type,
            'target_object': constraint.target.name, 'target_bone': constraint.subtarget,
            'influence': constraint.influence, 'owner_space': constraint.owner_space,
            'target_space': constraint.target_space})
        current = armature.pose.bones[constraint.subtarget]
    require(armature.parent is None and not armature.constraints,
            'Head input is unproven and this Armature is not an unconstrained root Object.')
    require(not any(path.split('.', 1)[0] in OBJECT_FIELDS for path in paths(armature)),
            'Root Object has animated/driven transforms; no known rigid input proof.')
    return {'kind': 'root_armature_world_rotation', 'anchor': anchor, 'owner': armature,
            'base': armature.matrix_world.copy(), 'trace': trace, 'fallback_reason': reason,
            'proof_diagnostics': proof_diagnostics, 'axis': 'X'}


def apply_input(strategy, angle):
    rotation = Matrix.Rotation(angle, 4, strategy['axis'])
    if strategy['kind'] == 'root_armature_world_rotation':
        point = strategy['base'].translation
        strategy['owner'].matrix_world = Matrix.Translation(point) @ rotation @ Matrix.Translation(-point) @ strategy['base']
    else:
        owner = strategy['owner']
        quaternion = strategy['base'] @ rotation.to_quaternion()
        if owner.rotation_mode == 'QUATERNION':
            owner.rotation_quaternion = quaternion
        elif owner.rotation_mode == 'AXIS_ANGLE':
            axis, rotation_angle = quaternion.to_axis_angle()
            owner.rotation_axis_angle = (rotation_angle, *axis)
        else:
            owner.rotation_euler = quaternion.to_euler(owner.rotation_mode)


def pulse(index):
    # Identical first 36 samples in every stage; then zero input for decay.
    amplitude = math.radians(4.0)
    if index <= 12:
        return amplitude * math.sin(math.pi * index / 24.0)
    if index <= 24:
        return amplitude
    if index <= 36:
        return amplitude * math.cos(math.pi * (index - 24) / 24.0)
    return 0.0


def point(armature, name, end='tail'):
    return armature.matrix_world @ getattr(armature.pose.bones[name], end)


def channel_equal(saved, bone):
    _owner, mode, values = saved
    return bone.rotation_mode == mode and all(tuple(getattr(bone, name)) == value for name, value in values.items())


def pair(data, first_order, other_order):
    by_order = {item['order']: item for item in data['strands']}
    first, other = by_order[first_order], by_order[other_order]
    require(first['mirror_id'] == other['strand_id'] and other['mirror_id'] == first['strand_id']
            and first['pair_id'] == other['pair_id'] and first['pair_proof'] in {'TOPOLOGY', 'GEOMETRY', 'GRAPH', 'MIRROR'}
            and other['pair_proof'] == first['pair_proof'], 'Requested pair lacks current complete reciprocal proof.')
    return first, other


def skin_sample(source, data):
    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if len(evaluated.data.vertices) != len(source.data.vertices):
        return {'available': False, 'reason': 'Evaluated modifier topology differs; source indices are not guessed.'}
    indices = sorted({vertex for item in data['strands'] for vertex in (item['layers'][0][0], item['layers'][-1][0])})
    return {'available': True, 'indices': indices,
            'positions_world': [list(evaluated.matrix_world @ evaluated.data.vertices[index].co) for index in indices]}


def native_parameter_proof(armature, data, effective, ids):
    """Observe real backend RNA and compare it with the profile/unit mapping."""
    scene = bpy.context.scene
    acceleration = scene.gravity.length * scene.unit_settings.scale_length
    dt = 1.0 / scene.render.fps
    iterations = scene.wiggle.iterations
    selected = set(ids)
    rows = []
    for item in data['strands']:
        lengths = [(armature.data.bones[name].tail_local - armature.data.bones[name].head_local).length
                   for name in item['bones']]
        distance, total = 0.0, sum(lengths)
        for index, (name, length) in enumerate(zip(item['bones'], lengths)):
            native = armature.pose.bones[name].wiggle
            require(not native.head and native.tail == (item['strand_id'] in selected),
                    'Actual native endpoint enablement differs from the selected tail-only stage.')
            if item['strand_id'] not in selected:
                continue
            distance += length
            fraction = distance / total
            require(0.0 <= fraction <= 1.0 + 1e-12,
                    'Computed native bone depth exceeds the chain except for floating-point roundoff.')
            fraction = 1.0 if index == len(item['bones']) - 1 else min(1.0, fraction)
            requested = profiles.depth_sample(effective[item['strand_id']], fraction)
            expected = {'stiff': 800.0 * requested['recovery'] ** 2,
                'damp': 20.0 * requested['damping'],
                'gravity': requested['gravity'] / acceleration if acceleration else 0.0,
                'stretch': effective[item['strand_id']]['stretch'], 'mass': requested['mass']}
            actual = {key: float(getattr(native, key)) for key in expected}
            require(all(math.isfinite(value) for value in actual.values()), 'Nonfinite native physics parameter.')
            require(all(math.isclose(actual[key], value, rel_tol=2e-6, abs_tol=2e-6)
                        for key, value in expected.items()), 'Actual Wiggle parameters differ from mapping v1: ' + name)
            require(native.enable and native.chain and not native.mute and not native.tail_mute,
                    'Actual solver chain is disabled or muted: ' + name)
            require(all(getattr(native, key) is None for key in
                        ('wind_ob', 'collider', 'collider_collection', 'pin_target')),
                    'An unexpected native collider/wind/pin is enabled: ' + name)
            rows.append({'strand_id': item['strand_id'], 'order': item['order'], 'bone': name,
                'bone_index': index, 'depth_position': fraction,
                'requested_depth_values': requested, 'expected_native': expected, 'actual_native': actual,
                'gravity_acceleration_m_s2': actual['gravity'] * acceleration,
                'one_frame_velocity_retention': max(0.0, min(1.0, 1.0 - actual['damp'] * dt)),
                'one_frame_spring_coefficient_per_iteration': actual['stiff'] * dt * dt / iterations,
                'head_enabled': native.head, 'tail_enabled': native.tail, 'chain': native.chain})
    for anchor_name in {item['anchor']['name'] for item in data['strands'] if item['anchor']}:
        anchor = armature.pose.bones[anchor_name].wiggle
        require(not anchor.head and not anchor.tail, 'Attachment anchor must not be a simulated endpoint.')
    return {'mapping_version': adapter.MAPPING_VERSION, 'backend_version': adapter.BACKEND_VERSION,
        'verified': True, 'bone_count': len(rows), 'native_float_relative_and_absolute_tolerance': 2e-6,
        'formulas': {'stiff': '800 * recovery**2', 'damp': '20 * damping',
            'gravity': 'requested m/s^2 / (length(scene.gravity) * scene.unit_settings.scale_length)',
            'stretch': 'native fraction unchanged', 'mass': 'relative chain coefficient; not kilograms'},
        'scene': {'gravity_vector': list(scene.gravity), 'gravity_length': scene.gravity.length,
            'unit_scale_length': scene.unit_settings.scale_length, 'use_gravity': scene.use_gravity,
            'upstream_reads_scene_use_gravity': False, 'fps': scene.render.fps,
            'fps_base': scene.render.fps_base, 'single_frame_dt_seconds': dt, 'iterations': iterations,
            'auto_sync': scene.wiggle.auto_sync, 'full_bone_colliders': scene.wiggle.full_bone_collision.enable_fullbone_collision},
        'object_world_scale': list(armature.matrix_world.to_scale()),
        'object_scale_extra_gravity_multiplier': 1.0,
        'unit_reason': 'Official reset stores endpoints in world coordinates; object scale is already represented.',
        'source_urls': ['https://github.com/Hans-xwh/wiggle-bones/blob/1.1.2/src/wiggle_bones/physics_engine.py#L237-L286',
                        'https://github.com/Hans-xwh/wiggle-bones/blob/1.1.2/src/wiggle_bones/wiggle_core.py'],
        'bones': rows}


def phase_comparison(first, other, *, changed_strand=None):
    """Compare the same chain/sample, never infer a geometric mirror partner."""
    require(first['raw_before']['sha256'] == other['raw_before']['sha256'],
            'Compared phases did not start from the same exact asset baseline.')
    by_id = {item['strand_id']: item for item in first['chains']}
    rows = []
    for item in other['chains']:
        require(item['strand_id'] in by_id, 'Phase comparison references a different chain.')
        reference = by_id[item['strand_id']]
        count = min(len(reference['samples']), len(item['samples']))
        differences = []
        for before, after in zip(reference['samples'][:count], item['samples'][:count]):
            require(before['sample'] == after['sample'], 'Phase sample timing is not aligned.')
            require(before['input_pulse_radians'] == after['input_pulse_radians'], 'Compared input pulses differ.')
            differences.append((Vector(after['tip_in_attachment_frame'])
                                - Vector(before['tip_in_attachment_frame'])).length)
        rows.append({'strand_id': item['strand_id'], 'order': item['order'], 'compared_samples': count,
            'intentionally_changed_profile': item['strand_id'] == changed_strand,
            'maximum_same_sample_attachment_tip_difference': max(differences),
            'rms_same_sample_attachment_tip_difference': math.sqrt(sum(value * value for value in differences) / count),
            'last_sample_attachment_tip_difference': differences[-1],
            'maximum_tip_displacement_delta': item['maximum_tip_displacement'] - reference['maximum_tip_displacement']})
    independent = None
    if changed_strand is not None:
        unchanged = [row for row in rows if not row['intentionally_changed_profile']]
        maximum = max(row['maximum_same_sample_attachment_tip_difference'] for row in unchanged)
        require(maximum <= 1e-5, 'Changing one Hair gravity affected a separate simulated strand response.')
        old_parameters = {row['bone']: row for row in first['native_parameters']['bones']}
        changed_parameters = [row for row in other['native_parameters']['bones'] if row['strand_id'] == changed_strand]
        delta = max(abs(row['actual_native']['gravity'] - old_parameters[row['bone']]['actual_native']['gravity'])
                    for row in changed_parameters)
        require(delta > 1e-7, 'The intended single-strand gravity change did not reach native RNA.')
        independent = {'unchanged_strands_maximum_response_difference': maximum,
                       'response_tolerance': 1e-5, 'changed_strand_maximum_native_gravity_delta': delta,
                       'separate_chain_response_unchanged': True}
    return {'reference_phase': first['name'], 'compared_phase': other['name'], 'same_raw_baseline': True,
        'same_input_pulse': True, 'coordinate_frame': 'registry attachment anchor local frame',
        'changed_strand_id': changed_strand, 'chains': rows, 'independence_observation': independent,
        'claim': 'Observed response comparison; solver parent ownership proves chains are uncoupled. No mirrored-trajectory equivalence asserted.'}


def stage(label, source, armature, data, effective, ids, strategy, frames, *, synchronized):
    require(not adapter.status()['active'], 'An earlier stage is still active.')
    raw_before = asset_fingerprint(source)
    pose_before = pose_snapshot()
    by_id = {item['strand_id']: item for item in data['strands']}
    selected = [by_id[key] for key in ids]
    unselected = [adapter._channels(armature.pose.bones[name]) for item in data['strands']
                  if item['strand_id'] not in ids for name in item['bones']]
    anchor = strategy['anchor']
    anchor_before = (armature.matrix_world @ anchor.matrix).copy()
    starts = {item['strand_id']: {'tip': point(armature, item['bones'][-1]),
                                 'root': point(armature, item['bones'][0], 'head')} for item in selected}
    samples, times, parent_map, anchor_angles = {key: [] for key in ids}, [], [], []
    result = {'name': label, 'frames': frames, 'strand_ids': ids, 'settings_synchronized': synchronized,
              'effective_inputs': effective, 'simulation_baked': False, 'pulse_degrees': 4.0,
              'pulse_end_sample': 36, 'skin_before': skin_sample(source, data)}
    began = time.perf_counter()
    try:
        adapter.start_preview(bpy.context, source, data, effective, ids)
        result['native_parameters'] = native_parameter_proof(armature, data, effective, ids)
        ranges = {key: [min(row['actual_native'][key] for row in result['native_parameters']['bones']),
                        max(row['actual_native'][key] for row in result['native_parameters']['bones'])]
                  for key in ('stiff', 'damp', 'gravity', 'stretch', 'mass')}
        print('REAL_HAIR_NATIVE_PARAMETERS', json.dumps({'stage': label,
            'mapping_version': result['native_parameters']['mapping_version'],
            'bone_count': result['native_parameters']['bone_count'],
            'scene': result['native_parameters']['scene'],
            'native_parameter_ranges': ranges,
            'units': {'gravity': 'scene multiplier; requested gravity m/s^2', 'mass': 'relative coefficient'}},
            ensure_ascii=False, allow_nan=False))
        for item in selected:
            owned = set(item['bones'])
            for index, name in enumerate(item['bones']):
                bone = armature.pose.bones[name]
                ancestor = adapter._SESSION['backend']['core'].get_parent(bone)
                require((ancestor is None if index == 0 else ancestor.name == item['bones'][index - 1]),
                        'A solver parent crosses independent strands or attachment.')
                require(ancestor is None or ancestor.name in owned, 'Solver coupling crosses strands.')
                parent_map.append({'bone': name, 'solver_parent': ancestor.name if ancestor else None})
        for index in range(1, frames + 1):
            sample_start = time.perf_counter()
            apply_input(strategy, pulse(index))
            bpy.context.scene.frame_set(pose_before['frame'] + index)
            require(adapter.status()['active'], 'A preview guard ended this stage: ' + adapter.status()['reason'])
            anchor_world = armature.matrix_world @ anchor.matrix
            rigid = anchor_world @ anchor_before.inverted()
            anchor_angles.append(anchor_world.to_quaternion().rotation_difference(anchor_before.to_quaternion()).angle)
            for item in selected:
                key = item['strand_id']
                tip, root = point(armature, item['bones'][-1]), point(armature, item['bones'][0], 'head')
                require(all(math.isfinite(value) for value in (*tip, *root)), 'Nonfinite Hair endpoint.')
                samples[key].append({'sample': index, 'tip_world': list(tip), 'root_world': list(root),
                    'input_pulse_radians': pulse(index),
                    'tip_in_attachment_frame': list(anchor_world.inverted() @ tip),
                    'tip_displacement': (tip - starts[key]['tip']).length,
                    'tip_relative_to_rigid_attachment': (tip - rigid @ starts[key]['tip']).length,
                    'root_distance_to_rigid_attachment': (root - rigid @ starts[key]['root']).length})
            require(all(channel_equal(saved, saved[0]) for saved in unselected),
                    'An unselected Hair chain changed local pose channels.')
            times.append(time.perf_counter() - sample_start)
        result['skin_simulated_end'] = skin_sample(source, data)
    finally:
        if adapter.status()['active']:
            adapter.stop_preview(reason='Real Hair isolated stage completed or failed.')
        # stop restores the input as part of Object/PoseBone channel rollback.
    result['strict_pose_baseline'] = check_pose(pose_before)
    raw_after = asset_fingerprint(source)
    require(raw_after['sha256'] == raw_before['sha256'], 'Raw mesh/weights/keys/Rest/Actions changed during stage.')
    result['raw_before'], result['raw_after'] = raw_before, raw_after
    result['strict_raw_baseline'] = True
    result['skin_after_stop'] = skin_sample(source, data)
    if result['skin_before']['available'] and result['skin_after_stop']['available']:
        error = max((Vector(a) - Vector(b)).length for a, b in zip(
            result['skin_before']['positions_world'], result['skin_after_stop']['positions_world']))
        require(error <= 1e-5, 'Evaluated Hair skin samples were not restored after stop.')
        result['skin_restoration_maximum_error'] = error
    require(max(anchor_angles) > 1e-4, 'The proven input did not move the actual attachment anchor.')
    result['maximum_observed_anchor_rotation_degrees'] = math.degrees(max(anchor_angles))
    result['solver_parent_map'] = parent_map
    result['unselected_local_channels_unchanged'] = True
    result['unselected_bone_count'] = len(unselected)
    result['timing'] = {'stage_seconds': time.perf_counter() - began,
        'frame_seconds_mean': statistics.mean(times), 'frame_seconds_median': statistics.median(times),
        'frame_seconds_max': max(times), 'frame_seconds_total': sum(times)}
    result['chains'] = []
    for item in selected:
        values = samples[item['strand_id']]
        points = [Vector(value['tip_in_attachment_frame']) for value in values]
        center = sum(points[-16:], Vector()) / 16
        early = max((position - center).length for position in points[24:40])
        late = max((position - center).length for position in points[-16:])
        increments = [(after - before).length for before, after in zip(points, points[1:])]
        result['chains'].append({'strand_id': item['strand_id'], 'order': item['order'],
            'group': effective[item['strand_id']]['group'], 'pair_id': item['pair_id'],
            'pair_proof': item['pair_proof'], 'finite': True, 'samples': values,
            'maximum_tip_displacement': max(value['tip_displacement'] for value in values),
            'maximum_relative_tip_displacement': max(value['tip_relative_to_rigid_attachment'] for value in values),
            'maximum_root_attachment_distance': max(value['root_distance_to_rigid_attachment'] for value in values),
            'decay': {'coordinate_frame': 'registry attachment anchor local frame',
                      'early_distance_to_final_window_mean': early,
                      'late_distance_to_final_window_mean': late, 'late_to_early_ratio': late / early if early else None,
                      'late_mean_tip_increment': statistics.mean(increments[-16:]),
                      'maximum_tip_increment': max(increments)}})
    return result


def load_backend():
    path = Path(os.environ['CD_WIGGLE_TEST_ROOT']).resolve()
    require(not adapter.available()['available'], 'Use factory state without a pre-enabled backend for this isolated script.')
    name = '_cd_real_hair_wiggle_112'
    spec = importlib.util.spec_from_file_location(name, path / '__init__.py', submodule_search_locations=[str(path)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    registered = False
    try:
        module.register()
        registered = True
        adapter._backend()  # Full official source/schema/handler proof, not UI cache.
    except Exception:
        if registered:
            module.unregister()
        raise
    return module


def main():
    require(bpy.app.background, 'Run this validation only in an isolated background Blender.')
    require(bpy.data.filepath, 'Open an explicit saved X before running the script.')
    artist_path = str(Path(bpy.data.filepath).resolve())
    candidate = Path(os.environ.get('CD_HAIR_CANDIDATE_PATH', str(DIRECTORY / (
        'real_hair_preview_candidate_' + bpy.app.version_string.replace(' ', '_').replace('.', '_')
        + '_' + str(time.time_ns()) + '.blend'))))
    require(str(candidate.resolve()) != artist_path, 'Candidate must differ from the artist file.')
    require(not candidate.exists(), 'Candidate path already exists; refusing to overwrite previous evidence.')
    source = bpy.data.objects['Hair']
    module = None
    result = {'ok': False, 'blender': bpy.app.version_string, 'source': source.name,
        'artist_path': artist_path, 'artist_saved': False, 'simulation_baked': False, 'stages': [],
        'limitations': ['backend colliders/wind/pins are disabled for this preview', 'no GUI or Unity validation',
                        'solver coefficients are not a native-material physical-equivalence measurement',
                        'settings sync is checked; mirrored trajectory equivalence is not asserted',
                        'decay is an observed trajectory diagnostic, not a material calibration']}
    try:
        require(hair._read_records(source)['source_id'].replace('-', '').lower() == EXPECTED_UID,
                'Wrong Hair source UUID; refusing metadata writes on another model.')
        initial = asset_fingerprint(source)
        data = registry.initialize(source)
        require(data['source_uid'] == EXPECTED_UID, 'Wrong Hair source UUID; refusing another model.')
        require(len(data['strands']) == 32 and sum(len(item['bones']) for item in data['strands']) == 128,
                'Expected original 32 strands / 128 segments; no rebind is authorized.')
        profiles.initialize(source, registry=data)
        record = profiles.assign_suggested_groups(source, registry=data)
        effective = profiles.effective_all(source, registry=data)
        first = pair(data, 14, 16)
        long = pair(data, 2, 5)
        for left, right in (first, long):
            require(effective[left['strand_id']] == effective[right['strand_id']], 'Pair effective settings differ.')
            require(effective[left['strand_id']]['sync_mirror'], 'Expected synchronized formal pair settings.')
        require(all(effective[item['strand_id']]['group'] == 'FRONT' for item in first), 'Short pair is not suggested FRONT.')
        require(all(effective[item['strand_id']]['group'] == 'BACK' for item in long), 'Long pair is not suggested BACK.')
        after_metadata = asset_fingerprint(source)
        require(after_metadata['sha256'] == initial['sha256'], 'Initialization modified data beyond two allowed metadata properties.')
        armature = source.get(hair.RIG_KEY)
        strategy = input_strategy(armature, data)
        result.update(source_uid=data['source_uid'], topology=data['topology'], counts={'strands': 32, 'segments': 128},
            groups=dict(collections.Counter(item['group'] for item in effective.values())),
            firstpair_ids=[item['strand_id'] for item in first], longpair_ids=[item['strand_id'] for item in long],
            initial_fingerprint=initial, metadata_fingerprint=after_metadata,
            input={'kind': strategy['kind'], 'anchor': strategy['anchor'].name, 'input': strategy['owner'].name,
                   'axis': strategy['axis'], 'constraint_trace': strategy['trace'],
                   'fallback_reason': strategy['fallback_reason'], 'proof_diagnostics': strategy['proof_diagnostics']})
        print('REAL_HAIR_INPUT_PROOF', json.dumps(result['input'], ensure_ascii=False, allow_nan=False))
        if os.environ.get('CD_HAIR_REQUIRE_HEAD_LOCAL') == '1':
            require(strategy['kind'] != 'root_armature_world_rotation',
                    'Head-local input is unproven; inspect native dependency_closure rejections before changing the gate.')
        if strategy['kind'] == 'root_armature_world_rotation':
            result['limitations'].append('Input is a proven root Object rigid rotation; Head-local CTRL response is unverified.')
        module = load_backend()
        ids = [item['strand_id'] for item in (*first, *long)]
        result['stages'].append(stage('focused_synchronized', source, armature, data, effective, ids, strategy, 96, synchronized=True))
        asymmetric = copy.deepcopy(effective)
        changed = first[1]['strand_id']
        asymmetric[changed]['gravity'] = min(20.0, asymmetric[changed]['gravity'] + 6.0)
        for knot in asymmetric[changed].get('depth', []):
            knot['gravity'] = min(20.0, knot.get('gravity', effective[changed]['gravity']) + 6.0)
        result['stages'].append(stage('deliberate_unsynchronized_gravity_test', source, armature, data,
            asymmetric, ids, strategy, 96, synchronized=False))
        result['stages'].append(stage('all_32_synchronized', source, armature, data, effective,
            [item['strand_id'] for item in data['strands']], strategy, 60, synchronized=True))
        result['phase_comparisons'] = [phase_comparison(result['stages'][0], result['stages'][1], changed_strand=changed)]
        focused_all = dict(result['stages'][2])
        focused_all['chains'] = [item for item in focused_all['chains'] if item['strand_id'] in ids]
        result['phase_comparisons'].append(phase_comparison(result['stages'][0], focused_all))
        require(not adapter.status()['active'], 'Stop preview before candidate save.')
        final = asset_fingerprint(source)
        require(final['sha256'] == initial['sha256'], 'Final model baseline differs.')
        require(profiles.read(source, registry=data) == record, 'Transient asymmetric test changed saved profiles.')
        require(registry.read(source, validate=True) == data, 'Saved registry proof changed.')
        require(str(Path(bpy.data.filepath).resolve()) == artist_path, 'Artist filepath changed.')
        save = bpy.ops.wm.save_as_mainfile(filepath=str(candidate), copy=True)
        require('FINISHED' in save and candidate.is_file(), 'Independent stopped candidate save failed.')
        require(str(Path(bpy.data.filepath).resolve()) == artist_path, 'copy=True changed artist filepath.')
        result.update(ok=True, strictbaseline=True, final_fingerprint=final,
                      recoverypath=str(candidate), candidate_saved=True,
                      metadata_changes_only=sorted(ALLOWED_METADATA))
    except Exception as exc:
        result['error'] = str(exc)
        raise
    finally:
        try:
            adapter.stop_preview(reason='Isolated real Hair validation teardown.')
            adapter.unregister_guards()
            if module is not None:
                module.unregister()
        finally:
            OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
            print('REAL_HAIR_PREVIEW_VALIDATION', json.dumps({'ok': result['ok'], 'output': str(OUTPUT),
                                                           'artist_saved': False, 'simulation_baked': False}))


if __name__ == '__main__':
    main()
