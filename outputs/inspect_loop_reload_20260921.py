import bpy, json, sys
from pathlib import Path
import character_designer as addon
lines = [line.body for line in bpy.context.space_data.scrollback]
classes = []
for cls in addon.CLASSES:
    base = next((base for base in cls.__mro__[1:] if hasattr(base, 'bl_rna_get_subclass_py')), None)
    actual = base.bl_rna_get_subclass_py(cls.__name__) if base else None
    classes.append(dict(name=cls.__name__, matches=actual is cls, actual=repr(actual), module=cls.__module__))
report = dict(version=addon.bl_info['version'], file=addon.__file__,
              enabled=getattr(addon, '__addon_enabled__', None),
              error=getattr(addon, 'ADDON_REFRESH_LAST_ERROR', None), classes=classes, console=lines[-1000:])
Path('D:/Blender/Projects/Character/X/outputs/loop_reload_diagnostics_20260921.json').write_text(json.dumps(report, indent=2))
print('RELOAD_DIAGNOSTIC_CAPTURED')
