import sys
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import addon_utils
m=addon_utils.enable('character_designer',default_set=False,persistent=True,refresh_handled=True)
assert m is not None
for i in range(2):
 m._reload_addon_deferred()
 m=sys.modules['character_designer']
 print('REFRESH_RESULT', i, m.ADDON_REFRESH_LAST_ERROR, m.__addon_enabled__)
 m._validate_registration_integrity()
 assert not m.ADDON_REFRESH_LAST_ERROR
addon_utils.disable('character_designer',default_set=False)
