# Private bone/Bake decision criteria, recorded before native bone validation

The user's target is normal full-character playback at the Scene's 30 FPS.
The authoring model remains editable, and artist shoe topology/weights are not
part of this refactor. A private playback artifact is the first usable boundary.
No bone or Bake native validation has passed as of this document's creation.

Exact gates remain mandatory: original topology, UV/material/stored attributes,
foreign Shape Keys and effective masks, original bone Rest/pose/channels, all
unconverted mesh output, source catalog and foreign-object protection, disk
pins, handler ownership and cleanup. Only the declared helper bones/groups,
raw lower/hand transfers, copied nondeform masks and dormant managed keys may
differ. Every helper must pass the existing fixed 2e-6 native matrix oracle.
Every repeated output must reproduce its own candidate hashes.

The paired formula is algebraically equivalent to the desired deformation,
but uses a different float32 route from inverse Shape Key correction. Exact
coordinate/normal hashes are reported honestly, even when numerical errors are
small. The following bounds are an initial engineering screen, not automatic
adoption and not a statement of exact equivalence:

- Converted mesh maximum position-vector error / source bounding-box diagonal
  <= 1e-6, RMS fraction <= 2e-7, with finite nonzero source scale unless exact.
- Maximum normal-vector error <= 5e-5 and RMS <= 1e-5, unitless, separately for
  vertex, polygon and corner normals.
- Cover every integer frame 1-30 in the actual saved clip and all prepared
  synthetic rest/twist/swing/combined cases at subdivision levels 0 and 1.

The position maximum is one millionth of actor size (about 0.001 pixel for a
1000-pixel actor). These are conservative practical screens for float32 path
differences, not physical-unit claims. A failed screen requires investigation;
the runner must retain failures rather than silently raise limits.

Live-helper equivalence must precede helper-only Bake. Bake must preserve the
copied Action's existing curves/layers/slots/drivers and all source content,
then replay forward, reverse, jumps and loop boundaries with native Action
evaluation only: no manual helper writes or corrective solver calls. Reopen the
result independently and repeat the full integer-frame geometry/matrix checks
with normal add-on lifecycle. Subframes, other clips and physical simulation
are unproven until separately tested.

Background ABBA is diagnostic evidence only. Final performance acceptance is
measured complete-character viewport playback under comparable shading and
shared-load conditions; no reciprocal of background milliseconds is reported
as GUI FPS. A smaller speed gain is not relabeled as the 30 FPS objective.

Model/effort: current task gpt-6.1-sol / ultra. Source-only, no deployment,
artist operations, scene save, native worker or Git publication in this step.
