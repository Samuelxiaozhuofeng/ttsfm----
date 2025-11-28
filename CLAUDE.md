# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 Flask 的 TTS（文本转语音）Web 应用，使用 ttsfm 库将文本转换为语音，并提供了章节管理、阅读进度追踪、以及 AI 助手问答功能。

## 核心技术栈

- **后端框架**: Flask 3.1.2
- **TTS 引擎**: ttsfm 3.4.1 (OpenAI TTS API 封装)
- **HTTP 客户端**: requests 2.32.3
- **数据存储**: JSON 文件 (library_data.json)

## 开发命令

```bash
# 启动应用
python app.py

# 访问地址
http://localhost:5000
```

应用将在端口 5000 上启动，支持以下页面：
- `/` - TTS 文本转语音主页
- `/library` - 章节书架管理页
- `/reader` - 阅读器页面（含 AI 问答）

## 核心架构

### 1. 模块分离原则

项目采用 **Blueprint 模式**将 AI 相关功能从主应用解耦：

- **app.py**: Flask 主应用入口
  - TTS 音频生成 (`/api/generate`)
  - 章节管理 (CRUD 操作: `/api/library/*`)
  - 阅读进度追踪 (`/api/library/progress/*`)
  - 文件上传/下载/播放

- **ai_routes.py**: AI 功能 Blueprint
  - AI 配置管理 (`/api/ai/settings`)
  - AI 连通性测试 (`/api/ai/test`)
  - 章节问答聊天 (`/api/chat/message`)
  - 聊天记录管理 (`/api/chat/history/*`)
  - 支持流式和非流式两种聊天模式

- **library.py**: 数据持久化层
  - 章节数据管理 (chapters)
  - 阅读进度管理 (progress)
  - AI 设置管理 (ai_settings)
  - 聊天记录管理 (chat_history)

依赖注入方式：
```python
# app.py 中的初始化流程
library = Library()
init_ai_routes(app, library)  # 将 library 实例注入 AI Blueprint
```

### 2. TTS 文本处理逻辑

- **短文本** (≤1000 字符): 使用 `generate_speech()` 一次性生成
- **长文本** (>1000 字符): 使用 `generate_speech_long_text()` 自动分块并合并
  - `max_length=1000`: 每块最大长度
  - `preserve_words=True`: 在词边界切分
  - `auto_combine=True`: 自动合并音频文件

### 3. AI 问答系统

采用 **OpenAI 兼容 API** 标准：

- **端点规范化**: `build_chat_endpoint()` 自动添加 `/chat/completions` 后缀
- **上下文构建**: System prompt 包含章节全文，历史对话限制最近 10 条
- **流式支持**: 当请求体包含 `{"stream": true}` 时，使用 SSE 返回增量内容
- **聊天记录**: 所有对话自动保存到 `library_data.json` 的 `chat_history` 中

### 4. 数据持久化

所有数据存储在 **library_data.json**，结构如下：

```json
{
  "chapters": {
    "chapter_xxx": {
      "id": "...",
      "title": "...",
      "content": "...",
      "audio_filename": "...",
      "created_at": "...",
      "word_count": 0,
      "char_count": 0
    }
  },
  "progress": {
    "chapter_xxx": {
      "current_time": 0.0,
      "last_read": "..."
    }
  },
  "ai_settings": {
    "api_url": "...",
    "api_key": "...",
    "model": "...",
    "updated_at": "..."
  },
  "chat_history": {
    "chapter_xxx": [
      {"role": "user", "content": "...", "timestamp": "..."},
      {"role": "assistant", "content": "...", "timestamp": "..."}
    ]
  }
}
```

- **Library 类**使用 `_ensure_data_structure()` 确保数据完整性
- 所有修改操作通过 `_save_data()` 自动保存

### 5. 目录结构

```
.
├── app.py              # Flask 主应用（TTS + 章节管理）
├── ai_routes.py        # AI 功能 Blueprint（问答 + 设置）
├── library.py          # 数据持久化层（JSON 存储）
├── read_text.py        # 独立脚本（读取 text.md 生成音频）
├── library_data.json   # 数据库文件（章节/进度/AI设置/聊天记录）
├── templates/          # Jinja2 模板
│   ├── index.html      # TTS 主页
│   ├── library.html    # 章节书架页
│   └── reader.html     # 阅读器页（含 AI 问答）
├── uploads/            # 用户上传文件目录
└── outputs/            # 生成的音频文件目录
```

## 代码规范

### 类型提示

所有 Python 代码必须使用静态类型提示：
```python
def add_chapter(self, chapter_id: str, title: str, content: str,
               audio_filename: str) -> Dict:
    ...

def get_chapter(self, chapter_id: str) -> Optional[Dict]:
    ...
```

### 错误处理

API 路由统一返回格式：
```python
# 成功
return jsonify({'success': True, 'data': ...})

# 失败
return jsonify({'error': '错误信息'}), 状态码
```

### 前端 API 约定

- 所有 API 路径以 `/api/` 开头
- RESTful 风格：GET 查询、POST 创建/更新、DELETE 删除
- 文件路径使用相对于 `OUTPUT_FOLDER` 的文件名


--

## 关于这个项目的用户

- 用户不是专业程序员，但会使用 Claude Code 做「结对编程」和功能开发。
- 用户对需求的想法有时不够完整、也可能比较模糊：在开始开发一个功能时，用户自己也可能说不清楚「究竟要什么」。
- 默认交流语言为：简体中文。

## Claude 在本项目中的核心职责

1. **主动澄清需求，而不是直接写代码。**
2. **主动扫描当前代码库，发现和用户需求相关的部分。**
3. **通过多轮问答，帮用户把真实需求挖掘清楚。**
4. **只有在需求足够清晰之后，才开始具体的设计和开发。**

## 工作方式偏好（必须遵守）

每当用户提出一个新功能 / 修改需求时，Claude 必须遵循以下流程，而不是立刻开始编码。

### 第 0 步：阅读与准备

- 在开始回答之前，先：
  - 浏览/扫描与该功能相关的代码（例如搜索文件名、关键字等）。
  - 如果有 `CLAUDE.md` 或需求文档，先快速阅读相关部分。
- 然后用简短几句话说明：
  - 你看到了哪些相关文件或模块；
  - 你初步认为这个需求大概会影响哪些地方。

### 第 1 步：用自己的话复述需求

- 不要直接假设自己已经理解。
- 先用你自己的话，总结你目前理解到的需求，包括：
  - 目标是什么（用户希望达成什么效果）；
  - 大概会涉及到哪些数据、用户场景、界面或接口；
  - 哪些点目前是「不确定」或「有多种可能实现的」。

### 第 2 步：主动提出问题（至少 5 个，按需更多）

- 每次有新需求时，Claude 必须主动向用户提问，而不是等用户自己补充。
- 这些问题应该：
  - 与当前功能强相关；
  - 尽量覆盖用户可能没有考虑到的地方（边界情况、错误情况、性能、体验、权限、安全等）；
  - 涵盖「现在」「未来可能扩展」两个角度。
- 问题要清晰、具体，用户可以用自然语言回答。

示例（只是风格，不是固定内容）：
- 「这个功能主要是给谁用？他们大概会在什么场景下使用？」
- 「如果操作失败/数据异常时，你希望系统怎么表现（比如提示、重试、日志）？」
- 「这个版本中，有哪些是‘必须现在实现的’，哪些可以留到以后迭代？」

### 第 3 步：多轮澄清，而不是“一问完事”

- 如果根据用户的第一轮回答，你仍然有不理解或有歧义的地方：
  - 你应该继续发起第 2 轮、第 3 轮提问；
  - 每一轮都要先简要总结「你现在新的理解」，再提新问题。
- 目标：**直到你可以把需求整理成一份清晰的「需求说明 + 验收标准」为止**。
- 在你自己感觉仍然有重要模糊点时，不允许直接开始写代码。

### 第 4 步：整理成「任务说明 + 验收标准」

在真正动手开发之前，Claude 必须输出一段结构化的小结，并征求用户确认：

- 内容包括（可用列表或小节）：
  1. 《功能需求说明》：用自然语言描述这个功能要做什么，给谁用，典型使用流程是什么。
  2. 《范围与暂不处理》：明确这次不会做哪些东西，以免范围失控。
  3. 《验收标准 / 完成条件》：列出若干条可以检查的条件（例如输入/输出、行为、边界情况）。
- 然后明确问用户：
  - 「请确认以上理解是否正确？如果有不对或需要补充的地方，请指出。只有在你确认之后，我才会开始具体的设计和开发。」

只有在用户确认之后，才进入开发阶段。

### 第 5 步：在开发过程中持续提问

- 即使已经开始写代码，如果发现：
  - 需求存在歧义；
  - 原有代码和需求冲突；
  - 出现新的设计选择（例如多种方案各有优缺点），
- Claude 需要：
  - 列出你看到的问题或不同方案；
  - 主动向用户解释差异，并明确询问用户的偏好或取舍；
  - 在得到用户反馈后，再继续实现。

### 开发完成后的要求（简要）

- 在声称某个功能「已完成」之前，Claude 应该：
  - 对照前面整理的《验收标准》逐条检查；
  - 用自然语言说明每一条是否满足；
  - 如果有暂时无法做到的部分，要明确标注为「未完成」或「待以后迭代」。

## 不允许的行为

- 在用户表达模糊、自己也不太确定时，**直接开始大规模写代码或重构**。
- 在没有进行足够的提问和澄清之前，就认定「自己已经完全理解需求」。
- 用一句话带过「这个很简单」「大概这样就行」而不说明细节和风险。

