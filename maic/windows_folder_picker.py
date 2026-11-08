"""Native Windows folder picker with real multi-selection support."""

import sys


class FolderPickerError(OSError):
    """Raised when the Windows shell folder picker cannot be opened."""


def select_folders(title: str = "Select source folders") -> list[str]:
    """Return filesystem folders selected in one Windows shell dialog."""
    if sys.platform != "win32":
        raise FolderPickerError("Windows folder picker is only available on Windows")

    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    hresult = ctypes.c_long
    ole32 = ctypes.OleDLL("ole32")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    owner_window = user32.GetForegroundWindow()
    ole32.CLSIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(GUID)]
    ole32.CLSIDFromString.restype = hresult
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = hresult
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = hresult
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole32.CoTaskMemFree.restype = None

    def failed(result: int) -> bool:
        return result < 0

    def check(result: int, operation: str) -> None:
        if failed(result):
            unsigned = ctypes.c_uint32(result).value
            raise FolderPickerError(f"{operation} failed with HRESULT 0x{unsigned:08X}")

    def guid(value: str) -> GUID:
        result = GUID()
        check(ole32.CLSIDFromString(value, ctypes.byref(result)), "CLSIDFromString")
        return result

    def method(interface, index: int, result_type, *argument_types):
        vtable = ctypes.cast(
            interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
        ).contents
        prototype = ctypes.WINFUNCTYPE(
            result_type, ctypes.c_void_p, *argument_types
        )
        return prototype(vtable[index])

    def release(interface) -> None:
        if interface:
            method(interface, 2, wintypes.ULONG)(interface)

    clsid_file_open_dialog = guid("{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}")
    iid_file_open_dialog = guid("{D57C7288-D4AD-4768-BE02-9D969532D960}")

    # Flask serves the request on a worker thread, so it needs its own STA.
    initialized = False
    init_result = ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    if init_result in (0, 1):  # S_OK or S_FALSE
        initialized = True
    else:
        check(init_result, "CoInitializeEx")

    dialog = ctypes.c_void_p()
    try:
        check(
            ole32.CoCreateInstance(
                ctypes.byref(clsid_file_open_dialog),
                None,
                0x1,  # CLSCTX_INPROC_SERVER
                ctypes.byref(iid_file_open_dialog),
                ctypes.byref(dialog),
            ),
            "CoCreateInstance",
        )

        get_options = method(dialog, 10, hresult, ctypes.POINTER(wintypes.DWORD))
        set_options = method(dialog, 9, hresult, wintypes.DWORD)
        set_title = method(dialog, 17, hresult, wintypes.LPCWSTR)
        show = method(dialog, 3, hresult, wintypes.HWND)
        get_results = method(
            dialog, 27, hresult, ctypes.POINTER(ctypes.c_void_p)
        )

        options = wintypes.DWORD()
        check(get_options(dialog, ctypes.byref(options)), "IFileDialog.GetOptions")
        options.value |= 0x20 | 0x40 | 0x200 | 0x800
        # FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_ALLOWMULTISELECT |
        # FOS_PATHMUSTEXIST
        check(set_options(dialog, options), "IFileDialog.SetOptions")
        check(set_title(dialog, title), "IFileDialog.SetTitle")

        # The request originates from a browser click. Owning the picker with
        # that foreground window keeps the modal dialog above the browser.
        show_result = show(dialog, owner_window)
        if ctypes.c_uint32(show_result).value == 0x800704C7:  # User cancelled.
            return []
        check(show_result, "IFileDialog.Show")

        items = ctypes.c_void_p()
        check(get_results(dialog, ctypes.byref(items)), "IFileOpenDialog.GetResults")
        try:
            get_count = method(
                items, 7, hresult, ctypes.POINTER(wintypes.DWORD)
            )
            get_item_at = method(
                items,
                8,
                hresult,
                wintypes.DWORD,
                ctypes.POINTER(ctypes.c_void_p),
            )
            count = wintypes.DWORD()
            check(get_count(items, ctypes.byref(count)), "IShellItemArray.GetCount")

            paths: list[str] = []
            for index in range(count.value):
                item = ctypes.c_void_p()
                check(
                    get_item_at(items, index, ctypes.byref(item)),
                    "IShellItemArray.GetItemAt",
                )
                try:
                    get_display_name = method(
                        item,
                        5,
                        hresult,
                        ctypes.c_uint,
                        ctypes.POINTER(ctypes.c_void_p),
                    )
                    path_pointer = ctypes.c_void_p()
                    check(
                        get_display_name(item, 0x80058000, ctypes.byref(path_pointer)),
                        "IShellItem.GetDisplayName",
                    )
                    try:
                        paths.append(ctypes.wstring_at(path_pointer.value))
                    finally:
                        ole32.CoTaskMemFree(path_pointer)
                finally:
                    release(item)
            return paths
        finally:
            release(items)
    finally:
        release(dialog)
        if initialized:
            ole32.CoUninitialize()
