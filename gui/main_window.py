"""
主窗口 - 连点器控制界面
"""

import json
import os
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QListWidget, QListWidgetItem, QTabWidget, QTextEdit,
    QFileDialog, QMessageBox, QSlider, QLineEdit, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QIcon, QFont, QColor

from core.clicker import ClickEngine, ClickConfig, ClickMode, ClickOrder, ClickRegion
from core.humanizer import HumanProfile
from core.hotkey import HotkeyManager, DEFAULT_HOTKEYS
from gui.region_selector import RegionSelector
from gui.styles import DARK_THEME, REGION_COLORS
from utils.win32_utils import enumerate_windows, WindowInfo


class MainWindow(QMainWindow):
    """主窗口"""

    # 线程安全的信号
    _sig_click = pyqtSignal(str, int, int, int)
    _sig_status = pyqtSignal(str)
    _sig_error = pyqtSignal(str)
    _sig_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.engine = ClickEngine()
        self.hotkey_mgr = HotkeyManager()
        self.region_selector = RegionSelector()
        self._region_counter = 0
        self._start_time = None
        self._config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                          "config.json")

        self._init_ui()
        self._init_signals()
        self._init_hotkeys()
        self._init_timer()
        self._load_config()

    def _init_ui(self):
        self.setWindowTitle("工程级连点器 v1.0")
        self.setMinimumSize(700, 680)
        self.resize(780, 750)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # === 顶部标题和状态栏 ===
        top_bar = QHBoxLayout()
        title = QLabel("⚡ 工程级连点器")
        title.setObjectName("titleLabel")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.status_label = QLabel("● 就绪")
        self.status_label.setObjectName("statusLabel")
        top_bar.addWidget(self.status_label)

        self.count_label = QLabel("0 次")
        self.count_label.setObjectName("countLabel")
        top_bar.addWidget(self.count_label)

        main_layout.addLayout(top_bar)

        # === 标签页 ===
        tabs = QTabWidget()
        main_layout.addWidget(tabs, 1)

        # --- Tab 1: 区域管理 ---
        region_tab = QWidget()
        region_layout = QVBoxLayout(region_tab)

        # 区域列表
        region_group = QGroupBox("点击区域")
        rg_layout = QVBoxLayout(region_group)

        self.region_list = QListWidget()
        self.region_list.setMinimumHeight(120)
        rg_layout.addWidget(self.region_list)

        btn_row = QHBoxLayout()
        self.add_region_btn = QPushButton("📐 框选添加区域")
        self.add_region_btn.setObjectName("selectRegionBtn")
        self.add_region_btn.clicked.connect(self._start_region_select)
        btn_row.addWidget(self.add_region_btn)

        self.del_region_btn = QPushButton("删除选中")
        self.del_region_btn.setObjectName("deleteBtn")
        self.del_region_btn.clicked.connect(self._delete_region)
        btn_row.addWidget(self.del_region_btn)

        self.clear_region_btn = QPushButton("清空全部")
        self.clear_region_btn.clicked.connect(self._clear_regions)
        btn_row.addWidget(self.clear_region_btn)

        btn_row.addStretch()
        rg_layout.addLayout(btn_row)
        region_layout.addWidget(region_group)

        # 区域顺序
        order_group = QGroupBox("多区域策略")
        order_layout = QHBoxLayout(order_group)

        order_layout.addWidget(QLabel("点击顺序:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["随机选择", "顺序轮询", "加权随机"])
        order_layout.addWidget(self.order_combo)
        order_layout.addStretch()

        region_layout.addWidget(order_group)
        tabs.addTab(region_tab, "区域管理")

        # --- Tab 2: 点击设置 ---
        click_tab = QWidget()
        click_layout = QVBoxLayout(click_tab)

        # 模式选择
        mode_group = QGroupBox("点击模式")
        mode_layout = QGridLayout(mode_group)

        mode_layout.addWidget(QLabel("模式:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["前台点击", "后台点击"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo, 0, 1)

        mode_layout.addWidget(QLabel("目标窗口:"), 1, 0)
        self.window_combo = QComboBox()
        self.window_combo.setMinimumWidth(300)
        mode_layout.addWidget(self.window_combo, 1, 1)

        self.refresh_windows_btn = QPushButton("刷新")
        self.refresh_windows_btn.clicked.connect(self._refresh_windows)
        mode_layout.addWidget(self.refresh_windows_btn, 1, 2)

        self.window_combo.setEnabled(False)
        self.refresh_windows_btn.setEnabled(False)

        click_layout.addWidget(mode_group)

        # 行为配置
        behavior_group = QGroupBox("真人模拟配置")
        bg_layout = QGridLayout(behavior_group)

        # 预设
        bg_layout.addWidget(QLabel("行为预设:"), 0, 0)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["正常", "快速", "谨慎", "自定义"])
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        bg_layout.addWidget(self.profile_combo, 0, 1, 1, 2)

        # 间隔
        bg_layout.addWidget(QLabel("最小间隔 (秒):"), 1, 0)
        self.min_interval = QDoubleSpinBox()
        self.min_interval.setRange(0.01, 10.0)
        self.min_interval.setSingleStep(0.01)
        self.min_interval.setValue(0.05)
        self.min_interval.setDecimals(3)
        bg_layout.addWidget(self.min_interval, 1, 1)

        bg_layout.addWidget(QLabel("最大间隔 (秒):"), 1, 2)
        self.max_interval = QDoubleSpinBox()
        self.max_interval.setRange(0.01, 10.0)
        self.max_interval.setSingleStep(0.01)
        self.max_interval.setValue(0.30)
        self.max_interval.setDecimals(3)
        bg_layout.addWidget(self.max_interval, 1, 3)

        # 抖动
        bg_layout.addWidget(QLabel("位置抖动 (px):"), 2, 0)
        self.jitter_spin = QSpinBox()
        self.jitter_spin.setRange(0, 50)
        self.jitter_spin.setValue(5)
        bg_layout.addWidget(self.jitter_spin, 2, 1)

        # 鼠标动画
        self.animate_check = QCheckBox("鼠标移动动画 (仅前台)")
        self.animate_check.setChecked(True)
        bg_layout.addWidget(self.animate_check, 2, 2, 1, 2)

        # 疲劳模拟
        self.fatigue_check = QCheckBox("疲劳模拟")
        self.fatigue_check.setChecked(True)
        bg_layout.addWidget(self.fatigue_check, 3, 0, 1, 2)

        # 随机暂停
        self.random_pause_check = QCheckBox("随机走神暂停")
        self.random_pause_check.setChecked(True)
        bg_layout.addWidget(self.random_pause_check, 3, 2, 1, 2)

        click_layout.addWidget(behavior_group)

        # 限制
        limit_group = QGroupBox("运行限制")
        lg_layout = QGridLayout(limit_group)

        lg_layout.addWidget(QLabel("最大点击次数 (0=无限):"), 0, 0)
        self.max_clicks_spin = QSpinBox()
        self.max_clicks_spin.setRange(0, 999999)
        self.max_clicks_spin.setValue(0)
        lg_layout.addWidget(self.max_clicks_spin, 0, 1)

        lg_layout.addWidget(QLabel("最大运行时间 (秒, 0=无限):"), 0, 2)
        self.max_duration_spin = QDoubleSpinBox()
        self.max_duration_spin.setRange(0, 86400)
        self.max_duration_spin.setValue(0)
        lg_layout.addWidget(self.max_duration_spin, 0, 3)

        click_layout.addWidget(limit_group)
        click_layout.addStretch()

        tabs.addTab(click_tab, "点击设置")

        # --- Tab 3: 热键设置 ---
        hotkey_tab = QWidget()
        hk_layout = QVBoxLayout(hotkey_tab)

        hotkey_group = QGroupBox("热键绑定")
        hkg_layout = QGridLayout(hotkey_group)

        self.hotkey_edits = {}
        hotkey_info = [
            ("toggle", "启动/停止:", DEFAULT_HOTKEYS['toggle']),
            ("pause", "暂停/恢复:", DEFAULT_HOTKEYS['pause']),
            ("emergency", "紧急停止:", DEFAULT_HOTKEYS['emergency']),
            ("select_region", "框选区域:", DEFAULT_HOTKEYS['select_region']),
        ]

        for i, (key, label, default) in enumerate(hotkey_info):
            hkg_layout.addWidget(QLabel(label), i, 0)
            edit = QLineEdit(default)
            edit.setMaximumWidth(150)
            edit.setAlignment(Qt.AlignCenter)
            self.hotkey_edits[key] = edit
            hkg_layout.addWidget(edit, i, 1)

        apply_hk_btn = QPushButton("应用热键")
        apply_hk_btn.clicked.connect(self._apply_hotkeys)
        hkg_layout.addWidget(apply_hk_btn, len(hotkey_info), 0, 1, 2)

        hk_layout.addWidget(hotkey_group)

        # 热键说明
        info_group = QGroupBox("说明")
        info_layout = QVBoxLayout(info_group)
        info_text = QLabel(
            "• 热键格式: F6, ctrl+F6, alt+shift+F1 等\n"
            "• 热键在全局生效，即使窗口未激活\n"
            "• 紧急停止会立即中断所有点击\n"
            "• 修改热键后需点击「应用热键」生效"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        hk_layout.addWidget(info_group)
        hk_layout.addStretch()

        tabs.addTab(hotkey_tab, "热键设置")

        # --- Tab 4: 日志 ---
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        log_btn_row = QHBoxLayout()
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_btn_row.addWidget(clear_log_btn)

        export_log_btn = QPushButton("导出日志")
        export_log_btn.clicked.connect(self._export_log)
        log_btn_row.addWidget(export_log_btn)
        log_btn_row.addStretch()
        log_layout.addLayout(log_btn_row)

        tabs.addTab(log_tab, "运行日志")

        # === 底部控制栏 ===
        bottom_bar = QHBoxLayout()

        self.start_btn = QPushButton("▶  启动  (F6)")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self._on_start)
        bottom_bar.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■  停止  (F6)")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setVisible(False)
        bottom_bar.addWidget(self.stop_btn)

        self.pause_btn = QPushButton("⏸  暂停  (F7)")
        self.pause_btn.clicked.connect(self._on_pause)
        self.pause_btn.setEnabled(False)
        bottom_bar.addWidget(self.pause_btn)

        bottom_bar.addStretch()

        # 配置导入导出
        save_cfg_btn = QPushButton("保存配置")
        save_cfg_btn.clicked.connect(self._save_config)
        bottom_bar.addWidget(save_cfg_btn)

        load_cfg_btn = QPushButton("加载配置")
        load_cfg_btn.clicked.connect(self._load_config_dialog)
        bottom_bar.addWidget(load_cfg_btn)

        main_layout.addLayout(bottom_bar)

        # 运行时间显示
        self.time_label = QLabel("")
        main_layout.addWidget(self.time_label)

    def _init_signals(self):
        """连接线程安全信号"""
        self._sig_click.connect(self._on_click_signal)
        self._sig_status.connect(self._on_status_signal)
        self._sig_error.connect(self._on_error_signal)
        self._sig_stopped.connect(self._on_stopped_signal)

        self.engine.set_callbacks(
            on_click=lambda name, x, y, cnt: self._sig_click.emit(name, x, y, cnt),
            on_status_change=lambda s: self._sig_status.emit(s),
            on_error=lambda e: self._sig_error.emit(e),
            on_stopped=lambda: self._sig_stopped.emit()
        )

        self.region_selector.region_selected.connect(self._on_region_selected)

    def _init_hotkeys(self):
        """初始化全局热键"""
        self.hotkey_mgr.bind(DEFAULT_HOTKEYS['toggle'], self._hotkey_toggle)
        self.hotkey_mgr.bind(DEFAULT_HOTKEYS['pause'], self._hotkey_pause)
        self.hotkey_mgr.bind(DEFAULT_HOTKEYS['emergency'], self._hotkey_emergency)
        self.hotkey_mgr.bind(DEFAULT_HOTKEYS['select_region'], self._hotkey_select_region)
        # Esc 键停止点击
        self.hotkey_mgr.bind('esc', self._hotkey_emergency)
        self.hotkey_mgr.start()

    def _init_timer(self):
        """初始化 UI 更新定时器"""
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._update_ui_timer)
        self.ui_timer.start(200)

    # ==================== 区域管理 ====================

    def _start_region_select(self):
        """启动区域框选"""
        self.showMinimized()
        QTimer.singleShot(300, self.region_selector.start_selection)

    @pyqtSlot(int, int, int, int)
    def _on_region_selected(self, x1, y1, x2, y2):
        """区域选择完成回调"""
        self._region_counter += 1
        color = REGION_COLORS[(self._region_counter - 1) % len(REGION_COLORS)]
        region = ClickRegion(
            name=f"区域 {self._region_counter}",
            x1=x1, y1=y1, x2=x2, y2=y2,
            color=color
        )
        self.engine.add_region(region)
        self._refresh_region_list()
        self._log(f"添加区域: {region.name} 物理坐标({x1},{y1})->({x2},{y2}) [{x2-x1}x{y2-y1}]")

        self.showNormal()
        self.activateWindow()

    def _delete_region(self):
        row = self.region_list.currentRow()
        if row >= 0:
            name = self.engine.regions[row].name
            self.engine.remove_region(row)
            self._refresh_region_list()
            self._log(f"删除区域: {name}")

    def _clear_regions(self):
        self.engine.clear_regions()
        self._refresh_region_list()
        self._region_counter = 0
        self._log("已清空所有区域")

    def _refresh_region_list(self):
        self.region_list.clear()
        for r in self.engine.regions:
            status = "✓" if r.enabled else "✗"
            text = f"{status} {r.name}  |  ({r.x1},{r.y1})→({r.x2},{r.y2})  |  {r.width}×{r.height}"
            item = QListWidgetItem(text)
            item.setForeground(QColor(r.color))
            self.region_list.addItem(item)

    # ==================== 模式切换 ====================

    def _on_mode_changed(self, index):
        is_bg = (index == 1)
        self.window_combo.setEnabled(is_bg)
        self.refresh_windows_btn.setEnabled(is_bg)
        self.animate_check.setEnabled(not is_bg)
        if is_bg:
            self._refresh_windows()

    def _refresh_windows(self):
        self.window_combo.clear()
        self._windows = enumerate_windows(visible_only=True)
        for w in self._windows:
            if w.width > 50 and w.height > 50:
                text = f"{w.title} [{w.process_name}] ({w.width}x{w.height})"
                self.window_combo.addItem(text, w.hwnd)

    # ==================== 行为预设 ====================

    def _on_profile_changed(self, index):
        if index == 0:  # 正常
            p = HumanProfile.normal()
        elif index == 1:  # 快速
            p = HumanProfile.fast()
        elif index == 2:  # 谨慎
            p = HumanProfile.careful()
        else:  # 自定义
            return

        self.min_interval.setValue(p.min_interval)
        self.max_interval.setValue(p.max_interval)
        self.jitter_spin.setValue(p.position_jitter)
        self.fatigue_check.setChecked(p.fatigue_enabled)
        self.random_pause_check.setChecked(p.random_pause_chance > 0.01)

    # ==================== 控制按钮 ====================

    def _build_config(self) -> ClickConfig:
        """从 UI 构建配置"""
        profile = HumanProfile(
            min_interval=self.min_interval.value(),
            max_interval=self.max_interval.value(),
            position_jitter=self.jitter_spin.value(),
            fatigue_enabled=self.fatigue_check.isChecked(),
            random_pause_chance=0.02 if self.random_pause_check.isChecked() else 0.0,
        )

        mode = ClickMode.BACKGROUND if self.mode_combo.currentIndex() == 1 else ClickMode.FOREGROUND

        order_map = {0: ClickOrder.RANDOM, 1: ClickOrder.SEQUENTIAL, 2: ClickOrder.WEIGHTED}
        order = order_map.get(self.order_combo.currentIndex(), ClickOrder.RANDOM)

        hwnd = 0
        if mode == ClickMode.BACKGROUND and self.window_combo.currentIndex() >= 0:
            hwnd = self.window_combo.currentData() or 0

        return ClickConfig(
            mode=mode,
            order=order,
            profile=profile,
            target_hwnd=hwnd,
            animate_mouse=self.animate_check.isChecked(),
            max_clicks=self.max_clicks_spin.value(),
            max_duration=self.max_duration_spin.value(),
        )

    def _on_start(self):
        config = self._build_config()
        self.engine.config = config
        self.engine.start()
        self._start_time = time.time()
        self.start_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.pause_btn.setEnabled(True)
        self._log("=== 连点器启动 ===")

    def _on_stop(self):
        self.engine.stop()
        self.start_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸  暂停  (F7)")
        self._log("=== 连点器停止 ===")

    def _on_pause(self):
        self.engine.pause()
        if self.engine.is_paused:
            self.pause_btn.setText("▶  恢复  (F7)")
        else:
            self.pause_btn.setText("⏸  暂停  (F7)")

    # ==================== 热键回调 ====================

    def _hotkey_toggle(self):
        if self.engine.is_running:
            self.engine.stop()
            QTimer.singleShot(0, self._on_stop)
        else:
            QTimer.singleShot(0, self._on_start)

    def _hotkey_pause(self):
        if self.engine.is_running:
            QTimer.singleShot(0, self._on_pause)

    def _hotkey_emergency(self):
        self.engine.stop()
        self._sig_error.emit("⚠ 紧急停止已触发!")
        QTimer.singleShot(0, self._on_stop)

    def _hotkey_select_region(self):
        if not self.engine.is_running:
            QTimer.singleShot(0, self._start_region_select)

    # ==================== 热键设置 ====================

    def _apply_hotkeys(self):
        self.hotkey_mgr.unbind_all()
        mapping = {
            'toggle': self._hotkey_toggle,
            'pause': self._hotkey_pause,
            'emergency': self._hotkey_emergency,
            'select_region': self._hotkey_select_region,
        }
        for key, edit in self.hotkey_edits.items():
            hotkey_str = edit.text().strip()
            if hotkey_str and key in mapping:
                self.hotkey_mgr.bind(hotkey_str, mapping[key])

        self._log("热键配置已更新")

    # ==================== UI 信号槽 ====================

    @pyqtSlot(str, int, int, int)
    def _on_click_signal(self, region_name, x, y, count):
        self.count_label.setText(f"{count} 次")

    @pyqtSlot(str)
    def _on_status_signal(self, status):
        self.status_label.setText(f"● {status}")
        if "运行" in status:
            self.status_label.setStyleSheet("color: #a6e3a1;")
        elif "暂停" in status:
            self.status_label.setStyleSheet("color: #f9e2af;")
        else:
            self.status_label.setStyleSheet("color: #cdd6f4;")

    @pyqtSlot(str)
    def _on_error_signal(self, error):
        self._log(f"[错误] {error}")
        self.status_label.setText(f"● {error}")
        self.status_label.setStyleSheet("color: #f38ba8;")

    @pyqtSlot()
    def _on_stopped_signal(self):
        self.start_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸  暂停  (F7)")
        self.status_label.setText("● 已停止")
        self.status_label.setStyleSheet("color: #cdd6f4;")
        if self._start_time:
            elapsed = time.time() - self._start_time
            self._log(f"运行 {elapsed:.1f} 秒，共点击 {self.engine.click_count} 次")
            self._start_time = None

    def _update_ui_timer(self):
        """定时更新 UI"""
        if self.engine.is_running and self._start_time:
            elapsed = time.time() - self._start_time
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            self.time_label.setText(f"运行时间: {mins:02d}:{secs:02d}  |  速率: ~{self.engine.click_count / max(elapsed, 0.1):.1f} 次/秒")
        else:
            self.time_label.setText("")

    # ==================== 日志 ====================

    def _log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "clicker_log.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            self._log(f"日志已导出到: {path}")

    # ==================== 配置持久化 ====================

    def _save_config(self):
        config = {
            'regions': [r.to_dict() for r in self.engine.regions],
            'mode': self.mode_combo.currentIndex(),
            'order': self.order_combo.currentIndex(),
            'profile': self.profile_combo.currentIndex(),
            'min_interval': self.min_interval.value(),
            'max_interval': self.max_interval.value(),
            'jitter': self.jitter_spin.value(),
            'animate': self.animate_check.isChecked(),
            'fatigue': self.fatigue_check.isChecked(),
            'random_pause': self.random_pause_check.isChecked(),
            'max_clicks': self.max_clicks_spin.value(),
            'max_duration': self.max_duration_spin.value(),
            'hotkeys': {k: v.text() for k, v in self.hotkey_edits.items()},
        }
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self._log(f"配置已保存到: {self._config_path}")
        except Exception as e:
            self._log(f"保存配置失败: {e}")

    def _load_config(self):
        if not os.path.exists(self._config_path):
            return
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 恢复区域
            self.engine.clear_regions()
            for rd in config.get('regions', []):
                self.engine.add_region(ClickRegion.from_dict(rd))
                self._region_counter += 1
            self._refresh_region_list()

            # 恢复设置
            self.mode_combo.setCurrentIndex(config.get('mode', 0))
            self.order_combo.setCurrentIndex(config.get('order', 0))
            self.profile_combo.setCurrentIndex(config.get('profile', 0))
            self.min_interval.setValue(config.get('min_interval', 0.05))
            self.max_interval.setValue(config.get('max_interval', 0.3))
            self.jitter_spin.setValue(config.get('jitter', 5))
            self.animate_check.setChecked(config.get('animate', True))
            self.fatigue_check.setChecked(config.get('fatigue', True))
            self.random_pause_check.setChecked(config.get('random_pause', True))
            self.max_clicks_spin.setValue(config.get('max_clicks', 0))
            self.max_duration_spin.setValue(config.get('max_duration', 0))

            # 恢复热键
            for key, value in config.get('hotkeys', {}).items():
                if key in self.hotkey_edits:
                    self.hotkey_edits[key].setText(value)

            self._log("已加载保存的配置")
        except Exception as e:
            self._log(f"加载配置失败: {e}")

    def _load_config_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "加载配置", "", "JSON Files (*.json)")
        if path:
            old_path = self._config_path
            self._config_path = path
            self._load_config()
            self._config_path = old_path

    # ==================== 窗口事件 ====================

    def keyPressEvent(self, event):
        """Esc 键停止点击"""
        if event.key() == Qt.Key_Escape:
            if self.engine.is_running:
                self._on_stop()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._save_config()
        self.hotkey_mgr.stop()
        self.engine.destroy()  # 先销毁引擎并等待线程结束，防止回调已删除的 Qt 对象
        super().closeEvent(event)
