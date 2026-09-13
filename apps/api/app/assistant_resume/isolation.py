from __future__ import annotations

import os
import sys
import sysconfig
from pathlib import Path

MEMORY_BYTES = 256 * 1024 * 1024
_job_handles: list[int] = []


def limit_memory() -> bool:
    """Set an OS-enforced process limit before loading the PDF library."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class BasicLimits(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD),
                ]

            class IoCounters(ctypes.Structure):
                _fields_ = [
                    (name, ctypes.c_uint64)
                    for name in (
                        "ReadOperationCount",
                        "WriteOperationCount",
                        "OtherOperationCount",
                        "ReadTransferCount",
                        "WriteTransferCount",
                        "OtherTransferCount",
                    )
                ]

            class ExtendedLimits(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", BasicLimits),
                    ("IoInfo", IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t),
                ]

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            kernel.CreateJobObjectW.restype = wintypes.HANDLE
            kernel.SetInformationJobObject.argtypes = [
                wintypes.HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
            kernel.SetInformationJobObject.restype = wintypes.BOOL
            kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            kernel.AssignProcessToJobObject.restype = wintypes.BOOL
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.CreateJobObjectW(None, None)
            if not handle:
                return False
            limits = ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x100 | 0x8
            limits.BasicLimitInformation.ActiveProcessLimit = 1
            limits.ProcessMemoryLimit = MEMORY_BYTES
            if not kernel.SetInformationJobObject(
                handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ):
                kernel.CloseHandle(handle)
                return False
            if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
                kernel.CloseHandle(handle)
                return False
            _job_handles.append(handle)
            return True
        if os.name == "posix":
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
            return True
    except (OSError, ValueError, ImportError):
        return False
    return False


def restrict_io() -> None:
    """Permit library reads, but no application files, writes, sockets or databases."""
    roots = tuple(
        Path(sysconfig.get_path(key)).resolve() for key in ("stdlib", "purelib", "platlib")
    )

    def audit(event: str, args: tuple) -> None:
        if event.startswith(("socket.", "sqlite3.", "subprocess.")) or event in (
            "os.system",
            "os.exec",
            "os.posix_spawn",
        ):
            raise PermissionError("parser_io_denied")
        if event == "open":
            path, mode, flags = args
            if isinstance(path, int):
                return
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                raise PermissionError("parser_io_denied")
            resolved = Path(os.fsdecode(path)).resolve()
            if not any(resolved.is_relative_to(root) for root in roots):
                raise PermissionError("parser_io_denied")

    sys.addaudithook(audit)
