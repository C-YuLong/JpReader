import sqlite3
import os
import json
from pathlib import Path

APP_DIR = Path(os.getenv("APPDATA", ".")) / "JpReader"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "data.db"
CONFIG_PATH = APP_DIR / "config.json"


DEFAULT_CONFIG = {
    "base_url": "https://api.deepseek.com/v1/chat/completions",
    "api_key": "",
    "model": "deepseek-chat",
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_requests": 0,
    # v4 新增
    "font_size": 18,            # 正文字号
    "line_height": 1.95,        # 行距
    "theme": "light",           # light / dark
    "jp_level": "N2",           # 日语水平
    "bg_image": "",             # 自定义背景图绝对路径
    "bg_opacity": 0.08,         # 背景透明度（0~1，越小越淡）
}



def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


class Storage:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                book_id TEXT PRIMARY KEY,
                path TEXT,
                title TEXT,
                last_chapter INTEGER DEFAULT 0,
                last_scroll INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT,
                book_title TEXT,
                chapter INTEGER,
                chapter_title TEXT,
                text TEXT,
                start_pos INTEGER DEFAULT -1,   -- 新增
                end_pos   INTEGER DEFAULT -1,   -- 新增
                color TEXT DEFAULT '#fff59d',
                ai_analysis TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 学习笔记：语法、词汇等，跨书
            CREATE TABLE IF NOT EXISTS study_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                tags TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 阅读笔记：绑定到具体书
            CREATE TABLE IF NOT EXISTS reading_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT,
                book_title TEXT,
                chapter INTEGER,
                title TEXT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cols = [r[1] for r in c.execute("PRAGMA table_info(highlights)").fetchall()]
        if "start_pos" not in cols:
            c.execute("ALTER TABLE highlights ADD COLUMN start_pos INTEGER DEFAULT -1")
        if "end_pos" not in cols:
            c.execute("ALTER TABLE highlights ADD COLUMN end_pos INTEGER DEFAULT -1")
        self.conn.commit()
        self.conn.commit()

    # --- 进度 ---
    def save_progress(self, book_id, path, title, chapter, scroll):
        self.conn.execute("""
            INSERT INTO books(book_id, path, title, last_chapter, last_scroll)
            VALUES(?,?,?,?,?)
            ON CONFLICT(book_id) DO UPDATE SET
                last_chapter=excluded.last_chapter,
                last_scroll=excluded.last_scroll,
                path=excluded.path
        """, (book_id, path, title, chapter, scroll))
        self.conn.commit()

    def get_progress(self, book_id):
        row = self.conn.execute(
            "SELECT last_chapter, last_scroll FROM books WHERE book_id=?", (book_id,)
        ).fetchone()
        return (row["last_chapter"], row["last_scroll"]) if row else (0, 0)

    # --- 高亮 ---
    def add_highlight(self, book_id, book_title, chapter, chapter_title, text,
                      start_pos=-1, end_pos=-1, color="#fff59d", ai_analysis=""):
        cur = self.conn.execute("""
            INSERT INTO highlights(book_id, book_title, chapter, chapter_title,
                                  text, start_pos, end_pos, color, ai_analysis)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (book_id, book_title, chapter, chapter_title, text,
              start_pos, end_pos, color, ai_analysis))
        self.conn.commit()
        return cur.lastrowid

    def list_highlights_for_chapter(self, book_id, chapter):
        rows = self.conn.execute("""
            SELECT * FROM highlights WHERE book_id=? AND chapter=? ORDER BY id
        """, (book_id, chapter)).fetchall()
        return [dict(r) for r in rows]


    def update_highlight_analysis(self, hid, analysis):
        self.conn.execute("UPDATE highlights SET ai_analysis=? WHERE id=?", (analysis, hid))
        self.conn.commit()

    def list_highlights(self, book_id=None):
        if book_id:
            rows = self.conn.execute(
                "SELECT * FROM highlights WHERE book_id=? ORDER BY id DESC", (book_id,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM highlights ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def delete_highlight(self, hid):
        self.conn.execute("DELETE FROM highlights WHERE id=?", (hid,))
        self.conn.commit()

    # --- 学习笔记 ---
    def add_study_note(self, title, content, tags=""):
        cur = self.conn.execute(
            "INSERT INTO study_notes(title, content, tags) VALUES(?,?,?)",
            (title, content, tags),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_study_note(self, nid, title, content, tags=""):
        self.conn.execute("""
            UPDATE study_notes SET title=?, content=?, tags=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (title, content, tags, nid))
        self.conn.commit()

    def list_study_notes(self):
        rows = self.conn.execute("SELECT * FROM study_notes ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def delete_study_note(self, nid):
        self.conn.execute("DELETE FROM study_notes WHERE id=?", (nid,))
        self.conn.commit()

    # --- 阅读笔记 ---
    def add_reading_note(self, book_id, book_title, chapter, title, content):
        cur = self.conn.execute("""
            INSERT INTO reading_notes(book_id, book_title, chapter, title, content)
            VALUES(?,?,?,?,?)
        """, (book_id, book_title, chapter, title, content))
        self.conn.commit()
        return cur.lastrowid

    def update_reading_note(self, nid, title, content):
        self.conn.execute("""
            UPDATE reading_notes SET title=?, content=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (title, content, nid))
        self.conn.commit()

    def list_reading_notes(self, book_id=None):
        if book_id:
            rows = self.conn.execute(
                "SELECT * FROM reading_notes WHERE book_id=? ORDER BY updated_at DESC", (book_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM reading_notes ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_reading_note(self, nid):
        self.conn.execute("DELETE FROM reading_notes WHERE id=?", (nid,))
        self.conn.commit()
