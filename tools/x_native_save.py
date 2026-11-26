"""Let Blender rotate the current Windows X scene while Git is reading it."""

import ctypes
from ctypes import wintypes as win
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import time
import uuid

import bpy
from bpy.app.handlers import persistent


TARGET = Path(r"D:\Blender\Projects\Character\X\X.blend")
WAIT_SECONDS = 8.0
_active = None

if os.name == "nt":
    _win = ctypes.WinDLL("kernel32", use_last_error=True)

    def _bind(name, result_type, *argument_types):
        fn = getattr(_win, name)
        fn.restype = result_type
        fn.argtypes = argument_types
        return fn

    _open = _bind("CreateFileW", win.HANDLE, win.LPCWSTR, win.DWORD, win.DWORD,
                  win.LPVOID, win.DWORD, win.DWORD, win.HANDLE)
    _close = _bind("CloseHandle", win.BOOL, win.HANDLE)
    _mutex = _bind("CreateMutexW", win.HANDLE, win.LPVOID, win.BOOL, win.LPCWSTR)
    _wait = _bind("WaitForSingleObject", win.DWORD, win.HANDLE, win.DWORD)
    _release = _bind("ReleaseMutex", win.BOOL, win.HANDLE)
    _set_info = _bind("SetFileInformationByHandle", win.BOOL, win.HANDLE, ctypes.c_int,
                      win.LPVOID, win.DWORD)
    _invalid = ctypes.c_void_p(-1).value


def _set_versions(value):
    preferences = bpy.context.preferences
    dirty = preferences.is_dirty
    preferences.filepaths.save_version = value
    if preferences.is_dirty != dirty:
        preferences.is_dirty = dirty


def _wait_for_readers(path):
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        # DELETE access excludes new readers that don't share delete, but
        # FILE_SHARE_READ | WRITE | DELETE still allows Blender to rename X.
        handle = _open(str(path), 0x10000, 7, None, 3, 0, None)
        if handle != _invalid:
            return handle
        error = ctypes.get_last_error()
        if error != 32 or time.monotonic() >= deadline:
            raise ctypes.WinError(error)
        time.sleep(0.035)


def _remove_matching(path, identity):
    # Hold the name against rename while comparing it, then dispose of that
    # open file. A newly arrived backup must never be removed by path alone.
    handle = _open(str(path), 0x10000, 1, None, 3, 0, None)
    if handle == _invalid:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not os.path.samestat(path.stat(), identity):
            raise RuntimeError(f"Another file now occupies {path}")
        delete = ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO.DeleteFile
        if not _set_info(handle, 4, ctypes.byref(delete), ctypes.sizeof(delete)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        _close(handle)


class _Save:
    def __init__(self, path):
        self.path = path
        self.lock = ExitStack()
        self.guard = ExitStack()
        self.original = None
        self.prior = None
        self.temporary_version = False
        self.nested = 0

    def prepare(self):
        # One pair of native callbacks per file across participating Blenders.
        key = hashlib.sha256(os.fsencode(os.path.normcase(self.path))).hexdigest()
        mutex = _mutex(None, False, "Local\\BlenderXSave-" + key)
        if not mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        self.lock.callback(_close, mutex)
        # Blender does not permit save_pre callbacks to cancel a native save.
        # An actual simultaneous writer must finish before either can reuse @.
        while (state := _wait(mutex, 30_000)) == 0x102:
            print("[X save] Waiting for another Blender to finish writing this file.")
        if state not in (0, 0x80):  # acquired / abandoned
            raise ctypes.WinError(ctypes.get_last_error())
        self.lock.callback(_release, mutex)

        handle = _wait_for_readers(self.path)
        self.guard.callback(_close, handle)
        prefs = bpy.context.preferences.filepaths
        if prefs.save_version:
            return
        original = self.path.stat()
        backup = Path(str(self.path) + "1")
        if backup.exists():
            prior = backup.with_name(f".{self.path.stem}-previous-backup-{uuid.uuid4().hex}.blend")
            os.link(backup, prior)
            self.prior = prior
        # Native MoveFileEx can rename an open source, but cannot replace an
        # open destination. Rotation moves our guarded X out of the way first.
        _set_versions(1)
        self.temporary_version = True
        self.original = original

    def finish(self, success):
        try:
            self.guard.close()
            if self.temporary_version and bpy.context.preferences.filepaths.save_version == 1:
                _set_versions(0)
            backup = Path(str(self.path) + "1")
            if self.prior and backup.exists() and backup.samefile(self.prior):
                self.prior.unlink()  # Rotation did not consume the older backup.
                return
            if self.original is None or not success:
                return  # Keep every recovery file from an interrupted rotation.
            _remove_matching(backup, self.original)
            if self.prior:
                self.prior.rename(backup)  # Windows refuses to overwrite a new file.
        finally:
            self.lock.close()


def _same_target(filepath):
    return bool(filepath and os.path.normcase(os.path.abspath(filepath))
                == os.path.normcase(str(TARGET)))


@persistent
def _before(filepath, *_args):
    global _active
    if os.name != "nt" or not _same_target(filepath) or not _same_target(bpy.data.filepath):
        return
    if _active:
        _active.nested += 1
        return
    _active = _Save(TARGET)
    try:
        _active.prepare()
    except Exception as exc:
        # Blender save_pre handlers cannot veto a save. Release the guard so
        # the normal writer can proceed using its own fallback and reporting.
        _active.guard.close()
        print(f"[X save] Native save will proceed without the file guard: {exc}")


def _finish(filepath, success):
    global _active
    if not _active or not _same_target(filepath):
        return
    if _active.nested:
        _active.nested -= 1
        return
    transaction, _active = _active, None
    try:
        transaction.finish(success)
    except Exception as exc:
        print(f"[X save] Retained backup or recovery files: {exc}")


@persistent
def _after(filepath, *_args):
    _finish(filepath, True)


@persistent
def _failed(filepath, *_args):
    _finish(filepath, False)


def _callbacks():
    handlers = bpy.app.handlers
    return ((handlers.save_pre, _before), (handlers.save_post, _after),
            (handlers.save_post_fail, _failed))


def register():
    if os.name == "nt":
        for handlers, callback in _callbacks():
            if callback not in handlers:
                handlers.append(callback)


def unregister():
    global _active
    if os.name == "nt":
        for handlers, callback in _callbacks():
            if callback in handlers:
                handlers.remove(callback)
        if _active:
            transaction, _active = _active, None
            transaction.finish(False)
