# Optional private Shoes Mirror pre-application

2026-10-15: source-only feasibility note. Not implemented, deployed, or measured.
Artist shoe topology and weights remain reserved for the user's later work.
No Blender, GUI, heavy job, or current artist inspection occurred for this note.

Applying a genuinely static Mirror once on an independently owned playback clone
can preserve the full mirrored shoe while removing repeated Mirror evaluation.
This is compatible with the private bone/Bake preview direction. It keeps both
shoe halves and the downstream Armature workload; it is not decimation.

Historical evidence: [late .41 snapshot](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/response_snapshot_1792005969313177800.json)
records Mirror → Armature, 28,177 base vertices, 76 groups, no Shape Keys,
ordinary LBS, ten material slots, no object drivers/NLA, and only three
delta_rotation_euler Action curves. This snapshot does **not** record
mirror_object or every Mirror RNA setting, and does not certify a future artist
state. The previous full evaluated result has 56,354 vertices.

The [old modifier localization](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/native_shoes_modifiers_report_20261015.json)
was private .41 with Cosha deleted: intact 32.332 ms, Mirror off 10.624 ms,
Armature off 17.122 ms, both off 7.672 ms. Those sequential samples were not
ABBA and changed the model. In particular, the 21.708 ms intact–Mirror-off gap
includes Armature processing half as many vertices. It is not a forecast for
pre-applying Mirror, which must retain all 56,354 vertices. Do not add these
component differences or convert them into GUI FPS.

## Narrow admission for a later experiment

- Use only an explicit disposable background scene, with separately owned shoe
  Object/Mesh and isolated Armature; source objects and artist disk remain fixed.
- Require exactly Mirror then Armature, both enabled, no Shape Keys, no animated
  Mesh data, and no preceding/downstream geometry or group consumers.
- Initially require mirror_object is None. This avoids a moving external mirror
  plane. Shoe Object animation is allowed: with a local mirror plane, animated
  object transforms do not by themselves change the mirrored local mesh.
- Read and pin the actual Mirror RNA settings and reject Action/NLA/driver paths
  that animate them. Preserve axis/bisect/merge/threshold/UV/material/vertex-group
  behavior through the native operation; do not substitute hand-written geometry.
- Freeze the source mesh, group mapping, raw weights, materials, UVs, normals and
  all attributes for the preview lifetime. An author edit invalidates the clone.

## Native operation and ownership requirements

Apply only the admitted first Mirror on the private clone in Object Mode; keep
Armature and its target/settings unchanged. Observe the native FINISHED result,
actual remaining modifier stack, and Object/Mesh identities rather than assuming
the operator keeps the same Mesh ID. Full source and clone-before-operation
protection must precede this transaction.

The [current scene session](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist_playback_scene.py)
tracks cleanup as (collection, pointer, session_uid). Its track_owned helper is
currently local to build_isolated_scene; close removes only recorded IDs and
refuses a reused pointer with a different UID. A later apply wrapper therefore
needs explicit ownership tracking for any newly allocated/replacement Mesh before
subsequent evaluation, plus correct session.id_map bookkeeping. Retain an old
owned orphan for cleanup. If native application retires a Mesh, reconcile that
specific before/after UID with a documented retirement instead of treating a
pointer alias as the old ID. Do not claim every globally new ID as this operation's
creation or delete ambiguous callback-created IDs. No such wrapper exists yet.

## Acceptance and priority

First finish and inspect the body bone/Bake proofs and remaining real playback
cost. Only implement this branch if the remaining shoe cost warrants it.

Compare the unmodified private complete scene against the Mirror-applied complete
scene for all 30 clip frames and representative fractional frames. Require the
same full evaluated topology/index order, coordinates, raw evaluated weights and
group mapping, vertex/corner normals, UVs, material indices, smooth flags, all
attributes and object matrices. Use the existing
[full shoe geometry oracle](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/probe_shoes_merge_07741.py)
as evidence coverage, extending it if native application introduces new fields.
Reject an unexplained difference; never waive it as a harmless topology change.
Verify the body/Bake result and original source graph remain protected too.

Only after the differential gate passes, run an interleaved current-input ABBA
comparison with both full shoe halves, the same body backend and rendering mode.
Record one-time apply cost, steady native evaluation, displayed playback FPS,
memory, source/input pins and complete session-UID cleanup separately. A later
shoe edit or changed Mirror dependency/settings is the rebuild trigger.
