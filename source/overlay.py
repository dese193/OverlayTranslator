from PyQt6 import QtWidgets, QtCore, QtGui
import sys
import time 

try:
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("WARNING: pywin32 modules are not installed. 'Click-through' feature will not work.")
    print("To install: pip install pywin32")

from modules import OVERLAY_POSITIONS


class OverlayWindow(QtWidgets.QWidget):
    show_text_signal = QtCore.pyqtSignal(str, bool, bool)
    copy_to_clipboard_signal = QtCore.pyqtSignal(str)

    def __init__(self, initial_width, initial_height, initial_position_key,
                 font_size, text_color, background_color, padding,
                 overlay_min_width, overlay_max_width,
                 overlay_min_height, overlay_max_height,
                 overlay_short_text_min_height, overlay_short_text_max_height,
                 overlay_display_time, overlay_positions_map):

        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.FONT_SIZE = font_size
        self.TEXT_COLOR = text_color
        self.BACKGROUND_COLOR = background_color
        self.PADDING = padding
        self.OVERLAY_MIN_WIDTH = overlay_min_width
        self.OVERLAY_MAX_WIDTH = overlay_max_width
        self.OVERLAY_MIN_HEIGHT = overlay_min_height
        self.OVERLAY_MAX_HEIGHT = overlay_max_height
        self.OVERLAY_SHORT_TEXT_MIN_HEIGHT = overlay_short_text_min_height
        self.OVERLAY_SHORT_TEXT_MAX_HEIGHT = overlay_short_text_max_height
        self.OVERLAY_DISPLAY_TIME = overlay_display_time
        self.overlay_positions_map = overlay_positions_map

        self.current_width = initial_width
        self.current_height = initial_height
        self.resize(self.current_width, self.current_height)

        self.position_key = initial_position_key

        self.label = QtWidgets.QLabel("", self)
        self.label.setStyleSheet(
            f"color: {self.TEXT_COLOR}; "
            f"font-size: {self.FONT_SIZE}px; "
            f"background-color: {self.BACKGROUND_COLOR};"
            f"padding: {self.PADDING}px;"
            "border-radius: 10px;"
        )
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.label.setWordWrap(True)
        self.label.setGeometry(0, 0, self.width(), self.height())

        self.hide()
        self.show_text_signal.connect(self.show_text)
        self.copy_to_clipboard_signal.connect(self._copy_text_to_clipboard)
        self.reposition_overlay(self.position_key)

        self.hide_timer = None 

    def resizeEvent(self, event):
        self.label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def reposition_overlay(self, position_key=None, is_test_display=False):
        valid_positions = self.overlay_positions_map

        if position_key in valid_positions:
            self.position_key = position_key
        elif not hasattr(self, 'position_key') or self.position_key not in valid_positions:
            self.position_key = "top_center"

        screen_geo = QtWidgets.QApplication.primaryScreen().geometry()

        x, y = 0, 0
        effective_width = self.width()
        effective_height = self.height()

        if self.position_key == "top_left": x, y = self.PADDING, self.PADDING
        elif self.position_key == "top_center": x, y = int((screen_geo.width() - effective_width) / 2), self.PADDING
        elif self.position_key == "top_right": x, y = screen_geo.width() - effective_width - self.PADDING, self.PADDING
        elif self.position_key == "bottom_left": x, y = self.PADDING, screen_geo.height() - effective_height - self.PADDING
        elif self.position_key == "bottom_center": x, y = int((screen_geo.width() - effective_width) / 2), screen_geo.height() - effective_height - self.PADDING
        elif self.position_key == "bottom_right": x, y = screen_geo.width() - effective_width - self.PADDING, screen_geo.height() - effective_height - self.PADDING

        self.move(x, y)

        if is_test_display:
            self.show_text("Test overlay position", is_test_display=True, is_short_message=True)
            if self.hide_timer is not None:
                self.hide_timer.stop()
            self.hide_timer = QtCore.QTimer(self)
            self.hide_timer.setSingleShot(True)
            self.hide_timer.timeout.connect(self.hide_overlay_and_clear_text)
            self.hide_timer.start(3 * 1000)

    def show_text(self, text, is_test_display=False, is_short_message=False):
        if not text.strip():
            self.hide()
            return

        self.label.setText(text)

        temp_label = QtWidgets.QLabel(text)
        temp_label.setWordWrap(True)
        temp_label.setFont(QtGui.QFont("Arial", self.FONT_SIZE))

        metrics = QtGui.QFontMetrics(temp_label.font())
        text_rect = metrics.boundingRect(QtCore.QRect(0, 0, self.OVERLAY_MAX_WIDTH - (2 * self.PADDING), 0),
                                         QtCore.Qt.TextFlag.TextWordWrap, text)

        required_width = text_rect.width() + (2 * self.PADDING)
        new_width = max(self.OVERLAY_MIN_WIDTH, min(self.OVERLAY_MAX_WIDTH, required_width))

        temp_label.setFixedWidth(new_width - (2 * self.PADDING))
        temp_label.adjustSize()
        required_height = temp_label.height()

        new_height = required_height + self.PADDING + 1
        new_height = max(self.OVERLAY_MIN_HEIGHT, new_height)

        if new_width != self.current_width or new_height != self.current_height:
            self.current_width = new_width
            self.current_height = new_height
            self.resize(self.current_width, self.current_height)
            QtWidgets.QApplication.processEvents()
            self.reposition_overlay(self.position_key)
        self.show()
        self.make_click_through()
        if self.hide_timer is not None:
            self.hide_timer.stop()
            self.hide_timer = None
        if not is_test_display:
            self.hide_timer = QtCore.QTimer(self)
            self.hide_timer.setSingleShot(True)
            self.hide_timer.timeout.connect(self.hide_overlay_and_clear_text)
            self.hide_timer.start(self.OVERLAY_DISPLAY_TIME * 1000)

    def hide_overlay_and_clear_text(self):
        self.hide()
        self.label.setText("")
        if self.hide_timer is not None:
            self.hide_timer.stop()
            self.hide_timer = None

    def make_click_through(self):
        if HAS_WIN32:
            try:
                hwnd = int(self.winId())
                style = win32api.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32api.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                         style | win32con.WS_EX_TRANSPARENT |
                                         win32con.WS_EX_LAYERED |
                                         win32con.WS_EX_TOPMOST |
                                         win32con.WS_EX_NOACTIVATE)
            except Exception as e:
                print(f"[WinAPI] Error while setting click-through: {e}")

    @QtCore.pyqtSlot(str)
    def _copy_text_to_clipboard(self, text_to_copy):
        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard:
            clipboard.setText(text_to_copy)

    def update_settings_from_config(self, new_config):
        self.FONT_SIZE = new_config["font_size"]
        self.TEXT_COLOR = new_config["text_color"]
        self.BACKGROUND_COLOR = new_config["background_color"]
        self.PADDING = new_config["padding"]
        self.OVERLAY_MIN_WIDTH = new_config["overlay_min_width"]
        self.OVERLAY_MAX_WIDTH = new_config["overlay_max_width"]
        self.OVERLAY_MIN_HEIGHT = new_config["overlay_min_height"]
        self.OVERLAY_MAX_HEIGHT = new_config["overlay_max_height"]
        self.OVERLAY_SHORT_TEXT_MIN_HEIGHT = new_config["overlay_short_text_min_height"]
        self.OVERLAY_SHORT_TEXT_MAX_HEIGHT = new_config["overlay_short_text_max_height"]
        self.OVERLAY_DISPLAY_TIME = new_config["overlay_display_time"]

        self.label.setStyleSheet(
            f"color: {self.TEXT_COLOR}; "
            f"font-size: {self.FONT_SIZE}px; "
            f"background-color: {self.BACKGROUND_COLOR};"
            f"padding-top: {self.PADDING}px;"
            f"padding-left: {self.PADDING}px;"
            f"padding-right: {self.PADDING}px;"
            f"padding-bottom: {self.PADDING // 2 + 1}px;"
            "border-radius: 10px;"
        )
        self.resize(self.current_width, self.current_height)
        self.reposition_overlay(new_config["overlay_position"])
        if self.isVisible() and self.hide_timer is not None:
            self.hide_timer.stop()
            self.hide_timer = QtCore.QTimer(self)
            self.hide_timer.setSingleShot(True)
            self.hide_timer.timeout.connect(self.hide_overlay_and_clear_text)
            self.hide_timer.start(self.OVERLAY_DISPLAY_TIME * 1000)