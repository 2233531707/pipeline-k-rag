<template>
  <BaseToolCall :tool-call="toolCall" :hide-params="false">
    <template #header>
      <div class="sep-header">
        <span class="note">{{ operationLabel }}</span>
        <span class="separator" v-if="resourceLabel">|</span>
        <span class="description" v-if="resourceLabel">知识库: {{ resourceLabel }}</span>
        <span class="separator" v-if="resultSummary">|</span>
        <span class="description">{{ resultSummary }}</span>
      </div>
    </template>
    <template #result>
      <div class="graph-result-card">
        <!-- 加载状态 -->
        <div v-if="isLoading" class="state-loading">
          <Loader2 class="spin-icon" :size="16" />
          <span>查询知识图谱中...</span>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="errorMsg" class="state-error">
          <AlertCircle :size="16" />
          <span>{{ errorMsg }}</span>
        </div>

        <!-- 空状态 -->
        <div v-else-if="isEmpty" class="state-empty">
          <Info :size="16" />
          <span>未查询到匹配的图谱节点和关系</span>
        </div>

        <!-- 图谱结果 -->
        <template v-else>
          <!-- 默认折叠：摘要栏 -->
          <details class="graph-details">
            <summary class="graph-summary">
              <span class="summary-title">已查询知识图谱</span>
              <span class="summary-stat">{{ nodeCount }} 个节点</span>
              <span class="summary-divider">·</span>
              <span class="summary-stat">{{ edgeCount }} 条关系</span>
              <span v-if="hasHints" class="summary-divider">·</span>
              <span v-if="hasHints" class="summary-hint">已生成知识库增强检索提示</span>
            </summary>

            <div class="graph-expanded">
              <!-- 节点列表 -->
              <div v-if="nodes.length > 0" class="graph-section">
                <div class="section-title">节点 ({{ nodes.length }})</div>
                <div class="entity-list">
                  <div
                    v-for="(node, index) in nodes"
                    :key="`node-${index}`"
                    class="entity-item"
                  >
                    <div class="entity-header">
                      <span class="entity-name">{{ getNodeName(node) }}</span>
                      <span class="entity-type">{{ getNodeType(node) }}</span>
                    </div>
                    <div v-if="getNodeDesc(node)" class="entity-desc">
                      {{ truncateText(getNodeDesc(node), 200) }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- 关系列表 -->
              <div v-if="edges.length > 0" class="graph-section">
                <div class="section-title">关系 ({{ edges.length }})</div>
                <div class="relation-list">
                  <div
                    v-for="(edge, index) in edges"
                    :key="`edge-${index}`"
                    class="relation-item"
                  >
                    <span class="rel-node">{{ edge.source_id || '-' }}</span>
                    <span class="rel-arrow">→</span>
                    <span class="rel-type">{{ edge.type || '关联' }}</span>
                    <span class="rel-arrow">→</span>
                    <span class="rel-node">{{ edge.target_id || '-' }}</span>
                  </div>
                </div>
              </div>

              <!-- 增强检索提示 -->
              <div v-if="hasHints" class="graph-section hints-section">
                <div class="section-title">增强检索提示</div>
                <div v-if="hints.graph_entity_ids.length > 0" class="hint-row">
                  <span class="hint-label">图谱实体 ID:</span>
                  <span class="hint-value">{{ hints.graph_entity_ids.join(', ') }}</span>
                </div>
                <div v-if="hints.chunk_ids.length > 0" class="hint-row">
                  <span class="hint-label">关联 Chunk:</span>
                  <span class="hint-value">{{ hints.chunk_ids.join(', ') }}</span>
                </div>
                <div v-if="hints.file_ids.length > 0" class="hint-row">
                  <span class="hint-label">关联文件:</span>
                  <span class="hint-value">{{ hints.file_ids.join(', ') }}</span>
                </div>
                <div v-if="hints.keywords.length > 0" class="hint-row">
                  <span class="hint-label">关键词:</span>
                  <span class="hint-value">{{ hints.keywords.join(', ') }}</span>
                </div>
              </div>
            </div>
          </details>
        </template>
      </div>
    </template>
  </BaseToolCall>
</template>

<script setup>
import { computed } from 'vue'
import { AlertCircle, Info, Loader2 } from 'lucide-vue-next'
import BaseToolCall from '../BaseToolCall.vue'
import { useDatabaseStore } from '@/stores/database'

const props = defineProps({
  toolCall: {
    type: Object,
    required: true
  }
})

const databaseStore = useDatabaseStore()

const args = computed(() => {
  const value = props.toolCall.args || props.toolCall.function?.arguments
  if (!value) return {}
  if (typeof value === 'object') return value
  try {
    return JSON.parse(value)
  } catch {
    return {}
  }
})

const resultContent = computed(() => {
  const content = props.toolCall.tool_call_result?.content
  if (!content) return null
  return content
})

const operationLabel = computed(() => 'query_knowledge_graph 查询')

const resourceLabel = computed(() => {
  if (!args.value.kb_id) return null
  return databaseStore.getDatabaseNameById(args.value.kb_id) || args.value.kb_id
})

const isLoading = computed(() => {
  const content = resultContent.value
  if (!content) return true
  return false
})

const parsed = computed(() => {
  const content = resultContent.value
  if (!content || typeof content !== 'object') return null

  // 处理可能的嵌套: content.content 或 content 本身
  const payload = content.content || content
  if (typeof payload === 'string') {
    try {
      return JSON.parse(payload)
    } catch {
      return null
    }
  }
  return payload
})

const errorMsg = computed(() => {
  if (!parsed.value) return null
  return parsed.value.error || null
})

const isEmpty = computed(() => {
  if (!parsed.value || errorMsg.value) return false
  const p = parsed.value
  return (!p.nodes || p.nodes.length === 0) && (!p.edges || p.edges.length === 0)
})

const nodes = computed(() => parsed.value?.nodes || [])
const edges = computed(() => parsed.value?.edges || [])
const hints = computed(() => parsed.value?.retrieval_hints || {})

const nodeCount = computed(() => nodes.value.length)
const edgeCount = computed(() => edges.value.length)

const hasHints = computed(() => {
  const h = hints.value
  return (
    (h.graph_entity_ids && h.graph_entity_ids.length > 0) ||
    (h.chunk_ids && h.chunk_ids.length > 0) ||
    (h.file_ids && h.file_ids.length > 0) ||
    (h.keywords && h.keywords.length > 0)
  )
})

const resultSummary = computed(() => `${nodeCount.value} 节点, ${edgeCount.value} 关系`)

// ===== helpers =====
const getNodeName = (node) => node?.name || node?.properties?.name || '未命名'
const getNodeType = (node) => node?.type || node?.labels?.join(', ') || '未知类型'
const getNodeDesc = (node) => {
  const props = node?.properties || {}
  return props.description || props.content_preview || ''
}
const truncateText = (text, max) => {
  const s = String(text)
  return s.length <= max ? s : s.slice(0, max) + '…'
}
</script>

<style scoped lang="less">
.graph-result-card {
  background: var(--gray-0);
  border-radius: var(--radius-md, 8px);
  overflow: hidden;

  .state-loading,
  .state-error,
  .state-empty {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    font-size: 13px;
  }

  .state-loading {
    color: var(--gray-600);
  }

  .state-error {
    color: var(--color-danger, #d43a43);
    background: var(--color-danger-light, #ffeaec);
    border-radius: 6px;
  }

  .state-empty {
    color: var(--gray-600);
  }

  .spin-icon {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
}

.graph-details {
  .graph-summary {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 12px;
    cursor: pointer;
    font-size: 13px;
    color: var(--gray-700);
    background: var(--gray-25);
    list-style: none;

    &::-webkit-details-marker {
      display: none;
    }

    .summary-title {
      font-weight: 600;
      margin-right: 4px;
    }

    .summary-stat {
      color: var(--gray-600);
      font-size: 12px;
    }

    .summary-divider {
      color: var(--gray-400);
      font-size: 12px;
    }

    .summary-hint {
      color: var(--color-success, #0f9f6e);
      font-size: 12px;
    }
  }

  &[open] .graph-summary {
    border-bottom: 1px solid var(--gray-100);
  }
}

.graph-expanded {
  .graph-section {
    padding: 10px 12px;
    border-bottom: 1px solid var(--gray-100);

    &:last-child {
      border-bottom: none;
    }

    .section-title {
      font-size: 12px;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 8px;
    }
  }

  .hints-section {
    background: var(--gray-15);

    .hint-row {
      display: flex;
      gap: 6px;
      font-size: 12px;
      line-height: 1.6;
      margin-bottom: 4px;

      .hint-label {
        color: var(--gray-600);
        font-weight: 500;
        white-space: nowrap;
      }

      .hint-value {
        color: var(--gray-700);
        word-break: break-all;
        font-family: monospace;
        font-size: 11px;
      }
    }
  }
}

.entity-list {
  display: flex;
  flex-direction: column;
  gap: 6px;

  .entity-item {
    border: 1px solid var(--gray-150);
    border-radius: 6px;
    padding: 8px;

    .entity-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;

      .entity-name {
        font-size: 13px;
        color: var(--gray-700);
        font-weight: 600;
      }

      .entity-type {
        font-size: 11px;
        color: var(--gray-600);
        background: var(--gray-25);
        border-radius: 4px;
        padding: 1px 6px;
      }
    }

    .entity-desc {
      font-size: 12px;
      line-height: 1.5;
      color: var(--gray-700);
      white-space: pre-wrap;
    }
  }
}

.relation-list {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .relation-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--gray-700);

    .rel-node {
      font-family: monospace;
      font-size: 11px;
      background: var(--gray-25);
      border-radius: 4px;
      padding: 1px 6px;
      max-width: 120px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .rel-arrow {
      color: var(--gray-400);
    }

    .rel-type {
      color: var(--main-600);
      font-weight: 500;
    }
  }
}
</style>
