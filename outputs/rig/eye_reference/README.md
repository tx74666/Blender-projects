Read-only eye rig audit — 2026-09-09

Sources: Rain `D:\Blender Samples\Characters\Rain v3.3\rain_v3.2.blend` and X `D:\Blender\Projects\Character\X\outputs\rig\X_left_foot_reset_preview.blend`. Inspected using Blender 5.2 background factory startup with embedded scripts disabled. Neither blend was saved or modified on disk. All coordinates below are armature-local unless stated otherwise.

Rain reference

- Shared mask controller: `TGT-Eyes`, custom mesh `WGT-Eyes_Target`. Individual targets `TGT-Eye.L` / `TGT-Eye.R` are children of it and use `WGT-Eye_Target`.
- `AIM-Eye.L/R` have WORLD-space Damped Track constraints, local `TRACK_Y`, to their respective targets. `BB-Eye.L/R` inherit the AIM rotations; `DEF-Eye.L/R` copy BB rotations. Eye aim is local positive Y.
- `TGT-Eyes` has no bone parent. An Armature constraint switches among `ROOT_Child`, `MSTR-Pelvis`, `LOC-Pelvis`, and `DEF-Head`. `Properties_Face["eye_target_parents"]` controls one-hot weights; its saved value is 1, choosing `MSTR-Pelvis`.
- Target bone heads are `(±0.04673844, -0.76713520, 1.46994054)`. Eye pivots are approximately `(±0.04682155, -0.08945030, 1.47355175)`. Pivot spacing is 0.0936431; target depth along armature Y is 0.677685, or 7.24 times pivot spacing.
- The master wire has 56 vertices/56 edges and a pinched bridge between two lobes. Its displayed rest bounds give width 0.101495 and height 0.051661. Both individual wires have 32 vertices/32 edges; their displayed bounds are 0.025784 wide by 0.033340 high, so the source rings are slightly elliptical.
- Display scales are 0.10149539 for the mask and 0.03334433 for each ring, with custom-shape bone-size scaling disabled. Shape translation/rotation properties are zero. Raw geometry lies in local YZ; bone roll maps mesh Z to armature X and mesh Y nearly to armature Z.
- The original ring geometry has an offset: the displayed centers are approximately `x=±0.0286275`, inset by 0.0181109 from their target bone heads. This is a source-asset quirk, not a necessary control mechanic. Original analytic rings can be centered on their targets.
- Shape data in `rain_eye_wires.json` includes raw vertices, edge lists, normalized vertices, display settings, and calculated rest vertices/bounds. Reference geometry is credited to Blender Foundation / Blender Studio, Rain Rig, CC BY 4.0. Copying its topology is not required to implement the requested control pattern.

X current rig

The character rig is **`CoshaRig`**. Two other armatures, `Anime Girl Base Mesh` and `Anime Girl Base Mesh.001`, contain unrelated Rigify eye controls. Do not select a rig merely by finding an `eye.L` bone.

| Bone | Parent | Rest head | Rest tail | Local +Y expressed in armature space |
| --- | --- | --- | --- | --- |
| `Head` | `Neck` | `(0, 0.047589943, 1.760459900)` | `(0, 0.049121048, 1.912583828)` | `(0, 0.010064347, 0.999949396)` |
| `eye.L` | `Head` | `(0.021800358, 0.026740108, 1.849194288)` | `(0.048999600, -0.021604294, 1.849720716)` | `(0.490314692, -0.871493816, 0.009489805)` |
| `eye.R` | `Head` | `(-0.021800358, 0.026740108, 1.849194288)` | `(-0.048999600, -0.021604294, 1.849720716)` | `(-0.490314692, -0.871493816, 0.009489805)` |

- Both eye bones are deform bones with identity pose basis, no constraints, and no custom shapes. `Head` also has identity pose basis and no constraints. CoshaRig has no active action, NLA strips, or eye/head drivers.
- Eye pivot spacing is 0.0436007. The eyes' native look axes diverge outward approximately 29.36 degrees per eye, with a small upward component. Placing both targets parallel in front of the face would rotate the existing eyes on installation. To preserve the current bind pose, place each target on that eye's native head-to-tail ray and use positive-Y tracking.
- CoshaRig object transform is uniform scale `0.782315731`, translation approximately `(0, 0.027212646, 0.175622880)`. Build positions in armature space; do not apply this scale twice.
- Mesh `Cosha` is deformed by CoshaRig. The `eye.L` and `eye.R` groups each contain 81 vertices above weight 0.01.
- The file contains an unrelated action named ` Attack 1 (1_24)` with eye/head animation curves. It is not assigned to CoshaRig. No source animation needs detaching for this character.
- X's divergent rest rays spread individual targets rapidly with distance. Do not copy Rain's 7.24-times-spacing depth blindly. Choose a practical depth, and size the shared mask from the resulting target spacing so its shape surrounds the two rings.
- For a head-following shared target, parenting the shared control under `Head` and the two individuals under the shared control is acyclic; the existing eyes are children of `Head`. A full Rain parent-switch mechanism is separate from the requested mask/two-target interaction.

Reproduce the audit:

```powershell
& 'D:\Blender5.2\blender.exe' --background --factory-startup --disable-autoexec --python 'D:\Blender\Projects\Character\X\outputs\rig\eye_reference\audit_eyes.py'
```

The script writes the two eye audits and wire JSON files alongside this report. It has no save-mainfile operation.
