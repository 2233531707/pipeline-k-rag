"""知识库中间件 - 提供通用知识库工具"""

from langchain.agents.middleware import AgentMiddleware

from yuxi.agents.toolkits.kbs import get_common_kb_tools
from yuxi.utils.logging_config import logger


class KnowledgeBaseMiddleware(AgentMiddleware):
    """知识库中间件 - 提供通用知识库工具，其他没有任何作用

    提供通用知识库工具：
    - list_kbs: 列出用户可访问的知识库
    - get_mindmap: 获取指定知识库的思维导图
    - query_kb: 在指定知识库中检索
    - query_knowledge_graph: 查询知识图谱
    - find_kb_document: 在指定文件内定位关键词或正则模式
    - open_kb_document: 按 file_id 分段打开知识库文档
    - list_spatial_layers/query_spatial_features/show_spatial_map: 查询并展示空间数据
    """

    def __init__(self, enabled_tools: list[str] | None = None):
        super().__init__()
        all_kb_tools = get_common_kb_tools()
        if enabled_tools is None:
            self.kb_tools = all_kb_tools
        else:
            enabled_names = {name for name in enabled_tools if isinstance(name, str)}
            self.kb_tools = [tool for tool in all_kb_tools if tool.name in enabled_names]
        self.tools = self.kb_tools
        logger.debug(f"Initialized KnowledgeBaseMiddleware with {len(self.kb_tools)}/{len(all_kb_tools)} tools")
