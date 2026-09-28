"""词典查询页 + 生词本页。

词典页复刻 MOJi 浏览器插件的核心流程：
  输入/划选日语 -> 云端查词 -> 点选词条 -> 查看释义/例句 -> 收藏到生词本
未登录或登录过期时给出引导；同时提供多家在线词典直达（无需登录）。
"""

from urllib.parse import quote

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QTextBrowser, QLineEdit, QPushButton, QLabel, QMessageBox, QSplitter,
    QFileDialog,
)
from pathlib import Path

from moji_dict import MojiClient, AuthError, MojiError, ONLINE_DICTS, detail_to_markdown


class _SearchWorker(QThread):
    done = pyqtSignal(list)
    failed = pyqtSignal(str, bool)  # (msg, is_auth_error)

    def __init__(self, client: MojiClient, text: str):
        super().__init__()
        self.client = client
        self.text = text

    def run(self):
        try:
            self.done.emit(self.client.search(self.text))
        except AuthError as e:
            self.failed.emit(str(e), True)
        except Exception as e:
            self.failed.emit(str(e), False)


class _DetailWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str, bool)

    def __init__(self, client: MojiClient, tar_id: str):
        super().__init__()
        self.client = client
        self.tar_id = tar_id

    def run(self):
        try:
            self.done.emit(self.client.fetch_word(self.tar_id))
        except AuthError as e:
            self.failed.emit(str(e), True)
        except Exception as e:
            self.failed.emit(str(e), False)


class DictionaryPanel(QWidget):
    """词典查询页。"""

    login_required = pyqtSignal()  # 让主窗口跳到设置登录

    def __init__(self, client: MojiClient, storage, get_book_title=None, parent=None):
        super().__init__(parent)
        self.client = client
        self.storage = storage
        self.get_book_title = get_book_title or (lambda: "")
        self.current_detail: dict | None = None
        self.current_source = ""
        self._workers: list[QThread] = []

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)

        # 顶部：搜索行
        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入日语 / 中文 / 假名 / 罗马音查词…")
        self.search_edit.returnPressed.connect(self.do_search)
        self.btn_search = QPushButton("查询")
        self.btn_search.clicked.connect(self.do_search)
        top.addWidget(QLabel("<b>词典</b>"))
        top.addWidget(self.search_edit, 1)
        top.addWidget(self.btn_search)
        v.addLayout(top)

        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("muted")
        v.addWidget(self.status_lbl)

        # 中间：结果列表 + 详情
        splitter = QSplitter(Qt.Horizontal)
        self.result_list = QListWidget()
        self.result_list.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self.result_list)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.detail_view = QTextBrowser()
        self.detail_view.setMarkdown("*查询后点击左侧词条查看释义与例句。*")
        rv.addWidget(self.detail_view, 1)

        btn_row = QHBoxLayout()
        self.btn_collect = QPushButton("收藏到生词本")
        self.btn_collect.setEnabled(False)
        self.btn_collect.clicked.connect(self.on_collect)
        btn_row.addWidget(self.btn_collect)
        btn_row.addStretch(1)
        rv.addLayout(btn_row)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        v.addWidget(splitter, 1)

        # 底部：在线词典直达
        online = QHBoxLayout()
        online.addWidget(QLabel("在线词典："))
        for name, _tpl in ONLINE_DICTS:
            b = QPushButton(name)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, t=_tpl: self._open_online(t))
            online.addWidget(b)
        online.addStretch(1)
        v.addLayout(online)

        self._update_status()

    # ---------- 外部入口 ----------
    def lookup(self, text: str):
        """主窗口划词后调用：填入并立即查询。"""
        self.search_edit.setText(text)
        self.do_search()

    def refresh_login_state(self):
        self._update_status()

    # ---------- 查询 ----------
    def _update_status(self):
        name = self.client.config.get("moji_username", "")
        if self.client.token and name:
            self.status_lbl.setText(f"已登录 MOJi：{name}（查词额度已解锁）")
        else:
            self.status_lbl.setText(
                "未登录也可直接查词；在「文件 → 设置」中登录 MOJi 账号可解锁更高额度。"
            )

    def do_search(self):
        text = self.search_edit.text().strip()
        if not text:
            return
        self.current_source = text
        self.result_list.clear()
        self.detail_view.setMarkdown(f"*正在查询：* {text} …")
        self.btn_collect.setEnabled(False)
        self.current_detail = None
        w = _SearchWorker(self.client, text)
        w.done.connect(self._on_search_done)
        w.failed.connect(self._on_failed)
        self._run(w)

    def _on_search_done(self, items: list):
        self.detail_view.setMarkdown("*点击左侧词条查看详情。*")
        if not items:
            self.detail_view.setMarkdown("*没有找到词条，换个关键词试试，或用下方在线词典。*")
            return
        for it in items:
            label = it["title"]
            if it.get("excerpt"):
                label += f"  —  {it['excerpt'][:40]}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, it)
            self.result_list.addItem(item)
        self.result_list.setCurrentRow(0)

    def _on_select(self, cur, _prev):
        if not cur:
            return
        it = cur.data(Qt.UserRole)
        self.detail_view.setMarkdown(f"*正在加载：* {it['title']} …")
        self.btn_collect.setEnabled(False)
        w = _DetailWorker(self.client, it["tar_id"])
        w.done.connect(lambda d, tar=it["tar_id"]: self._on_detail_done(d, tar))
        w.failed.connect(self._on_failed)
        self._run(w)

    def _on_detail_done(self, d: dict, tar_id: str):
        d["_tar_id"] = tar_id
        self.current_detail = d
        self.detail_view.setMarkdown(detail_to_markdown(d))
        saved = self.storage.vocab_exists(tar_id)
        self.btn_collect.setEnabled(not saved)
        self.btn_collect.setText("已收藏" if saved else "收藏到生词本")

    def _on_failed(self, msg: str, is_auth: bool):
        self.detail_view.setMarkdown(f"**查询失败**：{msg}")
        if is_auth:
            self._update_status()
            self.login_required.emit()

    def _run(self, w: QThread):
        self._workers.append(w)

        def _cleanup():
            if w in self._workers:
                self._workers.remove(w)
            w.deleteLater()

        w.finished.connect(_cleanup)
        w.start()

    # ---------- 收藏 ----------
    def on_collect(self):
        d = self.current_detail
        if not d:
            return
        vid = self.storage.add_vocab(
            word_id=d.get("_tar_id", ""),
            title=d.get("title") or d.get("spell") or "",
            spell=d.get("spell", ""),
            excerpt=d.get("excerpt", ""),
            detail_md=detail_to_markdown(d),
            source_text=self.current_source,
            book_title=self.get_book_title(),
        )
        if vid is None:
            QMessageBox.information(self, "提示", "这个词已在生词本里。")
        self.btn_collect.setEnabled(False)
        self.btn_collect.setText("已收藏")

    # ---------- 在线词典 ----------
    def _open_online(self, tpl: str):
        q = self.search_edit.text().strip()
        if not q:
            return
        QDesktopServices.openUrl(QUrl(tpl.format(q=quote(q))))


class VocabPanel(QWidget):
    """生词本：已收藏词条的复习与管理。"""

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.current_id = None

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("<b>生词本</b>"))
        top.addStretch(1)
        self.btn_export = QPushButton("导出 Markdown")
        self.btn_del = QPushButton("删除")
        top.addWidget(self.btn_export)
        top.addWidget(self.btn_del)
        v.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        self.listw = QListWidget()
        self.listw.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self.listw)

        self.detail = QTextBrowser()
        self.detail.setMarkdown("*暂无收藏。阅读时划词 → 查词 → 收藏到生词本。*")
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        v.addWidget(splitter, 1)

        self.btn_export.clicked.connect(self.export_md)
        self.btn_del.clicked.connect(self.delete_word)
        self.refresh()

    def refresh(self):
        self.listw.clear()
        for n in self.storage.list_vocab():
            label = n["title"] or n["spell"] or "(无标题)"
            if n.get("excerpt"):
                label += f"  —  {n['excerpt'][:36]}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, n)
            self.listw.addItem(item)

    def _on_select(self, cur, _prev):
        if not cur:
            return
        n = cur.data(Qt.UserRole)
        self.current_id = n["id"]
        md = n.get("detail_md") or n.get("excerpt") or ""
        if n.get("source_text"):
            md += f"\n\n---\n<sub>来源：{n['source_text'][:80]}"
            if n.get("book_title"):
                md += f"（《{n['book_title']}》）"
            md += "</sub>"
        self.detail.setMarkdown(md or "*（无内容）*")

    def delete_word(self):
        if not self.current_id:
            return
        if QMessageBox.question(self, "确认", "从生词本删除这个词？") != QMessageBox.Yes:
            return
        self.storage.delete_vocab(self.current_id)
        self.current_id = None
        self.refresh()
        self.detail.setMarkdown("*已删除。*")

    def export_md(self):
        rows = self.storage.list_vocab()
        if not rows:
            QMessageBox.information(self, "提示", "生词本为空。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出生词本", "vocabulary.md", "Markdown (*.md)")
        if not path:
            return
        lines = ["# 生词本\n"]
        for n in rows:
            lines.append(f"\n## {n['title'] or n['spell']}")
            if n.get("detail_md"):
                lines.append(n["detail_md"])
            elif n.get("excerpt"):
                lines.append(n["excerpt"])
            if n.get("source_text"):
                lines.append(f"\n> 来源：{n['source_text']}")
            lines.append("\n---")
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        QMessageBox.information(self, "完成", f"已导出：\n{path}")
