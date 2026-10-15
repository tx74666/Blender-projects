# Frozen forearm playback validation

This is a prepared validation path. It has not run Blender, changed the artist,
deployed a candidate, or measured a performance improvement.

The fixed default input is the existing private saved copy
`../../playback_performance_20261014/round4/input_saved_20261015.blend`, SHA256
`40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721`,
34691613 bytes. The earlier completed artist pin `ad5bf8ec...` is historical;
the actual artist disk has since changed. A later copy may be used only with an
explicit SHA256/length pin. Never open `X.blend` in this worker. Record its disk
pin before and after as a protection witness, without assuming its current
contents or holding its GUI.

The worker imports a pinned staged Character Designer package, the new
`forearm_twist_playback_core` module, and the root-owned isolation builder. All
source files in the staged package are pinned before import and checked again
at exit. Authoring calculation must retain the `.41` numeric/rejection path;
the source manifest identifies the preserved authoring functions and relevant
dependencies. Candidate work and test scripts stay local until accepted.

The root-owned builder must clone the complete actor dependency graph into a
separate disposable Scene, with private objects, mesh/armature/Shape Key data
and animation Actions, plus correctly remapped native ID references and saved
calibration links. A source mesh or rig must have no membership in the clone
Scene, and each cloned dependency must map back to exactly one source ID.
Shared mutable deformation/animation data is a failure. Canonical validation
and immutable template capture happen on the private source before clone IDs
exist. The target then binds the issued single-use template after exact static
data comparison; it does not run Original20 validation on duplicated identities.

The native comparison runs the source authoring route and the clone core route
on integer frames 1–30 in one private background process (`-t 1`). Automatic
forearm handlers are suppressed through the existing owned `defer_runtime`
scope, rather than removed or replaced. Both branches perform the same native
frame advance, graph evaluation, corrective publication and final graph update.
The source branch invokes the existing authoring calculation; the clone branch
calls each binding's `evaluate`. Golden source frames are captured before the
first clone exists. Every authoring ABBA block runs after complete clone cleanup;
every candidate block builds a fresh disposable scene and warms it before
timing. This is not a GUI playback test.

Every frame compares all paired meshes' evaluated coordinates, topology,
normals, corner normals, materials/indices, UVs, attributes and vertex-group
weights, every Shape Key's full coordinates/value/mute/relative link, and all
paired rigs' evaluated poses and Rest matrices. Clone display names are mapped
back to source identity only for explicitly cloned ID labels; native numeric
fields are never rounded or normalized. Each active Forearm side must remain
enabled, value 1, unmuted, with complete support, and no runtime/core errors.
Record compact component SHA256s and counts, without dumping vertex arrays.

Do not time a candidate after an exact differential failure. Preparation is
reported separately: actor cloning, canonical preparation, then frozen binding
construction. Repeated evaluation uses eight controlled ABBA blocks with two
warm frames and eight hot frames per block. Raw frame times, core stage times,
frame coverage and per-block medians are retained. Hash work and scene switching
are outside the measured region. Nested timings cannot be added to totals.

Close every owned binding and private scene, restore source context and the
runtime guard, unregister only this worker's registration, and prove no owned
handlers/timers/private IDs remain. Pin source assets around candidate execution
to prove that the authoring input was not changed. On failure retain the report,
exception, partial frame coverage and cleanup result; never relabel it PASS.

Native output equivalence and lower background times are prerequisites for a
later serialized GUI measurement on the artist. They do not establish 30 FPS,
future editing compatibility, physical simulation support, or bone replacement
equivalence. No reciprocal conversion of milliseconds to claimed GUI FPS.

No native/background/UI/heavy run may start until the shared window is released
and the root confirms the current memory/coordination state. Current work is
limited to source reads, runner construction, `py_compile` and pure scaffold
checks.
