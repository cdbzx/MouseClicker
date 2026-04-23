"""
人类行为模拟器 - 模拟真人点击行为
包含：贝塞尔曲线移动、随机延迟、点击力度模拟、路径抖动
"""

import random
import math
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class HumanProfile:
    """真人行为配置档案"""
    # 点击间隔 (秒)
    min_interval: float = 0.05
    max_interval: float = 0.3
    # 点击持续时间 (鼠标按下到释放, 秒)
    min_click_duration: float = 0.02
    max_click_duration: float = 0.08
    # 位置偏移 (像素)
    position_jitter: int = 5
    # 移动速度因子 (越大越慢)
    move_speed_factor: float = 1.0
    # 疲劳模拟：连续点击后延迟增加
    fatigue_enabled: bool = True
    fatigue_threshold: int = 50  # 多少次点击后开始疲劳
    fatigue_multiplier: float = 1.5  # 疲劳后延迟倍数
    # 随机暂停 (模拟人类走神)
    random_pause_chance: float = 0.02  # 2% 概率暂停
    random_pause_min: float = 0.5
    random_pause_max: float = 2.0

    # 预设档案
    @classmethod
    def fast(cls) -> 'HumanProfile':
        return cls(min_interval=0.03, max_interval=0.1, position_jitter=3,
                   move_speed_factor=0.5, fatigue_enabled=False, random_pause_chance=0.01)

    @classmethod
    def normal(cls) -> 'HumanProfile':
        return cls()

    @classmethod
    def careful(cls) -> 'HumanProfile':
        return cls(min_interval=0.2, max_interval=0.8, position_jitter=2,
                   move_speed_factor=2.0, fatigue_multiplier=2.0, random_pause_chance=0.05)


class BezierCurve:
    """贝塞尔曲线生成器 - 用于模拟真人鼠标移动路径"""

    @staticmethod
    def generate_control_points(start: Tuple[int, int], end: Tuple[int, int],
                                num_controls: int = 2) -> List[Tuple[float, float]]:
        """生成贝塞尔曲线控制点"""
        points = [start]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.sqrt(dx ** 2 + dy ** 2)

        for i in range(num_controls):
            t = (i + 1) / (num_controls + 1)
            # 基准点在直线上
            base_x = start[0] + dx * t
            base_y = start[1] + dy * t
            # 偏移量与距离成正比
            offset = distance * 0.3
            ctrl_x = base_x + random.uniform(-offset, offset)
            ctrl_y = base_y + random.uniform(-offset, offset)
            points.append((ctrl_x, ctrl_y))

        points.append(end)
        return points

    @staticmethod
    def evaluate(control_points: List[Tuple[float, float]], t: float) -> Tuple[float, float]:
        """De Casteljau 算法计算贝塞尔曲线上的点"""
        points = list(control_points)
        n = len(points)
        for r in range(1, n):
            for i in range(n - r):
                points[i] = (
                    (1 - t) * points[i][0] + t * points[i + 1][0],
                    (1 - t) * points[i][1] + t * points[i + 1][1]
                )
        return points[0]

    @staticmethod
    def generate_path(start: Tuple[int, int], end: Tuple[int, int],
                      steps: int = 20, num_controls: int = 2) -> List[Tuple[int, int]]:
        """生成从 start 到 end 的贝塞尔曲线路径"""
        control_points = BezierCurve.generate_control_points(start, end, num_controls)
        path = []
        for i in range(steps + 1):
            t = i / steps
            # 使用 ease-in-out 缓动函数
            t_eased = BezierCurve._ease_in_out(t)
            point = BezierCurve.evaluate(control_points, t_eased)
            path.append((int(point[0]), int(point[1])))
        return path

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """缓入缓出函数 - 模拟真人鼠标加速减速"""
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - (-2 * t + 2) ** 2 / 2


class HumanClickSimulator:
    """真人点击行为模拟器"""

    def __init__(self, profile: HumanProfile = None):
        self.profile = profile or HumanProfile.normal()
        self._click_count = 0
        self._session_start = time.time()

    def reset(self):
        """重置计数器"""
        self._click_count = 0
        self._session_start = time.time()

    def get_click_delay(self) -> float:
        """获取下一次点击的延迟时间"""
        p = self.profile
        base_delay = random.uniform(p.min_interval, p.max_interval)

        # 添加高斯噪声使延迟更自然
        noise = random.gauss(0, (p.max_interval - p.min_interval) * 0.1)
        delay = max(p.min_interval, base_delay + noise)

        # 疲劳效应
        if p.fatigue_enabled and self._click_count > p.fatigue_threshold:
            fatigue_factor = 1 + (p.fatigue_multiplier - 1) * min(
                (self._click_count - p.fatigue_threshold) / 100, 1.0
            )
            delay *= fatigue_factor

        # 随机暂停
        if random.random() < p.random_pause_chance:
            delay += random.uniform(p.random_pause_min, p.random_pause_max)

        return delay

    def get_click_duration(self) -> float:
        """获取鼠标按下到释放的持续时间"""
        p = self.profile
        duration = random.uniform(p.min_click_duration, p.max_click_duration)
        # 添加少量噪声
        duration += random.gauss(0, 0.005)
        return max(0.01, duration)

    def jitter_position(self, x: int, y: int) -> Tuple[int, int]:
        """给坐标添加随机抖动"""
        j = self.profile.position_jitter
        if j <= 0:
            return (x, y)
        dx = random.randint(-j, j)
        dy = random.randint(-j, j)
        return (x + dx, y + dy)

    def generate_move_path(self, start: Tuple[int, int],
                           end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """生成从当前位置到目标位置的真人移动路径"""
        distance = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
        # 步数与距离和速度因子相关
        steps = max(5, int(distance / 10 * self.profile.move_speed_factor))
        steps = min(steps, 50)  # 上限

        path = BezierCurve.generate_path(start, end, steps)

        # 给路径添加微小抖动
        jittered_path = []
        for i, (px, py) in enumerate(path):
            if 0 < i < len(path) - 1:  # 不抖动起点和终点
                px += random.randint(-1, 1)
                py += random.randint(-1, 1)
            jittered_path.append((px, py))

        return jittered_path

    def get_random_point_in_region(self, x1: int, y1: int,
                                   x2: int, y2: int) -> Tuple[int, int]:
        """在区域内生成随机点 (偏向中心的高斯分布)"""
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        sx = (x2 - x1) / 4  # 标准差
        sy = (y2 - y1) / 4

        x = int(random.gauss(cx, sx))
        y = int(random.gauss(cy, sy))

        # 确保在区域内
        x = max(x1, min(x2, x))
        y = max(y1, min(y2, y))

        return self.jitter_position(x, y)

    def increment_click(self):
        """记录一次点击"""
        self._click_count += 1

    @property
    def click_count(self) -> int:
        return self._click_count
