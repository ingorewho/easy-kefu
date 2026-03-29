# 智能客服项目指南

## 项目概述

**智能客服系统** - 基于 AI 的电商客服自动化解决方案

- **核心功能**: 拼多多商家客服自动回复、智能转接、知识库 RAG 检索
- **技术栈**: Python 3.11+, PyQt6, Playwright, Coze/Kimi/Qwen AI, ChromaDB
- **包管理**: uv (pyproject.toml)

## 目录结构

```
easy-kefu/
├── Agent/              # AI 机器人 (Coze/Kimi/Qwen + RAG)
├── Channel/            # 渠道接口 (拼多多 WebSocket)
├── Message/            # 消息队列/消费者/处理器
├── bridge/             # 桥接层 (Context/Reply)
├── database/           # SQLite + SQLAlchemy 模型
├── ui/                 # PyQt6 界面
├── knowledge_base/     # RAG 知识库 (ChromaDB + 文本向量化)
├── utils/              # 工具 (logger/业务时间队列/Telegram 告警)
├── icon/               # 应用图标资源
├── config.py           # 配置管理 (config.json)
├── app.py              # 应用程序入口
├── app_onedir.spec     # PyInstaller 打包配置 (macOS)
├── dmg_config.py       # DMG 安装包配置
├── build_dmg.py        # DMG 打包脚本
└── BUILD_GUIDE.md      # 详细打包指南
```

## 核心模块

| 模块 | 说明 |
|------|------|
| `PDDChannel` | 拼多多 WebSocket 客户端，消息收发 |
| `BotWithRAG` | AI 机器人包装器，支持混合检索 (本地+Web) |
| `MessageConsumer` | 消息队列消费，支持并发处理 |
| `BusinessHoursQueue` | 非工作时间消息队列 |
| `ChatHistoryUI` | 聊天记录管理 |

## 配置说明

**config.json** 主要配置项:
- `bot_type`: coze | kimi | qwen
- `enable_rag`: 是否启用知识库
- `businessHours`: 工作时间 (08:00-23:00)
- `emotion_alert_threshold`: 情绪告警阈值
- `ai_system_prompt`: AI 回复风格配置

## 常用命令

```bash
# 环境
uv venv && uv sync
uv run playwright install chrome

# 启动
python app.py

# 测试 RAG
uv run pytest test_rag.py
```

## macOS 打包指南

### 一键打包

```bash
# 完整打包流程
python build_dmg.py

# 输出: dist/智能客服-1.0.0.dmg
```

### 手动打包

```bash
# 1. 构建应用
pyinstaller app_onedir.spec --clean --noconfirm

# 2. 代码签名（可选）
codesign --force --deep --sign - "dist/智能客服.app"

# 3. 创建 DMG
dmgbuild -s dmg_config.py "智能客服" "dist/智能客服.dmg"
```

### 打包配置

- **app_onedir.spec**: PyInstaller 配置，使用单目录模式
- **dmg_config.py**: DMG 外观和布局配置
- **build_dmg.py**: 自动化打包脚本

详见 [BUILD_GUIDE.md](BUILD_GUIDE.md)

## 开发注意

- 2 空格缩进，单引号优先
- 消息类型：`ContextType.TEXT/IMAGE/GOODS_INQUIRY/ORDER_INFO` 等
- 数据库模型：`database/models.py` (Channel/Shop/Account/ChatMessage/AlertLog)
- macOS 打包使用 `onedir` 模式而非 `onefile`，以确保稳定性
