"""
工程级连点器 v1.0
启动入口

功能：
  - F6 启动/停止
  - F7 暂停/恢复
  - F8 紧急停止
  - F9 框选区域
  - 多区域点击（顺序/随机/加权）
  - 贝塞尔曲线鼠标移动
  - 真人行为模拟（抖动、疲劳、随机暂停）
  - 后台点击（Win32 API）
  - 配置持久化
"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from gui.main_window import MainWindow
from gui.styles import DARK_THEME


def main():
    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
