"""Pinned one-shot installation after Console finishes its input update."""
import bpy
import hashlib
from pathlib import Path
import sys
import types

source = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\live_profiler_mesh_v3.py")
expected_sha256 = "878ea3f3af54738d116297e16ce7662e3cd6c291452198aea074004b01acce3e"
pending_name = "_x_playback_live_mesh_profiler_v3_install_pending_20261015"
helpers = ("_x_playback_live_profiler_20261014", "_x_playback_live_mesh_profiler_20261014",
           "_x_playback_live_mesh_profiler_v2_20261015", "_x_playback_live_mesh_profiler_v3_20261015")
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_sha256
assert pending_name not in sys.modules, "A v3 installation is already pending"
assert not any(name in sys.modules for name in helpers), "Close the existing profiler before installing v3"
window, screen, area = bpy.context.window, bpy.context.screen, bpy.context.area
assert window and screen and area and area.type == "CONSOLE"
pending = types.ModuleType(pending_name)
sys.modules[pending_name] = pending

def install():
    try:
        assert window.screen == screen, "Observed screen changed before deferred install"
        assert any(candidate == area for candidate in screen.areas), "Observed Console area disappeared"
        assert area.type == "CONSOLE", "Observed Console area changed before deferred install"
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected_sha256, "Profiler source changed before deferred install"
        with bpy.context.temp_override(window=window, screen=screen, area=area):
            exec(compile(raw.decode("utf-8-sig"), str(source), "exec"), {})
    finally:
        if sys.modules.get(pending_name) is pending:
            del sys.modules[pending_name]
    return None

pending.callback = install
try:
    bpy.app.timers.register(install, first_interval=0.25)
except BaseException:
    if sys.modules.get(pending_name) is pending:
        del sys.modules[pending_name]
    raise
