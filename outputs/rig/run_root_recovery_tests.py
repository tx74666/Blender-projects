import sys
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\tests')
import test_root_control_blender as t
for test in (t.test_build_and_remove_rollback,t.test_dependencies_uniform_scale_and_reopen,t.test_existing_enhanced_master_reused):
 test(); print('PASS',test.__name__,flush=True)
