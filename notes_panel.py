from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QLineEdit, QPushButton, QLabel, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt


class NotesPanel(QWidget):
    """
    通用笔记面板。kind = 'study' 或 'reading'
    """
    def __init__(self, storage, kind: str, get_book_ctx=None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.kind = kind
        self.get_book_ctx = get_book_ctx  # 回调，返回 (book_id, book_title, chapter)
        self.current_id = None

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        title = "📓 学习笔记（语法·词汇）" if kind == "study" else "📖 阅读笔记"
        top.addWidget(QLabel(f"<b>{title}</b>"))
        top.addStretch(1)
        self.btn_new = QPushButton("新建")
        self.btn_save = QPushButton("保存")
        self.btn_del = QPushButton("删除")
        top.addWidget(self.btn_new)
        top.addWidget(self.btn_save)
        top.addWidget(self.btn_del)
        v.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        self.listw = QListWidget()
        self.listw.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self.listw)

        right = QWidget()
        rv = QVBoxLayout(right)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题")
        rv.addWidget(self.title_edit)
        if kind == "study":
            self.tags_edit = QLineEdit()
            self.tags_edit.setPlaceholderText("标签，逗号分隔，例如：N2,て形,助词")
            rv.addWidget(self.tags_edit)
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("在这里写笔记，支持 Markdown…")
        rv.addWidget(self.content_edit, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        v.addWidget(splitter, 1)

        self.btn_new.clicked.connect(self.new_note)
        self.btn_save.clicked.connect(self.save_note)
        self.btn_del.clicked.connect(self.delete_note)

        self.refresh()

    def refresh(self, book_id=None):
        self.listw.clear()
        if self.kind == "study":
            notes = self.storage.list_study_notes()
        else:
            notes = self.storage.list_reading_notes(book_id)
        for n in notes:
            label = n["title"] or "(无标题)"
            if self.kind == "reading" and n.get("book_title"):
                label = f"[{n['book_title'][:10]}] {label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, n)
            self.listw.addItem(item)

    def _on_select(self, cur, _prev):
        if not cur:
            return
        n = cur.data(Qt.UserRole)
        self.current_id = n["id"]
        self.title_edit.setText(n["title"] or "")
        self.content_edit.setPlainText(n["content"] or "")
        if self.kind == "study":
            self.tags_edit.setText(n.get("tags", "") or "")

    def new_note(self):
        self.current_id = None
        self.title_edit.clear()
        self.content_edit.clear()
        if self.kind == "study":
            self.tags_edit.clear()
        self.title_edit.setFocus()

    def save_note(self):
        title = self.title_edit.text().strip() or "(无标题)"
        content = self.content_edit.toPlainText()
        if self.kind == "study":
            tags = self.tags_edit.text().strip()
            if self.current_id:
                self.storage.update_study_note(self.current_id, title, content, tags)
            else:
                self.current_id = self.storage.add_study_note(title, content, tags)
        else:
            book_id, book_title, chapter = ("", "", 0)
            if self.get_book_ctx:
                book_id, book_title, chapter = self.get_book_ctx()
            if self.current_id:
                self.storage.update_reading_note(self.current_id, title, content)
            else:
                self.current_id = self.storage.add_reading_note(
                    book_id, book_title, chapter, title, content
                )
        self.refresh()
        QMessageBox.information(self, "已保存", "笔记已保存。")

    def delete_note(self):
        if not self.current_id:
            return
        if QMessageBox.question(self, "确认", "删除这条笔记？") != QMessageBox.Yes:
            return
        if self.kind == "study":
            self.storage.delete_study_note(self.current_id)
        else:
            self.storage.delete_reading_note(self.current_id)
        self.current_id = None
        self.new_note()
        self.refresh()
