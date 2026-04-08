import json
import requests


def build_system_prompt(jp_level: str = "N2", book_title: str = "") -> str:
    level_hint = {
        "N5": "学习者是日语初学者（N5 水平），请用最基础的语法术语，对所有汉字都标注假名，解释要非常详细。",
        "N4": "学习者处于 N4 水平，基础语法已掌握，请对中级以上汉字标注假名。",
        "N3": "学习者处于 N3 水平，请重点讲解中级语法和惯用表达。",
        "N2": "学习者处于 N2 水平，请聚焦于 N2/N1 语法点、书面语、惯用句型，常用汉字无需标假名。",
        "N1": "学习者处于 N1 水平，请重点解析高级语法、古语残留、文学性表达与微妙语感差异。",
    }.get(jp_level, "")

    book_line = f"当前阅读的书是《{book_title}》。" if book_title else ""

    return f"""你是一位资深日语老师。{book_line}{level_hint}

请对用户提供的日语句子进行解析，用中文按以下 Markdown 格式回答：

### 1. 原文（汉字标注假名）
使用 `汉字[假名]` 的格式标注读音（根据学习者水平决定标注密度）。

### 2. 逐词分解
| 词 | 原形 | 词性 | 含义 |

### 3. 语法点
列出句中使用的语法结构并解释。若是该水平的重点语法请特别指出。

### 4. 整句翻译

### 5. 学习提示
1~2 条针对该学习者水平的实用提示。
"""


class AIClient:
    def __init__(self, config: dict):
        self.config = config

    def analyze(self, sentence: str, jp_level: str = "N2", book_title: str = ""):
        """返回 (text, usage_dict)"""
        headers = {
            "Authorization": f"Bearer {self.config.get('api_key','')}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config["model"],
            "messages": [
                {"role": "system", "content": build_system_prompt(jp_level, book_title)},
                {"role": "user", "content": sentence},
            ],
            "temperature": 0.3,
            "stream": False,
        }
        try:
            r = requests.post(self.config["base_url"], headers=headers,
                              data=json.dumps(payload), timeout=90)
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {}) or {}
            return text, {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }
        except Exception as e:
            return f"**请求失败**：{e}", {"prompt_tokens": 0, "completion_tokens": 0}
