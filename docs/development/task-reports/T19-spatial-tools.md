# T19 任务报告 — 空间智能体工具

## 目标

新增 3 个空间智能体工具：list_spatial_layers、query_spatial_features、show_spatial_map。

## 分支

`main2.0`

## 修改文件

无

## 新增文件

| 文件 | 说明 |
|---|---|
| `backend/package/yuxi/agents/toolkits/kbs/spatial_tools.py` | 3 个空间工具 + 3 个输入模型 + 辅助函数 |

## 工具说明

### 1. list_spatial_layers

- 输入：`kb_id`
- 输出：`{ kb_id, layer_count, layers: [{layer_id, name, geometry_type, feature_count, bbox}] }`
- 仅返回元数据摘要，不返回几何数据

### 2. query_spatial_features

- 输入：`kb_id, layer_id, bbox?, limit=20`
- 输出：`{ kb_id, layer_id, total_features, returned, features: [{feature_id, geometry_type, properties}] }`
- 属性值截断 ≤120 字符，防止 ToolMessage 过大
- 不返回完整 GeoJSON geometry 坐标

### 3. show_spatial_map

- 输入：`kb_id, layer_ids, title?`
- 输出：`{ kb_id, title, layers, bounds, map_config: {map_style, center, zoom} }`
- 仅返回 URL、图层、bounds、样式——前端渲染地图
- 最多 10 个图层，自动计算合并 bbox
- 使用 CARTO Positron 底图样式

### 安全设计

| 规则 | 实现 |
|---|---|
| 不返回大体积 GeoJSON | query_spatial_features 无 geometry 坐标；show_spatial_map 无要素 |
| ToolMessage 大小保护 | 属性截断 120 字符，limit 上限 100 |
| 图层数量限制 | show_spatial_map 最多 10 个图层 |
| 权限 | 依赖 kb_id，会话级权限由上游中间件保证 |

## 验证

```bash
docker exec yuxi-sync-api sh -c 'cd /app && uv run --no-sync --no-dev python -c "from yuxi.agents.toolkits.kbs.spatial_tools import list_spatial_layers; print(type(list_spatial_layers))"'
# <class 'langchain_core.tools.structured.StructuredTool'> ✅
```

## 风险

- 工具未注册到 `get_common_kb_tools()`，需手动导入或在智能体配置中注册
- 实际数据库查询需 PostGIS 可用环境

## 已知限制

- `show_spatial_map` 底图使用 CARTO 免费瓦片（需外网访问）
- 空间工具未集成到前端 ToolCallRenderer

## 提交

- 代码 commit：待提交
- 报告 commit：待提交

## 远端

- `main2.0`
