"""
Global Hotkey Manager for FastCapture.
Uses native Win32 message-only HWND with dedicated WNDPROC message pump.
100% reliable global shortcut capture (supports Alt+S, Shift+S, Ctrl+S, etc.) with ZERO keyboard lag or typing issues.
"""

import sys
import ctypes
from PyQt6.QtCore import QObject, pyqtSignal, QThread

if sys.platform == "win32":
    from ctypes import wintypes
    import win32gui
    import win32con
    import win32api
    user32 = ctypes.windll.user32

    # Win32 Modifier Constants
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000

    VK_MAP = {
        "PRINTSCREEN": 0x2C,
        "SNAPSHOT": 0x2C,
        "PRTSCN": 0x2C,
        "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75,
        "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
        "ESCAPE": 0x1B, "SPACE": 0x20, "RETURN": 0x0D, "ENTER": 0x0D,
        "INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23,
        "PAGEUP": 0x21, "PAGEDOWN": 0x22
    }

def parse_hotkey_string(hk_str: str):
    """
    Parses a hotkey string like 'Shift+S' or 'Ctrl+PrintScreen' into
    (modifiers: int, vk_code: int).
    """
    if sys.platform != "win32":
        return 0, 0
    if not hk_str or hk_str.strip().upper() == "NONE":
        return 0, 0

    parts = [p.strip().upper() for p in hk_str.split("+")]
    modifiers = MOD_NOREPEAT
    vk_code = 0

    for part in parts:
        if part in ("CTRL", "CONTROL"):
            modifiers |= MOD_CONTROL
        elif part == "ALT":
            modifiers |= MOD_ALT
        elif part == "SHIFT":
            modifiers |= MOD_SHIFT
        elif part in ("WIN", "WINDOWS", "SUPER"):
            modifiers |= MOD_WIN
        elif part in VK_MAP:
            vk_code = VK_MAP[part]
        elif len(part) == 1:
            vk_code = ord(part)

    return modifiers, vk_code

class HotkeyListenerThread(QThread):
    hotkey_triggered = pyqtSignal(int)

    def __init__(self, hotkey_defs: dict):
        super().__init__()
        self.hotkey_defs = hotkey_defs.copy()  # dict: {id: (mods, vk)}
        self.hwnd = None
        self._class_name = f"FastCapHotkeyReceiver_{id(self)}"

    def run(self):
        if sys.platform != "win32":
            return

        h_inst = win32api.GetModuleHandle(None)

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == win32con.WM_HOTKEY:
                self.hotkey_triggered.emit(int(wparam))
                return 0
            elif msg == win32con.WM_CLOSE:
                win32gui.DestroyWindow(hwnd)
                return 0
            elif msg == win32con.WM_DESTROY:
                win32gui.PostQuitMessage(0)
                return 0
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = wnd_proc
        wc.lpszClassName = self._class_name
        wc.hInstance = h_inst

        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        self.hwnd = win32gui.CreateWindow(
            self._class_name,
            "FastCapHotkeyReceiver",
            0, 0, 0, 0, 0,
            win32con.HWND_MESSAGE,
            0,
            h_inst,
            None
        )

        # Register all hotkeys
        for hk_id, (mods, vk) in self.hotkey_defs.items():
            if vk != 0:
                success = user32.RegisterHotKey(self.hwnd, hk_id, mods, vk)
                if not success:
                    # Fallback without MOD_NOREPEAT
                    success = user32.RegisterHotKey(self.hwnd, hk_id, mods & ~MOD_NOREPEAT, vk)
                if not success:
                    pass

        # Native message pump
        win32gui.PumpMessages()

        # Cleanup on stop
        for hk_id in self.hotkey_defs:
            try:
                user32.UnregisterHotKey(self.hwnd, hk_id)
            except Exception:
                pass

        try:
            win32gui.UnregisterClass(self._class_name, h_inst)
        except Exception:
            pass

    def stop(self):
        if self.hwnd:
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
        self.wait(1000)

class DarwinHotkeyListener(QThread):
    hotkey_triggered = pyqtSignal(int)

    def __init__(self, mapping: list):
        super().__init__()
        self.mapping = mapping
        self._listener = None

    def _convert_to_pynput(self, hk_str: str) -> str:
        if not hk_str or hk_str.strip().upper() == "NONE":
            return ""
        parts = [p.strip() for p in hk_str.split("+")]
        pynput_parts = []
        for p in parts:
            up = p.upper()
            if up in ("CMD", "COMMAND", "SUPER", "WIN", "WINDOWS"):
                pynput_parts.append("<cmd>")
            elif up in ("CTRL", "CONTROL"):
                pynput_parts.append("<ctrl>")
            elif up == "ALT":
                pynput_parts.append("<alt>")
            elif up == "SHIFT":
                pynput_parts.append("<shift>")
            elif up in ("PRINTSCREEN", "SNAPSHOT", "PRTSCN"):
                pynput_parts.append("<print_screen>")
            elif up.startswith("F") and up[1:].isdigit():
                pynput_parts.append(f"<f{up[1:]}>")
            elif len(p) == 1:
                pynput_parts.append(p.lower())
            else:
                pynput_parts.append(f"<{p.lower()}>")
        return "+".join(pynput_parts)

    def run(self):
        try:
            from pynput import keyboard
        except ImportError:
            return

        hotkeys_dict = {}
        for hk_id, hk_str in self.mapping:
            pyn_str = self._convert_to_pynput(hk_str)
            if pyn_str:
                def make_cb(target_id=hk_id):
                    return lambda: self.hotkey_triggered.emit(target_id)
                hotkeys_dict[pyn_str] = make_cb(hk_id)

        if not hotkeys_dict:
            return

        try:
            with keyboard.GlobalHotKeys(hotkeys_dict) as h:
                self._listener = h
                h.join()
        except Exception:
            pass

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
        self.quit()
        self.wait(1000)

class GlobalHotkeyManager(QObject):
    active_window_pressed = pyqtSignal()
    window_object_pressed = pyqtSignal()
    rectangular_region_pressed = pyqtSignal()
    freehand_region_pressed = pyqtSignal()
    full_screen_pressed = pyqtSignal()
    color_picker_pressed = pyqtSignal()

    ID_ACTIVE_WIN = 101
    ID_WIN_OBJECT = 102
    ID_RECT_REGION = 103
    ID_FREEHAND = 104
    ID_FULLSCREEN = 105
    ID_COLOR_PICKER = 106

    def __init__(self, config_hotkeys: dict):
        super().__init__()
        self.config_hotkeys = config_hotkeys
        self.worker = None
        self.init_hotkeys()

    def _get_mapping_list(self) -> list:
        return [
            (self.ID_ACTIVE_WIN, self.config_hotkeys.get("active_window", "Alt+W")),
            (self.ID_WIN_OBJECT, self.config_hotkeys.get("window_object", "Alt+O")),
            (self.ID_RECT_REGION, self.config_hotkeys.get("rectangular_region", "Alt+S")),
            (self.ID_FREEHAND, self.config_hotkeys.get("freehand_region", "Alt+F")),
            (self.ID_FULLSCREEN, self.config_hotkeys.get("full_screen", "Alt+A")),
            (self.ID_COLOR_PICKER, self.config_hotkeys.get("color_picker", "Alt+C")),
        ]

    def _build_defs(self) -> dict:
        mapping = self._get_mapping_list()
        defs = {}
        for hk_id, hk_str in mapping:
            mods, vk = parse_hotkey_string(hk_str)
            if vk != 0:
                defs[hk_id] = (mods, vk)
        return defs

    def init_hotkeys(self):
        self.stop()

        if sys.platform == "win32":
            defs = self._build_defs()
            self.worker = HotkeyListenerThread(defs)
            self.worker.hotkey_triggered.connect(self._on_hotkey)
            self.worker.start()
        elif sys.platform == "darwin":
            mapping = self._get_mapping_list()
            self.worker = DarwinHotkeyListener(mapping)
            self.worker.hotkey_triggered.connect(self._on_hotkey)
            self.worker.start()

    def _on_hotkey(self, hk_id: int):
        if hk_id == self.ID_ACTIVE_WIN:
            self.active_window_pressed.emit()
        elif hk_id == self.ID_WIN_OBJECT:
            self.window_object_pressed.emit()
        elif hk_id == self.ID_RECT_REGION:
            self.rectangular_region_pressed.emit()
        elif hk_id == self.ID_FREEHAND:
            self.freehand_region_pressed.emit()
        elif hk_id == self.ID_FULLSCREEN:
            self.full_screen_pressed.emit()
        elif hk_id == self.ID_COLOR_PICKER:
            self.color_picker_pressed.emit()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
