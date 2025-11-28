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

## 扩展说明

参考 **模块结构.md** 中的详细设计说明，了解 AI 模块拆分的完整架构决策和未来扩展方向。
