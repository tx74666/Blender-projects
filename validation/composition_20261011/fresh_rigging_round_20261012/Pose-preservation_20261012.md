# Original Pose preservation — 2026-10-12

The original live X.blend contained an unused local Pose Action with 360 scalar curves and 360 keys on 15 left finger bones. It was absent from the old saved 1C seed. The old 99B in-memory snapshot remains unchanged.

A standalone Action library was written from original PID27676 without saving X or changing the original Action flags, context, selection, current frame or content. Actual write report: `Pose-preservation_01/Pose_library_write_report.json` (6ac66dc320e88238075a243586cdb92b535da14cc4decf912886dedb912296d4).

Backup: `Pose-preservation_01/Pose.blend` (c956d715940c7a92ea19a85e26997498a7bda0b0d86a300a443ba507e0055dc6), 95,415 bytes. Independent empty-process readback listed only Pose and no other library IDs. Every layer, strip, channelbag, slot, curve, key and recorded property matched content hash acdd30eda498c058f9fea9a7a019ec11ffd355e7409b666e26cb98e69d225d3f. Direct opening of the owned backup verified its persisted fake-user flag. Default append cleared that flag in the temporary readback process; this does not describe the original or persisted backup flag.

Actual readback02 report: `Pose-preservation_02_readback/Pose_library_readback_report.json` (26123aaff8dd5a83e00611ae52ca1aa1e4bb30db69294b99dfb1f5a9d6391aa2). Retained-handle native exit0 at 10:46:09.6349849Z; no Kill. Release: `resource_release_X_POSE_PRESERVE_202610121046Z.json` (b8bdd7652db1fb4ad1c8ac796a52783482a5404a40c31299675e5f5d42afa3c3).

Original X was not saved. Its disk SHA remains 3cd5619d70e8b4e21c2483884a04d352a2405f0eab02f00d34d306c81c5aa4b0. Final authorized artist save must set the original Pose retention flag and verify the saved Action survives. Do not delete or replace the user Pose; do not claim the old ten-action seed included it.
