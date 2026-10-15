"""Install after Console has completed its own input/history update."""
import bpy
import hashlib
from pathlib import Path

source = Path(r'D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\live_profiler_mesh_v2.py')
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'c362f4151a4bd45a5a1106631842cc875b7934d90b845e495e782b46949bd7a4'
window = bpy.context.window
area = bpy.context.area
assert window and area and area.type == 'CONSOLE'

def install():
    assert area.type == 'CONSOLE', 'Observed Console area changed before install'
    with bpy.context.temp_override(window=window, area=area):
        exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), {})
    return None

bpy.app.timers.register(install, first_interval=0.25)
