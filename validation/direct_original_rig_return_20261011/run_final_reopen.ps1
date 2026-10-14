$env:BLENDER_USER_DATAFILES='D:\Blender\Projects\Character\X\validation\dr24cache'
& 'D:\Blender5.2\blender.exe' --background --factory-startup --threads 1 --python 'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011\verify_final_saved_artist.py' *> 'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011\artist_final_reopen.log'
$taskFinalExit=$LASTEXITCODE
Get-Content -LiteralPath 'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011\artist_final_reopen.log' -Tail 6
exit $taskFinalExit
