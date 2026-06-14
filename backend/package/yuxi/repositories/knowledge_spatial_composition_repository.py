from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from yuxi.storage.postgres.manager import pg_manager


def _json_loads(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    return json.loads(value)


class KnowledgeSpatialCompositionRepository:
    async def create(
        self,
        *,
        composition_id: str,
        kb_id: str,
        name: str,
        items: list[dict[str, Any]],
        created_by: str,
    ) -> dict[str, Any]:
        async with pg_manager.get_async_session_context() as session:
            layer_ids = [item["layer_id"] for item in items]
            layer_count = (
                await session.execute(
                    text(
                        """
                        SELECT count(*) FROM knowledge_spatial_layers
                        WHERE kb_id = :kb_id
                          AND layer_id = ANY(CAST(:layer_ids AS VARCHAR[]))
                        """
                    ),
                    {"kb_id": kb_id, "layer_ids": layer_ids},
                )
            ).scalar_one()
            if layer_count != len(set(layer_ids)):
                raise ValueError("组合中包含不存在或无权访问的图层")

            await session.execute(
                text(
                    """
                    INSERT INTO knowledge_spatial_layer_compositions
                        (composition_id, kb_id, name, created_by)
                    VALUES (:composition_id, :kb_id, :name, :created_by)
                    """
                ),
                {
                    "composition_id": composition_id,
                    "kb_id": kb_id,
                    "name": name,
                    "created_by": created_by,
                },
            )
            await self._replace_items(session, composition_id, items)
        return await self.get(kb_id, composition_id)

    async def update(
        self,
        *,
        composition_id: str,
        kb_id: str,
        name: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                text(
                    """
                    UPDATE knowledge_spatial_layer_compositions
                    SET name = :name, updated_at = NOW()
                    WHERE composition_id = :composition_id AND kb_id = :kb_id
                    """
                ),
                {"composition_id": composition_id, "kb_id": kb_id, "name": name},
            )
            if not result.rowcount:
                return None

            layer_ids = [item["layer_id"] for item in items]
            layer_count = (
                await session.execute(
                    text(
                        """
                        SELECT count(*) FROM knowledge_spatial_layers
                        WHERE kb_id = :kb_id
                          AND layer_id = ANY(CAST(:layer_ids AS VARCHAR[]))
                        """
                    ),
                    {"kb_id": kb_id, "layer_ids": layer_ids},
                )
            ).scalar_one()
            if layer_count != len(set(layer_ids)):
                raise ValueError("组合中包含不存在或无权访问的图层")
            await self._replace_items(session, composition_id, items)
        return await self.get(kb_id, composition_id)

    async def list(self, kb_id: str) -> list[dict[str, Any]]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                text(
                    """
                    SELECT composition_id
                    FROM knowledge_spatial_layer_compositions
                    WHERE kb_id = :kb_id
                    ORDER BY updated_at DESC, id DESC
                    """
                ),
                {"kb_id": kb_id},
            )
            composition_ids = [row[0] for row in result.fetchall()]
        compositions = []
        for composition_id in composition_ids:
            composition = await self.get(kb_id, composition_id)
            if composition:
                compositions.append(composition)
        return compositions

    async def get(self, kb_id: str, composition_id: str) -> dict[str, Any] | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                text(
                    """
                    SELECT composition_id, kb_id, name, created_by, created_at, updated_at
                    FROM knowledge_spatial_layer_compositions
                    WHERE kb_id = :kb_id AND composition_id = :composition_id
                    """
                ),
                {"kb_id": kb_id, "composition_id": composition_id},
            )
            row = result.fetchone()
            if not row:
                return None
            composition = dict(row._mapping)

            items_result = await session.execute(
                text(
                    """
                    SELECT i.layer_id, l.name, l.geometry_type, l.feature_count, l.bbox,
                           i.position, i.visible, i.opacity, i.style_override
                    FROM knowledge_spatial_layer_composition_items i
                    JOIN knowledge_spatial_layers l ON l.layer_id = i.layer_id
                    WHERE i.composition_id = :composition_id
                    ORDER BY i.position
                    """
                ),
                {"composition_id": composition_id},
            )
            composition["items"] = []
            for item_row in items_result.fetchall():
                item = dict(item_row._mapping)
                item["bbox"] = _json_loads(item.get("bbox"))
                item["style_override"] = _json_loads(item.get("style_override")) or {}
                composition["items"].append(item)
            return composition

    async def delete(self, kb_id: str, composition_id: str) -> bool:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                text(
                    """
                    DELETE FROM knowledge_spatial_layer_compositions
                    WHERE kb_id = :kb_id AND composition_id = :composition_id
                    """
                ),
                {"kb_id": kb_id, "composition_id": composition_id},
            )
            return bool(result.rowcount)

    async def _replace_items(self, session, composition_id: str, items: list[dict[str, Any]]) -> None:
        await session.execute(
            text(
                """
                DELETE FROM knowledge_spatial_layer_composition_items
                WHERE composition_id = :composition_id
                """
            ),
            {"composition_id": composition_id},
        )
        if not items:
            return
        await session.execute(
            text(
                """
                INSERT INTO knowledge_spatial_layer_composition_items
                    (composition_id, layer_id, position, visible, opacity, style_override)
                VALUES
                    (:composition_id, :layer_id, :position, :visible, :opacity,
                     CAST(:style_override AS JSONB))
                """
            ),
            [
                {
                    "composition_id": composition_id,
                    "layer_id": item["layer_id"],
                    "position": position,
                    "visible": bool(item.get("visible", True)),
                    "opacity": float(item.get("opacity", 1)),
                    "style_override": json.dumps(item.get("style_override") or {}, ensure_ascii=False),
                }
                for position, item in enumerate(items)
            ],
        )
