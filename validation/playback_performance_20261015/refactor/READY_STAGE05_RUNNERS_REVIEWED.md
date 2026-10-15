Use this final preparation addendum with READY_STAGE05_RUNNERS.md. No native
job, UI interaction or artist operation was run by this agent.

Final dependency seal is `native_runner_dependencies_005_reviewed_v2.json`,
SHA256 `dec89b9a6eb132ee2964b06864816baa03bb636339c1b1847868e8af9151e2dd`.
Both earlier unrun candidate manifests are superseded and retained. The Stage05
source manifest and immutable Stage02 fixture manifest remain unchanged.

The final source witness SHA is
`e0a56ab2c38546a36dd90eaca1dc74ca1ad57da61bab7528b602144157ef8135`;
v5 support SHA is
`68451f7cc73d582da148b6a4efcbdf3596edaf4285310a3e40997273d70ff2ce`.
It additionally treats Object.active_shape_key and Key.reference_key as compact
name/pointer/index references. Every key's coordinates remain bulk-hashed;
generic RNA traversal cannot expand those links into point dictionaries.
Retained pure checks now pass ten cases, including traps against both unwanted
geometry traversal routes. All eight Python files compile.

Use NEW `scene_builder_smoke_005_v2.py` (SHA
`146b8ed27b600e064d55feb0252a2d7dfe67712654c399ddc5c0d51c1270f5ef`)
for the factory smoke. The original unrun Smoke005 remains unchanged. The new
smoke generates Basis plus one foreign shape key on unlinked Hair1 and requires
all source witness coverage BEFORE any graph clone: stored Scene setup status,
the exact catalog orphan field path ending assets[1].object -> Hair1, foreign
Object membership, raw Mesh/Key payload IDs and both payload components. Missing
coverage fails with its scope/catalog diagnostics and prevents an actor run.
This explicitly tests actual native is_property_set semantics; pure fakes do
not establish them.

After Console's actual END and root's serialized memory/window gate, root's
first command is:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/scene_builder_smoke_005_v2.py' -- --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_scene_smoke_report_005.json'
```

The frozen v5 / Bone005 command order and unused report names in the prior
guide remain correct: actual smoke PASS, frozen admission PASS, then full
frozen 1–30/ABBA; optional Bone admission, full Bone and separate synthetic
fixtures only at root's choice. No geometry metric or tolerance guard changed.
All new Bone005 imports point to v5 witnesses/scene helpers. No smoke/admission
or background result establishes GUI FPS or artist adoption.
