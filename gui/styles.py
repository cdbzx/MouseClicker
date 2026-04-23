"""
QSS 样式定义 - 现代暗色主题
"""

DARK_THEME = """
QMainWindow {
    background-color: #1e1e2e;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* 分组框 */
QGroupBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    font-size: 13px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    color: #89b4fa;
}

/* 按钮 */
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #585b70;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #313244;
}

QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #45475a;
}

QPushButton#startBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-size: 15px;
    min-height: 36px;
    border: none;
}

QPushButton#startBtn:hover {
    background-color: #94e2d5;
}

QPushButton#stopBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    font-size: 15px;
    min-height: 36px;
    border: none;
}

QPushButton#stopBtn:hover {
    background-color: #eba0ac;
}

QPushButton#selectRegionBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
}

QPushButton#selectRegionBtn:hover {
    background-color: #b4befe;
}

QPushButton#deleteBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    padding: 4px 10px;
}

/* 输入框 */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #89b4fa;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #89b4fa;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    background-color: #585b70;
    border: none;
    border-radius: 2px;
    width: 16px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #585b70;
    border: none;
    border-radius: 2px;
    width: 16px;
}

/* 下拉框 */
QComboBox {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 4px;
    padding: 6px 8px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #585b70;
    selection-background-color: #45475a;
}

/* 复选框 */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #585b70;
    background-color: #45475a;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

/* 滑块 */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #45475a;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #89b4fa;
    border: none;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #b4befe;
}

/* 列表 */
QListWidget {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    background-color: #45475a;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 2px 0;
    color: #cdd6f4;
}

QListWidget::item:selected {
    background-color: #585b70;
    border: 1px solid #89b4fa;
}

QListWidget::item:hover {
    background-color: #585b70;
}

/* 标签 */
QLabel {
    color: #cdd6f4;
    background: transparent;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #89b4fa;
}

QLabel#statusLabel {
    font-size: 14px;
    font-weight: bold;
    color: #a6e3a1;
    padding: 4px 8px;
    background-color: #313244;
    border-radius: 4px;
}

QLabel#countLabel {
    font-size: 18px;
    font-weight: bold;
    color: #f9e2af;
}

/* 进度条 */
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #45475a;
    text-align: center;
    color: #cdd6f4;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}

/* 标签页 */
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 6px;
    background-color: #313244;
}

QTabBar::tab {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #313244;
    color: #89b4fa;
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #585b70;
}

/* 滚动条 */
QScrollBar:vertical {
    border: none;
    background-color: #1e1e2e;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* 工具提示 */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}

/* 日志文本 */
QTextEdit {
    background-color: #11111b;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}
"""

REGION_COLORS = [
    "#f38ba8",  # 红
    "#89b4fa",  # 蓝
    "#a6e3a1",  # 绿
    "#f9e2af",  # 黄
    "#cba6f7",  # 紫
    "#94e2d5",  # 青
    "#fab387",  # 橙
    "#f5c2e7",  # 粉
]
