"""Private stored-shader API inventory; diagnostic only, never admission PASS.

Reuse the bounded shader path. Unknown native pointers/collections and stored
registered fields are recorded without invoking their getters. Resource bytes,
geometry, evaluated values and animation playback are not accepted here.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_shader_witness_008 as shader
import mesh_cache_current_input_007 as current

require, digest = shader.require, shader.digest


class Inventory(shader.ShaderWitness):
    def __init__(self):
        super().__init__()
        self.unsupported, self.guards, self.struct_counts = {}, {}, {}

    @staticmethod
    def _file(path):
        return {'path': str(Path(path).absolute()), 'scope': 'metadata-only; bytes not read'}

    def _image(self, image, identity):
        # Preserve the exact007 safe field scope; omit byte/decode reads.
        skip = {'pixels', 'packed_file', 'packed_files', 'tiles', 'views', 'render_slots',
            'filepath', 'filepath_raw', 'size', 'bindcode', 'depth', 'channels', 'has_data',
            'is_dirty', 'is_float', 'is_stereo_3d', 'is_multiview', 'display_aspect',
            'type', 'colorspace_settings', 'stereo_3d_format', 'preview', 'animation_data'}
        return {'identity': identity(image), 'state': self._state(image, identity, 'Image:'+image.name_full, skip=skip),
            'colorspace': self._nested(image.colorspace_settings, identity, 'Image.colorspace_settings'),
            'resource': {'identity': identity(image), 'scope': 'API inventory only; resource content unproved'}}

    def _state(self, value, identity, path, handlers=None, skip=()):
        import bpy
        base, handlers = shader.base, dict(handlers or {})
        excluded = base.SKIP | frozenset(skip)
        if isinstance(value, bpy.types.ID):
            excluded |= {'name', 'name_full'}
        props = [prop for prop in value.bl_rna.properties if prop.identifier not in excluded]
        require(sum(self.struct_counts.values()) < 20000, 'Inventory struct budget exceeded')
        before_raw = base._raw(value, identity)
        before_bits = tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in props)
        set_bits = dict(before_bits)
        unsupported = set()
        for prop in props:
            name = prop.identifier
            runtime = bool(getattr(prop, 'is_runtime', False))
            fixed = getattr(prop, 'fixed_type', None)
            known_unset = runtime and prop.type == 'POINTER' and not set_bits[name] and fixed is not None
            known_panel = name == 'panel_states' and shader.panel_property(value, prop)
            if ((runtime and not known_unset) or (not runtime and prop.type not in
                    {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'} and name not in handlers and not known_panel)):
                row = {'path': path+'.'+name, 'owner_type': value.bl_rna.identifier, 'field': name,
                    'type': prop.type, 'fixed_type': fixed.identifier if fixed is not None else None,
                    'is_runtime': runtime, 'is_property_set': set_bits[name], 'getter_invoked': False}
                self.unsupported[row['path']] = row
                unsupported.add(name)
        # The original source-read guards remain. No unsupported getter runs.
        result = super()._state(value, identity, path, handlers, excluded | unsupported)
        after_bits = tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in props)
        require(before_raw == base._raw(value, identity) and before_bits == after_bits,
            'Inventory getter changed raw/set status: '+path)
        self.guards[path] = {'raw_sha256': digest(before_raw), 'set_bits_sha256': digest(before_bits)}
        kind = value.bl_rna.identifier
        self.struct_counts[kind] = self.struct_counts.get(kind, 0)+1
        return result

    def snapshot(self, scene):
        self.unsupported, self.guards, self.struct_counts = {}, {}, {}
        value = self.capture(scene)  # stored only; no depsgraph, seek or update
        return {'safe_fields_sha256': value['sha256'], 'unsupported': sorted(self.unsupported.values(), key=lambda row: row['path']),
            'raw_set_guards': self.guards, 'struct_counts': self.struct_counts,
            'scope': 'Known bounded shader fields only; omitted unknown getters are descriptors, not inspected content. No resource-byte or evaluated/pixel proof.'}


def pin(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def context(bpy):
    scene = bpy.context.scene
    return {'filepath': bpy.data.filepath, 'scene': int(scene.as_pointer()),
        'frame': [scene.frame_current, float(scene.frame_subframe)], 'dirty': bool(bpy.data.is_dirty),
        'view_layer': int(bpy.context.view_layer.as_pointer()),
        'objects': sorted((int(obj.as_pointer()), obj.session_uid) for obj in scene.objects)}


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath
        and bpy.app.version[:2] == (5, 2), 'Fresh private factory background Blender5.2 required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1' for index, value in enumerate(native[:-1])), '-t1 required')
    snapshot, receipt_pin = current.load_snapshot(args.snapshot_report, args.snapshot_sha256, args.input_sha256, args.input_bytes)
    source, artist = Path(snapshot['copy']['path']).resolve(), Path(snapshot['artist_before']['path']).resolve()
    require(source != artist and not os.path.samefile(source, artist), 'Never open artist/hardlink')
    input_pin, artist_pin = pin(source), pin(artist)
    stage_proof = current.scene_source_proof()
    package = current.STAGE06/'addons/character_designer'
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    require(Path(addon.__file__).resolve().parent == package, 'Different standard package')
    import native_validation_support as base
    original_handlers = base.handler_snapshot()
    report.update(input_before=input_pin, artist_before=artist_pin, current_snapshot_receipt=receipt_pin,
        stage_proof=stage_proof, blender=bpy.app.version_string, pid=os.getpid(),
        scripts={path.name: pin(path) for path in (Path(__file__), shader.BASE_PATH, Path(shader.__file__), Path(current.__file__))})
    registered = False
    try:
        addon.register()
        registered = True
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False), 'Private current input open failed')
        scene = bpy.data.scenes.get(snapshot['source_identity']['scene'])
        require(scene is bpy.context.scene and Path(bpy.data.filepath).resolve() == source, 'Loaded current context differs')
        before, callbacks = context(bpy), base.handler_snapshot()
        witness = Inventory()
        first = witness.snapshot(scene)
        second = witness.snapshot(scene)
        report.update(inventory=first, repeat_inventory_exact=first == second,
            source_context_exact=before == context(bpy), normal_handlers_preserved=callbacks == base.handler_snapshot())
        require(report['repeat_inventory_exact'] and report['source_context_exact'] and report['normal_handlers_preserved'],
            'Read-only inventory guard failed')
        report['inventory_completed'] = True
    finally:
        errors = []
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        cleanup = {'errors': errors, 'handlers_restored_exact': original_handlers == base.handler_snapshot(),
            'input_disk_unchanged': input_pin == pin(source), 'artist_disk_unchanged': artist_pin == pin(artist),
            'stage_unchanged': stage_proof == current.scene_source_proof(),
            'scripts_unchanged': all(row == pin(row['path']) for row in report['scripts'].values())}
        report['cleanup'] = cleanup
        require(not errors and all(value for key, value in cleanup.items() if key != 'errors'), 'Inventory cleanup failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('snapshot-report', 'snapshot-sha256', 'input-sha256', 'report'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--input-bytes', required=True, type=int)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    path = Path(args.report).resolve()
    require(path.parent == HERE and path.suffix == '.json' and not path.exists(), 'Unused direct project report required')
    report = {'schema': 'x.current-shader-api-inventory/1', 'completed': False, 'acceptance': False,
        'no_scene_save': True, 'no_seek_update_manual_solver_or_defer': True,
        'scope': 'Private input metadata/safe stored fields only. Not full source RAM, geometry, resources, evaluated shader or performance acceptance.'}
    stream = path.open('x', encoding='utf-8')
    try:
        main(args, report)
        report['completed'] = report.get('inventory_completed') is True
    except BaseException:
        report['error'] = traceback.format_exc()
        raise
    finally:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        stream.close()
