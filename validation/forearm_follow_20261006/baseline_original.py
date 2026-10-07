"""Read-only isolated reference run against the frozen R8 runtime."""
import runpy
import sys
sys.path.insert(0, r'D:\Blender\Projects\Character\X\validation\animation_collection_20261005\candidate_source_r8\addons')
import character_designer
print('FROZEN_BASELINE', character_designer.__file__, flush=True)
runpy.run_path(r'D:\Blender\Projects\Character\X\Validation\forearm_follow_20261006\candidate_source\tests\test_forearm_original_mode_blender.py', run_name='__main__')
