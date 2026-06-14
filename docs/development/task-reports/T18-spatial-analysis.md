# T18 任务报告 — 图层叠加与派生空间分析

## 目标

实现空间图层的叠加组合与派生分析（intersection/union/difference），结果写入新图层不覆盖源数据。

## 分支

`main2.0`

## 修改文件

无

## 新增文件

| 文件 | 说明 |
|---|---|
| `backend/package/yuxi/knowledge/spatial/analysis_service.py` | 空间分析服务：intersection/union/difference，PostGIS ST 函数，结果写新图层 |
| `docs/development/task-reports/T18-spatial-analysis.md` | 本报告 |

## 实现要点

### 空间分析操作

```python
run_spatial_analysis(kb_id, layer_a_id, layer_b_id, operation, target_name, created_by)
  → 校验 operation in {intersection, union, difference}
  → ST_Intersection / ST_Union / ST_Difference (PostGIS)
  → 结果写入新 knowledge_spatial_features (新 layer_id)
  → 写入 knowledge_spatial_layers 元信息
  → 返回 { layer_id, feature_count, geometry_type, bbox }
```

### 设计决策

| 规则 | 实现 |
|---|---|
| 结果写入新图层 | 生成新 `layer_id`，不修改源图层 |
| 仅处理相交要素 | `ST_Intersects(a.geom, b.geom)` 预过滤 |
| 跳过空结果 | `ST_IsEmpty` 检查 |
| source_id 为空 | 派生图层无原始 source |
| 属性合并 | `a.properties \|\| b.properties` |
| 不覆盖源数据 | 源表不变 |

## 测试命令

```bash
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/knowledge/test_spatial_dataset_service.py test/unit/routers/test_knowledge_spatial_router.py -q"
```

## 测试结果

13 passed ✅（已有空间测试无误）

> T25 已在 PostGIS 16-3.5 环境完成点、线图层入库、要素查询和图层组合验证，详见 [T25 Docker 全量回归](T25-docker-regression.md)。

## 风险

- `MODE()` 聚合函数仅在 PostgreSQL 16+ / PostGIS 支持，低版本可能报错
- 大图层间 ST_Intersection 可能性能较差（建议限制要素数量）

## 已知限制

- 新增的分析服务未集成到 API 路由和前端，当前仅在 service 层可用
- `ST_Difference` 对于一对多要素可能产生多部分几何

## 提交

- 代码 commit：待提交
- 报告 commit：待提交

## 远端

- `main2.0`
