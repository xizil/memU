"""
MemU 数据模型层 - 内存框架的核心数据结构

本模块定义了 MemU 的三层记忆架构数据模型:
1. Resource (资源层): 原始数据存储
2. MemoryItem (记忆项层): 提取的结构化记忆
3. MemoryCategory (分类层): 记忆的组织分类

作者: xizil
版本: 1.5.1
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Literal

import pendulum
from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# 类型定义
# =============================================================================

# 记忆类型枚举 - 定义了六种核心记忆类型
# - profile: 用户 profile 信息 (如偏好、习惯)
# - event: 事件记录 (如会议、经历)
# - knowledge: 知识性记忆 (如技能、概念)
# - behavior: 行为模式记忆
# - skill: 技能相关记忆
# - tool: 工具使用记忆 (包含工具调用统计)
MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill", "tool"]


# =============================================================================
# 工具函数
# =============================================================================

def compute_content_hash(summary: str, memory_type: str) -> str:
    """
    为记忆内容生成唯一哈希值,用于去重和强化学习。

    规范化处理:
    - 统一小写
    - 去除首尾空格
    - 合并多余空白字符

    例如 "I love coffee" 和 "I  love  coffee" 会生成相同的哈希。

    参数:
        summary: 记忆摘要文本
        memory_type: 记忆类型 (profile/event/knowledge/behavior/skill/tool)

    返回:
        16字符的十六进制哈希字符串

    示例:
        >>> compute_content_hash("I love coffee", "profile")
        'a1b2c3d4e5f6g7h8'
    """
    # 规范化: 转小写 -> 去除首尾空格 -> 合并空白字符
    normalized = " ".join(summary.lower().split())
    content = f"{memory_type}:{normalized}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# 基础模型
# =============================================================================

class BaseRecord(BaseModel):
    """
    所有数据记录的基类,提供统一的 ID 和时间戳管理。

    特点:
    - 自动生成 UUID 作为主键
    - 自动记录创建时间和更新时间
    - 使用 pendulum 处理时区 (UTC)
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    updated_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))


class ToolCallResult(BaseModel):
    """
    工具调用结果记录 (Tool Memory 专用)

    用于追踪 AI Agent 工具调用的:
    - 输入/输出详情
    - 性能指标 (耗时、token 消耗)
    - 质量评分 (0.0-1.0)
    - 去重哈希 (基于输入+输出)

    用途:
    - 分析工具使用模式
    - 优化工具选择策略
    - 识别高频/低效工具
    """

    tool_name: str = Field(..., description="被调用的工具名称")
    input: dict[str, Any] | str = Field(default="", description="工具输入参数")
    output: str = Field(default="", description="工具输出结果")
    success: bool = Field(default=True, description="工具调用是否成功")
    time_cost: float = Field(default=0.0, description="工具执行耗时 (秒)")
    token_cost: int = Field(default=-1, description="工具消耗的 token 数 (-1 表示未知)")
    score: float = Field(default=0.0, description="质量评分 (0.0-1.0)")
    call_hash: str = Field(default="", description="用于去重的输入+输出哈希")
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))

    def generate_hash(self) -> str:
        """
        生成工具调用的去重哈希。

        哈希基于: tool_name + input (JSON排序) + output
        相同输入输出的调用会生成相同的哈希值。
        """
        input_str = json.dumps(self.input, sort_keys=True) if isinstance(self.input, dict) else str(self.input)
        combined = f"{self.tool_name}|{input_str}|{self.output}"
        return hashlib.md5(combined.encode("utf-8"), usedforsecurity=False).hexdigest()

    def ensure_hash(self) -> None:
        """确保 call_hash 已设置,如为空则自动生成。"""
        if not self.call_hash:
            self.call_hash = self.generate_hash()


# =============================================================================
# 三层记忆架构模型
# =============================================================================

class Resource(BaseRecord):
    """
    资源层 (第一层) - 原始数据的存储

    代表需要记忆的原始资源,如:
    - 对话记录
    - 文档内容
    - 图片/视频
    - 音频文件

    属性:
        url: 资源的原始 URL 或标识符
        modality: 资源模态类型 (conversation/document/image/video/audio)
        local_path: 本地存储路径
        caption: 资源的文字描述/摘要 (用于检索)
        embedding: caption 的向量表示 (用于向量检索)
    """

    url: str  # 资源原始 URL
    modality: str  # 模态类型: conversation/document/image/video/audio
    local_path: str  # 本地存储路径
    caption: str | None = None  # 资源描述/摘要
    embedding: list[float] | None = None  # 向量嵌入 (用于 RAG)


class MemoryItem(BaseRecord):
    """
    记忆项层 (第二层) - 从资源中提取的结构化记忆

    这是记忆框架的核心数据结构,代表从原始资源中提取的有意义的信息片段。

    属性:
        resource_id: 来源资源的 ID (关联到 Resource 层)
        memory_type: 记忆类型 (profile/event/knowledge/behavior/skill/tool)
        summary: 记忆内容的摘要描述
        embedding: summary 的向量表示 (用于相似度检索)
        happened_at: 记忆关联的事件时间
        extra: 扩展数据 (包含多种可选字段)

    extra 字段用途:
        - content_hash: 内容去重哈希
        - reinforcement_count: 强化学习次数
        - last_reinforced_at: 最后强化时间 (ISO格式)
        - ref_id: 跨记忆引用 ID (用于 category 摘要中的引用)
        - when_to_use: 检索提示 (何时使用此记忆)
        - metadata: 类型特定元数据 (如工具名、平均成功率)
        - tool_calls: 工具调用历史 (tool 类型专用)
    """

    resource_id: str | None  # 关联的 Resource ID
    memory_type: str  # 记忆类型
    summary: str  # 记忆摘要
    embedding: list[float] | None = None  # 向量嵌入
    happened_at: datetime | None = None  # 事件时间
    extra: dict[str, Any] = {}  # 扩展数据


class MemoryCategory(BaseRecord):
    """
    分类层 (第三层) - 记忆的组织结构

    用于对 MemoryItem 进行分类组织,支持:
    - 自动生成摘要
    - 向量检索
    - 层级组织

    属性:
        name: 分类名称
        description: 分类描述
        embedding: 描述的向量表示 (用于匹配相关记忆)
        summary: 分类的聚合摘要 (包含该分类下所有记忆的要点)
    """

    name: str  # 分类名称
    description: str  # 分类描述
    embedding: list[float] | None = None  # 向量嵌入
    summary: str | None = None  # 聚合摘要


class CategoryItem(BaseRecord):
    """
    分类-记忆项关联表

    建立 MemoryItem 和 MemoryCategory 之间的多对多关系。

    属性:
        item_id: 记忆项 ID
        category_id: 分类 ID
    """

    item_id: str  # 关联的 MemoryItem ID
    category_id: str  # 关联的 MemoryCategory ID


# =============================================================================
# 作用域模型混合
# =============================================================================

def merge_scope_model[TBaseRecord: BaseRecord](
    user_model: type[BaseModel], core_model: type[TBaseRecord], *, name_suffix: str
) -> type[TBaseRecord]:
    """
    创建混合了用户作用域的核心模型。

    这允许在多租户/多用户场景下,为每个用户的数据添加作用域标识。

    参数:
        user_model: 用户作用域模型 (包含 user_id 等字段)
        core_model: 核心数据模型 (Resource/MemoryItem等)
        name_suffix: 生成的模型名称后缀

    返回:
        混合了 user_model 和 core_model 的新模型类

    注意:
        如果 user_model 和 core_model 有相同字段名的属性,会抛出 TypeError
    """
    overlap = set(user_model.model_fields) & set(core_model.model_fields)
    if overlap:
        msg = f"Scope fields conflict with core model fields: {sorted(overlap)}"
        raise TypeError(msg)

    return type(
        f"{user_model.__name__}{core_model.__name__}{name_suffix}",
        (user_model, core_model),
        {"model_config": ConfigDict(extra="allow")},
    )


def build_scoped_models(
    user_model: type[BaseModel],
) -> tuple[type[Resource], type[MemoryCategory], type[MemoryItem], type[CategoryItem]]:
    """
    构建带有用户作用域的数据模型集合。

    参数:
        user_model: 用户作用域模型

    返回:
        元组 (Resource模型, MemoryCategory模型, MemoryItem模型, CategoryItem模型)

    用途:
        在多用户环境下,自动为所有数据模型添加 user_id 等作用域字段
    """
    resource_model = merge_scope_model(user_model, Resource, name_suffix="Resource")
    memory_category_model = merge_scope_model(user_model, MemoryCategory, name_suffix="MemoryCategory")
    memory_item_model = merge_scope_model(user_model, MemoryItem, name_suffix="MemoryItem")
    category_item_model = merge_scope_model(user_model, CategoryItem, name_suffix="CategoryItem")
    return resource_model, memory_category_model, memory_item_model, category_item_model


__all__ = [
    "BaseRecord",
    "CategoryItem",
    "MemoryCategory",
    "MemoryItem",
    "MemoryType",
    "Resource",
    "ToolCallResult",
    "build_scoped_models",
    "compute_content_hash",
    "merge_scope_model",
]
