from __future__ import annotations

import inspect
import json
from types import SimpleNamespace

import pytest

from yuxi.agents.toolkits.kbs import spatial_tools, tools


def _tool_callable(tool):
    callback = getattr(tool, "coroutine", None) or getattr(tool, "func", None)
    if callback is None:
        raise AssertionError(f"{tool.name} tool has no callable entry")
    return callback


async def _run_tool(tool, **kwargs):
    result = _tool_callable(tool)(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _runtime(visible_kbs=None):
    return SimpleNamespace(
        context=SimpleNamespace(
            _visible_knowledge_bases=visible_kbs
            if visible_kbs is not None
            else [{"kb_id": "kb-1", "kb_type": "milvus"}]
        )
    )


def test_common_kb_tools_registers_spatial_tools() -> None:
    names = {item.name for item in tools.get_common_kb_tools()}

    assert {
        "list_spatial_layers",
        "query_spatial_features",
        "show_spatial_map",
    }.issubset(names)


@pytest.mark.asyncio
async def test_list_spatial_layers_rejects_hidden_kb(monkeypatch) -> None:
    async def fail_repo():
        raise AssertionError("repository must not be accessed")

    monkeypatch.setattr(spatial_tools, "_get_spatial_repo", fail_repo)

    result = await _run_tool(
        spatial_tools.list_spatial_layers,
        kb_id="kb-hidden",
        runtime=_runtime([]),
    )

    assert "error" in result
    assert "可访问" in result["error"]


@pytest.mark.asyncio
async def test_list_spatial_layers_includes_derived_layers(monkeypatch) -> None:
    repo = SimpleNamespace(
        list_layers=lambda kb_id: None,
    )

    async def list_layers(kb_id):
        assert kb_id == "kb-1"
        return [
            {
                "layer_id": "spl-derived",
                "name": "交集结果",
                "source_name": None,
                "geometry_type": "Polygon",
                "feature_count": 3,
                "bbox": [1, 2, 3, 4],
            }
        ]

    repo.list_layers = list_layers

    async def get_repo():
        return repo

    monkeypatch.setattr(spatial_tools, "_get_spatial_repo", get_repo)

    result = await _run_tool(
        spatial_tools.list_spatial_layers,
        kb_id="kb-1",
        runtime=_runtime(),
    )

    assert result["layer_count"] == 1
    assert result["layers"][0]["layer_id"] == "spl-derived"


@pytest.mark.asyncio
async def test_query_spatial_features_parses_bbox_and_omits_geometry(monkeypatch) -> None:
    captured = {}

    async def get_layer(kb_id, layer_id):
        assert (kb_id, layer_id) == ("kb-1", "spl-1")
        return {"layer_id": layer_id, "name": "管线"}

    async def list_layer_features(kb_id, layer_id, **kwargs):
        captured.update(kwargs)
        return {
            "total": 1,
            "features": [
                {
                    "id": "feature-1",
                    "properties": {"name": "A" * 140},
                    "geometry": {"type": "LineString", "coordinates": [[1, 2], [3, 4]]},
                }
            ],
        }

    async def get_repo():
        return SimpleNamespace(
            get_layer=get_layer,
            list_layer_features=list_layer_features,
        )

    monkeypatch.setattr(spatial_tools, "_get_spatial_repo", get_repo)

    result = await _run_tool(
        spatial_tools.query_spatial_features,
        kb_id="kb-1",
        layer_id="spl-1",
        bbox="1,2,3,4",
        limit=20,
        runtime=_runtime(),
    )

    assert captured["bbox"] == (1.0, 2.0, 3.0, 4.0)
    assert result["features"][0]["geometry_type"] == "LineString"
    assert "coordinates" not in json.dumps(result, ensure_ascii=False)
    assert len(result["features"][0]["properties"]["name"]) <= 123


@pytest.mark.asyncio
async def test_show_spatial_map_uses_composition_order_and_style(monkeypatch) -> None:
    async def list_layers(kb_id):
        assert kb_id == "kb-1"
        return [
            {
                "layer_id": "spl-a",
                "name": "A",
                "geometry_type": "Polygon",
                "feature_count": 2,
                "bbox": [0, 0, 2, 2],
                "field_schema": [{"name": "name"}],
            },
            {
                "layer_id": "spl-b",
                "name": "B",
                "geometry_type": "Point",
                "feature_count": 1,
                "bbox": [10, 10, 11, 11],
                "field_schema": [],
            },
        ]

    async def get_composition(kb_id, composition_id):
        assert (kb_id, composition_id) == ("kb-1", "spc-1")
        return {
            "name": "叠加方案",
            "items": [
                {
                    "layer_id": "spl-b",
                    "visible": False,
                    "opacity": 0.4,
                    "style_override": {"color": "#ff0000"},
                },
                {
                    "layer_id": "spl-a",
                    "visible": True,
                    "opacity": 0.7,
                    "style_override": {},
                },
            ],
        }

    async def get_repo():
        return SimpleNamespace(list_layers=list_layers)

    async def get_composition_repo():
        return SimpleNamespace(get=get_composition)

    monkeypatch.setattr(spatial_tools, "_get_spatial_repo", get_repo)
    monkeypatch.setattr(spatial_tools, "_get_composition_repo", get_composition_repo)

    result = await _run_tool(
        spatial_tools.show_spatial_map,
        kb_id="kb-1",
        layer_ids=[],
        composition_id="spc-1",
        title="空间数据地图",
        runtime=_runtime(),
    )

    assert result["title"] == "叠加方案"
    assert [item["layer_id"] for item in result["layers"]] == ["spl-b", "spl-a"]
    assert result["layers"][0]["visible"] is False
    assert result["layers"][0]["style"] == {"color": "#ff0000"}
    assert result["layers"][1]["url"].endswith("/spl-a/features")
    assert result["bounds"] == [0, 0, 2, 2]
