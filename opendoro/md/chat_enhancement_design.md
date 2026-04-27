# DoroPet Chat UI 增强设计——文件附件与多功能 Agent 对话系统

## 1. 设计目标

将当前的 Chat 界面从"文本+图片"的简单对话，升级为**支持任意文件导入、多类型预览、上下文感知**的完整 Agent 对话工具。核心目标：

| 目标 | 说明 |
|------|------|
| **任意文件导入** | 支持拖拽/粘贴/选择上传文档(doc/xlsx/pdf/txt/json/html/csv/ppt/md)、图片、音视频、代码文件等 |
| **智能内容提取** | 自动提取文件文本内容注入 LLM 上下文，无需用户手动描述文件 |
| **多类型预览** | 在消息气泡内直接预览文件内容（非图片文件也能直观看到是什么） |
| **上下文管理** | 附件纳入消息历史、可被引用、可删除、有 token 预算提示 |
| **服务端友好** | 文件内容编码后发送给 LLM API；大文件自动分块/摘要 |

---

## 2. 系统架构概览

```
┌──────────────────────────────────────────────────────────┐
│                    ChatInterface (page)                   │
│  ┌─────────────────────────────────────────────────┐     │
│  │              MessageBubble x N                   │     │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────┐   │     │
│  │  │  Text    │  │  Attachment  │  │  Image   │   │     │
│  │  │  Block   │  │  Card(s)     │  │  Block   │   │     │
│  │  └──────────┘  └──────────────┘  └──────────┘   │     │
│  └─────────────────────────────────────────────────┘     │
│  ┌─────────────────────────────────────────────────┐     │
│  │            AttachmentInputBar                    │     │
│  │  [📎] [🖼] [📷]  📝 text input...  [model▼] [➤] │     │
│  │  ┌──────────────────────────────────────────┐   │     │
│  │  │  📄 report.docx (45KB)  📊 data.xlsx  ✕  │   │     │
│  │  └──────────────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
          │                        │
          ▼                        ▼
┌──────────────────┐   ┌──────────────────────┐
│  FileExtractor   │   │   AttachmentStorage   │
│  Pipeline        │   │   (本地文件仓库)       │
│  ┌────────────┐  │   └──────────────────────┘
│  │ docx/pdf   │  │
│  │ excel/csv  │  │
│  │ json/xml   │  │
│  │ html/md    │  │
│  │ txt/code   │  │
│  │ ppt        │  │
│  └────────────┘  │
└──────────────────┘
```

---

## 3. 数据模型变更

### 3.1 扩展数据库 Schema

当前 `messages` 表有 `images TEXT`（JSON 数组存储图片路径）。新设计扩展为统一的 `attachments TEXT`（JSON 数组存储所有附件信息），保留 `images` 列用于向后兼容。

```sql
-- messages 表新增/变更列
ALTER TABLE messages ADD COLUMN attachments TEXT;  -- JSON 数组，替代仅 images 的局限

-- 附件 JSON 结构 (每条记录)：
{
    "id": "uuid-string",
    "file_name": "report.docx",
    "file_path": "/data/attachments/uuid/report.docx",
    "file_type": "docx",           -- 标准化扩展名
    "category": "document",        -- document / image / audio / video / code / archive
    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "size_bytes": 45678,
    "extracted_text": "全文内容摘要或全文...",  -- 从文件提取的文本，用于 LLM 上下文
    "extraction_method": "full",   -- full / truncated / summary / failed
    "thumbnail_path": "/data/attachments/uuid/thumb.png",  -- 可选缩略图
    "added_at": "2026-04-27T12:00:00Z"
}
```

### 3.2 Python 数据类

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

class FileCategory(Enum):
    DOCUMENT = "document"    # docx, pdf, ppt, txt, md
    SPREADSHEET = "spreadsheet"  # xlsx, csv
    CODE = "code"           # py, js, ts, java, cpp, etc.
    DATA = "data"           # json, xml, yaml, toml
    IMAGE = "image"         # png, jpg, gif, webp, svg
    AUDIO = "audio"         # mp3, wav, ogg
    VIDEO = "video"         # mp4, webm
    WEB = "web"             # html, htm
    ARCHIVE = "archive"     # zip, tar, gz
    OTHER = "other"

@dataclass
class AttachmentInfo:
    """附件元信息"""
    id: str                          # UUID
    file_name: str                   # 原始文件名
    file_path: str                   # 存储路径（附件仓库内）
    file_type: str                   # 小写扩展名
    category: FileCategory
    mime_type: str
    size_bytes: int
    extracted_text: str = ""         # 提取的文本内容
    extraction_method: str = "none"  # full / truncated / summary / failed / none
    thumbnail_path: str = ""
    added_at: str = ""               # ISO 时间戳
    token_count: int = 0             # 估算的 token 数
```

### 3.3 消息历史中的附件表示

发送给 LLM 的消息格式（OpenAI 格式扩展）：

```python
# 用户消息示例（多附件）
{
    "role": "user",
    "content": [
        {"type": "text", "text": "请分析这两个文件"},
        {
            "type": "file",
            "file": {
                "file_name": "report.docx",
                "file_type": "docx",
                "size_bytes": 45678
            },
            "text": "文件 report.docx 的内容如下：\n\n[docx 全文提取...]\n\n--- 文件结束 ---"
        },
        {
            "type": "file",
            "file": {
                "file_name": "data.xlsx",
                "file_type": "xlsx",
                "size_bytes": 12345
            },
            "text": "文件 data.xlsx 的内容如下：\n\nSheet1:\n| A | B | C |\n|---|---|---|\n...\n\n--- 文件结束 ---"
        }
    ]
}
```

> **设计决策**：不直接发送文件二进制。提取文本内容后以文本块形式注入 LLM 上下文，同时附带文件元信息。这样兼容所有 LLM API。

---

## 4. 文件类型支持矩阵

### 4.1 完整支持列表

| 类别 | 扩展名 | 提取方式 | 预览方式 | 依赖 |
|------|--------|---------|---------|------|
| **Word** | .docx | python-docx 全文提取 | 格式化文本预览 + 页数统计 | `python-docx` |
| **Excel** | .xlsx, .xls | openpyxl/pandas → Markdown 表格 | 表格预览（前 N 行） | `openpyxl`, `pandas` |
| **CSV** | .csv | pandas/内置 csv → Markdown 表格 | 表格预览 + 行列统计 | `pandas` |
| **PDF** | .pdf | PyMuPDF/pdfplumber 全文提取 | 文本预览 + 页数 | `PyMuPDF` 或 `pdfplumber` |
| **PPT** | .pptx | python-pptx 提取文字 | 幻灯片缩略图 + 文本摘要 | `python-pptx` |
| **文本** | .txt, .log | 直接读取（自动编码检测） | 全文预览（语法高亮） | `chardet` |
| **Markdown** | .md | 直接读取 | 渲染 Markdown 预览 | 已有 `MessageParser` |
| **JSON** | .json | json.load + 格式化 | 语法高亮 JSON 树 | 内置 |
| **HTML** | .html, .htm | BeautifulSoup 提取纯文本 | 渲染 HTML 或源码高亮 | `beautifulsoup4` |
| **XML** | .xml | BeautifulSoup/内置 xml | 源码高亮 + 结构树 | `beautifulsoup4` |
| **YAML** | .yaml, .yml | PyYAML → 结构化文本 | 语法高亮 | `PyYAML` |
| **代码** | .py, .js, .ts, .java, .c, .cpp, .go, .rs, etc. | 直接读取 | 语法高亮代码块 | 已有 |
| **图片** | .png, .jpg, .jpeg, .gif, .webp, .bmp, .svg | 视觉模型 / 无提取 | 缩略图 + 点击放大 | 已有 |
| **音频** | .mp3, .wav, .ogg, .m4a | whisper 语音转文字（可选） | 音频波形 + 播放控件 | `whisper`（可选） |
| **视频** | .mp4, .webm, .avi, .mov | 无提取（仅元信息） | 视频缩略图 + 元信息 | `ffmpeg-python`（可选） |
| **压缩包** | .zip, .tar, .gz | 列出文件清单 | 文件树预览 | 内置 `zipfile`, `tarfile` |

### 4.2 大文件处理策略

```
文件大小阈值：
  ≤ 10KB    → 全文提取
  ≤ 100KB   → 全文提取（token 过多时截断到前 3000 字符 + "...[已截断]"）
  ≤ 1MB     → 截断到前 3000 字符 + "[文件共 N 字符，仅展示前 3000]"
  > 1MB      → 仅提取元信息 + "[文件过大（N MB），未提取文本内容，请使用技能处理]"
```

> 超大文件（>1MB）建议用户通过 Skills 处理（如已有 `pptx`、`docx`、`pdf`、`excel-xlsx` 技能）。

---

## 5. UI/UX 设计

### 5.1 附件输入栏 `AttachmentInputBar`

在现有输入框上方，新增附件预览条：

```
┌────────────────────────────────────────────────────────┐
│  📄 report.docx (45KB)  [✕]  已提取 2834 字符          │
│  📊 data.xlsx  (12KB)   [✕]  已提取 156 行 × 5 列      │
│  🖼 photo.jpg  (2.3MB)  [✕]  Vision 模式              │
│  📝 readme.md  (8KB)    [✕]  已提取 1024 字符          │
└────────────────────────────────────────────────────────┘
```

每个附件卡片显示：
- **图标**：按文件类型着色（docx=蓝色，xlsx=绿色，pdf=红色，代码=紫色，图片=橙色）
- **文件名**：过长时省略号截断
- **文件大小**：人性化显示（KB/MB）
- **提取状态**：`已提取 N 字符` / `Vision 模式` / `未提取` / `提取失败`
- **删除按钮** `✕`：从本次发送中移除（但保留在附件仓库中）

### 5.2 文件导入方式

| 方式 | 触发 | 行为 |
|------|------|------|
| **拖拽** | 拖文件到输入框区域 | 显示拖放高亮区域，松手后添加 |
| **粘贴** | Ctrl+V 粘贴文件（非图片） | 检测剪贴板文件，添加附件 |
| **按钮** | 点击 📎 附件按钮 | 打开文件选择对话框，多选支持 |
| **截图** | 点击 📷 截图按钮 | 已有，不变 |
| **图片按钮** | 点击 🖼 图片按钮 | 已有，不变；图片按图片逻辑处理 |

### 5.3 消息气泡中的附件展示

在 `MessageBubble` 中，附件在文本内容上方展示为**附件卡片组**：

```
┌──────────────────────────────────────┐
│  ┌──────────────────────────────┐    │
│  │ 📄 report.docx         45KB  │ ← 附件卡片（可点击展开/预览）
│  │ 📊 data.xlsx           12KB  │
│  └──────────────────────────────┘    │
│                                      │
│  请帮我分析这两个文件中的数据...      │ ← 用户消息文本
│                                      │
│                              [用户]  │
└──────────────────────────────────────┘
```

**附件卡片交互**：
- **点击**：展开内联预览面板（小窗显示文件内容摘要）
- **双击**：用系统默认程序打开原文件
- **右键菜单**：`复制文件` / `另存为...` / `重新提取文本`
- **悬停**：显示完整文件名、路径 tooltip

### 5.4 内联预览面板 `InlinePreviewPanel`

点击附件卡片后，在气泡内展开一个预览面板：

```
┌──────────────────────────────────────────┐
│ 📄 report.docx (2834 字符)    [展开▼] [✕] │
├──────────────────────────────────────────┤
│                                          │
│  文档内容预览：                          │
│  ┌────────────────────────────────────┐ │
│  │ 第一章 绪论                        │ │
│  │                                    │ │
│  │ 本研究旨在探讨...                  │ │
│  │ ...（滚动显示）                    │ │
│  └────────────────────────────────────┘ │
│                                          │
│  页数: 12   段落: 45   提取方式: 全文     │
└──────────────────────────────────────────┘
```

不同文件类型的预览渲染：
- **文档（docx/pdf/txt/md）**：纯文本/Markdown 渲染
- **表格（xlsx/csv）**：QTableWidget 展示前 100 行
- **JSON/XML/YAML**：语法高亮的源码视图或树形视图
- **代码**：语法高亮代码块
- **图片**：已有 `ClickableImageLabel`，不变
- **HTML**：源码高亮 + "用浏览器打开"按钮
- **压缩包**：文件树形列表

### 5.5 Token 预算提示

在附件输入栏右侧或底部状态栏显示：

```
📎 4 个附件 | 估算 ~3500 tokens | 当前模型上限 128K | ✅ 安全
```

当附件 token 接近模型上限时：
```
📎 4 个附件 | 估算 ~120000 tokens | 当前模型上限 128K | ⚠️ 接近上限
```

超出时：
```
📎 4 个附件 | 估算 ~150000 tokens | 当前模型上限 128K | ❌ 超出上限，请减少附件
```

"发送"按钮在超出上限时应禁用，并给出提示。

---

## 6. 文件提取管道 `FileExtractorPipeline`

### 6.1 架构

```python
class FileExtractorPipeline:
    """文件内容提取管道——责任链模式"""

    def __init__(self):
        self._extractors: List[BaseExtractor] = []
        self._register_defaults()

    def _register_defaults(self):
        """注册所有内置提取器"""
        self._extractors = [
            DocxExtractor(),
            ExcelExtractor(),
            CsvExtractor(),
            PdfExtractor(),
            PptxExtractor(),
            TextExtractor(),      # txt, log, md
            JsonExtractor(),      # json
            HtmlExtractor(),      # html, htm
            XmlExtractor(),       # xml
            YamlExtractor(),      # yaml, yml
            CodeExtractor(),      # py, js, ts, java, go, rs, c, cpp, ...
            ImageExtractor(),     # 图片——不提取文本，标记为 vision 模式
            ArchiveExtractor(),   # zip, tar, gz——仅列出内容
        ]

    def extract(self, file_path: str) -> ExtractResult:
        """根据扩展名匹配合适的提取器并提取文本"""
        ext = Path(file_path).suffix.lower().lstrip(".")
        for extractor in self._extractors:
            if ext in extractor.supported_extensions():
                return extractor.extract(file_path)
        return ExtractResult.failed(f"不支持的文件类型: .{ext}")
```

### 6.2 提取器接口

```python
class BaseExtractor(ABC):
    """文件提取器基类"""

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """返回支持的文件扩展名列表"""
        pass

    @abstractmethod
    def extract(self, file_path: str) -> ExtractResult:
        """从文件提取文本内容"""
        pass

    def can_handle(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower().lstrip(".")
        return ext in self.supported_extensions()

@dataclass
class ExtractResult:
    text: str                        # 提取的文本
    method: str                      # "full" | "truncated" | "summary" | "failed"
    token_estimate: int = 0
    metadata: dict = field(default_factory=dict)  # 如页数、行列数等
    error: str = ""

    @classmethod
    def failed(cls, error: str) -> "ExtractResult":
        return cls(text="", method="failed", error=error)
```

### 6.3 各提取器要点

**DocxExtractor** (`python-docx`)：
- 遍历 `document.paragraphs` 提取文本
- 提取表格内容（Markdown 表格格式）
- 统计段落数、表格数

**ExcelExtractor** (`openpyxl`)：
- 遍历所有 sheet
- 每个 sheet 输出 Markdown 表格
- 有公式的单元格标记 `[公式]`
- 支持 .xlsx 和 .xls

**CsvExtractor** (内置 `csv` 模块)：
- 自动检测分隔符（`,` / `;` / `\t`）
- 自动检测编码（chardet）
- 输出 Markdown 表格

**PdfExtractor** (`PyMuPDF` / `pdfplumber`)：
- 优先 PyMuPDF（快速），回退 pdfplumber（精确）
- 提取文本 + 表格
- 统计页数

**TextExtractor**：
- 自动编码检测（chardet + cchardet）
- .txt / .log / .md（Markdown 保留原样）
- 无依赖（仅 chardet 可选）

**HtmlExtractor** (`beautifulsoup4`)：
- 提取 `<body>` 内纯文本
- 保留标题层级结构
- 提取 `<table>` 为 Markdown 表格

**CodeExtractor**：
- 直接读取，保留原样
- 用于语法高亮渲染
- 支持 30+ 编程语言

**ImageExtractor**：
- 不提取文本
- 标记 `method="vision"` 表示需要视觉模型处理
- 记录尺寸、格式等元信息

---

## 7. 附件存储 `AttachmentStorage`

### 7.1 存储策略

```
%LOCALAPPDATA%/DoroPet/attachments/
├── {uuid1}/
│   ├── original.docx          ← 原始文件
│   ├── thumb.png              ← 缩略图（可选）
│   └── meta.json              ← 提取结果缓存
├── {uuid2}/
│   ├── data.xlsx
│   └── meta.json
└── ...
```

### 7.2 核心类

```python
class AttachmentStorage:
    """附件仓库——单一实例"""

    def __init__(self):
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.root = os.path.join(base, "DoroPet", "attachments")
        os.makedirs(self.root, exist_ok=True)

    def store(self, source_path: str) -> AttachmentInfo:
        """将文件复制到仓库，生成 UUID 目录，返回元信息"""
        pass

    def get_path(self, attachment_id: str) -> str:
        """获取附件在仓库中的原始文件路径"""
        pass

    def get_meta(self, attachment_id: str) -> dict:
        """获取缓存的提取结果"""
        pass

    def delete(self, attachment_id: str):
        """删除附件及其目录"""
        pass

    def get_total_size(self) -> int:
        """获取仓库总大小（用于清理提示）"""
        pass
```

### 7.3 清理策略

在 Settings 中提供选项：
- 退出时自动清理（默认关闭）
- 附件保留天数（默认 30 天）
- 手动"清理所有附件"按钮
- 仓库总大小显示

---

## 8. 与现有系统的集成点

### 8.1 与 Skill 系统的配合

已有的文件操作 Skills（`docx`、`pdf`、`pptx`、`excel-xlsx`）用于 LLM **生成/修改**文件。而附件系统的文本提取用于 LLM **读取/理解**文件。两者互补：

| 场景 | 使用方式 |
|------|---------|
| "帮我总结这个 PDF" | 附件提取 → 文本注入 LLM 上下文 → LLM 直接总结 |
| "帮我创建一个 Word 文档" | LLM 调用 `docx` Skill 生成文件 → 文件返回给用户 |
| "分析这个 Excel 并生成 PPT" | 附件提取 Excel 内容 → LLM 分析 → 调用 `pptx` Skill 生成 |

### 8.2 与 MessageBubble 的集成

当前 `MessageBubble` 按以下顺序渲染：
```
图片 → ThinkingWidget → Text/Code/Image 块 → 操作栏
```

修改为：
```
附件卡片组 → 图片 → ThinkingWidget → Text/Code/Image 块 → 操作栏
```

### 8.3 与 quick_chat_window.py 的集成

`QuickChatWindow` 使用不同的 `QuickMessageBubble`。需要同步支持附件，但由于功能定位不同（快速轻量对话），QuickChatWindow 可以使用简化版附件系统：
- 支持图片（已有）+ 文本文件（txt/md）
- 不支持完整文档提取
- 拖拽仍支持，但不渲染复杂预览

### 8.4 与消息历史的兼容

- 新字段 `attachments TEXT` 存储 JSON 数组
- 旧字段 `images TEXT` 保留向后兼容
- 加载消息时优先读 `attachments`，回退读 `images`
- 新消息写入时同时填充 `images`（图片路径）和 `attachments`（完整信息）

---

## 9. 依赖项清单

新增 Python 依赖：

```txt
# 文档提取
python-docx>=1.1.0         # .docx 提取
openpyxl>=3.1.0            # .xlsx 提取
xlrd>=2.0.0                # .xls 提取（可选）
PyMuPDF>=1.23.0            # .pdf 提取（优先）
pdfplumber>=0.10.0         # .pdf 提取（备选）
python-pptx>=0.6.0         # .pptx 提取

# 文本/标记语言
chardet>=5.0.0             # 编码检测
beautifulsoup4>=4.12.0     # HTML/XML 提取
lxml>=4.9.0                # HTML/XML 解析加速
PyYAML>=6.0                # YAML 解析

# 可选增强
Pillow>=10.0.0             # 缩略图生成（已有）
openai-whisper>=20231117   # 音频转文字（可选）
ffmpeg-python>=0.2.0       # 视频元信息（可选）
```

---

## 10. 实现计划

### Phase 1: 基础设施（优先级最高）

| 任务 | 产出 | 依赖 |
|------|------|------|
| 实现 `AttachmentStorage` | 文件仓库，增删查 | 无 |
| 实现 `FileExtractorPipeline` + 6 个核心提取器 | Docx/Excel/CSV/PDF/Text/Code 提取器 | 新增 pip 依赖 |
| 扩展数据库 Schema | `attachments` 列迁移 | `AttachmentStorage` |
| 实现 `AttachmentInfo` 数据类 | 附件元信息模型 | 无 |
| 单元测试 | 提取器正确性验证 | 提取器实现 |

### Phase 2: UI 核心

| 任务 | 产出 | 依赖 |
|------|------|------|
| `AttachmentCard` 组件 | 单个附件卡片（显示、点击预览、删除） | Phase 1 |
| `AttachmentInputBar` 组件 | 附件预览条 + Token 预算提示 | `AttachmentCard` |
| `InlinePreviewPanel` 组件 | 内联预览面板（文本/表格/代码/JSON 树） | 提取器 |
| 扩展 `PasteableTextEdit` | 支持文件粘贴/拖拽（当前仅图片） | `AttachmentInputBar` |
| 扩展 `MessageBubble` | 附件卡片组渲染 | `AttachmentCard` |

### Phase 3: 发送流程

| 任务 | 产出 | 依赖 |
|------|------|------|
| 发送时自动提取附件文本 | `send_message()` 调用提取管道 | Phase 1, Phase 2 |
| 附件文本注入 LLM 上下文 | `trigger_llm_generation()` 构建消息 | 提取管道 |
| Token 预算检查 | 发送前验证，超限时拦截 | Phase 2 |
| 附件在消息历史中的持久化 | 存入/读取 `attachments` JSON | DB Schema |

### Phase 4: 增强与优化

| 任务 | 产出 | 依赖 |
|------|------|------|
| 更多提取器支持 | PPT/HTML/JSON/XML/YAML/Archive | Phase 1 提取器框架 |
| 内联预览优化 | 表格组件、JSON 树、语法高亮 | Phase 2 |
| QuickChatWindow 简化适配 | 基本附件支持 | Phase 1-2 |
| 音频转文字（可选） | whisper 集成 | 细粒度评估 |
| 附件清理策略 UI | Settings 中的清理选项 | `AttachmentStorage` |

---

## 11. 文件类型图标映射

| 类别 | 图标 | 颜色 |
|------|------|------|
| docx | 📄 | #2196F3 (蓝) |
| xlsx/csv | 📊 | #4CAF50 (绿) |
| pdf | 📕 | #F44336 (红) |
| ppt/pptx | 📽 | #FF9800 (橙) |
| txt/log | 📝 | #9E9E9E (灰) |
| md | 📘 | #2196F3 (蓝) |
| json/xml/yaml | 📋 | #795548 (棕) |
| html/htm | 🌐 | #E91E63 (粉) |
| 代码文件 | 💻 | #6A1B9A (紫) |
| zip/tar/gz | 📦 | #607D8B (蓝灰) |
| 图片文件 | 🖼 | #FF9800 (橙) |
| 音频文件 | 🎵 | #00BCD4 (青) |
| 视频文件 | 🎬 | #3F51B5 (靛蓝) |

---

## 12. 风险与考量

| 风险 | 缓解措施 |
|------|---------|
| **大文件内存占用** | 严格的大小阈值截断策略；大文件引导使用 Skills |
| **依赖安装失败** | 所有提取器用 try/except 包裹，提取失败优雅降级 |
| **PDF 提取质量不稳定** | 双引擎策略 PyMuPDF + pdfplumber，结果取更长的 |
| **旧版消息兼容** | `images` 字段保留，新的 `attachments` 字段渐进迁移 |
| **附件仓库磁盘膨胀** | 提供清理策略；设置仓库大小上限（默认 500MB） |
| **QuickChatWindow 重复代码** | 共享 `AttachmentStorage` 和提取管道；简化版 UI 仅覆盖核心场景 |
