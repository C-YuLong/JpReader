import os
import tempfile
import hashlib
from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT
import mobi


class Chapter:
    def __init__(self, title, html, plain):
        self.title = title
        self.html = html
        self.plain = plain


class Book:
    def __init__(self, path):
        self.path = path
        self.title = os.path.basename(path)
        self.chapters: list[Chapter] = []
        self.book_id = hashlib.md5(path.encode("utf-8")).hexdigest()
        self._load()

    def _load(self):
        ext = os.path.splitext(self.path)[1].lower()
        if ext == ".epub":
            self._load_epub(self.path)
        elif ext in (".mobi", ".azw", ".azw3"):
            tmp_dir, epub_path = mobi.extract(self.path)
            # mobi 解包后会生成一个 epub 或 html 目录
            # 尝试先找 epub
            found_epub = None
            for root, _, files in os.walk(tmp_dir):
                for f in files:
                    if f.lower().endswith(".epub"):
                        found_epub = os.path.join(root, f)
                        break
            if found_epub:
                self._load_epub(found_epub)
            else:
                self._load_html_dir(tmp_dir)
        else:
            raise ValueError(f"不支持的格式: {ext}")

    def _load_epub(self, path):
        book = epub.read_epub(path)
        if book.title:
            self.title = book.title
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            html = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            plain = soup.get_text("\n", strip=True)
            if not plain.strip():
                continue
            # 取 h1/h2/title 作为章节名
            title_tag = soup.find(["h1", "h2", "h3", "title"])
            title = title_tag.get_text(strip=True) if title_tag else f"第 {len(self.chapters)+1} 章"
            self.chapters.append(Chapter(title, html, plain))

    def _load_html_dir(self, tmp_dir):
        htmls = []
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                if f.lower().endswith((".html", ".htm", ".xhtml")):
                    htmls.append(os.path.join(root, f))
        htmls.sort()
        for p in htmls:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()
            soup = BeautifulSoup(html, "html.parser")
            plain = soup.get_text("\n", strip=True)
            if not plain.strip():
                continue
            title = soup.title.string if soup.title else f"第 {len(self.chapters)+1} 章"
            self.chapters.append(Chapter(title, html, plain))
