# Blender Projects

A shared place to exchange `.blend` files and move Blender projects forward together.

## Current Projects

- `X.blend`: Character X work-in-progress.

Open `X.blend` in Blender 5.1 or newer. The current file has the front and side reference images packed into the blend file so the scene opens with its modeling references intact.

Third-party/downloaded assets under `assets/` are not part of the first version commit unless intentionally added later.

## Character Designer add-on

The current add-on is **0.41.3**. **Weight Flow** has been removed; the **Weight**
page retains **Weight Tools** and **Weight Symmetry**. Use Blender's native tools
for local weight smoothing. The current workflow is documented in the
[add-on guide](addons/character_designer/README.md); the entries below describe
earlier releases.

Version 0.40.2 completes hair controls for Mirror sources: new versions include
both side chains and one chain for a strand joined along the center seam. The
original mesh and earlier versions stay intact. Hair3's seven source strands
produce 13 complete chains (52 hair bones at four per chain). Select an older
hair result and Generate New Version to rebuild with the complete controls.

Version 0.40.0 adds **Clothing > Skirt Setup**: automatic tapered cage fitting,
waist/mid/hem ring controls, skirt weights, a connected cloth simulation cage,
closed pelvis/thigh colliders, sequential physics baking, and an independent
baked animation copy. See the [add-on guide](addons/character_designer/README.md)
for the workflow and supported skirt topology.

**Hair > Hair Bones** now also supports **Per Strand** and **Grouped** modes.
Capture the strand boundaries, group or split members, optionally edit one
guide per group, and generate independent versions for comparison. Switching
versions preserves manually edited weights and animation; six selected strands
can be compared as 18 hair bones versus two shared chains with six hair bones.

The personal character-modeling add-on source lives in
`addons/character_designer`. Version 0.38.0 adds **Hair > Hair Bones**:
select long hair strands from joined mesh geometry, inspect the selection,
and generate native FK controls with local weights. Existing head rigs are
reused where identifiable, and welded roots stay anchored while individual
strands bend. The generated bones work after saving and reopening without
an add-on runtime. See the [add-on guide](addons/character_designer/README.md)
for the two-button workflow and supported selection rules.

Version 0.37.0 makes Forearm Twist symmetric by
default, with one test/calibration, enable switch and remove action for both
arms. Pose Mode Hand Targets open the same body calibration. Existing loop
shares automatically follow Build IK, Rebuild, Remove Generated, refresh,
Undo and file reload; no side selection or manual synchronization is needed.
Each hand keeps its own pose and each arm keeps its own weights. The hand's
Twist channel still turns the hand; the calibrated sleeve replaces its
original weighted axial rotation with the saved per-loop shares.

Version 0.35.0 adds **Rig > Forearm Twist
(Prototype)**: a 90° hand-turn test, highlighted forearm loops, saved per-loop
twist shares, and Confirm/Cancel with pose restoration. One managed corrective
Shape Key per side distributes circular twist through the existing skinning;
no bones, modifiers, or repainted weights are added. The bounded prototype
supports ordinary Armature-first LBS within ±120°, preserves existing relative
keys, and updates during playback/rendering with the add-on enabled. See the
[add-on guide](addons/character_designer/README.md) for supported inputs and use.

Version 0.34.2 fixes the **Auto Align** display
handoff for Hand and Foot Targets. When Auto changes the evaluated wrist/ankle
frame, the visible controller now receives that same complete transform delta
instead of being compensated back to its old world-space orientation. This
keeps fitted sole outlines attached to the rotated foot while leaving Target
Rotation, IK position, Rest bones, weights, and meshes untouched. Display
defaults are converted together with the active visual frame, so Reset Visual,
Manual/Auto round-trips, Rebuild, and artist offsets stay coherent. Existing
generated rigs should use **Rebuild Rig** once after refreshing the add-on.

Version 0.34.1 makes a Pole's connector follow its
**Control Visual** shape choice: choosing **Sphere Wire** removes the separate
joint-to-Pole line, while **Arrow** and **Rig Default** restore it. This applies
to both Direct Pre-Roll GPU guides and Stable VIS guides, without changing the
IK solve, control pose, or generated bone count.

Version 0.34.0 gives every generated Hand and Foot
IK Target an aligned, animator-readable Local XYZ rotation frame without adding
another control bone. X is Flex/Extend (Toe Up/Down for feet), Y is Twist/Bank,
and Z is Side/Wave (Turn for feet). These channels work in both Manual and
**Auto Align**: Auto keeps the solved Forearm/Shin orientation as the base and
adds the Target's local rotation afterward. A contextual **Target Rotation**
panel exposes the three channels and a rotation-only Reset; it does not reset
location, scale, Custom Shape adjustments, Rest bones, weights, or meshes.
No hard ankle clamp is imposed in this first version, so the animator retains
all three degrees of freedom. Existing generated rigs migrate transactionally
through **Rebuild Rig** and failure restores their prior graph exactly.

Version 0.33.0 makes each Direct Pole read as one
visual control: its live shaft now uses the same Blender bone/theme state as
the arrowhead, so both are black while idle and both highlight blue together.
The existing **Control Visual** panel also gains an active-control **Shape**
menu with Rig Default, Arrow, and Sphere Wire choices. Alternate shapes are
owned display widgets that survive Rebuild and are removed with the generated
rig; switching them never edits control transforms, constraints, Rest bones,
weights, or meshes.

Version 0.32.0 advances Direct Pre-Roll to schema
5. Each limb still exposes only the Target and Pole as visible, selectable
animator controls, while one hidden, non-selectable, non-Deform Pole
display-aim helper keeps the presentation aligned. In Pose Mode the GPU overlay
draws the real bend-joint-to-Pole shaft whenever the relevant viewport, bone,
and collection visibility allows it, whether or not the Pole is selected. The
existing `WGT_Randy_PoleArrow` remains the only pyramid/cone head and rotates
dynamically as the Pole moves, keeping its base perpendicular to the live
shaft; no duplicate arrowhead or persistent scene object is created.

**Auto Align** is one rig-wide toggle independent of the limb dropdown. One
switch applies atomically to every generated Arm and Leg. While enabled, every
Hand and Foot Target's visible custom-shape frame follows its own evaluated end;
the shoe-sole outline therefore follows the live Foot/Shin pitch and roll
instead of remaining visually flat. Returning to Manual first matches all
Targets to their live end orientations, then restores each Target's own display
frame without a visible pop.

Version 0.31.1 previously kept each Direct Pre-Roll Pole as one visual arrow:
the existing `WGT_Randy_PoleArrow` custom shape was the only arrowhead, while a
selected-only GPU overlay drew just the bend-joint-to-Pole shaft. That release
did not create a display-aim helper or persistent scene object.

Version 0.31.0 turns **Auto Align Target** into a
persistent Hand/Foot mode: while enabled, the end uses the limb's natural
solved orientation instead of Target rotation; disabling it first matches the
Target to that orientation and then returns to ordinary manual rotation without
a visible pop. Its state survives Rebuild, and a transition that would need to
overwrite protected animation or locked channels fails closed.

The new **Control Visual** panel adjusts only a generated animator
control's Custom Shape Offset, Rotation, and Scale, with a Reset action and
Rebuild preservation; IK, Rest bones, constraints, weights, and meshes remain
untouched.

Version 0.30.0 placed the shared finger-ring widgets on the actual source-bone
Heads (the bend joints).

Direct Foot controls are now separate left/right 64-point outlines fitted to
each visible shoe's sole, yaw, center, and medial big-toe side. Old shared Foot
widgets and midpoint finger displays upgrade transactionally through Rebuild,
with exact rollback on failure. Version 0.29.4 separates each generated Limb IK
solver from the deform-bone orientation. Hidden MCH upper/lower bones solve the
requested elbow or knee plane, while two independent ORI helpers transport the
artist-authored upper/lower cross-sections by their minimum swing. An arm can
therefore bend behind the character without rolling the elbow inset and outer
elbow tip through roughly 180 degrees. Hands and feet retain their independent
target rotation.

Existing schema-1/2 rigs upgrade transactionally through **Rebuild Rig**. The
upgrade removes the old direct-IK graph before reading the underlying artist
frames, so an old Pole-induced twist is not baked into the new ORI helpers.
Repeated schema-3 rebuilds preserve the current controls and pose without
drift, while changing or flipping a Pole direction recalibrates the MCH solver
from the clean source frame. Remove owns and cleans the added MCH/ORI bones and
constraints, and failure restores the prior rig exactly.

Version 0.29.3 makes repeated **Rebuild Rig**
idempotent for the short Edit Mode Pole-line helpers: every rebuild authors the
helper from the real Rest joint toward the newly-created Pole in one consistent
Armature-local coordinate space. This prevents a second rebuild from reversing
an arm helper while the actual IK plane remains correct. Version 0.29.2 restored the explicit anatomical
Limb IK defaults for Character Designer's Armature-local `-Y`-forward humanoid
convention: elbows use `+Y` behind the character and knees use `-Y` in front.
It no longer normalizes a tiny modeled rest residual into the default, which
had sent X's elbows forward and amplified its knees' lateral offset to about
91%. The real Pole, bend, and arrow remain aligned. Generated Pole bones stay
short and Keep Offset at the target; Edit Mode Pole-line helpers now also use a
short rest bone while their existing Stretch To constraint draws the complete
joint-to-Pole guide in Pose Mode. Existing generated Poles retain saved artist
directions and are never silently migrated. To adopt the corrected defaults,
Analyze, choose each built limb, press **Default Direction**, then use
**Rebuild Rig**.

Version 0.29.0 expands **Copy Weight to Opposite**
with same-side multi-bone selection in Pose Mode and Weight Paint. All selected
Deform-bone pairs are planned from one immutable Vertex Group snapshot and pass
one complete preflight before the first write. The whole batch commits as one
Undo step, or any invalid pair leaves every Vertex Group unchanged. The active
`.L`/`.R` Vertex Group remains the source for the original single-copy workflow
when there is no intentional multi-bone selection. Names must end in exactly
`.L` or `.R`; suffixes such as `.001` are never stripped or guessed.

Each directed source-to-counterpart copy keeps the source bone's real local-X
half untouched, replaces the opposite half in the paired group, and clears
wrong-side source/target memberships without rewriting unrelated Vertex Groups.
Exact spatial pairing, paired Deform bones, unlocked groups, single-user Mesh
data, and preserved per-vertex Deform totals are required; ambiguous inputs, or
any copy that would change those totals, fail before writing.

Version 0.27.0 upgrades **Randy Rig: Limb IK** with
a compact Left/Right Arm/Leg dropdown and one complete first-pass control set:
one `CTRL_master`, concave hand targets, dynamic elbow/knee Pole arrows, foot
outlines under the sole, and heel/bank controls backed by hidden solver targets.
**Build IK** creates only the dropdown limb, while **Build All** completes every
available arm and leg in one atomic Undo step. The Master rests at Armature-local
ground zero. Each dropdown limb exposes an Armature-local Pole Direction
XYZ plus one-click Default. The evaluated Blender solver aligns the real elbow/knee bend
to that explicit direction instead of silently following a shallow modeled
bend. A mathematically straight chain is refused with an actionable prompt to
add a small elbow/knee pre-bend; measurable near-straight limbs remain
supported. Exact schema ownership lets Rebuild transactionally
upgrade 0.25 controls and lets Remove restore the source rig; a moved Master is
neutralized during incremental Build/Rebuild so transforms are not baked twice.
The source hierarchy, Mesh, modifiers, Vertex Groups, and weights stay intact.
Translation, rotation, and uniform Master scale are supported; Build/Rebuild
fail closed on non-uniform scale. Finger widget geometry is prepared but no
finger bones are generated, and this compact heel pivot is not yet a complete
reverse-pivot ball/toe rig. Rain-inspired control-shape attribution is recorded
in [ATTRIBUTION.md](addons/character_designer/ATTRIBUTION.md).

Version 0.24.0 upgrades **Auto Weight Selected Bones** with **Full Auto Blend
(Normalized)**. All editable Deform bones compete
in one complete Automatic Weights solve, then only the selected bones' old/new
influence region is repaired: locked weights reserve their exact share, selected
solver values get first claim on the available budget, full-solver neighboring
bones fill the remainder, generated-side Mirror groups stay empty, and each
affected Deform total becomes one. With no locked reservation, a selected
full-weight core remains 1. This replaces the old
`1 + 1 -> 0.5 + 0.5` proportional behavior and cleans single-bone heat leakage
without touching non-Deform groups, locked weights, or outside vertices. On a
supported half Mesh, the one intentional exception is that all invalid
generated-side base weights are cleared so they cannot contaminate the solve. The
session-only UI checkbox defaults on and does not dirty `X.blend`; the direct
operator flag defaults false so omitted and explicit-false script calls retain
their strict-mode behavior. “Normalized” means sum-to-one; the transition uses
the full Bone Heat solver's local proportions and does not add a separate Smooth
pass. Version 0.22.0 adds an RR Helper-style page grid:
**Hair / Weight / Rig** and **Modeling / Reference**. Only the selected tool
family is shown, and the page choice is session-only so it never dirties the
`.blend`. Version 0.21.0 introduced **Weight Flow**, which was removed in
version 0.41.3. Version 0.19.0
preserves compatible Mirror and Subdivision Surface stacks when an applied Mesh
is recovered to Curve. The
original modifier order, Mirror settings, and Catmull-Clark/Simple levels stay
non-destructive on the output; Half and Full profiles both remain supported,
while any other modifier is safely refused before writing. Version 0.18.0 keeps RR Helper's unobtrusive
**Refresh Add-on** workflow: it appears only for changed Python source, reloads
without saving or reopening the current `.blend`, and disappears once current.
It also expands **Recover Applied Curve** with explicit Aligned Bezier handles,
a GPU-only parameter preview, and **Add** or atomic **Replace Mesh** output.
Replace removes only a fully recovered source Object and preserves its Mesh
datablock. Version 0.17.0 gives **Recover Applied Curve** a
default smooth Bezier cage with a bounded 3–32 **Control Points** slider
(default 5); **Exact** keeps one Poly point per source cross-section. Position,
Radius, and unwrapped Tilt are sampled by source arc length, and changing mode
or count updates the same output Object. Version 0.16.0 adds **Recover Applied Curve** for
turning selected applied-hair Mesh bands (or a simple longitudinal guide path)
back into editable Poly Curves. It restores per-point Radius and Tilt and
reconstructs compatible Half-Round/Full-Round/rectangle Extrude profiles without
helper objects. Multiple strands are transactional, matching strands update in
place, and the source Mesh selection remains untouched. Version 0.15.3 makes Centered, Surface, and Blend
operate immediately on the active generated Centerline in Object Mode or Curve
Edit Mode. Dragging Blend's 0–1 Mix moves and persists the current Curve without
leaving Edit Mode, changing point selection, replacing its data, or adding a
button. Version 0.15.2 originally added a save-first refresh guard; version
0.18.0 retains RR Helper's in-memory Python-module reload, which does
not save or reopen the current `.blend`. Version 0.15.1 orders the compact selector as
**Centered**, **Surface**, **Blend** and gives Blend a Curve-persistent 0–1 Mix
slider: 0 is the exact Centered endpoint and 1 is the exact Surface endpoint.
Every value retains the same curvature-aware outward ribbon and recomputes Tilt
from its own tangent, so changing Mix never reverses the hair profile. Object
Mode refresh preserves the Curve's saved placement and Mix. Version 0.14.1 removes internal rig UUIDs from
visible Hook modifier labels: new and upgraded rigs use readable names such as
`CD Spline IK Hook 01`, while exact UUID ownership remains in hidden registry
metadata. Legacy names migrate in place through the existing contextual rig
action, including transactional rollback and driver-path preservation. Version
0.14.0 gives every Spline IK control an
explicit strap-relative frame: local X is strap width, local Y is the exact
Bezier tangent and Twist channel, and local Z is the strap-front normal. A
Y-first driver contract keeps combined X/Z steering out of Tilt, while Y still
drives Curve Tilt and interpolated bone Roll 1:1. Existing Rotation-Tilt-missing
rigs and already-enabled v1/Swing rigs are aligned in place through one
contextual action. Hook compensation and zero-point migration preserve the
Curve, current Tilt, bone pose, and driver identities; the Curve's real
evaluated profile direction is used instead of loose-edge Mesh normals. No
persistent helper objects are added. Version 0.13.0 reduces Hair Centerline to one
contextual **Generate / Update Centerline** action, always keeps the generated
Half profile flush with the authored outer surface, and recognizes continuous
dominant face ribbons on rounded rectangular loops such as Hair2's eight-point
sections. Cumulative ribbon area and outward curvature decide the front before
the object-origin fallback, preventing the profile from turning into the head.
Version 0.12.0 makes every Spline IK sphere/cube
controller's physical Swing-Twist Y drive the corresponding Bezier point Tilt
and smoothly interpolated bone Roll, so weighted flat shoe straps visibly twist
without extra helper objects. New rigs are
ready immediately; older valid rigs expose an in-place **Enable Rotation Tilt**
upgrade that keeps the current controller pose, Curve Tilt, Hook behavior, and
Outliner clean. Version 0.11.0 adds optional **Align Front
Surface** placement for Hair Centerlines. It offsets every Curve point so the
front of its Round/Half profile is flush with the source front surface, while
**Reset Centered** restores the recorded cross-section centers. Existing Curve
objects can be updated in place either from a newly selected strip (including a
different point count) or from their recorded source layers; the object,
materials, mode, selection, and current alignment choice are retained. Metadata
v4 records both the center and exact front target and still reads v2/v3 output.
Version 0.10.0 turns confirmed Hair Centerlines
into immediately usable **Round / Half** profiles. A closed four-sided loop
uses its widest real boundary edge for Depth and Radius; other closed profiles
keep their full cross-section span. A collapsed tip stays at 1.5% of its
nearest real loop, and Tilt aligns the half-round bulge to the detected outward
broad face without 180-degree flips. Metadata v3 keeps the raw chord, boundary
edge, and final shaping frame while remaining able to read v2 outputs. Version
0.9.1 improves **Spline IK Setup**: the
captured chain may be built directly from Object Mode, the full Curve span is
shown explicitly as captured root Head to captured tip Tail, and **Select &
Reveal Controls** selects/frames all generated controls while locating the
active middle control in the Outliner. Invalid recapture keeps the last valid
chain with a dismissible non-red warning. Version 0.9.0 introduced the tool:
capture one
continuous selected Armature bone chain, choose the number of Curve controls
and their relative display size, then build a 3D Bezier Curve with one Hooked
wire controller per point. End controllers are cubes whose rotation steers the
Bezier tangent; interior controllers are spheres for bending. The generated
tip constraint uses strict no-stretch Y/XZ settings, does not use Curve Radius,
and does not modify bones, weights, or the deform mesh. Existing non-generated
Spline IK constraints are never replaced unless the visible opt-in is enabled,
and their old target Curve is retained.

Version 0.8.0 makes **Set Symmetry** automatically
accept either one manifold centerline or the two adjacent boundary chains of a
center band, including an even-column closed tube that meets safely again on
its opposite face. Version 0.7.3 makes the reference-image recovery check safe
during Blender's restricted add-on registration, restoring normal enable and
**Refresh Add-on** behavior. Version 0.7.2 keeps managed reference images
connected when a Temp `quit.blend` or autosave is opened, without changing a
valid artist-selected path or any unowned image. Version 0.7.1 introduced
topology-proven **Delta Symmetry**. After the two side groups are built, use
**Auto Select Opposite** to keep paired vertices selected and
**Mirror Movement** to reflect only Edit Mode movement deltas while preserving
the model's existing asymmetry. Native Mesh Mirror axes are suspended only
while Mirror Movement is active and restored exactly when it stops or before a
save. Incompatible editing states turn the toggle off without a persistent red
panel error. Modal G with automatic opposite selection, Undo, Redo, and Esc are
covered by an isolated Blender GUI test.

The add-on also provides a selection-driven live centerline preview toggle:
select a complete connected run of hair cross-sections and the preview updates
immediately as the mesh selection changes.
Confirming creates one shaped Poly curve point at each valid layer's arithmetic
center. It supports open hair strips, closed tubes, and a single-vertex endpoint
at either end while leaving the source mesh and Edit Mode selection untouched.
Each point preserves the source layer's exact maximum local chord, real boundary
width, and stable front frame as versioned Curve-object metadata while applying
the corresponding Radius and Tilt to a Round/Half bevel. Its N-panel also
includes a validated, timer-deferred **Refresh Add-on** workflow inspired by RR
Helper. Character Designer remains separate from RR Helper, which is dedicated
to the team's Blender/BlackUnity workflow.

The current-selection parser accepts open rows, closed profile loops, and a
single collapsed point tip. It derives one center point per topological layer in
vertex, edge, or face selection mode and confirms only after re-reading the live
selection, so selected side faces cannot be mistaken for one large cap.
The Refresh control follows RR Helper's behavior: it appears only when installed
Python source differs from the loaded version, then disappears after a
successful in-memory reload. It never saves or reloads the current `.blend`.

Version 0.7.0 keeps Blender's workspace add-on filtering enabled while ensuring
that Character Designer and the active render engine remain on each filtered
workspace's allow-list. In a Cycles scene this preserves Material Slots,
Preview, and Surface without exposing unrelated add-ons.

Version 0.6.0 also adds generic **Reference View Sets**. A versioned manifest
can describe any subject—not only a person—with optional Front, Back, Left,
Right, Top, and Bottom images. Character Designer scans
`//References/CDesigner/**/reference-views.json`, converts manifest meters to
the current Scene's Blender Units, and creates or updates tagged Image Empties
under a dedicated collection and set root. Repeated sync is idempotent; hiding
does not delete anything, and Clear Current Set only removes exclusively owned,
exactly tagged objects.
