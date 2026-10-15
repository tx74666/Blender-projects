Stage05 runners are prepared source-only. No Blender process, GUI interaction,
artist open/save or deployment was started by the validation agent. Root owns
all serialized execution after Console's actual END and its memory/window gate.

Use `native_runner_dependencies_005_reviewed.json`, SHA256
`829344a1474636e6c5abd1c9c052715d5c57263be010390b5afd09a825f22473`.
The earlier `native_runner_dependencies_005.json` is an unrun obsolete draft
from before the getter-safety review; retain it, but do not execute its pins.
All historical v2/v3/v4, Smoke003/004, Bone004, Stage01–04 and native reports
remain untouched. The reviewed manifest seals all new entry points, both old
support dependencies, the new witness helpers and the retained pure checks.

Stage05 source manifest SHA
`d62c3178ca6f0615fa4517440c157bba0ab2ced87cb64aa560ac1830197bac34`
was verified against all 162 staged Python files without Blender. Synthetic
Bone005 uses the existing immutable Stage02 fixture manifest, SHA
`ff45ab73077d3f848e2db2c315df7c7cefcfdf2061947ec8388e07c111ccabcc`;
both fixture file pins were verified. No source or fixture manifest was changed.

V5 preserves the original output oracle and comparison rules. It extends
source_property_witness(scene) with exact stored registered Scene/Object RNA,
native ID-reference paths and referenced outside-scene Object/data/Key/Action
payloads. It checks every stored getter's set bit and each nested structure's
own raw storage before/after reads, plus the complete set-bit vector. Unset
registered fields are represented by set-status and RNA schema/default
descriptors without invoking their getter. Their computed/default getter
outputs are explicitly unclaimed. Foreign raw mesh coordinates/topology,
normals/attributes/UV/weights and key bytes are hashes. Other Material/Image/
World/Node IDs are exact references only here; no pixel/node-content or foreign
evaluated-geometry claim is made. Native users/tag/update bookkeeping is omitted
because private graph references alter bookkeeping without changing payloads.

Independent source review found no remaining current witness blocker. Seven
Python files compile. Retained `source_reference_witness_v5_pure_checks.py`
passes eight checks: stored Hair1 reference, foreign location and stored role
mutations, repeat exactness, unset getter trap, hidden cross-field set-bit write,
nested own-raw write, and normal no-storage-write behavior. These are pure
scaffold checks; all native APIs/equivalence remain unverified.

Smoke005 registers/unregisters only this staged addon in its factory worker.
It retains the earlier material/world/compositor/nested-group/read-only Image
checks and adds linked Cube plus unlinked Hair1 typed catalog rows. It requires
clone linked-object remapping, orphan pointer None with row/role/order/active
index retained, exact detachment receipt, source catalog and foreign Hair1
payload preservation before and after private close, handler/timer cleanup,
owned fixture cleanup and disk/source/helper pins. Optional driver/META rejection
fixtures were not added. Smoke and witness checks are outside performance timing.

The commands below require unused report filenames. Run factory smoke first:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/scene_builder_smoke_005.py' -- --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_scene_smoke_report_005.json'
```

After actual smoke passes, run frozen saved-frame admission. It skips all ABBA
timing and retains all_30_complete_outputs_exact=false:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/private_playback_native_runner_v5.py' -- --input 'D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/input_saved_20261015.blend' --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --builder-module character_designer.forearm_twist_playback_scene --admission-only --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_admission_report_005.json'
```

Only after actual admission passes, run full frozen 1–30 exact differential and
ABBA timing with the same command, omit `--admission-only`, and use the unused
report `native_frozen_report_005.json`.

Root may then choose Bone005 admission. Its helper matrix oracle, strict
nonvector fields and full coordinate/normal errors retain every original rule;
there is no automatic numeric tolerance eligibility:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_preview_runner_005.py' -- --input 'D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/input_saved_20261015.blend' --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --admission-only --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_admission_report_005.json'
```

The full Bone005 run uses that command without `--admission-only` and unused
`native_bone_report_005.json`. Separate synthetic swing/twist fixtures use:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_synthetic_runner_005.py' -- --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --fixture-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_02/fixture_manifest.json' --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_synthetic_report_005.json'
```

No smoke, admission, background timing or source preparation establishes GUI
FPS, all-animation/subframe/physics equivalence, artist adoption or bake export
eligibility. The staged saved input is the fixed 40644… copy; the artist is only
read for disk pins and is never opened or saved by these workers.
