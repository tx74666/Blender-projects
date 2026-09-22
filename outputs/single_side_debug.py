import sys, traceback
sys.path[:0] = [r'D:\MyRepository\Blender-addons-by-Randy\tests']
import test_finger_single_side_blender as t
from character_designer import finger_preview_cache as cache
from unittest.mock import patch
old = cache.clear
def clear():
    print('CLEAR_CACHE', len(cache._entries), flush=True)
    traceback.print_stack(limit=7)
    old()
t.character_designer.register()
with patch.object(cache, 'clear', clear):
    t.test_side_switch_preserves_selection_parameters_and_warm_frames()
