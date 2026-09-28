"""MOJi辞書（mojidict.com）查词封装。

2026-09 服务端改版后的新架构（旧 Parse 云函数 search_v3/fetchWord_v2 已下线）：
- 查词：GET /app/mojidict/api/v2/search/all?text=...&types=102&highlight=true
  types 是数字枚举（word=102），传字符串会静默返回 {}
- 详情：GET /app/mojidict/api/v1/word/detailInfo?wordId=...
- 请求头：X-MOJI-DEVICE-ID / x-MOJI-APP-ID(com.mojitec.mojidict) /
  X-MOJI-OS(PCWeb) / X-MOJI-APP-VERSION / X-MOJI-TOKEN(可空)
- 未登录也可查词；登录（Parse /parse/login）后带 X-MOJI-TOKEN 可提高额度。

词条结构：word(拼写/读音/音调/摘要) + subdetails(中文义项+日文释义交替)
+ examples(按 subdetailsId 关联)。
"""

import json
import uuid
from urllib.parse import urlencode

import requests

GATEWAY = "https://api.mojidict.com/app/mojidict"
PARSE_BASE = "https://api.mojidict.com/parse"
PARSE_APP_ID = "E62VyFVLMiW7kvbtVq3p"
MOJI_APP_ID = "com.mojitec.mojidict"
APP_VERSION = "4.18.3"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TIMEOUT = 20

TYPE_WORD = 102  # 搜索类型枚举：词条


class MojiError(Exception):
    """MOJi 接口一般性错误。"""


class AuthError(MojiError):
    """未登录或 token 已过期。"""


# ---------- 词条详情解析 ----------

def parse_word_detail(res: dict) -> dict:
    """detailInfo 响应 -> 易渲染结构。

    subdetails 里 zh-CN 与 ja 条目交替出现：zh-CN 是中文义项，
    紧随其后 lang=ja 的是该义项的日文释义。examples 按 subdetailsId 挂到义项上。
    """
    word = res.get("word") or {}
    subs = res.get("subdetails") or []
    exs = res.get("examples") or []

    ex_by_sub: dict[str, list] = {}
    for e in exs:
        t = (e.get("title") or "").strip()
        if t:
            ex_by_sub.setdefault(e.get("subdetailsId"), []).append(t)

    meanings = []
    for s in subs:
        title = (s.get("title") or "").strip()
        if not title:
            continue
        sid = s.get("objectId") or s.get("relaId") or s.get("id") or ""
        if s.get("lang") == "ja":
            if meanings and not meanings[-1].get("ja_gloss"):
                meanings[-1]["ja_gloss"] = title
            continue
        meanings.append({
            "title": title,
            "ja_gloss": "",
            "examples": ex_by_sub.get(sid, [])[:3],
        })

    return {
        "object_id": word.get("objectId") or word.get("id") or "",
        "title": word.get("spell") or "",
        "spell": word.get("spell") or "",
        "pron": word.get("pron") or "",
        "accent": word.get("accent") or "",
        "romaji": word.get("romaji") or "",
        "excerpt": word.get("excerpt") or "",
        "excerpt_b": word.get("excerptB") or "",
        "tags": (word.get("tags") or "").replace("#", " · "),
        "meanings": meanings,
    }


def detail_to_markdown(d: dict) -> str:
    """词条详情 -> Markdown，用于详情视图与生词本导出。"""
    lines = []
    head = d.get("spell") or d.get("title") or ""
    if d.get("pron") and d["pron"] != head:
        head = f"{head} | {d['pron']}"
    if d.get("accent"):
        head = f"{head} {d['accent']}"
    lines.append(f"## {head}")

    meta = []
    if d.get("romaji"):
        meta.append(d["romaji"])
    if d.get("tags"):
        meta.append(d["tags"])
    if meta:
        lines.append(f"*{' · '.join(meta)}*")

    excerpt = d.get("excerpt") or d.get("excerpt_b") or ""
    if excerpt:
        lines.append(f"\n> {excerpt}")

    meanings = d.get("meanings") or []
    if meanings:
        lines.append("\n**释义**")
        for i, m in enumerate(meanings, 1):
            lines.append(f"{i}. {m['title']}")
            if m.get("ja_gloss"):
                lines.append(f"   {m['ja_gloss']}")
            for ex in m.get("examples") or []:
                lines.append(f"   - {ex}")
    return "\n".join(lines)


# ---------- 客户端 ----------

class MojiClient:
    """持有 config 引用，token 变更后调用方负责 save_config。"""

    def __init__(self, config: dict):
        self.config = config

    # ---------- 账号（登录仅用于提高额度，查词本身无需登录） ----------
    @property
    def token(self) -> str:
        return self.config.get("moji_session_token", "")

    @property
    def device_id(self) -> str:
        did = self.config.get("moji_installation_id", "")
        if not did:
            did = str(uuid.uuid4())
            self.config["moji_installation_id"] = did
        return did

    def login(self, username: str, password: str):
        """Parse 登录。返回 (session_token, user_info)。失败抛 MojiError。"""
        r = requests.post(
            f"{PARSE_BASE}/login",
            headers={
                "X-Parse-Application-Id": PARSE_APP_ID,
                "Content-Type": "application/json",
                "User-Agent": UA,
            },
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
        data = r.json()
        token = data.get("sessionToken")
        if token:
            self.config["moji_session_token"] = token
            self.config["moji_username"] = data.get("username", username)
            return token, data
        raise MojiError(data.get("error") or f"登录失败 (code {data.get('code')})")

    def logout(self):
        self.config["moji_session_token"] = ""
        self.config["moji_username"] = ""

    # ---------- 查词 ----------
    def _headers(self) -> dict:
        h = {
            "X-MOJI-DEVICE-ID": self.device_id,
            "x-MOJI-APP-ID": MOJI_APP_ID,
            "X-MOJI-OS": "PCWeb",
            "X-MOJI-APP-VERSION": APP_VERSION,
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
        }
        if self.token:
            h["X-MOJI-TOKEN"] = self.token
            h["X-MOJI-SESSION-ID"] = self.token
        return h

    def _get(self, path: str, params: dict) -> dict:
        url = f"{GATEWAY}{path}?{urlencode(params)}"
        try:
            r = requests.get(url, headers=self._headers(), timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise MojiError(f"网络错误：{e}") from e
        except ValueError as e:
            raise MojiError("接口返回异常，可能是服务端调整。") from e
        if not isinstance(data, dict):
            raise MojiError("接口返回异常。")
        return data

    def search(self, text: str, limit: int = 12) -> list[dict]:
        """查词（假名/中日/罗马音自动识别）。返回 [{title, excerpt, tar_id}]。"""
        data = self._get("/api/v2/search/all", {
            "text": text,
            "types": TYPE_WORD,
            "highlight": "true",
        })
        items = []
        for it in ((data.get("word") or {}).get("list") or [])[:limit]:
            tar = it.get("targetId", "")
            if not tar or "http" in tar:
                continue
            items.append({
                "title": (it.get("title") or "").replace("◎", "⓪"),
                "excerpt": it.get("excerpt") or "",
                "tar_id": tar,
                "type": it.get("targetType", TYPE_WORD),
            })
        return items

    def fetch_word(self, tar_id: str) -> dict:
        """取词条详情，返回 parse_word_detail 的结构。"""
        data = self._get("/api/v1/word/detailInfo", {"wordId": tar_id})
        if not data.get("word"):
            raise MojiError("没有找到该词条的详情。")
        return parse_word_detail(data)


# ---------- 在线词典直达（浏览器插件同款，无需登录） ----------
ONLINE_DICTS = [
    ("Weblio 日中", "https://www.weblio.jp/content/{q}"),
    ("Jisho 日英", "https://jisho.org/search/{q}"),
    ("Kotobank 日日", "https://kotobank.jp/gs/?q={q}"),
    ("Google 翻译", "https://translate.google.com/?sl=ja&tl=zh-CN&text={q}"),
]
