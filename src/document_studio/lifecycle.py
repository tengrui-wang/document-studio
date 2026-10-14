"""Windows mutex shared with Inno Setup's stable AppMutex."""
import ctypes
import os
from . import APP_MUTEX


def create_app_mutex():
    if os.name != "nt":
        return None, False
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    ctypes.set_last_error(0)
    handle = kernel.CreateMutexW(None, False, APP_MUTEX)
    if not handle:
        raise RuntimeError("无法创建应用运行锁，请检查 Windows 会话权限。")
    return handle, ctypes.get_last_error() == 183
