"""Source only. Execute solely in the separately authorized final artist-save scope.
Root must verify the completed owned Pose backup and native readback first.
This fragment sets Pose's intended fake-user retention flag; it does not save X.
"""
import bpy
import json
import os
from pathlib import Path

assert os.getpid() == 27676
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
pose = bpy.data.actions.get('Pose')
assert pose is not None and pose.library is None and pose.name == 'Pose'
assert 'character_designer_pose_asset_v1' in pose
before = {'fake_user': pose.use_fake_user, 'users': pose.users}
pose.use_fake_user = True
assert pose.use_fake_user is True
print(json.dumps({'schema': 'x.validation.original-Pose-final-save-retention/1',
    'before': before, 'after': {'fake_user': pose.use_fake_user, 'users': pose.users},
    'artist_saved_by_this_fragment': False, 'required_next_step': 'Authorized artist save and actual save-success/readback verification.'}))
