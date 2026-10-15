"""Standalone three-sample PC2 factory probe; no addon, blend open/save or GUI.

Only Root launches this worker. The reference mesh receives known local points;
the cache mesh is read only after setup and must advance through MeshCache alone.
"""
from array import array
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback

HERE = Path(__file__).resolve().parent
HEADER = struct.Struct('<12siiffi')
POINTS = (
    ((1., 2., 3.), (2., 2., 3.), (2., 3., 3.), (1., 3., 3.), (1.5, 2.5, 4.)),
    ((1., 2., 3.), (2., 2., 3.), (2.25, 3., 3.), (1., 3., 3.), (1.5, 2.5, 4.5)),
    ((1., 2., 3.), (2., 1.5, 3.), (2., 3., 3.), (1., 3., 3.25), (1.25, 2.5, 4.)),
)
FACES = ((0, 3, 2, 1), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4))
MOTION = (
    ((3., -2., 1.), (.125, -.25, .375), (1.25, .75, 1.5)),
    ((3.5, -1.75, 1.5), (.25, .125, -.125), (.75, 1.5, 1.25)),
    ((2.75, -2.5, .75), (-.125, .375, .25), (1.5, 1.25, .75)),
)
VISITS = (1, 2, 3, 3, 2, 1, 2, 1, 3, 1, 3, 1)
SOURCES = [
    'https://raw.githubusercontent.com/blender/blender/blender-v5.2-release/source/blender/modifiers/intern/MOD_meshcache.cc',
    'https://raw.githubusercontent.com/blender/blender/blender-v5.2-release/source/blender/modifiers/intern/MOD_meshcache_pc2.cc',
    'https://raw.githubusercontent.com/blender/blender/blender-v5.2-release/source/blender/modifiers/intern/MOD_meshcache_util.cc',
    'https://raw.githubusercontent.com/blender/blender/blender-v5.2-release/source/blender/blenkernel/intern/mesh_normals.cc',
]


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(Path(path).resolve()), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode()).hexdigest()


def encode_pc2(samples):
    require(samples and samples[0], 'PC2 requires nonempty samples and vertices')
    count = len(samples[0])
    values = []
    for sample in samples:
        require(len(sample) == count, 'PC2 vertex count changed')
        for point in sample:
            require(len(point) == 3 and all(math.isfinite(v) for v in point), 'Invalid PC2 point')
            values.extend(point)
    return HEADER.pack(b'POINTCACHE2\0', 1, count, 0., 1., len(samples)) + struct.pack('<'+str(len(values))+'f', *values)


def inspect_pc2(raw):
    require(len(raw) >= HEADER.size, 'PC2 header missing')
    magic, version, vertices, start, sampling, samples = HEADER.unpack_from(raw)
    require(magic == b'POINTCACHE2\0' and version == 1 and vertices > 0 and samples > 0,
            'PC2 header differs')
    require(start == 0. and sampling == 1. and len(raw) == HEADER.size + vertices*samples*12,
            'PC2 header timing or payload size differs')
    values = struct.unpack_from('<'+str(vertices*samples*3)+'f', raw, HEADER.size)
    require(all(math.isfinite(v) for v in values), 'PC2 contains nonfinite points')
    return {'header_bytes': HEADER.size, 'vertices': vertices, 'samples': samples,
            'start': start, 'sampling': sampling, 'sha256': hashlib.sha256(raw).hexdigest()}


def bulk(collection, field, width=3):
    data = array('f', [0.]) * (len(collection)*width)
    collection.foreach_get(field, data)
    return data.tobytes()


def vector_diff(left, right):
    require(len(left) == len(right) and len(left) % 12 == 0, 'Vector scope differs')
    a, b = array('f'), array('f')
    a.frombytes(left)
    b.frombytes(right)
    require(all(math.isfinite(v) for v in (*a, *b)), 'Nonfinite vector output')
    squared = [sum((a[i+j]-b[i+j])**2 for j in range(3)) for i in range(0, len(a), 3)]
    return {'exact': left == right, 'sha256_reference': hashlib.sha256(left).hexdigest(),
            'sha256_cache': hashlib.sha256(right).hexdigest(), 'count': len(squared),
            'max_error': math.sqrt(max(squared, default=0.)),
            'rms_error': math.sqrt(sum(squared)/len(squared)) if squared else 0.}


def static_payload(obj, mesh):
    scalar = {'FLOAT', 'INT', 'INT8', 'BOOLEAN'}
    vector = {'FLOAT_VECTOR': 'vector', 'FLOAT2': 'vector', 'FLOAT_COLOR': 'color',
              'BYTE_COLOR': 'color', 'INT32_2D': 'value', 'INT16_2D': 'value'}
    attributes = {}
    for attr in mesh.attributes:
        if attr.name == 'position':
            continue
        require(attr.data_type in scalar or attr.data_type in vector,
                'Unclaimed factory attribute type: '+attr.data_type)
        values = [item.value for item in attr.data] if attr.data_type in scalar else [
            tuple(getattr(item, vector[attr.data_type])) for item in attr.data]
        attributes[attr.name] = (attr.domain, attr.data_type, values)
    return {'edges': [tuple(edge.vertices) for edge in mesh.edges],
        'loops': [(loop.vertex_index, loop.edge_index) for loop in mesh.loops],
        'faces': [(face.loop_start, face.loop_total, face.material_index, face.use_smooth) for face in mesh.polygons],
        'materials': [(type(mat).__name__, mat.name_full) if mat else None for mat in mesh.materials],
        'uv_layers': [(uv.name, uv.active_render) for uv in mesh.uv_layers], 'attributes': attributes,
        'vertex_groups': [(group.index, group.name) for group in obj.vertex_groups],
        'weights': [[(item.group, float(item.weight)) for item in vertex.groups] for vertex in mesh.vertices]}


def output(obj, graph):
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.data
    return {'position': bulk(mesh.vertices, 'co'), 'vertex_normal': bulk(mesh.vertices, 'normal'),
        'polygon_normal': bulk(mesh.polygons, 'normal'), 'corner_normal': bulk(mesh.corner_normals, 'vector')}, {
        'static': digest(static_payload(obj, mesh)),
        'world': digest([tuple(row) for row in evaluated.matrix_world]),
        'channels': [tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.scale)]}


def handlers(bpy):
    return {name: [id(item) for item in value] for name in dir(bpy.app.handlers)
            if isinstance((value := getattr(bpy.app.handlers, name)), list)}


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath,
            'A private factory-startup background process is required')
    require(bpy.app.version[:2] == (5, 2), 'This API probe targets Blender 5.2')
    require(any(v in ('-t', '--threads') and native[i+1] == '1' for i, v in enumerate(native[:-1])),
            'Explicit -t 1 required')
    cache_dir = Path(args.cache_dir).resolve()
    require(cache_dir.parent == HERE and not cache_dir.exists(), 'Name a new direct child cache directory')
    artist = pin(args.artist)
    initial_handlers, scene, owned = handlers(bpy), bpy.context.scene, []
    initial_frame = scene.frame_current
    def own(collection, item):
        entry = (collection, int(item.as_pointer()), item.session_uid)
        if entry not in owned:
            owned.append(entry)
        return item
    raw = encode_pc2(POINTS)
    cache_dir.mkdir()
    pc2 = cache_dir/'three_samples.pc2'
    with pc2.open('xb') as stream:
        stream.write(raw)
    report.update(script=pin(__file__), artist_before=artist, blender=bpy.app.version_string,
                  pc2=pin(pc2), format=inspect_pc2(raw), frames=[], official_source_references=SOURCES)
    try:
        materials = [own('materials', bpy.data.materials.new('PC2 Factory Material '+str(i))) for i in range(2)]
        for normal_mode in ('computed', 'static_corner_float3'):
            mesh = own('meshes', bpy.data.meshes.new('PC2 Factory Reference '+normal_mode))
            mesh.from_pydata(POINTS[0], [], FACES)
            mesh.update()
            for mat in materials:
                mesh.materials.append(mat)
            for face in mesh.polygons:
                face.material_index, face.use_smooth = face.index % 2, face.index % 2 == 0
            uv = mesh.uv_layers.new(name='FixtureUV')
            for i, item in enumerate(uv.data):
                item.uv = ((i % 4)/4., (i // 4)/4.)
            for name, kind, domain in (('fixture_weight', 'FLOAT', 'POINT'), ('fixture_class', 'INT', 'FACE')):
                attr = mesh.attributes.new(name=name, type=kind, domain=domain)
                for i, item in enumerate(attr.data):
                    item.value = (i+1)/8. if kind == 'FLOAT' else i
            sharp = mesh.attributes.get('sharp_edge') or mesh.attributes.new(name='sharp_edge', type='BOOLEAN', domain='EDGE')
            sharp.data[0].value = True
            if normal_mode != 'computed':
                attr = mesh.attributes.new(name='custom_normal', type='FLOAT_VECTOR', domain='CORNER')
                for i, item in enumerate(attr.data):
                    item.vector = (0., 0., 1.) if i % 2 else (.6, 0., .8)
            clone_mesh = own('meshes', mesh.copy())
            reference = own('objects', bpy.data.objects.new('PC2 Reference '+normal_mode, mesh))
            cached = own('objects', bpy.data.objects.new('PC2 Cached '+normal_mode, clone_mesh))
            for obj in (reference, cached):
                scene.collection.objects.link(obj)
                group = obj.vertex_groups.new(name='StaticWeight')
                group.add([0, 2, 4], .5, 'REPLACE')
                obj.rotation_mode = 'XYZ'
                for frame, channels in enumerate(MOTION, 1):
                    obj.location, obj.rotation_euler, obj.scale = channels
                    for path in ('location', 'rotation_euler', 'scale'):
                        require(obj.keyframe_insert(data_path=path, frame=frame), 'Transform key insert failed')
                        own('actions', obj.animation_data.action)
            mod = cached.modifiers.new('PC2 Factory Playback', 'MESH_CACHE')
            mod.filepath, mod.cache_format, mod.deform_mode = str(pc2), 'PC2', 'OVERWRITE'
            mod.factor, mod.vertex_group, mod.interpolation = 1., '', 'NONE'
            mod.play_mode, mod.time_mode, mod.frame_start, mod.frame_scale = 'SCENE', 'FRAME', 1., 1.
            mod.forward_axis, mod.up_axis, mod.flip_axis = 'POS_Y', 'POS_Z', (False, False, False)
            static_before = digest(static_payload(cached, clone_mesh))
            basis_before = bulk(clone_mesh.vertices, 'co')
            for visit, frame in enumerate(VISITS):
                reference.data.vertices.foreach_set('co', [v for point in POINTS[frame-1] for v in point])
                reference.data.update()
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                graph = bpy.context.evaluated_depsgraph_get()
                expected, a = output(reference, graph)
                actual, b = output(cached, graph)
                fields = {name: vector_diff(expected[name], actual[name]) for name in expected}
                row = {'normal_mode': normal_mode, 'visit': visit, 'frame': frame, 'fields': fields,
                    'world_exact': a['world'] == b['world'],
                    'transform_channels_exact': a['channels'] == b['channels'] == list(MOTION[frame-1]),
                    'attributes_topology_material_weights_exact': a['static'] == b['static'] == static_before}
                report['frames'].append(row)
                require(digest(static_payload(cached, clone_mesh)) == static_before,
                        'Cache modifier changed original static mesh data')
                require(bulk(clone_mesh.vertices, 'co') == basis_before,
                        'Cache modifier changed original mesh coordinates')
        report['all_positions_normals_exact'] = all(field['exact'] for row in report['frames'] for field in row['fields'].values())
        report['all_transform_static_payload_exact'] = all(row['world_exact'] and row['transform_channels_exact']
            and row['attributes_topology_material_weights_exact'] for row in report['frames'])
        require(report['all_positions_normals_exact'] and report['all_transform_static_payload_exact'],
                'Factory PC2 exact replay gate failed; inspect retained field metrics')
    finally:
        errors = []
        for collection in ('objects', 'meshes', 'materials', 'actions'):
            values = getattr(bpy.data, collection)
            current = {int(item.as_pointer()): item for item in values}
            for kind, pointer, uid in reversed(owned):
                if kind == collection and pointer in current:
                    try:
                        item = current[pointer]
                        require(item.session_uid == uid, 'Owned pointer was reused; retain replacement')
                        values.remove(item, do_unlink=True)
                    except BaseException:
                        errors.append(traceback.format_exc())
        scene.frame_set(initial_frame)
        report['cleanup'] = {'errors': errors, 'handlers_unchanged': initial_handlers == handlers(bpy),
            'artist_disk_unchanged': artist == pin(args.artist), 'pc2_unchanged': report['pc2'] == pin(pc2),
            'script_unchanged': report['script'] == pin(__file__),
            'all_owned_ids_removed': not any(pointer in {int(item.as_pointer()) for item in getattr(bpy.data, kind)}
                for kind, pointer, uid in owned),
            'no_blend_open': not bpy.data.filepath}
        require(not errors and all(v for k, v in report['cleanup'].items() if k != 'errors'), 'Factory cleanup/pin gate failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('artist', 'cache-dir', 'report'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.pc2-mesh-cache-factory/1', 'completed': False,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'no_addon_registration': True, 'no_blend_open_or_save': True, 'gui_fps_verified': False,
        'limits': ['Three known integer samples; no subframe/FPS/full-actor claim.',
                   'Computed normals and static Float3 CORNER custom normals only; animated custom normals are not encoded in PC2.',
                   'Local positions, independent native transform keys, fixed fixture topology/UV/material slots/weights/typed attributes only.',
                   'New PC2 file is retained as owned evidence; no artist or blend file is written.']}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
