import sys
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QListWidget, QTextBrowser,
    QSplitter, QAction, QTabWidget, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QPushButton, QMessageBox, QMenu, QInputDialog
)
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QIcon, QFontDatabase
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

from reader_core import Book
from storage import Storage, load_config, save_config, get_data_dir
from ai_client import AIClient
from moji_dict import MojiClient
from dictionary_panel import DictionaryPanel, VocabPanel
from settings_dialog import SettingsDialog
from notes_panel import NotesPanel
from floating_bar import FloatingBar
from ui_style import build_qss, build_reader_css


# 分主题的高亮配色
HIGHLIGHT_THEMES = {
    "light": {"bg": "#fff3a3", "fg": None},         # 荧光黄背景，文字色不变
    "dark":  {"bg": "#5c4e1e", "fg": "#f5ecc8"},     # 深琥珀背景，暖白文字
}
ASSETS_DIR = Path(__file__).parent / "assets"


def _get_highlight_colors(theme: str):
    return HIGHLIGHT_THEMES.get(theme, HIGHLIGHT_THEMES["light"])


class AIWorker(QThread):
    done = pyqtSignal(str, dict)

    def __init__(self, client, text, config, book_title):
        super().__init__()
        self.client = client
        self.text = text
        self.jp_level = config.get("jp_level", "N2")
        self.book_title = book_title

    def run(self):
        result, usage = self.client.analyze(self.text, self.jp_level, self.book_title)
        self.done.emit(result, usage)


class ReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("日语阅读")
        icon_path = ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.config = load_config()
        self._resize_for_screen()
        # 使用配置中的数据目录
        data_dir = get_data_dir(self.config)
        self.storage = Storage(data_dir / "data.db")
        self.ai = AIClient(self.config)
        self.moji = MojiClient(self.config)
        self.book: Book | None = None
        self.current_chapter = 0
        self.last_highlight_id = None

        self._build_ui()
        self._build_menu()
        self._update_status()
        self._apply_background()

        # 启动时自动恢复上次打开的书
        QTimer.singleShot(100, self._restore_last_book)

    # ---------- UI ----------
    def _resize_for_screen(self):
        """以当前屏幕的可用区域为上限，避免默认窗口挤压小屏阅读区。"""
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1380, 840)
            return
        area = screen.availableGeometry()
        width = min(1380, max(800, round(area.width() * 0.92)))
        height = min(840, max(600, round(area.height() * 0.90)))
        self.resize(min(width, area.width()), min(height, area.height()))

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(self._build_reader_tab(), "阅读")
        self.dict_panel = DictionaryPanel(
            self.moji, self.storage, get_book_title=self._current_book_title
        )
        self.dict_panel.login_required.connect(self.open_settings)
        self.tabs.addTab(self.dict_panel, "词典")
        self.vocab_panel = VocabPanel(self.storage)
        self.tabs.addTab(self.vocab_panel, "生词本")
        self.study_panel = NotesPanel(self.storage, kind="study")
        self.tabs.addTab(self.study_panel, "学习笔记")
        self.reading_panel = NotesPanel(
            self.storage, kind="reading", get_book_ctx=self._current_book_ctx
        )
        self.tabs.addTab(self.reading_panel, "阅读笔记")
        self.tabs.addTab(self._build_highlights_tab(), "高亮总览")

        self.statusBar()

    def _current_book_title(self) -> str:
        return self.book.title if self.book else ""

    def _build_reader_tab(self):
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(16, 10, 16, 12)
        outer.setSpacing(8)

        # 顶部工具条 —— 按钮用 setMinimumSize，不再 setFixedWidth
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        btn_smaller = QPushButton(" A− ")
        btn_bigger = QPushButton(" A+ ")
        btn_theme = QPushButton(
            " 深色模式 " if self.config.get("theme", "light") == "light" else " 浅色模式 "
        )
        self.btn_theme = btn_theme
        for btn in (btn_smaller, btn_bigger, btn_theme):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(32)
        btn_smaller.clicked.connect(lambda: self._change_font_size(-1))
        btn_bigger.clicked.connect(lambda: self._change_font_size(1))
        btn_theme.clicked.connect(self._toggle_theme)
        toolbar.addStretch(1)
        toolbar.addWidget(btn_smaller)
        toolbar.addWidget(btn_bigger)
        toolbar.addSpacing(10)
        toolbar.addWidget(btn_theme)
        outer.addLayout(toolbar)

        # 下方主区域
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        outer.addLayout(root, 1)

        # 左：章节
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)
        title = QLabel("目录")
        title.setObjectName("h2")
        lv.addWidget(title)
        self.chapter_list = QListWidget()
        self.chapter_list.currentRowChanged.connect(self.load_chapter)
        lv.addWidget(self.chapter_list, 1)
        left.setMaximumWidth(280)

        # 中：正文
        self.text_view = QTextBrowser()
        self.text_view.setOpenExternalLinks(False)
        self.text_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_view.customContextMenuRequested.connect(self._text_menu)
        self.text_view.selectionChanged.connect(self._on_selection_changed)

        # 浮条
        self.floating_bar = FloatingBar(
            self.text_view.viewport(), mode="reader",
            theme=self.config.get("theme", "light"),
            ui_font_size=self.config.get("ui_font_size", 15),
        )
        self.floating_bar.hide()
        self.floating_bar.highlight_clicked.connect(self.on_highlight)
        self.floating_bar.note_clicked.connect(self.on_save_as_reading_note)
        self.floating_bar.analyze_clicked.connect(self.on_analyze)
        self.floating_bar.lookup_clicked.connect(self.on_lookup)

        # 右：AI 面板
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        ai_title = QLabel("AI 解析")
        ai_title.setObjectName("h2")
        rl.addWidget(ai_title)
        self.ai_view = QTextBrowser()
        self.ai_view.setMarkdown("*划选句子后点击浮条上的「解析」。*")
        self.ai_view.selectionChanged.connect(self._on_ai_selection_changed)
        rl.addWidget(self.ai_view, 1)

        self.ai_floating_bar = FloatingBar(
            self.ai_view.viewport(), mode="ai",
            theme=self.config.get("theme", "light"),
            ui_font_size=self.config.get("ui_font_size", 15),
        )
        self.ai_floating_bar.hide()
        self.ai_floating_bar.note_clicked.connect(self.on_save_ai_selection_as_study)

        right.setMaximumWidth(440)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.text_view)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([260, 780, 400])
        splitter.setHandleWidth(6)
        root.addWidget(splitter)
        return w

    def _change_font_size(self, delta: int):
        size = int(self.config.get("font_size", 20)) + delta
        size = max(12, min(36, size))
        self.config["font_size"] = size
        save_config(self.config)
        if self.book:
            # 保持滚动位置
            scroll = self.text_view.verticalScrollBar().value()
            self.load_chapter(self.current_chapter)
            QTimer.singleShot(0, lambda: self.text_view.verticalScrollBar().setValue(scroll))

    def _rebuild_floating_bars(self):
        """浮动操作条有独立样式，界面字号或主题变化后需一并刷新。"""
        for name in ("floating_bar", "ai_floating_bar"):
            old_bar = getattr(self, name, None)
            if old_bar:
                old_bar.hide()
                old_bar.deleteLater()

        theme = self.config.get("theme", "light")
        ui_font_size = self.config.get("ui_font_size", 15)
        self.floating_bar = FloatingBar(
            self.text_view.viewport(), mode="reader", theme=theme,
            ui_font_size=ui_font_size,
        )
        self.floating_bar.hide()
        self.floating_bar.highlight_clicked.connect(self.on_highlight)
        self.floating_bar.note_clicked.connect(self.on_save_as_reading_note)
        self.floating_bar.analyze_clicked.connect(self.on_analyze)
        self.floating_bar.lookup_clicked.connect(self.on_lookup)

        self.ai_floating_bar = FloatingBar(
            self.ai_view.viewport(), mode="ai", theme=theme,
            ui_font_size=ui_font_size,
        )
        self.ai_floating_bar.hide()
        self.ai_floating_bar.note_clicked.connect(self.on_save_ai_selection_as_study)

    def _toggle_theme(self):
        new_theme = "dark" if self.config.get("theme", "light") == "light" else "light"
        self.config["theme"] = new_theme
        save_config(self.config)

        # 记住当前滚动位置
        scroll = self.text_view.verticalScrollBar().value()

        ui_fs = int(self.config.get("ui_font_size", 15))
        QApplication.instance().setStyleSheet(build_qss(new_theme, ui_fs))
        self.btn_theme.setText(" 深色模式 " if new_theme == "light" else " 浅色模式 ")

        if self.book:
            self.load_chapter(self.current_chapter)

        self._apply_background()

        # 恢复滚动位置（延迟一帧等 HTML 渲染完成）
        QTimer.singleShot(0, lambda: self.text_view.verticalScrollBar().setValue(scroll))

        self._rebuild_floating_bars()

    def _build_highlights_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)
        top = QHBoxLayout()
        lbl = QLabel("所有高亮")
        lbl.setObjectName("h1")
        top.addWidget(lbl)
        top.addStretch(1)
        btn = QPushButton("刷新")
        btn.clicked.connect(self._refresh_highlights)
        top.addWidget(btn)
        v.addLayout(top)

        self.hl_view = QTextBrowser()
        v.addWidget(self.hl_view, 1)
        self._refresh_highlights()
        return w

    def _refresh_highlights(self):
        rows = self.storage.list_highlights()
        if not rows:
            self.hl_view.setMarkdown("*暂无高亮。*")
            return
        md = []
        for r in rows:
            md.append(f"### {r['book_title']} — 第{r['chapter']+1}章")
            md.append(f"> {r['text']}\n")
            if r["ai_analysis"]:
                md.append(r["ai_analysis"])
            md.append(f"<sub>{r['created_at']}</sub>\n\n---")
        self.hl_view.setMarkdown("\n".join(md))

    def _apply_background(self):
        bg = self.config.get("bg_image", "")
        opacity = float(self.config.get("bg_opacity", 0.08))
        if not bg or not Path(bg).exists():
            self.text_view.viewport().setStyleSheet("")
            return
        path = bg.replace("\\", "/")
        theme = self.config.get("theme", "light")
        base = "255,255,255" if theme == "light" else "30,30,32"
        veil_alpha = max(0.0, 1.0 - opacity)
        self.text_view.viewport().setStyleSheet(f"""
            QWidget {{
                background-image: url("{path}");
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
        """)
        self.text_view.setStyleSheet(f"""
            QTextBrowser {{
                background: rgba({base},{veil_alpha});
                border: 1px solid transparent;
                border-radius: 8px;
            }}
        """)

    # ---------- 菜单 ----------
    def _build_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("文件")
        fm.addAction("打开电子书…", self.open_book)
        fm.addSeparator()
        fm.addAction("设置…", self.open_settings)
        fm.addSeparator()
        fm.addAction("退出", self.close)

        em = mb.addMenu("导出")
        em.addAction("高亮 → Markdown", lambda: self.export_highlights("md"))
        em.addAction("高亮 → Anki TSV", lambda: self.export_highlights("anki"))
        em.addAction("高亮 → JSON", lambda: self.export_highlights("json"))
        em.addSeparator()
        em.addAction("学习笔记 → Markdown", lambda: self.export_notes("study"))
        em.addAction("阅读笔记 → Markdown", lambda: self.export_notes("reading"))
        em.addSeparator()
        em.addAction("全部导出 (ZIP)", self.export_all)

    # ---------- 选区 / 浮条 ----------
    def _on_selection_changed(self):
        cursor = self.text_view.textCursor()
        if not cursor.hasSelection():
            self.floating_bar.hide()
            return
        QTimer.singleShot(50, self._show_reader_bar)

    def _show_reader_bar(self):
        cursor = self.text_view.textCursor()
        if not cursor.hasSelection():
            return
        rect = self.text_view.cursorRect(cursor)
        global_pt = self.text_view.viewport().mapToGlobal(rect.topRight())
        self.floating_bar.show_at(global_pt)

    def _on_ai_selection_changed(self):
        cursor = self.ai_view.textCursor()
        if not cursor.hasSelection():
            self.ai_floating_bar.hide()
            return
        QTimer.singleShot(50, self._show_ai_bar)

    def _show_ai_bar(self):
        cursor = self.ai_view.textCursor()
        if not cursor.hasSelection():
            return
        rect = self.ai_view.cursorRect(cursor)
        global_pt = self.ai_view.viewport().mapToGlobal(rect.topRight())
        self.ai_floating_bar.show_at(global_pt)

    def _selected_text(self) -> str:
        return self.text_view.textCursor().selectedText().replace("\u2029", "\n").strip()

    def _selected_text_ai(self) -> str:
        return self.ai_view.textCursor().selectedText().replace("\u2029", "\n").strip()

    def _selected_text_current(self) -> str:
        t = self._selected_text()
        if t:
            return t
        return self._selected_text_ai()

    def on_save_ai_selection_as_study(self):
        text = self._selected_text_ai()
        if not text:
            return
        title, ok = QInputDialog.getText(self, "学习笔记", "标题：", text=text[:20])
        if not ok:
            return
        self.storage.add_study_note(
            title=title or text[:20],
            content=f"{text}\n\n---\n来源：AI 解析",
            tags=self.config.get("jp_level", ""),
        )
        self.study_panel.refresh()
        self.tabs.setCurrentWidget(self.study_panel)

    def _text_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("高亮", self.on_highlight)
        menu.addAction("存为学习笔记", self.on_save_as_study)
        menu.addAction("存为阅读笔记", self.on_save_as_reading_note)
        menu.addAction("查词", self.on_lookup)
        menu.addAction("AI 解析", self.on_analyze)
        menu.exec_(self.text_view.mapToGlobal(pos))

    # ---------- 书 / 章节 ----------
    def _current_book_ctx(self):
        if not self.book:
            return ("", "", 0)
        return (self.book.book_id, self.book.title, self.current_chapter)

    def _restore_last_book(self):
        """启动时自动打开上次阅读的电子书。"""
        last_path = self.config.get("last_book_path", "")
        if not last_path or not Path(last_path).exists():
            return
        try:
            self._do_open_book(last_path)
        except Exception:
            pass  # 文件已删除或损坏，静默跳过

    def _do_open_book(self, path: str):
        """内部打开书的逻辑，open_book 和 _restore_last_book 共用。"""
        self.book = Book(path)
        self.setWindowTitle(f"{self.book.title} — 日语阅读")
        self.chapter_list.clear()
        for i, ch in enumerate(self.book.chapters):
            self.chapter_list.addItem(f"{i+1}  {ch.title[:28]}")
        ch, scroll = self.storage.get_progress(self.book.book_id)
        self.chapter_list.setCurrentRow(min(ch, len(self.book.chapters) - 1))
        # 延迟恢复滚动位置，等 HTML 渲染完
        QTimer.singleShot(50, lambda: self.text_view.verticalScrollBar().setValue(scroll))
        self.reading_panel.refresh(self.book.book_id)

        # 记住这本书的路径
        self.config["last_book_path"] = path
        save_config(self.config)

    def open_book(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开电子书", "", "电子书 (*.epub *.mobi *.azw *.azw3)"
        )
        if not path:
            return
        try:
            self._do_open_book(path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开：{e}")

    def load_chapter(self, idx):
        if not self.book or idx < 0 or idx >= len(self.book.chapters):
            return
        self.current_chapter = idx
        ch = self.book.chapters[idx]
        css = build_reader_css(
            self.config.get("theme", "light"),
            int(self.config.get("font_size", 20)),
            float(self.config.get("line_height", 1.95)),
        )
        self.text_view.setHtml(css + ch.html)
        self._replay_highlights()
        self._save_progress()

    def _replay_highlights(self):
        """重新打开时把已有高亮画回文本，颜色跟随当前主题。"""
        if not self.book:
            return
        rows = self.storage.list_highlights_for_chapter(
            self.book.book_id, self.current_chapter
        )
        doc = self.text_view.document()
        plain = self.text_view.toPlainText()

        # 根据当前主题选择高亮色
        theme = self.config.get("theme", "light")
        hl = _get_highlight_colors(theme)

        for r in rows:
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(hl["bg"]))
            if hl["fg"]:
                fmt.setForeground(QColor(hl["fg"]))
            cursor = QTextCursor(doc)
            # 优先使用保存的偏移
            if r["start_pos"] >= 0 and r["end_pos"] > r["start_pos"]:
                cursor.setPosition(r["start_pos"])
                cursor.setPosition(r["end_pos"], QTextCursor.KeepAnchor)
                if cursor.selectedText().replace("\u2029", "\n") == r["text"]:
                    cursor.mergeCharFormat(fmt)
                    continue
            # 兜底：按文本搜索
            idx = plain.find(r["text"])
            if idx >= 0:
                cursor.setPosition(idx)
                cursor.setPosition(idx + len(r["text"]), QTextCursor.KeepAnchor)
                cursor.mergeCharFormat(fmt)

    def _save_progress(self):
        if not self.book:
            return
        self.storage.save_progress(
            self.book.book_id, self.book.path, self.book.title,
            self.current_chapter,
            self.text_view.verticalScrollBar().value(),
        )

    def closeEvent(self, e):
        self._save_progress()
        save_config(self.config)
        super().closeEvent(e)

    # ---------- 动作 ----------
    def on_highlight(self):
        cursor = self.text_view.textCursor()
        if not cursor.hasSelection() or not self.book:
            return

        theme = self.config.get("theme", "light")
        hl = _get_highlight_colors(theme)

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(hl["bg"]))
        if hl["fg"]:
            fmt.setForeground(QColor(hl["fg"]))

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.mergeCharFormat(fmt)
        text = self._selected_text()
        if text:
            ch_title = self.book.chapters[self.current_chapter].title
            self.last_highlight_id = self.storage.add_highlight(
                self.book.book_id, self.book.title,
                self.current_chapter, ch_title, text,
                start_pos=start, end_pos=end, color=hl["bg"],
            )

    def on_lookup(self):
        """划词查词：跳到词典页并查询选中文本。"""
        text = self._selected_text_current()
        if not text:
            return
        self.tabs.setCurrentWidget(self.dict_panel)
        self.dict_panel.lookup(text)

    def on_analyze(self):
        text = self._selected_text_current()
        if not text:
            return
        if not self.config.get("api_key"):
            QMessageBox.warning(self, "提示", "请先在「文件 → 设置」中填写 API Key。")
            return
        self.last_analyzed_text = text
        self.ai_view.setMarkdown(f"*正在分析：* {text}\n\n请稍候…")
        self.worker = AIWorker(self.ai, text, self.config, self._current_book_title())
        self.worker.done.connect(self._on_ai_done)
        self.worker.start()

    def _on_ai_done(self, result, usage):
        self.ai_view.setMarkdown(result)
        self.config["total_prompt_tokens"] = (
            self.config.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
        )
        self.config["total_completion_tokens"] = (
            self.config.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
        )
        self.config["total_requests"] = self.config.get("total_requests", 0) + 1
        save_config(self.config)
        self._update_status()

    def on_save_as_study(self):
        text = self._selected_text()
        if not text:
            return
        title, ok = QInputDialog.getText(self, "学习笔记", "标题：", text=text[:20])
        if not ok:
            return
        self.storage.add_study_note(
            title=title or text[:20],
            content=f"> {text}\n\n（在此补充语法、用法说明）",
            tags="",
        )
        self.study_panel.refresh()
        self.tabs.setCurrentWidget(self.study_panel)

    def on_save_as_reading_note(self):
        text = self._selected_text()
        if not text or not self.book:
            return
        title, ok = QInputDialog.getText(self, "阅读笔记", "标题：", text=text[:20])
        if not ok:
            return
        self.storage.add_reading_note(
            self.book.book_id, self.book.title, self.current_chapter,
            title or text[:20],
            f"> {text}\n\n（在此写下你的想法）",
        )
        self.reading_panel.refresh(self.book.book_id)

    # ---------- 设置 / 状态 ----------
    def open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec_():
            self.config = dlg.get_config()
            save_config(self.config)
            self.ai.config = self.config
            self.moji.config = self.config
            self.dict_panel.refresh_login_state()
            self._update_status()
            self._apply_background()
            ui_fs = int(self.config.get("ui_font_size", 15))
            QApplication.instance().setStyleSheet(
                build_qss(self.config.get("theme", "light"), ui_fs)
            )
            self._rebuild_floating_bars()
            if self.book:
                scroll = self.text_view.verticalScrollBar().value()
                self.load_chapter(self.current_chapter)
                QTimer.singleShot(0, lambda: self.text_view.verticalScrollBar().setValue(scroll))

    def _update_status(self):
        total = (self.config.get("total_prompt_tokens", 0)
                 + self.config.get("total_completion_tokens", 0))
        data_dir = get_data_dir(self.config)
        self.statusBar().showMessage(
            f"  模型 {self.config.get('model','-')}    ·    "
            f"请求 {self.config.get('total_requests',0)}    ·    "
            f"tokens {total:,}    ·    "
            f"数据 {data_dir}"
        )

    # ---------- 导出 ----------
    def export_highlights(self, fmt):
        rows = self.storage.list_highlights()
        if not rows:
            QMessageBox.information(self, "提示", "暂无高亮。")
            return
        ext = {"md": "Markdown (*.md)", "anki": "Anki TSV (*.tsv)", "json": "JSON (*.json)"}[fmt]
        path, _ = QFileDialog.getSaveFileName(self, "导出高亮", "highlights", ext)
        if not path:
            return
        p = Path(path)
        if fmt == "md":
            lines = ["# 高亮导出\n"]
            by_book = {}
            for r in rows:
                by_book.setdefault(r["book_title"], []).append(r)
            for book, items in by_book.items():
                lines.append(f"\n## {book}\n")
                for r in items:
                    lines.append(f"### 第{r['chapter']+1}章 {r['chapter_title'] or ''}")
                    lines.append(f"> {r['text']}\n")
                    if r["ai_analysis"]:
                        lines.append(r["ai_analysis"])
                    lines.append("\n---\n")
            p.write_text("\n".join(lines), encoding="utf-8")
        elif fmt == "anki":
            lines = []
            for r in rows:
                f_ = r["text"].replace("\t", " ").replace("\n", "<br>")
                b_ = (r["ai_analysis"] or f"{r['book_title']} 第{r['chapter']+1}章").replace("\t", " ").replace("\n", "<br>")
                lines.append(f"{f_}\t{b_}")
            p.write_text("\n".join(lines), encoding="utf-8")
        else:
            p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(self, "完成", f"已导出：\n{p}")

    def export_notes(self, kind):
        if kind == "study":
            notes = self.storage.list_study_notes()
            default, header = "study_notes.md", "# 学习笔记\n"
        else:
            notes = self.storage.list_reading_notes()
            default, header = "reading_notes.md", "# 阅读笔记\n"
        if not notes:
            QMessageBox.information(self, "提示", "暂无笔记。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出笔记", default, "Markdown (*.md)")
        if not path:
            return
        lines = [header]
        for n in notes:
            lines.append(f"\n## {n['title'] or '(无标题)'}")
            if kind == "study" and n.get("tags"):
                lines.append(f"*标签：{n['tags']}*")
            if kind == "reading" and n.get("book_title"):
                lines.append(f"*《{n['book_title']}》 第{(n.get('chapter') or 0)+1}章*")
            lines.append("")
            lines.append(n["content"] or "")
            lines.append("\n---")
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        QMessageBox.information(self, "完成", f"已导出：\n{path}")

    def export_all(self):
        import zipfile
        path, _ = QFileDialog.getSaveFileName(
            self, "导出全部", "jp_reader_export.zip", "ZIP (*.zip)"
        )
        if not path:
            return
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("highlights.json", json.dumps(
                self.storage.list_highlights(), ensure_ascii=False, indent=2
            ))
            z.writestr("study_notes.json", json.dumps(
                self.storage.list_study_notes(), ensure_ascii=False, indent=2
            ))
            z.writestr("reading_notes.json", json.dumps(
                self.storage.list_reading_notes(), ensure_ascii=False, indent=2
            ))
        QMessageBox.information(self, "完成", f"已导出：\n{path}")


def main():
    # 必须在 QApplication 创建前启用，让 125%/150% 等系统缩放使用逻辑像素。
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    icon_path = ASSETS_DIR / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    w = ReaderWindow()
    ui_fs = int(w.config.get("ui_font_size", 15))
    app.setStyleSheet(build_qss(w.config.get("theme", "light"), ui_fs))
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
