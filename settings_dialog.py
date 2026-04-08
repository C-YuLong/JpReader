from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMessageBox, QGroupBox, QComboBox, QWidget, QSlider, QFileDialog
)
from PyQt5.QtCore import Qt



PRESET_ENDPOINTS = {
    "DeepSeek":   ("https://api.deepseek.com/v1/chat/completions", "deepseek-chat"),
    "OpenAI":     ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    "Moonshot":   ("https://api.moonshot.cn/v1/chat/completions", "moonshot-v1-8k"),
    "Ollama本地": ("http://localhost:11434/v1/chat/completions", "qwen2.5:7b"),
    "自定义":     ("", ""),
}


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(520, 460)
        self.config = config.copy()

        layout = QVBoxLayout(self)

        # --- API 配置 ---
        api_box = QGroupBox("API 配置")
        form = QFormLayout(api_box)

        self.preset = QComboBox()
        self.preset.addItems(PRESET_ENDPOINTS.keys())
        self.preset.currentTextChanged.connect(self._on_preset)
        form.addRow("服务商预设：", self.preset)

        self.base_url = QLineEdit(self.config.get("base_url", ""))
        self.api_key = QLineEdit(self.config.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.Password)
        self.model = QLineEdit(self.config.get("model", ""))

        form.addRow("Base URL：", self.base_url)
        form.addRow("API Key：", self.api_key)
        form.addRow("模型名：", self.model)

        from PyQt5.QtWidgets import QComboBox as _QComboBox
        self.jp_level = _QComboBox()
        self.jp_level.addItems(["N5", "N4", "N3", "N2", "N1"])
        self.jp_level.setCurrentText(self.config.get("jp_level", "N2"))
        form.addRow("日语水平：", self.jp_level)

        layout.addWidget(api_box)


        # --- 用量统计 ---
        usage_box = QGroupBox("用量统计")
        ul = QFormLayout(usage_box)
        self.lbl_model = QLabel(self.config.get("model", "-"))
        self.lbl_req = QLabel(str(self.config.get("total_requests", 0)))
        self.lbl_pt = QLabel(f"{self.config.get('total_prompt_tokens', 0):,}")
        self.lbl_ct = QLabel(f"{self.config.get('total_completion_tokens', 0):,}")
        total = (self.config.get("total_prompt_tokens", 0)
                 + self.config.get("total_completion_tokens", 0))
        self.lbl_total = QLabel(f"<b>{total:,}</b>")
        ul.addRow("当前模型：", self.lbl_model)
        ul.addRow("总请求次数：", self.lbl_req)
        ul.addRow("Prompt tokens：", self.lbl_pt)
        ul.addRow("Completion tokens：", self.lbl_ct)
        ul.addRow("合计 tokens：", self.lbl_total)

        reset_btn = QPushButton("重置用量统计")
        reset_btn.clicked.connect(self._reset_usage)
        ul.addRow(reset_btn)
        # --- 外观 ---
        look_box = QGroupBox("外观")
        look_form = QFormLayout(look_box)

        bg_row = QHBoxLayout()
        self.bg_path = QLineEdit(self.config.get("bg_image", ""))
        bg_pick = QPushButton("选择图片…")
        bg_clear = QPushButton("清除")
        bg_row.addWidget(self.bg_path, 1)
        bg_row.addWidget(bg_pick)
        bg_row.addWidget(bg_clear)
        bg_wrap = QWidget()
        bg_wrap.setLayout(bg_row)
        look_form.addRow("背景图片：", bg_wrap)

        def _pick():
            p, _ = QFileDialog.getOpenFileName(self, "选择背景图", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)")
            if p:
                self.bg_path.setText(p)
        def _clear():
            self.bg_path.clear()
        bg_pick.clicked.connect(_pick)
        bg_clear.clicked.connect(_clear)

        self.bg_opacity = QSlider(Qt.Horizontal)
        self.bg_opacity.setRange(0, 30)   # 最大 30%，避免打扰阅读
        self.bg_opacity.setValue(int(self.config.get("bg_opacity", 0.08) * 100))
        self.bg_opacity_label = QLabel(f"{self.bg_opacity.value()}%")
        self.bg_opacity.valueChanged.connect(lambda v: self.bg_opacity_label.setText(f"{v}%"))
        op_row = QHBoxLayout()
        op_row.addWidget(self.bg_opacity, 1)
        op_row.addWidget(self.bg_opacity_label)
        op_wrap = QWidget(); op_wrap.setLayout(op_row)
        look_form.addRow("背景透明度：", op_wrap)

        layout.addWidget(look_box)

        layout.addWidget(usage_box)

        # --- 按钮 ---
        btns = QHBoxLayout()
        ok = QPushButton("保存")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def _on_preset(self, name):
        url, model = PRESET_ENDPOINTS.get(name, ("", ""))
        if url:
            self.base_url.setText(url)
        if model:
            self.model.setText(model)

    def _reset_usage(self):
        if QMessageBox.question(self, "确认", "确定要清零用量统计吗？") == QMessageBox.Yes:
            self.config["total_prompt_tokens"] = 0
            self.config["total_completion_tokens"] = 0
            self.config["total_requests"] = 0
            self.lbl_pt.setText("0")
            self.lbl_ct.setText("0")
            self.lbl_req.setText("0")
            self.lbl_total.setText("<b>0</b>")

    def get_config(self) -> dict:
        self.config["base_url"] = self.base_url.text().strip()
        self.config["api_key"] = self.api_key.text().strip()
        self.config["model"] = self.model.text().strip()
        self.config["jp_level"] = self.jp_level.currentText()
        self.config["bg_image"] = self.bg_path.text().strip()
        self.config["bg_opacity"] = self.bg_opacity.value() / 100.0
        return self.config

