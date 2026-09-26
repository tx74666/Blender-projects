import bpy
import ctypes
import json
from pathlib import Path
from datetime import datetime

def run_viewport_probe():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),
                  ('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),
                  ('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),
                  ('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),
                  ('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t),('PrivateUsage',ctypes.c_size_t)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
    psapi.GetProcessMemoryInfo.restype=ctypes.c_int
    def sample(label):
        value=Counters()
        value.cb=ctypes.sizeof(value)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'label':label,'time':datetime.now().isoformat(),'working_set':value.WorkingSetSize,'private_commit':value.PrivateUsage}
    areas=[(a,a.spaces.active.shading.type) for a in bpy.context.screen.areas if a.type=='VIEW_3D']
    result={'samples':[sample('original_material')],'original_modes':[mode for a,mode in areas]}
    for area,mode in areas:
        area.spaces.active.shading.type='SOLID'
    def restore():
        try:
            result['samples'].append(sample('solid_after_5s'))
        finally:
            for area,mode in areas:
                area.spaces.active.shading.type=mode
        bpy.app.timers.register(finish,first_interval=5.0)
    def finish():
        result['samples'].append(sample('restored_material_after_5s'))
        result['restored_modes']=[a.spaces.active.shading.type for a,mode in areas]
        result['unloaded_candidates']=[im.name for im in bpy.data.images if not im.has_data]
        (Path(r'D:\Blender\Projects\Character\X\outputs\memory_health')/'viewport_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print('VIEWPORT MEMORY PROBE COMPLETE; original shading restored.',result['samples'])
    bpy.app.timers.register(restore,first_interval=5.0)
    print('Viewport memory comparison running for 10 seconds; original shading will be restored automatically.')

run_viewport_probe()
