"""Тёмная тема в цветах VS Code Dark+ для приложения."""

from string import Template

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Палитра, повторяющая основные цвета VS Code Dark+
COLORS = {
    "bg": "#1e1e1e",  # редактор
    "sidebar": "#252526",  # боковая панель
    "panel": "#2d2d30",
    "input": "#3c3c3c",
    "border": "#3c3c3c",
    "border_light": "#454545",
    "fg": "#cccccc",
    "fg_bright": "#e7e7e7",
    "fg_muted": "#9d9d9d",
    "accent": "#007acc",  # status bar / focus
    "button": "#0e639c",
    "button_hover": "#1177bb",
    "button_pressed": "#0a4d7a",
    "selection": "#094771",
    "hover": "#2a2d2e",
    "scrollbar": "#424242",
    "scrollbar_hover": "#4f4f4f",
    "danger": "#f48771",
}

_QSS = Template(
    """
QWidget {
    background-color: $bg;
    color: $fg;
    font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: $bg;
}

QLabel {
    background: transparent;
}

QLabel#appTitle {
    color: $fg_bright;
    font-size: 19px;
    font-weight: 600;
}

QLabel#mutedLabel {
    color: $fg_muted;
}

QGroupBox {
    background-color: $sidebar;
    border: 1px solid $border;
    border-radius: 4px;
    margin-top: 16px;
    padding: 10px 8px 8px 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: $fg_muted;
    background-color: $bg;
    font-weight: 600;
}

QPushButton {
    background-color: $input;
    border: 1px solid $border;
    border-radius: 3px;
    padding: 6px 14px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #3a3d41;
    border-color: $border_light;
}

QPushButton:pressed {
    background-color: $panel;
}

QPushButton:disabled {
    color: #6b6b6b;
    background-color: $panel;
    border-color: $border;
}

QPushButton#primaryButton {
    background-color: $button;
    border: 1px solid $button;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: $button_hover;
    border-color: $button_hover;
}

QPushButton#primaryButton:pressed {
    background-color: $button_pressed;
}

QPushButton#dangerButton {
    color: $danger;
}

QPushButton#dangerButton:hover {
    background-color: #4b2a2a;
    border-color: #6b3333;
}

QLineEdit, QComboBox {
    background-color: $input;
    border: 1px solid $border;
    border-radius: 3px;
    padding: 6px 8px;
    selection-background-color: $selection;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid $accent;
}

QLineEdit:disabled, QComboBox:disabled {
    color: $fg_muted;
}

QLineEdit#deeplinkInput {
    font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace;
    padding: 8px;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: $panel;
    border: 1px solid $border_light;
    selection-background-color: $selection;
    selection-color: #ffffff;
    outline: 0;
}

QListWidget {
    background-color: $sidebar;
    border: 1px solid $border;
    border-radius: 3px;
    padding: 4px;
    outline: 0;
}

QListWidget::item {
    padding: 5px 6px;
    border-radius: 3px;
}

QListWidget::item:hover {
    background-color: $hover;
}

QListWidget::item:selected {
    background-color: $selection;
    color: #ffffff;
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: $scrollbar;
    min-height: 24px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: $scrollbar_hover;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: $scrollbar;
    min-width: 24px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background: $scrollbar_hover;
}

QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}

QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}

QToolTip {
    background-color: $sidebar;
    color: $fg;
    border: 1px solid $border_light;
    padding: 4px 6px;
}

QMenu {
    background-color: $sidebar;
    border: 1px solid $border_light;
    padding: 4px;
}

QMenu::item {
    padding: 5px 24px 5px 12px;
    border-radius: 3px;
}

QMenu::item:selected {
    background-color: $selection;
    color: #ffffff;
}

QStatusBar {
    background-color: $accent;
    color: #ffffff;
}

QStatusBar::item {
    border: none;
}

QStatusBar QLabel {
    color: #ffffff;
    background: transparent;
}
"""
).substitute(COLORS)


def _build_palette() -> QPalette:
    palette = QPalette()
    bg = QColor(COLORS["bg"])
    sidebar = QColor(COLORS["sidebar"])
    fg = QColor(COLORS["fg"])
    muted = QColor(COLORS["fg_muted"])
    accent = QColor(COLORS["accent"])
    selection = QColor(COLORS["selection"])

    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.WindowText, fg)
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["input"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, sidebar)
    palette.setColor(QPalette.ColorRole.ToolTipBase, sidebar)
    palette.setColor(QPalette.ColorRole.ToolTipText, fg)
    palette.setColor(QPalette.ColorRole.Text, fg)
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["input"]))
    palette.setColor(QPalette.ColorRole.ButtonText, fg)
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, accent)
    palette.setColor(QPalette.ColorRole.Highlight, selection)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, muted)

    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#6b6b6b"))

    return palette


def apply_theme(app: QApplication) -> None:
    """Применяет Fusion-стиль, палитру и QSS тёмной темы VS Code."""
    app.setStyle("Fusion")
    app.setPalette(_build_palette())
    app.setStyleSheet(_QSS)
