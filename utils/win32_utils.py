"""
Win32 API 工具 - 后台点击、窗口枚举
使用 SendMessage/PostMessage 实现不抢占前台焦点的点击
"""

import ctypes
import ctypes.wintypes
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Win32 常量
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MOUSEMOVE = 0x0200
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

# Win32 API
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int
    title: str
    class_name: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    pid: int = 0
    process_name: str = ""

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    def __str__(self):
        return f"[{self.hwnd:#010x}] {self.title} ({self.width}x{self.height})"


def _make_lparam(x: int, y: int) -> int:
    """将 x, y 坐标打包为 LPARAM"""
    return (y << 16) | (x & 0xFFFF)


def send_click(hwnd: int, x: int, y: int, button: str = 'left') -> bool:
    """
    向指定窗口发送后台点击消息
    坐标为相对于窗口客户区的坐标
    """
    try:
        lparam = _make_lparam(x, y)

        if button == 'left':
            down_msg = WM_LBUTTONDOWN
            up_msg = WM_LBUTTONUP
            wparam = MK_LBUTTON
        elif button == 'right':
            down_msg = WM_RBUTTONDOWN
            up_msg = WM_RBUTTONUP
            wparam = MK_RBUTTON
        else:
            return False

        # PostMessage 是异步的，不会阻塞
        user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        user32.PostMessageW(hwnd, down_msg, wparam, lparam)
        user32.PostMessageW(hwnd, up_msg, 0, lparam)
        return True
    except Exception:
        return False


def send_click_sync(hwnd: int, x: int, y: int, button: str = 'left') -> bool:
    """
    同步版本 - 使用 SendMessage（等待窗口处理完成）
    """
    try:
        lparam = _make_lparam(x, y)

        if button == 'left':
            down_msg = WM_LBUTTONDOWN
            up_msg = WM_LBUTTONUP
            wparam = MK_LBUTTON
        elif button == 'right':
            down_msg = WM_RBUTTONDOWN
            up_msg = WM_RBUTTONUP
            wparam = MK_RBUTTON
        else:
            return False

        user32.SendMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        user32.SendMessageW(hwnd, down_msg, wparam, lparam)
        user32.SendMessageW(hwnd, up_msg, 0, lparam)
        return True
    except Exception:
        return False


def screen_to_client(hwnd: int, x: int, y: int) -> Tuple[int, int]:
    """将屏幕坐标转换为窗口客户区坐标"""
    point = ctypes.wintypes.POINT(x, y)
    user32.ScreenToClient(hwnd, ctypes.byref(point))
    return (point.x, point.y)


def client_to_screen(hwnd: int, x: int, y: int) -> Tuple[int, int]:
    """将窗口客户区坐标转换为屏幕坐标"""
    point = ctypes.wintypes.POINT(x, y)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    return (point.x, point.y)


def get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """获取窗口矩形区域（屏幕坐标）"""
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def get_client_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """获取窗口客户区矩形"""
    rect = ctypes.wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def get_window_title(hwnd: int) -> str:
    """获取窗口标题"""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_window_class(hwnd: int) -> str:
    """获取窗口类名"""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_window_pid(hwnd: int) -> int:
    """获取窗口所属进程 ID"""
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def get_process_name(pid: int) -> str:
    """根据 PID 获取进程名"""
    try:
        handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if handle:
            buf = ctypes.create_unicode_buffer(260)
            psapi.GetModuleBaseNameW(handle, None, buf, 260)
            kernel32.CloseHandle(handle)
            return buf.value
    except Exception:
        pass
    return ""


def enumerate_windows(visible_only: bool = True,
                      title_filter: str = "") -> List[WindowInfo]:
    """枚举所有顶级窗口"""
    windows = []

    def _enum_callback(hwnd, _):
        if visible_only and not user32.IsWindowVisible(hwnd):
            return True

        title = get_window_title(hwnd)
        if not title:
            return True

        if title_filter and title_filter.lower() not in title.lower():
            return True

        class_name = get_window_class(hwnd)
        rect = get_window_rect(hwnd)
        pid = get_window_pid(hwnd)
        proc_name = get_process_name(pid)

        windows.append(WindowInfo(
            hwnd=hwnd,
            title=title,
            class_name=class_name,
            rect=rect,
            pid=pid,
            process_name=proc_name
        ))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

    return windows


def find_window_by_title(title: str) -> Optional[int]:
    """根据标题查找窗口句柄"""
    hwnd = user32.FindWindowW(None, title)
    return hwnd if hwnd else None


def find_windows_by_partial_title(partial_title: str) -> List[WindowInfo]:
    """根据部分标题查找窗口"""
    return enumerate_windows(visible_only=True, title_filter=partial_title)


def is_window_valid(hwnd: int) -> bool:
    """检查窗口句柄是否有效"""
    return bool(user32.IsWindow(hwnd))


def bring_window_to_front(hwnd: int):
    """将窗口带到前台"""
    user32.SetForegroundWindow(hwnd)


def get_foreground_window() -> int:
    """获取当前前台窗口"""
    return user32.GetForegroundWindow()
