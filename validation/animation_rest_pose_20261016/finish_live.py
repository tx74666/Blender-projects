"""Post-event-loop save confirmation and owned temporary bridge shutdown."""
import bpy
import hashlib
import json
import os
from pathlib import Path
import threading
import blender_mcp
import character_designer

folder = Path(r'D:\Blender\Projects\Character\X\validation\animation_rest_pose_20261016')
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert os.getpid() == 24416 and Path(bpy.data.filepath) == artist
rig = bpy.context.scene.character_designer_setup.rig
assert rig.name == 'CoshaRig' and rig.data.pose_position == 'REST'
assert bpy.context.mode == 'EDIT_MESH' and bpy.context.object.name == 'Shoes'
assert bpy.data.is_saved and not bpy.data.is_dirty
delivery = json.loads((folder / 'live_delivery.json').read_text(encoding='utf-8'))
assert hashlib.sha256(artist.read_bytes()).hexdigest() == delivery['artist_sha256']
servers = []
for thread in threading.enumerate():
    server = getattr(getattr(thread, '_target', None), '__self__', None)
    if (isinstance(server, blender_mcp.BlenderMCPServer)
            and server.host == '127.0.0.1' and server.port == 9877
            and server.server_thread is thread):
        servers.append(server)
assert len(servers) == 1
report = {'passed': True, 'pid': os.getpid(), 'version': character_designer.bl_info['version'],
          'is_saved': bpy.data.is_saved, 'is_dirty': bpy.data.is_dirty,
          'pose_position': rig.data.pose_position, 'mode': bpy.context.mode,
          'artist_sha256': delivery['artist_sha256'], 'temporary_bridge_shutdown_scheduled': True}
(folder / 'post_eventloop_save.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.app.timers.register(servers[0].stop, first_interval=.5)
print(json.dumps(report))
