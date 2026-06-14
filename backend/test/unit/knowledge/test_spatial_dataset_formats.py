from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from yuxi.knowledge.spatial.dataset_service import (
    SPATIAL_READ_BATCH_SIZE,
    SpatialDatasetService,
)


def test_discover_spatial_layers_accepts_geojson(tmp_path: Path) -> None:
    geojson_path = tmp_path / "sample.geojson"
    geojson_path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

    layers = SpatialDatasetService()._discover_spatial_layers(geojson_path)

    assert layers == [(geojson_path, None)]


def test_discover_spatial_layers_lists_gpkg_layers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gpkg_path = tmp_path / "sample.gpkg"
    gpkg_path.write_bytes(b"gpkg")
    fake_pyogrio = types.ModuleType("pyogrio")
    fake_pyogrio.list_layers = lambda path: [("pipes", "LineString"), ("nodes", "Point")]
    monkeypatch.setitem(sys.modules, "pyogrio", fake_pyogrio)

    layers = SpatialDatasetService()._discover_spatial_layers(gpkg_path)

    assert layers == [(gpkg_path, "pipes"), (gpkg_path, "nodes")]


def test_read_layer_passes_row_slice_to_geopandas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "sample.geojson"
    requested_rows = []
    fake_geopandas = types.ModuleType("geopandas")
    fake_shapely_geometry = types.ModuleType("shapely.geometry")

    def fake_read_file(path, **kwargs):
        assert Path(path) == source_path
        requested_rows.append(kwargs.get("rows"))
        raise RuntimeError("stop")

    fake_geopandas.read_file = fake_read_file
    fake_shapely_geometry.mapping = lambda geom: geom
    monkeypatch.setitem(sys.modules, "geopandas", fake_geopandas)
    monkeypatch.setitem(sys.modules, "shapely.geometry", fake_shapely_geometry)

    rows = slice(5, 10)
    with pytest.raises(ValueError, match="读取图层 sample.geojson 失败"):
        SpatialDatasetService()._read_layer(source_path, rows=rows)

    assert requested_rows == [rows, rows, rows, rows]


@pytest.mark.asyncio
async def test_import_dataset_reads_and_writes_in_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRepository:
        def __init__(self):
            self.inserted = []
            self.layer_updates = []

        async def create_source(self, data):
            self.source = data

        async def create_layer(self, data):
            self.layer = data

        async def insert_features(self, features):
            self.inserted.extend(features)

        async def update_layer_summary(self, kb_id, layer_id, **kwargs):
            self.layer_updates.append((kb_id, layer_id, kwargs))

        async def delete_layer(self, kb_id, layer_id):
            raise AssertionError((kb_id, layer_id))

        async def delete_by_file(self, kb_id, file_id):
            return []

    repository = FakeRepository()
    service = SpatialDatasetService(repository=repository)

    async def prepare_source(*args, **kwargs):
        return Path("/tmp/sample.geojson")

    monkeypatch.setattr(service, "_prepare_source_dir", prepare_source)
    monkeypatch.setattr(
        service,
        "_discover_spatial_layers",
        lambda path: [(path, None)],
    )

    requested_starts = []

    def read_layer(path, layer_name, *, rows):
        del path, layer_name
        requested_starts.append(rows.start)
        source_id = f"feature-{rows.start}"
        return {
            "original_crs": "EPSG:4326",
            "original_srid": 4326,
            "field_schema": [{"name": "name", "type": "object"}],
            "geometry_type": "Point",
            "bbox": [rows.start, 0, rows.start + 1, 1],
            "features": [
                {
                    "source_feature_id": source_id,
                    "geometry_type": "Point",
                    "properties": {"name": source_id},
                    "text_content": source_id,
                    "bbox": [rows.start, 0, rows.start + 1, 1],
                    "geometry": {"type": "Point", "coordinates": [rows.start, 0]},
                }
            ],
            "row_count": SPATIAL_READ_BATCH_SIZE if rows.start == 0 else 1,
            "skipped_feature_count": 0,
        }

    monkeypatch.setattr(service, "_read_layer", read_layer)

    result = await service.import_dataset(
        kb_id="kb-1",
        file_id="file-1",
        source="ignored",
        source_name="sample.geojson",
        operator_id="user-1",
    )

    assert requested_starts == [0, SPATIAL_READ_BATCH_SIZE]
    assert result.summary["feature_count"] == 2
    assert len(repository.inserted) == 2
    assert repository.layer_updates[0][2]["feature_count"] == 2
