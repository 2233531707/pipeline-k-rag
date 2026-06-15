"""显式知识图谱查询工具模块"""

import re
from typing import Any

from langgraph.prebuilt.tool_node import ToolRuntime
from pydantic import BaseModel, Field

from yuxi.agents.toolkits.kbs.tools import (
    _resolve_visible_knowledge_bases_for_query,
)
from yuxi.agents.toolkits.registry import tool
from yuxi.utils import logger


class QueryKnowledgeGraphInput(BaseModel):
    """显式查询知识图谱节点和关系的输入模型"""

    kb_id: str = Field(description="知识库资源 ID 或知识库名称")
    keyword: str = Field(
        default="*",
        description="图谱查询关键词；省略或使用 * 表示任意返回节点",
    )
    max_depth: int = Field(default=1, ge=0, le=5, description="关系跳数，0 表示仅匹配关键词节点")
    max_nodes: int = Field(default=50, ge=1, le=200, description="最大返回节点数")
    exclude_chunk: bool = Field(default=True, description="是否排除 Chunk 节点，默认排除以聚焦实体")


def _extract_retrieval_hints(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    keyword: str,
) -> dict[str, Any]:
    """从图谱查询结果中提取增强检索提示信息。

    目标：让模型能够将图谱中的实体/Chunk/文件 ID 反哺到 query_kb，
    实现图谱种子增强检索。
    """
    graph_entity_ids: list[str] = []
    chunk_ids: list[str] = []
    file_ids: list[str] = []

    for node in nodes:
        node_type = node.get("type", "")
        props = node.get("properties") or {}

        if node_type == "Chunk":
            cid = props.get("chunk_id")
            if cid and cid not in chunk_ids:
                chunk_ids.append(cid)
            fid = props.get("file_id")
            if fid and fid not in file_ids:
                file_ids.append(fid)
        else:
            eid = props.get("entity_id")
            if eid and eid not in graph_entity_ids:
                graph_entity_ids.append(eid)
            # 实体关联的 chunk_ids 也可能是检索线索
            ent_chunk_ids = props.get("chunk_ids") or []
            for cid in ent_chunk_ids:
                if cid not in chunk_ids:
                    chunk_ids.append(cid)

    # 从关系中也提取可能的线索
    for edge in edges:
        eprops = edge.get("properties") or {}
        for key in ("chunk_id", "source_chunk_id", "target_chunk_id"):
            cid = eprops.get(key)
            if cid and cid not in chunk_ids:
                chunk_ids.append(cid)

    # 从 keyword 中分词提取关键词
    keywords: list[str] = []
    raw_tokens = re.split(r"[，,、\s]+", keyword.strip()) if keyword.strip() and keyword.strip() != "*" else []
    for token in raw_tokens:
        token = token.strip()
        if token and len(token) >= 1:
            keywords.append(token)

    # 合并实体名作为关键词
    for node in nodes:
        name = node.get("name") or ""
        if name and name not in keywords and name != "Unknown":
            keywords.append(name)

    return {
        "graph_entity_ids": graph_entity_ids[:30],
        "chunk_ids": chunk_ids[:30],
        "file_ids": file_ids[:20],
        "keywords": keywords[:20],
    }


@tool(category="knowledge", tags=["知识库", "图谱"], args_schema=QueryKnowledgeGraphInput)
async def query_knowledge_graph(
    kb_id: str,
    keyword: str = "*",
    max_depth: int = 1,
    max_nodes: int = 50,
    exclude_chunk: bool = True,
    runtime: ToolRuntime = None,
) -> dict[str, Any]:
    """显式查询知识图谱中的节点和关系

    当用户需要探查知识图谱中的实体（人物、机构、概念等）及其之间的关系时使用。
    与 query_kb 不同，本工具直接返回图谱结构而非文档片段。
    返回结果中的 graph_entity_ids 可用于 query_kb 的图谱增强检索。

    Args:
        kb_id: 知识库资源 ID 或知识库名称
        keyword: 图谱查询关键词；省略或使用 * 表示任意返回节点
        max_depth: 关系跳数（0=仅匹配节点，1=一跳邻居，以此类推）
        max_nodes: 最大返回节点数
        exclude_chunk: 是否排除 Chunk 节点

    Returns:
        包含 nodes、edges 和 retrieval_hints 的字典
    """
    if not kb_id:
        return {"error": "请提供 kb_id"}
    normalized_keyword = str(keyword or "").strip() or "*"

    visible_kbs = await _resolve_visible_knowledge_bases_for_query(runtime)
    if not visible_kbs:
        return {"error": "无法获取当前会话可访问的知识库"}

    normalized_kb_id = str(kb_id).strip()
    matched_kbs = [kb for kb in visible_kbs if str(kb.get("kb_id") or "").strip() == normalized_kb_id]
    if not matched_kbs:
        matched_kbs = [kb for kb in visible_kbs if str(kb.get("name") or "").strip() == normalized_kb_id]
    if len(matched_kbs) > 1:
        return {"error": f"知识库名称 '{normalized_kb_id}' 不唯一，请改用 kb_id"}
    if not matched_kbs:
        return {"error": f"知识库资源 '{normalized_kb_id}' 不存在或当前会话未启用"}

    matched_kb = matched_kbs[0]
    normalized_kb_id = str(matched_kb.get("kb_id") or "").strip()
    kb_type = str(matched_kb.get("kb_type") or "").lower()

    if kb_type != "milvus":
        return {"error": f"知识库 '{normalized_kb_id}' 类型为 '{kb_type}'，不支持图谱查询。仅 Milvus 知识库支持图谱。"}

    try:
        from yuxi.knowledge.graphs.milvus_graph_service import MilvusGraphService

        service = MilvusGraphService(kb_id=normalized_kb_id)
        result = await service.query_nodes(
            kb_id=normalized_kb_id,
            keyword=normalized_keyword,
            max_depth=max_depth,
            max_nodes=max_nodes,
            exclude_chunk=exclude_chunk,
        )

        nodes = result.get("nodes") or []
        edges = result.get("edges") or []

        retrieval_hints = _extract_retrieval_hints(nodes, edges, normalized_keyword)

        return {
            "kb_id": normalized_kb_id,
            "query": normalized_keyword,
            "nodes": nodes,
            "edges": edges,
            "retrieval_hints": retrieval_hints,
        }
    except Exception as e:
        logger.error(f"知识图谱查询失败: {e}")
        return {"error": f"图谱查询失败: {str(e)}"}
