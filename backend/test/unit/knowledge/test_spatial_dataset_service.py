import os
import sys
import types
import zipfile
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "dummy-test-key")

from yuxi.knowledge.spatial import SpatialDatasetService


def test_safe_extract_zip_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("../evil.shp", "bad")

    service = SpatialDatasetService()

    with pytest.raises(ValueError, match="不安全路径"):
        service._safe_extract_zip(str(archive_path), tmp_path / "extract")


def test_discover_shapefile_layers_requires_sidecars(tmp_path: Path) -> None:
    shp_path = tmp_path / "points.shp"
    shp_path.write_bytes(b"")

    service = SpatialDatasetService()

    with pytest.raises(ValueError, match="缺少伴随文件"):
        service._discover_shapefile_layers(tmp_path)


def test_safe_extract_zip_rejects_backslash_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "bad-windows.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("..\\evil.shp", "bad")

    service = SpatialDatasetService()

    with pytest.raises(ValueError, match="不安全路径"):
        service._safe_extract_zip(str(archive_path), tmp_path / "extract")


def test_safe_extract_zip_rejects_windows_drive_path(tmp_path: Path) -> None:
    archive_path = tmp_path / "bad-drive.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("C:\\temp\\evil.shp", "bad")

    service = SpatialDatasetService()

    with pytest.raises(ValueError, match="不安全路径"):
        service._safe_extract_zip(str(archive_path), tmp_path / "extract")


def test_discover_shapefile_layers_accepts_uppercase_sidecars(tmp_path: Path) -> None:
    shp_path = tmp_path / "points.SHP"
    shp_path.write_bytes(b"")
    for suffix in (".DBF", ".SHX", ".PRJ"):
        shp_path.with_suffix(suffix).write_bytes(b"")

    service = SpatialDatasetService()

    assert service._discover_shapefile_layers(tmp_path) == [shp_path]


@pytest.mark.asyncio
async def test_prepare_source_dir_accepts_local_shp_parent(tmp_path: Path) -> None:
    shp_path = tmp_path / "points.shp"
    shp_path.write_bytes(b"")

    service = SpatialDatasetService()

    source_dir = await service._prepare_source_dir(str(shp_path), str(tmp_path / "work"))

    assert source_dir == tmp_path


def test_build_markdown_contains_layer_summary() -> None:
    service = SpatialDatasetService()
    markdown = service._build_markdown(
        "pipe.zip",
        {
            "source_id": "sp_1",
            "layer_count": 1,
            "feature_count": 2,
            "skipped_feature_count": 0,
            "bbox": [1, 2, 3, 4],
            "layers": [
                {
                    "name": "jspoint",
                    "geometry_type": "Point",
                    "feature_count": 2,
                    "field_schema": [{"name": "EXP_NO"}],
                }
            ],
        },
        ["空间图层 jspoint 要素 P1，几何类型 Point。属性：EXP_NO=P1"],
    )

    assert "# 空间数据集：pipe.zip" in markdown
    assert "jspoint" in markdown
    assert "EXP_NO=P1" in markdown


def test_read_layer_accepts_string_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = SpatialDatasetService()
    shp_path = tmp_path / "points.shp"

    fake_geopandas = types.ModuleType("geopandas")
    fake_shapely = types.ModuleType("shapely")
    fake_shapely_geometry = types.ModuleType("shapely.geometry")

    def fake_read_file(path: Path, **kwargs):  # noqa: ARG001
        assert path == shp_path
        raise RuntimeError("stop")

    fake_geopandas.read_file = fake_read_file
    fake_shapely_geometry.mapping = lambda geom: geom
    monkeypatch.setitem(sys.modules, "geopandas", fake_geopandas)
    monkeypatch.setitem(sys.modules, "shapely", fake_shapely)
    monkeypatch.setitem(sys.modules, "shapely.geometry", fake_shapely_geometry)

    with pytest.raises(ValueError, match="读取图层 points.shp 失败"):
        service._read_layer(str(shp_path))
