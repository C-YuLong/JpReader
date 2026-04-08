from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame, QLabel
from PyQt5.QtCore import Qt, pyqtSignal


class FloatingBar(QFrame):
    highlight_clicked = pyqtSignal()
    note_clicked = pyqtSignal()
    analyze_clicked = pyqtSignal()

    def __init__(self, parent=None, mode: str = "reader", theme: str = "light"):
        """
        mode='reader' 显示：高亮 | 笔记 | 解析
        mode='ai'     显示：笔记（仅一项，因为是从 AI 解析面板划选的）
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.mode = mode

        if theme == "dark":
            card_bg = "#3a3a3e"
            text_color = "#e4e4e4"
            hover_color = "#ffd66b"
            sep_color = "#666"
            shadow = "rgba(0,0,0,0.4)"
        else:
            card_bg = "#ffffff"
            text_color = "#333333"
            hover_color = "#0066cc"
            sep_color = "#ddd"
            shadow = "rgba(0,0,0,0.12)"

        self.setStyleSheet(f"""
            QFrame#card {{
                background: {card_bg};
                border-radius: 20px;
                border: 1px solid {sep_color};
            }}
            QPushButton {{
                background: transparent;
                color: {text_color};
                border: none;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: 500;
            }}
            QPushButton:hover {{ color: {hover_color}; }}
            QLabel#sep {{
                color: {sep_color};
                padding: 0;
                margin: 0;
                font-size: 16px;
            }}
        """)


        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName("card")
        outer.addWidget(self.card)

        lay = QHBoxLayout(self.card)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(0)

        def sep():
            s = QLabel("│")
            s.setObjectName("sep")
            s.setAlignment(Qt.AlignCenter)
            return s

        if mode == "reader":
            self.btn_hl = QPushButton("高亮")
            self.btn_note = QPushButton("笔记")
            self.btn_ai = QPushButton("解析")
            lay.addWidget(self.btn_hl)
            lay.addWidget(sep())
            lay.addWidget(self.btn_note)
            lay.addWidget(sep())
            lay.addWidget(self.btn_ai)
            self.btn_hl.clicked.connect(self._emit_hl)
            self.btn_note.clicked.connect(self._emit_note)
            self.btn_ai.clicked.connect(self._emit_ai)
        else:  # ai
            self.btn_note = QPushButton("记入学习笔记")
            lay.addWidget(self.btn_note)
            self.btn_note.clicked.connect(self._emit_note)

    def _emit_hl(self):
        self.hide(); self.highlight_clicked.emit()

    def _emit_note(self):
        self.hide(); self.note_clicked.emit()

    def _emit_ai(self):
        self.hide(); self.analyze_clicked.emit()

    def show_at(self, global_pos):
        self.adjustSize()
        self.move(global_pos.x() - self.width() // 2,
                  global_pos.y() - self.height() - 12)
        self.show()
        self.raise_()
