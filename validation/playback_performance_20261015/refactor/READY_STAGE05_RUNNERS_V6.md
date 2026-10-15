Final loaded-actor preparation uses `native_runner_dependencies_005_reviewed_v3.json`,
SHA256 `6af6c2bfe15d99ac00717bae6f4a488d845dd2a984fc707f3e690abfa700dfa0`.
It seals twelve dependencies, including root's Bake006 and its fixed decision
policy. Earlier unrun dependency seals and entry points are retained. Stage05
source and the existing Stage02 fixture manifest are unchanged.

New frozen v6 SHA
`3e8991008438b1174974b04c49be8cb14c5ded100949248c974773ae06a276d4`;
new Bone006 SHA
`6402af01ffde9fd14ab8a98e7eb5d242bec0bcbd83d467109e17bf97d7befe76`;
root's Bake006 SHA
`e4a776b283872ce4ea40f9d1d9c34e9ca16f6031491a70994c14290a4ca4a2c0`.

The new shared helper assert_fixed_source_reference_coverage(scene, props,
input_pin) runs immediately after initial source properties are captured and
before any clone. It requires the exact fixed 40644… SHA and byte length,
source Scene assets[3].object typed reference to the registry's Hair1 with exact
pointer/UID, foreign Hair1 Object scope, actual raw Mesh payload ID/component,
and Key payload ID/component if Hair1 has keys. It looks up bpy.data.objects
directly and invokes no Scene PropertyGroup getter. Missing loaded-file coverage
raises; factory-fresh coverage cannot substitute. The gate returns the compact
report.initial_source_reference_coverage receipt only when all checks pass.

Eleven Python sources compile. Pure gate checks passed full/optional-no-Key
coverage and rejected wrong path/UID or missing Object/Mesh/Key coverage. A
forbidden Scene PG getter trap was untouched. Existing ten v5 pure checks remain
passing. Independent source review approved the tiny gate and all three call
sites. These checks do not establish actual native coverage or equivalence.
No Blender/UI/native job, artist open/save or deployment was performed here.

Root alone executes after Console's actual END and the shared memory/window
gate. First use the unchanged Smoke005_v2 command from
READY_STAGE05_RUNNERS_REVIEWED.md, unused native_scene_smoke_report_005.json.
After actual factory smoke PASS, run frozen loaded admission:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/private_playback_native_runner_v6.py' -- --input 'D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/input_saved_20261015.blend' --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --builder-module character_designer.forearm_twist_playback_scene --admission-only --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_admission_report_006.json'
```

After actual admission PASS, use the same v6 command without --admission-only
and unused native_frozen_report_006.json for complete 1–30/ABBA validation.
At root's choice the Bone admission command is:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_preview_runner_006.py' -- --input 'D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/input_saved_20261015.blend' --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --admission-only --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_admission_report_006.json'
```

Its full run omits --admission-only and uses unused native_bone_report_006.json.
Synthetic005 opens no file and remains unchanged; use its existing Stage02
fixture command from READY_STAGE05_RUNNERS.md. Bake006 is a separate full
source/live/baked experiment, with no artifact-writing branch:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_bake_runner_006.py' -- --input 'D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/input_saved_20261015.blend' --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --geometry-policy exact --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_bake_report_006.json'
```

Any choice of practical005 belongs to root's fixed decision policy, never a
change to the witness or automatic artifact/adoption eligibility. Background
smoke/admission/timing cannot establish actual GUI FPS or artist adoption.
