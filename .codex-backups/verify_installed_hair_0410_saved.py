"""Read-only cold-start verification after the authorized X hair migration."""
import hashlib
import json
from pathlib import Path
import sys

import bpy

path = Path(bpy.data.filepath)
digest = hashlib.sha256(path.read_bytes()).hexdigest()
module = sys.modules.get('character_designer')
assert module is not None
assert module.bl_info['version'] == (0, 41, 0), module.bl_info
assert 'scripts\\addons\\character_designer' in module.__file__, module.__file__
module._validate_registration_integrity()
settings = bpy.context.window_manager.character_designer_hair_bones
assert 'active_variant' not in settings.bl_rna.properties
assert 'target_armature' in settings.bl_rna.properties
from character_designer import hair_bones_binding as binding
from character_designer import hair_bones_variants as variants
from character_designer import hair_bones_rig as rig
from character_designer import forearm_twist
source = bpy.data.objects['Hair3']
assert binding.is_bound(source)
assert not variants.variants_for(source)
assert len(source.data.vertices) == 469
assert all(name in bpy.data.objects for name in ('Hair1', 'Hair2', 'Hair3'))
target, head = binding.resolve_target(bpy.context, source)
assert target.name == 'CoshaRig' and head == 'Head'
record = rig._read_records(source)
assert len(record['chains']) == 13
cap = json.loads(source[binding.BINDING_KEY])['cap_vertices']
assert len(cap) == 162
group = source.vertex_groups['Head']
assert all(group.weight(index) == 1.0 for index in cap)
assert all(target.data.bones[chain['bones'][0]].parent.name == 'Head' for chain in record['chains'])
assert record['mirror_layout'] == 'BEFORE_ARMATURE_X'
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
assert forearm_twist._RUNTIME_REGISTERED and not forearm_twist._INITIALIZE_PENDING
assert not forearm_twist._ERRORS, forearm_twist._ERRORS
assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
print('INSTALLED_0410_SAVED_X_PASS=' + json.dumps(dict(version=module.bl_info['version'],
      source=source.name, rig=target.name, head=head, chains=len(record['chains']),
      bones=sum(len(chain['bones']) for chain in record['chains']), cap_vertices=len(cap),
      old_copies=0, forearm_errors=0, input_unchanged=digest)), flush=True)
