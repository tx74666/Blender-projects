# Hair export / managed Worklist Rest

2026-10-15. Current task: repair the reported Hair connection/ordered-parent
export refusal, then continue the requested playback work. Source changes are
in the shared add-on repository. The artist currently has unsaved work; the
saved X.blend identity alone does not establish current scene contents.

The source diagnosis identifies a mismatch between an adopted Worklist
translation copy (which intentionally clears mapped native connection flags)
and Hair's authored connection proof. The candidate authenticates the existing
Worklist Rest view and projects only the connection flag. Live geometry,
matrices, ownership, parents, groups, and exact registry comparisons remain.
This is a source-level diagnosis until observed against the current artist.

Candidate version: 0.77.43, not yet released/deployed/refreshed/saved. Only
`hair_strand_registry.py` and the package version belong to this repair. The
four unreleased playback modules are excluded from its release projection.

Prepared native tests: canonical `tests/test_hair_worklist_rest_blender.py`.
They must run in an isolated background factory process during the next
available serial window; they never open or save the artist file.

Playback receipt 009 completed in the previous stopped run and remains
immutable. Its strict admission and 57 dependency pins were rechecked using
Blender's bundled Python without launching Blender. It proves its older
SaveCopy010 / 6fd snapshot, not the current model or GUI FPS. New artist saves
invalidate its direct current-artist pin; preserve that evidence and acquire a
new snapshot for the changed model instead of editing old pins.

No Git stage/commit/push. No current task worker, Unity operation, GUI input,
deployment, or artist save has run yet. Model / reasoning effort for this new
task are unrecorded; inherited old task metadata is not fresh verification.
