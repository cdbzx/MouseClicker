"""
点击引擎 - 核心点击逻辑
支持：前台点击、后台点击、多区域轮询、随机路径
"""

import time
import random
import threading
import pyautogui
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable
from enum import Enum

from core.humanizer import HumanClickSimulator, HumanProfile
from utils.win32_utils import send_click, screen_to_client, is_window_valid


class ClickMode(Enum):
    FOREGROUND = "foreground"  # 前台点击 (pyautogui)
    BACKGROUND = "background"  # 后台点击 (Win32 SendMessage)


class ClickOrder(Enum):
    SEQUENTIAL = "sequential"  # 顺序轮询区域
    RANDOM = "random"          # 随机选择区域
    WEIGHTED = "weighted"      # 加权随机


@dataclass
class ClickRegion:
    """点击区域定义"""
    name: str
    x1: int
    y1: int
    x2: int
    y2: int
    enabled: bool = True
    weight: float = 1.0  # 加权随机时的权重
    color: str = "#FF0000"  # 显示颜色

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def width(self) -> int:
        return abs(self.x2 - self.x1)

    @property
    def height(self) -> int:
        return abs(self.y2 - self.y1)

    def normalize(self):
        """确保 x1<x2, y1<y2"""
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1

    def contains(self, x: int, y: int) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def to_dict(self) -> dict:
        return {
            'name': self.name, 'x1': self.x1, 'y1': self.y1,
            'x2': self.x2, 'y2': self.y2, 'enabled': self.enabled,
            'weight': self.weight, 'color': self.color
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ClickRegion':
        return cls(**d)


@dataclass
class ClickConfig:
    """点击配置"""
    mode: ClickMode = ClickMode.FOREGROUND
    order: ClickOrder = ClickOrder.RANDOM
    profile: HumanProfile = field(default_factory=HumanProfile.normal)
    # 后台模式的目标窗口句柄
    target_hwnd: int = 0
    # 是否启用鼠标移动动画 (仅前台模式)
    animate_mouse: bool = True
    # 双击概率
    double_click_chance: float = 0.0
    # 右键概率
    right_click_chance: float = 0.0
    # 总点击次数限制 (0=无限)
    max_clicks: int = 0
    # 总运行时间限制秒 (0=无限)
    max_duration: float = 0


class ClickEngine:
    """点击引擎主类"""

    def __init__(self):
        self._regions: List[ClickRegion] = []
        self._config = ClickConfig()
        self._simulator = HumanClickSimulator()
        self._running = False
        self._paused = False
        self._destroyed = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._current_region_index = 0

        # 回调
        self._on_click: Optional[Callable] = None  # (region_name, x, y, click_count)
        self._on_status_change: Optional[Callable] = None  # (status_str)
        self._on_error: Optional[Callable] = None  # (error_str)
        self._on_stopped: Optional[Callable] = None  # ()

        # 禁用 pyautogui 安全特性
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0

    @property
    def regions(self) -> List[ClickRegion]:
        return self._regions

    @property
    def config(self) -> ClickConfig:
        return self._config

    @config.setter
    def config(self, value: ClickConfig):
        self._config = value
        self._simulator = HumanClickSimulator(value.profile)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def click_count(self) -> int:
        return self._simulator.click_count

    def set_callbacks(self, on_click=None, on_status_change=None,
                      on_error=None, on_stopped=None):
        self._on_click = on_click
        self._on_status_change = on_status_change
        self._on_error = on_error
        self._on_stopped = on_stopped

    def add_region(self, region: ClickRegion):
        region.normalize()
        self._regions.append(region)

    def remove_region(self, index: int):
        if 0 <= index < len(self._regions):
            self._regions.pop(index)

    def clear_regions(self):
        self._regions.clear()

    def start(self):
        """启动点击"""
        if self._running:
            return

        enabled_regions = [r for r in self._regions if r.enabled]
        if not enabled_regions:
            if self._on_error:
                self._on_error("没有启用的点击区域")
            return

        if self._config.mode == ClickMode.BACKGROUND:
            if not self._config.target_hwnd or not is_window_valid(self._config.target_hwnd):
                if self._on_error:
                    self._on_error("后台模式需要有效的目标窗口")
                return

        self._running = True
        self._paused = False
        self._simulator.reset()
        self._current_region_index = 0

        self._thread = threading.Thread(target=self._click_loop, daemon=True)
        self._thread.start()

        if self._on_status_change:
            self._on_status_change("运行中")

    def stop(self):
        """停止点击"""
        self._running = False
        self._paused = False
        if self._on_status_change and not self._destroyed:
            try:
                self._on_status_change("已停止")
            except RuntimeError:
                pass

    def destroy(self):
        """销毁引擎 - 在窗口关闭前调用，阻止后续回调"""
        self._destroyed = True
        self._running = False
        self._paused = False
        # 等待点击线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._on_click = None
        self._on_status_change = None
        self._on_error = None
        self._on_stopped = None

    def pause(self):
        """暂停/恢复"""
        if not self._running:
            return
        self._paused = not self._paused
        status = "已暂停" if self._paused else "运行中"
        if self._on_status_change:
            self._on_status_change(status)

    def toggle(self):
        """切换启动/停止"""
        if self._running:
            self.stop()
        else:
            self.start()

    def _select_region(self) -> Optional[ClickRegion]:
        """根据策略选择下一个点击区域"""
        enabled = [r for r in self._regions if r.enabled]
        if not enabled:
            return None

        if self._config.order == ClickOrder.SEQUENTIAL:
            idx = self._current_region_index % len(enabled)
            self._current_region_index += 1
            return enabled[idx]

        elif self._config.order == ClickOrder.RANDOM:
            return random.choice(enabled)

        elif self._config.order == ClickOrder.WEIGHTED:
            weights = [r.weight for r in enabled]
            total = sum(weights)
            if total <= 0:
                return random.choice(enabled)
            return random.choices(enabled, weights=weights, k=1)[0]

        return enabled[0]

    def _click_loop(self):
        """主点击循环"""
        start_time = time.time()

        try:
            while self._running:
                # 暂停检查
                while self._paused and self._running:
                    time.sleep(0.05)

                if not self._running:
                    break

                # 检查限制
                cfg = self._config
                if cfg.max_clicks > 0 and self._simulator.click_count >= cfg.max_clicks:
                    break
                if cfg.max_duration > 0 and (time.time() - start_time) >= cfg.max_duration:
                    break

                # 选择区域
                region = self._select_region()
                if not region:
                    break

                # 生成点击坐标
                target_x, target_y = self._simulator.get_random_point_in_region(
                    region.x1, region.y1, region.x2, region.y2
                )

                # 执行点击
                success = self._perform_click(target_x, target_y, region)

                if success:
                    self._simulator.increment_click()
                    if self._on_click:
                        self._on_click(region.name, target_x, target_y,
                                       self._simulator.click_count)

                # 等待
                delay = self._simulator.get_click_delay()
                # 分段等待以便快速响应停止
                wait_end = time.time() + delay
                while time.time() < wait_end and self._running:
                    time.sleep(min(0.01, wait_end - time.time()))

        except Exception as e:
            if self._on_error and not self._destroyed:
                try:
                    self._on_error(f"点击引擎错误: {str(e)}")
                except RuntimeError:
                    pass
        finally:
            self._running = False
            self._paused = False
            if self._on_stopped and not self._destroyed:
                try:
                    self._on_stopped()
                except RuntimeError:
                    pass

    def _perform_click(self, x: int, y: int, region: ClickRegion) -> bool:
        """执行一次点击"""
        try:
            # 决定按钮
            button = 'left'
            if random.random() < self._config.right_click_chance:
                button = 'right'

            if self._config.mode == ClickMode.FOREGROUND:
                return self._foreground_click(x, y, button)
            else:
                return self._background_click(x, y, button)

        except Exception as e:
            if self._on_error:
                self._on_error(f"点击失败 ({x}, {y}): {str(e)}")
            return False

    def _foreground_click(self, x: int, y: int, button: str = 'left') -> bool:
        """前台点击"""
        if self._config.animate_mouse:
            # 获取当前鼠标位置
            current_x, current_y = pyautogui.position()
            # 生成移动路径
            path = self._simulator.generate_move_path(
                (current_x, current_y), (x, y)
            )
            # 沿路径移动
            for px, py in path:
                if not self._running:
                    return False
                pyautogui.moveTo(px, py, _pause=False)
                time.sleep(0.005)

        # 点击
        duration = self._simulator.get_click_duration()

        if button == 'left':
            pyautogui.mouseDown(x, y, button='left', _pause=False)
            time.sleep(duration)
            pyautogui.mouseUp(x, y, button='left', _pause=False)

            # 双击
            if random.random() < self._config.double_click_chance:
                time.sleep(random.uniform(0.02, 0.08))
                pyautogui.mouseDown(x, y, button='left', _pause=False)
                time.sleep(duration)
                pyautogui.mouseUp(x, y, button='left', _pause=False)
        else:
            pyautogui.mouseDown(x, y, button='right', _pause=False)
            time.sleep(duration)
            pyautogui.mouseUp(x, y, button='right', _pause=False)

        return True

    def _background_click(self, x: int, y: int, button: str = 'left') -> bool:
        """后台点击 - 使用 Win32 API"""
        hwnd = self._config.target_hwnd
        if not is_window_valid(hwnd):
            if self._on_error:
                self._on_error("目标窗口已失效")
            return False

        # 将屏幕坐标转换为窗口客户区坐标
        client_x, client_y = screen_to_client(hwnd, x, y)
        return send_click(hwnd, client_x, client_y, button)
