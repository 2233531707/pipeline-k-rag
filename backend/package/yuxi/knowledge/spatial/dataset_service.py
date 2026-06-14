from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from neo4j import GraphDatabase

from yuxi.knowledge.utils.kb_utils import parse_minio_url
from yuxi.repositories.knowledge_spatial_repository import KnowledgeSpatialRepository
from yuxi.storage.minio import get_minio_client
from yuxi.utils import logger

SUPPORTED_GEOMETRY_FAMILIES = {"Point", "LineString", "Polygon"}
SOURCE_TYPE_SHAPEFILE_DATASET = "shapefile_dataset"
SPATIAL_INSERT_BATCH_SIZE = 500
SPATIAL_READ_BATCH_SIZE = 5_000
MAX_SPATIAL_ARCHIVE_FILES = 2_000
MAX_SPATIAL_SINGLE_FILE_BYTES = 512 * 1024 * 1024
MAX_SPATIAL_EXTRACTED_BYTES = 5 * 1024 * 1024 * 1024


@dataclass(slots=True)
class SpatialDatasetImportResult:
    source_id: str
    markdown: str
    summary: dict[str, Any]


class SpatialDatasetService:
    def __init__(self, repository: KnowledgeSpatialRepository | None = None):
        self.repository = repository or KnowledgeSpatialRepository()

    async def import_dataset(
        self,
        *,
        kb_id: str,
        file_id: str,
        source: str,
        source_name: str,
        operator_id: str | None = None,
    ) -> SpatialDatasetImportResult:
        source_id = f"sp_{uuid.uuid4().hex}"
        work_dir: str | None = None

        await self.repository.create_source(
            {
                "source_id": source_id,
                "kb_id": kb_id,
                "file_id": file_id,
                "name": source_name,
                "status": "parsing",
                "original_crs": None,
                "layer_count": 0,
                "feature_count": 0,
                "skipped_feature_count": 0,
                "bbox": None,
                "summary": {},
                "error_message": None,
                "created_by": operator_id,
            }
        )

        try:
            work_dir = tempfile.mkdtemp(prefix="yuxi_spatial_")
            prepared_source = await self._prepare_source_dir(source, work_dir, source_name)
            layers = self._discover_spatial_layers(prepared_source)
            if not layers:
                raise ValueError("空间数据中未找到可导入图层")

            imported_layers: list[dict[str, Any]] = []
            all_feature_texts: list[str] = []
            total_features = 0
            skipped_features = 0
            source_bbox: list[float] | None = None
            original_crs_values: list[str] = []

            for dataset_path, dataset_layer_name in layers:
                layer_id = f"spl_{uuid.uuid4().hex}"
                layer_name = dataset_layer_name or dataset_path.stem
                layer_created = False
                layer_feature_count = 0
                layer_bbox: list[float] | None = None
                layer_geometry_types: set[str] = set()
                layer_info: dict[str, Any] | None = None
                read_offset = 0

                while True:
                    batch_info = await asyncio.to_thread(
                        self._read_layer,
                        dataset_path,
                        dataset_layer_name,
                        rows=slice(read_offset, read_offset + SPATIAL_READ_BATCH_SIZE),
                    )
                    raw_row_count = int(batch_info["row_count"])
                    skipped_features += int(batch_info["skipped_feature_count"])
                    if raw_row_count == 0:
                        break

                    if not layer_created:
                        layer_info = batch_info
                        await self.repository.create_layer(
                            {
                                "layer_id": layer_id,
                                "source_id": source_id,
                                "kb_id": kb_id,
                                "name": layer_name,
                                "geometry_type": "Unknown",
                                "original_srid": batch_info["original_srid"],
                                "field_schema": batch_info["field_schema"],
                                "feature_count": 0,
                                "bbox": None,
                                "created_by": operator_id,
                            }
                        )
                        layer_created = True
                        if batch_info["original_crs"]:
                            original_crs_values.append(batch_info["original_crs"])

                    feature_payloads = []
                    for feature in batch_info["features"]:
                        feature_payloads.append(
                            {
                                "feature_id": f"spf_{uuid.uuid4().hex}",
                                "layer_id": layer_id,
                                "source_id": source_id,
                                "kb_id": kb_id,
                                "source_feature_id": feature["source_feature_id"],
                                "geometry_type": feature["geometry_type"],
                                "properties": feature["properties"],
                                "text_content": feature["text_content"],
                                "bbox": feature["bbox"],
                                "geometry": feature["geometry"],
                            }
                        )
                        if len(all_feature_texts) < 1000:
                            all_feature_texts.append(feature["text_content"])

                    for offset in range(0, len(feature_payloads), SPATIAL_INSERT_BATCH_SIZE):
                        await self.repository.insert_features(
                            feature_payloads[offset : offset + SPATIAL_INSERT_BATCH_SIZE]
                        )

                    layer_feature_count += len(feature_payloads)
                    layer_bbox = self._merge_bbox(layer_bbox, batch_info["bbox"])
                    layer_geometry_types.update(feature["geometry_type"] for feature in batch_info["features"])
                    read_offset += raw_row_count
                    if raw_row_count < SPATIAL_READ_BATCH_SIZE:
                        break

                if not layer_created:
                    continue
                if layer_feature_count == 0:
                    await self.repository.delete_layer(kb_id, layer_id)
                    continue

                geometry_type = ",".join(sorted(layer_geometry_types)) or "Unknown"
                await self.repository.update_layer_summary(
                    kb_id,
                    layer_id,
                    geometry_type=geometry_type,
                    feature_count=layer_feature_count,
                    bbox=layer_bbox,
                )
                layer_summary = {
                    "layer_id": layer_id,
                    "source_id": source_id,
                    "kb_id": kb_id,
                    "name": layer_name,
                    "geometry_type": geometry_type,
                    "original_srid": layer_info["original_srid"],
                    "field_schema": layer_info["field_schema"],
                    "feature_count": layer_feature_count,
                    "bbox": layer_bbox,
                    "created_by": operator_id,
                }
                total_features += layer_feature_count
                source_bbox = self._merge_bbox(source_bbox, layer_bbox)
                imported_layers.append(layer_summary)

            if not imported_layers:
                raise ValueError("空间数据 ZIP 中没有可导入的有效几何要素")

            summary = {
                "source_id": source_id,
                "name": source_name,
                "layer_count": len(imported_layers),
                "feature_count": total_features,
                "skipped_feature_count": skipped_features,
                "bbox": source_bbox,
                "layers": imported_layers,
            }
            original_crs = ", ".join(sorted(set(original_crs_values)))[:128] if original_crs_values else None
            await self.repository.create_source(
                {
                    "source_id": source_id,
                    "kb_id": kb_id,
                    "file_id": file_id,
                    "name": source_name,
                    "status": "parsed",
                    "original_crs": original_crs,
                    "layer_count": len(imported_layers),
                    "feature_count": total_features,
                    "skipped_feature_count": skipped_features,
                    "bbox": source_bbox,
                    "summary": summary,
                    "error_message": None,
                    "created_by": operator_id,
                }
            )
            markdown = self._build_markdown(source_name, summary, all_feature_texts)
            return SpatialDatasetImportResult(source_id=source_id, markdown=markdown, summary=summary)

        except Exception as exc:
            logger.error(f"空间数据集解析失败 file_id={file_id}: {exc}")
            await self.repository.delete_by_file(kb_id, file_id)
            await self.repository.create_source(
                {
                    "source_id": source_id,
                    "kb_id": kb_id,
                    "file_id": file_id,
                    "name": source_name,
                    "status": "error",
                    "original_crs": None,
                    "layer_count": 0,
                    "feature_count": 0,
                    "skipped_feature_count": 0,
                    "bbox": None,
                    "summary": {},
                    "error_message": str(exc),
                    "created_by": operator_id,
                }
            )
            raise
        finally:
            if work_dir and os.path.exists(work_dir):
                shutil.rmtree(work_dir, ignore_errors=True)

    async def index_graph_for_file(self, *, kb_id: str, file_id: str) -> None:
        source = await self.repository.get_source_by_file(kb_id, file_id)
        if not source or source.get("status") != "parsed":
            return
        features = await self.repository.list_features_for_source(kb_id, source["source_id"])
        if not features:
            return
        await asyncio.to_thread(self._write_spatial_graph, kb_id, source["source_id"], features)

    async def delete_by_file(self, *, kb_id: str, file_id: str) -> None:
        source_ids = await self.repository.delete_by_file(kb_id, file_id)
        for source_id in source_ids:
            try:
                await asyncio.to_thread(self._delete_spatial_graph, kb_id, source_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"删除空间图谱失败 kb_id={kb_id} source_id={source_id}: {exc}")

    async def delete_by_db(self, *, kb_id: str) -> None:
        source_ids = await self.repository.delete_by_db(kb_id)
        for source_id in source_ids:
            try:
                await asyncio.to_thread(self._delete_spatial_graph, kb_id, source_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"删除空间图谱失败 kb_id={kb_id} source_id={source_id}: {exc}")

    async def _prepare_source_dir(self, source: str, work_dir: str, source_name: str | None = None) -> Path:
        if source.startswith(("http://", "https://")):
            bucket_name, object_name = parse_minio_url(source)
            suffix = Path(source_name or object_name).suffix.lower()
            if suffix not in {".zip", ".shp", ".geojson", ".json", ".gpkg"}:
                raise ValueError("空间数据源仅支持 .geojson、.json、.zip 和 .gpkg")
            target = Path(work_dir) / f"dataset{suffix}"
            await get_minio_client().adownload_file_to_path(bucket_name, object_name, str(target))
            if suffix == ".zip":
                extract_dir = Path(work_dir) / "extract"
                extract_dir.mkdir(parents=True, exist_ok=True)
                self._safe_extract_zip(str(target), extract_dir)
                return extract_dir
            if suffix == ".shp":
                return target.parent
            return target

        source_path = Path(source)
        if source_path.is_dir():
            return source_path
        if source_path.suffix.lower() == ".zip":
            extract_dir = Path(work_dir) / "extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            self._safe_extract_zip(str(source_path), extract_dir)
            return extract_dir
        if source_path.suffix.lower() == ".shp":
            return source_path.parent
        if source_path.suffix.lower() in {".geojson", ".json", ".gpkg"}:
            return source_path
        raise ValueError("空间数据源仅支持 .geojson、.json、.zip 和 .gpkg")

    def _safe_extract_zip(self, zip_path: str, target_dir: Path) -> None:
        file_count = 0
        total_size = 0
        with zipfile.ZipFile(zip_path) as zf:
            for entry in zf.infolist():
                if entry.is_dir():
                    continue
                normalized = entry.filename.replace("\\", "/")
                parts = PurePosixPath(normalized).parts
                windows_path = PureWindowsPath(entry.filename)
                if normalized.startswith("/") or windows_path.is_absolute() or windows_path.drive or ".." in parts:
                    raise ValueError(f"ZIP 包含不安全路径: {entry.filename}")
                file_count += 1
                total_size += entry.file_size
                if file_count > MAX_SPATIAL_ARCHIVE_FILES:
                    raise ValueError("空间数据 ZIP 文件数量超过限制")
                if entry.file_size > MAX_SPATIAL_SINGLE_FILE_BYTES:
                    raise ValueError(f"空间数据 ZIP 单文件过大: {entry.filename}")
                if total_size > MAX_SPATIAL_EXTRACTED_BYTES:
                    raise ValueError("空间数据 ZIP 解压总大小超过限制")
                target_path = (target_dir / normalized).resolve()
                if not str(target_path).startswith(str(target_dir.resolve()) + os.sep):
                    raise ValueError(f"ZIP 包含不安全路径: {entry.filename}")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(entry) as source_handle, target_path.open("wb") as target_handle:
                    shutil.copyfileobj(source_handle, target_handle)

    def _discover_spatial_layers(self, source: Path) -> list[tuple[Path, str | None]]:
        if source.is_file():
            paths = [source]
        else:
            paths = sorted(
                path
                for path in source.rglob("*")
                if path.is_file() and path.suffix.lower() in {".shp", ".geojson", ".json", ".gpkg"}
            )

        layers: list[tuple[Path, str | None]] = []
        for path in paths:
            suffix = path.suffix.lower()
            if suffix == ".shp":
                self._validate_shapefile_sidecars(path)
                layers.append((path, None))
            elif suffix == ".gpkg":
                try:
                    from pyogrio import list_layers

                    layer_names = [str(item[0]) for item in list_layers(path)]
                except ImportError as exc:
                    raise RuntimeError("GPKG 导入需要 pyogrio") from exc
                layers.extend((path, layer_name) for layer_name in layer_names)
            else:
                layers.append((path, None))
        return layers

    def _validate_shapefile_sidecars(self, shp_path: Path) -> None:
        sibling_names = {path.name.lower() for path in shp_path.parent.iterdir()}
        missing = [ext for ext in (".dbf", ".shx", ".prj") if f"{shp_path.stem}{ext}".lower() not in sibling_names]
        if missing:
            raise ValueError(f"图层 {shp_path.name} 缺少伴随文件: {', '.join(missing)}")

    def _discover_shapefile_layers(self, root: Path) -> list[Path]:
        layers = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".shp")
        for shp_path in layers:
            self._validate_shapefile_sidecars(shp_path)
        return layers

    def _read_layer(
        self,
        shp_path: Path | str,
        layer_name: str | None = None,
        *,
        rows: slice | None = None,
    ) -> dict[str, Any]:
        shp_path = Path(shp_path)
        try:
            import geopandas as gpd
            from shapely.geometry import mapping
        except ImportError as exc:
            raise RuntimeError("缺少 GeoPandas 运行依赖，请安装 geopandas 与 pyogrio 后重试") from exc

        last_error: Exception | None = None
        for encoding in (None, "utf-8", "gbk", "gb18030"):
            try:
                read_kwargs = {"encoding": encoding} if encoding else {}
                if layer_name:
                    read_kwargs["layer"] = layer_name
                if rows is not None:
                    read_kwargs["rows"] = rows
                gdf = gpd.read_file(shp_path, **read_kwargs)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        else:
            raise ValueError(f"读取图层 {shp_path.name} 失败: {last_error}")

        if gdf.crs is None:
            raise ValueError(f"图层 {shp_path.name} 缺少 CRS，请提供 .prj 文件中的坐标系信息")

        original_crs = str(gdf.crs)
        original_srid = gdf.crs.to_epsg()
        raw_row_count = len(gdf)
        geometry_col = gdf.geometry.name
        field_schema = [
            {"name": str(column), "type": str(dtype)}
            for column, dtype in gdf.drop(columns=[geometry_col]).dtypes.items()
        ]

        valid_mask = gdf.geometry.notna() & ~gdf.geometry.is_empty
        skipped = int((~valid_mask).sum())
        gdf = gdf.loc[valid_mask].copy()
        if gdf.empty:
            return {
                "original_crs": original_crs,
                "original_srid": original_srid,
                "field_schema": field_schema,
                "geometry_type": "Unknown",
                "bbox": None,
                "features": [],
                "row_count": raw_row_count,
                "skipped_feature_count": skipped,
            }

        families = {self._geometry_family(value) for value in gdf.geometry.geom_type.dropna().unique()}
        unsupported = families - SUPPORTED_GEOMETRY_FAMILIES
        if unsupported:
            raise ValueError(f"图层 {shp_path.name} 包含暂不支持的几何类型: {', '.join(sorted(unsupported))}")

        gdf = gdf.to_crs(epsg=4326)
        from shapely import make_valid

        gdf.geometry = gdf.geometry.apply(lambda geom: make_valid(geom) if not geom.is_valid else geom)
        repaired_mask = gdf.geometry.notna() & ~gdf.geometry.is_empty
        skipped += int((~repaired_mask).sum())
        gdf = gdf.loc[repaired_mask].copy()
        if gdf.empty:
            return {
                "original_crs": original_crs,
                "original_srid": original_srid,
                "field_schema": field_schema,
                "geometry_type": "Unknown",
                "bbox": None,
                "features": [],
                "row_count": raw_row_count,
                "skipped_feature_count": skipped,
            }
        total_bounds = [float(v) for v in gdf.total_bounds]
        features = []
        attr_columns = [column for column in gdf.columns if column != geometry_col]
        for idx, row in gdf.iterrows():
            geom = row[geometry_col]
            if geom is None or geom.is_empty:
                skipped += 1
                continue
            properties = {str(column): self._to_json_value(row[column]) for column in attr_columns}
            source_feature_id = self._source_feature_id(properties, idx)
            geometry_type = str(geom.geom_type)
            text_content = self._feature_text(layer_name or shp_path.stem, source_feature_id, geometry_type, properties)
            features.append(
                {
                    "source_feature_id": source_feature_id,
                    "geometry_type": geometry_type,
                    "properties": properties,
                    "text_content": text_content,
                    "bbox": [float(v) for v in geom.bounds],
                    "geometry": mapping(geom),
                }
            )

        geometry_type = ",".join(sorted({feature["geometry_type"] for feature in features})) or "Unknown"
        return {
            "original_crs": original_crs,
            "original_srid": original_srid,
            "field_schema": field_schema,
            "geometry_type": geometry_type,
            "bbox": total_bounds,
            "features": features,
            "row_count": raw_row_count,
            "skipped_feature_count": skipped,
        }

    def _feature_text(
        self,
        layer_name: str,
        source_feature_id: str,
        geometry_type: str,
        properties: dict[str, Any],
    ) -> str:
        prop_text = "；".join(f"{key}={value}" for key, value in properties.items() if value not in (None, ""))
        return f"空间图层 {layer_name} 要素 {source_feature_id}，几何类型 {geometry_type}。属性：{prop_text}"

    def _source_feature_id(self, properties: dict[str, Any], fallback: Any) -> str:
        for key in ("EXP_NO", "PIPEID", "ROADID", "OBJECTID", "FID", "ID"):
            value = properties.get(key)
            if value not in (None, ""):
                return str(value)
        return str(fallback)

    def _geometry_family(self, geom_type: str) -> str:
        if geom_type.startswith("Multi"):
            return geom_type[5:]
        return geom_type

    def _to_json_value(self, value: Any) -> Any:
        if value is None:
            return None
        try:
            if value != value:  # NaN
                return None
        except Exception:  # noqa: BLE001
            pass
        if isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, float):
            return None if math.isnan(value) or math.isinf(value) else value
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if hasattr(value, "item"):
            return self._to_json_value(value.item())
        return str(value)

    def _merge_bbox(self, current: list[float] | None, bbox: list[float] | None) -> list[float] | None:
        if not bbox:
            return current
        if not current:
            return list(bbox)
        return [
            min(current[0], bbox[0]),
            min(current[1], bbox[1]),
            max(current[2], bbox[2]),
            max(current[3], bbox[3]),
        ]

    def _build_markdown(self, source_name: str, summary: dict[str, Any], feature_texts: list[str]) -> str:
        lines = [
            f"# 空间数据集：{source_name}",
            "",
            f"- 数据源 ID：{summary['source_id']}",
            f"- 图层数量：{summary['layer_count']}",
            f"- 要素数量：{summary['feature_count']}",
            f"- 跳过空几何：{summary['skipped_feature_count']}",
            f"- 空间范围（WGS84）：{summary.get('bbox')}",
            "",
            "## 图层摘要",
        ]
        for layer in summary["layers"]:
            lines.append(
                f"- {layer['name']}：{layer['geometry_type']}，{layer['feature_count']} 个要素，字段 "
                + "、".join(field["name"] for field in layer.get("field_schema") or [])
            )
        lines.extend(["", "## 要素属性"])
        lines.extend(f"- {text}" for text in feature_texts)
        return "\n".join(lines)

    def _write_spatial_graph(self, kb_id: str, source_id: str, features: list[dict[str, Any]]) -> None:
        if not self._valid_neo4j_label(kb_id):
            raise ValueError(f"Invalid kb_id for Neo4j label: {kb_id}")

        neo4j_uri = os.getenv("NEO4J_URI") or "bolt://localhost:7687"
        neo4j_username = os.getenv("NEO4J_USERNAME") or "neo4j"
        neo4j_password = os.getenv("NEO4J_PASSWORD") or "0123456789"
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        try:
            point_index: dict[str, str] = {}
            line_links: list[tuple[str, str, str]] = []
            with driver.session() as session:
                for feature in features:
                    props = feature.get("properties") or {}
                    entity_id = self._graph_entity_id(source_id, feature["feature_id"])
                    node_props = self._neo4j_props(
                        props
                        | {
                            "entity_id": entity_id,
                            "name": props.get("EXP_NO") or props.get("PIPEID") or feature["source_feature_id"],
                            "feature_id": feature["feature_id"],
                            "source_id": source_id,
                            "kb_id": kb_id,
                            "layer_name": feature["layer_name"],
                            "geometry_type": feature["geometry_type"],
                            "description": feature.get("text_content"),
                        }
                    )
                    session.run(
                        f"""
                        MERGE (n:Entity:Spatial:`{kb_id}` {{entity_id: $entity_id}})
                        SET n += $props
                        """,
                        entity_id=entity_id,
                        props=node_props,
                    )

                    exp_no = self._clean_key(props.get("EXP_NO"))
                    if exp_no and "Point" in str(feature.get("geometry_type")):
                        point_index[exp_no] = entity_id

                    road_name = self._clean_key(props.get("ROADNAME"))
                    if road_name:
                        road_entity_id = self._graph_entity_id(source_id, f"road:{road_name}")
                        session.run(
                            f"""
                            MERGE (road:Entity:Spatial:`{kb_id}` {{entity_id: $road_entity_id}})
                            SET road += $road_props
                            WITH road
                            MATCH (n:Entity:Spatial:`{kb_id}` {{entity_id: $entity_id}})
                            MERGE (n)-[r:LOCATED_ON]->(road)
                            SET r.type = 'LOCATED_ON'
                            """,
                            road_entity_id=road_entity_id,
                            road_props={
                                "entity_id": road_entity_id,
                                "name": road_name,
                                "source_id": source_id,
                                "kb_id": kb_id,
                                "entity_type": "road",
                            },
                            entity_id=entity_id,
                        )

                    start_key = self._clean_key(props.get("S_POINT"))
                    end_key = self._clean_key(props.get("E_POINT"))
                    if start_key:
                        line_links.append((entity_id, "STARTS_AT", start_key))
                    if end_key:
                        line_links.append((entity_id, "ENDS_AT", end_key))

                for line_entity_id, rel_type, point_key in line_links:
                    point_entity_id = point_index.get(point_key)
                    if not point_entity_id:
                        continue
                    session.run(
                        f"""
                        MATCH (line:Entity:Spatial:`{kb_id}` {{entity_id: $line_entity_id}})
                        MATCH (point:Entity:Spatial:`{kb_id}` {{entity_id: $point_entity_id}})
                        MERGE (line)-[r:{rel_type}]->(point)
                        SET r.type = $rel_type
                        """,
                        line_entity_id=line_entity_id,
                        point_entity_id=point_entity_id,
                        rel_type=rel_type,
                    )
        finally:
            driver.close()

    def _delete_spatial_graph(self, kb_id: str, source_id: str) -> None:
        if not self._valid_neo4j_label(kb_id):
            return
        neo4j_uri = os.getenv("NEO4J_URI") or "bolt://localhost:7687"
        neo4j_username = os.getenv("NEO4J_USERNAME") or "neo4j"
        neo4j_password = os.getenv("NEO4J_PASSWORD") or "0123456789"
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        try:
            with driver.session() as session:
                session.run(
                    f"MATCH (n:Spatial:`{kb_id}` {{source_id: $source_id}}) DETACH DELETE n",
                    source_id=source_id,
                )
        finally:
            driver.close()

    def _valid_neo4j_label(self, label: str) -> bool:
        return bool(label) and all(char.isalnum() or char == "_" for char in label)

    def _graph_entity_id(self, source_id: str, suffix: str) -> str:
        return f"spatial:{source_id}:{suffix}"

    def _clean_key(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value).strip() or None

    def _neo4j_props(self, props: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for key, value in props.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                result[str(key)] = value
            elif isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
                result[str(key)] = value
            else:
                result[str(key)] = json.dumps(value, ensure_ascii=False, default=str)
        return result
