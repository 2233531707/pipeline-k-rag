from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from yuxi.storage.postgres.manager import pg_manager


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    return json.loads(value)


class KnowledgeSpatialRepository:
    async def create_source(self, data: dict[str, Any]) -> None:
        sql = text(
            """
            INSERT INTO knowledge_spatial_sources (
                source_id, kb_id, file_id, name, status, original_crs,
                layer_count, feature_count, skipped_feature_count, bbox,
                summary, error_message, created_by
            ) VALUES (
                :source_id, :kb_id, :file_id, :name, :status, :original_crs,
                :layer_count, :feature_count, :skipped_feature_count, CAST(:bbox AS JSONB),
                CAST(:summary AS JSONB), :error_message, :created_by
            )
            ON CONFLICT (source_id) DO UPDATE SET
                status = EXCLUDED.status,
                original_crs = EXCLUDED.original_crs,
                layer_count = EXCLUDED.layer_count,
                feature_count = EXCLUDED.feature_count,
                skipped_feature_count = EXCLUDED.skipped_feature_count,
                bbox = EXCLUDED.bbox,
                summary = EXCLUDED.summary,
                error_message = EXCLUDED.error_message,
                updated_at = NOW()
            """
        )
        payload = {
            **data,
            "bbox": _json_dumps(data.get("bbox")),
            "summary": _json_dumps(data.get("summary") or {}),
        }
        async with pg_manager.get_async_session_context() as session:
            await session.execute(sql, payload)

    async def update_source_status(
        self,
        source_id: str,
        *,
        status: str,
        error_message: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        sql = text(
            """
            UPDATE knowledge_spatial_sources
            SET status = :status,
                error_message = :error_message,
                summary = COALESCE(CAST(:summary AS JSONB), summary),
                updated_at = NOW()
            WHERE source_id = :source_id
            """
        )
        async with pg_manager.get_async_session_context() as session:
            await session.execute(
                sql,
                {
                    "source_id": source_id,
                    "status": status,
                    "error_message": error_message,
                    "summary": _json_dumps(summary) if summary is not None else None,
                },
            )

    async def create_layer(self, data: dict[str, Any]) -> None:
        sql = text(
            """
            INSERT INTO knowledge_spatial_layers (
                layer_id, source_id, kb_id, name, geometry_type,
                original_srid, field_schema, feature_count, bbox, created_by
            ) VALUES (
                :layer_id, :source_id, :kb_id, :name, :geometry_type,
                :original_srid, CAST(:field_schema AS JSONB), :feature_count, CAST(:bbox AS JSONB), :created_by
            )
            """
        )
        payload = {
            **data,
            "created_by": data.get("created_by"),
            "field_schema": _json_dumps(data.get("field_schema") or []),
            "bbox": _json_dumps(data.get("bbox")),
        }
        async with pg_manager.get_async_session_context() as session:
            await session.execute(sql, payload)

    async def update_layer_summary(
        self,
        kb_id: str,
        layer_id: str,
        *,
        geometry_type: str,
        feature_count: int,
        bbox: list[float] | None,
    ) -> None:
        sql = text(
            """
            UPDATE knowledge_spatial_layers
            SET geometry_type = :geometry_type,
                feature_count = :feature_count,
                bbox = CAST(:bbox AS JSONB)
            WHERE kb_id = :kb_id AND layer_id = :layer_id
            """
        )
        async with pg_manager.get_async_session_context() as session:
            await session.execute(
                sql,
                {
                    "kb_id": kb_id,
                    "layer_id": layer_id,
                    "geometry_type": geometry_type,
                    "feature_count": feature_count,
                    "bbox": _json_dumps(bbox),
                },
            )

    async def insert_features(self, features: list[dict[str, Any]]) -> None:
        if not features:
            return
        sql = text(
            """
            INSERT INTO knowledge_spatial_features (
                feature_id, layer_id, source_id, kb_id, source_feature_id,
                geometry_type, properties, text_content, bbox, geom
            ) VALUES (
                :feature_id, :layer_id, :source_id, :kb_id, :source_feature_id,
                :geometry_type, CAST(:properties AS JSONB), :text_content, CAST(:bbox AS JSONB),
                ST_SetSRID(ST_GeomFromGeoJSON(:geometry_geojson), 4326)
            )
            """
        )
        payloads = [
            {
                **feature,
                "properties": _json_dumps(feature.get("properties") or {}),
                "bbox": _json_dumps(feature.get("bbox")),
                "geometry_geojson": _json_dumps(feature.get("geometry")),
            }
            for feature in features
        ]
        async with pg_manager.get_async_session_context() as session:
            await session.execute(sql, payloads)

    async def list_sources(self, kb_id: str) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT s.*, COALESCE(
                json_agg(
                    json_build_object(
                        'layer_id', l.layer_id,
                        'name', l.name,
                        'geometry_type', l.geometry_type,
                        'original_srid', l.original_srid,
                        'field_schema', l.field_schema,
                        'feature_count', l.feature_count,
                        'bbox', l.bbox
                    ) ORDER BY l.name
                ) FILTER (WHERE l.layer_id IS NOT NULL), '[]'
            ) AS layers
            FROM knowledge_spatial_sources s
            LEFT JOIN knowledge_spatial_layers l ON l.source_id = s.source_id
            WHERE s.kb_id = :kb_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
            """
        )
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql, {"kb_id": kb_id})
            return [self._source_row_to_dict(row._mapping) for row in result.fetchall()]

    async def get_source_by_file(self, kb_id: str, file_id: str) -> dict[str, Any] | None:
        sql = text(
            """
            SELECT * FROM knowledge_spatial_sources
            WHERE kb_id = :kb_id AND file_id = :file_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql, {"kb_id": kb_id, "file_id": file_id})
            row = result.fetchone()
            return self._source_row_to_dict(row._mapping) if row else None

    async def list_layers(self, kb_id: str) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT l.*, s.name AS source_name
            FROM knowledge_spatial_layers l
            LEFT JOIN knowledge_spatial_sources s ON s.source_id = l.source_id
            WHERE l.kb_id = :kb_id
            ORDER BY l.created_at DESC, l.id DESC
            """
        )
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql, {"kb_id": kb_id})
            return [self._layer_row_to_dict(row._mapping) for row in result.fetchall()]

    async def get_layer(self, kb_id: str, layer_id: str) -> dict[str, Any] | None:
        sql = text("SELECT * FROM knowledge_spatial_layers WHERE kb_id = :kb_id AND layer_id = :layer_id")
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql, {"kb_id": kb_id, "layer_id": layer_id})
            row = result.fetchone()
            return self._layer_row_to_dict(row._mapping) if row else None

    async def delete_layer(self, kb_id: str, layer_id: str) -> bool:
        async with pg_manager.get_async_session_context() as session:
            source_id = (
                await session.execute(
                    text(
                        "SELECT source_id FROM knowledge_spatial_layers WHERE kb_id = :kb_id AND layer_id = :layer_id"
                    ),
                    {"kb_id": kb_id, "layer_id": layer_id},
                )
            ).scalar_one_or_none()
            result = await session.execute(
                text("DELETE FROM knowledge_spatial_layers WHERE kb_id = :kb_id AND layer_id = :layer_id"),
                {"kb_id": kb_id, "layer_id": layer_id},
            )
            if result.rowcount and source_id:
                await session.execute(
                    text(
                        """
                        UPDATE knowledge_spatial_sources
                        SET layer_count = (SELECT count(*) FROM knowledge_spatial_layers WHERE source_id = :source_id),
                            feature_count = (
                                SELECT count(*) FROM knowledge_spatial_features
                                WHERE source_id = :source_id
                            ),
                            updated_at = NOW()
                        WHERE source_id = :source_id
                        """
                    ),
                    {"source_id": source_id},
                )
            return bool(result.rowcount)

    async def list_layer_features(
        self,
        kb_id: str,
        layer_id: str,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> dict[str, Any]:
        where = "kb_id = :kb_id AND layer_id = :layer_id"
        params: dict[str, Any] = {"kb_id": kb_id, "layer_id": layer_id, "limit": limit, "offset": offset}
        if bbox:
            where += " AND geom && ST_MakeEnvelope(:west, :south, :east, :north, 4326)"
            params.update({"west": bbox[0], "south": bbox[1], "east": bbox[2], "north": bbox[3]})

        count_sql = text(f"SELECT count(*) FROM knowledge_spatial_features WHERE {where}")
        features_sql = text(
            f"""
            SELECT feature_id, source_feature_id, geometry_type, properties, bbox,
                   ST_AsGeoJSON(geom)::json AS geometry
            FROM knowledge_spatial_features
            WHERE {where}
            ORDER BY id
            LIMIT :limit OFFSET :offset
            """
        )
        async with pg_manager.get_async_session_context() as session:
            total = (await session.execute(count_sql, params)).scalar_one()
            result = await session.execute(features_sql, params)
            features = [self._feature_row_to_geojson(row._mapping) for row in result.fetchall()]
        return {
            "type": "FeatureCollection",
            "features": features,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_feature(self, kb_id: str, feature_id: str) -> dict[str, Any] | None:
        sql = text(
            """
            SELECT feature_id, layer_id, source_id, source_feature_id, geometry_type,
                   properties, text_content, bbox, ST_AsGeoJSON(geom)::json AS geometry
            FROM knowledge_spatial_features
            WHERE kb_id = :kb_id AND feature_id = :feature_id
            """
        )
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql, {"kb_id": kb_id, "feature_id": feature_id})
            row = result.fetchone()
            if not row:
                return None
            data = dict(row._mapping)
            data["properties"] = _json_loads(data.get("properties")) or {}
            data["bbox"] = _json_loads(data.get("bbox"))
            data["geometry"] = _json_loads(data.get("geometry"))
            return data

    async def list_features_for_source(self, kb_id: str, source_id: str) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT f.feature_id, f.layer_id, f.source_id, f.source_feature_id,
                   f.geometry_type, f.properties, f.text_content, l.name AS layer_name
            FROM knowledge_spatial_features f
            JOIN knowledge_spatial_layers l ON l.layer_id = f.layer_id
            WHERE f.kb_id = :kb_id AND f.source_id = :source_id
            ORDER BY l.name, f.id
            """
        )
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql, {"kb_id": kb_id, "source_id": source_id})
            items = []
            for row in result.fetchall():
                data = dict(row._mapping)
                data["properties"] = _json_loads(data.get("properties")) or {}
                items.append(data)
            return items

    async def delete_by_file(self, kb_id: str, file_id: str) -> list[str]:
        sources = await self._source_ids_for_file(kb_id, file_id)
        if not sources:
            return []
        sql = text("DELETE FROM knowledge_spatial_sources WHERE kb_id = :kb_id AND file_id = :file_id")
        async with pg_manager.get_async_session_context() as session:
            await session.execute(sql, {"kb_id": kb_id, "file_id": file_id})
        return sources

    async def delete_by_db(self, kb_id: str) -> list[str]:
        sql_ids = text("SELECT source_id FROM knowledge_spatial_sources WHERE kb_id = :kb_id")
        sql_delete = text("DELETE FROM knowledge_spatial_sources WHERE kb_id = :kb_id")
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql_ids, {"kb_id": kb_id})
            source_ids = [row[0] for row in result.fetchall()]
            await session.execute(sql_delete, {"kb_id": kb_id})
        return source_ids

    async def _source_ids_for_file(self, kb_id: str, file_id: str) -> list[str]:
        sql = text("SELECT source_id FROM knowledge_spatial_sources WHERE kb_id = :kb_id AND file_id = :file_id")
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(sql, {"kb_id": kb_id, "file_id": file_id})
            return [row[0] for row in result.fetchall()]

    def _source_row_to_dict(self, row: Any) -> dict[str, Any]:
        data = dict(row)
        for key in ("bbox", "summary", "layers"):
            data[key] = _json_loads(data.get(key))
        return data

    def _layer_row_to_dict(self, row: Any) -> dict[str, Any]:
        data = dict(row)
        data["field_schema"] = _json_loads(data.get("field_schema")) or []
        data["bbox"] = _json_loads(data.get("bbox"))
        return data

    def _feature_row_to_geojson(self, row: Any) -> dict[str, Any]:
        data = dict(row)
        properties = _json_loads(data.get("properties")) or {}
        properties.update(
            {
                "feature_id": data.get("feature_id"),
                "source_feature_id": data.get("source_feature_id"),
                "geometry_type": data.get("geometry_type"),
                "bbox": _json_loads(data.get("bbox")),
            }
        )
        return {
            "type": "Feature",
            "id": data.get("feature_id"),
            "geometry": _json_loads(data.get("geometry")),
            "properties": properties,
        }
