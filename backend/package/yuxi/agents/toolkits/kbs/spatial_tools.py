"""空间数据智能体工具。"""

from typing import Any

from langgraph.prebuilt.tool_node import ToolRuntime
from pydantic import BaseModel, Field

from yuxi.agents.toolkits.kbs.tools import _resolve_visible_knowledge_bases_for_query
from yuxi.agents.toolkits.registry import tool
from yuxi.utils import logger


async def _get_spatial_repo():
    from yuxi.repositories.knowledge_spatial_repository import KnowledgeSpatialRepository

    return KnowledgeSpatialRepository()


async def _get_composition_repo():
    from yuxi.repositories.knowledge_spatial_composition_repository import (
        KnowledgeSpatialCompositionRepository,
    )

    return KnowledgeSpatialCompositionRepository()


async def _resolve_spatial_kb(kb_id: str, runtime: ToolRuntime | None) -> tuple[str | None, str | None]:
    normalized_kb_id = str(kb_id or "").strip()
    if not normalized_kb_id:
        return None, "请提供 kb_id"

    visible_kbs = await _resolve_visible_knowledge_bases_for_query(runtime)
    if not visible_kbs:
        return None, "无法获取当前会话可访问的知识库"

    target = next(
        (kb for kb in visible_kbs if str(kb.get("kb_id") or "").strip() == normalized_kb_id),
        None,
    )
    if target is None:
        return None, f"知识库资源 '{normalized_kb_id}' 不存在或当前会话未启用"
    if str(target.get("kb_type") or "milvus").lower() != "milvus":
        return None, "空间数据工具仅支持 Milvus 知识库"
    return normalized_kb_id, None


def _parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    try:
        parts = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise ValueError("bbox 必须为 west,south,east,north") from exc
    if len(parts) != 4:
        raise ValueError("bbox 必须包含四个坐标值")
    west, south, east, north = parts
    if west >= east or south >= north:
        raise ValueError("bbox 坐标范围无效")
    return west, south, east, north


def _merge_bbox(
    current: list[float] | None,
    bbox: list[float] | None,
) -> list[float] | None:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return current
    if current is None:
        return list(bbox)
    return [
        min(current[0], bbox[0]),
        min(current[1], bbox[1]),
        max(current[2], bbox[2]),
        max(current[3], bbox[3]),
    ]


def _map_layer_payload(
    kb_id: str,
    layer: dict[str, Any],
    item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = item or {}
    popup_fields = [
        str(field.get("name"))
        for field in (layer.get("field_schema") or [])
        if isinstance(field, dict) and field.get("name")
    ][:12]
    layer_id = str(layer.get("layer_id") or "")
    return {
        "layer_id": layer_id,
        "name": layer.get("name") or layer_id,
        "geometry_type": layer.get("geometry_type") or "Unknown",
        "feature_count": int(layer.get("feature_count") or 0),
        "bbox": layer.get("bbox"),
        "url": f"/api/knowledge/databases/{kb_id}/spatial/layers/{layer_id}/features",
        "visible": bool(item.get("visible", True)),
        "opacity": float(item.get("opacity", 1)),
        "style": item.get("style_override") or {},
        "popup_fields": popup_fields,
    }


class ListSpatialLayersInput(BaseModel):
    kb_id: str = Field(description="知识库资源 ID")


class QuerySpatialFeaturesInput(BaseModel):
    kb_id: str = Field(description="知识库资源 ID")
    layer_id: str = Field(description="图层 ID，来自 list_spatial_layers")
    bbox: str | None = Field(
        default=None,
        description="可选，格式 'west,south,east,north' 的边界框",
    )
    limit: int = Field(default=20, ge=1, le=100, description="最大返回要素数")


class ShowSpatialMapInput(BaseModel):
    kb_id: str = Field(description="知识库资源 ID")
    layer_ids: list[str] = Field(default_factory=list, description="要显示的图层 ID 列表")
    composition_id: str | None = Field(default=None, description="可选的图层组合 ID")
    title: str = Field(default="空间数据地图", description="地图标题")


@tool(category="knowledge", tags=["空间数据"], args_schema=ListSpatialLayersInput)
async def list_spatial_layers(kb_id: str, runtime: ToolRuntime = None) -> Any:
    """列出当前会话可访问知识库中的空间图层。"""
    normalized_kb_id, error = await _resolve_spatial_kb(kb_id, runtime)
    if error:
        return {"error": error}

    try:
        layers = await (await _get_spatial_repo()).list_layers(normalized_kb_id)
        return {
            "kb_id": normalized_kb_id,
            "layer_count": len(layers),
            "layers": [
                {
                    "layer_id": layer.get("layer_id"),
                    "name": layer.get("name"),
                    "source_name": layer.get("source_name"),
                    "geometry_type": layer.get("geometry_type") or "Unknown",
                    "feature_count": int(layer.get("feature_count") or 0),
                    "bbox": layer.get("bbox"),
                }
                for layer in layers
            ],
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(f"列出空间图层失败: {exc}")
        return {"error": f"查询失败: {exc}"}


@tool(category="knowledge", tags=["空间数据"], args_schema=QuerySpatialFeaturesInput)
async def query_spatial_features(
    kb_id: str,
    layer_id: str,
    bbox: str | None = None,
    limit: int = 20,
    runtime: ToolRuntime = None,
) -> Any:
    """查询空间要素摘要，不返回完整几何坐标。"""
    normalized_kb_id, error = await _resolve_spatial_kb(kb_id, runtime)
    if error:
        return {"error": error}
    normalized_layer_id = str(layer_id or "").strip()
    if not normalized_layer_id:
        return {"error": "请提供 layer_id"}

    try:
        parsed_bbox = _parse_bbox(bbox)
        repo = await _get_spatial_repo()
        layer_info = await repo.get_layer(normalized_kb_id, normalized_layer_id)
        if not layer_info:
            return {"error": f"图层 {normalized_layer_id} 不存在"}

        result = await repo.list_layer_features(
            normalized_kb_id,
            normalized_layer_id,
            bbox=parsed_bbox,
            limit=min(limit, 100),
        )
        summaries = []
        for feature in (result.get("features") or [])[:limit]:
            properties = {}
            for key, value in (feature.get("properties") or {}).items():
                text = str(value)
                properties[key] = f"{text[:120]}..." if len(text) > 120 else text
            summaries.append(
                {
                    "feature_id": feature.get("id") or (feature.get("properties") or {}).get("feature_id"),
                    "geometry_type": (feature.get("geometry") or {}).get("type"),
                    "properties": properties,
                }
            )

        return {
            "kb_id": normalized_kb_id,
            "layer_id": normalized_layer_id,
            "layer_name": layer_info.get("name"),
            "total_features": int(result.get("total") or 0),
            "returned": len(summaries),
            "features": summaries,
            "bbox": list(parsed_bbox) if parsed_bbox else None,
        }
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"查询空间要素失败: {exc}")
        return {"error": f"查询失败: {exc}"}


@tool(category="knowledge", tags=["空间数据", "地图"], args_schema=ShowSpatialMapInput)
async def show_spatial_map(
    kb_id: str,
    layer_ids: list[str] | None = None,
    composition_id: str | None = None,
    title: str = "空间数据地图",
    runtime: ToolRuntime = None,
) -> Any:
    """返回会话地图所需的 URL、图层、范围、样式和弹窗字段。"""
    normalized_kb_id, error = await _resolve_spatial_kb(kb_id, runtime)
    if error:
        return {"error": error}

    try:
        layers = await (await _get_spatial_repo()).list_layers(normalized_kb_id)
        layer_map = {str(layer.get("layer_id")): layer for layer in layers}
        requested_items: list[dict[str, Any]]

        if composition_id:
            composition = await (await _get_composition_repo()).get(
                normalized_kb_id,
                composition_id,
            )
            if not composition:
                return {"error": f"图层组合 {composition_id} 不存在"}
            requested_items = composition.get("items") or []
            if title == "空间数据地图":
                title = composition.get("name") or title
        else:
            requested_items = [{"layer_id": layer_id} for layer_id in (layer_ids or [])[:10]]

        if not requested_items:
            return {"error": "请提供至少一个图层 ID 或 composition_id"}

        selected_layers = []
        merged_bbox = None
        for item in requested_items[:20]:
            layer = layer_map.get(str(item.get("layer_id") or ""))
            if not layer:
                continue
            payload = _map_layer_payload(normalized_kb_id, layer, item)
            selected_layers.append(payload)
            if payload["visible"]:
                merged_bbox = _merge_bbox(merged_bbox, payload.get("bbox"))

        if not selected_layers:
            return {"error": "未找到匹配的图层"}

        return {
            "kb_id": normalized_kb_id,
            "composition_id": composition_id,
            "title": title,
            "layers": selected_layers,
            "bounds": merged_bbox,
            "map_config": {
                "map_style": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                "center": (
                    [
                        (merged_bbox[0] + merged_bbox[2]) / 2,
                        (merged_bbox[1] + merged_bbox[3]) / 2,
                    ]
                    if merged_bbox
                    else [0, 0]
                ),
                "zoom": 12,
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(f"显示空间地图失败: {exc}")
        return {"error": f"地图生成失败: {exc}"}
