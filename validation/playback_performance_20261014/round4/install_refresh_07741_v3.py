"""Explicit one-shot Console installer; waits for Console input to settle.

Run this file only after deployment/check of the pinned candidate and removal
of owned profilers. It performs no deployment or artist save. The worker keeps
the Console area unchanged, writes a unique receipt/SaveCopy, and fails closed.
"""
import bpy
import hashlib
import os
from pathlib import Path
import sys
import types

SOURCE = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\protected_refresh_07741_v3.py")
EXPECTED_SHA = "069fe18afcb46a11b6faf63dac3846281dde3c4c0fbc9da90d3c50f105a71eef"
PREFIX = "_x_protected_refresh_07741_v3_20261015"
PENDING = PREFIX + "_install_pending"
SOURCE_NAME = PREFIX + "_source"
assert os.getpid() == 24416, "Wrong original artist PID"
assert Path(bpy.data.filepath).resolve() == Path(r"D:\Blender\Projects\Character\X\X.blend").resolve(), "Wrong artist file"
assert not any(name.startswith("_x_playback") for name in sys.modules), "Close the owned profiler first"
assert not any(name.startswith(PREFIX) for name in sys.modules), "A protected refresh is already owned/pending"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA, "Protected refresh source changed"
window, screen, area, scene = bpy.context.window, bpy.context.screen, bpy.context.area, bpy.context.scene
assert window and screen and area and area.type == "CONSOLE", "Use the observed original Console area"
assert not screen.is_animation_playing, "Artist must be paused"
pending = types.ModuleType(PENDING)
sys.modules[PENDING] = pending


def install():
    try:
        assert window.screen == screen and window.scene == scene, "Owning screen/scene changed"
        assert any(item == area for item in screen.areas) and area.type == "CONSOLE", "Observed Console changed"
        assert not any(name.startswith("_x_playback") for name in sys.modules), "An owned profiler appeared"
        assert SOURCE_NAME not in sys.modules and PREFIX not in sys.modules, "Another refresh appeared"
        raw = SOURCE.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA, "Source changed before deferred execution"
        source = types.ModuleType(SOURCE_NAME)
        source.__file__ = str(SOURCE)
        sys.modules[SOURCE_NAME] = source
        try:
            # Execute exactly the pinned source bytes; never use a cached pyc.
            exec(compile(raw.decode("utf-8-sig"), str(SOURCE), "exec"), source.__dict__)
            with bpy.context.temp_override(window=window, screen=screen, area=area):
                pending.controller = source.begin(window, screen, area, scene)
        except BaseException:
            if PREFIX not in sys.modules:
                sys.modules.pop(SOURCE_NAME, None)
            raise
    finally:
        if sys.modules.get(PENDING) is pending:
            sys.modules.pop(PENDING, None)
    return None


pending.callback = install
try:
    bpy.app.timers.register(install, first_interval=0.25)
except BaseException:
    if sys.modules.get(PENDING) is pending:
        sys.modules.pop(PENDING, None)
    raise
