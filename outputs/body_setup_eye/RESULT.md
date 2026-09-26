# Body Setup finger overlay default — 0.61.64

Generate/Update Body Setup now turns off the existing Capture Detection eye after the full rig transaction succeeds. References, loop marks and bend previews follow the existing eye semantics. Saved guide and Mark data, and rig custom shapes, are retained. Failed preflight, generation or transaction recovery leaves visibility unchanged. Users can reopen the eye manually; its state is saved with the blend file.

Canonical change: `D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\body_setup.py`.

Validation: all 10 cases in `tests/test_body_setup_blender.py` passed in Blender 5.2. Coverage includes first generation, reuse/update, save/reopen, preflight rejection, late generation failure and update rollback. See `tests.log`.

Built `character_designer-0.61.64.zip`. Deployed to the Blender 5.2 user add-ons directory and X's validation copy. `deploy_local.py --module character_designer --project-addons D:\Blender\Projects\Character\X\addons --check` verified 104 files in each target, with zero differences.

The running X window was refreshed using Character Designer's built-in Refresh Add-on. The refresh button cleared and the Fingers panel returned normally. This refresh did not generate a rig or save X.blend. The temporary test Blender exited normally; only the original X instance remained.

Changes are local and uncommitted; nothing was pushed. Existing unrelated working-tree changes were retained.
