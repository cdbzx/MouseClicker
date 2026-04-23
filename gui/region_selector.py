"""
区域选择器 - 全屏透明覆盖层，支持鼠标框选区域
使用 Win32 GetCursorPos 获取物理像素坐标，解决 DPI 缩放偏移问题
"""

import ctypes
import ctypes.wintypes
from PyQt5.QtWidgets import QWidget, QApplication, QLabel
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QCursor


def _get_physical_cursor_pos():
    """通过 Win32 API 获取鼠标物理像素坐标（不受 DPI 缩放影响）"""
    point = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return (point.x, point.y)


def _get_dpi_scale():
    """获取主屏幕 DPI 缩放比例（不修改进程 DPI 感知，避免与 Qt 冲突）"""
    screen = QApplication.primaryScreen()
    if screen:
        return screen.devicePixelRatio()
    return 1.0


class RegionSelector(QWidget):
    """
    全屏透明覆盖层 - 鼠标拖拽框选区域

    坐标系说明：
      - _start_phys / _end_phys: 物理像素坐标（传给点击引擎，与 pyautogui/Win32 一致）
      - _start_logical / _end_logical: 逻辑像素坐标（Qt 绘图用）
      - region_selected 信号发射物理坐标
    """
    region_selected = pyqtSignal(int, int, int, int)  # 物理像素 x1, y1, x2, y2
    selection_cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        # 物理像素坐标（真实屏幕坐标）
        self._start_phys = (0, 0)
        self._end_phys = (0, 0)
        # 逻辑像素坐标（Qt 绘图坐标）
        self._start_logical = QPoint()
        self._end_logical = QPoint()
        self._selecting = False
        self._dpi_scale = 1.0
        self._setup_ui()

    def _setup_ui(self):
        # 获取所有屏幕的总区域（逻辑像素）
        screen_geo = QApplication.primaryScreen().geometry()
        for screen in QApplication.screens():
            screen_geo = screen_geo.united(screen.geometry())

        self.setGeometry(screen_geo)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setMouseTracking(True)

    def start_selection(self):
        """开始区域选择"""
        self._selecting = False
        self._start_phys = (0, 0)
        self._end_phys = (0, 0)
        self._start_logical = QPoint()
        self._end_logical = QPoint()
        self._dpi_scale = _get_dpi_scale()
        self.showFullScreen()
        self.activateWindow()
        self.raise_()

    def _capture_pos(self, event):
        """同时捕获物理坐标和逻辑坐标"""
        phys = _get_physical_cursor_pos()
        logical = event.globalPos()
        return phys, logical

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            phys, logical = self._capture_pos(event)
            self._start_phys = phys
            self._end_phys = phys
            self._start_logical = logical
            self._end_logical = logical
            self._selecting = True
            self.update()
        elif event.button() == Qt.RightButton:
            self.selection_cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event):
        if self._selecting:
            phys, logical = self._capture_pos(event)
            self._end_phys = phys
            self._end_logical = logical
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            phys, logical = self._capture_pos(event)
            self._end_phys = phys
            self._end_logical = logical

            # 用物理坐标计算真实区域（传给点击引擎）
            px1 = min(self._start_phys[0], self._end_phys[0])
            py1 = min(self._start_phys[1], self._end_phys[1])
            px2 = max(self._start_phys[0], self._end_phys[0])
            py2 = max(self._start_phys[1], self._end_phys[1])

            # 最小区域检查（物理像素）
            if (px2 - px1) > 10 and (py2 - py1) > 10:
                self.region_selected.emit(px1, py1, px2, py2)
            else:
                self.selection_cancelled.emit()

            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.selection_cancelled.emit()
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 半透明背景
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if not self._start_logical.isNull() and (self._selecting or not self._end_logical.isNull()):
            # 使用逻辑坐标绘制（Qt 绘图坐标系）
            lx1 = min(self._start_logical.x(), self._end_logical.x())
            ly1 = min(self._start_logical.y(), self._end_logical.y())
            lx2 = max(self._start_logical.x(), self._end_logical.x())
            ly2 = max(self._start_logical.y(), self._end_logical.y())

            sel_rect = QRect(lx1, ly1, lx2 - lx1, ly2 - ly1)

            # 清除选中区域的半透明遮罩（让选中区域透明）
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(sel_rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # 选区边框
            pen = QPen(QColor("#89b4fa"), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(sel_rect)

            # 角标
            corner_size = 12
            corner_pen = QPen(QColor("#89b4fa"), 3, Qt.SolidLine)
            painter.setPen(corner_pen)
            corners = [
                (lx1, ly1, corner_size, 0, 0, corner_size),
                (lx2, ly1, -corner_size, 0, 0, corner_size),
                (lx1, ly2, corner_size, 0, 0, -corner_size),
                (lx2, ly2, -corner_size, 0, 0, -corner_size),
            ]
            for cx, cy, dx1, dy1, dx2, dy2 in corners:
                painter.drawLine(cx, cy, cx + dx1, cy + dy1)
                painter.drawLine(cx, cy, cx + dx2, cy + dy2)

            # 显示物理像素坐标（真实点击位置）
            px1 = min(self._start_phys[0], self._end_phys[0])
            py1 = min(self._start_phys[1], self._end_phys[1])
            px2 = max(self._start_phys[0], self._end_phys[0])
            py2 = max(self._start_phys[1], self._end_phys[1])
            pw = px2 - px1
            ph = py2 - py1

            scale_info = f"  [缩放: {self._dpi_scale:.0%}]" if self._dpi_scale != 1.0 else ""
            info_text = f"{pw} × {ph}  ({px1}, {py1}) → ({px2}, {py2}){scale_info}"

            font = QFont("Microsoft YaHei", 11)
            font.setBold(True)
            painter.setFont(font)

            # 信息背景
            fm = painter.fontMetrics()
            text_rect = fm.boundingRect(info_text)
            bg_rect = QRect(
                lx1, ly1 - text_rect.height() - 12,
                text_rect.width() + 20, text_rect.height() + 8
            )
            if bg_rect.y() < 0:
                bg_rect.moveTop(ly2 + 4)

            painter.fillRect(bg_rect, QColor(30, 30, 46, 220))
            painter.setPen(QColor("#cdd6f4"))
            painter.drawText(bg_rect, Qt.AlignCenter, info_text)

        # 提示文字
        if not self._selecting:
            hint = "拖拽鼠标框选区域  |  ESC 取消  |  右键取消"
            font = QFont("Microsoft YaHei", 14)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 180))
            painter.drawText(self.rect(), Qt.AlignHCenter | Qt.AlignTop,
                             "\n\n" + hint)

        painter.end()
