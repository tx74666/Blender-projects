# Pose Library menu restored

The current Modeling workspace had Filter Add-ons enabled without `pose_library` in its owner list. Blender therefore skipped the registered Pose Library menu callbacks. Live inspection confirmed the add-on was enabled and loaded, the selected Fist asset was an ACTION, and the object was in Pose Mode.

Added only `pose_library` to the Modeling workspace's owner list. Preserved all existing filtering entries. Restored the temporarily used console to the AnimeFront.png Image Editor in Paint mode.

Verified visually that the Fist context menu now contains enabled Apply Pose and Apply Pose Flipped commands. Left that menu open for the user's next action. Did not apply a pose.

This workspace setting is stored in X.blend, not user preferences. The current blend has not been saved by this repair; save X.blend normally to retain it across reopening. No add-on code or Blender installation files were changed.

Evidence: `pose_menu_inventory.json` and `pose_menu_repair.json` in this directory.
