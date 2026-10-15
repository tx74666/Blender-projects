"""Queue the pinned final-save worker after Console finishes its input update.

The worker waits up to 90 seconds for the exact original Hair line as current
unexecuted native Console input. This installer never executes that line.
"""
import bpy
import hashlib
import os
from pathlib import Path
import sys
import types

source = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\final_save_07741.py")
expected_sha256 = "e3348a733000917c7d91fcf6d0683792e9a672e5503a71861439f983a5af9494"
source_name = "_x_final_save_07741_20261015_source"
helper_name = "_x_final_save_07741_20261015"
pending_name = helper_name + "_installer_pending"
assert os.getpid() == 24416 and not bpy.app.background
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_sha256
assert all(name not in sys.modules for name in (source_name, helper_name, pending_name))
window, screen, area, scene = bpy.context.window, bpy.context.screen, bpy.context.area, bpy.context.scene
assert window and screen and area and scene and area.type == "CONSOLE"
cd = sys.modules.get("character_designer")
assert cd is not None and tuple(cd.bl_info["version"]) == (0, 77, 41)
pending = types.ModuleType(pending_name)
sys.modules[pending_name] = pending

def install():
    module = None
    try:
        assert window.screen == screen and window.scene == scene
        assert area.type == "CONSOLE" and any(candidate == area for candidate in screen.areas)
        assert source_name not in sys.modules and helper_name not in sys.modules
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected_sha256, "Final-save source changed before deferred installation"
        module = types.ModuleType(source_name)
        module.__file__ = str(source)
        sys.modules[source_name] = module
        exec(compile(raw.decode("utf-8-sig"), str(source), "exec"), module.__dict__)
        with bpy.context.temp_override(window=window, screen=screen, area=area):
            pending.controller = module.begin(window, screen, area, scene)
        print("Final-save worker waiting for original Hair command as unexecuted Console input; do not press Return on that line.")
    except BaseException:
        if module is not None and sys.modules.get(source_name) is module and helper_name not in sys.modules:
            del sys.modules[source_name]
        raise
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
