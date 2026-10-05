"""Factory-only native RNA proof, no artist open/save and no effect claims."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "experimental_direct_cloth_render.py"
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == "b91fa8379eaca5198ff8d843887c76e3c1e6f391d91cdd55c05801bc32128ce0"
assert bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath
assert "--disable-autoexec" in sys.argv
bpy.context.preferences.use_preferences_save = False
sys.path.insert(0, str(HERE))
import experimental_direct_cloth_render as frozen

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--render", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
assert not args.output.exists()
args.output.mkdir()

rig_data = bpy.data.armatures.new("QA Empty Armature")
rig = bpy.data.objects.new("QA Empty Armature", rig_data)
bpy.context.scene.collection.objects.link(rig)
mesh = bpy.data.meshes.new("QA Modifier Settings Mesh")
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
source = bpy.data.objects.new("QA Modifier Settings Source", mesh)
bpy.context.scene.collection.objects.link(source)
arm = source.modifiers.new("Armature", "ARMATURE")
arm.object = rig
subsurf = source.modifiers.new("Subdivision", "SUBSURF")
arm.is_active = True
subsurf.is_active = False
expected = [frozen.strict_rna(modifier) for modifier in source.modifiers]
wrapper = source.copy()
wrapper.name = "QA Modifier Settings Wrapper"
bpy.context.scene.collection.objects.link(wrapper)
originals = tuple(wrapper.modifiers)
before = [frozen.strict_rna(modifier) for modifier in originals]
assert before == expected
added = wrapper.modifiers.new("QA Position Pass Through", "NODES")
wrapper.modifiers.move(2, 1)
after_add = [frozen.strict_rna(modifier) for modifier in originals]
diffs = [{key: {"before": left[key], "after": right[key]} for key in left if left[key] != right[key]}
         for left, right in zip(expected, after_add)]
assert diffs == [{"is_active": {"before": True, "after": False}}, {}], diffs
for modifier, original in zip(originals, expected):
    modifier.is_active = original["is_active"]
added.is_active = False
after_restore = [frozen.strict_rna(modifier) for modifier in originals]
source_after = [frozen.strict_rna(modifier) for modifier in source.modifiers]
assert after_restore == expected and source_after == expected
assert not added.is_active and [modifier.type for modifier in wrapper.modifiers] == ["ARMATURE", "NODES", "SUBSURF"]
report = {"success": True, "runtime": bpy.app.version_string,
          "factory_empty_scene_only": True, "artist_opened": False, "artist_saved": False,
          "all_writable_RNA_diff_before_restore": diffs,
          "source_exact": True, "copied_modifiers_exact_after_active_restore": True,
          "new_modifier_inactive": True, "native_geometry_effect_proved": False,
          "frozen_source_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest()}
path = args.output / "modifier_activation.json"
path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("MODIFIER_ACTIVATION_PROOF=" + str(path), flush=True)
