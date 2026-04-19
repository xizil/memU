# MemU 源代码分析文档

> **源码路径**: [src/memu/](src/memu/)
>
> **核心模块**:
> - [app/service.py](src/memu/app/service.py) - MemoryService 核心服务
> - [app/memorize.py](src/memu/app/memorize.py) - 记忆学习模块
> - [app/retrieve.py](src/memu/app/retrieve.py) - 记忆检索模块
> - [database/models.py](src/memu/database/models.py) - 数据模型
> - [workflow/](src/memu/workflow/) - 工作流引擎

---

## 快速导航

| 章节 | 源码文件 | 说明 |
|------|----------|------|
| [第一章 核心服务](#第一章-核心服务-appServicepy) | [service.py](src/memu/app/service.py) | MemoryService 入口 |
| [第二章 记忆模块](#第二章-记忆模块-appmemorizepy) | [memorize.py](src/memu/app/memorize.py) | memorize 工作流 |
| [第三章 检索模块](#第三章-检索模块-appretrievepy) | [retrieve.py](src/memu/app/retrieve.py) | RAG/LLM 检索 |
| [第四章 数据模型](#第四章-数据模型-databasemodelspy) | [models.py](src/memu/database/models.py) | 三层架构 |
| [第五章 数据库层](#第五章-数据库层) | [database/](src/memu/database/) | Repository 模式 |
| [第六章 LLM 模块](#第六章-llm-模块) | [llm/](src/memu/llm/) | 多后端支持 |
| [第七章 工作流引擎](#第七章-工作流引擎) | [workflow/](src/memu/workflow/) | Pipeline 管理 |
| [第八章 提示词系统](#第八章-提示词系统) | [prompts/](src/memu/prompts/) | 模板管理 |

---

## 项目概述

MemU (memU-py) 是一个 Python + Rust 混合项目,是一个用于 24/7 AI 代理的 AI 记忆框架。核心代码位于 `src/memu/` 目录。

### 技术栈

- **Python**: 3.13+
- **Rust**: 通过 PyO3/Maturin 实现 Python 扩展模块
- **数据库**: 支持 InMemory、PostgreSQL (pgvector)、SQLite
- **依赖**: Pydantic, SQLModel, httpx, numpy, pendulum, alembic

### 项目结构

```
/Users/samj/vscode/memU/
├── src/
│   ├── lib.rs              # Rust 入口点
│   └── memu/
│       ├── app/            # 核心应用逻辑 (service, memorize, retrieve, crud, patch)
│       ├── blob/           # 文件存储 (LocalFS)
│       ├── client/         # OpenAI 客户端包装器
│       ├── database/       # 数据库抽象层
│       │   ├── inmemory/   # 内存存储实现
│       │   ├── postgres/   # PostgreSQL 实现
│       │   ├── sqlite/     # SQLite 实现
│       │   └── repositories/ # 仓储模式接口
│       ├── embedding/      # 向量化客户端
│       ├── integrations/    # 第三方集成 (LangGraph)
│       ├── llm/            # LLM 客户端封装
│       │   └── backends/  # 多后端支持 (OpenAI, Grok, Doubao, OpenRouter)
│       ├── prompts/        # 提示词模板
│       ├── utils/          # 工具函数
│       └── workflow/       # 工作流引擎
├── tests/                  # 测试文件
├── examples/               # 示例代码
└── pyproject.toml          # Python 项目配置
```

---

## 第一章: 核心服务 (app/service.py)

> **源码**: [src/memu/app/service.py](src/memu/app/service.py)

### 1.1 UML 类图

> **说明**: MemoryService 是整个框架的核心入口类,继承三大 Mixin 提供完整功能。

```uml
@startuml
skinparam backgroundColor #FEFEFE
skinparam classAttributeIconSize 0

class MemoryService {
    + llm_profiles: LLMProfilesConfig  ''LLM 配置集合(支持多 profile)"
    + user_config: UserConfig  ''用户配置"
    + database: Database  ''数据库后端"
    + blob_config: BlobConfig  ''文件存储配置"
    + memorize_config: MemorizeConfig  ''记忆配置"
    + retrieve_config: RetrieveConfig  ''检索配置"
    + _workflow_runner: WorkflowRunner  ''工作流运行器"
    + _pipelines: PipelineManager  ''管道管理器"
    --
    + memorize(resource_url, modality, user): dict  ''记忆学习入口"
    + retrieve(queries, where): dict  ''记忆检索入口"
    + create_memory_item(...): dict  ''创建记忆项"
    + update_memory_item(...): dict  ''更新记忆项"
    + delete_memory_item(...): dict  ''删除记忆项"
    + list_memory_items(...): dict  ''列出记忆项"
    --
    + intercept_before_llm_call(fn, ...): LLMInterceptorHandle  ''LLM 调用前拦截"
    + intercept_after_llm_call(fn, ...): LLMInterceptorHandle  ''LLM 调用后拦截"
    + intercept_before_workflow_step(fn, ...): WorkflowInterceptorHandle  ''工作流步骤前拦截"
}

class Context {
    + categories_ready: bool  ''分类是否已初始化"
    + category_ids: list[str]  ''已初始化的分类 ID"
    + category_name_to_id: dict[str, str]  ''分类名到 ID 的映射"
    + category_init_task: asyncio.Task  ''异步初始化任务"
}

class PipelineManager {
    + available_capabilities: set  ''可用能力集(llm/vector/db/io/vision)"
    + llm_profiles: set  ''已注册的 LLM profile"
    --
    + register(workflow_name, steps, initial_state_keys)  ''注册工作流"
    + build(workflow_name): list[WorkflowStep]  ''构建工作流步骤链"
    + config_step(pipeline, step_id, configs): int  ''配置步骤参数"
    + insert_after(pipeline, target, new_step): int  ''在目标步骤后插入"
    + replace_step(pipeline, target, new_step): int  ''替换步骤"
}

MemoryService *-- Context : ''持有运行时上下文"
MemoryService *-- PipelineManager : ''管理所有工作流"
MemoryService o-- Database : ''使用数据库后端"
MemoryService o-- "many" LLMClientWrapper : ''缓存 LLM 客户端"

note top of MemoryService
    **核心职责**:
    1. 配置管理 - 统一管理 LLM、数据库、存储等配置
    2. 客户端工厂 - 按需创建 LLM 客户端 (支持多 profile)
    3. 拦截器系统 - 在 LLM 调用和工作流步骤前后注入逻辑
    4. 工作流编排 - 管理 memorize/retrieve 等工作流的执行

    **继承的 Mixin**:
    - MemorizeMixin: 记忆学习功能
    - RetrieveMixin: 记忆检索功能
    - CRUDMixin: 记忆项的增删改查
end note

note top of Context
    **用途**: 管理分类初始化的异步状态
    - 支持延迟初始化
    - 支持多用户/多租户场景隔离
end note

note top of PipelineManager
    **可用能力**:
    - llm: 调用 LLM
    - vector: 向量检索
    - db: 数据库操作
    - io: 文件读写
    - vision: 视觉处理
end note
@enduml
```

### 1.2 MemoryService 类

### 1.1 MemoryService 类

`MemoryService` 是整个框架的核心入口,继承自 `MemorizeMixin`, `RetrieveMixin`, 和 `CRUDMixin`。

#### 初始化配置

```python
class MemoryService(MemorizeMixin, RetrieveMixin, CRUDMixin):
    def __init__(
        self,
        *,
        llm_profiles: LLMProfilesConfig | dict[str, Any] | None = None,
        blob_config: BlobConfig | dict[str, Any] | None = None,
        database_config: DatabaseConfig | dict[str, Any] | None = None,
        memorize_config: MemorizeConfig | dict[str, Any] | None = None,
        retrieve_config: RetrieveConfig | dict[str, Any] | None = None,
        workflow_runner: WorkflowRunner | str | None = None,
        user_config: UserConfig | dict[str, Any] | None = None,
    )
```

#### 核心属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `llm_profiles` | LLMProfilesConfig | LLM 配置集合,支持多 profile |
| `database` | Database | 数据库后端实例 |
| `blob_config` | BlobConfig | 文件存储配置 |
| `memorize_config` | MemorizeConfig | 记忆配置 |
| `retrieve_config` | RetrieveConfig | 检索配置 |
| `category_configs` | list[CategoryConfig] | 记忆分类配置 |
| `_workflow_runner` | WorkflowRunner | 工作流运行器 |
| `_pipelines` | PipelineManager | 管道管理器 |

#### LLM 客户端管理

```python
def _init_llm_client(self, config: LLMConfig | None = None) -> Any
```

支持三种客户端后端:
- **sdk**: 官方 OpenAI SDK
- **httpx**: HTTP 客户端 (通用)
- **lazyllm_backend**: LazyLLM 客户端

```python
def _get_llm_client(self, profile: str | None = None, step_context: Mapping[str, Any] | None = None) -> Any
```

#### 拦截器系统

MemoryService 提供 LLM 调用和工作流步骤的拦截能力:

```python
# LLM 拦截器
def intercept_before_llm_call(self, fn, name=None, priority=0, where=None) -> LLMInterceptorHandle
def intercept_after_llm_call(self, fn, name=None, priority=0, where=None) -> LLMInterceptorHandle
def intercept_on_error_llm_call(self, fn, name=None, priority=0, where=None) -> LLMInterceptorHandle

# 工作流拦截器
def intercept_before_workflow_step(self, fn, name=None) -> WorkflowInterceptorHandle
def intercept_after_workflow_step(self, fn, name=None) -> WorkflowInterceptorHandle
def intercept_on_error_workflow_step(self, fn, name=None) -> WorkflowInterceptorHandle
```

#### 管道管理

```python
def configure_pipeline(self, *, step_id: str, configs: Mapping[str, Any], pipeline: str = "memorize") -> int
def insert_step_after(self, *, target_step_id: str, new_step: WorkflowStep, pipeline: str = "memorize") -> int
def insert_step_before(self, *, target_step_id: str, new_step: WorkflowStep, pipeline: str = "memorize") -> int
def replace_step(self, *, target_step_id: str, new_step: WorkflowStep, pipeline: str = "memorize") -> int
def remove_step(self, *, target_step_id: str, pipeline: str = "memorize") -> int
```

### 1.2 配置模型 (app/settings.py)

> **源码**: [src/memu/app/settings.py](src/memu/app/settings.py)
>
> **说明**: 配置文件采用 Pydantic 模型,支持字典和模型两种配置方式,自动验证类型和默认值。

#### LLMConfig - LLM 配置

```python
class LLMConfig(BaseModel):
    """LLM 客户端配置模型"""
    provider: str = "openai"              # LLM 提供商标识 (openai/grok/doubao 等)
    base_url: str = "https://api.openai.com/v1"  # API 基础地址
    api_key: str = "OPENAI_API_KEY"      # API 密钥
    chat_model: str = "gpt-4o-mini"      # 聊天模型名称
    client_backend: str = "sdk"           # 客户端后端类型: 'sdk'(官方SDK) / 'httpx'(HTTP) / 'lazyllm_backend'
    lazyllm_source: LazyLLMSource = Field(default=LazyLLMSource())  # LazyLLM 源配置
    endpoint_overrides: dict[str, str] = {}  # API 端点覆盖 (用于兼容不同提供商)
    embed_model: str = "text-embedding-3-small"  # 向量化模型
    embed_batch_size: int = 1             # 向量化批处理大小
```

**配置示例**:
```python
# 使用 OpenAI SDK
LLMConfig(provider="openai", chat_model="gpt-4o", client_backend="sdk")

# 使用兼容 OpenAI 的 HTTP API (如 Grok)
LLMConfig(provider="grok", base_url="https://api.grok.ai/v1",
          chat_model="grok-2", client_backend="httpx")
```

#### LazyLLMSource - LazyLLM 源配置

```python
class LazyLLMSource(BaseModel):
    """
    LazyLLM 集成配置

    LazyLLM 是一个大模型懒加载框架,支持:
    - llm_source: 主 LLM 源
    - embed_source: 向量模型源
    - vlm_source: 视觉语言模型源 (用于图片/视频分析)
    - stt_source: 语音转文本源 (用于音频处理)
    """
    source: str | None        # 默认数据源 (当其他源未指定时使用)
    llm_source: str | None   # LLM 数据源
    embed_source: str | None  # 向量化数据源
    vlm_source: str | None    # 视觉模型数据源
    stt_source: str | None    # 语音转文本数据源
    vlm_model: str = "qwen-vl-plus"   # 视觉语言模型名称
    stt_model: str = "qwen-audio-turbo"  # 语音识别模型名称
```

#### 数据库配置

```python
class MetadataStoreConfig(BaseModel):
    """
    元数据存储配置

    支持三种存储后端:
    - inmemory: 内存存储 (仅测试用,数据不持久化)
    - postgres: PostgreSQL 数据库 (生产环境推荐)
    - sqlite: SQLite 数据库 (轻量级场景)
    """
    provider: Literal["inmemory", "postgres", "sqlite"] = "inmemory"  # 存储提供商
    ddl_mode: Literal["create", "validate"] = "create"  # DDL 模式: create(自动创建表)/validate(验证表结构)
    dsn: str | None  # 数据库连接字符串 (Data Source Name)

class VectorIndexConfig(BaseModel):
    """
    向量索引配置

    向量索引用于高效相似度检索:
    - bruteforce: 暴力搜索 (简单,适合小数据量)
    - pgvector: PostgreSQL 向量索引 (生产环境推荐)
    - none: 禁用向量检索
    """
    provider: Literal["bruteforce", "pgvector", "none"] = "bruteforce"  # 向量索引类型
    dsn: str | None  # 向量数据库连接字符串 (pgvector 使用)

class DatabaseConfig(BaseModel):
    """数据库完整配置"""
    metadata_store: MetadataStoreConfig   # 元数据存储配置
    vector_index: VectorIndexConfig | None  # 向量索引配置 (可选)
```

**配置示例**:
```python
# 开发环境 - 使用内存存储
DatabaseConfig(
    metadata_store=MetadataStoreConfig(provider="inmemory")
)

# 生产环境 - PostgreSQL + pgvector
DatabaseConfig(
    metadata_store=MetadataStoreConfig(provider="postgres", dsn="postgresql://user:pass@localhost:5432/memu"),
    vector_index=VectorIndexConfig(provider="pgvector", dsn="postgresql://user:pass@localhost:5432/memu")
)
```

#### 记忆配置 (MemorizeConfig)

```python
class MemorizeConfig(BaseModel):
    """
    记忆学习配置

    控制如何从资源中提取和存储记忆。
    """

    # 分类分配阈值 - 记忆与分类的匹配分数阈值 (0.0-1.0)
    category_assign_threshold: float = 0.25

    # 多模态预处理提示词 - 按模态 (conversation/video/image/audio/document) 配置
    multimodal_preprocess_prompts: dict[str, str | CustomPrompt]

    # 预处理步骤使用的 LLM profile
    preprocess_llm_profile: str = "default"

    # 要提取的记忆类型列表
    # 可选值: profile(用户信息) / event(事件) / knowledge(知识) / behavior(行为) / skill(技能) / tool(工具)
    memory_types: list[str] = ["profile", "event"]

    # 各记忆类型的提取提示词
    memory_type_prompts: dict[str, str | CustomPrompt]

    # 记忆提取步骤使用的 LLM profile
    memory_extract_llm_profile: str = "default"

    # 记忆分类配置列表
    memory_categories: list[CategoryConfig]

    # 分类摘要更新提示词 (模板)
    default_category_summary_prompt: str | CustomPrompt

    # 分类摘要目标长度 (字符数)
    default_category_summary_target_length: int = 400

    # 分类更新步骤使用的 LLM profile
    category_update_llm_profile: str = "default"

    # 是否启用记忆项引用 (在分类摘要中生成 [ref:ITEM_ID] 引用)
    enable_item_references: bool = False

    # 是否启用强化学习追踪 (记录记忆被访问/使用的次数)
    enable_item_reinforcement: bool = False
```

**配置示例**:
```python
MemorizeConfig(
    memory_types=["profile", "event", "knowledge", "skill"],
    memory_categories=[
        CategoryConfig(name="用户偏好", description="用户的个人偏好和习惯"),
        CategoryConfig(name="工作相关", description="工作内容和项目信息"),
    ],
    enable_item_references=True,  # 启用引用追踪
)
```

#### 检索配置 (RetrieveConfig)

```python
class RetrieveConfig(BaseModel):
    """
    记忆检索配置

    控制如何从记忆系统中检索相关信息。
    """

    # 检索方法:
    # - "rag": 向量相似度检索 (RAG),快速但依赖向量质量
    # - "llm": LLM 深度推理排序,更智能但 token 消耗更大
    method: Literal["rag", "llm"] = "rag"

    # 是否启用意图路由 (判断查询是否真正需要检索)
    route_intention: bool = True

    # 分类检索配置
    category: RetrieveCategoryConfig

    # 记忆项检索配置
    item: RetrieveItemConfig

    # 资源检索配置
    resource: RetrieveResourceConfig

    # 是否启用充分性检查 (每层检索后判断是否足够)
    sufficiency_check: bool = True

    # 充分性检查提示词 (用于 LLM 判断检索结果是否足够)
    sufficiency_check_prompt: str

    # 充分性检查使用的 LLM profile
    sufficiency_check_llm_profile: str = "default"

    # LLM 排序模式使用的 LLM profile (仅 method="llm" 时)
    llm_ranking_llm_profile: str = "default"
```

#### 检索子配置

```python
class RetrieveItemConfig(BaseModel):
    """
    记忆项检索子配置
    """

    enabled: bool = True              # 是否启用记忆项检索
    top_k: int = 5                   # 返回前 K 条最相关结果

    # 是否使用分类引用感知检索
    # 启用后,检索会考虑分类摘要中的 [ref:ITEM_ID] 引用
    use_category_references: bool = False

    # 排序方式:
    # - "similarity": 余弦相似度排序 (默认)
    # - "salience": 相关性+时效性综合排序 (更智能)
    ranking: Literal["similarity", "salience"] = "similarity"

    # 时间衰减半衰期 (天) - 仅 salience 模式
    # 记忆随时间推移逐渐降低权重,30天时权重减半
    recency_decay_days: float = 30.0
```

**检索配置示例**:
```python
RetrieveConfig(
    method="rag",
    route_intention=True,
    sufficiency_check=True,
    item=RetrieveItemConfig(
        top_k=10,
        ranking="salience",
        recency_decay_days=14,  # 两周半衰期
    )
)
```

### 1.3 Context 数据类

```python
@dataclass
class Context:
    categories_ready: bool = False
    category_ids: list[str] = field(default_factory=list)
    category_name_to_id: dict[str, str] = field(default_factory=dict)
    category_init_task: asyncio.Task | None = None
```

---

## 第二章: 记忆模块 (app/memorize.py)

> **源码**: [src/memu/app/memorize.py](src/memu/app/memorize.py)

### 2.1 Memorize 工作流时序图

> **说明**: memorize 工作流将原始资源转换为结构化记忆,经过 6 个处理阶段。

```uml
@startuml
participant "Client" as C #lightblue
participant "MemoryService" as S #lightblue
participant "WorkflowEngine" as W #lightyellow
participant "Ingest\n(摄取资源)" as I #lightgreen
participant "Preprocess\n(多模态预处理)" as P #lightgreen
participant "Extract\n(记忆提取)" as E #lightgreen
participant "Categorize\n(分类关联)" as Cat #lightgreen
participant "Persist\n(持久化索引)" as PS #lightgreen
database "Database" as DB #lightgray

C -> S: **memorize**(resource_url, modality)
S -> S: _ensure_categories_ready() ''确保分类已初始化"
S -> W: _run_workflow("memorize", state)

note over W
    **工作流步骤**:
    1. ingest_resource - 获取资源
    2. preprocess_multimodal - 预处理
    3. extract_items - 提取记忆
    4. dedupe_merge - 去重合并
    5. categorize_items - 分类关联
    6. persist_index - 持久化索引
    7. build_response - 构建响应
end note

W -> I: _memorize_ingest_resource()
I -> DB: fs.fetch(url, modality) ''下载或读取本地资源"
I --> W: (local_path, raw_text)

W -> P: _memorize_preprocess_multimodal()
P -> P: _dispatch_preprocessor(modality) ''根据模态分发处理器"
alt conversation (对话)
    P -> P: _preprocess_conversation()
    P -> P: _parse_conversation_preprocess_with_segments() ''解析对话分段"
else video (视频)
    P -> P: _preprocess_video()
    P -> P: VideoFrameExtractor.extract_middle_frame() ''提取中间帧"
else image (图片)
    P -> P: _preprocess_image() ''使用 Vision API 分析"
end
P --> W: preprocessed_resources ''返回预处理后的资源列表"

W -> E: _memorize_extract_items()
loop **每种 memory_type** (profile/event/knowledge/behavior/skill/tool)
    E -> E: _generate_structured_entries()
    E -> DB: LLM.chat(prompt) ''调用 LLM 提取结构化记忆"
end
E --> W: resource_plans ''返回资源计划列表"

W -> Cat: _memorize_categorize_items()
loop **每条 resource_plan**
    Cat -> Cat: _create_resource_with_caption() ''创建资源记录"
    Cat -> DB: resource_repo.create() ''存储资源"
    Cat -> Cat: _persist_memory_items() ''持久化记忆项"
    Cat -> DB: memory_item_repo.create() ''存储记忆项"
    Cat -> DB: category_item_repo.link() ''建立分类关联"
end
Cat --> W: (resources, items, relations)

W -> PS: _memorize_persist_and_index()
PS -> PS: _update_category_summaries() ''更新分类摘要"
PS -> DB: category_repo.update() ''持久化分类更新"
PS --> W: updated_summaries

W -> W: _memorize_build_response() ''构建最终响应"
W --> S: WorkflowState
S --> C: **response** (resources, items, categories, relations)

@enduml
```

### 2.2 MemorizeMixin 类

### 2.1 MemorizeMixin 类

核心异步方法 `memorize()`:

```python
async def memorize(
    self,
    *,
    resource_url: str,
    modality: str,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

**参数**:
- `resource_url`: 资源路径或 URL
- `modality`: 资源模态 (conversation, document, video, image, audio)
- `user`: 用户作用域数据

**返回**:
```python
{
    "resource": {...},      # 单个资源
    "resources": [...],     # 多个资源
    "items": [...],         # 记忆项列表
    "categories": [...],     # 更新的分类
    "relations": [...]      # 分类-项关系
}
```

### 2.2 记忆工作流 (Memorize Workflow)

```
memorize workflow:
┌─────────────────┐
│ ingest_resource │  (io capability)
│  - fetch file   │
└────────┬────────┘
         ↓
┌─────────────────────┐
│ preprocess_multimodal│  (llm capability)
│  - segment video    │
│  - transcribe audio │
└────────┬────────────┘
         ↓
┌─────────────────┐
│  extract_items  │  (llm capability)
│  - parse XML    │
│  - extract mems │
└────────┬────────┘
         ↓
┌─────────────────┐
│  dedupe_merge   │
│  (placeholder)  │
└────────┬────────┘
         ↓
┌─────────────────────┐
│  categorize_items   │ (db + vector capability)
│  - create resources │
│  - create items     │
│  - link categories  │
└────────┬────────────┘
         ↓
┌─────────────────────┐
│  persist_index      │ (db + llm capability)
│  - update summaries │
│  - persist refs     │
└────────┬────────────┘
         ↓
┌─────────────────┐
│  build_response │
│  (emit)         │
└─────────────────┘
```

### 2.3 关键处理方法

#### 资源获取

```python
async def _memorize_ingest_resource(self, state: WorkflowState, step_context: Any) -> WorkflowState:
    local_path, raw_text = await self.fs.fetch(state["resource_url"], state["modality"])
    state.update({"local_path": local_path, "raw_text": raw_text})
    return state
```

#### 多模态预处理

```python
async def _memorize_preprocess_multimodal(self, state: WorkflowState, step_context: Any) -> WorkflowState:
```

支持模态:
- **conversation**: 使用索引标记格式化对话
- **video**: 使用 ffmpeg 提取中间帧,调用 Vision API
- **image**: 调用 Vision API 分析图像
- **document**: 精简并提取标题
- **audio**: 转录音频

#### 记忆项提取

```python
async def _memorize_extract_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
```

对于每个 memory_type (profile, event, knowledge, behavior, skill, tool):
1. 构建提取提示词
2. 并行调用 LLM
3. 解析 XML 结构化输出

#### 分类处理

```python
async def _memorize_categorize_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
```

为每个资源创建:
1. Resource 记录 (带嵌入向量)
2. MemoryItem 记录 (从结构化条目)
3. CategoryItem 关系

#### 分类摘要更新

```python
async def _update_category_summaries(
    self,
    updates: dict[str, list[tuple[str, str]]],
    ctx: Context,
    store: Database,
    llm_client: Any | None = None,
) -> dict[str, str]:
```

使用 LLM 根据新记忆项更新分类摘要。

### 2.4 支持的记忆类型

```python
MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill", "tool"]
```

| 类型 | 说明 |
|------|------|
| profile | 用户Profile信息 |
| event | 事件记录 |
| knowledge | 知识性信息 |
| behavior | 行为模式 |
| skill | 技能提取 |
| tool | 工具使用记录 |

### 2.5 引用追踪系统

当 `enable_item_references=True` 时启用:

```python
async def _persist_item_references(
    self,
    *,
    updated_summaries: dict[str, str],
    category_updates: dict[str, list[tuple[str, str]]],
    store: Database,
) -> None:
```

在分类摘要中生成 `[ref:ITEM_ID]` 格式的引用。

---

## 第三章: 检索模块 (app/retrieve.py)

> **源码**: [src/memu/app/retrieve.py](src/memu/app/retrieve.py)

### 3.1 Retrieve 工作流时序图

> **说明**: retrieve 工作流支持 RAG (向量检索) 和 LLM (深度推理) 两种模式,通过充分性检查决定是否继续检索。

```uml
@startuml
participant "Client" as C #lightblue
participant "MemoryService" as S #lightblue
participant "WorkflowEngine" as W #lightyellow
participant "RouteIntention\n(意图路由)" as RI #lightgreen
participant "RouteCategory\n(分类检索)" as RC #lightgreen
participant "SufficiencyCheck\n(充分性检查)" as SC #lightgreen
participant "RecallItems\n(记忆项检索)" as RI2 #lightgreen
participant "RecallResources\n(资源检索)" as RR #lightgreen
participant "BuildContext\n(构建上下文)" as BC #lightgreen
database "Database" as DB #lightgray

C -> S: **retrieve**(queries, where)
note over S
    **检索模式**:
    - method="rag": 向量相似度检索
    - method="llm": LLM 深度推理排序
end note

S -> W: _run_workflow("retrieve_rag" 或 "retrieve_llm", state)

W -> RI: _rag_route_intention()
alt **route_intention enabled** (启用意图路由)
    RI -> DB: LLM.chat(pre_retrieval_prompt) ''判断是否需要检索"
    RI -> RI: _decide_if_retrieval_needed() ''决定检索意图"
end
RI --> W: (needs_retrieval, rewritten_query)

alt **needs_retrieval AND retrieve_category**
    W -> RC: _rag_route_category()
    RC -> DB: category_repo.list_categories() ''获取所有分类"
    RC -> DB: embed_client.embed(query) ''将查询向量化"
    RC -> RC: cosine_topk(qvec, corpus) ''余弦相似度检索"
    RC --> W: (category_hits, query_vector)

    alt **sufficiency_check enabled** (启用充分性检查)
        W -> SC: _rag_category_sufficiency()
        SC -> DB: LLM.chat(sufficiency_prompt) ''判断分类检索是否足够"
        SC --> W: (proceed_to_items, rewritten_query) ''决定是否继续检索 Items"
    end
end

alt **proceed_to_items AND retrieve_item**
    W -> RI2: _rag_recall_items()
    RI2 -> DB: memory_item_repo.vector_search_items() ''向量搜索记忆项"
    RI2 --> W: item_hits

    alt **sufficiency_check enabled**
        W -> SC: _rag_item_sufficiency()
        SC --> W: (proceed_to_resources, rewritten_query)
    end
end

alt **proceed_to_resources AND retrieve_resource**
    W -> RR: _rag_recall_resources()
    RR -> DB: resource_repo.list_resources() ''获取所有资源"
    RR -> RR: cosine_topk(qvec, corpus) ''资源向量检索"
    RR --> W: resource_hits
end

W -> BC: _rag_build_context()
BC --> W: response
W --> S: WorkflowState
S --> C: **response** (categories, items, resources)

note over W
    **充分性检查 (Sufficiency Check)**:
    每层检索后,LLM 判断当前结果是否足够回答查询。
    如不够,则:
    1. 重写查询 (rewritten_query)
    2. 继续下一层检索
    这样可以避免过度检索,节省 token。
end note

@enduml
```

### 3.2 RetrieveMixin 类

> **源码**: [src/memu/app/retrieve.py](src/memu/app/retrieve.py)
>
> **说明**: RetrieveMixin 提供记忆检索的核心 API,支持 RAG 和 LLM 两种检索模式。

#### retrieve() - 记忆检索入口

```python
async def retrieve(
    self,
    queries: list[dict[str, Any]],   # 查询列表,最后一个为主查询,前面的为上下文
    where: dict[str, Any] | None = None,  # 过滤条件 (如 {"user_id": "xxx"})
) -> dict[str, Any]:
    """
    检索记忆的核心方法。

    参数说明:
        queries: 查询列表
            - 格式: [{"role": "user", "content": {"text": "查询内容"}}]
            - 最后一个元素为主查询,前面的为对话上下文
            - 支持历史查询重写 (rewritten_query)

        where: 过滤条件
            - 用于多租户/多用户场景的数据隔离
            - 格式: {"user_id": "xxx", "other_field": "value"}

    返回数据结构:
        {
            "needs_retrieval": bool,      # 是否需要检索 (route_intention 可能跳过)
            "original_query": str,         # 原始查询
            "rewritten_query": str,        # 重写后的查询 (用于更精准检索)
            "next_step_query": str | None, # 充分性检查后的下一步查询
            "categories": [...],            # 分类检索结果
            "items": [...],               # 记忆项检索结果
            "resources": [...]            # 资源检索结果
        }

    示例:
        >>> # 简单检索
        >>> result = await service.retrieve(
        ...     queries=[{"role": "user", "content": {"text": "我上周开会讨论了什么"}}]
        ... )

        >>> # 带上下文的检索
        >>> result = await service.retrieve(
        ...     queries=[
        ...         {"role": "user", "content": {"text": "那个项目的时间线是什么"}},
        ...         {"role": "user", "content": {"text": "我之前提到过这个项目"}},  # 上下文
        ...     ]
        ... )
    """
```

#### 返回值详解

```python
{
    "needs_retrieval": bool,      # 是否执行了检索
                              # - True: 执行了检索,结果在 categories/items/resources
                              # - False: 路由判断不需要检索 (如纯闲聊)

    "original_query": str,         # 用户原始查询内容

    "rewritten_query": str,        # LLM 重写后的查询
                              # 可能比原始查询更精准或增加了上下文理解

    "next_step_query": str | None, # 充分性检查后生成的查询
                              # 如果充分性检查判断需要更多检索,这是下一步的查询

    "categories": [                # 分类检索结果
        {
            "id": str,             # 分类 ID
            "name": str,          # 分类名称
            "description": str,    # 分类描述
            "summary": str,       # 分类聚合摘要
            "score": float,      # 相似度得分
            ...
        }
    ],

    "items": [                     # 记忆项检索结果
        {
            "id": str,             # 记忆项 ID
            "memory_type": str,    # 记忆类型 (profile/event/knowledge...)
            "summary": str,        # 记忆摘要
            "resource_id": str,    # 来源资源 ID
            "score": float,       # 相似度得分
            ...
        }
    ],

    "resources": [                 # 资源检索结果
        {
            "id": str,             # 资源 ID
            "url": str,            # 资源 URL
            "modality": str,       # 模态类型
            "caption": str,        # 资源描述
            "score": float,       # 相似度得分
            ...
        }
    ]
}
```

### 3.2 检索方法详解

#### RAG 检索 (基于向量)

```
retrieve_rag workflow:
┌──────────────────┐
│ route_intention  │  (llm) - 判断是否需要检索
└────────┬─────────┘
         ↓
┌──────────────────┐
│ route_category   │  (vector) - 嵌入查询,搜索分类
└────────┬─────────┘
         ↓
┌─────────────────────┐
│ sufficiency_after_  │ (llm) - 判断是否需要更多
│     category        │
└────────┬────────────┘
         ↓
┌──────────────────┐
│ recall_items     │  (vector) - 搜索记忆项
└────────┬─────────┘
         ↓
┌─────────────────────┐
│ sufficiency_after_  │ (llm) - 判断是否需要更多
│     items           │
└────────┬────────────┘
         ↓
┌──────────────────┐
│ recall_resources │  (vector) - 搜索资源
└────────┬─────────┘
         ↓
┌──────────────────┐
│ build_context   │ (emit)
└──────────────────┘
```

#### LLM 检索 (基于语言模型排序)

```
retrieve_llm workflow:
┌──────────────────┐
│ route_intention  │  (llm)
└────────┬─────────┘
         ↓
┌──────────────────┐
│ route_category   │  (llm) - LLM 排序分类
└────────┬─────────┘
         ↓
┌─────────────────────┐
│ sufficiency_after_  │ (llm)
│     category        │
└────────┬────────────┘
         ↓
┌──────────────────┐
│ recall_items     │  (llm) - LLM 排序记忆项
└────────┬─────────┘
         ↓
┌─────────────────────┐
│ sufficiency_after_  │ (llm)
│     items          │
└────────┬────────────┘
         ↓
┌──────────────────┐
│ recall_resources │  (llm) - LLM 排序资源
└────────┬─────────┘
         ↓
┌──────────────────┐
│ build_context   │ (emit)
└──────────────────┘
```

### 3.3 充分性检查 (Sufficiency Check)

> **说明**: 充分性检查是 MemU 检索系统的核心优化机制,用于避免过度检索。

```python
async def _decide_if_retrieval_needed(
    self,
    query: str,                           # 当前查询
    context_queries: list[dict[str, Any]] | None,  # 对话历史上下文
    retrieved_content: str | None = None,  # 已检索到的内容
    system_prompt: str | None = None,     # 系统提示词 (可选)
    llm_client: Any | None = None,         # LLM 客户端 (可选)
) -> tuple[bool, str]:
    """
    判断是否需要继续检索,并返回重写后的查询。

    工作原理:
    1. 将已检索到的内容 + 当前查询发给 LLM
    2. LLM 判断: "当前内容是否足够回答查询?"
    3. 如果不够,生成更精确的 rewritten_query

    返回值:
        - needs_retrieval: True=需要更多检索, False=当前内容足够
        - rewritten_query: 重写后的查询 (用于下一步检索)

    优势:
        - 节省 token: 避免不必要的检索
        - 提高精度: 重写查询更精准
        - 自适应: 根据实际需求动态调整检索深度
    """
```

**充分性检查的工作流程**:

```
┌─────────────────────────────────────────┐
│  已检索内容 (categories/items/resources)  │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         LLM 判断 (Sufficiency)           │
│  "这些内容是否足够回答用户的查询?"          │
└─────────────────┬───────────────────────┘
                  ↓
         ┌────────┴────────┐
         ↓                 ↓
    ┌─────足够─────┐  ┌─────不够─────┐
    ↓              ↓  ↓              ↓
  返回当前结果    生成 rewritten_query
                    继续下一层检索
```

### 3.4 向量搜索 (cosine_topk)

> **说明**: 基于余弦相似度的向量近邻搜索,用于 RAG 模式的记忆检索。

```python
def cosine_topk(
    query_vec: list[float],                              # 查询向量
    corpus: Iterable[tuple[str, list[float] | None]],   # 语料库: (id, 向量) 元组列表
    k: int = 5,                                          # 返回前 k 个最相似结果
) -> list[tuple[str, float]]:
    """
    计算查询向量与语料库中每个向量的余弦相似度,返回 top-k 结果。

    余弦相似度公式:
        cos(θ) = (A · B) / (||A|| × ||B||)

    参数:
        query_vec: 查询的嵌入向量
        corpus: 语料库,每个元素为 (唯一ID, 向量) 元组
        k: 返回最相似的 k 个结果

    返回:
        [(id_1, score_1), (id_2, score_2), ...]
        按相似度降序排列的 (ID, 分数) 列表

    示例:
        >>> corpus = [("item1", [0.1, 0.2, ...]), ("item2", [0.3, 0.4, ...])]
        >>> cosine_topk(query_vector, corpus, k=3)
        [("item2", 0.95), ("item1", 0.87), ...]
    """
```

### 3.5 Salience 评分 (综合相关性评分)

> **说明**: 当 `ranking="salience"` 时启用,综合考虑相似度、强化次数和时效性。

```python
def salience_score(
    similarity: float,                    # 余弦相似度分数 (0.0-1.0)
    reinforcement_count: int,             # 记忆被访问/使用的次数
    last_reinforced_at: datetime | None, # 上次强化的时间戳
    recency_decay_days: float = 30.0,    # 半衰期 (天)
) -> float:
    """
    计算记忆项的综合相关性评分 (Salience Score)。

    公式:
        score = similarity × log(reinforcement_count + 1) × time_decay

    其中:
        - similarity: 向量余弦相似度
        - log(reinforcement_count + 1): 强化因子 (访问次数越多,分数越高)
        - time_decay = exp(-0.693 × days_ago / recency_decay_days)
          (指数衰减,半衰期为 recency_decay_days 天)

    参数说明:
        similarity: 原始向量相似度 (0.0-1.0)
        reinforcement_count: 记忆被强化的次数
            - 每次记忆被检索使用,reinforcement_count + 1
            - 用于衡量记忆的重要性和使用频率
        last_reinforced_at: 上次强化的时间
            - 用于计算时间衰减
            - 如果为 None,视为极旧的记忆
        recency_decay_days: 时间衰减半衰期
            - 默认 30 天,表示 30 天后权重减半
            - 越小表示越重视新记忆

    返回:
        综合评分,分数越高表示越相关

    示例:
        >>> # 高相似度 + 高强化 + 新记忆
        >>> salience_score(0.9, 10, datetime.now(), 30)
        0.9 * log(11) * exp(-0.001) ≈ 2.07

        >>> # 低相似度 + 无强化 + 旧记忆
        >>> salience_score(0.3, 1, days_ago(60), 30)
        0.3 * log(2) * exp(-1.386) ≈ 0.11
    """
```

**Salience vs Similarity 排序对比**:

| 特性 | similarity | salience |
|------|------------|----------|
| 排序依据 | 仅向量相似度 | 相似度 + 强化 + 时效 |
| 适用场景 | 简单检索 | 长期记忆系统 |
| 准确性 | 基础 | 更智能 |
| 计算成本 | 低 | 略高 |

---

## 第四章: CRUD 和 Patch 模块

> **源码**:
> - [app/crud.py](src/memu/app/crud.py) - CRUDMixin
> - [app/patch.py](src/memu/app/patch.py) - PatchMixin

### 4.1 CRUDMixin - 基础增删改查

> **说明**: CRUDMixin 提供内存项的基础数据库操作,用于直接管理记忆数据。

```python
class CRUDMixin:
    """
    记忆项基础 CRUD 操作Mixin

    提供的方法:
    - list: 列出记忆项/分类
    - delete: 删除记忆项
    - clear: 清空记忆

    注意: 不提供 create/update,这些通过 PatchMixin 提供
    """

    async def list_memory_items(
        self,
        where: dict[str, Any] | None = None,  # 过滤条件
    ) -> dict[str, Any]:
        """
        列出记忆项列表

        参数:
            where: 过滤条件
                - 支持 user_id 等字段过滤
                - 格式: {"user_id": "xxx", "memory_type": "profile"}

        返回:
            {
                "items": [
                    {
                        "id": str,
                        "memory_type": str,
                        "summary": str,
                        "resource_id": str,
                        "created_at": str,
                        ...
                    },
                    ...
                ]
            }
        """

    async def list_memory_categories(
        self,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        列出分类列表

        返回:
            {
                "categories": [
                    {
                        "id": str,
                        "name": str,
                        "description": str,
                        "summary": str,
                        ...
                    },
                    ...
                ]
            }
        """

    async def clear_memory(
        self,
        where: dict[str, Any] | None = None,  # 过滤条件,为空则清空所有
    ) -> dict[str, Any]:
        """
        清空记忆

        警告: 此操作不可恢复!

        参数:
            where: 过滤条件
                - 为 None: 清空所有记忆
                - 为 {"user_id": "xxx"}: 仅清空该用户的记忆

        返回:
            {
                "deleted_items": int,     # 删除的记忆项数量
                "deleted_resources": int, # 删除的资源数量
                "deleted_categories": int # 删除的分类数量 (仅在清空所有时)
            }
        """
```

### 4.2 PatchMixin - 记忆项更新操作

> **说明**: PatchMixin 提供记忆项的创建、更新和删除操作,支持传播到分类摘要。

```python
class PatchMixin:
    """
    记忆项 Patch 操作Mixin

    提供的方法:
    - create_memory_item: 创建新记忆项
    - update_memory_item: 更新现有记忆项
    - delete_memory_item: 删除记忆项

    核心特性:
    - propagate: 是否将更改传播到分类摘要
    - user: 多用户/多租户数据隔离
    """

    async def create_memory_item(
        self,
        *,
        memory_type: MemoryType,              # 记忆类型 (profile/event/knowledge等)
        memory_content: str,                   # 记忆内容/摘要
        memory_categories: list[str],         # 所属分类名称列表
        user: dict[str, Any] | None = None,   # 用户作用域数据
        propagate: bool = True,               # 是否传播到分类摘要
    ) -> dict[str, Any]:
        """
        创建新的记忆项

        参数:
            memory_type: 记忆类型
                - "profile": 用户 profile 信息
                - "event": 事件记录
                - "knowledge": 知识性信息
                - "behavior": 行为模式
                - "skill": 技能相关
                - "tool": 工具使用

            memory_content: 记忆内容摘要
                - 这是记忆的核心文本内容
                - 会自动生成向量嵌入

            memory_categories: 所属分类
                - 分类名称列表,如 ["用户偏好", "工作相关"]
                - 如果分类不存在,会自动创建

            user: 用户作用域
                - 用于多用户数据隔离
                - 通常包含 user_id

            propagate: 是否传播到分类摘要
                - True: 同时更新相关分类的摘要 (默认)
                - False: 仅创建记忆项,不更新摘要

        返回:
            {
                "item": {
                    "id": str,           # 新创建的记忆项 ID
                    "memory_type": str,  # 记忆类型
                    "summary": str,      # 记忆摘要
                    ...
                },
                "categories": [...]       # 更新后的分类列表
            }
        """

    async def update_memory_item(
        self,
        *,
        memory_id: str,                        # 要更新的记忆项 ID
        memory_type: MemoryType | None = None, # 新记忆类型 (可选)
        memory_content: str | None = None,    # 新记忆内容 (可选)
        memory_categories: list[str] | None = None,  # 新分类列表 (可选)
        user: dict[str, Any] | None = None,   # 用户作用域
        propagate: bool = True,               # 是否传播到分类摘要
    ) -> dict[str, Any]:
        """
        更新现有的记忆项

        参数:
            memory_id: 要更新的记忆项 ID
                - 必须指定
                - 如果不存在会抛出错误

            memory_type: 新的记忆类型
                - 可选,不指定则保持不变

            memory_content: 新的记忆内容
                - 可选,不指定则保持不变
                - 如果修改,会重新生成向量嵌入

            memory_categories: 新的分类列表
                - 可选,不指定则保持不变
                - 支持增删分类

            user: 用户作用域

            propagate: 是否传播到分类摘要
                - True: 更新相关分类的摘要 (默认)
                - False: 仅更新记忆项

        返回:
            {
                "item": {...},    # 更新后的记忆项
                "categories": [...] # 更新后的分类列表
            }
        """

    async def delete_memory_item(
        self,
        *,
        memory_id: str,                        # 要删除的记忆项 ID
        user: dict[str, Any] | None = None,   # 用户作用域
        propagate: bool = True,               # 是否传播到分类摘要
    ) -> dict[str, Any]:
        """
        删除记忆项

        参数:
            memory_id: 要删除的记忆项 ID

            user: 用户作用域 (用于验证权限)

            propagate: 是否传播到分类摘要
                - True: 从分类摘要中移除引用 (默认)
                - False: 仅删除记忆项

        返回:
            {
                "deleted": True,
                "id": memory_id
            }
        """
```

### 4.3 Patch 工作流 (Patch Workflow)

```
┌─────────────────────────────────────────────────────────────┐
│                    patch_create 流程                         │
│  (创建新记忆项)                                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│  1. create_memory_item 步骤                                  │
│     - 生成向量嵌入                                           │
│     - 存储记忆项                                             │
│     - 建立分类关联                                           │
└─────────────────────────────────────────────────────────────┘
                    ↓ (propagate=True)
┌─────────────────────────────────────────────────────────────┐
│  2. update_category_summaries 步骤                           │
│     - 将新记忆添加到分类摘要                                  │
│     - 保持摘要在目标长度内                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    patch_update 流程                         │
│  (更新现有记忆项)                                            │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│  1. find_memory_item 步骤                                   │
│     - 验证记忆项存在                                         │
│     - 检查用户权限                                           │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│  2. update_item_and_relations 步骤                           │
│     - 更新记忆项内容/类型                                     │
│     - 重新生成分类关联 (如有变化)                             │
│     - 重新生成向量嵌入 (如有内容变化)                         │
└─────────────────────────────────────────────────────────────┘
                    ↓ (propagate=True)
┌─────────────────────────────────────────────────────────────┐
│  3. update_category_summaries 步骤                           │
│     - 重新生成受影响的分类摘要                                │
└─────────────────────────────────────────────────────────────┘
```

async def delete_memory_item(
    self,
    *,
    memory_id: str,
    user: dict[str, Any] | None = None,
    propagate: bool = True,
) -> dict[str, Any]
```

**propagate 参数**: 控制是否更新关联分类的摘要

### 4.3 Patch 工作流

```
patch_create workflow:
┌──────────────────────┐
│ create_memory_item   │ (db + llm)
│  - embed content    │
│  - create item      │
│  - link categories  │
└────────┬───────────┘
         ↓
┌──────────────────────┐
│ persist_index        │ (db + llm)
│  - update summaries  │
└────────┬───────────┘
         ↓
┌──────────────────────┐
│ build_response       │ (emit)
└──────────────────────┘
```

---

## 第五章: 数据模型 (database/models.py)

> **源码**: [src/memu/database/models.py](src/memu/database/models.py)

### 5.1 UML 数据模型类图

> **说明**: MemU 采用三层记忆架构,支持多模态资源存储、结构化记忆提取和自动分类聚合。

```uml
@startuml
skinparam classAttributeIconSize 0
skinparam defaultTextAlignment center

class BaseRecord {
    + id: str ''UUID 主键"
    + created_at: datetime ''创建时间 (UTC)"
    + updated_at: datetime ''更新时间 (UTC)"
}

class Resource {
    + url: str ''资源原始 URL"
    + modality: str ''模态: conversation/document/image/video/audio"
    + local_path: str ''本地存储路径"
    + caption: str | None ''资源描述/摘要"
    + embedding: list[float] | None ''向量嵌入 (用于 RAG)"
}

class MemoryItem {
    + resource_id: str | None ''关联的 Resource ID"
    + memory_type: str ''类型: profile/event/knowledge/behavior/skill/tool"
    + summary: str ''记忆摘要"
    + embedding: list[float] | None ''向量嵌入"
    + happened_at: datetime | None ''事件时间"
    + extra: dict[str, Any] ''扩展数据"
}

class MemoryCategory {
    + name: str ''分类名称"
    + description: str ''分类描述"
    + embedding: list[float] | None ''向量嵌入"
    + summary: str | None ''聚合摘要"
}

class CategoryItem {
    + item_id: str ''关联的 MemoryItem ID"
    + category_id: str ''关联的 MemoryCategory ID"
}

class ToolCallResult {
    + tool_name: str ''工具名称"
    + input: dict | str ''工具输入参数"
    + output: str ''工具输出结果"
    + success: bool ''是否成功"
    + time_cost: float ''执行耗时(秒)"
    + token_cost: int ''Token 消耗"
    + score: float ''质量评分 (0.0-1.0)"
    + call_hash: str ''去重哈希"
}

BaseRecord <|-- Resource ''资源层 (第一层)"
BaseRecord <|-- MemoryItem ''记忆项层 (第二层)"
BaseRecord <|-- MemoryCategory ''分类层 (第三层)"
BaseRecord <|-- CategoryItem ''关联表"

MemoryItem "1" --> "0..1" Resource : ''记忆项关联资源"
MemoryCategory "1" <-- "0..*" CategoryItem : ''分类包含多个记忆项"
MemoryItem "1" <-- "0..*" CategoryItem : ''记忆项属于多个分类"

note top of Resource
    **第一层: 资源层**
    - 存储原始数据 (对话/文档/图片/视频)
    - modality 区分不同模态
    - caption 用于检索
end note

note top of MemoryItem
    **第二层: 记忆项层**
    - 从资源中提取的结构化记忆
    - 支持六种 memory_type
    - extra 字段存储:
      - content_hash (去重)
      - reinforcement_count (强化)
      - tool_calls (工具统计)
end note

note top of MemoryCategory
    **第三层: 分类层**
    - 组织记忆的结构化分类
    - 自动聚合相关记忆摘要
    - 支持向量检索匹配
end note

note "Tool Memory 专用\nToolCallResult 记录:\n- 工具调用详情\n- 性能指标\n- 质量评分" as ToolNote
MemoryItem .. ToolNote
ToolNote .. ToolCallResult

@enduml
```

### 5.2 核心模型

```python
class BaseRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    updated_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
```

#### Resource (资源)

```python
class Resource(BaseRecord):
    url: str                    # 资源 URL
    modality: str              # 模态类型
    local_path: str             # 本地路径
    caption: str | None        # 标题/描述
    embedding: list[float] | None  # 嵌入向量
```

#### MemoryItem (记忆项)

```python
class MemoryItem(BaseRecord):
    resource_id: str | None     # 关联资源
    memory_type: str            # 记忆类型
    summary: str                # 摘要内容
    embedding: list[float] | None  # 嵌入向量
    happened_at: datetime | None    # 发生时间
    extra: dict[str, Any] = {}      # 扩展字段
    # extra 可能包含:
    # - content_hash: str          # 内容哈希 (去重)
    # - reinforcement_count: int   # 强化次数
    # - last_reinforced_at: str     # 上次强化时间
    # - ref_id: str                 # 引用 ID
    # - when_to_use: str            # 使用提示
    # - metadata: dict             # 类型特定元数据
    # - tool_calls: list[dict]     # 工具调用历史
```

#### MemoryCategory (记忆分类)

```python
class MemoryCategory(BaseRecord):
    name: str                   # 分类名称
    description: str            # 分类描述
    embedding: list[float] | None  # 嵌入向量
    summary: str | None         # 摘要内容
```

#### CategoryItem (分类-项关系)

```python
class CategoryItem(BaseRecord):
    item_id: str               # 记忆项 ID
    category_id: str           # 分类 ID
```

### 5.2 MemoryType 类型别称

```python
MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill", "tool"]
```

### 5.3 作用域模型混合

```python
def merge_scope_model(
    user_model: type[BaseModel],
    core_model: type[TBaseRecord],
    *,
    name_suffix: str
) -> type[TBaseRecord]
```

允许将用户定义字段 (如 `user_id`, `agent_id`, `session_id`) 混入核心模型。

### 5.4 工具调用结果 (ToolCallResult)

```python
class ToolCallResult(BaseModel):
    tool_name: str                    # 工具名称
    input: dict[str, Any] | str       # 输入参数
    output: str                        # 输出结果
    success: bool = True              # 是否成功
    time_cost: float = 0.0            # 耗时(秒)
    token_cost: int = -1               # token 消耗
    score: float = 0.0                # 质量分数
    call_hash: str = ""               # 去重哈希
    created_at: datetime               # 创建时间
```

---

## 第六章: 数据库抽象层

> **源码**: [src/memu/database/interfaces.py](src/memu/database/interfaces.py)
>
> **说明**: 数据库抽象层采用 Repository 模式,解耦业务逻辑与存储实现。支持多种后端:内存/PostgreSQL/SQLite。

### 6.1 Database 接口

> **说明**: Database 是整个数据库层的主接口,聚合了所有仓储 (Repository)。

```python
@runtime_checkable
class Database(Protocol):
    """
    数据库接口 - 聚合所有数据仓储

    属性:
        resource_repo: 资源仓储 - 管理原始数据资源
        memory_category_repo: 分类仓储 - 管理记忆分类
        memory_item_repo: 记忆项仓储 - 管理结构化记忆
        category_item_repo: 关联仓储 - 管理分类与记忆项的关联

    集合属性 (用于内存后端):
        resources: 资源字典 {id: Resource}
        items: 记忆项字典 {id: MemoryItem}
        categories: 分类字典 {id: MemoryCategory}
        relations: 关联列表 [CategoryItem, ...]
    """

    # 四个核心仓储
    resource_repo: ResourceRepo           # 资源仓储
    memory_category_repo: MemoryCategoryRepo  # 分类仓储
    memory_item_repo: MemoryItemRepo      # 记忆项仓储
    category_item_repo: CategoryItemRepo  # 关联仓储

    # 集合属性 (内存后端使用,ORM后端可能为空)
    resources: dict[str, ResourceRecord]          # 资源字典
    items: dict[str, MemoryItemRecord]             # 记忆项字典
    categories: dict[str, MemoryCategoryRecord]    # 分类字典
    relations: list[CategoryItemRecord]            # 关联列表

    def close(self) -> None: ...  # 关闭数据库连接
```

**UML 关系图**:

```uml
@startuml
class Database {
    + resource_repo: ResourceRepo
    + memory_category_repo: MemoryCategoryRepo
    + memory_item_repo: MemoryItemRepo
    + category_item_repo: CategoryItemRepo
}

class ResourceRepo {
    + resources: dict
    + create_resource()
    + list_resources()
    + clear_resources()
}

class MemoryItemRepo {
    + items: dict
    + create_item()
    + get_item()
    + list_items()
    + update_item()
    + delete_item()
    + vector_search_items()  ''向量搜索
}

class MemoryCategoryRepo {
    + categories: dict
    + get_or_create_category()
    + list_categories()
    + update_category()
}

class CategoryItemRepo {
    + relations: list
    + link_item_category()
    + unlink_item_category()
    + get_item_categories()
}

Database *-- ResourceRepo
Database *-- MemoryItemRepo
Database *-- MemoryCategoryRepo
Database *-- CategoryItemRepo
@enduml
```

### 6.2 仓储接口详解

#### ResourceRepo - 资源仓储

```python
@runtime_checkable
class ResourceRepo(Protocol):
    """
    资源仓储接口

    负责管理原始数据资源的存储和检索。
    资源是记忆系统的最底层数据,包括对话、文档、图片等。
    """

    resources: dict[str, Resource]  # 资源字典

    def list_resources(
        self,
        where: Mapping[str, Any] | None = None,  # 过滤条件
    ) -> dict[str, Resource]:
        """列出资源列表,支持按用户等条件过滤"""

    def clear_resources(
        self,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, Resource]:
        """清空资源,可按条件过滤"""

    def create_resource(
        self,
        *,
        url: str,                    # 资源原始 URL
        modality: str,               # 模态类型
        local_path: str,             # 本地存储路径
        caption: str | None,         # 资源描述 (用于检索)
        embedding: list[float] | None,  # 向量嵌入
        user_data: dict[str, Any],   # 用户作用域数据
    ) -> Resource:
        """创建新的资源记录"""

    def load_existing(self) -> None:
        """从存储加载已存在的资源 (用于初始化)"""
```

#### MemoryItemRepo - 记忆项仓储

```python
@runtime_checkable
class MemoryItemRepo(Protocol):
    """
    记忆项仓储接口

    负责管理结构化记忆的存储和检索。
    核心功能:
    - CRUD 操作
    - 向量搜索
    - 引用感知检索
    """

    items: dict[str, MemoryItem]

    def get_item(self, item_id: str) -> MemoryItem | None:
        """根据 ID 获取记忆项"""

    def list_items(
        self,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, MemoryItem]:
        """列出记忆项,支持过滤"""

    def clear_items(
        self,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, MemoryItem]:
        """清空记忆项"""

    def create_item(
        self,
        *,
        resource_id: str,              # 来源资源 ID
        memory_type: MemoryType,        # 记忆类型
        summary: str,                   # 记忆摘要
        embedding: list[float],         # 向量嵌入
        user_data: dict[str, Any],      # 用户作用域
        reinforce: bool = False,       # 是否启用强化学习
        tool_record: dict[str, Any] | None = None,  # 工具记录 (tool 类型)
    ) -> MemoryItem:
        """
        创建新的记忆项

        特点:
        - 自动生成 UUID
        - 自动设置时间戳
        - 支持强化学习追踪
        """

    def update_item(
        self,
        *,
        item_id: str,                              # 记忆项 ID
        memory_type: MemoryType | None = None,     # 新类型
        summary: str | None = None,               # 新摘要
        embedding: list[float] | None = None,     # 新嵌入
        extra: dict[str, Any] | None = None,       # 新扩展数据
        tool_record: dict[str, Any] | None = None, # 新工具记录
    ) -> MemoryItem:
        """更新记忆项,可选字段仅在提供时更新"""

    def delete_item(self, item_id: str) -> None:
        """删除记忆项"""

    def list_items_by_ref_ids(
        self,
        ref_ids: list[str],              # 引用 ID 列表 [ref:xxx, ...]
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, MemoryItem]:
        """
        根据引用 ID 列表获取记忆项

        用于引用感知检索:
        - 从分类摘要中提取 [ref:xxx] 引用
        - 通过 ref_id 快速定位目标记忆项
        """

    def vector_search_items(
        self,
        query_vec: list[float],                    # 查询向量
        top_k: int,                                # 返回前 k 个
        where: Mapping[str, Any] | None = None,   # 过滤条件
    ) -> list[tuple[str, float]]:
        """
        向量相似度搜索

        返回: [(记忆项ID, 相似度分数), ...]

        支持的排序模式:
        - similarity: 纯余弦相似度
        - salience: 综合评分 (相似度+强化+时效)
        """

    def load_existing(self) -> None:
        """从存储加载已存在的记忆项"""
```

#### MemoryCategoryRepo - 分类仓储

```python
@runtime_checkable
class MemoryCategoryRepo(Protocol):
    """
    分类仓储接口

    负责管理记忆分类的创建和更新。
    分类用于组织记忆,支持聚合摘要。
    """

    categories: dict[str, MemoryCategory]

    def list_categories(
        self,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, MemoryCategory]:
        """列出所有分类"""

    def clear_categories(
        self,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, MemoryCategory]:
        """清空分类"""

    def get_or_create_category(
        self,
        *,
        name: str,                      # 分类名称
        description: str,                # 分类描述
        embedding: list[float],          # 描述向量
        user_data: dict[str, Any],       # 用户作用域
    ) -> MemoryCategory:
        """
        获取或创建分类

        逻辑:
        - 如果同名分类存在,直接返回
        - 如果不存在,创建新的分类
        """

    def update_category(
        self,
        *,
        category_id: str,                           # 分类 ID
        name: str | None = None,                   # 新名称
        description: str | None = None,            # 新描述
        embedding: list[float] | None = None,      # 新向量
        summary: str | None = None,                # 新摘要
    ) -> MemoryCategory:
        """
        更新分类

        特点:
        - 可部分更新 (只传需要修改的字段)
        - summary 更新会触发 LLM 重新生成
        """

    def load_existing(self) -> None:
        """从存储加载已存在的分类"""
```

#### CategoryItemRepo - 关联仓储

```python
@runtime_checkable
class CategoryItemRepo(Protocol):
    """
    分类-记忆项关联仓储接口

    负责管理 MemoryItem 和 MemoryCategory 的多对多关系。
    """

    relations: list[CategoryItem]

    def list_relations(
        self,
        where: Mapping[str, Any] | None = None,
    ) -> list[CategoryItem]:
        """列出所有关联关系"""

    def link_item_category(
        self,
        item_id: str,            # 记忆项 ID
        cat_id: str,             # 分类 ID
        user_data: dict[str, Any],  # 用户作用域
    ) -> CategoryItem:
        """
        建立记忆项与分类的关联

        创建新的 CategoryItem 记录。
        """

    def unlink_item_category(
        self,
        item_id: str,   # 记忆项 ID
        cat_id: str,    # 分类 ID
    ) -> None:
        """
        解除记忆项与分类的关联

        删除对应的 CategoryItem 记录。
        """

    def get_item_categories(
        self,
        item_id: str,  # 记忆项 ID
    ) -> list[CategoryItem]:
        """
        获取记忆项所属的所有分类

        返回该记忆项关联的所有 CategoryItem 记录。
        """

    def load_existing(self) -> None:
        """从存储加载已存在的关联"""
```

### 6.3 数据库工厂

> **说明**: build_database() 是数据库层的入口工厂函数,根据配置创建相应的存储实现。

```python
def build_database(
    *,
    config: DatabaseConfig,           # 数据库配置
    user_model: type[BaseModel],      # 用户作用域模型
) -> Database:
    """
    根据配置创建数据库存储实例。

    支持的存储后端:

    1. **inmemory** (默认)
       - 内存存储,数据不持久化
       - 仅适合测试或开发
       - 启动快,无额外依赖

    2. **postgres**
       - PostgreSQL + pgvector
       - 生产环境推荐
       - 支持向量检索
       - 数据持久化

    3. **sqlite**
       - SQLite 文件存储
       - 轻量级场景
       - 单文件数据库

    参数:
        config: 数据库配置对象
            - metadata_store.provider: 选择存储后端
            - metadata_store.dsn: 连接字符串
            - vector_index.provider: 向量索引类型

        user_model: 用户作用域模型
            - 用于多租户数据隔离
            - 通常包含 user_id 等字段

    返回:
        Database 接口实例
            - 内存后端返回 InMemoryStore
            - PostgreSQL 后端返回 PostgresStore
            - SQLite 后端返回 SQLiteStore

    示例:
        >>> config = DatabaseConfig(
        ...     metadata_store=MetadataStoreConfig(provider="postgres", dsn="postgresql://..."),
        ...     vector_index=VectorIndexConfig(provider="pgvector", dsn="postgresql://...")
        ... )
        >>> db = build_database(config=config, user_model=UserModel)
    """
```

**工厂模式 UML**:

```uml
@startuml
class DatabaseFactory {
    + build_database(config, user_model): Database
}

class InMemoryStore {
    + resources: dict
    + items: dict
    + categories: dict
}

class PostgresStore {
    + resource_repo
    + memory_item_repo
    + ...
}

class SQLiteStore {
    + resource_repo
    + memory_item_repo
    + ...
}

Database <|-- InMemoryStore
Database <|-- PostgresStore
Database <|-- SQLiteStore

DatabaseFactory --> InMemoryStore : "inmemory"
DatabaseFactory --> PostgresStore : "postgres"
DatabaseFactory --> SQLiteStore : "sqlite"
@enduml
```

---

## 第七章: 数据库实现

### 7.1 InMemory 存储

```python
class InMemoryStore(Database):
    def __init__(
        self,
        *,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        memory_item_model: type[Any] | None = None,
        memory_category_model: type[Any] | None = None,
        category_item_model: type[Any] | None = None,
        state: InMemoryState | None = None,
    ) -> None:
```

使用 `InMemoryState` 管理状态:

```python
class InMemoryState(DatabaseState):
    resources: dict[str, Resource] = {}
    items: dict[str, MemoryItem] = {}
    categories: dict[str, MemoryCategory] = {}
    relations: list[CategoryItem] = []
```

### 7.2 PostgreSQL 存储

```python
class PostgresStore(Database):
    def __init__(
        self,
        *,
        dsn: str,
        ddl_mode: DDLMode = "create",
        vector_provider: str | None = None,
        scope_model: type[BaseModel] | None = None,
        # ... 其他参数
    ) -> None:
```

**特点**:
- 支持 `pgvector` 向量类型
- 使用 SQLModel/SQLAlchemy ORM
- Alembic 迁移支持

**表结构** (PostgreSQL):

```sql
CREATE TABLE resources (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    url VARCHAR NOT NULL,
    modality VARCHAR NOT NULL,
    local_path VARCHAR NOT NULL,
    caption TEXT,
    embedding VECTOR,  -- pgvector
    -- scope fields
);

CREATE TABLE memory_categories (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    name VARCHAR NOT NULL,
    description TEXT NOT NULL,
    embedding VECTOR,
    summary TEXT,
    -- scope fields
);

CREATE TABLE memory_items (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    resource_id VARCHAR REFERENCES resources(id),
    memory_type VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    embedding VECTOR,
    happened_at TIMESTAMP,
    extra JSONB,
    -- scope fields
);

CREATE TABLE category_items (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    item_id VARCHAR NOT NULL REFERENCES memory_items(id),
    category_id VARCHAR NOT NULL REFERENCES memory_categories(id),
    -- scope fields
);
```

### 7.3 SQLite 存储

```python
class SQLiteStore(Database):
    def __init__(
        self,
        *,
        dsn: str,
        scope_model: type[BaseModel] | None = None,
        # ... 其他参数
    ) -> None:
```

**特点**:
- 轻量级,文件存储
- 向量以 JSON 格式存储在 TEXT 列中
- 使用 brute-force 余弦相似度搜索

---

## 第八章: 向量搜索 (database/inmemory/vector.py)

### 8.1 余弦相似度

```python
def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)
```

### 8.2 Top-K 向量搜索

```python
def cosine_topk(
    query_vec: list[float],
    corpus: Iterable[tuple[str, list[float] | None]],
    k: int = 5,
) -> list[tuple[str, float]]:
```

使用 `argpartition` 实现 O(n) 的 top-k 选择。

### 8.3 Salience 感知搜索

```python
def cosine_topk_salience(
    query_vec: list[float],
    corpus: Iterable[tuple[str, list[float] | None, int, datetime | None]],
    k: int = 5,
    recency_decay_days: float = 30.0,
) -> list[tuple[str, float]]:
```

结合相似度、强化次数和时间衰减计算最终分数。

---

## 第九章: LLM 模块

> **源码**: [src/memu/llm/](src/memu/llm/)
>
> **说明**: LLM 模块封装了多种大语言模型提供商,提供统一的接口,支持拦截器机制。

### 9.1 HTTPLLMClient - HTTP LLM 客户端

> **说明**: 基于 httpx 的通用 HTTP 客户端,支持 OpenAI 兼容的 API 接口。

```python
class HTTPLLMClient:
    """
    HTTP LLM 客户端

    基于 httpx 的异步 HTTP 客户端,支持:
    - OpenAI API 兼容接口
    - 多种 Provider (OpenAI/Grok/Doubao/OpenRouter)
    - 自定义端点覆盖
    - 向量化、视觉、语音转文本等多模态能力
    """

    def __init__(
        self,
        *,
        base_url: str,                            # API 基础地址
        api_key: str,                             # API 密钥
        chat_model: str,                          # 聊天模型名称
        provider: str = "openai",                 # 提供商名称
        endpoint_overrides: dict[str, str] | None = None,  # 端点覆盖
        timeout: int = 60,                        # 请求超时 (秒)
        embed_model: str | None = None,           # 向量化模型名称
    ) -> None:
```

#### 支持的方法

```python
async def chat(
    self,
    prompt: str,                              # 用户 prompt
    *,
    max_tokens: int | None = None,           # 最大生成 token 数
    system_prompt: str | None = None,         # 系统提示词
    temperature: float = 0.2,                # 生成温度 (0.0-2.0)
) -> tuple[str, dict[str, Any]]:
    """
    聊天Completion

    参数:
        prompt: 用户输入的提示词
        max_tokens: 限制生成的最大 token 数 (None=不限制)
        system_prompt: 系统角色设定
        temperature: 采样温度
            - 0.0: 确定性输出
            - 0.2-0.5: 平衡模式 (推荐)
            - 0.8-1.0: 创意模式

    返回:
        (response_text, raw_response)
        - response_text: LLM 生成的文本回复
        - raw_response: 原始 API 响应 (可用于调试)
    """

async def summarize(
    self,
    text: str,                                # 待摘要文本
    max_tokens: int | None = None,           # 最大 token 数
    system_prompt: str | None = None,         # 系统提示词
) -> tuple[str, dict[str, Any]]:
    """
    文本摘要

    使用专门的摘要提示词模板生成简洁摘要。
    """

async def vision(
    self,
    prompt: str,                             # 视觉查询
    image_path: str,                          # 图片路径
    *,
    max_tokens: int | None = None,           # 最大 token 数
    system_prompt: str | None = None,         # 系统提示词
) -> tuple[str, dict[str, Any]]:
    """
    视觉问答

    支持图片理解和分析:
    - 分析图片内容
    - 提取图片信息
    - 生成图片描述

    适用于:
    - 图片记忆预处理
    - 视频帧分析
    - 文档图片 OCR
    """

async def embed(
    self,
    inputs: list[str],                      # 待向量化的文本列表
) -> tuple[list[list[float]], dict[str, Any]]:
    """
    文本向量化

    将文本转换为向量嵌入:
    - 输入: 文本列表
    - 输出: 向量列表

    返回:
        (embeddings, raw_response)
        - embeddings: [[0.1, 0.2, ...], ...] 向量列表
        - raw_response: 原始 API 响应
    """

async def transcribe(
    self,
    audio_path: str,                         # 音频文件路径
    *,
    prompt: str | None = None,               # 提示词 (提高准确性)
    language: str | None = None,             # 语言代码 (如 "zh", "en")
    response_format: str = "text",           # 输出格式
) -> tuple[str, dict[str, Any]] | None:
    """
    语音转文本 (STT)

    将音频文件转录为文本:
    - 支持多种音频格式 (mp3, wav, m4a, webm)
    - 支持语言指定
    - 适用于音频记忆的预处理
    """
```

### 9.2 LLM 后端 (LLMBackend)

> **说明**: LLMBackend 是不同模型提供商的 API 适配器,处理各提供商的请求格式和响应解析差异。

#### Base LLMBackend

```python
class LLMBackend:
    """
    LLM 后端基类

    定义了 LLM API 的标准接口,各提供商继承实现:
    - build_summary_payload(): 构建聊天请求体
    - parse_summary_response(): 解析聊天响应
    - build_vision_payload(): 构建视觉请求体
    """

    name: str = "base"                         # 后端名称
    summary_endpoint: str = "/chat/completions"  # 默认端点

    def build_summary_payload(
        self,
        *,
        text: str,                            # 用户输入
        system_prompt: str | None,            # 系统提示词
        chat_model: str,                      # 模型名称
        max_tokens: int | None,               # 最大 token
    ) -> dict[str, Any]:
        """构建聊天Completion请求体"""

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        """从API响应中提取文本内容"""

    def build_vision_payload(
        self,
        *,
        prompt: str,                          # 视觉查询
        base64_image: str,                    # Base64编码图片
        mime_type: str,                       # 图片MIME类型
        system_prompt: str | None,            # 系统提示词
        chat_model: str,                      # 模型名称
        max_tokens: int | None,               # 最大 token
    ) -> dict[str, Any]:
        """构建视觉问答请求体"""
```

#### OpenAI 后端

```python
class OpenAILLMBackend(LLMBackend):
    """
    OpenAI API 后端

    使用标准的 OpenAI Chat API 格式:
    - Endpoint: /chat/completions
    - Format: messages array
    """
    name = "openai"
```

#### Grok 后端

```python
class GrokBackend(OpenAILLMBackend):
    """
    Grok API 后端

    继承 OpenAI 格式,主要差异:
    - 不同的 base_url
    - 不同的 API Key
    - 部分特性可能不同
    """
    name = "grok"
```

#### Doubao 后端

```python
class DoubaoLLMBackend(LLMBackend):
    """
    豆包 (Doubao) API 后端

    字节跳动的豆包大模型:
    - Endpoint: /api/v3/chat/completions (不同版本)
    - 兼容 OpenAI 格式
    """
    name = "doubao"
    summary_endpoint = "/api/v3/chat/completions"
```

#### OpenRouter 后端

```python
class OpenRouterLLMBackend(LLMBackend):
    """
    OpenRouter API 后端

    OpenRouter 聚合多种模型:
    - Endpoint: /api/v1/chat/completions
    - 支持模型选择
    """
    name = "openrouter"
    summary_endpoint = "/api/v1/chat/completions"
```

**后端选择指南**:

| Provider | Backend | 特点 |
|----------|---------|------|
| OpenAI | OpenAILLMBackend | 官方 SDK,稳定 |
| Grok | GrokBackend | xAI 模型 |
| Doubao | DoubaoLLMBackend | 字节跳动,性价比 |
| OpenRouter | OpenRouterLLMBackend | 模型聚合,灵活 |

### 9.3 LLMClientWrapper - 拦截器封装

> **说明**: LLMClientWrapper 是 LLM 客户端的拦截器封装,支持在调用前后注入自定义逻辑。

```python
class LLMClientWrapper:
    """
    LLM 客户端拦截器封装

    在原始 LLM 客户端基础上,添加拦截器能力:
    - before: 调用前拦截,可修改参数
    - after: 调用后拦截,可处理响应
    - on_error: 异常拦截,可统一错误处理

    支持的方法:
    - chat() / summarize()
    - vision()
    - embed()
    - transcribe()
    """

    def __init__(
        self,
        client: Any,                              # 原始 LLM 客户端
        *,
        registry: LLMInterceptorRegistry,          # 拦截器注册表
        metadata: LLMCallMetadata | None = None,  # 调用元数据
        provider: str | None = None,              # 提供商名称
        chat_model: str | None = None,           # 聊天模型
        embed_model: str | None = None,           # 向量模型
    ) -> None:
```

### 9.4 拦截器系统

> **说明**: 拦截器系统提供 LLM 调用的全方位监控和干预能力。

```python
@dataclass
class LLMCallMetadata:
    """
    LLM 调用元数据

    记录每次 LLM 调用的上下文信息:
    """
    profile: str | None = None      # LLM profile 名称
    operation: str | None = None    # 操作名称 (如 "memorize", "retrieve")
    step_id: str | None = None      # 工作流步骤 ID
    trace_id: str | None = None    # 调用追踪 ID
    tags: Mapping[str, Any] | None = None  # 自定义标签

@dataclass
class LLMCallFilter:
    """
    拦截器过滤条件

    控制拦截器在何种情况下触发:
    """
    operations: set[str] | None = None   # 仅拦截指定操作
    step_ids: set[str] | None = None    # 仅拦截指定步骤
    providers: set[str] | None = None   # 仅拦截指定提供商
    models: set[str] | None = None      # 仅拦截指定模型
    statuses: set[str] | None = None    # 仅拦截指定状态

class LLMInterceptorRegistry:
    """
    LLM 拦截器注册表

    管理所有拦截器的注册和调用:
    - register_before(): 注册调用前拦截器
    - register_after(): 注册调用后拦截器
    - register_on_error(): 注册异常拦截器
    """

    def register_before(
        self,
        fn,                        # 拦截函数
        name=None,                 # 拦截器名称
        priority=0,                 # 优先级 (高优先级先执行)
        where=None,                 # 过滤条件 (LLMCallFilter)
    ) -> LLMInterceptorHandle:
        """
        注册调用前拦截器

        拦截函数签名:
            def before(
                metadata: LLMCallMetadata,
                request_data: dict,
                **kwargs
            ) -> tuple[dict, bool]:
                # 返回 (修改后的请求, 是否继续)
                return modified_request, True
        """

    def register_after(
        self,
        fn,
        name=None,
        priority=0,
        where=None,
    ) -> LLMInterceptorHandle:
        """
        注册调用后拦截器

        拦截函数签名:
            def after(
                metadata: LLMCallMetadata,
                request_data: dict,
                response_data: dict,
                **kwargs
            ) -> dict:
                # 返回 (可能修改的) 响应
                return modified_response
        """

    def register_on_error(
        self,
        fn,
        name=None,
        priority=0,
        where=None,
    ) -> LLMInterceptorHandle:
        """
        注册异常拦截器

        拦截函数签名:
            def on_error(
                metadata: LLMCallMetadata,
                request_data: dict,
                error: Exception,
                **kwargs
            ) -> None:
                # 处理错误 (记录日志/发送告警)
        """

class LLMInterceptorHandle:
    """
    拦截器句柄

    用于取消已注册的拦截器:
    """
    def dispose(self) -> bool:
        """移除拦截器,返回是否成功"""
```

**拦截器使用示例**:

```python
# 注册日志拦截器
service.intercept_before_llm_call(
    lambda metadata, **kwargs: print(f"LLM调用: {metadata.operation}"),
    name="log_calls",
    priority=10,
)

# 注册 Token 计数拦截器
service.intercept_after_llm_call(
    lambda metadata, response, **kwargs: print(f"Token消耗: {response.get('usage')}"),
    name="count_tokens",
)

# 注册错误告警拦截器
service.intercept_on_error_llm_call(
    lambda metadata, error, **kwargs: send_alert(str(error)),
    name="error_alert",
)
```

---

## 第十章: 向量化模块 (embedding/)

### 10.1 OpenAI Embedding SDK Client

```python
class OpenAIEmbeddingSDKClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        embed_model: str,
        batch_size: int = 25,
    ) -> None:

    async def embed(self, inputs: list[str]) -> list[list[float]]:
```

### 10.2 后端支持

```python
class _OpenAIEmbeddingBackend:
    name = "openai"
    embedding_endpoint = "/embeddings"

class _DoubaoEmbeddingBackend:
    name = "doubao"
    embedding_endpoint = "/api/v3/embeddings"

class _OpenRouterEmbeddingBackend:
    name = "openrouter"
    embedding_endpoint = "/api/v1/embeddings"
```

---

## 第十一章: 工作流引擎 (workflow/)

> **源码**: [src/memu/workflow/](src/memu/workflow/)
>
> **说明**: 工作流引擎是基于步骤的流水线系统,支持步骤编排、拦截器和动态修改。

### 11.1 WorkflowStep - 工作流步骤

> **说明**: WorkflowStep 是工作流的基本执行单元,封装了处理逻辑和依赖关系。

```python
@dataclass
class WorkflowStep:
    """
    工作流步骤定义

    每个步骤代表工作流中的一个处理阶段:
    - 有唯一的 step_id 标识
    - 有处理函数 (handler) 执行具体逻辑
    - 有输入/输出状态键声明
    - 有能力要求 (capabilities) 声明
    """

    step_id: str                    # 步骤唯一标识
    role: str                       # 步骤角色 (ingest/preprocess/extract等)
    handler: WorkflowHandler         # 处理函数
                                 # 签名: (WorkflowState, WorkflowContext) -> WorkflowState
    description: str = ""           # 步骤描述 (可选)

    # 状态依赖声明
    requires: set[str] = field(default_factory=set)   # 需要的前置状态键
    produces: set[str] = field(default_factory=set)   # 产生的输出状态键

    # 能力要求声明
    capabilities: set[str] = field(default_factory=set)
    # 可选能力: llm / vector / db / io / vision

    config: dict[str, Any] = field(default_factory=dict)  # 步骤配置参数

    async def run(self, state: WorkflowState, context: WorkflowContext) -> WorkflowState:
        """
        执行步骤处理函数

        流程:
        1. 调用 handler(state, context)
        2. 如果返回协程,await 执行
        3. 返回处理后的状态
        """
        result = self.handler(state, context)
        if inspect.isawaitable(result):
            result = await result
        return dict(result)
```

**WorkflowStep UML**:

```uml
@startuml
class WorkflowStep {
    + step_id: str
    + role: str
    + handler: WorkflowHandler
    + requires: set[str]  ''前置依赖"
    + produces: set[str] ''输出声明"
    + capabilities: set[str]  ''能力要求"
    + config: dict
    --
    + run(state, context): WorkflowState
}

class PipelineManager {
    + available_capabilities: set
    + llm_profiles: set
    --
    + register(name, steps, initial_state_keys)
    + build(name): list[WorkflowStep]
    + config_step(name, step_id, configs): int
    + insert_after(name, target, new_step): int
    + replace_step(name, target, new_step): int
}

class WorkflowRunner {
    ''
    + run(workflow_name, steps, state, context, registry): WorkflowState
}

WorkflowStep --> PipelineManager : ''注册到"
WorkflowRunner --> WorkflowStep : ''执行"
@enduml
```

### 11.2 PipelineManager - 管道管理器

> **说明**: PipelineManager 管理所有工作流的注册、构建和动态修改。

```python
class PipelineManager:
    """
    工作流管道管理器

    核心职责:
    - 注册工作流 (register)
    - 构建工作流步骤链 (build)
    - 动态修改步骤 (insert/replace/remove)
    - 步骤版本管理
    """

    def __init__(
        self,
        *,
        available_capabilities: set[str] | None = None,  # 可用能力集
        llm_profiles: set[str] | None = None,            # 可用 LLM profile
    ) -> None:
        """
        初始化管道管理器

        available_capabilities: 系统支持的能力
            - "llm": LLM 调用
            - "vector": 向量检索
            - "db": 数据库操作
            - "io": 文件读写
            - "vision": 视觉处理
        """

    def register(
        self,
        name: str,                              # 工作流名称
        steps: Iterable[WorkflowStep],           # 步骤列表
        *,
        initial_state_keys: set[str] | None = None,  # 初始状态键
    ) -> None:
        """
        注册工作流

        将工作流的步骤链和初始状态声明注册到管理器。
        注册后可被 _run_workflow() 调用。
        """

    def build(self, name: str) -> list[WorkflowStep]:
        """
        构建工作流

        获取指定名称工作流的最新步骤链。
        用于执行前准备。
        """

    def config_step(
        self,
        name: str,           # 工作流名称
        step_id: str,         # 目标步骤 ID
        configs: dict[str, Any],  # 新配置
    ) -> int:
        """
        配置步骤参数

        动态修改步骤的 config:
        - 可修改 LLM profile
        - 可修改其他配置项

        返回: 版本号
        """

    def insert_after(
        self,
        name: str,              # 工作流名称
        target_step_id: str,    # 目标步骤 ID
        new_step: WorkflowStep, # 新步骤
    ) -> int:
        """
        在目标步骤后插入新步骤

        用于:
        - 添加自定义处理步骤
        - 在特定位置插入验证逻辑
        """

    def insert_before(
        self,
        name: str,
        target_step_id: str,
        new_step: WorkflowStep,
    ) -> int:
        """在目标步骤前插入新步骤"""

    def replace_step(
        self,
        name: str,
        target_step_id: str,
        new_step: WorkflowStep,
    ) -> int:
        """
        替换步骤

        用于:
        - 用优化后的处理函数替换默认步骤
        - 改变步骤实现而不改变工作流结构
        """

    def remove_step(
        self,
        name: str,
        target_step_id: str,
    ) -> int:
        """
        删除步骤

        用于:
        - 跳过不必要的步骤
        - 简化工作流
        """
```

### 11.3 WorkflowRunner - 工作流运行器

> **说明**: WorkflowRunner 是工作流的执行器,负责按序执行步骤并调用拦截器。

```python
@runtime_checkable
class WorkflowRunner(Protocol):
    """
    工作流运行器接口

    定义工作流执行的标准接口。
    支持本地运行和远程运行等多种实现。
    """

    name: str  # 运行器名称

    async def run(
        self,
        workflow_name: str,                              # 工作流名称
        steps: list[WorkflowStep],                       # 步骤列表
        initial_state: WorkflowState,                     # 初始状态
        context: WorkflowContext = None,                # 运行上下文
        interceptor_registry: WorkflowInterceptorRegistry | None = None,  # 拦截器
    ) -> WorkflowState: ...

class LocalWorkflowRunner:
    """
    本地工作流运行器

    在当前进程执行工作流:
    - 顺序执行每个步骤
    - 支持异步处理
    - 支持拦截器
    """

    name = "local"

    async def run(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        initial_state: WorkflowState,
        context: WorkflowContext = None,
        interceptor_registry: WorkflowInterceptorRegistry | None = None,
    ) -> WorkflowState:
        """
        本地执行工作流

        返回最终的工作流状态
        """
        return await run_steps(workflow_name, steps, initial_state, context, interceptor_registry)
```

### 11.4 工作流步骤执行器 (run_steps)

> **说明**: run_steps 是工作流的核心执行函数,负责按序执行每个步骤并管理状态。

```python
async def run_steps(
    name: str,                                  # 工作流名称
    steps: list[WorkflowStep],                   # 步骤列表
    initial_state: WorkflowState,               # 初始状态
    context: WorkflowContext = None,             # 运行上下文
    interceptor_registry: WorkflowInterceptorRegistry | None = None,  # 拦截器
) -> WorkflowState:
    """
    执行工作流步骤链

    执行流程:
    ┌─────────────────────────────────────────────┐
    │  1. 初始化                                   │
    │     - 检查初始状态是否包含必需的 state_keys    │
    └─────────────────────────────────────────────┘
                        ↓
    ┌─────────────────────────────────────────────┐
    │  2. 遍历每个步骤                              │
    │     ┌─────────────────────────────────────┐ │
    │     │ 2.1 before 拦截器                    │ │
    │     │     - 可修改状态                      │ │
    │     │     - 可跳过步骤                      │ │
    │     └─────────────────────────────────────┘ │
    │                ↓                            │
    │     ┌─────────────────────────────────────┐ │
    │     │ 2.2 执行步骤处理器                    │ │
    │     │     - 检查 requires                   │ │
    │     │     - 调用 handler(state, context)   │ │
    │     │     - 更新 produces 到 state          │ │
    │     └─────────────────────────────────────┘ │
    │                ↓                            │
    │     ┌─────────────────────────────────────┐ │
    │     │ 2.3 after 拦截器                     │ │
    │     │     - 可修改返回状态                  │ │
    │     └─────────────────────────────────────┘ │
    │     ┌─────────────────────────────────────┐ │
    │     │ 2.4 错误处理                         │ │
    │     │     - on_error 拦截器                │ │
    │     │     - 记录错误状态                   │ │
    │     └─────────────────────────────────────┘ │
    └─────────────────────────────────────────────┘
                        ↓
    ┌─────────────────────────────────────────────┐
    │  3. 返回最终状态                              │
    └─────────────────────────────────────────────┘
    """
```

### 11.5 工作流拦截器

> **说明**: 工作流拦截器允许在工作流步骤执行前后注入自定义逻辑。

```python
@dataclass(frozen=True)
class WorkflowStepContext:
    """
    工作流步骤上下文

    在拦截器中访问当前步骤的信息:
    """
    workflow_name: str      # 工作流名称
    step_id: str            # 步骤 ID
    step_role: str           # 步骤角色
    step_context: dict[str, Any]  # 步骤配置

class WorkflowInterceptorRegistry:
    """
    工作流拦截器注册表

    管理工作流步骤的拦截器:
    """

    def register_before(
        self,
        fn: Callable[..., Any],         # 拦截函数
        *,
        name: str | None = None,         # 拦截器名称
    ) -> WorkflowInterceptorHandle:
        """
        注册步骤前拦截器

        签名: (step_context, state) -> (可能修改的) state
        """

    def register_after(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        注册步骤后拦截器

        签名: (step_context, state) -> (可能修改的) state
        """

    def register_on_error(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
    ) -> WorkflowInterceptorHandle:
        """
        注册错误拦截器

        签名: (step_context, state, error) -> None
        """
```

**拦截器使用示例**:

```python
# 注册步骤前日志拦截器
service.intercept_before_workflow_step(
    lambda step_ctx, state: print(f"开始步骤: {step_ctx.step_id}"),
    name="log_steps"
)

# 注册步骤后验证拦截器
service.intercept_after_workflow_step(
    lambda step_ctx, state: validate_state(state),
    name="validate"
)

# 注册错误处理拦截器
service.intercept_on_error_workflow_step(
    lambda step_ctx, state, error: handle_error(error),
    name="error_handler"
)
```

---

## 第十二章: 提示词模块 (prompts/)

> **源码**: [src/memu/prompts/](src/memu/prompts/)
>
> **说明**: 提示词模块管理所有 LLM 交互的模板,支持自定义和按模态切换。

### 12.1 记忆类型提示词 (memory_type/)

> **说明**: 记忆类型提示词用于从资源中提取结构化记忆。

```python
# 各记忆类型的提取提示词模板
PROMPTS: dict[str, str] = {
    "profile": ...,   # 从对话中提取用户 profile 信息
                      # - 偏好、习惯、背景等

    "event": ...,     # 从对话中提取事件记录
                      # - 会议、讨论、重要事件等

    "knowledge": ..., # 从对话中提取知识性信息
                      # - 事实、概念、定义等

    "behavior": ...,  # 从对话中提取行为模式
                      # - 习惯性行为、模式等

    "skill": ...,     # 从对话中提取技能相关
                      # - 擅长的技能、工具使用能力等

    "tool": ...,      # 从对话中提取工具使用记录
                      # - 使用的工具、使用效果等
}

# 自定义提示词块 (可组合)
CUSTOM_PROMPTS: dict[str, dict[str, str]] = {
    "profile": {
        "objective": "...",   # 任务目标块
        "rules": "...",        # 规则块
        "output": "...",       # 输出格式块
        # ... 可按需组合
    },
    # 每个类型有多个自定义块
}

# 默认启用的记忆类型
DEFAULT_MEMORY_TYPES: list[str] = ["profile", "event"]

# 自定义提示词块的优先级
DEFAULT_MEMORY_CUSTOM_PROMPT_ORDINAL: dict[str, int] = {
    "objective": 10,   # 任务目标
    "workflow": 20,   # 工作流程
    "rules": 30,      # 规则约束
    "category": 40,   # 分类指导
    "output": 50,     # 输出格式
    "examples": 60,   # 示例
    "input": 90,      # 输入说明
}
# 数字越小,越靠前
```

**记忆类型提示词工作流程**:

```
┌─────────────────────────────────────────────────────────┐
│  1. 根据 memory_type 选择提示词模板                        │
│     - 如果配置了自定义提示词,使用自定义                    │
│     - 否则使用默认模板                                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  2. 格式化提示词                                         │
│     - {resource}: 原始文本内容                           │
│     - {categories_str}: 分类描述字符串                    │
│     - {target_length}: 目标长度                          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  3. 调用 LLM 提取记忆                                    │
│     - 期望返回 XML 格式的结构化结果                       │
│     - <memory><content>...</content></memory>           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  4. 解析 LLM 输出                                        │
│     - 提取 <content> 和 <categories>                     │
│     - 返回 (memory_type, content, categories) 元组       │
└─────────────────────────────────────────────────────────┘
```

### 12.2 预处理提示词 (preprocess/)

> **说明**: 预处理提示词用于处理多模态资源 (对话、视频、图片等)。

```python
# 按模态类型的预处理提示词
PROMPTS: dict[str, str] = {
    "conversation": """
        # 对话分段提示词

        将对话分割成有意义的话题段:
        - 每个段应该是独立的话题
        - 包含开始和结束的行号
        - 保留关键上下文

        输入: 对话文本
        输出: 分段列表 (start, end, caption)
    """,

    "video": """
        # 视频分析提示词

        分析视频帧图像:
        - 描述画面内容
        - 提取关键信息
        - 生成简短标题

        输入: 视频帧图像
        输出: 详细描述 + 标题
    """,

    "image": """
        # 图像分析提示词

        理解图像内容:
        - 描述图像主体
        - 识别文字/物体
        - 提取语义信息

        输入: 图像文件
        输出: 详细描述 + 标题
    """,

    "document": """
        # 文档处理提示词

        精简文档内容:
        - 保留关键信息
        - 去除冗余
        - 生成摘要

        输入: 文档文本
        输出: 精简内容 + 标题
    """,

    "audio": """
        # 音频处理提示词

        处理音频转录:
        - 规范化文本
        - 添加标点
        - 修正错误

        输入: 音频转录文本
        输出: 规范化文本 + 标题
    """,
}
```

### 12.3 检索提示词 (retrieve/)

> **说明**: 检索相关提示词用于判断检索意图和充分性检查。

#### Pre-Retrieval Decision - 检索意图判断

```python
# 系统提示词
SYSTEM_PROMPT = """
# 任务目标

你是一个记忆检索助手。你的任务是:
1. 判断用户的查询是否需要从记忆中检索信息
2. 如果需要,重写查询以包含相关上下文

判断标准:
- 查询涉及具体事实/事件 → 需要检索
- 查询涉及用户偏好/习惯 → 需要检索
- 查询是闲聊/问候 → 不需要检索
- 查询可以直接基于上下文回答 → 不需要检索

输出格式:
<decision>RETRIEVE|NO_RETRIEVE</decision>
<rewritten_query>重写后的查询</rewritten_query>
"""

# 用户提示词模板
USER_PROMPT = """
# 对话历史
{conversation_history}

# 当前查询
{query}

# 已检索内容
{retrieved_content}

请判断:
1. 当前查询是否需要更多信息才能准确回答?
2. 如果需要,如何重写查询以更好地检索?

输出:
<decision>RETRIEVE 或 NO_RETRIEVE</decision>
<rewritten_query>重写后的查询(如果需要)</rewritten_query>
"""
```

#### LLM Category Ranker - 分类排序

```python
# 用于 LLM 模式下的分类排序
CATEGORY_RANKER_PROMPT = """
# 任务

根据查询,从以下分类列表中选择最相关的分类。

查询: {query}
目标数量: {top_k}

分类列表:
{categories_data}

输出格式:
{{"categories": ["id1", "id2", ...]}}
"""
```

#### LLM Item Ranker - 记忆项排序

```python
# 用于 LLM 模式下的记忆项排序
ITEM_RANKER_PROMPT = """
# 任务

根据查询和相关分类,从以下记忆项中选择最相关的。

查询: {query}
目标数量: {top_k}

相关分类:
{relevant_categories}

记忆项列表:
{items_data}

输出格式:
{{"items": ["id1", "id2", ...]}}
"""
```

### 12.4 分类摘要提示词 (category_summary/)

> **说明**: 用于更新分类的聚合摘要。

```python
# 默认分类摘要提示词
CATEGORY_SUMMARY_PROMPT = """
# 任务

更新分类摘要,纳入新的记忆项。

分类: {category}
原始摘要: {original_content}

新记忆项:
{new_memory_items_text}

目标长度: 约 {target_length} 字符

要求:
- 整合新旧内容
- 保持简洁连贯
- 突出关键信息
"""

# 带引用支持的分类摘要提示词 (enable_item_references=True)
CATEGORY_SUMMARY_PROMPT_WITH_REFS = """
# 任务

更新分类摘要,纳入新的记忆项。

分类: {category}
原始摘要: {original_content}

新记忆项:
{new_memory_items_text}

目标长度: 约 {target_length} 字符

要求:
- 为每个记忆项生成 [ref:item_id] 引用
- 在摘要中适当位置插入引用
- 保持摘要的连贯性和可读性
"""
```

### 12.5 自定义提示词配置

> **说明**: MemU 支持完全自定义提示词,可通过配置文件或代码覆盖默认模板。

```python
# 自定义提示词配置示例
MemorizeConfig(
    # 为特定记忆类型自定义提示词
    memory_type_prompts={
        "profile": """
            # 自定义 Profile 提取提示词

            你是用户 profile 分析师。从对话中提取:
            - 姓名、职位、公司
            - 兴趣爱好
            - 沟通偏好
            - 重要背景

            输出格式:
            <profile>
                <name>...</name>
                <interests>...</interests>
                <preferences>...</preferences>
            </profile>
        """,
    },

    # 为特定模态自定义预处理提示词
    multimodal_preprocess_prompts={
        "video": "自定义视频分析提示词...",
        "image": "自定义图像分析提示词...",
    },
)

# 或使用 CustomPrompt 结构
from memu.app.settings import CustomPrompt, PromptBlock

MemorizeConfig(
    memory_type_prompts={
        "profile": CustomPrompt(
            blocks=[
                PromptBlock(ordinal=10, name="objective", prompt="提取用户 profile 信息"),
                PromptBlock(ordinal=50, name="output", prompt="输出 XML 格式"),
            ]
        )
    }
)
```
"""
```

#### LLM Rankers

```python
# llm_category_ranker.py - LLM 分类排序
LLM_CATEGORY_RANKER_PROMPT = """
给定查询和相关分类,按相关性排序...
"""

# llm_item_ranker.py - LLM 记忆项排序
LLM_ITEM_RANKER_PROMPT = """
给定查询和相关记忆项,按相关性排序...
"""

# llm_resource_ranker.py - LLM 资源排序
LLM_RESOURCE_RANKER_PROMPT = """
给定上下文和相关资源,按相关性排序...
"""
```

### 12.4 分类摘要提示词 (category_summary/)

```python
PROMPT = """
给定分类名称、原始摘要和新记忆项,生成更新后的摘要...
"""

# 支持引用格式
PROMPT_WITH_REFS = """
使用 [ref:ITEM_ID] 格式引用源记忆项...
"""

DEFAULT_CATEGORY_SUMMARY_PROMPT_ORDINAL: dict[str, int] = {
    "objective": 10,
    "workflow": 20,
    "rules": 30,
    "output": 40,
    "examples": 50,
    "input": 90,
}
```

### 12.5 分类补丁提示词 (category_patch/)

```python
CATEGORY_PATCH_PROMPT = """
给定分类、原始摘要和更新内容(新增或删除的记忆),
生成更新后的摘要...
"""
```

---

## 第十三章: 文件存储 (blob/)

### 13.1 LocalFS

```python
class LocalFS:
    def __init__(self, base_dir: str) -> None:
        self.base = pathlib.Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    async def fetch(self, url: str, modality: str) -> tuple[str, str | None]:
        """
        获取资源并返回 (local_path, text_content)

        支持:
        - 本地文件: 直接使用
        - HTTP URL: 下载到 base_dir
        """
```

**模态处理**:
- `conversation`, `document`, `text`: 返回文本内容
- 其他模态: 仅返回文件路径

---

## 第十四章: 客户端包装器 (client/)

### 14.1 MemuOpenAIWrapper

自动注入记忆的 OpenAI 客户端包装器:

```python
class MemuOpenAIWrapper:
    def __init__(
        self,
        client,                    # 原始 OpenAI 客户端
        service: MemoryService,     # MemU 服务
        user_data: dict[str, Any],  # 用户作用域
        ranking: str = "salience",  # 排序策略
        top_k: int = 5,             # 记忆数量
    ) -> None:
```

### 14.2 使用示例

```python
from openai import OpenAI
from memu.client import wrap_openai

client = wrap_openai(
    OpenAI(),
    service,
    user_data={"user_id": "user123"},
    ranking="salience",
)

# 记忆自动注入
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's my favorite drink?"}]
)
```

---

## 第十五章: 集成 (integrations/)

### 15.1 LangGraph 集成

```python
class MemULangGraphTools:
    def __init__(self, memory_service: MemoryService) -> None:
        self.memory_service = memory_service

    def tools(self) -> list[BaseTool]:
        return [
            self.save_memory_tool(),
            self.search_memory_tool(),
        ]

    def save_memory_tool(self) -> StructuredTool:
        """保存记忆的工具"""

    def search_memory_tool(self) -> StructuredTool:
        """搜索记忆的工具"""
```

#### save_memory

```python
class SaveRecallInput(BaseModel):
    content: str                          # 要保存的内容
    user_id: str                          # 用户 ID
    metadata: dict[str, Any] | None      # 额外元数据
```

#### search_memory

```python
class SearchRecallInput(BaseModel):
    query: str                             # 搜索查询
    user_id: str                           # 用户 ID
    limit: int = 5                        # 返回数量
    metadata_filter: dict[str, Any] | None  # 元数据过滤
    min_relevance_score: float = 0.0     # 最小相关性分数
```

---

## 第十六章: 工具函数 (utils/)

### 16.1 引用处理 (references.py)

```python
REFERENCE_PATTERN = re.compile(r"\[ref:([a-zA-Z0-9_,\-]+)\]")

def extract_references(text: str | None) -> list[str]:
    """从文本中提取所有引用 ID"""

def strip_references(text: str | None) -> str | None:
    """移除文本中的引用标记"""

def format_references_as_citations(text: str | None) -> str | None:
    """将 [ref:ID] 转换为 [1], [2] 等编号引用"""

def fetch_referenced_items(text: str, store: Database) -> list[dict]:
    """获取文本中引用的记忆项"""

def build_item_reference_map(items: list[tuple[str, str]]) -> str:
    """为 LLM 提示构建引用映射字符串"""
```

### 16.2 对话格式化 (conversation.py)

```python
def format_conversation_for_preprocess(raw_text: str) -> str:
    """
    将对话格式化为适合 LLM 预处理的行格式。

    输入:
    - JSON 列表: [{"role": "...", "content": "...", "created_at": "..."}]
    - JSON 对象: {"content": [...]}

    输出格式:
    [0] 2024-01-01 [user]: Hello
    [1] [assistant]: Hi there!
    """
```

### 16.3 工具内存 (tool.py)

```python
class ToolMemoryHelper:
    @staticmethod
    def add_tool_call(item: MemoryItem, tool_call: ToolCallResult) -> None:
        """将工具调用添加到记忆项的 extra 中"""

    @staticmethod
    def get_tool_statistics(item: MemoryItem, recent_n: int | None = None) -> dict[str, Any]:
        """
        计算工具记忆统计:
        - total_calls: 总调用次数
        - recent_calls_analyzed: 分析的最近调用数
        - avg_time_cost: 平均耗时
        - success_rate: 成功率
        - avg_score: 平均分数
        - avg_token_cost: 平均 token 消耗
        """
```

---

## 第十七章: Rust 入口 (lib.rs)

```rust
use pyo3::prelude::*;

#[pyfunction]
fn hello_from_bin() -> String {
    "Hello from memu!".to_string()
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello_from_bin, m)?)?;
    Ok(())
}
```

Rust 模块提供 Python 扩展入口,当前仅包含一个简单的问候函数。

---

## 第十八章: 核心算法流程

### 18.1 记忆流程 (memorize)

```
┌──────────────────────────────────────────────────────────────┐
│                      memorize(resource_url, modality, user)    │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  1. ingest_resource                                               │
│     - fs.fetch(url, modality) -> (local_path, raw_text)         │
│     - 能力: io                                                  │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  2. preprocess_multimodal                                       │
│     - 对话: 格式化 + 分段 + 生成 caption                       │
│     - 视频: 提取中间帧 + Vision API 分析                        │
│     - 图像: Vision API 分析                                     │
│     - 文档: 精简 + 提取 caption                                │
│     - 音频: 转录 (如果需要)                                     │
│     - 能力: llm                                                │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  3. extract_items                                               │
│     - 对每个 memory_type:                                        │
│       - 构建提取提示词                                            │
│       - 并行调用 LLM                                             │
│       - 解析 XML 输出                                           │
│     - 能力: llm                                                │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  4. dedupe_merge (placeholder)                                │
│     - 预留用于去重和合并                                         │
│     - 能力: 无                                                  │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  5. categorize_items                                           │
│     - 为每个资源创建 Resource + 嵌入                              │
│     - 为每个条目创建 MemoryItem + 嵌入                            │
│     - 创建 CategoryItem 关系                                     │
│     - 能力: db, vector                                         │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  6. persist_index                                               │
│     - 更新分类摘要 (LLM)                                         │
│     - 如果启用,持久化引用                                         │
│     - 能力: db, llm                                            │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  7. build_response                                              │
│     - 返回 resource, items, categories, relations                 │
│     - 能力: 无                                                  │
└──────────────────────────────────────────────────────────────┘
```

### 18.2 检索流程 (retrieve - RAG)

```
┌──────────────────────────────────────────────────────────────┐
│                   retrieve(queries, where)                    │
│  queries: [{"role": "user", "content": "..."}, ...]           │
│  where: 过滤条件 (user_id 等)                                   │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  1. route_intention                                           │
│     - 判断是否需要检索                                           │
│     - 如果需要,重写查询                                           │
│     - 能力: llm                                                │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  2. route_category                                             │
│     - 嵌入查询                                                  │
│     - 余弦相似度搜索分类                                         │
│     - 能力: vector                                             │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  3. sufficiency_after_category                                  │
│     - 判断是否需要检索 items                                     │
│     - 如果需要,更新查询向量                                       │
│     - 能力: llm                                                │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  4. recall_items                                               │
│     - 向量搜索记忆项                                             │
│     - (可选) Salience 排序                                      │
│     - 能力: vector                                             │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  5. sufficiency_after_items                                    │
│     - 判断是否需要检索 resources                                 │
│     - 如果需要,更新查询向量                                       │
│     - 能力: llm                                                │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  6. recall_resources                                           │
│     - 向量搜索资源 (基于 caption 嵌入)                             │
│     - 能力: vector                                             │
└────────────────────────────┬─────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│  7. build_context                                              │
│     - 组装最终响应                                               │
│     - 能力: 无                                                  │
└──────────────────────────────────────────────────────────────┘
```

### 18.3 Salience 评分算法

```
Salience Score = Similarity × Reinforcement Factor × Recency Factor

其中:
- Similarity = cosine(query_vec, item_vec)
- Reinforcement Factor = log(reinforcement_count + 1)
- Recency Factor = exp(-0.693 × days_ago / recency_decay_days)
```

**特点**:
- 对数增强防止高频记忆分数过高
- 指数衰减使旧记忆逐渐淡化
- 半衰期可配置 (默认 30 天)

---

## 第十九章: 数据层次结构

```
┌─────────────────────────────────────────────────────────────────┐
│                        MemoryService                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Memorize    │  │ Retrieve    │  │ CRUD        │              │
│  │ Mixin       │  │ Mixin       │  │ Mixin       │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Database                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │ Resource    │  │ MemoryItem  │  │ Memory      │  │Category │  │
│  │ Repo       │  │ Repo       │  │ Category    │  │Item     │  │
│  │            │  │            │  │ Repo       │  │Repo    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Data Models                                  │
│                                                                 │
│  ┌───────────────┐      ┌───────────────────┐                    │
│  │  Resource     │ 1:N  │  MemoryItem        │                    │
│  │  - url        │─────│  - memory_type     │                    │
│  │  - modality   │      │  - summary         │                    │
│  │  - caption    │      │  - embedding       │                    │
│  │  - embedding  │      │  - extra           │                    │
│  └───────────────┘      └───────────────────┘                    │
│           │                        │                            │
│           │                        │ N:M                        │
│           │                        │────────────┐               │
│           │                                 │               │
│           ↓                                 ↓               │
│  ┌───────────────────┐      ┌───────────────────┐            │
│  │  MemoryCategory   │◄─────│  CategoryItem     │            │
│  │  - name           │  N:M │  - item_id        │            │
│  │  - description    │      │  - category_id    │            │
│  │  - embedding       │      └───────────────────┘            │
│  │  - summary        │                                      │
│  └───────────────────┘                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 第二十章: 客户端 API 表面

### 20.1 MemoryService 公共 API

```python
# 记忆
async memorize(resource_url, modality, user=None) -> dict

# 检索
async retrieve(queries, where=None) -> dict

# CRUD
async list_memory_items(where=None) -> dict
async list_memory_categories(where=None) -> dict
async clear_memory(where=None) -> dict

# Patch
async create_memory_item(memory_type, memory_content, memory_categories, user=None, propagate=True) -> dict
async update_memory_item(memory_id, memory_type=None, memory_content=None, memory_categories=None, user=None, propagate=True) -> dict
async delete_memory_item(memory_id, user=None, propagate=True) -> dict

# 配置
configure_pipeline(step_id, configs, pipeline="memorize") -> int
insert_step_after(target_step_id, new_step, pipeline="memorize") -> int
insert_step_before(target_step_id, new_step, pipeline="memorize") -> int
replace_step(target_step_id, new_step, pipeline="memorize") -> int
remove_step(target_step_id, pipeline="memorize") -> int

# 拦截器
intercept_before_llm_call(fn, name=None, priority=0, where=None) -> LLMInterceptorHandle
intercept_after_llm_call(fn, name=None, priority=0, where=None) -> LLMInterceptorHandle
intercept_on_error_llm_call(fn, name=None, priority=0, where=None) -> LLMInterceptorHandle
intercept_before_workflow_step(fn, name=None) -> WorkflowInterceptorHandle
intercept_after_workflow_step(fn, name=None) -> WorkflowInterceptorHandle
intercept_on_error_workflow_step(fn, name=None) -> WorkflowInterceptorHandle
```

### 20.2 返回数据结构

#### memorize 返回

```python
{
    "resource": {                    # 单个资源
        "id": "uuid",
        "url": "...",
        "modality": "...",
        "local_path": "...",
        "caption": "...",
        "created_at": "...",
        "updated_at": "..."
    },
    "resources": [...],             # 或多个资源
    "items": [
        {
            "id": "uuid",
            "resource_id": "...",
            "memory_type": "profile|event|...",
            "summary": "...",
            "created_at": "...",
            "updated_at": "...",
            "extra": {...}
        }
    ],
    "categories": [
        {
            "id": "uuid",
            "name": "...",
            "description": "...",
            "summary": "...",
            "created_at": "...",
            "updated_at": "..."
        }
    ],
    "relations": [
        {
            "id": "uuid",
            "item_id": "...",
            "category_id": "...",
            "created_at": "...",
            "updated_at": "..."
        }
    ]
}
```

#### retrieve 返回

```python
{
    "needs_retrieval": bool,
    "original_query": str,
    "rewritten_query": str,
    "next_step_query": str | None,
    "categories": [
        {
            "id": "uuid",
            "name": "...",
            "summary": "...",
            "score": 0.95,  # 相似度分数
            ...
        }
    ],
    "items": [
        {
            "id": "uuid",
            "memory_type": "...",
            "summary": "...",
            "score": 0.87,
            ...
        }
    ],
    "resources": [
        {
            "id": "uuid",
            "url": "...",
            "caption": "...",
            "score": 0.82,
            ...
        }
    ]
}
```

---

## 第二十一章: 数据库 Schema

### 21.1 PostgreSQL Schema (SQLModel)

```python
# Resources 表
class ResourceModel(BaseModelMixin, Resource):
    url: str
    modality: str
    local_path: str
    caption: str | None
    embedding: list[float] | None  # pgvector

# Memory Items 表
class MemoryItemModel(BaseModelMixin, MemoryItem):
    resource_id: str | None  # FK -> resources.id
    memory_type: MemoryType
    summary: str
    embedding: list[float] | None  # pgvector
    happened_at: datetime | None
    extra: dict[str, Any]  # JSONB

# Memory Categories 表
class MemoryCategoryModel(BaseModelMixin, MemoryCategory):
    name: str (indexed)
    description: str
    embedding: list[float] | None  # pgvector
    summary: str | None

# Category Items 表 (关系)
class CategoryItemModel(BaseModelMixin, CategoryItem):
    item_id: str  # FK -> memory_items.id
    category_id: str  # FK -> memory_categories.id
    # 唯一索引: (item_id, category_id)
```

### 21.2 SQLite Schema

```python
# 差异:
# - embedding 存储为 JSON 字符串 (embedding_json TEXT)
# - 向量搜索使用 brute-force cosine similarity
```

### 21.3 Alembic 迁移

```python
# env.py
def run_migrations_offline() -> None:
    # 离线模式

def run_migrations_online() -> None:
    # 在线模式
    # 使用 engine_from_config 连接数据库
```

---

## 第二十二章: 多后端支持

### 22.1 LLM 提供商

| 提供商 | 后端类 | API 端点 | 说明 |
|--------|--------|----------|------|
| OpenAI | OpenAILLMBackend | /chat/completions | 默认 |
| Grok | GrokBackend | /chat/completions | 继承 OpenAI |
| Doubao | DoubaoLLMBackend | /api/v3/chat/completions | 豆包 |
| OpenRouter | OpenRouterLLMBackend | /api/v1/chat/completions | OpenRouter |

### 22.2 Embedding 提供商

| 提供商 | 后端类 | API 端点 |
|--------|--------|----------|
| OpenAI | _OpenAIEmbeddingBackend | /embeddings |
| Doubao | _DoubaoEmbeddingBackend | /api/v3/embeddings |
| Grok | _OpenAIEmbeddingBackend | /embeddings |
| OpenRouter | _OpenRouterEmbeddingBackend | /api/v1/embeddings |

### 22.3 数据库后端

| 后端 | 类 | 向量支持 |
|------|------|----------|
| InMemory | InMemoryStore | brute-force |
| PostgreSQL | PostgresStore | pgvector |
| SQLite | SQLiteStore | JSON + brute-force |

---

## 第二十三章: 配置示例

### 23.1 基础配置

```python
from memu.app import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "api_key": "sk-...",
            "chat_model": "gpt-4o-mini",
        },
    },
)
```

### 23.2 自定义记忆类型

```python
service = MemoryService(
    llm_profiles={...},
    memorize_config={
        "memory_types": ["profile", "event", "skill"],
        "memory_type_prompts": {
            "skill": "提取技能信息..."
        },
        "memory_categories": [
            {"name": "技术技能", "description": "编程和工具使用"},
            {"name": "软技能", "description": "沟通和协作"},
        ],
    },
)
```

### 23.3 PostgreSQL 配置

```python
service = MemoryService(
    database_config={
        "metadata_store": {
            "provider": "postgres",
            "dsn": "postgresql://user:pass@localhost:5432/memu",
        },
        "vector_index": {
            "provider": "pgvector",
            "dsn": "postgresql://user:pass@localhost:5432/memu",
        },
    },
)
```

### 23.4 检索配置

```python
service = MemoryService(
    retrieve_config={
        "method": "rag",  # 或 "llm"
        "route_intention": True,
        "item": {
            "top_k": 10,
            "ranking": "salience",
            "recency_decay_days": 14.0,
        },
    },
)
```

---

## 第二十四章: 示例代码

### 24.1 对话记忆

```python
import asyncio
from memu.app import MemoryService

async def main():
    service = MemoryService(
        llm_profiles={
            "default": {
                "api_key": "sk-...",
                }
        },
    )

    # 保存对话
    result = await service.memorize(
        resource_url="conversation.json",  # JSON 格式对话
        modality="conversation",
        user={"user_id": "user123"},
    )
    print(f"提取了 {len(result['items'])} 个记忆项")

    # 检索记忆
    result = await service.retrieve(
        queries=[{"role": "user", "content": "我之前提到过什么偏好?"}],
        where={"user_id": "user123"},
    )
    print(f"找到 {len(result['items'])} 条相关记忆")

asyncio.run(main())
```

### 24.2 技能提取

```python
service = MemoryService(
    llm_profiles={...},
    memorize_config={
        "memory_types": ["skill"],
        "memory_type_prompts": {
            "skill": """
从日志中提取技能信息...

Text: {resource}
"""
        },
        "memory_categories": [
            {"name": "deployment", "description": "部署技能"},
            {"name": "debugging", "description": "调试技能"},
        ],
    },
)

# 处理日志文件
result = await service.memorize(
    resource_url="agent_log.txt",
    modality="document",
)
```

### 24.3 LangGraph 集成

```python
from memu.app import MemoryService
from memu.integrations.langgraph import MemULangGraphTools

service = MemoryService(...)
tools = MemULangGraphTools(service).tools()

# 在 LangGraph agent 中使用
# save_memory: 保存对话到记忆
# search_memory: 搜索相关记忆
```

---

## 第二十五章: 扩展机制

### 25.1 自定义工作流步骤

```python
from memu.workflow.step import WorkflowStep

async def my_custom_handler(state, step_context):
    # 自定义处理逻辑
    state["custom_key"] = "custom_value"
    return state

new_step = WorkflowStep(
    step_id="my_step",
    role="custom",
    handler=my_custom_handler,
    requires={"input_key"},
    produces={"custom_key"},
    capabilities={"llm"},  # 如果需要 LLM
)

service.insert_step_after(
    target_step_id="some_existing_step",
    new_step=new_step,
    pipeline="memorize",
)
```

### 25.2 拦截器使用

```python
async def log_llm_calls(ctx, request_view, response_view=None, usage=None):
    print(f"LLM Call: {ctx.operation}")
    if response_view:
        print(f"Response: {response_view.content[:100]}...")

# 注册前拦截器
service.intercept_before_llm_call(
    log_llm_calls,
    name="my_logger",
    where={"operation": "chat"},  # 可选过滤
)
```

### 25.3 自定义分类摘要提示词

```python
service = MemoryService(
    memorize_config={
        "default_category_summary_prompt": {
            "objective": "更新用户 {category} 记忆摘要",
            "rules": "保持简洁,不超过 200 字",
            "output": "直接输出摘要,不用额外标记",
        },
        "memory_categories": [
            {
                "name": "preferences",
                "summary_prompt": {
                    "objective": "专门更新偏好摘要",
                    "rules": "专注于偏好相关",
                },
            },
        ],
    },
)
```

---

## 附录 A: 类型别称

```python
# 记忆类型
MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill", "tool"]

# 工作流状态
WorkflowState = dict[str, Any]

# 工作流上下文
WorkflowContext = Mapping[str, Any] | None

# 工作流处理器
WorkflowHandler = Callable[[WorkflowState, WorkflowContext], Awaitable[WorkflowState] | WorkflowState]
```

---

## 附录 B: 常量

```python
# 默认记忆类型
DEFAULT_MEMORY_TYPES = ["profile", "event"]

# 检索排名策略
RANKING_SIMILARITY = "similarity"
RANKING_SALIENCE = "salience"

# 检索方法
METHOD_RAG = "rag"
METHOD_LLM = "llm"

# 向量索引提供商
VECTOR_PROVIDER_BRUTEFORCE = "bruteforce"
VECTOR_PROVIDER_PGVECTOR = "pgvector"
VECTOR_PROVIDER_NONE = "none"

# 数据库提供商
DB_PROVIDER_INMEMORY = "inmemory"
DB_PROVIDER_POSTGRES = "postgres"
DB_PROVIDER_SQLITE = "sqlite"
```

---

## 附录 C: 目录结构

```
src/memu/
├── __init__.py
├── app/
│   ├── __init__.py
│   ├── service.py       # MemoryService
│   ├── settings.py       # 配置模型
│   ├── memorize.py      # 记忆 Mixin
│   ├── retrieve.py      # 检索 Mixin
│   ├── crud.py          # CRUD Mixin
│   └── patch.py         # Patch Mixin
├── blob/
│   ├── __init__.py
│   └── local_fs.py      # LocalFS 文件存储
├── client/
│   ├── __init__.py
│   └── openai_wrapper.py  # OpenAI 包装器
├── database/
│   ├── __init__.py
│   ├── interfaces.py    # Database 接口
│   ├── models.py         # 核心数据模型
│   ├── factory.py        # 数据库工厂
│   ├── state.py          # 状态定义
│   ├── repositories/     # 仓储接口
│   ├── inmemory/         # 内存实现
│   ├── postgres/          # PostgreSQL 实现
│   └── sqlite/           # SQLite 实现
├── embedding/
│   ├── __init__.py
│   ├── backends/        # Embedding 后端
│   ├── http_client.py
│   └── openai_sdk.py
├── integrations/
│   ├── __init__.py
│   └── langgraph.py      # LangGraph 集成
├── llm/
│   ├── __init__.py
│   ├── backends/         # LLM 后端
│   ├── http_client.py    # HTTP LLM 客户端
│   ├── openai_sdk.py    # OpenAI SDK 客户端
│   ├── lazyllm_client.py
│   └── wrapper.py        # 拦截器包装器
├── prompts/
│   ├── __init__.py
│   ├── category_patch/
│   ├── category_summary/
│   ├── memory_type/
│   ├── preprocess/
│   └── retrieve/
├── utils/
│   ├── __init__.py
│   ├── category.py
│   ├── category_with_refs.py
│   ├── conversation.py
│   ├── references.py
│   ├── tool.py
│   └── video.py
└── workflow/
    ├── __init__.py
    ├── interceptor.py
    ├── pipeline.py
    ├── runner.py
    └── step.py
```

---

## 附录 D: 依赖项

### 核心依赖

- `defusedxml>=0.7.1`: 安全 XML 解析
- `httpx>=0.28.1`: HTTP 客户端
- `numpy>=2.3.4`: 数值计算
- `openai>=2.8.0`: OpenAI SDK
- `pydantic>=2.12.4`: 数据验证
- `sqlmodel>=0.0.27`: ORM
- `alembic>=1.14.0`: 数据库迁移
- `pendulum>=3.1.0`: 日期时间处理
- `langchain-core>=1.2.7`: LangChain 核心
- `lazyllm>=0.7.3`: LazyLLM 客户端

### 可选依赖

- `pgvector>=0.3.4`: PostgreSQL 向量支持
- `sqlalchemy[postgresql-psycbinary]>=2.0.36`: PostgreSQL 支持
- `langgraph>=0.0.10`: LangGraph 集成
- `claude-agent-sdk>=0.1.24`: Claude 集成

---

## 总结

MemU 是一个设计精良的 AI 记忆框架,具有以下特点:

1. **模块化设计**: 清晰的分层架构,从服务到数据库再到存储后端
2. **多模态支持**: 处理对话、文档、视频、图像、音频等多种输入
3. **灵活的检索**: 支持 RAG 和 LLM 两种检索模式,以及 Salience 感知排序
4. **可扩展性**: 管道系统、拦截器机制、自定义提示词支持
5. **多后端支持**: 多种 LLM 提供商、Embedding 提供商、数据库后端
6. **工作流引擎**: 基于步骤的工作流系统,支持复杂的记忆操作流程
7. **引用追踪**: 记忆项之间的引用关系,支持追踪信息来源
8. **工具集成**: LangGraph 集成,方便在代理中使用记忆功能

本文档提供了 MemU 框架的完整源代码分析,涵盖了所有主要模块、类、函数及其相互关系。
