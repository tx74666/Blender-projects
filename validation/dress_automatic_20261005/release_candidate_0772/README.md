# Unapproved Dress release skeleton

This directory is not deployable and has not been built, installed, or run in Blender. The runtime version remains 0.77.1. The skeleton retains the current canonical ACTUAL_SURFACE_DELTA_V1 selection rather than making Direct the public default. The approved Pose0.77.1 baseline used implicit LEGACY_CAGE, so the copied Dress modules do introduce a Legacy-to-Delta route change relative to that baseline.

The approved installed 0.77.1 baseline is retained except for ten exact current canonical Dress modules and mesh_copy.py, required by the retained Delta constructors. release_projection.json records the exact before/after file map and excluded pending modules. baseline_release_projection.json is historical baseline evidence, not candidate deployment approval.

The four model/animation export host/worker modules are still byte-identical to the approved baseline. Standalone canonical Direct-only export rejection gates have not been prepared or extracted; this is an explicit release blocker. Complete pending Delta export/snapshot and animation/worklist changes are excluded.

No version bump, public Direct default, native acceptance, build, deployment, or export approval is claimed. release_projection_pre_review.json preserves the original metadata before this baseline/current-canonical comparison was clarified; all runtime bytes are unchanged.
