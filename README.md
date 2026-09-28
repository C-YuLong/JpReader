<div align="center">

# ✨ JpReader AI
### A beautiful Japanese eBook reader with AI grammar analysis

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="PyQt5" src="https://img.shields.io/badge/PyQt5-Desktop_App-41CD52?style=for-the-badge&logo=qt&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white">
  <img alt="AI Powered" src="https://img.shields.io/badge/AI-Powered-black?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge">
</p>

<p align="center">
  Read Japanese books beautifully, highlight sentences, ask AI to explain grammar, and turn reading into structured learning.
</p>

</div>

---

## 🌙 Overview

**JpReader AI** is a desktop Japanese eBook reader built for learners who want more than just reading.

It supports **EPUB / MOBI**, lets you **highlight text**, write **reading notes**, keep **study notes**, and send selected Japanese sentences to an **AI model** for grammar breakdown, translation, reading hints, and usage explanations.

It is designed for a smooth workflow:

> **Read → Highlight → Ask AI → Save Notes → Export for review**

---

## ⚡ Features

### 📚 eBook Reading
- Open **EPUB / MOBI / AZW / AZW3**
- Clean desktop reading experience on Windows
- Restore last reading position automatically
- Chapter navigation for long books

### 🖍 Highlight & Annotation
- Select any sentence or paragraph
- Add highlight marks and keep them persistent
- Save reading notes linked to a specific book and chapter
- Review all highlights in one place

### 🧠 AI Grammar Analysis
- Send selected Japanese text to an AI model
- Get:
  - sentence breakdown
  - grammar explanations
  - word-level meaning
  - kana / reading hints
  - full translation
  - learning tips
- Supports OpenAI-compatible endpoints

### 📖 MOJi Dictionary Integration（MOJi辞書）
- 与 MOJi辞書 浏览器插件同源的查词体验，无需浏览器
- **划词查词**：阅读时选中文本 → 浮条点「查词」→ 自动跳转词典页查询
- **云端查词**：假名、中日英、罗马音自动识别（调用 mojidict.com 官方接口）
- **词条详情**：释义、音调（⓪①②…）、词性、日文释义、例句与翻译
- **账号登录（可选）**：未登录也能查词；在「设置」中登录 MOJi 账号可解锁更高查词额度，本地只保存登录 token
- **生词本**：一键收藏词条，含完整释义与例句，支持删除与导出 Markdown
- **在线词典直达**：Weblio / Jisho / Kotobank / Google 翻译一键跳转（无需登录）

### 📝 Notes System
- **Study Notes**: grammar / vocabulary / reusable language notes
- **Reading Notes**: notes tied to a specific book and chapter
- Export notes for review or external organization

### 📤 Export Support
- Export highlights as:
  - Markdown
  - JSON
  - Anki TSV
- Export notes as Markdown
- Export all data as ZIP archive

### ⚙ Settings & Usage Tracking
- Configure:
  - API Base URL
  - API Key
  - Model name
  - JLPT level
- Track:
  - total requests
  - prompt tokens
  - completion tokens
  - total token usage

---

## 🖼 Preview

> Replace these with your own screenshots later.

```text
[ Home / Reader View ]
┌──────────────────────────────────────────────────────────────┐
│ Chapters │               Reading Area              │ AI Box │
│          │  Select sentence → highlight / analyze  │        │
└──────────────────────────────────────────────────────────────┘
````

```text
[ AI Analysis ]
- Original sentence
- Reading / kana
- Vocabulary breakdown
- Grammar patterns
- Translation
- Learning tips
```

---

## 🚀 Why this project?

Most eBook readers are made for reading.

**JpReader AI** is made for **learning through reading**.

Instead of constantly switching between:

* eBook reader
* dictionary
* grammar search
* note app
* flashcard tool

you keep everything in one focused workflow.

---

## 🧩 Tech Stack

* **Python**
* **PyQt5** — desktop UI
* **ebooklib** — EPUB parsing
* **BeautifulSoup4** — HTML extraction
* **mobi** — MOBI extraction / conversion
* **SQLite** — local storage for progress, notes, highlights
* **Requests** — AI API calls
* **PyInstaller** — packaging to `.exe`

---

## 📂 Project Structure

```bash
reader/
├── main.py
├── reader_core.py
├── ai_client.py
├── moji_dict.py          # MOJi辞書 查词/登录封装
├── dictionary_panel.py   # 词典页 + 生词本页
├── storage.py
├── settings_dialog.py
├── notes_panel.py
├── floating_bar.py
├── ui_style.py
├── assets/
│   └── icon.ico
└── requirements.txt
```

---

## 🛠 Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourname/jpreader-ai.git
cd jpreader-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run locally

```bash
python main.py
```

---

## 📦 Build EXE for Windows

Install PyInstaller first:

```bash
pip install pyinstaller
```

Build:

```bash
pyinstaller --noconfirm --onefile --windowed ^
  --name JpReader ^
  --icon assets\icon.ico ^
  --add-data "assets;assets" ^
  --collect-all ebooklib ^
  --collect-all mobi ^
  main.py
```

After build, the executable will be generated in:

```bash
dist/JpReader.exe
```

---

## 🤖 AI Configuration

This project uses an **OpenAI-compatible API interface**.

You can connect it to:

* OpenAI
* DeepSeek
* Moonshot
* local Ollama
* any compatible endpoint

Typical config fields:

* `base_url`
* `api_key`
* `model`

The AI system prompt can include:

* current **JLPT level**
* current **book title**
* selected **Japanese sentence**

So the analysis feels more contextual and useful.

---

## 🧠 Example Workflow

1. Open a Japanese eBook
2. Select an interesting sentence
3. Click **Analyze**
4. Read the AI explanation
5. Select key parts from the explanation
6. Save them into **Study Notes**
7. Export important content to Markdown / Anki

---

## 📤 Export Formats

### Highlights

* `Markdown`
* `JSON`
* `Anki TSV`

### Notes

* `Markdown`

### Full Data Backup

* `ZIP`

This makes it easy to:

* review notes later
* migrate your study archive
* turn highlights into flashcards

---

## 💡 Ideal Users

This app is built for:

* Japanese learners reading native books
* JLPT learners
* people who want to combine **extensive reading** with **deep grammar study**
* anyone who wants a clean desktop reading workflow with AI assistance

---

## 🔐 Local Data

The app stores local data such as:

* reading progress
* highlights
* notes
* usage config

Typically under:

```bash
%APPDATA%\JpReader\
```

---

## 📜 License

MIT License

---

## 🙌 Contributing

Issues and pull requests are welcome.

If you want to contribute, ideas include:

* UI improvements
* typography and theme support
* parser robustness
* local NLP integration
* annotation UX polishing

---

<div align="center">

### If this project helps your Japanese reading journey, give it a ⭐

</div>
```
