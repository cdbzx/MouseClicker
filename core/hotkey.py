"""
全局热键管理器 - 使用 pynput 监听全局按键
支持组合键和自定义热键绑定
"""

import time
import threading
from typing import Dict, Callable, Optional, Set
from pynput import keyboard


class HotkeyManager:
    """全局热键管理器"""

    # 防抖间隔（秒），同一热键在此时间内不重复触发
    DEBOUNCE_INTERVAL = 0.3

    def __init__(self):
        self._bindings: Dict[str, Callable] = {}
        self._listener: Optional[keyboard.Listener] = None
        self._running = False
        self._pressed_keys: Set[str] = set()
        self._lock = threading.Lock()
        self._last_trigger: Dict[str, float] = {}  # 防抖时间戳

    def bind(self, key_name: str, callback: Callable):
        """
        绑定热键
        key_name 格式: "F6", "ctrl+F6", "alt+shift+F1" 等
        """
        normalized = self._normalize_key_name(key_name)
        self._bindings[normalized] = callback

    def unbind(self, key_name: str):
        """解绑热键"""
        normalized = self._normalize_key_name(key_name)
        self._bindings.pop(normalized, None)

    def unbind_all(self):
        """解绑所有热键"""
        self._bindings.clear()

    def start(self):
        """启动热键监听"""
        if self._running:
            return
        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        """停止热键监听"""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()

    def _normalize_key_name(self, key_name: str) -> str:
        """标准化键名"""
        parts = [p.strip().lower() for p in key_name.split('+')]
        # 排序修饰键，主键放最后
        modifiers = sorted([p for p in parts if p in ('ctrl', 'alt', 'shift')])
        main_keys = [p for p in parts if p not in ('ctrl', 'alt', 'shift')]
        return '+'.join(modifiers + main_keys)

    def _key_to_string(self, key) -> str:
        """将 pynput Key 对象转换为字符串"""
        try:
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            elif hasattr(key, 'name'):
                return key.name.lower()
            elif hasattr(key, 'vk'):
                # 功能键映射
                vk = key.vk
                if 112 <= vk <= 123:  # F1-F12
                    return f'f{vk - 111}'
                return str(key).lower()
        except AttributeError:
            pass
        return str(key).lower().replace("key.", "")

    def _get_current_combo(self) -> str:
        """获取当前按下的组合键字符串"""
        with self._lock:
            keys = set(self._pressed_keys)

        modifiers = []
        main_keys = []

        for k in keys:
            if k in ('ctrl_l', 'ctrl_r', 'ctrl'):
                if 'ctrl' not in modifiers:
                    modifiers.append('ctrl')
            elif k in ('alt_l', 'alt_r', 'alt', 'alt_gr'):
                if 'alt' not in modifiers:
                    modifiers.append('alt')
            elif k in ('shift_l', 'shift_r', 'shift'):
                if 'shift' not in modifiers:
                    modifiers.append('shift')
            else:
                main_keys.append(k)

        modifiers.sort()
        return '+'.join(modifiers + main_keys)

    def _try_trigger(self, combo: str):
        """尝试触发热键回调（带防抖）"""
        if combo not in self._bindings:
            return
        now = time.time()
        last = self._last_trigger.get(combo, 0)
        if now - last < self.DEBOUNCE_INTERVAL:
            return
        self._last_trigger[combo] = now
        try:
            callback = self._bindings[combo]
            threading.Thread(target=callback, daemon=True).start()
        except Exception:
            pass

    def _on_press(self, key):
        """按键按下事件"""
        if not self._running:
            return

        key_str = self._key_to_string(key)
        with self._lock:
            self._pressed_keys.add(key_str)

        # 策略1: 直接匹配单键（最可靠，不受残留键影响）
        self._try_trigger(key_str)

        # 策略2: 组合键匹配
        combo = self._get_current_combo()
        if combo != key_str:
            self._try_trigger(combo)

    def _on_release(self, key):
        """按键释放事件"""
        if not self._running:
            return

        key_str = self._key_to_string(key)
        with self._lock:
            self._pressed_keys.discard(key_str)
            # 定期清理：释放任意键时，如果只剩修饰键，全部清除
            remaining = set(self._pressed_keys)
            non_modifier = [k for k in remaining
                           if k not in ('ctrl_l','ctrl_r','alt_l','alt_r',
                                        'shift_l','shift_r','alt_gr')]
            if not non_modifier:
                self._pressed_keys.clear()


# 默认热键配置
DEFAULT_HOTKEYS = {
    'toggle': 'F6',       # 启动/停止
    'pause': 'F7',        # 暂停/恢复
    'emergency': 'F8',    # 紧急停止（停止+清空状态）
    'select_region': 'F9' # 框选区域
}
