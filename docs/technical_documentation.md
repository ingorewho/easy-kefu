# 智能客服系统 - 技术文档

> 版本: 1.0.0
> 日期: 2026-03-11
> Python: 3.11+

---

## 1. 项目概述

### 1.1 产品定位

**智能客服系统** 是一款基于 Python + PyQt6 开发的桌面应用程序，为拼多多商家提供 AI 自动化客服解决方案。

### 1.2 核心功能

- **AI 智能回复**: 集成字节跳动 Coze AI 平台，自动回复用户咨询
- **多渠道管理**: 支持多店铺、多账号统一管理
- **实时消息处理**: WebSocket 实时接收和发送消息
- **关键词管理**: 自定义关键词触发转人工客服
- **营业时间控制**: 非营业时间自动回复提示
- **可视化监控**: 实时查看消息处理状态和日志

### 1.3 技术栈

| 层级 | 技术 |
|-----|------|
| GUI | PyQt6 + PyQt6-Fluent-Widgets |
| 异步通信 | asyncio + websockets |
| AI 引擎 | Coze API (cozepy) |
| 数据库 | SQLite + SQLAlchemy |
| 浏览器自动化 | Playwright |
| 包管理 | UV |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      UI 层 (PyQt6)                          │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ 自动回复  │ 关键词   │ 账号管理  │ 日志管理  │             │
│  │  监控    │  管理    │         │         │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
├─────────────────────────────────────────────────────────────┤
│                    核心业务逻辑层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   消息队列    │  │  消息消费者   │  │  消息处理器   │      │
│  │ MessageQueue │  │   Consumer   │  │   Handler    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                   渠道适配层 (Channel)                       │
│         ┌─────────────────────────────────────┐            │
│         │      拼多多 WebSocket 客户端         │            │
│         │   (PDDChannel - WebSocket 通信)      │            │
│         └─────────────────────────────────────┘            │
├─────────────────────────────────────────────────────────────┤
│                    AI 引擎层 (Agent)                        │
│         ┌─────────────────────────────────────┐            │
│         │         CozeBot                     │            │
│         │   (字节跳动 Coze AI 平台接口)        │            │
│         │  - 会话管理 (ConversationManager)   │            │
│         │  - 用户会话 (UserSessionManager)    │            │
│         └─────────────────────────────────────┘            │
├─────────────────────────────────────────────────────────────┤
│                    数据持久化层                             │
│         ┌─────────────────────────────────────┐            │
│         │   SQLite 数据库 (SQLAlchemy ORM)    │            │
│         │   - 渠道、店铺、账号、关键词表       │            │
│         └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | 核心文件 |
|-----|------|---------|
| `Agent/` | AI 机器人实现 | `CozeAgent/bot.py` |
| `Channel/` | 电商平台接口 | `pinduoduo/pdd_chnnel.py` |
| `Message/` | 消息队列处理 | `message_queue.py`, `message_consumer.py` |
| `database/` | 数据持久化 | `models.py`, `db_manager.py` |
| `ui/` | 用户界面 | `main_ui.py`, `auto_reply_ui.py` |
| `utils/` | 工具函数 | `logger.py`, `performance_monitor.py` |

---

## 3. 核心流程

### 3.1 消息处理流程

```
WebSocket 消息接收
       ↓
PDDChatMessage 解析 (pdd_message.py)
       ↓
Context 对象转换 (包含消息类型、内容、元数据)
       ↓
消息分类：
├─→ 立即处理（系统消息、认证、撤回）→ 直接响应
└─→ 入队处理（用户消息、商品咨询、订单）→ 消息队列
              ↓
        消息消费者拉取
              ↓
        按用户 ID 路由到对应处理器
              ↓
        处理器链依次尝试处理
              ↓
        AI Bot 生成回复 → 发送 API 调用
```

### 3.2 AI 回复流程

```
用户发送消息
       ↓
消息队列 → 消费者
       ↓
AIAutoReplyHandler
       ↓
CozeBot.reply()
  ├─→ 获取/创建用户会话 (SQLite)
  ├─→ 调用 Coze API 生成回复
  └─→ 返回 Reply 对象
       ↓
SendMessage API 发送回复
```

---

## 4. 详细设计

### 4.1 消息系统

#### 4.1.1 消息队列 (MessageQueue)

**文件**: `Message/message_queue.py`

**特性**:
- TTL 机制，自动清理过期消息（默认 5 分钟）
- 异步操作，线程安全
- 最大容量限制（默认 1000 条）

**核心方法**:
```python
async def put(self, message: BaseMessage, ttl: int = 300)  # 入队
async def get(self) -> BaseMessage                       # 出队
async def cleanup_expired()                              # 清理过期消息
```

#### 4.1.2 消息消费者 (MessageConsumer)

**文件**: `Message/message_consumer.py`

**特性**:
- 按用户 ID 分组处理，确保同一用户消息串行处理
- 不同用户之间并发处理（默认最大并发数 10）
- 支持用户处理器超时清理（30 秒无消息自动关闭）

#### 4.1.3 消息处理器链

**文件**: `Message/message_handler.py`

**处理器优先级**:

1. **BusinessHoursHandler** - 营业时间检查
   - 非营业时间自动回复提示
   - 默认营业时间: 08:00 - 23:00

2. **CustomerServiceTransferHandler** - 客服转接
   - 触发关键词: '人工客服', '转人工', '人工', '客服', '投诉', '举报', '不满意'
   - 自动将会话转接给人工客服

3. **AIAutoReplyHandler** - AI 自动回复
   - 调用 Coze AI 生成回复
   - 支持文本、图片、视频、商品咨询等多种消息类型

### 4.2 拼多多渠道适配器

**文件**: `Channel/pinduoduo/pdd_chnnel.py`

**核心功能**:
- WebSocket 连接管理（`wss://m-ws.pinduoduo.com/`）
- 多店铺、多账号支持
- 消息接收与解析
- 并发控制（信号量限制最大并发数 50）

**消息类型映射**:

| PDD 消息类型 | ContextType | 处理方式 |
|-----------|-------------|---------|
| 文本消息 (0) | TEXT | AI 回复 |
| 图片消息 (1) | IMAGE | AI 回复 |
| 视频消息 (14) | VIDEO | AI 回复 |
| 表情消息 (5) | EMOTION | AI 回复 |
| 商品咨询 (0/sub_type=0) | GOODS_INQUIRY | AI 回复 |
| 订单信息 (1/sub_type=1) | ORDER_INFO | AI 回复 |
| 撤回消息 (1002) | WITHDRAW | 立即处理 |
| 转接消息 (24) | TRANSFER | 立即处理 |

### 4.3 AI 引擎 (CozeBot)

**文件**: `Agent/CozeAgent/bot.py`

**工作流程**:

1. 接收 Context 对象
2. 提取用户 ID: `f"{shop_id}_{from_uid}"`
3. 获取或创建会话（SQLite 存储 `user_session.db`）
4. 调用 Coze API:
   - 创建消息（`conversations.messages.create`）
   - 发起聊天（`chat.create_and_poll`）
5. 解析回复，返回 Reply 对象

**会话管理**:

```python
# UserSessionManager (user_session.py)
- 使用 SQLite 存储用户会话映射
- 表结构: user_id → conversation_id → created_at
- 支持会话创建、查询、删除
```

### 4.4 数据库设计

**文件**: `database/models.py`

**实体关系**:

```
Channel（渠道表）
    ↓ 1:N
Shop（店铺表）
    ↓ 1:N
Account（账号表）

Keyword（关键词表）- 独立表
```

**Account 表结构**:

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| shop_id | ForeignKey | 店铺外键 |
| user_id | String | 拼多多用户标识 |
| username | String | 登录用户名 |
| password | String | 登录密码 |
| cookies | JSON | 登录 cookies |
| status | Integer | 0-休息, 1-在线, 3-离线 |

---

## 5. 配置说明

### 5.1 配置文件 (config.json)

**文件**: `config.py` 管理，运行时自动生成

```json
{
    "coze_api_base": "https://api.coze.cn",
    "coze_token": "your_token_here",
    "coze_bot_id": "your_bot_id_here",
    "bot_type": "coze",
    "businessHours": {
        "start": "08:00",
        "end": "23:00"
    }
}
```

### 5.2 环境变量

| 变量 | 说明 | 默认值 |
|-----|------|--------|
| `LOG_LEVEL` | 日志级别 | `info` |
| `ENABLE_STRUCTURED_LOGS` | 启用结构化日志 | `false` |

### 5.3 日志配置

**文件**: `utils/logger.py`

- 普通日志: `logs/app.log`（10MB 轮转，保留 5 个备份）
- 结构化日志: `logs/app_structured.log`

---

## 6. 性能优化

### 6.1 并发控制

```python
# PDDChannel 层
max_concurrent_messages = 50

# MessageConsumer 层
max_concurrent = 10

# AIHandler 层
max_workers = 5
```

### 6.2 资源管理

**文件**: `utils/resource_manager.py`

- `WebSocketResourceManager`: 管理 WebSocket 连接生命周期
- `ThreadResourceManager`: 管理线程池关闭
- `ResourceManager`: 通用资源注册与清理

### 6.3 性能监控

**文件**: `utils/performance_monitor.py`

- 记录函数执行时间
- 统计指标: count, min, max, avg
- 自动清理 1 小时前的指标

---

## 7. 项目结构

```
Customer-Agent/
├── app.py                      # 应用入口
├── config.py                   # 配置管理
├── pyproject.toml              # 项目依赖
├── uv.lock                     # 依赖锁定
│
├── Agent/                      # AI 智能代理
│   ├── bot.py                  # Bot 基类
│   ├── bot_factory.py          # Bot 工厂
│   └── CozeAgent/              # Coze 实现
│       ├── bot.py              # CozeBot
│       ├── conversation_manager.py
│       └── user_session.py
│
├── Channel/                    # 渠道适配
│   ├── channel.py              # 渠道基类
│   └── pinduoduo/              # 拼多多实现
│       ├── pdd_chnnel.py       # WebSocket 客户端
│       ├── pdd_login.py        # 登录处理
│       ├── pdd_message.py      # 消息解析
│       └── utils/API/          # API 封装
│
├── Message/                    # 消息系统
│   ├── message.py              # 消息基类
│   ├── message_queue.py        # 消息队列
│   ├── message_consumer.py     # 消息消费者
│   └── message_handler.py      # 消息处理器
│
├── database/                   # 数据层
│   ├── models.py               # ORM 模型
│   └── db_manager.py           # 数据库管理
│
├── ui/                         # UI 界面
│   ├── main_ui.py              # 主窗口
│   ├── auto_reply_ui.py        # 自动回复监控
│   ├── user_ui.py              # 账号管理
│   ├── keyword_ui.py           # 关键词管理
│   ├── log_ui.py               # 日志查看
│   └── setting_ui.py           # 设置
│
├── utils/                      # 工具类
│   ├── logger.py               # 日志系统
│   ├── performance_monitor.py  # 性能监控
│   └── resource_manager.py     # 资源管理
│
└── docs/                       # 文档和截图
```

---

## 8. 开发指南

### 8.1 环境搭建

```bash
# 安装 uv 包管理器
pip install uv

# 创建虚拟环境并安装依赖
uv venv
uv sync

# 安装浏览器驱动
uv run playwright install chrome
```

### 8.2 启动应用

```bash
python app.py
```

### 8.3 数据库操作

```bash
# 查看数据库表
sqlite3 database/channel_shop.db ".tables"

# 查询账号信息
sqlite3 database/channel_shop.db "SELECT * FROM accounts;"
```

### 8.4 日志查看

```bash
# 实时查看日志
tail -f logs/app.log

# 查看结构化日志（需安装 jq）
tail -f logs/app_structured.log | jq '.'
```

---

## 9. 设计模式

| 模式 | 应用位置 |
|-----|---------|
| 工厂模式 | `bot_factory.py` - 创建不同类型的 Bot |
| 策略模式 | `MessageHandler` - 多种处理器实现 |
| 观察者模式 | WebSocket 消息监听与处理 |
| 责任链模式 | Handler 链依次处理消息 |
| 单例模式 | `DatabaseManager`, `UserSessionManager` |
| 上下文模式 | `Context` 对象贯穿消息生命周期 |

---

## 10. 扩展性设计

### 10.1 添加新的电商平台

1. 在 `Channel/` 下创建新目录（如 `jd/`, `taobao/`）
2. 继承 `Channel` 基类实现渠道适配器
3. 实现 `send_message`, `connect`, `disconnect` 等方法

### 10.2 切换 AI 引擎

1. 在 `Agent/` 下创建新目录（如 `OpenAIAgent/`）
2. 继承 `Bot` 基类实现新的 Bot
3. 修改 `bot_factory.py` 支持新的 `bot_type`

---

## 11. 注意事项

1. **敏感信息**: `config.json` 和 `cookies.json` 包含敏感信息，已添加到 `.gitignore`
2. **数据库**: SQLite 数据库文件不应提交到版本控制
3. **日志**: 日志文件自动轮转（10MB 上限）
4. **性能**: 生产环境建议关闭 SQL 日志（`echo=False`）
5. **资源清理**: 应用退出时会自动清理 WebSocket 连接和线程池资源

---

## 12. 依赖清单

```toml
[project.dependencies]
playwright = ">=1.52.0"
websockets = ">=10.4"
requests = ">=2.28.0"
PySocks = ">=1.7.1"
cozepy = ">=0.15.0"
flask = ">=3.1.0"
flask-sqlalchemy = ">=3.1.1"
flask-cors = ">=5.0.1"
pyqt6 = ">=6.9.0"
pyqt6-fluent-widgets = ">=1.8.1"
```
