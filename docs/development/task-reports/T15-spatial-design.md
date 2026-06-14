# T15 任务报告 — 空间数据模块扫描与设计

## 目标

扫描现有空间数据模块能力，确认架构，输出设计报告。

## 分支

`main2.0`

## 扫描结果

### 已有架构确认

空间数据模块已存在完整实现，架构如下：

```
PostGIS (postgis/postgis:16-3.5)
  ├── knowledge_spatial_sources    # 空间数据源
  ├── knowledge_spatial_layers     # 空间图层
  └── knowledge_spatial_features   # 空间要素 (geometry(Geometry,4326))
+ MinIO (文件存储)
+ GeoPandas (读写 Shapefile/GeoJSON)
+ Shapely (几何运算)
+ PyProj (CRS 转换 EPSG:4326)
+ Neo4j (空间图谱索引)
```

### 已有组件清单

| 层级 | 文件 | 功能 |
|---|---|---|
| 数据库 | `storage/postgres/manager.py` | 3 张空间表 DDL + GiST 索引 |
| 仓库 | `repositories/knowledge_spatial_repository.py` | 309 行，SQLAlchemy Core CRUD + 空间查询 |
| 服务 | `knowledge/spatial/dataset_service.py` | 539 行，导入/导出/图谱索引 |
| 路由 | `server/routers/knowledge_router.py` | 3 个空间 API 端点 |
| 前端 | `components/SpatialDataSection.vue` | 522 行，SVG 地图预览 + 图层选择 |
| 前端 | `apis/knowledge_api.js` (spatialApi) | 3 个 API 调用封装 |
| 测试 | `test/unit/knowledge/test_spatial_dataset_service.py` | 8 个测试 |
| 测试 | `test/unit/routers/test_knowledge_spatial_router.py` | 2 个测试 |

### 已有 API 端点

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/knowledge/databases/{kb_id}/spatial/sources` | 列出空间数据源 |
| GET | `/api/knowledge/databases/{kb_id}/spatial/layers/{layer_id}/features?bbox=` | GeoJSON FeatureCollection |
| GET | `/api/knowledge/databases/{kb_id}/spatial/features/{feature_id}` | 单个 GeoJSON Feature |

### 导入流程

```
上传 .zip (含 .shp/.dbf/.shx/.prj)
  → MinIO 存储
  → 安全解压 (Zip Slip 防护)
  → GeoPandas 读取 → CRS 校验 → EPSG:4326 重投影
  → geometry repair (空几何跳过)
  → 写入 PostGIS (3 张表)
  → Neo4j 空间图谱索引 (:Entity:Spatial + 关系)
  → 生成 Markdown 摘要 → Milvus 嵌入
```

### 前端可视化

- SVG 内联渲染 (Point/LineString/Polygon)
- 简易线性投影 (lng/lat → viewport)
- 图层选择器 + 要素详情面板
- 无 MapLibre/Leaflet 瓦片底图

### 与指南要求的差距

| T16-T20 要求 | 现状 | 差距 |
|---|---|---|
| T16: PostGIS 空间图层基础模型 | ✅ 已有 3 张表 | 无需新建 |
| T17: 空间数据上传与图层管理 | ✅ 已实现 | 无需新建 |
| T18: 图层叠加与派生分析 | ❌ 未实现 | intersection/union/difference 待添加 |
| T19: 空间智能体工具 | ❌ 未实现 | list_spatial_layers/query_spatial_features/show_spatial_map 待添加 |
| T20: 会话内地图可视化 | ❌ 未实现 | MapLibre GL JS 瓦片地图待替换 SVG |

## 设计决策

### T18: 图层叠加

- `spatial_layer_compositions` 表：组合名、owner、样式
- `spatial_layer_composition_items` 表：order、visible、opacity、style_override
- 派生分析（intersection/union/difference）结果写入新图层，不修改源图层

### T19: 空间智能体工具

- `list_spatial_layers`: 列出 kb 的空间图层
- `query_spatial_features`: 按 bbox/layer_id 查询要素，返回摘要（不返回大体积 GeoJSON）
- `show_spatial_map`: 返回 URL+bounds+图层+样式，不返回 FeatureCollection

### T20: MapLibre GL JS 地图

- 替换当前 SVG 预览为 MapLibre GL JS 瓦片底图
- 多图层叠加、显隐、顺序、透明度控制
- 缩放、平移、自动 bounds、点击 Popup

## 确认架构

```
PostgreSQL + PostGIS    ✅ 已就绪
MinIO                   ✅ 已就绪
GeoPandas + Shapely     ✅ 已就绪
PyProj (EPSG:4326)      ✅ 已就绪
MapLibre GL JS          ❌ 待 T20 引入
```

## 修改文件

无（仅设计文档）

## 新增文件

| 文件 | 说明 |
|---|---|
| `docs/development/task-reports/T15-spatial-design.md` | 本报告 |

## 测试命令

```bash
git diff --check
```

## 测试结果

✅ 通过（无代码修改）

## 风险

- T16/T17 的内容实际上已完成，按指南流程执行时需注意不重复创建已有表
- MapLibre GL JS 需要额外的 npm 依赖和瓦片服务

## 已知限制

- 当前 SVG 地图无底图瓦片，地理参考性弱
- 图层叠加和派生分析未实现
- 空间智能体工具未注册为 Agent 工具

## 提交

本报告待提交。

## 远端

- 分支：`main2.0`
