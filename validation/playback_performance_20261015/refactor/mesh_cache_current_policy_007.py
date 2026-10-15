"""Explicit current-input checks around the two unchanged numerical kernels."""
import importlib
from pathlib import Path

import mesh_cache_current_contract_007 as contract
import mesh_cache_current_input_007 as current_input
import mesh_cache_shader_witness_007 as shader

base, require = contract.base, contract.require
HERE = Path(__file__).resolve().parent


class CurrentPolicy:
    def __init__(self, snapshot, snapshot_receipt_pin, source_seal_pin, tiny_pin, report):
        self.snapshot = snapshot
        self.snapshot_pin = snapshot['copy']
        self.snapshot_receipt_pin = snapshot_receipt_pin
        self.source_seal_pin = source_seal_pin
        self.sources = contract.verify_sources(source_seal_pin)
        self.stage_proof = current_input.scene_source_proof()
        self.contract = contract
        self.report = report
        self.source_shader = shader.ShaderWitness()
        self.target_shader = shader.ShaderWitness()
        self.source_before = self.session = None
        self.native_reverse = self.shader_id_mapping = None
        self.golden_shader = {}
        report.update(current_snapshot_receipt=snapshot_receipt_pin,
            current_snapshot_identity=snapshot['source_identity'], current_source_seal=source_seal_pin,
            current_sources=self.sources, tiny_fixture_receipt=tiny_pin,
            current_frame_domain={'frames': list(contract.FRAMES), 'fps': 30, 'fps_base': 1.0},
            visibility_replay=[], shader_replay=[],
            adapter_sources=self.sources,
            current_resources_final_before_cleanup_exact=False,
            limits=['Source is the guarded current SaveCopy at its receipt timestamp; later artist edits require recapture.',
                'Exact integer1–30 geometry, normals, UV/attributes/weights/world and Base state are checked.',
                'Material graph/parameters/drivers and external or packed resource bytes are compared; shader pixels and implicit coordinates remain unproved.',
                'PC2 and resource files remain external persistent local dependencies; no portable package, subframe or motion-blur claim.',
                'No artist writes, deployment, automatic adoption, or GUI FPS claim.'])

    def scene_module(self, package, report):
        return current_input.load_scene_module(package, report)

    def choose_witness(self, args, report):
        return importlib.import_module('mesh_cache_actor_full30_004').choose_v9(args, report)

    def loaded_source(self, bpy):
        identity = self.snapshot['source_identity']
        scene = bpy.data.scenes.get(identity['scene'])
        require(scene is not None and identity['view_layer'] in scene.view_layers, 'Captured Scene/ViewLayer missing')
        bpy.context.window.scene = scene
        bpy.context.window.view_layer = scene.view_layers[identity['view_layer']]
        require([scene.frame_current, float(scene.frame_subframe)] == identity['frame'], 'Captured saved frame differs')
        require(scene.frame_start == 1 and scene.frame_end == 30 and scene.render.fps == 30
            and float(scene.render.fps_base) == 1.0, 'Current clip must be1–30/30FPS')
        return scene

    @staticmethod
    def capture(witness, scene, reverse=None):
        import bpy
        require(bpy.context.scene is scene, 'Shader capture requires the current Scene depsgraph')
        return contract.json_value(witness.capture(scene, reverse, depsgraph=bpy.context.evaluated_depsgraph_get()))

    def begin_source(self, scene, report):
        require(self.source_before is None, 'Source protection baseline already captured')
        self.source_before = self.capture(self.source_shader, scene)
        report['protected_shader_before'] = self.source_before

    def protect_source(self, scene):
        require(self.source_before is not None, 'Source shader baseline missing')
        exact = self.capture(self.source_shader, scene) == self.source_before
        self.source_shader.verify_resources()
        if self.session is not None and not self.session.closed:
            verified = False
            if 'reopen_contract' in self.report:
                contract.verify_shader_resources(self.session.scene, self.report['reopen_contract'])
                verified = True
            elif self.report['shader_replay']:
                self.target_shader.verify_resources()
                verified = True
            if verified:
                self.report['current_resources_final_before_cleanup_exact'] = True
        return exact

    def source_frame(self, scene, frame):
        require(frame in contract.FRAMES, 'Source shader frame outside fixed domain')
        value = self.capture(self.source_shader, scene)
        self.golden_shader[frame] = value
        return value

    def bind_target(self, session, report):
        require(self.session is None and session.source_scene is not session.scene and not session.closed,
            'One isolated disposable target required')
        self.session = session
        self.native_reverse = {target: source for source, target in session.id_map.items()}
        self.shader_id_mapping = shader.serialize_id_mapping(session.id_map)
        report['visibility_contract'] = session.view_layer_state
        report['source_to_clone_visibility_exact'] = True
        report['shader_id_mapping'] = self.shader_id_mapping

    def target_frame(self, scene, frame, reverse, report):
        require(self.session is not None and scene is self.session.scene, 'Different target Scene')
        all_layers = not report['visibility_replay'] or len(report['visibility_replay']) == 149
        result = contract.visibility.check_visibility(scene, self.session.view_layer_state, all_layers=all_layers)
        report['visibility_replay'].append({'frame': frame, 'exact': result['exact'], 'subframe': float(scene.frame_subframe)})
        value = self.capture(self.target_shader, scene, self.native_reverse)
        expected = self.golden_shader[frame]
        exact = value == expected
        report['shader_replay'].append({'frame': frame, 'exact': exact,
            'source_sha256': expected['sha256'], 'target_sha256': value['sha256']})
        require(exact, 'Current material graph/parameters/resources differ at frame '+str(frame))

    def scene_sources_unchanged(self):
        return self.stage_proof == current_input.scene_source_proof()

    def finalize_clip(self, report):
        report['all_replay_visibility_exact'] = len(report['visibility_replay']) == 150 and all(row['exact'] for row in report['visibility_replay'])
        report['all_replay_materials_exact'] = len(report['shader_replay']) == 150 and all(row['exact'] for row in report['shader_replay'])
        report['current_sources_unchanged'] = self.sources == contract.verify_sources(self.source_seal_pin)
        report['current_scene_sources_unchanged'] = self.scene_sources_unchanged()
        require(all(report[key] is True for key in ('all_replay_visibility_exact', 'all_replay_materials_exact',
            'current_sources_unchanged', 'current_scene_sources_unchanged', 'current_resources_final_before_cleanup_exact')),
            'Current clip material/visibility/source proof failed')
        contract.validate_tiny(report['tiny_fixture_receipt']['path'], report['tiny_fixture_receipt']['sha256'])
        contract.verify_pin(self.snapshot_receipt_pin)

    def bind_stage_proof(self, passed, report):
        require(passed['current_scene_source_proof'] == self.stage_proof
            and passed['current_snapshot_receipt'] == self.snapshot_receipt_pin, 'Assembler capture/stages differ')
        report['dependency_pins'].update(self.sources)

    def finalize_assembly(self, report):
        report['current_sources_unchanged'] = self.sources == contract.verify_sources(self.source_seal_pin)
        report['current_scene_sources_unchanged'] = self.scene_sources_unchanged()
        require(all(report[key] is True for key in ('current_sources_unchanged', 'current_scene_sources_unchanged',
            'current_resources_final_before_cleanup_exact')), 'Current assembler material/resource/source proof failed')
        require(report['reopen_contract']['visibility'] == report['visibility_contract'], 'Serialized Base contract differs')
        contract.verify_pin(self.snapshot_receipt_pin)


def prepare_capture(args, report):
    snapshot, receipt_pin = current_input.load_snapshot(args.snapshot_report, args.snapshot_sha256, args.input_sha256, args.input_bytes)
    require(Path(args.input).resolve() == Path(snapshot['copy']['path']).resolve()
        and Path(args.artist).resolve() == Path(snapshot['artist_before']['path']).resolve(), 'Explicit current copy/artist routes differ')
    source_seal = base.pin(HERE/'current_cache_sources_007.json')
    require(source_seal['sha256'] == args.source_seal_sha256, 'Current source seal CLI SHA differs')
    tiny = contract.validate_tiny(args.tiny_report, args.tiny_sha256)
    return CurrentPolicy(snapshot, receipt_pin, source_seal, tiny, report)


def prepare_assembly(args, report):
    passed, _ = contract.load_full30(args.full30_report, args.full30_sha256)
    require(passed['current_source_seal']['sha256'] == args.source_seal_sha256, 'Assembler source seal CLI SHA differs')
    snapshot, pin = current_input.load_snapshot(passed['current_snapshot_receipt']['path'],
        passed['current_snapshot_receipt']['sha256'], passed['input_before']['sha256'], passed['input_before']['bytes'])
    require(Path(args.artist).resolve() == Path(snapshot['artist_before']['path']).resolve(), 'Assembler artist route differs')
    return CurrentPolicy(snapshot, pin, passed['current_source_seal'], passed['tiny_fixture_receipt'], report)
