# T17 任务报告 — 空间数据上传与图层管理

## 目标

确认空间数据上传与图层管理（Shapefile/GeoJSON/GPKG 导入、CRS 转换、安全防护）已就绪。

## 分支

`main2.0`

## 扫描结果

T17 要求的功能已在项目中完整实现：

### 支持格式

| 格式 | 实现方式 | 状态 |
|---|---|---|
| .zip (Shapefile) | 解压 → 发现 .shp → 校验 .dbf/.shx/.prj | ✅ |
| .geojson | GeoPandas 原生支持 | ✅ |
| .json | 同 .geojson | ✅ |
| .gpkg | GeoPandas 原生支持 | ✅ |

### 导入流程

```
上传 (.zip/.geojson/.gpkg)
  → MinIO 存储
  → 安全解压 (Zip Slip 防护)
  → GeoPandas 读取 → CRS 校验 (无 CRS 拒绝)
  → EPSG:4326 重投影
  → geometry repair (空几何跳过)
  → PostGIS 写入 (3 张表)
  → Neo4j 空间图谱索引
```

### 安全防护 (已有)

| 防护 | 实现 | 测试 |
|---|---|---|
| Zip Slip | Unix `../evil.shp` + Windows `..\\evil.shp` 拒绝 | ✅ test_spatial_dataset_service.py |
| Shapefile 完整性 | 要求 .dbf + .shx + .prj 三文件 | ✅ 8 test_zip 相关用例 |
| 无 CRS 拒绝 | 校验 crs 存在 | ✅ SpatialDatasetService |
| 权限隔离 | API 通过 get_admin_user 验证 | ✅ knowledge_router.py |

### 已有测试 (13 passed)

```bash
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/knowledge/test_spatial_dataset_service.py test/unit/routers/test_knowledge_spatial_router.py -q"
# 13 passed ✅
```

### 已有前端

| 组件 | 功能 | 状态 |
|---|---|---|
| FileUploadModal.vue | mode='spatial', 提示 .zip(含.shp/.dbf/.shx/.prj) | ✅ |
| SpatialDataSection.vue | 图层选择、SVG 预览、要素详情 | ✅ |
| spatialApi (knowledge_api.js) | 3 个 API 封装 | ✅ |

## 修改文件

无

## 测试命令

```bash
docker exec yuxi-sync-api sh -c "cd /app && uv run --no-sync --no-dev pytest test/unit/knowledge/test_spatial_dataset_service.py test/unit/routers/test_knowledge_spatial_router.py -q"
```

## 测试结果

13 passed ✅（复用已有测试）

## 风险

- GPKG 格式未针对性测试（仅有 Shapefile 测试覆盖）

## 已知限制

- 当前仅支持 Point/LineString/Polygon 及其 Multi- 变体
- 大图层 (>50,000 要素) 前端 SVG 渲染性能有限

## 提交

报告已记录状态。

## 远端

- `main2.0`
