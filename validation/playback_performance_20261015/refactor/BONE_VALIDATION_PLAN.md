# Paired bone preview experiment

Prepared only. No Blender, GUI, scene save, deployment or native worker has run
for this experiment. Stage01 is a historical unused source seal and must not be
overwritten or invoked. Stage02 remains pending the final independent source
review, including exact Plan/certificate identity ownership.

`native_bone_preview_runner.py` opens only the fixed private saved-copy pin,
never the artist. The complete `.41` source frames 1–30 are captured before any
cloned IDs exist. The current artist is protected by an external before/after
disk pin; the old artist closeout pin is not treated as current identity.

The source path uses full canonical authoring validation. Source `capture`
issues a template, and `plan_from_template` creates a one-use bone plan before
any core binding could consume the template. This branch never calls
`core.prepare` or `core.evaluate`. It uses the final background-only graph
builder and supplies both the exact certificate and isolated Scene to the bone
builder. Fresh complete source/clone static checks precede every modification.

Only private output data changes: approved native float32 lower/hand weight
transfers, new paired helper groups/bones, and muted/zeroed managed corrective
keys. Foreign Shape Key masks affected by transfers are copied to nondeform
groups. Full base weights are independently checked against the exact approved
rewrites; unrelated weights, topology, keys and original bones must remain.

Each frame reads the clone's evaluated original lower/hand deformations, updates
helper basis, lets Blender update natively, and verifies the helpers' evaluated
deformations against the requested matrices. Basis readback and evaluated matrix
oracle evidence is retained. Failure invalidates the private controller, retains
its exact error evidence, and stops acceptance. The fixed matrix bound cannot be
waived by the runner. The evaluated oracle is outside the timed pipeline.

The report compares complete evaluated float32 coordinates and vertex/face/
corner normals using exact hashes, maximum vector/component error, and RMS
error. Source coordinate bounding boxes and error fractions of their diagonals
make model-space differences interpretable. Scene unit settings and evaluated
object world transforms are observed; object-local differences are not silently
converted to millimeters. Normals use unitless component errors.

Topology, UVs, stored attributes (except the built-in position alias), material
bindings, original bone Rest/pose/channels, foreign key coordinates/values/mutes
and effective masks remain strict. Unconverted meshes must also keep exact
coordinate/normal outputs. Any strict difference retains all collected frames
and skips timing. Bone geometry errors are not automatically made eligible by a
tolerance threshold, even when the helper matrix oracle passes.

If strict fields pass, eight ABBA blocks measure the authoring route against
paired bones. Each A runs with no cloned IDs; each B builds and warms a fresh
private Scene. Source canonical capture, plan construction, cloning and bone
construction are separately reported. Hot timing splits frame advance, first
native update, corrective/helper update, and final native update. Hash/oracle
work and context switching are outside timing. Repeated candidate outputs must
reproduce the differential's exact candidate hashes and numeric differences.

`native_bone_synthetic_runner.py` is a separate factory-startup process that
opens no `.blend`. Its two existing fixture modules must be copied and sealed
beside the staged add-on. It generates a transformed ROLL_DECOUPLED fixture with
an affected foreign expression mask, and tests rest, +90/-90 degree twist,
0.35-radian bend plus 0.20-radian side wave, and combined 45-degree twist with
bend/side wave/elbow offset, at Subsurf levels 0 and 1. It carries the same matrix,
geometry and source-protection gates. A rejected matrix case remains a failure;
the saved actor or all other animations are not inferred from fixture results.

All own controllers/templates/plans/private Scenes and actual created IDs are
closed. Source frames and output are restored before owned addon teardown.
Handler order, known lifecycle timer removal, empty issuance registries, file
pins and source seals are checked. Generated fixture cleanup records native
session UID alongside pointer and collection; it cannot rely on pointer reuse.
Reports hold compact hashes/counts/metrics, with golden raw arrays compressed
only in worker memory.

This prepares evidence for deciding whether a bone backend is useful. It is not
an artist conversion, animation bake, export certification, GUI FPS result or
normal-performance guarantee. Native invocation still requires root's actual
shared-heavy window and current resource admission.
