"""Root's private Console view setup; no launch, selection, geometry or save."""
import hashlib
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPACE = ('lens', 'clip_start', 'clip_end', 'show_region_ui', 'show_region_toolbar', 'show_gizmo')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path):
    path, digest, size = Path(path).resolve(), hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
            size += len(block)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': size}


def state(space, view):
    return {'space': {key: getattr(space, key) for key in SPACE},
        'location': list(view.view_location), 'rotation': list(view.view_rotation),
        'distance': float(view.view_distance), 'perspective': view.view_perspective,
        'shading': space.shading.type, 'overlays': bool(space.overlay.show_overlays)}


def run(config):
    import bpy
    from mathutils import Vector
    require(set(config) == {'expected_pid', 'loaded_file', 'loaded_sha256', 'mode', 'cosha_object',
        'view_config', 'view_config_sha256'}, 'Explicit private view CONFIG required')
    require(type(config['expected_pid']) is int and config['expected_pid'] == os.getpid()
        and not bpy.app.background and config['mode'] in {'cache', 'baseline'}, 'Owned GUI PID/mode required')
    loaded, artist = Path(config['loaded_file']).resolve(strict=True), (HERE.parents[2]/'X.blend').resolve(strict=True)
    require(loaded != artist and not os.path.samefile(loaded, artist)
        and Path(bpy.data.filepath).resolve() == loaded, 'Never configure artist or another loaded file')
    loaded_pin = pin(loaded)
    require(loaded_pin['sha256'] == config['loaded_sha256'], 'Observed private file pin differs')
    scene, area = bpy.context.scene, bpy.context.area
    require(scene.frame_current == 1 and scene.frame_subframe == 0. and area and area.type == 'CONSOLE'
        and not bpy.context.screen.is_animation_playing, 'Stopped frame1 private Console required')
    spaces = [item for item in area.spaces if item.type == 'VIEW_3D']
    require(len(spaces) == 1, 'One existing VIEW3D space required; switch it to Console first')
    space, path = spaces[0], Path(config['view_config']).resolve()
    view = space.region_3d
    require(view is not None and not space.local_view and not space.region_quadviews,
        'Existing ordinary VIEW3D region required')
    require(path.parent == HERE and path.suffix == '.json', 'Direct project view-config JSON required')
    if config['mode'] == 'cache':
        require(config['view_config_sha256'] is None and not path.exists(), 'New cache view JSON required')
        obj = scene.objects.get(config['cosha_object'])
        require(obj is not None and obj.type == 'MESH', 'Explicit evaluated Cosha Mesh required')
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        corners = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
        low, high = (Vector(tuple(fn(point[i] for point in corners) for i in range(3))) for fn in (min, max))
        radius = (high-low).length*.5
        require(math.isfinite(radius) and radius > 0. and area.width > 0 and area.height > 0, 'Invalid full-body bounds/area')
        half_fov = math.atan(18./50./max(1., area.width/area.height))
        values = {'space': dict(zip(SPACE, (50., .01, 1000., False, False, False))),
            'location': list((low+high)*.5), 'rotation': [math.sqrt(.5), math.sqrt(.5), 0., 0.],
            'distance': radius/math.sin(half_fov)*1.12, 'perspective': 'PERSP', 'shading': 'MATERIAL', 'overlays': True}
    else:
        require(config['cosha_object'] is None and pin(path)['sha256'] == config['view_config_sha256'], 'Pinned cache view config required')
        document = json.loads(path.read_text(encoding='utf8'))
        require(document.get('schema') == 'x.private-current-view/1'
            and document['area_size'] == [area.width, area.height], 'Match the cache Console area dimensions first')
        values = document['view']
    require(set(values) == {'space', 'location', 'rotation', 'distance', 'perspective', 'shading', 'overlays'}
        and set(values['space']) == set(SPACE) and values['perspective'] == 'PERSP'
        and values['shading'] == 'MATERIAL' and values['overlays'] is True, 'Fixed non-camera Material view required')
    for key in SPACE:
        setattr(space, key, values['space'][key])
    view.view_location, view.view_rotation, view.view_distance = values['location'], values['rotation'], values['distance']
    view.view_perspective, space.shading.type, space.overlay.show_overlays = 'PERSP', 'MATERIAL', True
    observed = state(space, view)
    if config['mode'] == 'cache':
        document = {'schema': 'x.private-current-view/1', 'cache_private': loaded_pin, 'pid': os.getpid(),
            'cosha_object': obj.name_full, 'area_size': [area.width, area.height], 'view': observed}
        with path.open('x', encoding='utf8') as stream:
            json.dump(document, stream, indent=2, allow_nan=False)
            stream.write('\n')
    else:
        require(observed == values, 'Native baseline view readback differs from the recorded cache view')
    area.tag_redraw()
    return {'view_config': pin(path), 'view': observed, 'scope': 'Private view only; Root switches back to VIEW3D and prewarms before FPS.'}
