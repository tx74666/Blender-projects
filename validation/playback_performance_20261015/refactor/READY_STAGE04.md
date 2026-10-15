Stage04 is sealed for the readonly Image Empty fix. Stage03/v3/Smoke003 and all
their original reports remain protected. The v3 actor run found the unsupported
Image copy path; its failed cleanup remains recorded, and its worker exited.

Source manifest SHA256:
`477f104ef7a0dc96994f7d287df38a2c5786cf9f726df4c93b45576dd3153a38`.
193 package files copied exactly, 161 Python files sealed, 9 authoring AST
functions matched `.41`. Scene builder SHA
`8e0ff44b3623037baa760a228d71a1d6797912971d85a542c18c4e4848e259f1`.
Fixture manifest SHA `95b7d3164337323667539add74a025f9f152be229106c0fef78e937aff14117c`.
Receipt SHA `60cce6d50382dc788e2cbd5c511bbcc7a8a324158b2eaf82c0cfafe105bc79f3`.

New v4 runner SHA
`1eee3fdb64a940773f512a110d9e8b786541530250e04ead60dd110c91647696`;
Smoke004 SHA `551fbd7d2d8a33ba56e6191280d717f4f4c491ec691e11e1c22ea29dc88765f0`.
The shared-image exception requires exactly EMPTY plus Image, identical Image
data, and no Image entry in the owned ID map. All other object data remains
independently owned. Generic Action checks use optional animation_data access.

Root executes serially:

1. Factory Smoke004 with Stage04, unused `native_scene_smoke_report_004.json`.
   The generated Image Empty object must be private while the original Image
   remains shared; there must be no copied Image. The smoke owns and cleans its
   generated Image explicitly by native UID after ordinary graph cleanup.
2. v4 with `--admission-only`, the same fixed private saved input, Stage04, and
   unused `native_frozen_admission_report_004.json`. Only the saved current frame
   is tested through golden capture, complete clone, core prepare/evaluate,
   exact output/source guard and cleanup. It sets
   `admission_current_frame_exact=true` only on success,
   `all_30_complete_outputs_exact=false`, and performs no ABBA timing. Source
   and target component scopes are included for diagnosis.
3. Only after actual admission passes, v4 without that flag, Stage04 and unused
   `native_frozen_report_004.json`, for all 30 frames and ABBA blocks.

Commands otherwise follow Stage03's CLI. All new scripts compile. This agent
did not invoke Blender, touch the GUI, open/save the artist or deploy anything.
No preparation, smoke or admission result establishes GUI FPS or full clip
equivalence. Existing bone scripts import their historical v2 helpers and need
a separate reviewed update if their later graph includes readonly Image data.
