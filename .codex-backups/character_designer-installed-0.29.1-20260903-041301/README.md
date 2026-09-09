# Character Designer 0.29.1

Character Designer is Randy's personal Blender add-on. It stays separate from
RR Helper and focuses on character-modeling tools.

Version 0.29.1 corrects Limb IK Pole defaults for rigs whose authored bend is
not aligned to a pure Armature-local Y axis. Analyze and **Default Direction**
now derive each chain's normalized modeled rest-joint residual relative to its
root-to-end chord. This keeps the actual lateral knee/elbow plane and avoids a
build-time twist. A chain without a measurable rest plane alone uses the fixed
fallbacks: arm-behind `-Y` and knee-forward `+Y` for a character facing `+Y`.
An existing generated Pole's saved direction still wins during hydration, so
updating the add-on never silently migrates an artist-selected direction.
To migrate an older generated rig, use **Remove Generated Rig → Analyze Rig →
select each limb and press Default Direction (or enter an explicit XYZ) → Build
All**. Analyze intentionally keeps the current edit buffer when the Armature is
unchanged, so Analyze alone does not replace those values after Remove.

Version 0.29.0 expands **Copy Weight to Opposite** with same-side multi-bone
selection in Pose Mode and Weight Paint. Every selected Deform-bone pair is
planned from one immutable Vertex Group snapshot, then the complete batch is
preflighted before the first write. All pairs commit as one Undo step, or any
invalid pair leaves every Vertex Group unchanged. The original active-group
single-copy workflow remains available when there is no intentional multi-bone
selection. Source names must end in exactly `.L` or `.R`; the tool never strips
or guesses through suffixes such as `.001`.

The directed copy treats each source as explicit rather than relying on
Blender's selection-dependent Mirror command. Character Designer resolves each
paired Deform bone, derives the source half from that bone in Mesh-local space,
keeps the source half exact, replaces the paired group on the opposite half,
and clears wrong-side memberships from both group names. The operation requires
unique spatial X pairs for every weighted source vertex, unlocked groups,
single-user editable Mesh data, and unchanged per-vertex Deform totals. It
fails before writing when the result would need an implicit Normalize or when
the rig, names, transform, or pairing is ambiguous. Other Vertex Groups remain
point-for-point unchanged and context is restored.

## Weight Symmetry

In Pose Mode or Weight Paint, select two or more same-side Deform Pose bones,
then open **Character Designer > Weight > Weight Symmetry**. The button reports
the selected count and copies all pairs together. In Weight Paint, leaving no
intentional multi-bone Pose selection preserves the original workflow: make a
side-named group such as `forearm.L` active and use the exact one-way action
**Copy forearm.L -> forearm.R**. Each pair uses only its source group's weighted
source-side support, so unrelated asymmetric parts of the same character mesh
do not block the operation.

This is an exact reassignment/copy tool, not a global Normalize command. It
overwrites each opposite group's side, clears source/target wrong-side
memberships, preserves center-line memberships and every other group, and
cancels the entire batch before writing if any pair is invalid or a per-vertex
Deform total would change. A completed single- or multi-pair operation is one
Blender Undo step.

Version 0.27.0 refines **Randy Rig: Limb IK** around the compact single-limb
selector and a first complete animator-facing control set. One identity-rest
`CTRL_master` moves the character through exact source-root constraints without
rewriting the artist hierarchy; its head and horizontal widget rest at
Armature-local ground zero. Arms use concave hand targets and dynamic
elbow Pole arrows; legs use sole-level foot targets, dynamic knee Pole arrows,
and `CTRL_heel_roll.*` controls driving hidden solver targets. Pole guide lines
stretch and aim live while only the actual Pole remains selectable. **Build IK**
creates only the limb shown in the dropdown; **Build All** completes every
populated Arm/Leg chain through one atomic build transaction and Undo step.
Partly filled chains fail closed before anything is generated. The former Build
Arms/Build Legs operators remain registered for script/keymap compatibility but
are no longer drawn. Finger-ring-with-bump
geometry is prepared for a later finger-control release but creates no bones.

Every dropdown limb has an explicit Armature-local **Pole Direction XYZ** and a
**Default Direction** button. A detected chain defaults to its modeled rest
bend; only a directionless chain uses the fixed anatomical fallback. Magnitude
is normalized, so **Pole Distance** remains the only distance control. Zero,
non-finite, or chain-parallel
directions fail before generated data is changed. Blender's evaluated IK solver
aligns the real elbow/knee residual to the visible Pole instead of compensating
back to a shallow modeled bend. A mathematically straight two-bone chain has no
stable bend plane, so Build fails closed with an instruction to add a small
elbow/knee bend first; measurable near-straight chains remain supported. New
Pole bones remember the applied direction;
0.26.1 rigs without that optional tag remain removable and rebuildable.

The generated graph is schema-versioned. Rebuild upgrades owned 0.25 legacy
limb controls in one transaction, while Remove continues to understand the old
inventory. Incremental Build and Rebuild neutralize and restore a moved Master
so no transform is baked twice. Master translation, rotation, and uniform scale
are supported; non-uniform scale is refused during Build/Rebuild because it
would introduce ambiguous IK shear. The heel control is a deliberately compact
first-pass heel/bank pivot, not Rain's complete reverse-pivot ball/toe system.
The Rain-inspired visual language is documented in
[ATTRIBUTION.md](ATTRIBUTION.md).

Generated bones, constraints, collections, widgets, and registries carry exact
versioned ownership. Repeated Build does not create suffix duplicates; foreign
same-name bones, pre-existing constraints, shared or linked Armature data, and
corrupt ownership fail closed. Remove/Rebuild validate the complete graph and
refuse artist animation, Drivers, foreign constraint references, foreign child
bones, or foreign collection members. Original deform-bone names, parents,
rest matrices, Deform/connect flags, Meshes, modifiers, Vertex Groups, and
weights remain untouched. This release still omits IK/FK switching, Spine IK,
finger controls, and shoulder/corrective deformation helpers.

Version 0.24.0 replaces proportional affected-weight scaling with **Full Auto
Blend (Normalized)**. When enabled, all editable Deform bones on the current rig
compete in one full Automatic Weights solve. Character Designer then applies
only the selected bones' old/new influence region: after locked weights reserve
their exact share, selected Bone Heat values get first claim on the remaining
budget, full-solver neighboring bones fill the remainder, and every affected
vertex totals one. Where locked weights leave the full budget available, a
target core therefore stays at weight 1 instead of turning an old `1 + 1`
overlap into `0.5 + 0.5`.
Pre-existing target leakage outside the full-rig solution is removed and repaired
from the full solver's local support. On a true half Mesh, generated-side pair
groups are kept empty so the Mirror modifier owns the opposite side. Non-Deform
groups, locked weights, and all vertices outside the repaired region remain
exact, except that a supported half Mesh has all invalid generated-side base
weights cleared. A non-empty locked generated-side group is refused and the
complete Vertex Group snapshot is restored. Any failed weighting transaction
likewise restores that snapshot. The session-only UI checkbox defaults on
but never dirties or persists into the `.blend`. The direct operator property
defaults to false, preserving omitted or explicit-false calls; scripts that
previously passed the 0.23 normalization flag as true now opt into the new Full
Auto Blend semantics.

Version 0.23.0 introduced the earlier **Normalize Affected Deform Weights**
option. Its equal proportional scaling is superseded in 0.24.0 because it could
dilute a full selected core and could not repair the spatial leakage of a
single-bone Bone Heat solve.

Version 0.22.0 reorganizes the sidebar with the same compact two-row page grid
used by RR Helper: **Hair / Weight / Rig** and **Modeling / Reference**. The
active page is visibly pressed, and only that tool family remains visible.
Weight Tools and Weight Flow now share the dedicated Weight page; Delta
Symmetry is under Modeling, Spline IK under Rig, and Reference Views under
Reference. The page choice is session-only (`SKIP_SAVE`), so changing pages
does not dirty or persist into `X.blend`.

Version 0.21.0 adds a separate **Weight Flow** section for topology-aware,
live-previewed weight transitions. In Weight Paint, select a non-branching
vertex chain, a closed loop, or a complete surface region with an interior;
then select exactly two visible Deform Pose bones. Weight Flow redistributes
only those two groups' existing per-vertex budget, so every other Vertex Group
remains point-for-point unchanged. Open chains interpolate by local arc length,
closed loops relax to their budget-weighted mean, and surface interiors use
inverse-edge-length harmonic passes while their selected boundary remains
fixed. Linear, Smooth, and Sharp profiles, a 0–1 Strength slider, and live
surface Iterations update the dialog Preview from the original snapshot rather
than accumulating. OK creates one Undo step; Esc, refresh, unregister, or any
failure restores the complete original group state.

Version 0.20.3 makes selected-bone weighting fail closed before it can produce
misleading results on an unsupported half-Mesh stack. A true half Mesh must use
one active object-local X Mirror with **Vertex Groups** enabled, and that Mirror
must be before the Armature modifier. Multiple X Mirrors, a custom Mirror
Object, extra Mirror axes, or an Armature-before-Mirror stack are refused with
a normal warning. Shared Mesh data is also refused so an unselected linked
duplicate cannot receive the same underlying weight edits; make the Mesh data
Single User first. Version 0.20.2 makes selected-bone weighting complete the Vertex Group naming
contract for a true half Mesh with X Mirror and **Vertex Groups** enabled. When
a selected source-side `.L`/`.R` bone has a real Deform counterpart but that
counterpart group is missing, the tool creates only an empty paired group. The
base Mesh receives no opposite-side weights; Blender's Mirror modifier then
assigns the evaluated mirrored vertices to the paired bone correctly. Existing
unselected groups and every weight remain byte-for-byte protected, and failure
removes any newly created empty pair during rollback. Version 0.20.1 makes the
Weight Tools UI English-only. Version 0.20.0 adds a
separate **Weight Tools** section with **Auto Weight Selected Bones**. It wraps
Blender's selected-bone Bone Heat solver in
an all-or-nothing transaction: only visible selected Deform bones may receive
new weights, while every other Vertex Group is checked point by point and must
remain exactly unchanged. It works with an existing Armature modifier and does
not re-parent the Mesh or replace modifiers. Mesh X Mirror and paint masks are
temporarily isolated so they cannot redirect the write into an unselected
counterpart group or limit the calculation to a masked subset, then their exact
states are restored. Parenting, modifier identity and order, every bone's
Deform flag, active Vertex Group, selection, and Pose/Weight Paint mode are
preserved. Any failure rolls the complete Vertex Group state back, and the
finished operation supports Undo.

Version 0.19.0 makes **Recover Applied Curve** modifier-aware without adding
another mode control. A source stack made only of **Mirror** and **Subdivision
Surface** is copied to each recovered Curve in its exact original order,
including Mirror axes/object/Bisect settings and Catmull-Clark or Simple
Subdivision levels. This retains a non-destructive stack instead of baking it
twice, and works for both Half and Full source profiles. Preview reports the
stack that will be preserved. Any other modifier is refused before a Curve is
written. Version 0.18.0 expands **Recover Applied Curve** with explicit Aligned Bezier
handles, a GPU-only live preview, and **Add** or **Replace Mesh** output. Add
keeps the source Mesh. Replace removes only the source Object, and only after a
complete source passes preflight and every recovered strand succeeds. Version
0.17.2 matches RR Helper's unobtrusive **Refresh Add-on** workflow. The button
appears only when installed Python files changed (or refresh needs attention),
reloads the add-on without saving or reloading the current `.blend`, and
disappears after the refreshed code becomes current. Version 0.15.3 makes the
compact placement controls operate directly on the
active generated Centerline in either Object Mode or Curve Edit Mode. Centered
and Surface move the Curve immediately; Blend's 0–1 Mix updates continuously
and persists on that Curve. Curve Edit Mode uses an in-place point update, so
the active object, edited data, control-point selection, and mode are preserved.
No new button is added. Version 0.15.2 originally introduced a save-first guard
for add-on refresh; the newer 0.17.2 workflow supersedes that guard by reloading
only Python modules, matching RR Helper and leaving the current `.blend` open
and unsaved in memory. Version 0.15.1 turns Hair Centerline **Blend** into a continuous 0–1 Mix:
0 is the exact Centered endpoint, 1 is the exact Surface endpoint, and every
intermediate value is available. The compact mode order is **Centered**,
**Surface**, **Blend**; the Mix slider appears only for Blend and is stored on
each generated Curve. Every value reuses the same outward ribbon, normal, and
Tilt logic, so placement never reverses the hair profile.

## Randy Rig: Limb IK

1. Make the intended source Armature active in Object or Pose Mode, open the
   **Rig** page, and click **Analyze Rig**. Choose Left/Right Arm or Leg in the
   dropdown, then review or correct that limb's Upper, Lower, and End fields.
   Set **Pole Direction (Local)** with XYZ, or use **Default Direction** to
   restore that selected chain's modeled rest bend. If the rest chain is too
   straight to define a plane, the fallback is arm-behind (`-Y`) or
   knee-forward (`+Y`) for a character facing `+Y`.
2. Click **Build IK** to create only the limb selected in the dropdown, or
   **Build All** to complete every populated Arm and Leg together in one atomic
   Undo step. The lower deform bone receives a no-stretch two-bone IK constraint;
   the hand or foot receives owned target rotation. A partly filled mapping
   cancels Build All before any generated data is written.
3. Move the whole character with `CTRL_master`. Pose limbs with
   `CTRL_hand_IK.*`, `CTRL_foot_IK.*`, `CTRL_elbow_pole.*`, and
   `CTRL_knee_pole.*`; rotate `CTRL_heel_roll.*` for the first-pass heel/bank
   pivot. The visible guide line and arrow update automatically with each Pole.
4. Change a direction and use **Rebuild Rig** to apply it to exactly the sides
   already generated, or to transactionally upgrade an owned 0.25 rig. The
   upper/lower pair deliberately re-planes to the chosen Pole while its End and
   unrelated source bones remain protected. Use **Remove Generated Rig** to restore the exact source
   rig. Removal remains available even if the Master was scaled non-uniformly,
   although Build/Rebuild require finite positive uniform scale.

Analyze is read-only. Build, Remove, and Rebuild are Undoable.
Generated controls never deform the Mesh, and exact ownership prevents the
cleanup tools from deleting artist-authored rig parts. If a generated control
is referenced by animation, a Driver, a foreign constraint, or a foreign child
bone, removal is refused.

Limb IK improves posing and joint aim; it does not by itself preserve shoulder
volume. Shoulder thinning at high arm elevation still calls for weight work and
later clavicle/scapular or corrective deformation helpers.

## Weight Tools

**Auto Weight Selected Bones** repairs the currently selected, visible Deform
bones. With the default Full Auto Blend it temporarily solves all eligible
current-rig Deform bones together; strict mode solves only the selection:

1. Select one already bound Mesh together with its Armature. In Pose Mode or
   Armature Edit Mode, select the exact bones to recalculate. The same button
   also works while the bound Mesh is already in Weight Paint Mode.
2. Open **Character Designer > Weight Tools** and click
   **Auto Weight Selected Bones**. Keep **Full Auto Blend (Normalized)** enabled
   for the healthy default: all current-rig Deform bones compete in Bone Heat,
   then only the selected bones' repaired local region is written back. The Mesh
   must have one unambiguous existing Armature modifier; the tool never creates,
   removes, or reorders modifiers and never changes parenting.
3. Existing target groups are replaced and a missing selected-bone group is
   created. A locked target group is refused until the artist unlocks it.

The complete Vertex Group state is snapshotted before the native solver runs.
In Full Auto Blend, unlocked Deform groups may be rewritten only inside the
selected groups' old/new influence union; non-Deform groups, locked groups, and
all membership outside that union stay exact, except that invalid generated-side
base weights on a supported half Mesh are cleared as described below. In strict
mode, every group not named after a selected Deform bone stays exact everywhere.
Mesh X Mirror is temporarily disabled, while face/vertex paint masks are temporarily disabled so
the calculation covers the complete base Mesh. All three flags are restored in
`finally`. Any protected-state change, native cancellation, unusable selected
result, or Python failure restores the complete original Vertex Group state
before returning.

The UI starts with **Full Auto Blend (Normalized)** enabled. It does not use a
single isolated bone as the heat source: all editable current-rig Deform bones
participate, so the selected result is the same spatial field it would receive
inside a complete Automatic Weights calculation. Only vertices influenced by
the selected groups before or after that solve are replaced. At each such
vertex, locked Deform weights first reserve their exact share. Selected solver
values then receive first claim on the available budget; the full solver's other
unlocked Deform values are scaled into the remainder. Consequently an unlocked
weight-1 core stays at 1, while a locked reservation can reduce the selected
value. Utility, mask, foreign, and non-Deform groups stay exact. “Normalized”
means that affected Deform totals equal one; this command does not run an
additional topology Smooth pass. The spatial transition comes from the complete
Bone Heat solver's local proportions. If the locked budget exceeds one, leaves
no room for the selected result, or the full solve has no support for a required
repair, the whole operation rolls back. One Undo removes the complete result
(including new groups), and one Redo restores it.

Turning the checkbox off retains the historical strict mode for scripts and
special cases: Blender recalculates only the selected groups and every other
group is verified byte-for-byte unchanged. That isolated solve is not a full-rig
weight column and can reach distant geometry when no neighboring bones compete,
so it is not recommended for ordinary character binding. Strict mode does not
normalize the combined Deform column; its final per-vertex total may exceed one.

For a true half Mesh that relies on a Mirror modifier's Vertex Group mirroring,
only source-side and center bones can own meaningful base-mesh weights. A bone
located solely on the generated side is refused with a normal warning; select
its source-side counterpart instead. Blender requires both `.L`/`.R` group
definitions before the Mirror modifier can flip evaluated membership, but only
the source-side group should own base vertices. Strict mode adds a missing empty
pair. Full Auto Blend clears every generated-side Deform group on the base Mesh,
including stale weights unrelated to the selected pair, then verifies that all
of those groups remain empty. The supported stack has one
object-local, X-only Mirror with **Vertex Groups** enabled before Armature;
Subdivision may be before or after that Mirror. The tool refuses ambiguous
Mirror stacks and shared Mesh data rather than claiming success when an opposite
bone could not independently deform its side.

## Weight Flow

**Weight Flow** creates a controlled transition without using Blender's global
Normalize or touching unrelated weights:

1. Keep the bound Mesh in Weight Paint Mode and enable **Vertex Selection
   Mask**. Select one or more complete non-branching chains, closed loops, or
   surface regions. A surface region needs a fixed outer boundary and at least
   one interior vertex row.
2. Select exactly two visible Deform Pose bones. Both matching Vertex Groups
   must already exist and be unlocked; make either one the active Vertex Group
   so Blender can display its Preview colors.
3. Open **Character Designer > Weight Flow** and click **Preview Weight Flow**.
   Adjust **Profile** and **Strength**. A surface region also exposes
   **Iterations**. Every slider change is recomputed from the captured original
   weights rather than from the previous Preview.
4. Press OK to apply or Esc to restore. Confirmed output is one Undo/Redo step.

For each selected vertex, the sum originally owned by the two participating
groups is treated as a fixed budget. Weight Flow only changes how that budget is
split between them. Other groups—including locked artist groups—retain their
exact definition, sparse membership, float weights, order, and lock state. The
two participating groups are likewise unchanged outside the vertex selection.
The tool does not alter parenting, object selection, the Armature or other
modifiers, Mirror/Subdivision settings, Mesh data, or any bone Deform flag.
Zero-budget vertices, branching selections, missing/locked participant groups,
closed surfaces without a boundary, and shared Mesh data are refused before any
Preview write.

## Spline IK Setup

**Spline IK Setup** builds the repetitive Curve, Hook-controller, and
constraint wiring for a flexible strap or other connected bone chain. It does
not create or edit deform bones, vertex groups, weights, or meshes.

1. In Armature Edit Mode or Pose Mode, select the exact continuous span the
   Curve should cover. Selecting the full chain produces a Curve from the
   captured root Head to the captured tip Tail; leaving rigid end bones
   unselected produces a flexible middle-only span.
2. Click **Capture Selected Chain**. The selection must be one unbranched,
   gap-free parent-to-child path with at least two bones.
3. Set **Curve Points** (default 5) and **Control Size Ratio** (default 6% of
   the chain's local length), then click **Build Spline IK Setup**. A stored
   capture can be built directly from Object Mode even when another object is
   active.
4. Click **Select & Reveal Controls** to select and frame every controller,
   enable Viewport Extras, and reveal the active middle controller in the
   Outliner. Move the generated spherical middle controls to bend the Curve. Move or
   rotate either cube end control to position the end and steer its Bezier
   tangent. Every controller exposes a Curve/strap-aware local frame: X follows
   strap width, Y follows the exact hooked Bezier tangent, and Z follows the
   evaluated strap-front normal. Rotate local Y to drive the matching Curve
   point's Tilt 1:1. The same Y-first rotation channel is distributed smoothly
   across the captured chain as incremental bone Roll, so a weighted non-round
   strap visibly twists instead of only changing Curve metadata. Local X/Z can
   be combined to steer the Curve without leaking into Tilt.

New setups include **Rotation Tilt** automatically. An older valid setup exposes
one contextual action: **Enable Rotation Tilt** when the drivers are absent, or
**Align Rotation Tilt Axes** when its saved v1/Swing drivers still use the old
frame. A fully enabled older setup shows the same contextual action once as
**Clean Hook Names**. Version 0.14.1 keeps the generated rig UUID exclusively
inside ownership metadata; visible modifiers use `CD Spline IK Hook 01`, `02`,
and so on. Existing UUID-bearing modifiers are renamed in place without
replacing their pointers, bindings, animation paths, or evaluated Curve. All
three paths work in place. They derive width/front from the evaluated
deform-bone frame, align the visible Empty axes, and use the Curve's actual
evaluated four-sided profile direction rather than the loose-edge Mesh `normal`
(which is only a tangent). The missing-driver path rebases Curve Tilt so a
zeroed controller represents the authored strap front. The v1 path freezes the
current evaluated Tilt and bone Roll into the new zero point, then converts the
same FCurves to isolated YXZ targets. Hook inverse compensation preserves the
Curve and evaluated bone pose while the controls change orientation. The small
profile probe exists only during evaluation and is removed immediately; no
persistent helper object or dependency cycle is added. Local axes are shown on
the controls. Artist bone constraints, unrelated animation, and the existing
X/Z Curve shape remain unchanged.

An invalid recapture never replaces the last valid chain. It reports a neutral
warning that the previous capture was kept. Routine mode/selection preconditions
also remain non-red; red status is reserved for a failed data transaction or
damaged generated setup, and every status message has a dismiss button.

The Curve and controls are created in Armature-local space and parented to the
Armature, so the complete setup follows its object transform. Every Bezier
point, including its two handles, is bound to its corresponding wire Empty by
one Hook modifier. Controls are independent after creation; no symmetry is
forced, so an initially symmetric chain may be adjusted symmetrically or
asymmetrically.

The Spline IK constraint is placed on the selected tip bone with its Chain
Length equal to the captured bone count. Y Scale and XZ Scale are both `None`,
Curve Radius, Even Divisions, and Chain Offset are disabled, and the constraint
is unmuted. This strictly prevents the Spline IK solver from introducing bone
scale. Consequently, if an artist later makes the Curve longer than the fixed
bone chain, the tip cannot both remain unscaled and reach the Curve endpoint.

Generated data carries an exact versioned internal UUID; it is not exposed in
artist-facing Hook modifier names. Rebuilding or **Remove Generated** only
removes a matching Character Designer setup. A foreign Spline
IK on the selected tip blocks Build by default; **Replace Existing Spline IK**
must be enabled explicitly, replaces only one unambiguous constraint, and never
deletes its target Curve.

If the generated Curve Object itself has artist Action, Driver, or NLA data,
**Remove Generated** stops before deleting anything and reports a normal
warning. This avoids pretending to recover Object animation that Blender's
manual Curve-object removal backup cannot reproduce losslessly.

## Generic Reference View Sets

The **Reference Views** panel creates spatial image references for any subject:
a prop, vehicle, building, room, creature, or character. It does not assume a
human height or anatomy. Codex Console (or another tool) writes a set beneath
`//References/CDesigner/<set>/reference-views.json`; **Scan Standard Folder**
finds those manifests and **Create / Update Views** synchronizes the selected
set.

The version-1 contract is:

```json
{
  "schema": "blackunity.cdesigner.reference-view-set",
  "version": 1,
  "setId": "2ed7799e-5b80-41da-a8cf-502aa32d09db",
  "name": "Any Subject",
  "updatedAt": "2026-08-04T08:00:00Z",
  "units": "METERS",
  "placement": {
    "origin": [0.0, 0.0, 0.0],
    "displaySizeMeters": 2.0,
    "distanceMeters": 10.0,
    "opacity": 0.35,
    "showInFront": true
  },
  "views": {
    "front": {
      "file": "front.png",
      "enabled": true,
      "flipHorizontal": false,
      "flipVertical": false,
      "distanceMeters": null,
      "displaySizeMeters": null,
      "opacity": null
    }
  }
}
```

`null` per-view values inherit `placement`. Image paths use drive-free POSIX
relative syntax and are rejected for backslashes, `.`/`..` components, or any
real-path escape from the manifest folder. Unknown fields are ignored
for forward-compatible producers, while schema, version, UUID, units, numeric
ranges, booleans, and enabled image files are validated before the Scene is
changed. Meter values are divided by `Scene.unit_settings.scale_length` to get
Blender Units.

Project-local loaded Images are stored with Blender `//` paths so moving the
saved `.blend` together with its `References` directory keeps links portable;
images outside the `.blend` directory retain absolute paths.
When Blender opens a Temp recovery file such as `quit.blend` or an autosave,
Character Designer detects only its exactly tagged managed Images whose `//`
path is now missing and reconnects them from the validated absolute source path
stored with the view. Existing valid paths, packed Images, and user Images are
left untouched. Version 0.7.3 defers this current-file check until add-on
registration has left Blender's restricted-data context, so both normal enable
and **Refresh Add-on** can complete safely.

An unused direction may be omitted or use `"file": null`. A null file is always
an unconfigured slot—even if an older producer accidentally leaves
`"enabled": true`—so a partial Front-only set remains usable. When a previously
created direction becomes empty or disabled, synchronization hides its managed
Empty but does not delete it; only **Clear Current Set** performs deletion.

Each Scene receives one tagged `C Designer References` collection. Every set
has a tagged root Empty and up to six tagged Image Empties. The image planes are
single-sided toward the subject so opposite views do not overlap; all remain
non-rendering. Synchronization leaves Edit Mode, the active object, and the
selection untouched. A failure rolls back new data and restores already managed
objects. **Clear Current Set** never claims same-named user data and retains a
managed object if another Scene or an unowned child depends on it.
Synchronization and visibility changes are refused before mutation when their
managed collection or objects are shared by multiple Scenes, preventing one
Scene's operation from silently changing another Scene.
Standard-folder discovery also refuses symlink, Junction, and other Windows
reparse-point directories, and rechecks every traversed directory and manifest
against the real `//References/CDesigner` boundary.

The WindowManager controls are intentionally session-only, but managed Scene
objects are persistent. On reopen, **Managed Scene Sets** reconstructs available
sets from exact current-version tags. A single set is adopted automatically;
multiple sets require an explicit UUID-backed dropdown choice before Show,
Hide, or Clear becomes available. This recovery does not require the original
manifest to still exist.

## Delta Symmetry

**Delta Symmetry** links the two topological sides of an asymmetric mesh
without forcing their absolute positions to become mirror images. It reflects
only the movement delta: an X-axis local delta `(dx, dy, dz)` becomes
`(-dx, dy, dz)` on the paired vertex, while both vertices keep their existing
different baselines.

1. Edit one Mesh and select either one continuous, non-branching center edge
   chain/loop, or two adjacent center-band boundary chains. For a center band,
   both boundaries must have matching open/closed structure and edge count;
   every boundary edge must have one band face and one outer face.
2. Choose **Local** or **World** and the reflection axis, then click **Set
   Symmetry**. The topology is detected automatically; there is no mode switch.
3. Enable **Auto Select Opposite** in Vertex Select mode. Selecting or
   deselecting a paired vertex immediately applies the same selection state to
   its partner while keeping the vertex you clicked active. To clear a linked
   pair, Shift-deselect its active/source vertex or use `Alt+A`.
4. Enable **Mirror Movement** and use normal Blender transforms. It remembers
   which side you selected first, so multi-vertex transforms still use the
   intended side as the driver.

Pairing is propagated face-by-face from the chosen centerline or center band.
With a band, its two boundary rows become the first vertex pairs, then pairing
grows outward. On an even-column closed tube, the two directions may meet at a
topologically proven opposite self-mapped face, so selecting only the front
band boundaries is sufficient. The tool supports matching quad, triangle, and
n-gon topology and never substitutes a nearest spatial vertex when topology is
ambiguous. Side labels are assigned to whole topological components, not sorted
independently for every pair.

Mirror Movement currently supports one edited Mesh at a time. While it is on,
Character Designer temporarily disables Blender's native Mesh Mirror axes and
restores their exact previous state when the feature turns off, the add-on is
refreshed, or the file is saved. Auto Merge and Proportional Editing remain
untouched; if either conflicts with the workflow, Mirror Movement simply turns
itself off. Leaving the paired mesh, changing topology, or leaving Vertex
Select mode likewise turns the relevant toggle off without a persistent red
error. Native modal translation with Auto Select Opposite has been verified as
one Undo/Redo step, and Esc restores both sides. The pair map is deliberately
session-only and must be rebuilt after an add-on reload or Blender restart.

## Hair Centerline

Character Designer turns selected hair cross-sections into an exact, shaped
center curve with one visible action and one compact placement selector:

1. In Mesh Edit Mode, select the complete connected strip that should define
   the centerline.
2. Choose **Centered**, **Surface**, or **Blend**. Centered preserves the
   original section centers and allows the Half profile to protrude; Surface
   keeps the evaluated visible front flush with the source mesh. Blend reveals
   a **Mix** slider: 0 is Centered, 1 is Surface, and the full range is usable.
3. Click **Generate / Update Centerline**. If the current scene already has a
   Character Designer Curve with the same source-layer record, that exact Curve
   is updated in place. A new Curve is created only when the source has no
   generated Curve in the current scene; a related but nonmatching or ambiguous
   target stops with a normal informational message and creates nothing.
4. With a generated Curve active in Object Mode, the same control reads
   **Refresh Centerline**, re-reads its recorded source layers, and preserves
   that Curve's saved placement and Mix.

Generation uses the selected placement mode; Object Mode refresh uses the
Curve's saved placement. **Blend** first solves the complete Centered and
Surface endpoints, then interpolates every Curve point by Mix and recomputes
Tilt from the resulting Curve's own tangent; raw Tilt values are never averaged.
The dominant-ribbon front direction is shared by every value, so changing Mix
cannot turn the Half profile into the head. Old fixed-Blend Curves without a
stored Mix read as exactly 0.5. The legacy preview, alignment, and explicit-target
operators remain registered for file and shortcut compatibility but are no
longer exposed as separate panel buttons.

Open rows, closed profile loops, and a collapsed `POINT` tip are supported. The
selection parser is independent of Blender's vertex/edge/face selection mode.
For example, four selected triangular profile loops plus one pointed tip are
read as `3 → 3 → 3 → 3 → 1` and create five center points; selected side faces
are never mistaken for one large root cap.

Each valid topological layer contributes one preview point at the arithmetic
mean of that layer's current vertices. The points stay in source-object local
space and the source transform is copied to the confirmed Curve, preserving
the original placement and local precision.

The confirmed Curve is immediately usable as a hair profile. It uses a
**Round** bevel with **Half** fill. The widest source cross-section sets the
default Depth, while every control point receives a proportional Radius. A
collapsed `POINT` endpoint keeps 1.5% of its nearest non-`POINT` loop's Radius:
visually pointed at normal scale, but still nonzero when inspected closely.

For a closed four-sided strand, width comes from the longest real boundary
edge rather than a diagonal vertex chord. Four-point rectangles and rounded
rectangles with more vertices both identify their two dominant longitudinal
face ribbons. The outward ribbon is chosen once for the full strip from
cumulative surface area and the direction opposite centerline curvature, with
the source-origin radial test retained only as a fallback. This prevents a
single noisy segment or reversed polygon winding from flipping the profile into
the head. Point Tilt aligns the Half-round bulge to that outward normal and is
unwrapped continuously along Blender's Minimum-twist frame.

Closed profiles without a dominant opposite face pair keep their complete
tangent-plane span, so a smooth regular 8- or 10-sided profile is not reduced to
one polygon edge. Open rows likewise use their complete end-to-end span. The
one-action workflow does not modify the source mesh or its selection. In-place
updates retain the Curve object, its materials, collections, and identity.

### Recover Applied Curve

When hair was previously converted or applied to a Mesh, select its complete
regular surface band in Mesh Edit Mode and click **Recover Applied Curve**. You
may select several disconnected strands at once. For a clean quad strand, a
single unbranched longitudinal edge path is also enough; its endpoints define
the recovered range and Character Designer expands it across the complete
cross-sections without changing the visible selection.

Each connected strand becomes one independent Curve Object. Choose **Bezier**
for a smaller, smoother editing cage: its **Control Points** slider is bounded
to 3–32 and defaults to 5. The endpoints stay exact, while interior position,
Radius, and continuously unwrapped Tilt are interpolated uniformly by source
arc length. Explicit **Aligned** Bezier handles keep the reduced cage smooth,
stable, and directly editable without relying on Blender's Auto-handle solver.
Choose **Exact** when geometric fidelity matters more than control count; it
keeps one Poly point for every recovered source cross-section. Changing the
mode or point count and repeating the action updates the same Curve Object.
Use the slider—not manual point deletion—to change the managed cage size.
Moving points or handles is normal Curve editing, but running Recover again
rebuilds the cage from the selected source Mesh and therefore replaces those
manual Curve edits. A manually added/deleted control point is treated as an
unreadable managed output and is refused rather than guessed over.

Point Radius keeps Alt+S meaningful, and point Tilt restores roll around the
local path. Common applied hair profiles are reconstructed without helper
objects:

- Round + Half with Extrude;
- Round + Full capsule profiles;
- rectangular Full profiles using Curve's embedded Profile data.

For Half profiles, the open endpoints identify the applied axis. Character
Designer also solves an equivalent Curve Offset when the section planes provide
enough evidence; otherwise the equivalent position stays in the recovered
control points with Offset zero. Mesh geometry cannot uniquely reveal the
historical split between Offset, control-point position, and some profile
parameters, so Exact mode promises equivalent editable geometry rather than the
original hidden parameter history. An applied Mesh cannot recover deleted
historical Bezier handles; Bezier mode creates a new explicit Aligned-handle
cage and is intentionally a smooth approximation when its point count is
reduced. A strand whose width/depth ratio changes along its length is refused
instead of being silently approximated by Radius alone.

**Recovery Preview** draws the current result directly in the viewport using
the GPU. Curve type, control-point count, and output changes update it
immediately, so the cage can be judged before recovery is confirmed. Preview
never deletes the source Mesh and never creates a temporary Object or datablock.
Turning preview off, confirming recovery, or refreshing the add-on clears all
preview drawing state. If the source has a compatible Mirror/Subdivision stack,
Preview also names the original-order stack that the Curve will retain.

The **Output** choice controls source ownership:

- **Add** is the default. It keeps the source Mesh Object and creates or updates
  the matching recovered Curve Object.
- **Replace Mesh** is destructive only after every strand in the complete source
  Mesh has passed preflight and the entire Curve batch has succeeded. It then
  removes the source Object, but does not delete its Mesh datablock; shared Mesh
  data therefore remains available to other Objects.

Replace Mesh refuses a partial source selection rather than deleting unselected
geometry. Mirror and Subdivision Surface are transferred in original stack
order, so ordinary combinations of either modifier no longer block Replace.
Other modifier types are refused. Sources with parent/child relationships,
constraints, animation or drivers, shape keys, links to multiple scenes, or
other ownership that cannot be transferred safely are still refused.
Replacement is a single Undo transaction, and any failure before source removal
leaves the source Object intact. A managed recovery output may update its copied
stack, but an extra or reordered artist modifier is never silently deleted.

In Add mode, recovery objects keep the exact source Mesh identity plus a
direction-independent source-layer signature. Renaming a source or reusing its
former name cannot send an update to the wrong Curve. The same component
updates its existing Curve Object; another component from the same Mesh creates
its own Curve and can later be refreshed independently. Replace outputs retain
their provenance metadata after the source Object is removed. The whole
selection is preflighted before any write, and creation/update is all-or-nothing
across the batch.

## Source Metadata

The confirmed Curve keeps lossless, versioned source metadata behind the
automatic profile. For every layer it records:

- the raw maximum vertex-to-vertex chord and the vertex pair that defines it;
- the maximum profile span used as the cross-section sizing reference;
- the longest real boundary edge and its vertex pair;
- the final shaping width, front normal, width axis, source face, and
  orientation source;
- the local center, the exact front-surface target and how it was found, the
  tangent, legacy width axis, and raw mesh normal.

The metadata is stored in `SOURCE_OBJECT_LOCAL` space together with the source
matrix at confirmation time. Metadata v4 added the Centered and Front Surface
solutions; v5 refreshes the front semantics with continuous dominant-ribbon and
curvature evidence. Valid v2, v3, and v4 Curve metadata remains readable and is
safely upgraded from its recorded source by the one-action workflow.
`profile_tip_radius` stores a ratio applied to the nearest non-`POINT` layer
Radius, not a global Radius. `shape_span_local` uses the longest boundary edge
only for a four-sided `CLOSED` layer; every other non-point layer keeps its full
tangent-plane profile span.

## Refresh Add-on

Character Designer watches its installed Python files. **Refresh Add-on** is
hidden while the loaded code matches disk and appears only when source changed,
a refresh is running, or an error needs attention. Refresh validates the Python
files and then reloads only the add-on modules; it neither saves nor reloads the
current `.blend`, so unsaved modeling remains in Blender memory without a save
prompt. Successful reload establishes the new source signature and the button
disappears. Session-only live preview and Delta Symmetry capture are stopped
safely as part of unloading the old runtime.

## Workspace Filter Guard

Character Designer preserves Blender's per-workspace add-on filtering. In each
workspace where filtering is enabled, it only ensures that Character Designer
and the owner required by the current render engine are present. For Cycles,
that owner is `cycles`, which keeps Material Slots, Preview, and Surface
available in Material Properties. Existing allow-list entries are never removed
and filtering is never disabled. The guard runs after registration and continues
to cover project loads, add-on refreshes, workspace changes, and render-engine
changes.
