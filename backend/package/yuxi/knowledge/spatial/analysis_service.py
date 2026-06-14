"""图层派生空间分析服务。"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text

from yuxi.repositories.knowledge_spatial_repository import KnowledgeSpatialRepository
from yuxi.storage.postgres.manager import pg_manager


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def build_field_schema_from_layer(layer: dict[str, Any]) -> list[dict[str, Any]]:
    field_schema = layer.get("field_schema") or []
    if isinstance(field_schema, str):
        try:
            field_schema = json.loads(field_schema)
        except (json.JSONDecodeError, TypeError):
            return []
    return field_schema


async def run_spatial_analysis(
    kb_id: str,
    layer_a_id: str,
    layer_b_id: str,
    operation: str,
    *,
    target_name: str,
    created_by: str,
) -> dict[str, Any]:
    valid_ops = {"intersection", "union", "difference"}
    if operation not in valid_ops:
        raise ValueError(f"不支持的空间分析操作: {operation}")
    if layer_a_id == layer_b_id:
        raise ValueError("空间分析需要选择两个不同图层")

    repository = KnowledgeSpatialRepository()
    layer_a = await repository.get_layer(kb_id, layer_a_id)
    layer_b = await repository.get_layer(kb_id, layer_b_id)
    if not layer_a or not layer_b:
        raise ValueError("空间分析图层不存在或不属于当前知识库")

    new_layer_id = _generate_id("spl")
    target_name = (target_name or "").strip() or f"{operation}_{layer_a['name']}_{layer_b['name']}"
    field_schema = [
        {"name": "_operation", "type": "string"},
        {"name": "_source_layer_a", "type": "string"},
        {"name": "_source_layer_b", "type": "string"},
    ]
    await repository.create_layer(
        {
            "layer_id": new_layer_id,
            "source_id": None,
            "kb_id": kb_id,
            "name": target_name,
            "geometry_type": "Unknown",
            "original_srid": 4326,
            "field_schema": field_schema,
            "feature_count": 0,
            "bbox": None,
            "created_by": created_by,
        }
    )

    params = {
        "kb_id": kb_id,
        "layer_a_id": layer_a_id,
        "layer_b_id": layer_b_id,
        "new_layer_id": new_layer_id,
        "feature_prefix": f"spf_{new_layer_id}_",
        "operation": operation,
    }
    try:
        async with pg_manager.get_async_session_context() as session:
            if operation == "intersection":
                insert_sql = text(
                    """
                    INSERT INTO knowledge_spatial_features (
                        feature_id, layer_id, source_id, kb_id, source_feature_id,
                        geometry_type, properties, text_content, bbox, geom
                    )
                    SELECT
                        :feature_prefix || row_number() OVER (),
                        :new_layer_id,
                        NULL,
                        :kb_id,
                        a.feature_id || ':' || b.feature_id,
                        GeometryType(result.geom),
                        jsonb_build_object(
                            '_operation', :operation,
                            '_source_layer_a', :layer_a_id,
                            '_source_layer_b', :layer_b_id,
                            'layer_a', COALESCE(a.properties, '{}'::jsonb),
                            'layer_b', COALESCE(b.properties, '{}'::jsonb)
                        ),
                        '',
                        jsonb_build_array(
                            ST_XMin(ST_Envelope(result.geom)),
                            ST_YMin(ST_Envelope(result.geom)),
                            ST_XMax(ST_Envelope(result.geom)),
                            ST_YMax(ST_Envelope(result.geom))
                        ),
                        result.geom
                    FROM knowledge_spatial_features a
                    JOIN knowledge_spatial_features b
                      ON b.kb_id = a.kb_id
                     AND b.layer_id = :layer_b_id
                     AND ST_Intersects(a.geom, b.geom)
                    CROSS JOIN LATERAL (
                        SELECT ST_MakeValid(ST_Intersection(a.geom, b.geom)) AS geom
                    ) result
                    WHERE a.kb_id = :kb_id
                      AND a.layer_id = :layer_a_id
                      AND NOT ST_IsEmpty(result.geom)
                    """
                )
            elif operation == "difference":
                insert_sql = text(
                    """
                    INSERT INTO knowledge_spatial_features (
                        feature_id, layer_id, source_id, kb_id, source_feature_id,
                        geometry_type, properties, text_content, bbox, geom
                    )
                    SELECT
                        :feature_prefix || row_number() OVER (),
                        :new_layer_id,
                        NULL,
                        :kb_id,
                        a.feature_id,
                        GeometryType(result.geom),
                        jsonb_build_object(
                            '_operation', :operation,
                            '_source_layer_a', :layer_a_id,
                            '_source_layer_b', :layer_b_id,
                            'source', COALESCE(a.properties, '{}'::jsonb)
                        ),
                        '',
                        jsonb_build_array(
                            ST_XMin(ST_Envelope(result.geom)),
                            ST_YMin(ST_Envelope(result.geom)),
                            ST_XMax(ST_Envelope(result.geom)),
                            ST_YMax(ST_Envelope(result.geom))
                        ),
                        result.geom
                    FROM knowledge_spatial_features a
                    CROSS JOIN LATERAL (
                        SELECT ST_MakeValid(
                            CASE
                                WHEN overlaps.geom IS NULL THEN a.geom
                                ELSE ST_Difference(a.geom, overlaps.geom)
                            END
                        ) AS geom
                        FROM (
                            SELECT ST_UnaryUnion(ST_Collect(b.geom)) AS geom
                            FROM knowledge_spatial_features b
                            WHERE b.kb_id = :kb_id
                              AND b.layer_id = :layer_b_id
                              AND ST_Intersects(a.geom, b.geom)
                        ) overlaps
                    ) result
                    WHERE a.kb_id = :kb_id
                      AND a.layer_id = :layer_a_id
                      AND NOT ST_IsEmpty(result.geom)
                    """
                )
            else:
                insert_sql = text(
                    """
                    INSERT INTO knowledge_spatial_features (
                        feature_id, layer_id, source_id, kb_id, source_feature_id,
                        geometry_type, properties, text_content, bbox, geom
                    )
                    SELECT
                        :feature_prefix || '1',
                        :new_layer_id,
                        NULL,
                        :kb_id,
                        :operation,
                        GeometryType(result.geom),
                        jsonb_build_object(
                            '_operation', :operation,
                            '_source_layer_a', :layer_a_id,
                            '_source_layer_b', :layer_b_id
                        ),
                        '',
                        jsonb_build_array(
                            ST_XMin(ST_Envelope(result.geom)),
                            ST_YMin(ST_Envelope(result.geom)),
                            ST_XMax(ST_Envelope(result.geom)),
                            ST_YMax(ST_Envelope(result.geom))
                        ),
                        result.geom
                    FROM (
                        SELECT ST_MakeValid(ST_UnaryUnion(ST_Collect(geom))) AS geom
                        FROM knowledge_spatial_features
                        WHERE kb_id = :kb_id
                          AND layer_id IN (:layer_a_id, :layer_b_id)
                    ) result
                    WHERE result.geom IS NOT NULL AND NOT ST_IsEmpty(result.geom)
                    """
                )
            await session.execute(insert_sql, params)
            stats = (
                await session.execute(
                    text(
                        """
                        SELECT
                            count(*) AS feature_count,
                            COALESCE(MODE() WITHIN GROUP (ORDER BY geometry_type), 'Unknown') AS geometry_type,
                            CASE WHEN count(*) = 0 THEN NULL ELSE jsonb_build_array(
                                MIN(ST_XMin(ST_Envelope(geom))),
                                MIN(ST_YMin(ST_Envelope(geom))),
                                MAX(ST_XMax(ST_Envelope(geom))),
                                MAX(ST_YMax(ST_Envelope(geom)))
                            ) END AS bbox
                        FROM knowledge_spatial_features
                        WHERE kb_id = :kb_id AND layer_id = :new_layer_id
                        """
                    ),
                    params,
                )
            ).one()
            await session.execute(
                text(
                    """
                    UPDATE knowledge_spatial_layers
                    SET feature_count = :feature_count,
                        geometry_type = :geometry_type,
                        bbox = CAST(:bbox AS JSONB)
                    WHERE kb_id = :kb_id AND layer_id = :new_layer_id
                    """
                ),
                {
                    **params,
                    "feature_count": int(stats.feature_count),
                    "geometry_type": stats.geometry_type,
                    "bbox": json.dumps(stats.bbox) if stats.bbox is not None else None,
                },
            )
        return {
            "layer_id": new_layer_id,
            "name": target_name,
            "feature_count": int(stats.feature_count),
            "geometry_type": stats.geometry_type,
            "bbox": stats.bbox,
            "operation": operation,
            "source_layer_ids": [layer_a_id, layer_b_id],
        }
    except Exception:
        await repository.delete_layer(kb_id, new_layer_id)
        raise
