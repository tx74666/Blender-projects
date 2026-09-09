import sys
sys.path.insert(0,r'D:\Blender\Projects\Character\X\tests')
import test_hair_bones_variants_blender as t
t.test_standalone_and_repeated_hidden_source(); print('STANDALONE PASS')
t.test_native_reopen(); print('REOPEN PASS')
