def build_qss(theme: str = "light") -> str:
    if theme == "dark":
        bg = "#1e1e20"
        surface = "#2a2a2d"
        border = "#3a3a3e"
        text = "#e4e4e4"
        sub = "#9a9a9a"
        hover = "#35353a"
        accent = "#e4e4e4"
        accent_bg = "#3a3a3e"
        selbg = "#5a4a1f"
        status_bg = "#242427"
    else:
        bg = "#fafafa"
        surface = "#ffffff"
        border = "#ececec"
        text = "#2b2b2b"
        sub = "#888888"
        hover = "#f4f4f4"
        accent = "#2b2b2b"
        accent_bg = "#ececec"
        selbg = "#ffe082"
        status_bg = "#f4f4f4"

    return f"""
* {{
    font-family: "Inter", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    color: {text};
}}
QMainWindow, QDialog, QWidget {{ background: {bg}; }}

QTabWidget::pane {{ border: none; background: {bg}; }}
QTabBar::tab {{
    background: transparent; padding: 10px 20px; margin-right: 4px;
    color: {sub}; border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {text}; border-bottom: 2px solid {accent}; }}
QTabBar::tab:hover {{ color: {text}; }}

QListWidget {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px;
    padding: 6px; outline: 0;
}}
QListWidget::item {{ padding: 8px 10px; border-radius: 6px; color: {text}; }}
QListWidget::item:selected {{ background: {accent_bg}; }}
QListWidget::item:hover {{ background: {hover}; }}

QTextBrowser, QTextEdit, QLineEdit {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px;
    padding: 10px; selection-background-color: {selbg}; selection-color: #000;
    color: {text};
}}

QPushButton {{
    background: {surface}; border: 1px solid {border}; border-radius: 6px;
    padding: 7px 14px; color: {text};
}}
QPushButton:hover {{ background: {hover}; }}
QPushButton:pressed {{ background: {accent_bg}; }}

QLabel#h1 {{ font-size: 18px; font-weight: 600; color: {text}; }}
QLabel#h2 {{ font-size: 14px; font-weight: 600; color: {text}; }}
QLabel#muted {{ color: {sub}; }}

QMenuBar {{ background: {bg}; border-bottom: 1px solid {border}; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; }}
QMenuBar::item:selected {{ background: {accent_bg}; border-radius: 4px; }}

QMenu {{ background: {surface}; border: 1px solid {border}; border-radius: 6px; padding: 4px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 4px; color: {text}; }}
QMenu::item:selected {{ background: {accent_bg}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {sub}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QStatusBar {{ background: {status_bg}; color: {sub}; border-top: 1px solid {border}; }}

QComboBox {{
    background: {surface}; border: 1px solid {border}; border-radius: 6px;
    padding: 6px 10px; color: {text};
}}
QComboBox QAbstractItemView {{
    background: {surface}; border: 1px solid {border}; color: {text};
    selection-background-color: {accent_bg};
}}

QGroupBox {{
    border: 1px solid {border}; border-radius: 8px; margin-top: 14px;
    padding-top: 10px; background: {surface};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 12px; padding: 0 6px;
    color: {sub}; font-weight: 600;
}}

QSlider::groove:horizontal {{
    height: 4px; background: {border}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {accent}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}}
"""


def build_reader_css(theme: str = "light", font_size: int = 18, line_height: float = 1.95) -> str:
    if theme == "dark":
        color = "#e4e4e4"
        bg = "transparent"
        h_color = "#f0f0f0"
        rt_color = "#aaaaaa"
    else:
        color = "#2b2b2b"
        bg = "transparent"
        h_color = "#111111"
        rt_color = "#888888"

    return f"""
<style>
  body {{
    font-family: "Source Han Serif SC","Source Han Serif","Noto Serif CJK JP",
                 "Yu Mincho","MS Mincho","Hiragino Mincho ProN",serif;
    font-size: {font_size}px;
    line-height: {line_height};
    color: {color};
    background: {bg};
    padding: 20px 40px;
    max-width: 780px;
    margin: 0 auto;
  }}
  p {{ margin: 0.9em 0; }}
  h1,h2,h3,h4 {{ font-weight: 600; color: {h_color}; }}
  ruby rt {{ font-size: 0.55em; color: {rt_color}; }}
</style>
"""
