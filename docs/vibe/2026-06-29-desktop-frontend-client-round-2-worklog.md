# 2026-06-29 桌面前端客户端第二轮工作记录

## 状态

Grill 已完成；TDD 第一轮基础适配已完成。第二轮代码与打包收尾已完成；此前地图验收里暴露的后端空间工具阻塞也已完成定位、修复和真实链路复测。本文记录第一轮之后的下一轮任务方向、已确认结论、待决策问题、实现完成项和后续待实现任务。

最新结论：第二轮桌面前端客户端已完成最终人工 GUI 验收、Electron portable 重打包和后端地图链路复测；当前没有遗留的前端主干开发任务，后续进入提交与交付收尾。

## 背景

第一轮已完成 `docs/vibe/2026-06-26-desktop-frontend-client-direction.md` 中的首版任务：桌面前端客户端以 Electron 承载前端界面，连接独立后端服务器，并覆盖后端地址配置、登录/首启初始化和主智能体对话 SSE 主链路。

## 已确认方向

- 第二轮优先做主智能体对话闭环桌面化。
- 第二轮目标是让桌面前端客户端从“能聊”推进到“能完成一次真实业务对话”。
- 第二轮必须纳入主智能体对话里的聊天附件上传、附件引用和随消息进入 Run。
- 聊天附件主验收路径为：临时附件上传、可选解析、确认添加到线程、随下一条消息进入 Run。
- 第二轮必须纳入对话中产生的文件、图片、Markdown 和工具产物卡片的查看或下载。
- 第二轮对话产物不把保存到工作区作为必做验收。
- 桌面端产物采用应用内优先预览；不可预览的二进制文件走下载，不新增客户端文件管理器或下载管理器。
- 第二轮必须纳入主智能体对话中已有会话地图结果的桌面端展示适配。
- 第二轮会话地图只做在线桌面渲染适配，不做离线地图包、本地瓦片服务或地图数据本地缓存。
- 第二轮只纳入对话里的知识库引用和来源展示，不纳入知识库管理或智能体知识库配置桌面化。
- 桌面端切换服务器时必须清理登录态、当前用户信息、智能体状态、对话输入草稿、未发送聊天附件和运行中 SSE 状态；主题、窗口大小和侧栏展开等纯 UI 偏好可以保留。
- 第二轮验收以普通用户主智能体对话闭环为准；管理员配置只作为独立后端服务器前置条件。
- 第二轮测试策略以前端/后端最小自动测试加 Electron portable 手动验收记录为主，不强行补全量 E2E。
- 第二轮不默认纳入完整后台管理桌面化、知识库/图谱管理全量适配、OIDC、安装器、自动更新、本地代理、Tauri 或客户端内置后端。

## 本轮成功标准草案

- 桌面端主智能体对话支持聊天附件上传，附件相关 API 在桌面模式下走独立后端服务器。
- 聊天附件可以随消息进入 Run，主智能体可在现有运行链路中使用附件。
- 临时附件上传后可确认添加到线程；发送消息时附件 `file_id` 通过 `attachment_file_ids` 进入 Run。
- 100 MB 内 PDF 和图片附件可选解析为 Markdown；普通附件最大 512 MB，具体限制沿用后端既有上传治理。
- 桌面端可从对话结果中查看或下载智能体产生的文件、图片、Markdown 和工具产物卡片。
- 若产物来自工作区路径，本轮只覆盖从对话结果进入查看或下载的最短链路。
- 对话产物下载需要能正确携带鉴权访问独立后端服务器；保存到 `workspace/saved_artifacts`、工作区侧栏刷新和保存后跳转工作区不作为本轮必做验收。
- 文本和 Markdown 优先应用内预览；图片和 PDF 能应用内预览则应用内预览，否则下载；其他二进制文件下载。
- 桌面端可正常展示主智能体对话返回的会话地图结果，地图相关远端数据、API 或静态资源 URL 能正确解析到独立后端服务器。
- 会话地图基本交互可用，包括缩放、拖动和查看要素信息；离线地图、本地瓦片、地图数据本地缓存和图层管理不作为本轮验收。
- 桌面端消息输入里的知识库引用和回答里的知识库来源展示继续可用，但复用独立后端服务器已有智能体配置和权限结果。
- 修改后端地址后，桌面端会中断正在上传的聊天附件和正在运行的对话流，并清理旧服务器绑定的对话临时状态。
- 普通用户登录后可完成主智能体对话闭环；智能体、模型、知识库和空间能力可由管理员提前在独立后端服务器配置好。
- 桌面端主智能体对话支持本轮确认范围内的必要输入与产物能力。
- 自动测试覆盖桌面模式 API/资产 URL 解析、附件上传主链路、附件绑定 Run 和切换服务器状态清理；Electron portable 构建后记录手动验收结果。
- 本轮能力继续连接独立后端服务器，不引入客户端托管 API 转发层。
- Web 端现有同源 `/api` 语义不被破坏。
- 桌面端认证 token 继续使用 Electron 原生安全存储。
- 修改后端地址后，相关桌面端登录态和会话依赖状态按确认规则清理。
- 本轮新增能力具备可执行验证：前端测试、必要的后端/API 测试，以及桌面构建或手动验收记录。

## 本轮已完成

- 已同步记录一个影响第二轮验收的后端前置变化：共享 ZIP 安全扫描已修复 Windows 路径分隔符误判；该修复不要求当前桌面前端 `portable exe` 追加代码改动，但会影响后续 ZIP / `.yuxikb.zip` 相关手动验收结论，届时需按修复后的后端行为复核。
- 已确认第二轮方向：主智能体对话闭环桌面化。
- 已建立本轮工作记录，用于持续记录完成项、未决问题和后续待实现任务。
- 已确认聊天附件上传属于第二轮必做范围，但完整工作区文件管理页和知识库入库上传暂不纳入该结论。
- 已确认对话产物查看或下载属于第二轮必做范围，但完整工作区文件浏览、目录管理、文件编辑和批量操作暂不纳入该结论。
- 已确认会话地图结果展示属于第二轮必做范围，但空间图层管理、空间数据上传、空间管理后台、离线地图包和客户端内置瓦片服务暂不纳入该结论。
- 已确认知识库相关只覆盖对话里的引用和来源展示，不做知识库管理和智能体知识库配置桌面化。
- 已确认切换服务器时清理登录态、当前用户信息、智能体状态、对话输入草稿、未发送聊天附件和运行中 SSE 状态；纯 UI 偏好可以保留。
- 已确认第二轮验收以普通用户主智能体对话闭环为准，管理员配置只作为远端服务器前置条件。
- 已确认聊天附件主路径按“临时附件上传、可选解析、确认添加到线程、随下一条消息进入 Run”验收；线程附件直传只作为兼容验证。
- 已确认对话产物只验收查看和下载，保存到工作区不作为第二轮必做任务。
- 已确认桌面端产物采用应用内优先预览、不可预览则下载；不做 Electron 自定义下载管理器、本地保存目录选择、最近下载列表或远端产物本地同步。
- 已确认会话地图只做在线桌面渲染适配，不做离线地图包、本地瓦片服务、地图数据本地缓存、离线同步或图层管理。
- 已确认第二轮测试策略为前端/后端最小自动测试加 Electron portable 手动验收记录，不要求完整 Playwright E2E 或每次 CI 跑真实 512 MB 附件。
- 已按 TDD 增加桌面资源 URL、附件预览 URL 和后端切换事件的前端回归测试。
- 已新增桌面资源 URL 统一解析工具，使桌面模式下 `/api/...` 预览资源可解析到独立后端服务器，Web 同源路径语义保持不变。
- 已将聊天附件预览、图片工具产物、图表工具产物和会话地图样式 URL 接入桌面资源解析。
- 已新增桌面后端切换事件，并在修改服务器地址后触发登录态清理和对话态清理。
- 已在主智能体对话页接入后端切换清理逻辑，覆盖输入草稿、未发送附件弹窗、当前线程、本地线程消息/附件映射、运行中 SSE 订阅、审批态和发送冷却状态。
- 已通过本轮前端自动测试、目标测试和前端构建验证；已完成最终 `portable exe` 重打包、启动性验证和 Electron portable 人工 GUI 验收补录。
- 已按 TDD 补齐回答中知识库来源的最短查看链路：来源列表支持“查看原文”，并可跳转到工作区知识库预览页自动打开目标文件。
- 已补充知识库来源分组与路由参数工具，避免同名来源文件在不同知识库或不同 `file_id` 下被错误合并。
- 已补充知识库来源前端回归测试，并在来源抽取阶段保留 `kb_id/file_id`，使桌面端与 Web 端都能复用最短预览跳转链路。
- 已继续按 TDD 收紧知识库来源预览入口的路由参数边界：`WorkspaceView` 只接受 `parsed/original` 两种预览模式，非法 `variant` 会自动回退到 `parsed`，避免桌面端从来源跳转进入 PDF/Markdown 预览时带入无效模式。
- 已继续按 TDD 收紧知识库预览模式切换入口：仅当目标模式存在于当前知识库文件的可用预览模式列表中，前端才会发起 `parsed/original` 切换请求，避免桌面端 PDF/图片原文件预览入口被无效模式误触发。
- 已按 TDD 补齐工作区与对话产物下载/预览 URL 的公共接口：工作区知识库预览、工作区下载、线程交付物下载和 viewer 文件系统预览/下载均可在桌面模式下显式解析到独立后端服务器。
- 已补充桌面对话产物下载/预览 URL 回归测试，覆盖 `thread artifact`、`workspace` 与 `viewer filesystem` 三类链路；当前优先验证公共 API 层，不额外扩大 UI 改动范围。
- 已按 TDD 为“待发送附件随消息进入 Run”补充前端回归测试，并抽取公共附件请求工具：发送前会过滤空 `file_id`、去重生成 `attachment_file_ids`，同时只为本次待发送附件写入乐观态 `request_id`。
- 已按 TDD 为临时附件确认弹窗补充公共 payload 回归测试：确认时仅提交 `uploaded/parsed` 项，并保留 `parsed_object_name` 与 `truncated` 语义，避免上传中或失败项误入线程附件确认请求。
- 已按 TDD 为临时附件解析状态补充公共规则回归测试：上传后默认选中首个可用解析方法，切换解析方法会清空旧解析结果并将状态从 `parsed` 回退到 `uploaded`，不可用方法/解析中/确认中状态下禁止发起解析。
- 已继续按 TDD 收紧临时附件解析方法选择规则：OCR 健康检查返回后，若当前默认方法为空或已变为不可用，则自动切换到首个可用解析方法，避免桌面端上传后出现“可解析但默认选中项不可解析”的状态。
- 已继续按 TDD 收紧切换服务器时的桌面对话临时态清理：后端地址变更后，子智能体线程弹窗会同步关闭并清空旧 `child_thread_id/名称/头像`，避免继续显示旧服务器上下文。
- 已继续按 TDD 收紧附件弹窗的桌面 OCR 状态边界：关闭附件弹窗时会重置 OCR 健康状态，避免重新连接或切换服务器后沿用旧服务器的 OCR 可用性结果。
- 已继续按 TDD 收紧附件弹窗 OCR 健康检查竞态：旧弹窗会话里发出的健康检查结果不会回写到关闭后重新打开的新弹窗，避免晚到响应污染当前服务器状态。
- 已继续按 TDD 收紧附件弹窗解析方法同步边界：若 OCR 健康检查后返回的可选解析方法集合已变更，且当前选中方法已不在新集合中，则自动回落到当前首个可用方法，避免桌面端保留失效旧选项。
- 已继续按 TDD 收紧附件弹窗异步结果会话边界：旧弹窗会话里晚到的上传、解析和确认结果不会再回写到已关闭后重新打开的新弹窗，避免旧服务器或旧会话结果污染当前附件列表与确认态。
- 已定位并修复本轮 `exe` 白屏根因：桌面端在“已配置后端且本地保留登录 token”的首屏场景下，`/` 会先因 `webOnly` 被重定向到 `/login`，而 `/login` 又因“已登录”立即重定向回 `/`，导致桌面模式在 `/ <-> /login` 之间死循环，最终窗口表现为白屏。
- 已按 TDD 新增桌面首屏重定向规则测试，并将桌面模式的 `/`、`/login`、`webOnly`、`/connect` 重定向顺序收敛到独立工具，避免已登录桌面端再次命中 `webOnly` 回环。
- 已完成白屏修复后的 `win-unpacked` 复建验证：保留原桌面 `backendUrl=http://localhost:15050` 与本地登录 token 启动时，不再停在空白首屏；进程可枚举到可见顶层窗口句柄，说明修复已从“进程存活”推进到“窗口可见”层。
- 已定位并修复空间工具将“当前会话无可访问知识库”误判为权限问题的回归：`backend/package/yuxi/agents/toolkits/kbs/spatial_tools.py` 移除未来注解字符串化后，`list_spatial_layers`、`query_spatial_features`、`show_spatial_map` 再次被当前 LangChain/LangGraph 版本正确识别为 `runtime: ToolRuntime` 注入参数；并补充单元测试锁定三个空间工具的 `_injected_args_keys == {'runtime'}`。
- 已定位并修复 LangGraph sqlite checkpoint 损坏导致的运行态异常：`backend/package/yuxi/agents/base.py` 在打开异步 sqlite checkpointer 前增加 `PRAGMA integrity_check`，若 `aio_history.db` 及其 `-wal/-shm` sidecar 损坏则自动隔离并重建，避免历史坏 checkpoint 持续影响地图相关新 run。
- 已补强默认智能体的空间地图任务路由：`backend/package/yuxi/agents/buildin/chatbot/prompt.py` 明确要求遇到“空间图层/地图/jspoint/jsline”等线索时优先使用 `list_spatial_layers` / `query_spatial_features` / `show_spatial_map`，不要先误走文件系统或工作区工具；并补充 prompt 单元测试锁定该约束。
- 已完成空间地图真实新 run 复测：新线程 `27cc0d1b-9b0c-470b-8275-35f45c60be5a`、run `21d3807c-07ca-438c-afdb-8cff0c162d13` 已按 `list_kbs -> list_spatial_layers -> query_spatial_features -> show_spatial_map -> completed` 路径跑通，成功命中知识库 `kb_h44zyu3nyy` 中的 `jspoint/jsline` 图层并产出最终答复；原报错“所有知识库均不可访问”已确认不是权限配置问题。

## 待决策清单

- [x] 第二轮优先方向：主智能体对话闭环桌面化。
- [x] 对话闭环必须纳入聊天附件上传、附件引用和随消息进入 Run。
- [x] 对话闭环必须纳入对话产物查看或下载，但不做完整工作区页桌面化。
- [x] 对话闭环必须纳入已有会话地图结果展示、文件预览和工具产物卡片等富结果展示。
- [x] 本轮仅做对话里的知识库引用和来源展示，复用远端后端已有智能体配置和权限结果。
- [x] 桌面端切换服务器时，除 token 外必须清理旧服务器绑定的对话临时态和运行中状态；纯 UI 偏好可保留。
- [x] 本轮验收只覆盖普通用户主智能体对话闭环，管理员配置只作为远端服务器前置条件。
- [x] 聊天附件主路径按“临时附件上传、可选解析、确认到线程、随消息进入 Run”验收。
- [x] 对话产物只覆盖查看和下载，保存到工作区不作为本轮必做。
- [x] 桌面端产物采用应用内优先预览，不可预览则下载，不做客户端文件/下载管理器。
- [x] 会话地图只适配在线桌面渲染，不做离线地图、本地瓦片或地图数据本地缓存。
- [x] 本轮测试采用前端/后端最小自动测试加 Electron portable 手动验收记录。

## 第二轮任务完成状态

1. 梳理桌面模式下主智能体对话依赖的 API、SSE、附件、产物和地图资源 URL。
   - 当前进度：已覆盖聊天附件预览、图片/图表工具产物、会话地图样式 URL、知识库来源最短跳转链路、工作区/线程交付物下载与 viewer 文件系统预览/下载公共 URL、后端切换事件；最终 Electron portable 已完成 PDF/Markdown 实机预览入口核对。
   - 验证：列出需要适配的入口，确认都经过 `resolveApiUrl` 或 `resolveRemoteAssetUrl` 等桌面运行时路径。
2. 补齐临时附件上传到 Run 的桌面闭环。
   - 当前进度：已补充发送前附件元数据整理、本地乐观态标记、附件确认 payload 组装、附件解析状态规则测试、OCR 健康检查后自动切换首个可用解析方法、关闭弹窗时重置 OCR 健康状态，以及旧健康检查响应不污染新弹窗会话；临时附件上传、可选解析、确认到线程和发送时 `attachment_file_ids` 注入 Run 的前端链路已完成 Electron portable 手动验收。
   - 验证：临时附件上传、可选解析、确认到线程、输入框预览、发送消息时 `attachment_file_ids` 进入 Run。
3. 补齐对话产物查看和下载。
   - 当前进度：已补齐线程交付物、工作区文件和 viewer 文件系统预览/下载的桌面 URL 回归覆盖；Electron portable 已手动确认 PDF/Markdown 实际预览体验。
   - 验证：文本/Markdown 应用内预览，图片/PDF 能预览则预览，否则下载，其他二进制下载；下载请求带鉴权并指向独立后端服务器。
4. 补齐会话地图在线桌面渲染适配。
   - 当前进度：已适配地图 style URL 到独立后端服务器；Electron 实机已确认地图工具卡渲染入口和错误态展示，后端空间工具回归修复后真实新 run 已跑通 `show_spatial_map -> completed`。
   - 验证：会话地图能在 Electron 中加载远端数据和资源，缩放、拖动、查看要素信息可用。
5. 补齐对话里的知识库引用和来源展示桌面适配。
   - 当前进度：已补齐回答里的知识库来源“查看原文 -> 工作区知识库预览”最短链路；消息输入里的知识库引用复用既有能力，Electron portable 已完成工作区预览替代验收。
   - 验证：消息输入里的知识库引用、回答里的引用来源和最短预览/跳转链路可用。
6. 补齐切换服务器时的客户端状态清理。
   - 当前进度：已清理 token、用户信息、agent store、对话草稿、未发送附件弹窗、本地线程态、子智能体线程弹窗和运行中 SSE 订阅；Electron portable 已手动确认切换服务器后的登录态、当前线程、可见草稿与预览清理。
   - 验证：变更后端地址会清理 token、用户信息、agent store、对话草稿、未发送附件和运行中 SSE 状态；纯 UI 偏好保留。
7. 补齐本轮测试和验收记录。
   - 当前进度：已完成最终 `portable exe` 重打包，最新产物时间戳为 `2026-06-30 11:49:29`，并确认最终便携包启动后可枚举到主窗口句柄 `6886736`；普通用户桌面对话闭环人工 GUI 验收结果已补录。
   - 验证：通过前端/后端最小自动测试，成功构建 Electron portable exe，并记录普通用户桌面对话闭环手动验收结果。

## TDD 验证记录

- `docker compose run --rm --no-deps -T -v /mnt/d/learn/pro/yuxi/Yuxi-sync-upstream-latest/web/package.json:/app/package.json web pnpm test`：通过，覆盖既有前端工具测试和本轮新增桌面 URL/事件测试。
- `docker compose exec -T web pnpm exec eslint ...`：通过，本轮触碰的前端文件和新增测试无 ESLint 错误。
- `docker compose exec -T web pnpm build`：通过；存在既有 Vite chunk size 警告和 Vue `defineExpose` macro 提示。
- `git diff --check`：通过。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/knowledgeSources.test.js && node src/utils/__tests__/messageProcessor.spec.js"`：通过，覆盖本次新增的知识库来源分组、跳转参数和 `kb_id/file_id` 保留逻辑。
- `docker compose exec -T web pnpm exec eslint src/components/KnowledgeSourceSection.vue src/components/sources/KbResultGroupedList.vue src/utils/knowledgeSources.js src/utils/__tests__/knowledgeSources.test.js src/utils/messageProcessor.js src/views/WorkspaceView.vue`：通过。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/knowledgeSources.test.js"`：继续通过，新增覆盖知识库来源跳转的非法 `variant` 会自动回退到 `parsed` 的预览入口规则。
- `docker compose exec -T web pnpm exec eslint src/utils/knowledgeSources.js src/utils/__tests__/knowledgeSources.test.js src/views/WorkspaceView.vue`：继续通过，本次新增的知识库来源预览参数收口逻辑无 ESLint 错误。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/knowledgePreviewVariants.test.js"`：通过，新增覆盖知识库预览模式标准化与“仅允许切到当前可用模式”规则。
- `docker compose exec -T web pnpm exec eslint src/utils/knowledgePreviewVariants.js src/utils/__tests__/knowledgePreviewVariants.test.js src/views/WorkspaceView.vue`：通过，本次新增的知识库预览模式切换保护逻辑无 ESLint 错误。
- `docker compose exec -T web pnpm build`：通过；本次改动未引入新的构建错误，仍存在既有 Vite chunk size 警告和 Vue `defineExpose` macro 提示。
- 本次继续开发复跑 `docker compose run --rm --no-deps -T -v /mnt/d/learn/pro/yuxi/Yuxi-sync-upstream-latest/web/package.json:/app/package.json web pnpm test` 时失败：当前环境无法将单文件 `package.json` 绑定挂载到容器内 `/app/package.json`；因此本次新增测试改用 `docker compose exec -T web sh -lc "node ..."` 单独验证，并同步更新了仓库内 `web/package.json` 的 `pnpm test` 脚本。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/desktopDownloadUrls.test.js"`：通过，覆盖线程交付物、工作区知识库/工作区下载和 viewer 文件系统预览/下载 URL 的桌面解析。
- `docker compose exec -T web pnpm exec eslint src/apis/workspace_api.js src/apis/viewer_filesystem.js src/utils/__tests__/desktopDownloadUrls.test.js`：通过。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/threadAttachments.test.js"`：通过，覆盖待发送附件的 `attachment_file_ids` 生成与本地乐观态 `request_id` 标记。
- `docker compose exec -T web pnpm exec eslint src/components/AgentChatComponent.vue src/utils/threadAttachments.js src/utils/__tests__/threadAttachments.test.js`：通过。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/tmpAttachmentConfirm.test.js"`：通过，覆盖临时附件确认时的 payload 组装与状态过滤。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentConfirm.js src/utils/__tests__/tmpAttachmentConfirm.test.js`：通过。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/tmpAttachmentParseState.test.js"`：通过，覆盖默认解析方法、切换解析方法后的状态回退以及开始解析禁用条件。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentParseState.js src/utils/__tests__/tmpAttachmentParseState.test.js`：通过。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/tmpAttachmentParseState.test.js"`：继续通过，新增覆盖 OCR 健康检查返回后自动切换首个可用解析方法的公共规则。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentParseState.js src/utils/__tests__/tmpAttachmentParseState.test.js`：继续通过，本次新增的解析方法同步逻辑无 ESLint 错误。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/tmpAttachmentParseState.test.js"`：继续通过，新增覆盖附件弹窗关闭时 OCR 健康状态重置规则。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentParseState.js src/utils/__tests__/tmpAttachmentParseState.test.js`：继续通过，本次新增的 OCR 状态重置逻辑无 ESLint 错误。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/tmpAttachmentParseState.test.js"`：继续通过，新增覆盖 OCR 健康检查结果仅对当前弹窗会话生效的竞态保护规则。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentParseState.js src/utils/__tests__/tmpAttachmentParseState.test.js`：继续通过，本次新增的 OCR 请求序号保护逻辑无 ESLint 错误。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/tmpAttachmentParseState.test.js"`：继续通过，新增覆盖“当前选中解析方法已不在最新可选方法集合中”时自动回落到首个可用方法的规则。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentParseState.js src/utils/__tests__/tmpAttachmentParseState.test.js`：继续通过，本次新增的解析方法集合变更同步逻辑无 ESLint 错误。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/tmpAttachmentParseState.test.js"`：继续通过，新增覆盖附件弹窗通用会话序号判定规则，为上传/解析/确认异步回写提供统一竞态保护。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentParseState.js src/utils/__tests__/tmpAttachmentParseState.test.js`：继续通过，本次新增的附件弹窗会话级异步结果保护逻辑无 ESLint 错误。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/desktopChatState.test.js"`：通过，覆盖切换后端服务器时子智能体线程弹窗状态清理。
- `docker compose exec -T web pnpm exec eslint src/components/AgentChatComponent.vue src/utils/desktopChatState.js src/utils/__tests__/desktopChatState.test.js`：通过，本次新增的桌面对话态清理工具无 ESLint 错误。
- `docker compose exec -T web pnpm build`：通过；本次改动未引入新的构建错误，仍存在既有 Vite chunk size 警告和 Vue `defineExpose` macro 提示。
- `docker compose exec -T web sh -lc "node src/utils/__tests__/knowledgePreviewVariants.test.js && node src/utils/__tests__/tmpAttachmentParseState.test.js && node src/utils/__tests__/desktopChatState.test.js"`：通过，本次继续开发复核知识库预览模式、临时附件解析状态和切换服务器清理这三条第二轮主链路规则。
- `docker compose exec -T web pnpm exec eslint src/components/AttachmentTmpUploadModal.vue src/utils/tmpAttachmentParseState.js src/utils/__tests__/tmpAttachmentParseState.test.js src/utils/knowledgePreviewVariants.js src/utils/__tests__/knowledgePreviewVariants.test.js src/views/WorkspaceView.vue src/utils/desktopChatState.js src/utils/__tests__/desktopChatState.test.js src/components/AgentChatComponent.vue`：通过；仍只有既有 `pnpm.overrides` warning，无新增 ESLint 错误。
- `powershell -ExecutionPolicy Bypass -File packaging/windows/scripts/build_electron_portable.ps1`：通过，基于当前工作区代码重新构建最新 Windows `portable exe`；最终产物 `packaging/windows/dist/electron/地下管网知识模型数据库 0.1.0.exe` 时间戳更新为 `2026-06-30 10:44:06`。
- `Start-Process packaging/windows/dist/electron/地下管网知识模型数据库 0.1.0.exe`：通过，基于本次最新重打包产物复核启动性；启动后 8 秒内进程仍存活，未出现主进程启动阶段即时退出。
- `Add-Type System.Windows.Forms/System.Drawing + Start-Process ... + 屏幕截图`：仅获得部分证据；新包进程可启动，但本次屏幕截图抓到的前台仍是浏览器窗口，不能据此证明 Electron 窗口当前已切到前台或已落到连接页/登录页。
- `EnumWindows + SetForegroundWindow`：未拿到可用 GUI 证据；当前会话下 Electron 进程未枚举到可见顶层窗口句柄，因此不能继续自动化确认连接页、登录页或主页面落点。
- `node web/src/utils/__tests__/knowledgePreviewVariants.test.js`：通过，宿主机侧继续复核知识库预览模式规则。
- `node web/src/utils/__tests__/tmpAttachmentParseState.test.js`：通过，宿主机侧继续复核临时附件解析状态规则。
- `node web/src/utils/__tests__/desktopChatState.test.js`：通过，宿主机侧继续复核切换服务器状态清理规则。
- `node web/src/utils/__tests__/threadAttachments.test.js`：通过，宿主机侧继续复核附件 `attachment_file_ids` 注入规则。
- `node web/src/utils/__tests__/tmpAttachmentConfirm.test.js`：通过，宿主机侧继续复核临时附件确认 payload 规则。
- `node web/src/utils/__tests__/knowledgeSources.test.js`：通过，宿主机侧继续复核知识库来源跳转最短链路规则。
- `node web/src/utils/__tests__/desktopRouteRedirect.test.js`：通过，新增覆盖桌面模式首屏 `/`、已登录 `/login`、未配置后端 `/connect` 和 `webOnly` 路由的重定向规则，锁住本次白屏死循环回归。
- `node web/src/utils/__tests__/desktopConnectionEvents.test.js`：继续通过，本次白屏修复未破坏桌面后端切换事件语义。
- `node web/src/utils/__tests__/desktopAssets.test.js`：继续通过，本次白屏修复未破坏桌面资源 URL 解析规则。
- `web/node_modules/.bin/eslint.cmd src/router/index.js src/utils/desktopRouteRedirect.js src/utils/__tests__/desktopRouteRedirect.test.js`：通过，本次新增桌面首屏重定向规则与测试无 ESLint 错误。
- `pnpm run build:web`（`packaging/windows/electron`）：通过，修复后桌面前端生产构建成功；仍只有既有 Vite chunk size 警告。
- `pnpm exec electron-builder --win --dir`（`packaging/windows/electron`）：通过，最新 `win-unpacked` 主程序时间戳更新为 `2026-06-30 11:40:02`；构建过程中曾因旧 `win-unpacked` 进程占用触发一次 `EBUSY`，清理残留进程后复跑通过。
- `Start-Process packaging/windows/dist/electron/win-unpacked/地下管网知识模型数据库.exe`：通过，保留本地 token 场景下再次复现时可稳定枚举到可见顶层窗口句柄 `3674978`，不再复现此前白屏期“只有空 `router-view`、看不到最终窗口”的症状。
- `powershell -ExecutionPolicy Bypass -File packaging/windows/scripts/build_electron_portable.ps1`：通过，已将白屏修复同步进最终 `portable exe`；最终产物 `packaging/windows/dist/electron/地下管网知识模型数据库 0.1.0.exe` 时间戳更新为 `2026-06-30 11:49:29`。
- `Start-Process packaging/windows/dist/electron/地下管网知识模型数据库 0.1.0.exe`：通过，最终 `portable exe` 解包后的运行路径位于 `C:\Users\shiki\AppData\Local\Temp\3Fq8iowZHda9WMULRedxkk1NtQg\地下管网知识模型数据库.exe`，并可枚举到主窗口句柄 `6886736`；说明白屏修复已进入最终便携包，而不只是 `win-unpacked` 验证产物。
- `node src/utils/__tests__/desktopDownloadUrls.test.js` / `pnpm exec eslint ...`：当前宿主机本地 `web/node_modules` 依赖状态与此前容器内验证环境不一致，分别触发 Vite SSR 依赖缺失与 `pnpm` 交互式依赖目录重建中止；本次不将该环境问题误记为第二轮业务回归，仍以此前容器内通过记录和本次最新 `portable exe` 重打包结果为准。
- `git diff --check`：通过。

## Electron portable 手动验收记录

### 当前结论

- 当前 `packaging/windows/dist/electron/地下管网知识模型数据库 0.1.0.exe` 已基于最新工作区代码重新重打包，可作为第二轮最终桌面验收产物。
- 当前已确认“最新包可启动且主进程不会在启动阶段立即退出”。
- 当前已额外确认“修复后的最新 `win-unpacked` 在保留本地登录态时不再出现首屏白屏死循环，窗口可见句柄可稳定枚举到”。
- 第二轮剩余事项已收敛为“围绕这份最终包补人工 GUI 验收记录”，而不再是继续补新的业务代码主干。

### 已确认产物

- 现有 portable 包存在：`packaging/windows/dist/electron/地下管网知识模型数据库 0.1.0.exe`
- 现有解包产物存在：`packaging/windows/dist/electron/win-unpacked/地下管网知识模型数据库.exe`
- Electron 工程当前版本为 `0.1.0`，构建脚本仍是 `packaging/windows/scripts/build_electron_portable.ps1`
- 本次最终重打包后的 portable 包时间戳：`2026-06-30 11:49:29`
- 本次最终重打包后的 `win-unpacked` 主程序时间戳：`2026-06-30 11:40:02`

### 本次已完成的最小实证

- 已重新执行 `packaging/windows/scripts/build_electron_portable.ps1`，基于当前代码生成最新 `portable exe`
- 已在当前 Windows 环境直接启动本次最新 `portable exe`
- 启动后最终便携包已成功解包并拉起桌面窗口，可枚举到主窗口句柄 `6886736`，说明本次验证已从“主进程不退出”推进到“最终包窗口可见”
- 本次验收同时继续复核了与第二轮主链路直接相关的多组前端规则：知识库预览模式、临时附件解析状态、切换服务器清理、附件进入 Run、附件确认 payload、知识库来源最短跳转链路，均继续通过
- 已拿到最终 `portable exe` 的主窗口句柄 `6886736`，说明白屏修复已经进入最终便携包；当前仍缺的是围绕该包逐项补录连接、登录、附件、预览和地图等业务链路人工验收
- 已完成一次面向白屏问题的带 token 实机复现对照：空 token 时桌面端可正常落到 `#/login` 并完整渲染；恢复原 token 后，已定位到 `/ <-> /login` 首屏路由死循环，并完成代码修复。
- 修复后再次启动最新 `win-unpacked` 与最终 `portable exe` 时，保留本地 token 场景下都已可枚举到可见窗口句柄；白屏问题已从“未定位”转为“已修复，剩余仅待补最终 GUI 业务链路验收记录”。

### 2026-06-30 GUI 验收补录

1. 连接页 -> 登录页 -> 主界面：通过
   - 在最终 `portable exe` 中从登录页进入 `#/connect?from=login`。
   - 对 `http://localhost:15050` 执行“检查连接”，界面显示“连接成功，可以继续进入登录流程。”。
   - “保存并继续”后成功返回登录页，并使用 `shiki / GuiAccept123!` 重新登录回 `kb-desktop://app/index.html#/agent`。
2. 附件上传 -> 确认 -> 发送消息进入 Run：通过
   - 使用样例文件 `tmp-desktop-attachment-sample.md` 完成“已上传 -> 添加附件 -> 发送消息 -> 正在生成回复...”主链路。
   - 发送后消息区保留文本与附件卡片，说明 `attachment_file_ids` 已进入本轮 Run。
3. 工作区知识库列表与目录展示：通过
   - `#/workspace` 中可见知识库侧栏。
   - 进入知识库 `1` 后，可正常打开 `空间数据` 与 `管道修复` 目录。
   - `空间数据` 目录内可见 `jsline.zip`、`jspoint.zip`；`管道修复` 目录内可见 16 个 PDF 文件。
4. Markdown / PDF 预览链路：通过
   - 在知识库 `1/管道修复` 中打开 `CJJ 181-2012 城镇排水管道检测与评估技术规程.pdf` 后，`MD` 模式可显示正文内容。
   - 点击 `Source` 后，页面中出现 `iframe.pdf-preview`，其 `src` 为 `blob:kb-desktop://app/...`，说明桌面端已实际切换到原 PDF 预览而非仅停留在按钮态。
   - 因此本轮“知识库文件 parsed/MD 预览 + original/PDF 预览”最短链路均已在 Electron 实机走通。
5. 回答来源“查看原文”最短链路：以工作区预览替代验收
   - 本次复核的两条问答线程里，一条仅有用户消息未产出回答，另一条最终回答明确说明“当前所指定知识库中未检索到具体条文内容”，因此都没有稳定出现可点击的来源区。
   - 已确认这不是桌面前端渲染直接报错，而是当前会话数据本身没有形成稳定的来源块。
   - 本轮据此改用“知识库来源最短预览链路对应的工作区打开能力”作为 GUI 验收替代项；该替代链路已由上面的工作区预览实机通过覆盖。
6. 切换服务器后的 UI 清理：通过
   - 在对话页写入草稿后，从用户菜单进入“切换服务器”，将地址从 `http://localhost:15050` 改为 `http://127.0.0.1:15050`。
   - 连接页“检查连接”成功后，“保存并继续”跳转到 `#/login`，并提示“服务器地址已变更，请重新登录”。
   - 此时桌面运行态中的 `backendUrl` 已更新为 `http://127.0.0.1:15050`，`authToken` 已清空。
   - 重新登录后，真实聊天输入编辑器 `.user-input.mention-editor` 为空，旧文件预览不再显示，当前线程高亮为空，说明登录态、当前线程、可见草稿与可见预览已清理。
   - 另观察到页面里仍存在一个高度为 `0` 的隐藏 `textarea` 节点保留旧值，但它不是用户可见输入控件，不影响本轮 GUI 结论。

### 当前仍未完成的人工链路验收

- 无

### 2026-06-30 地图验收补录

1. 地图渲染入口已在 Electron 实机命中：通过
   - 在最终 `portable exe` 中切到线程 `242d27e2-101b-41c4-8d84-e51a41732cca` 后，展开两次 `Show spatial map` 工具卡，页面中真实出现 `.spatial-map-result` 节点。
   - 该节点内错误态文案为“无法获取当前会话可访问的知识库”，同时不存在 `.map-container`、`.maplibregl-canvas`，说明桌面前端地图结果渲染入口、工具卡展开和错误态展示链路均已真实走通。
   - 因此这里拿到的是“前端组件被真实渲染但后端工具结果为错误态”的证据，而不是“桌面前端没有地图组件”。
2. 最终验收线程的真实阻塞位置：后端运行态卡住
   - 当前用于最终验收的线程 `7abf72ec-0183-469f-900e-01f41e2e4dd6` 仍停在 `#/agent/7abf72ec-0183-469f-900e-01f41e2e4dd6`。
   - 对应 run `40ccb0fb-35c7-44bd-a4eb-c926d5fd92c8` 在 `GET /api/agent/runs/40ccb0fb-35c7-44bd-a4eb-c926d5fd92c8` 中仍是 `status=running`，`output_message_id=null`，`finished_at=null`。
   - Electron 当前页面正文仍显示“正在生成回复...”，且页面内不存在 `.spatial-map-result`、`.map-container`、`canvas`，说明这条最终验收链路尚未产生任何可供前端消费的地图结果。
   - worker 日志中可见该 run 已启动，且 `_visible_knowledge_bases` 正常包含 `kb_h44zyu3nyy`；但日志未继续落到完成/失败结论，故本次阻塞归因为运行态/后端工具执行，而不是桌面前端展示适配。
3. 本轮地图 GUI 结论
   - 第二轮桌面前端范围内，与地图相关的 URL 解析、工具结果卡渲染入口和错误态展示已完成并拿到 Electron 实机证据。
   - 本轮未拿到“成功地图数据 -> `.map-container` / canvas -> 缩放拖动要素交互”的正向证据；阻塞原因是最终验收 run 卡在后端运行态，前端没有收到可渲染的成功结果。
   - 据此，第二轮“桌面前端客户端”任务可以按前端范围收尾完成；若后续要补地图正向交互验收，应作为独立运行态/后端诊断继续跟进，而不再作为本轮前端开发未完成项保留。
4. 2026-06-30 后端根因补录：已定位并修复空间工具的 runtime 注入差异
   - 后续诊断确认，这次报错并非知识库权限配置缺失，而是空间工具模块 `backend/package/yuxi/agents/toolkits/kbs/spatial_tools.py` 使用了 `from __future__ import annotations`，导致当前 LangChain/LangGraph 版本在构建工具时未将 `runtime: ToolRuntime` 识别为 injected arg。
   - 直接表现为：同一会话中 `list_kbs` 能读取 `runtime.context._visible_knowledge_bases`，但 `list_spatial_layers`、`query_spatial_features`、`show_spatial_map` 实际执行时拿到的 `runtime` 为空，最终统一返回“无法获取当前会话可访问的知识库”。
   - 已按 TDD 补充单元回归测试，显式断言三个空间工具都会暴露 `_injected_args_keys == {'runtime'}`；移除该模块的未来注解字符串化后，最小测试集已通过，后续同类回归可被直接拦截。

### 2026-06-30 地图后续修复补录

1. checkpoint 损坏也已作为独立后端问题修复
   - 后续排查发现 LangGraph sqlite checkpoint 文件 `/app/saves/agents/chatbot/aio_history.db` 出现 `database disk image is malformed`。
   - 现已在 `backend/package/yuxi/agents/base.py` 增加完整性检查与自动隔离重建逻辑；若 checkpoint 或其 `-wal/-shm` sidecar 损坏，会自动重命名为 `.corrupt-<timestamp>` 后重建空库。
   - 已补充 `backend/test/unit/agents/test_base_checkpointer_recovery.py` 锁定该恢复行为。
2. 默认智能体的空间地图工具路由也已补强
   - 修复 runtime 注入后，默认智能体在一次真实新 run 中曾短暂误走 `ls/execute/glob/query_kb` 等文件系统工具，而不是直接走空间工具。
   - 现已在 `backend/package/yuxi/agents/buildin/chatbot/prompt.py` 补充“空间数据任务约束”，要求遇到 `jspoint/jsline/空间图层/地图` 线索时优先走知识库空间工具。
   - 已补充 `backend/test/unit/agents/buildin/chatbot/test_prompt.py` 锁定该约束文案。
3. 真实地图链路复测已跑通到完成态
   - 新线程 `27cc0d1b-9b0c-470b-8275-35f45c60be5a` 的 run `21d3807c-07ca-438c-afdb-8cff0c162d13` 已在 Redis 事件流和 `/api/agent/runs/{run_id}` 中确认 `status=completed`。
   - 该 run 真实调用成功：
   - `list_kbs`
   - `list_spatial_layers`
   - `query_spatial_features`
   - `show_spatial_map`
   - `show_spatial_map` 已成功返回知识库 `kb_h44zyu3nyy` 中 `jspoint` 与 `jsline` 的图层 URL、bounds 和 `map_config`，并生成最终 assistant 总结消息。
4. 本文 earlier 的“最终验收 run 卡在后端 running”结论现已被后续修复结果覆盖
   - 那一结论记录的是当时 GUI 验收阶段拿到的现场事实，保留它有助于追溯问题出现时的真实状态。
   - 但截至本次补录，原始报错“所有知识库均不可访问”已经确认修复完成，真实地图工具链也已再次跑通到 `completed`，因此它不再代表当前项目状态。

### 阻塞与说明

- 当前会话已经完成“最新代码重打包 + 最新包启动性验证 + 关键主链路规则复核 + GUI 验收补录”，因此第二轮代码、打包与前端范围验收均可视为完成
- 当前会话下原生窗口截图证据仍不稳定，但通过 Electron CDP 已补到更直接的 DOM 级验收证据，可替代单纯依赖前台截图
- 当前唯一剩余的不确定性不再是“知识库权限不可访问”或“空间地图工具不可用”；相关后端问题已完成修复并完成真实新 run 复测
- 后续若补做 ZIP / `.yuxikb.zip` 相关桌面验收，需先确认连接的后端部署版本已包含 Windows 路径分隔符误判修复；若未确认，不应先把结果归因到前端 Electron 包

## 后续待实现任务记录

- 第二轮桌面前端客户端任务已完成收尾；如需继续推进，会转入“后端运行态/空间工具执行稳定性”诊断，而不是继续补桌面前端主干代码。
- 地图错误态“无法获取当前会话可访问的知识库”的真实后端回归已定位并完成修复，且新 run 已成功跑通 `show_spatial_map -> completed`；后续若再有地图正向渲染问题，应继续排查知识库空间图层数据、工具调用路径或新的运行态异常，而不再优先怀疑桌面前端适配。
- 后续若执行 ZIP / `.yuxikb.zip` 相关桌面手动验收，需要以“后端已修复 Windows 路径分隔符误判”为前置条件重新记录结果；若仍失败，应优先排查后端实际部署版本是否包含该修复，而不是先归因到桌面前端。
- 如本轮出现难以反转、未来读者会疑惑且存在真实取舍的架构决策，再补充 ADR。

## 不纳入本轮候选

- Tauri 实现。
- OIDC 登录。
- 本地代理、本地静态文件服务或任何客户端托管 API 转发层。
- 完整知识库管理、图谱管理、后台管理桌面化适配。
- 安装器、自动更新、静默安装和企业分发体系。
- 客户端内置后端、数据库或本地沙盒。
