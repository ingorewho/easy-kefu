# 智能客服系统 - 深度研究文档

> 版本: 1.1.0
> 研究日期: 2026-03-16
> Python: 3.11+

---

## 1. 项目概述

### 1.1 产品定位

**智能客服系统** 是一款基于 Python + PyQt6 开发的桌面应用程序，为拼多多商家提供 AI 自动化客服解决方案。

### 1.2 核心功能

- **AI 智能回复**: 集成多平台 AI (Coze/Kimi/Qwen)，自动回复用户咨询
- **RAG 知识库**: 支持本地知识库检索、Web 搜索增强、知识自动沉淀
- **多渠道管理**: 支持多店铺、多账号统一管理
- **实时消息处理**: WebSocket 实时接收和发送消息
- **关键词管理**: 自定义关键词触发转人工客服
- **营业时间控制**: 非营业时间自动缓存消息，工作时间恢复处理
- **可视化监控**: 实时查看消息处理状态和日志

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      UI 层 (PyQt6)                          │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ 自动回复  │ 关键词   │ 账号管理  │ 日志管理  │             │
│  │  AI测试  │ 知识库   │ 聊天历史  │  设置    │             │
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
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ CozeBot  │  │ KimiBot  │  │ QwenBot  │  │ BotWith  │   │
│  │          │  │(Moonshot)│  │(DashScope│  │   RAG    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    数据持久化层                             │
│         ┌─────────────────────────────────────┐            │
│         │   SQLite 数据库 (SQLAlchemy ORM)    │            │
│         │   - 渠道、店铺、账号、关键词表       │            │
│         │   - 聊天消息历史记录                 │            │
│         └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | 核心文件 |
|-----|------|---------|
| `Agent/` | AI 机器人实现 | `bot_factory.py`, `CozeAgent/bot.py`, `bot_with_rag.py` |
| `Channel/` | 电商平台接口 | `pinduoduo/pdd_chnnel.py` |
| `Message/` | 消息队列处理 | `message_queue.py`, `message_consumer.py`, `message_handler.py` |
| `database/` | 数据持久化 | `models.py`, `db_manager.py` |
| `ui/` | 用户界面 | `main_ui.py`, `auto_reply_ui.py`, `knowledge_base_ui.py` |
| `utils/` | 工具函数 | `logger.py`, `performance_monitor.py`, `business_hours_queue.py` |
| `knowledge_base/` | RAG 知识库 | `rag_retriever.py`, `vector_store.py`, `document_processor.py` |

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

### 3.2 处理器链流程

```
消息进入处理器链
       ↓
BusinessHoursHandler (营业时间检查)
   ├─→ 非营业时间 → 缓存到队列，不回复
   └─→ 营业时间 → 继续
       ↓
CustomerServiceTransferHandler (转人工检查)
   ├─→ 触发关键词 → 转接人工客服
   └─→ 未触发 → 继续
       ↓
AIAutoReplyHandler (AI 自动回复)
   ├─→ 保存消息到数据库
   ├─→ 加载历史对话上下文
   ├─→ 调用 AI Bot 生成回复
   ├─→ 发送回复到拼多多
   └─→ 更新数据库状态
```

### 3.3 RAG 知识库流程

```
用户消息
   ↓
BotWithRAG.reply()
   ↓
├─→ 提取文本查询内容
├─→ 查询本地 ChromaDB 向量数据库
├─→ 如果本地无结果 → Web 搜索 (SerpAPI)
├─→ 如果 Web 搜索置信度高 → 自动沉淀到本地知识库
├─→ 构建增强提示词（检索结果 + 对话历史 + 原始查询）
↓
调用基础 Bot 生成回复
```

### 3.4 非工作时间消息处理流程

```
用户发送消息 (非工作时间)
   ↓
BusinessHoursHandler.can_handle() → True
   ↓
BusinessHoursHandler.handle()
   ↓
创建 QueuedMessage 对象
   ↓
添加到 business_hours_queue
   ↓
等待，不回复、不打开会话

... 时间流逝，进入工作时间 ...

BusinessHoursQueueManager._monitor_loop()
   ↓
检测到进入工作时间
   ↓
遍历处理队列中的消息
   ↓
将消息标记 _from_business_hours_queue = True
   ↓
放入正常处理队列
   ↓
处理器链处理 (跳过 BusinessHoursHandler)
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
async def put(self, context: Context) -> str              # 入队，返回消息ID
async def get(self, timeout=None) -> Dict                 # 出队
async def cleanup_expired()                               # 清理过期消息
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
   - 非营业时间自动将消息缓存到队列
   - 工作时间恢复后逐一处理
   - 默认营业时间: 08:00 - 23:00

2. **CustomerServiceTransferHandler** - 客服转接
   - 触发关键词: '人工客服', '转人工', '人工', '客服', '投诉', '举报', '不满意', '解决不了', '要求赔偿'
   - 自动将会话转接给人工客服

3. **AIAutoReplyHandler** - AI 自动回复
   - 调用 AI Bot 生成回复
   - 支持文本、图片、视频、商品咨询等多种消息类型
   - 30 秒超时控制

### 4.2 拼多多渠道适配器

**文件**: `Channel/pinduoduo/pdd_chnnel.py`

**核心功能**:
- WebSocket 连接管理（`wss://m-ws.pinduoduo.com/`）
- 多店铺、多账号支持
- 消息接收与解析
- 并发控制（信号量限制最大并发数 50）
- 非工作时间队列集成

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

### 4.3 AI 引擎层

#### 4.3.1 CozeBot

**文件**: `Agent/CozeAgent/bot.py`

**工作流程**:
1. 接收 Context 对象
2. 提取用户 ID: `f"{shop_id}_{from_uid}"`
3. 获取或创建会话（SQLite 存储 `user_session.db`）
4. 调用 Coze API:
   - 创建消息（`conversations.messages.create`）
   - 发起聊天（`chat.create_and_poll`）
5. 解析回复，返回 Reply 对象

#### 4.3.2 KimiBot

**文件**: `Agent/KimiAgent/bot.py`

**特点**:
- 使用 Moonshot AI API (OpenAI 兼容接口)
- 支持多轮对话历史
- 自动处理商品咨询和订单信息

#### 4.3.3 QwenBot

**文件**: `Agent/QwenAgent/bot.py`

**特点**:
- 使用阿里云百炼 (DashScope) API
- 支持 qwen-turbo/plus/max 模型

#### 4.3.4 BotWithRAG

**文件**: `Agent/bot_with_rag.py`

**功能**:
- 包装基础 Bot，添加 RAG 能力
- 混合检索：本地向量库 + Web 搜索
- 自动增强提示词（含对话历史）
- AI 回复风格配置（口语化/正式、字数限制、标点控制）

**配置项**:
```python
ai_system_prompt = "你是电商客服，回复要简短口语化，不超过20字"
ai_reply_max_length = 20
ai_reply_style = "casual"  # casual(口语化) | formal(正式)
ai_reply_no_punctuation = True
ai_reply_delay_min = 2
ai_reply_delay_max = 10
```

### 4.4 知识库系统

**核心组件**:
- `knowledge_base/rag_retriever.py` - RAG 检索器（混合检索）
- `knowledge_base/vector_store.py` - ChromaDB 向量存储
- `knowledge_base/document_processor.py` - 文档加载解析
- `knowledge_base/ai_document_splitter.py` - AI 智能文档拆分
- `knowledge_base/knowledge_extractor.py` - 知识抽取
- `knowledge_base/knowledge_sink.py` - 知识沉淀
- `knowledge_base/web_search.py` - Web 搜索 (SerpAPI)

**支持的文档格式**:
- PDF (pypdf)
- Word (python-docx)
- TXT/Markdown

**向量化**:
- 使用 sentence-transformers
- 默认模型: all-MiniLM-L6-v2

**混合检索流程**:
```python
# 1. 本地向量库检索
local_results = vector_store.search(query, top_k=top_k)

# 2. 如果本地无结果且启用 Web 搜索
if not local_results and enable_web_fallback:
    web_results = web_search.search(query)
    # 3. 知识沉淀（如果置信度高）
    if confidence >= min_confidence:
        knowledge_sink.save(query, web_results)

# 4. 构建增强提示词
enhanced_prompt = build_prompt(query, local_results + web_results)
```

### 4.5 非工作时间队列系统

**文件**: `utils/business_hours_queue.py`

**核心功能**:
- 单例模式管理队列
- 定时检查工作时间状态（默认 60 秒）
- 消息缓存和恢复处理

**QueuedMessage 结构**:
```python
@dataclass
class QueuedMessage:
    msg_id: str
    context: Any              # Context 对象
    queue_name: str
    shop_id: str
    user_id: str
    username: str
    from_uid: str
    nickname: str
    timestamp: float
    added_at: datetime
```

### 4.6 数据库设计

**文件**: `database/models.py`

**实体关系**:

```
Channel（渠道表）
    ↓ 1:N
Shop（店铺表）
    ↓ 1:N
Account（账号表）
    ↓ 1:N
ChatMessage（聊天消息表）

Keyword（关键词表）- 独立表
```

**ChatMessage 表结构**:

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| account_id | ForeignKey | 账号外键 |
| shop_id | String | 店铺ID |
| from_uid | String | 用户标识 |
| nickname | String | 用户昵称 |
| message_type | String | 消息类型 |
| user_content | Text | 用户消息内容 |
| ai_reply | Text | AI 回复内容 |
| conversation_id | String | 会话ID |
| status | Integer | 0-未回复, 1-已回复, 2-转人工, 3-失败 |
| created_at | DateTime | 创建时间 |
| replied_at | DateTime | AI回复时间 |

---

## 5. 配置系统

### 5.1 配置文件 (config.py)

**支持的 AI 引擎配置**:

```python
# Coze 配置
coze_api_base = "https://api.coze.cn"
coze_token = ""
coze_bot_id = ""

# Kimi 配置
kimi_api_base = "https://api.moonshot.cn/v1"
kimi_api_key = ""
kimi_model = "kimi-k2.5"

# Qwen 配置
qwen_api_base = "https://dashscope.aliyuncs.com/api/v1"
qwen_api_key = ""
qwen_model = "qwen-turbo"

# RAG 配置
enable_rag = False
rag_top_k = 5
rag_score_threshold = 0.5
enable_web_search_fallback = True
web_search_provider = "serpapi"
serpapi_key = ""
web_search_min_confidence = 0.6
web_search_auto_sink = True

# 知识库文档拆分配置
kb_split_mode = "ai"           # ai | simple | none
kb_ai_split_max_chunk_size = 800
kb_simple_chunk_size = 500
```

### 5.2 环境变量

| 变量 | 说明 | 默认值 |
|-----|------|--------|
| `LOG_LEVEL` | 日志级别 | `info` |
| `ENABLE_STRUCTURED_LOGS` | 启用结构化日志 | `false` |

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

### 6.4 数据库连接池

```python
# DatabaseManager 配置
pool_size = 10
max_overflow = 20
pool_pre_ping = True      # 连接健康检查
pool_recycle = 3600       # 连接回收时间（秒）
```

---

## 7. 用户界面

### 7.1 界面结构

**文件**: `ui/main_ui.py`

| 界面 | 功能 | 文件 |
|-----|------|------|
| 自动回复 | 监控实时消息处理 | `auto_reply_ui.py` |
| 关键词管理 | 配置转人工关键词 | `keyword_ui.py` |
| 账号管理 | 管理店铺账号 | `user_ui.py` |
| 聊天历史 | 查看消息记录 | `chat_history_ui.py` |
| AI 测试 | 测试 AI 回复效果 | `ai_test_ui.py` |
| 知识库 | 管理 RAG 知识库 | `knowledge_base_ui.py` |
| 日志管理 | 查看系统日志 | `log_ui.py` |
| 设置 | 配置 API 参数 | `setting_ui.py` |

### 7.2 技术栈

- PyQt6 - GUI 框架
- PyQt6-Fluent-Widgets - 现代化 UI 组件库
- FluentIcon - 图标系统

---

## 8. 设计模式

| 模式 | 应用位置 |
|-----|---------|
| 工厂模式 | `bot_factory.py` - 创建不同类型的 Bot |
| 策略模式 | `MessageHandler` - 多种处理器实现 |
| 观察者模式 | WebSocket 消息监听与处理 |
| 责任链模式 | Handler 链依次处理消息 |
| 单例模式 | `DatabaseManager`, `BusinessHoursQueueManager` |
| 装饰器模式 | `BotWithRAG` - 为 Bot 添加 RAG 能力 |
| 上下文模式 | `Context` 对象贯穿消息生命周期 |

---

## 9. 扩展性设计

### 9.1 添加新的电商平台

1. 在 `Channel/` 下创建新目录（如 `jd/`, `taobao/`）
2. 继承 `Channel` 基类实现渠道适配器
3. 实现 `send_message`, `connect`, `disconnect` 等方法

### 9.2 切换 AI 引擎

1. 在 `Agent/` 下创建新目录（如 `OpenAIAgent/`）
2. 继承 `Bot` 基类实现新的 Bot
3. 修改 `bot_factory.py` 支持新的 `bot_type`

---

## 10. 关键代码片段

### 10.1 消息入队

```python
# Message/__init__.py
async def put_message(queue_name: str, context: Context) -> str:
    queue = message_queue_manager.get_or_create_queue(queue_name)
    return await queue.put(context)
```

### 10.2 创建 Bot

```python
# Agent/bot_factory.py
from config import config

def create_bot(bot_type: str = None, enable_rag: bool = None):
    bot_type = bot_type or config.get("bot_type", "coze")
    enable_rag = enable_rag if enable_rag is not None else config.get("enable_rag", False)

    if bot_type == "coze":
        from Agent.CozeAgent.bot import CozeBot
        base_bot = CozeBot()
    elif bot_type == "kimi":
        from Agent.KimiAgent.bot import KimiBot
        base_bot = KimiBot()
    elif bot_type == "qwen":
        from Agent.QwenAgent.bot import QwenBot
        base_bot = QwenBot()
    else:
        raise RuntimeError(f"Invalid bot type: {bot_type}")

    if enable_rag:
        from Agent.bot_with_rag import BotWithRAG
        return BotWithRAG(base_bot, enable_rag=True)

    return base_bot
```

### 10.3 处理器链

```python
# Message/message_handler.py
def handler_chain(use_ai: bool = True, businessHours: Dict[str, str] = None):
    handlers = [
        BusinessHoursHandler(business_hours=businessHours),
        CustomerServiceTransferHandler()
    ]
    if use_ai:
        handlers.append(create_ai_handler())
    return handlers
```

### 10.4 RAG 增强提示词构建

```python
# Agent/bot_with_rag.py
def _format_chat_history(self, chat_history: list) -> str:
    if not chat_history:
        return ""

    context_parts = ["\n【对话上下文】"]

    for msg in chat_history:
        user_content = msg.get('user_content', '')
        ai_reply = msg.get('ai_reply', '')

        if user_content:
            if len(user_content) > 50:
                user_content = user_content[:47] + "..."
            context_parts.append(f"用户：{user_content}")

        if ai_reply:
            if len(ai_reply) > 50:
                ai_reply = ai_reply[:47] + "..."
            context_parts.append(f"客服：{ai_reply}")

    return "\n".join(context_parts)
```

### 10.5 非工作时间队列处理

```python
# utils/business_hours_queue.py
async def _monitor_loop(self):
    last_state = None

    while self._running:
        current_state = self._is_business_hours()

        if current_state != last_state:
            if current_state:
                self.logger.info("进入工作时间，开始处理队列消息")
                await self._process_queue()
            else:
                self.logger.info("进入非工作时间，新消息将被缓存")
            last_state = current_state
        elif current_state and self.message_queue:
            await self._process_queue()

        await asyncio.sleep(self.check_interval)
```

---

## 11. 依赖清单

```toml
[project.dependencies]
playwright = ">=1.52.0"          # 浏览器自动化
websockets = ">=10.4"           # WebSocket 通信
requests = ">=2.28.0"           # HTTP 请求
cozepy = ">=0.15.0"             # Coze AI SDK
openai = ">=1.0.0"              # Kimi/OpenAI SDK
dashscope = ">=1.0.0"           # Qwen SDK
pyqt6 = ">=6.9.0"               # GUI 框架
pyqt6-fluent-widgets = ">=1.8.1" # UI 组件
chromadb = ">=0.4.0"            # 向量数据库
sentence-transformers = ">=2.2.0" # 文本向量化
openpyxl = ">=3.0.0"            # Excel 导出
sqlalchemy = ">=2.0.0"          # ORM
```

---

## 12. 注意事项

1. **敏感信息**: `config.json` 和 `cookies.json` 包含敏感信息，已添加到 `.gitignore`
2. **数据库**: SQLite 数据库文件不应提交到版本控制
3. **日志**: 日志文件自动轮转（10MB 上限）
4. **性能**: 生产环境建议关闭 SQL 日志（`echo=False`）
5. **资源清理**: 应用退出时会自动清理 WebSocket 连接和线程池资源
6. **并发安全**: 消息队列使用 asyncio.Lock 保证线程安全
7. **Bot 热刷新**: AIAutoReplyHandler 会在每次处理前检查配置变化，自动刷新 Bot 实例
