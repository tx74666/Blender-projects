"""Run one owned, isolated Blender probe with read-only Windows resource sampling."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import time

class MemoryStatus(ctypes.Structure):
    _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [(name, ctypes.c_ulonglong) for name in ('totalPhysical', 'availablePhysical', 'totalPageFile', 'availablePageFile', 'totalVirtual', 'availableVirtual', 'availableExtendedVirtual')]

class CounterUnion(ctypes.Union):
    _fields_ = [('doubleValue', ctypes.c_double), ('longValue', wintypes.LONG), ('largeValue', ctypes.c_longlong)]

class CounterValue(ctypes.Structure):
    _fields_ = [('status', wintypes.DWORD), ('value', CounterUnion)]

class ProcessMemory(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('pageFaultCount', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in ('peakWorkingSet', 'workingSet', 'peakPagedPool', 'pagedPool', 'peakNonpagedPool', 'nonpagedPool', 'pageFileUsage', 'peakPageFileUsage', 'privateUsage')]

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
psapi = ctypes.WinDLL('psapi', use_last_error=True)
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemory), wintypes.DWORD]

class Counters:
    def __init__(self):
        self.library = ctypes.WinDLL('pdh')
        self.library.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(wintypes.HANDLE)]
        self.library.PdhAddEnglishCounterW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(wintypes.HANDLE)]
        self.library.PdhCollectQueryData.argtypes = [wintypes.HANDLE]
        self.library.PdhGetFormattedCounterValue.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(CounterValue)]
        self.library.PdhCloseQuery.argtypes = [wintypes.HANDLE]
        self.query = wintypes.HANDLE()
        self.error = self.library.PdhOpenQueryW(None, 0, ctypes.byref(self.query))
        self.items = {}
        if not self.error:
            for name, path in {'pagesInputPerSec': r'\Memory\Pages Input/sec', 'pagesOutputPerSec': r'\Memory\Pages Output/sec', 'pageReadsPerSec': r'\Memory\Page Reads/sec', 'systemCpuPercent': r'\Processor(_Total)\% Processor Time', 'diskReadBytesPerSec': r'\PhysicalDisk(_Total)\Disk Read Bytes/sec', 'diskWriteBytesPerSec': r'\PhysicalDisk(_Total)\Disk Write Bytes/sec'}.items():
                handle = wintypes.HANDLE()
                status = self.library.PdhAddEnglishCounterW(self.query, path, 0, ctypes.byref(handle))
                if not status:
                    self.items[name] = handle
            self.library.PdhCollectQueryData(self.query)

    def sample(self):
        result = {}
        if self.error:
            return {'pdhUnavailable': self.error}
        status = self.library.PdhCollectQueryData(self.query)
        if status:
            return {'pdhCollectError': status}
        for name, handle in self.items.items():
            value = CounterValue()
            status = self.library.PdhGetFormattedCounterValue(handle, 0x200, None, ctypes.byref(value))
            result[name] = round(value.value.doubleValue, 3) if not status and value.status in (0, 1) else None
        return result

    def close(self):
        if self.query:
            self.library.PdhCloseQuery(self.query)

def memory():
    value = MemoryStatus()
    value.length = ctypes.sizeof(value)
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'availableBytes': value.availablePhysical, 'totalBytes': value.totalPhysical, 'usedPercent': value.load}

def filetime(value):
    return ((value.dwHighDateTime << 32) | value.dwLowDateTime) / 10_000_000

def process_sample(pid):
    handle = kernel.OpenProcess(0x1000 | 0x0010, False, pid)
    if not handle:
        return {'pid': pid, 'unavailable': ctypes.get_last_error()}
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(item) for item in times)):
            return {'pid': pid, 'unavailable': ctypes.get_last_error()}
        result = {'pid': pid, 'cpuSeconds': filetime(times[2]) + filetime(times[3])}
        value = ProcessMemory()
        value.cb = ctypes.sizeof(value)
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(value), value.cb):
            result.update(workingSetBytes=value.workingSet, privateCommitBytes=value.privateUsage, pageFaultCount=value.pageFaultCount)
        return result
    finally:
        kernel.CloseHandle(handle)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--executable', required=True)
    parser.add_argument('--script', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--gui-pid', type=int, required=True)
    parser.add_argument('--samples', type=int, default=5)
    parser.add_argument('--mode', choices=('current', 'controls'), default='current')
    parser.add_argument('--cases', default='baseline,no_subsurf,no_forearm,no_subsurf_no_forearm')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    before = memory()
    if before['availableBytes'] < 200 * 1024 * 1024:
        raise RuntimeError('Less than 200 MiB available; no new Blender process started.')
    command = [args.executable, '--background', '--factory-startup', '--disable-autoexec', '--threads', '2', '--python-exit-code', '17', '--python', args.script, '--', '--input', args.input, '--output', str(output / 'benchmark.json'), '--repeats', str(args.samples), '--mode', args.mode, '--cases', args.cases]
    metadata = {'command': command, 'startedEpoch': time.time(), 'before': before, 'logicalCpus': os.cpu_count(), 'guiPid': args.gui_pid, 'limits': ['Saved independent scene copy; no GUI changes', 'Two worker threads; no GPU redraw or Undo timing', 'Process pageFaultCount includes soft and hard faults; system PDH page I/O is not Blender-specific']}
    counters = Counters()
    last = {}
    started = time.perf_counter()
    with (output / 'blender.log').open('w', encoding='utf-8') as log, (output / 'resources.jsonl').open('w', encoding='utf-8') as resources:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        metadata['ownedPid'] = child.pid
        print(json.dumps({'startedPid': child.pid, 'availableMiB': round(before['availableBytes'] / 1024**2), 'output': str(output)}), flush=True)
        try:
            while child.poll() is None:
                stamp = time.perf_counter()
                item = {'epoch': time.time(), 'elapsedSeconds': stamp - started, 'memory': memory(), 'counters': counters.sample(), 'processes': []}
                for pid in (args.gui_pid, child.pid):
                    proc = process_sample(pid)
                    old = last.get(pid)
                    if old and 'cpuSeconds' in proc and 'cpuSeconds' in old[1]:
                        duration = stamp - old[0]
                        proc['cpuCoreEquivalents'] = round((proc['cpuSeconds'] - old[1]['cpuSeconds']) / duration, 3)
                        if 'pageFaultCount' in old[1] and 'pageFaultCount' in proc:
                            proc['allPageFaultsPerSec'] = round((proc['pageFaultCount'] - old[1]['pageFaultCount']) / duration, 1)
                    last[pid] = (stamp, proc.copy())
                    item['processes'].append(proc)
                resources.write(json.dumps(item) + '\n')
                resources.flush()
                time.sleep(0.5)
            metadata.update(exitCode=child.returncode, elapsedSeconds=time.perf_counter()-started, endedEpoch=time.time(), after=memory())
        finally:
            counters.close()
    (output / 'run.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps({'exitCode': metadata['exitCode'], 'elapsedSeconds': round(metadata['elapsedSeconds'], 2)}), flush=True)
    if metadata['exitCode']:
        raise SystemExit(metadata['exitCode'])

if __name__ == '__main__':
    main()
