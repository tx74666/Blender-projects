"""Run only synthetic native Undo after an isolated GUI has initialized."""
import runpy
import traceback
from pathlib import Path

import bpy

root = Path(r'D:\MyRepository\Blender-addons-by-Randy')
output = Path(r'D:\Blender\Projects\Character\X\outputs\two_stage_20260921\native_undo_gui_result.txt')


def run():
    try:
        namespace = runpy.run_path(str(root / 'tests/test_finger_two_stage_blender.py'))
        namespace['character_designer'].register()
        namespace['test_native_operator_undo_restores_each_phase_and_allows_repositioning']()
        output.write_text('NATIVE_TWO_STAGE_UNDO_PASS\n', encoding='utf-8')
        print('NATIVE_TWO_STAGE_UNDO_PASS', flush=True)
    except BaseException:
        output.write_text(traceback.format_exc(), encoding='utf-8')
        traceback.print_exc()
    finally:
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(run, first_interval=2.0)
