"""Shared dark palette."""

STYLESHEET = """
QMainWindow, QWidget { background: #151922; color: #e6eaf2; font-size: 13px; }
QMenuBar, QToolBar, QStatusBar { background: #1d2330; }
QMenu { background: #252d3c; }
QMenu::item:selected { background: #3a4c68; }
QToolBar { border: 0; spacing: 12px; padding: 9px; }
QPushButton, QToolButton, QComboBox { background: #2b3548; border: 1px solid #3e4b63;
    border-radius: 5px; padding: 7px 12px; }
QPushButton:hover, QToolButton:hover { background: #3b4d6b; }
QPushButton:disabled { color: #70798a; background: #222936; }
QTreeWidget, QPlainTextEdit { background: #10151e; border: 1px solid #303a4e; }
QTreeWidget::item { padding: 8px 3px; }
QTreeWidget::item:selected { background: #2c4a70; }
QHeaderView::section { background: #222b3a; padding: 8px; border: 0; }
QSlider::groove:horizontal { background: #354156; height: 5px; }
QSlider::handle:horizontal { background: #72b6ff; width: 12px; margin: -5px 0;
    border-radius: 5px; }
QSplitter::handle { background: #252d3c; width: 5px; }
QLabel#heading { font-size: 15px; font-weight: 600; padding: 6px 0; }
"""
