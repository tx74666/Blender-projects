# Character Designer: Save Pose and synchronized application

Draft, 2026-10-07. Deployment and live-character validation are pending.

Save Pose creates one local Action asset in Current File. Selecting a native limb bone or its corresponding public Body control resolves to the same complete native limb region. Selected Region and All Body are available; Include Fingers is optional.

Capture records the evaluated native pose, including the visible IK result, rather than dormant native input values. The asset stores complete native transforms, supported B-Bone channels, its authoring native Rest, and diagnostic control modes. Capture preserves the artist's assigned Action, keys, mode, selection, pose, and active Original session.

Applying the asset restores the native target pose and matches the current control graph, including dormant controls, so editing and later IK/FK switches can continue from the restored pose. Application preserves the current IK/FK or Original mode when the saved pose is representable. Native Rest provenance validates compatible control rebuilds; incompatible native skeleton changes are rejected.

This feature supports validated Character Designer Body setups. Hair, Dress, foreign controllers, and generated mechanism selections are outside the supported capture scope. Unsupported constraints or drivers, non-finite transforms, and transforms requiring shear or singular scale are rejected without creating a partial asset.

## Validation status

- Capture integration: 15 tests passed.
- Activation integration: 13 tests passed.
- Mirror integration: 9 tests passed.
- Weights integration: two errors remain to be repaired.
- Keymap checks: pending.
- Actual Cosha character validation: pending.
- Release build, local deployment, deployment checks, runtime refresh, and artist-file save: pending.

The passed tests cover isolated Blender fixtures. They do not yet establish Asset Browser interaction or live Cosha behavior.
