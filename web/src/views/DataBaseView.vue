<template>
  <div class="database-container layout-container">
    <PageHeader
      v-if="!props.embedded"
      title="知识库"
      :active-key="knowledgeActiveView"
      :tabs="knowledgeViewItems"
      :loading="dbState.listLoading"
      :show-border="true"
      aria-label="知识库视图切换"
    />

    <PageShoulder v-model:search="searchQuery" search-placeholder="搜索知识库...">
      <template #filters>
        <a-select
          v-model:value="typeFilter"
          style="width: 120px"
          placeholder="全部类型"
          allow-clear
        >
          <a-select-option :value="null">全部类型</a-select-option>
          <a-select-option v-for="t in kbTypes" :key="t" :value="t">
            {{ getKbTypeLabel(t) }}
          </a-select-option>
        </a-select>
      </template>
      <template #actions>
        <a-button
          class="lucide-icon-btn"
          @click="openCreateGroupModal()"
        >
          <FolderPlus :size="16" /> 新建分组
        </a-button>
        <a-button
          class="lucide-icon-btn"
          @click="state.openImportModal = true"
        >
          <Upload :size="16" /> 从迁移包导入
        </a-button>
        <a-button
          type="primary"
          class="lucide-icon-btn"
          :disabled="!kbTypes.length"
          @click="openCreateDatabaseModal()"
        >
          <Plus :size="16" /> 新建知识库
        </a-button>
      </template>
    </PageShoulder>

    <a-modal
      :open="state.openNewGroupModal"
      title="新建知识库分组"
      :confirm-loading="groupState.creating"
      @ok="handleCreateGroup"
      @cancel="cancelCreateGroup"
      destroyOnClose
    >
      <a-input
        v-model:value="newGroup.name"
        placeholder="分组名称"
        @pressEnter="handleCreateGroup"
      />
      <div class="field-hint">可选父分组</div>
      <a-select
        v-model:value="newGroup.parent_group_id"
        class="full-width"
        :options="knowledgeGroupOptions"
        allow-clear
        placeholder="顶级分组"
      />
    </a-modal>

    <a-modal
      :open="state.openNewDatabaseModel"
      title="新建知识库"
      :confirm-loading="dbState.creating"
      @ok="handleCreateDatabase"
      @cancel="cancelCreateDatabase"
      class="new-database-modal"
      width="800px"
      destroyOnClose
    >
      <div class="new-database-form">
        <!-- 知识库类型选择 -->
        <div class="form-section">
          <h3 class="section-title">知识库类型<span class="required-mark">*</span></h3>
          <div class="kb-type-cards">
            <div
              v-for="(typeInfo, typeKey) in orderedKbTypes"
              :key="typeKey"
              class="kb-type-card"
              :class="{ active: newDatabase.kb_type === typeKey }"
              :data-type="typeKey"
              @click="handleKbTypeChange(typeKey)"
            >
              <div class="card-header">
                <component :is="getKbTypeIcon(typeKey)" class="type-icon" />
                <span class="type-title">{{ getKbTypeLabel(typeKey) }}</span>
              </div>
              <div class="card-description">{{ getKbTypeDescription(typeInfo) }}</div>
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3 class="section-title">知识库名称<span class="required-mark">*</span></h3>
          <a-input v-model:value="newDatabase.name" placeholder="新建知识库名称" />
        </div>

        <div class="form-section">
          <h3 class="section-title">知识库分组</h3>
          <a-select
            v-model:value="newDatabase.group_id"
            class="full-width"
            :options="knowledgeGroupOptions"
          />
        </div>

        <div v-if="selectedKbTypeInfo?.requires_embedding_model" class="form-grid two-columns">
          <div class="form-section compact-section">
            <h3 class="section-title">嵌入模型</h3>
            <EmbeddingModelSelector
              v-model:value="newDatabase.embedding_model_spec"
              class="full-width"
              placeholder="请选择嵌入模型"
            />
          </div>

          <div class="form-section compact-section">
            <div class="chunk-preset-title-row">
              <h3 class="section-title">分块策略</h3>
              <a-tooltip :title="selectedPresetDescription">
                <QuestionCircleOutlined class="chunk-preset-help-icon" />
              </a-tooltip>
            </div>
            <a-select
              v-model:value="newDatabase.chunk_preset_id"
              :options="chunkPresetOptions"
              class="full-width"
            />
          </div>
        </div>

        <div v-if="createParamOptions.length" class="form-grid three-columns">
          <div
            v-for="field in createParamOptions"
            :key="field.key"
            class="form-section compact-section"
          >
            <h3 class="section-title">
              {{ field.label || field.key
              }}<span v-if="field.required" class="required-mark">*</span>
            </h3>
            <a-input-password
              v-if="field.type === 'password'"
              v-model:value="newDatabase.additional_params[field.key]"
              :placeholder="field.placeholder"
            />
            <a-input-number
              v-else-if="field.type === 'number'"
              v-model:value="newDatabase.additional_params[field.key]"
              :min="field.min"
              :max="field.max"
              :step="field.step"
              class="full-width"
            />
            <a-switch
              v-else-if="field.type === 'boolean'"
              v-model:checked="newDatabase.additional_params[field.key]"
            />
            <a-select
              v-else-if="field.type === 'select'"
              v-model:value="newDatabase.additional_params[field.key]"
              :options="field.options || []"
              class="full-width"
            />
            <a-input
              v-else
              v-model:value="newDatabase.additional_params[field.key]"
              :placeholder="field.placeholder"
            />
            <p v-if="field.description" class="field-hint">{{ field.description }}</p>
          </div>
        </div>

        <!-- 图谱抽取 Chat 模型预配置（仅 Milvus） -->
        <div
          v-if="newDatabase.kb_type === 'milvus'"
          class="form-section graph-build-section"
        >
          <div class="graph-build-header">
            <h3 class="section-title">知识图谱构建</h3>
            <a-switch
              v-model:checked="graphBuildEnabled"
              size="small"
            />
            <span class="graph-build-toggle-label">创建时配置知识图谱抽取</span>
          </div>

          <template v-if="graphBuildEnabled">
            <div class="form-grid two-columns">
              <div class="form-section compact-section">
                <h3 class="section-title">抽取器类型</h3>
                <a-input :value="'LLM'" disabled class="full-width" />
              </div>

              <div class="form-section compact-section">
                <h3 class="section-title">图谱抽取 Chat 模型<span class="required-mark">*</span></h3>
                <ChatModelSelector
                  v-model:value="graphBuildConfig.model_spec"
                  class="full-width"
                  placeholder="请选择图谱抽取 Chat 模型"
                />
              </div>

              <div class="form-section compact-section">
                <h3 class="section-title">Schema</h3>
                <a-textarea
                  v-model:value="graphBuildConfig.schema"
                  placeholder="可选，JSON 格式的抽取约束"
                  :rows="2"
                  class="full-width"
                />
              </div>

              <div class="form-section compact-section">
                <h3 class="section-title">并发队列数</h3>
                <a-input-number
                  v-model:value="graphBuildConfig.concurrency_count"
                  :min="1"
                  :max="1000"
                  class="full-width"
                />
              </div>
            </div>

            <div class="form-section compact-section">
              <h3 class="section-title">模型参数 JSON</h3>
              <a-textarea
                v-model:value="graphBuildConfig.model_params_json"
                placeholder='可选，如 {"temperature": 0.1}'
                :rows="2"
                class="full-width mono-textarea"
              />
            </div>
          </template>
        </div>

        <div class="form-section">
          <h3 class="section-title">知识库描述</h3>
          <p class="field-hint description-hint">
            在智能体流程中，这里的描述会作为工具的描述。智能体会根据知识库的标题和描述来选择合适的工具。所以这里描述的越详细，智能体越容易选择到合适的工具。
          </p>
          <AiTextarea
            v-model="newDatabase.description"
            :name="newDatabase.name"
            placeholder="新建知识库描述"
            :auto-size="{ minRows: 3, maxRows: 10 }"
          />
        </div>

        <!-- 共享配置 -->
        <div class="form-section compact-section">
          <h3 class="section-title">共享设置</h3>
          <ShareConfigForm
            ref="shareConfigFormRef"
            v-model="shareConfig"
            :auto-select-user-dept="true"
          />
        </div>
      </div>
      <template #footer>
        <a-button key="back" @click="cancelCreateDatabase">取消</a-button>
        <a-button
          key="submit"
          type="primary"
          :loading="dbState.creating"
          :disabled="!selectedKbTypeInfo"
          @click="handleCreateDatabase"
          >创建</a-button
        >
      </template>
    </a-modal>

    <!-- 从迁移包导入 Modal -->
    <a-modal
      :open="state.openImportModal"
      title="从迁移包导入"
      width="680px"
      :footer="null"
      destroyOnClose
      @cancel="cancelImport"
    >
      <div class="import-flow">
        <!-- 步骤1: 选择文件 -->
        <div class="import-step">
          <div class="step-indicator">1</div>
          <div class="step-content">
            <h4>选择 .yuxikb.zip 迁移包</h4>
            <input
              ref="fileInputRef"
              type="file"
              accept=".yuxikb.zip,.zip"
              style="display:none"
              @change="handleFileSelected"
            />
            <a-button @click="$refs.fileInputRef.click()" :disabled="importState.preflighting">
              <Upload :size="14" /> 选择文件
            </a-button>
            <span v-if="importState.fileName" class="file-name">{{ importState.fileName }}</span>
          </div>
        </div>

        <!-- 步骤2: 预检报告 -->
        <div v-if="importState.preflightReport" class="import-step">
          <div class="step-indicator">2</div>
          <div class="step-content">
            <h4>预检报告</h4>
            <div class="preflight-card">
              <div class="preflight-row">
                <span>名称：</span><strong>{{ importState.preflightReport.database_name }}</strong>
              </div>
              <div class="preflight-row">
                <span>文件数：</span><strong>{{ importState.preflightReport.files }}</strong>
              </div>
              <div class="preflight-row">
                <span>Chunk 数：</span><strong>{{ importState.preflightReport.chunks }}</strong>
              </div>
              <div class="preflight-row">
                <span>实体数：</span><strong>{{ importState.preflightReport.entities }}</strong>
              </div>
              <div class="preflight-row">
                <span>关系数：</span><strong>{{ importState.preflightReport.relationships }}</strong>
              </div>
              <div v-if="importState.preflightReport.warnings?.length" class="preflight-warnings">
                <p v-for="(w, i) in importState.preflightReport.warnings" :key="i" class="warning-text">
                  ⚠ {{ w }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤3: 配置 -->
        <div v-if="importState.preflightReport" class="import-step">
          <div class="step-indicator">3</div>
          <div class="step-content">
            <h4>导入配置</h4>
            <div class="form-grid">
              <div class="form-section compact-section">
                <h3 class="section-title">新知识库名称</h3>
                <a-input v-model:value="importConfig.targetName" placeholder="留空则使用原名称" />
              </div>
              <div v-if="importState.preflightReport.requires_embedding_model" class="form-section compact-section">
                <h3 class="section-title">嵌入模型<span class="required-mark">*</span></h3>
                <EmbeddingModelSelector
                  v-model:value="importConfig.embeddingModelSpec"
                  class="full-width"
                  placeholder="请选择嵌入模型"
                />
              </div>
              <div v-if="importState.preflightReport.requires_graph_chat_model" class="form-section compact-section">
                <h3 class="section-title">图谱抽取 Chat 模型</h3>
                <ChatModelSelector
                  v-model:value="importConfig.graphChatModelSpec"
                  class="full-width"
                  placeholder="请选择（可选）"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤4: 操作按钮 -->
        <div v-if="!importState.preflightReport" class="import-actions">
          <a-button @click="cancelImport">取消</a-button>
          <a-button
            type="primary"
            :loading="importState.preflighting"
            :disabled="!importState.file"
            @click="runPreflight"
          >
            开始预检
          </a-button>
        </div>
        <div v-else class="import-actions">
          <a-button @click="cancelImport">取消</a-button>
          <a-button
            type="primary"
            :loading="importState.importing"
            :disabled="!canStartImport"
            @click="startImport"
          >
            开始导入
          </a-button>
        </div>

        <div v-if="importState.taskId && !importState.importReport" class="import-step">
          <div class="step-indicator">4</div>
          <div class="step-content">
            <h4>正在导入</h4>
            <a-progress :percent="Math.round(importState.progress)" />
            <p class="field-hint">{{ importState.taskMessage || '等待后台任务执行' }}</p>
          </div>
        </div>

        <!-- 导入结果 -->
        <div v-if="importState.importReport" class="import-step">
          <div class="step-indicator">✓</div>
          <div class="step-content">
            <h4>导入完成</h4>
            <div class="preflight-card success-card">
              <div class="preflight-row"><span>知识库 ID：</span><strong>{{ importState.importReport.kb_id }}</strong></div>
              <div class="preflight-row"><span>名称：</span><strong>{{ importState.importReport.database_name }}</strong></div>
              <div class="preflight-row"><span>文件：</span><strong>{{ importState.importReport.files_uploaded }}</strong></div>
              <div class="preflight-row"><span>Chunk：</span><strong>{{ importState.importReport.chunks_imported }}</strong></div>
            </div>
          </div>
        </div>

        <!-- 错误 -->
        <div v-if="importState.error" class="import-error">
          <AlertCircle :size="16" /> {{ importState.error }}
        </div>
      </div>
    </a-modal>

    <!-- 加载状态 -->
    <div v-if="dbState.listLoading" class="loading-container">
      <a-spin size="large" />
      <p>正在加载知识库...</p>
    </div>

    <!-- 空状态显示 -->
    <ResourceEmptyState
      v-else-if="!databases || databases.length === 0"
      title="暂无知识库"
      description="创建知识库后，可以上传文件并配置检索、图谱和评估能力。"
      :icon="getKbTypeIcon('milvus')"
    >
      <template #actions>
        <a-button
          type="primary"
          size="large"
          class="lucide-icon-btn"
          :disabled="!kbTypes.length"
          @click="openCreateDatabaseModal()"
        >
          <template #icon>
            <Plus :size="16" />
          </template>
          创建知识库
        </a-button>
      </template>
    </ResourceEmptyState>

    <!-- 数据库列表 -->
    <div v-else class="knowledge-group-list">
      <section
        v-for="group in knowledgeGroupSections"
        :key="group.group_id"
        class="knowledge-group-section"
      >
        <KnowledgeGroupTree
          :group="group"
          :kb-types="kbTypes"
          :knowledge-group-options="knowledgeGroupOptions"
          :expanded-group-ids="expandedGroupIds"
          :card-subtitle="cardSubtitle"
          :card-tags="cardTags"
          :get-kb-type-icon="getKbTypeIcon"
          @toggle-group="toggleGroupExpanded"
          @create-group="openCreateGroupModal"
          @create-database="openCreateDatabaseModal"
          @rename-group="openRenameGroupModal"
          @delete-group="handleDeleteGroup"
          @move-database="handleMoveDatabase"
          @navigate-database="navigateToDatabase"
        />
      </section>
    </div>

    <a-modal
      :open="state.openRenameGroupModal"
      title="重命名知识库分组"
      :confirm-loading="groupState.renaming"
      @ok="handleRenameGroup"
      @cancel="cancelRenameGroup"
      destroyOnClose
    >
      <a-input
        v-model:value="editingGroup.name"
        placeholder="分组名称"
        @pressEnter="handleRenameGroup"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, reactive, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useConfigStore } from '@/stores/config'
import { useDatabaseStore } from '@/stores/database'
import { QuestionCircleOutlined } from '@ant-design/icons-vue'
import { Plus, Upload, AlertCircle, FolderPlus } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { databaseApi, typeApi } from '@/apis/knowledge_api'
import { taskerApi } from '@/apis/tasker'
import PageHeader from '@/components/shared/PageHeader.vue'
import PageShoulder from '@/components/shared/PageShoulder.vue'
import ResourceEmptyState from '@/components/shared/ResourceEmptyState.vue'
import EmbeddingModelSelector from '@/components/EmbeddingModelSelector.vue'
import ChatModelSelector from '@/components/ChatModelSelector.vue'
import ShareConfigForm from '@/components/ShareConfigForm.vue'
import ExtensionCardGrid from '@/components/extensions/ExtensionCardGrid.vue'
import InfoCard from '@/components/shared/InfoCard.vue'
import dayjs, { parseToShanghai } from '@/utils/time'
import AiTextarea from '@/components/AiTextarea.vue'
import { getKbTypeLabel, getKbTypeIcon, getKbTypeColor, kbUtils } from '@/utils/kb_utils'
import { CHUNK_PRESET_OPTIONS, getChunkPresetDescription } from '@/utils/chunk_presets'
import { DEFAULT_KNOWLEDGE_GROUP_ID, buildKnowledgeGroupSections } from '@/utils/knowledgeGroups'
import KnowledgeGroupTree from '@/components/knowledge/KnowledgeGroupTree.vue'

const route = useRoute()
const router = useRouter()
const configStore = useConfigStore()
const databaseStore = useDatabaseStore()

const props = defineProps({
  embedded: { type: Boolean, default: false }
})

// 使用 store 的状态
const { databases, state: dbState } = storeToRefs(databaseStore)

const knowledgeActiveView = 'documents'
const knowledgeViewItems = [
  { key: 'documents', label: '文档知识库', path: '/extensions?tab=knowledge' }
]

const kbTypes = computed(() => Object.keys(supportedKbTypes.value))
const searchQuery = ref('')
const typeFilter = ref(null)
const knowledgeGroups = ref([])
const groupState = reactive({ creating: false, renaming: false, movingDatabaseId: '' })
const newGroup = reactive({ name: '', parent_group_id: undefined })
const editingGroup = reactive({ group_id: '', name: '' })
const expandedGroupIds = ref(new Set([DEFAULT_KNOWLEDGE_GROUP_ID]))

const filteredDatabases = computed(() => {
  let list = databases.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(
      (db) =>
        db.name.toLowerCase().includes(q) ||
        (db.description && db.description.toLowerCase().includes(q))
    )
  }
  if (typeFilter.value) {
    list = list.filter((db) => (db.kb_type || 'milvus') === typeFilter.value)
  }
  return list
})

const knowledgeGroupSections = computed(() =>
  buildKnowledgeGroupSections(knowledgeGroups.value, filteredDatabases.value)
)

const knowledgeGroupOptions = computed(() =>
  knowledgeGroupSections.value.map((group) => ({
    label: group.name,
    value: group.group_id
  }))
)

const state = reactive({
  openNewDatabaseModel: false,
  openImportModal: false,
  openNewGroupModal: false,
  openRenameGroupModal: false
})

// 导入状态
const importState = reactive({
  file: null,
  fileName: '',
  preflighting: false,
  importing: false,
  preflightReport: null,
  importReport: null,
  taskId: null,
  progress: 0,
  taskMessage: '',
  error: null
})

const fileInputRef = ref(null)

const importConfig = reactive({
  targetName: '',
  embeddingModelSpec: configStore.config?.embed_model || '',
  graphChatModelSpec: ''
})

const canStartImport = computed(() => {
  if (importState.preflightReport?.requires_embedding_model && !importConfig.embeddingModelSpec) {
    return false
  }
  return true
})

let importRunToken = 0
const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds))

const cancelImport = () => {
  importRunToken += 1
  state.openImportModal = false
  importState.file = null
  importState.fileName = ''
  importState.preflighting = false
  importState.importing = false
  importState.preflightReport = null
  importState.importReport = null
  importState.taskId = null
  importState.progress = 0
  importState.taskMessage = ''
  importState.error = null
  importConfig.targetName = ''
  importConfig.embeddingModelSpec = configStore.config?.embed_model || ''
  importConfig.graphChatModelSpec = ''
}

const handleFileSelected = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  importState.file = file
  importState.fileName = file.name
  importState.preflightReport = null
  importState.importReport = null
  importState.taskId = null
  importState.progress = 0
  importState.taskMessage = ''
  importState.error = null
}

const runPreflight = async () => {
  if (!importState.file) return
  importState.preflighting = true
  importState.error = null
  try {
    const formData = new FormData()
    formData.append('file', importState.file)
    const response = await databaseApi.preflightImport(formData)
    if (response?.preflight_passed !== undefined) {
      importState.preflightReport = response
    } else {
      importState.error = response?.detail || '预检失败'
    }
  } catch (e) {
    importState.error = e?.detail || e?.message || '预检请求失败'
  } finally {
    importState.preflighting = false
  }
}

const waitForImportTask = async (taskId, runToken) => {
  const deadline = Date.now() + 30 * 60 * 1000
  while (Date.now() < deadline && runToken === importRunToken) {
    const task = await databaseApi.getPortableImportStatus(taskId)
    importState.progress = Number(task?.progress || 0)
    importState.taskMessage = task?.message || ''

    if (task?.status === 'success') {
      return task.result
    }
    if (task?.status === 'failed' || task?.status === 'cancelled') {
      throw new Error(task.error || task.message || '迁移导入任务失败')
    }
    await wait(1000)
  }
  if (runToken !== importRunToken) {
    return null
  }
  throw new Error('迁移导入等待超时，请在任务中心查看状态')
}

const startImport = async () => {
  if (!importState.file) return
  const runToken = ++importRunToken
  importState.importing = true
  importState.error = null
  try {
    const response = await databaseApi.importPortablePackage({
      file: importState.file,
      target_name: importConfig.targetName,
      embedding_model_spec: importConfig.embeddingModelSpec,
      graph_chat_model_spec: importConfig.graphChatModelSpec || undefined
    })
    if (!response?.task_id) throw new Error(response?.detail || '导入任务提交失败')

    importState.taskId = response.task_id
    taskerApi.fetchTaskDetail(response.task_id).catch(() => {})
    const report = await waitForImportTask(response.task_id, runToken)
    if (!report || runToken !== importRunToken) return

    importState.importReport = report
    importState.progress = 100
    importState.taskMessage = '导入完成'
    await databaseStore.loadDatabases()
  } catch (e) {
    if (runToken === importRunToken) {
      importState.error = e?.detail || e?.message || '导入请求失败'
    }
  } finally {
    if (runToken === importRunToken) importState.importing = false
  }
}

const createDefaultShareConfig = () => ({
  access_level: 'global',
  department_ids: [],
  user_uids: []
})

const shareConfig = ref(createDefaultShareConfig())
const shareConfigFormRef = ref(null)

// 图谱预配置状态
const graphBuildEnabled = ref(false)
const graphBuildConfig = reactive({
  model_spec: '',
  schema: '',
  concurrency_count: 1,
  model_params_json: '{}'
})

const chunkPresetOptions = CHUNK_PRESET_OPTIONS.map(({ label, value }) => ({ label, value }))

const createEmptyDatabaseForm = () => ({
  name: '',
  description: '',
  group_id: DEFAULT_KNOWLEDGE_GROUP_ID,
  embedding_model_spec: configStore.config?.embed_model,
  kb_type: '',
  storage: '',
  chunk_preset_id: 'general',
  additional_params: {}
})

const newDatabase = reactive(createEmptyDatabaseForm())

const selectedPresetDescription = computed(() =>
  getChunkPresetDescription(newDatabase.chunk_preset_id)
)

// 支持的知识库类型
const supportedKbTypes = ref({})

// 有序的知识库类型
const orderedKbTypes = computed(() => supportedKbTypes.value)

const selectedKbTypeInfo = computed(() => supportedKbTypes.value[newDatabase.kb_type] || null)

const createParamOptions = computed(() => selectedKbTypeInfo.value?.create_params?.options || [])

const getKbTypeDescription = (typeInfo) => typeInfo?.description || ''

const resetCreateParamValues = () => {
  newDatabase.additional_params = {}
  for (const field of createParamOptions.value) {
    if ('default' in field) {
      newDatabase.additional_params[field.key] = field.default
    } else if (field.type === 'boolean') {
      newDatabase.additional_params[field.key] = false
    } else {
      newDatabase.additional_params[field.key] = ''
    }
  }
}

// 加载支持的知识库类型
const loadSupportedKbTypes = async () => {
  try {
    const data = await typeApi.getKnowledgeBaseTypes()
    supportedKbTypes.value = data.kb_types || {}
    newDatabase.kb_type = kbTypes.value[0] || ''
    resetCreateParamValues()
  } catch (error) {
    console.error('加载知识库类型失败:', error)
    supportedKbTypes.value = {}
    newDatabase.kb_type = ''
    resetCreateParamValues()
    message.error('加载知识库类型失败，请稍后重试')
  }
}

const loadKnowledgeGroups = async () => {
  try {
    const data = await databaseApi.getGroups()
    knowledgeGroups.value = data.groups || []
  } catch (error) {
    console.error('加载知识库分组失败:', error)
    knowledgeGroups.value = []
    message.error('加载知识库分组失败，请稍后重试')
  }
}

const cancelCreateGroup = () => {
  state.openNewGroupModal = false
  newGroup.name = ''
  newGroup.parent_group_id = undefined
}

const openCreateGroupModal = (parentGroupId = undefined) => {
  state.openNewGroupModal = true
  newGroup.parent_group_id = parentGroupId
}

const handleCreateGroup = async () => {
  const name = newGroup.name.trim()
  if (!name) {
    message.error('分组名称不能为空')
    return
  }
  groupState.creating = true
  try {
    const group = await databaseApi.createGroup({
      name,
      parent_group_id: newGroup.parent_group_id || undefined
    })
    await loadKnowledgeGroups()
    toggleGroupExpanded(group.parent_group_id || DEFAULT_KNOWLEDGE_GROUP_ID, true)
    toggleGroupExpanded(group.group_id, true)
    newDatabase.group_id = group.group_id
    cancelCreateGroup()
    message.success('分组创建成功')
  } catch (error) {
    message.error(error.message || '分组创建失败')
  } finally {
    groupState.creating = false
  }
}

const openRenameGroupModal = (group) => {
  editingGroup.group_id = group.group_id
  editingGroup.name = group.name
  state.openRenameGroupModal = true
}

const cancelRenameGroup = () => {
  state.openRenameGroupModal = false
  editingGroup.group_id = ''
  editingGroup.name = ''
}

const handleRenameGroup = async () => {
  const name = editingGroup.name.trim()
  if (!name) {
    message.error('分组名称不能为空')
    return
  }
  groupState.renaming = true
  try {
    await databaseApi.renameGroup(editingGroup.group_id, { name })
    await loadKnowledgeGroups()
    cancelRenameGroup()
    message.success('分组已重命名')
  } catch (error) {
    message.error(error.message || '分组重命名失败')
  } finally {
    groupState.renaming = false
  }
}

const handleDeleteGroup = async (group) => {
  try {
    await databaseApi.deleteGroup(group.group_id)
    await loadKnowledgeGroups()
    message.success('分组已删除')
  } catch (error) {
    message.error(error.message || '分组删除失败')
  }
}

const handleMoveDatabase = async (database, groupId) => {
  if ((database.group_id || DEFAULT_KNOWLEDGE_GROUP_ID) === groupId) return
  groupState.movingDatabaseId = database.kb_id
  try {
    await databaseApi.updateDatabase(database.kb_id, {
      name: database.name,
      description: database.description || '',
      group_id: groupId
    })
    await databaseStore.loadDatabases()
    message.success('知识库已移动')
  } catch (error) {
    message.error(error.message || '知识库移动失败')
  } finally {
    groupState.movingDatabaseId = ''
  }
}

const toggleGroupExpanded = (groupId, forceExpanded = null) => {
  const next = new Set(expandedGroupIds.value)
  const shouldExpand = forceExpanded === null ? !next.has(groupId) : forceExpanded
  if (shouldExpand) {
    next.add(groupId)
  } else {
    next.delete(groupId)
  }
  expandedGroupIds.value = next
}

const resetNewDatabase = () => {
  Object.assign(newDatabase, createEmptyDatabaseForm())
  newDatabase.kb_type = kbTypes.value[0] || ''
  resetCreateParamValues()
  shareConfig.value = createDefaultShareConfig()
  graphBuildEnabled.value = false
  Object.assign(graphBuildConfig, {
    model_spec: '',
    schema: '',
    concurrency_count: 1,
    model_params_json: '{}'
  })
}

const cancelCreateDatabase = () => {
  state.openNewDatabaseModel = false
  resetNewDatabase()
}

const openCreateDatabaseModal = (groupId = DEFAULT_KNOWLEDGE_GROUP_ID) => {
  state.openNewDatabaseModel = true
  newDatabase.group_id = groupId
}

// 格式化创建时间
const formatCreatedTime = (createdAt) => {
  if (!createdAt) return ''
  const parsed = parseToShanghai(createdAt)
  if (!parsed) return ''

  const today = dayjs().startOf('day')
  const createdDay = parsed.startOf('day')
  const diffInDays = today.diff(createdDay, 'day')

  if (diffInDays === 0) {
    return '今天创建'
  }
  if (diffInDays === 1) {
    return '昨天创建'
  }
  if (diffInDays < 7) {
    return `${diffInDays} 天前创建`
  }
  if (diffInDays < 30) {
    const weeks = Math.floor(diffInDays / 7)
    return `${weeks} 周前创建`
  }
  if (diffInDays < 365) {
    const months = Math.floor(diffInDays / 30)
    return `${months} 个月前创建`
  }
  const years = Math.floor(diffInDays / 365)
  return `${years} 年前创建`
}

// 处理知识库类型改变
const handleKbTypeChange = (type) => {
  console.log('知识库类型改变:', type)
  resetNewDatabase()
  newDatabase.kb_type = type
  resetCreateParamValues()
}

// 构建请求数据（只负责表单数据转换）
const buildRequestData = () => {
  const requestData = {
    database_name: newDatabase.name.trim(),
    description: newDatabase.description?.trim() || '',
    kb_type: newDatabase.kb_type,
    group_id: newDatabase.group_id || DEFAULT_KNOWLEDGE_GROUP_ID,
    additional_params: {}
  }

  if (selectedKbTypeInfo.value?.requires_embedding_model) {
    requestData.embedding_model_spec =
      newDatabase.embedding_model_spec || configStore.config.embed_model
    requestData.additional_params.chunk_preset_id = newDatabase.chunk_preset_id || 'general'
  }

  requestData.share_config = {
    access_level: shareConfig.value.access_level,
    department_ids:
      shareConfig.value.access_level === 'department' ? shareConfig.value.department_ids || [] : [],
    user_uids: shareConfig.value.access_level === 'user' ? shareConfig.value.user_uids || [] : []
  }

  // 根据类型添加特定配置
  if (['milvus'].includes(newDatabase.kb_type)) {
    if (newDatabase.storage) {
      requestData.additional_params.storage = newDatabase.storage
    }
    // 图谱抽取预配置
    if (graphBuildEnabled.value && graphBuildConfig.model_spec) {
      let modelParams = {}
      try {
        if (graphBuildConfig.model_params_json && graphBuildConfig.model_params_json.trim()) {
          modelParams = JSON.parse(graphBuildConfig.model_params_json)
        }
      } catch {
        message.warning('模型参数 JSON 格式无效，将使用空对象')
      }
      requestData.graph_build_config = {
        enabled: true,
        extractor_type: 'llm',
        extractor_options: {
          model_spec: graphBuildConfig.model_spec,
          schema: graphBuildConfig.schema || '',
          concurrency_count: graphBuildConfig.concurrency_count || 1,
          model_params: modelParams
        }
      }
    }
  }

  for (const field of createParamOptions.value) {
    const value = newDatabase.additional_params[field.key]
    requestData.additional_params[field.key] = typeof value === 'string' ? value.trim() : value
  }

  return requestData
}

// 创建按钮处理
const handleCreateDatabase = async () => {
  if (!selectedKbTypeInfo.value) {
    message.error('知识库类型加载失败，无法创建知识库')
    return
  }

  for (const field of createParamOptions.value) {
    if (!field.required) continue
    const value = newDatabase.additional_params[field.key]
    if (value === undefined || value === null || (typeof value === 'string' && !value.trim())) {
      message.error(`请填写${field.label || field.key}`)
      return
    }
  }

  if (shareConfigFormRef.value) {
    const validation = shareConfigFormRef.value.validate()
    if (!validation.valid) {
      message.warning(validation.message)
      return
    }
  }

  const requestData = buildRequestData()
  try {
    await databaseStore.createDatabase(requestData)
    resetNewDatabase()
    state.openNewDatabaseModel = false
  } catch {
    // 错误已在 store 中处理
  }
}

const cardSubtitle = (database) => {
  const parts = []
  if (database.created_at) {
    parts.push(formatCreatedTime(database.created_at))
  }
  if (!kbUtils.isReadOnlyDatabase(database)) {
    parts.push(`${database.row_count || 0} 文件`)
  }
  return parts.join(' · ')
}

const cardTags = (database) => {
  const tags = [
    {
      name: getKbTypeLabel(database.kb_type || 'milvus'),
      color: getKbTypeColor(database.kb_type || 'milvus')
    }
  ]
  if (database.embedding_model_spec) {
    tags.push({
      name: database.embedding_model_spec.split('/').slice(-1)[0],
      color: 'blue'
    })
  }
  return tags
}

const navigateToDatabase = (database) => {
  router.push({ path: `/extensions/knowledgebase/${database.kb_id}` })
}

watch(
  () => route.path,
  (newPath) => {
    if (newPath === '/extensions' && route.query.tab === 'knowledge') {
      databaseStore.loadDatabases()
    }
  }
)

onMounted(() => {
  loadSupportedKbTypes()
  loadKnowledgeGroups()
  databaseStore.loadDatabases()
})

onBeforeUnmount(() => {
  importRunToken += 1
})

defineExpose({
  loading: computed(() => dbState.value.listLoading)
})
</script>

<style lang="less" scoped>
.new-database-modal {
  .new-database-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .form-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form-section.compact-section {
    gap: 6px;
  }

  .form-grid {
    display: grid;
    gap: 16px;

    &.two-columns {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    &.three-columns {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    @media (max-width: 768px) {
      &.two-columns,
      &.three-columns {
        grid-template-columns: 1fr;
      }
    }
  }

  .full-width {
    width: 100%;
  }

  .compact-model-selector {
    height: 40px;
  }

  .section-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--gray-800);
  }

  .required-mark {
    margin-left: 2px;
    color: var(--color-error-500);
  }

  .field-hint {
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
    color: var(--gray-600);
  }

  .description-hint {
    margin-top: -2px;
  }

  .chunk-preset-title-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .chunk-preset-help-icon {
    color: var(--gray-500);
    cursor: help;
    font-size: 14px;
  }

  .kb-type-guide {
    margin: 12px 0;
  }

  .privacy-config {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
  }

  .kb-type-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 4px 0 0;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .kb-type-card {
      border: 1px solid var(--gray-150);
      border-radius: 12px;
      padding: 14px;
      cursor: pointer;
      transition: all 0.2s ease;
      background: var(--gray-0);
      position: relative;
      overflow: hidden;

      &:hover {
        border-color: var(--main-color);
      }

      &.active {
        border-color: var(--main-color);
        background: var(--main-10);
        box-shadow: 0 0 0 1px var(--main-20);

        .type-icon {
          color: var(--main-color);
        }
      }

      .card-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;

        .type-icon {
          width: 20px;
          height: 20px;
          color: var(--main-color);
          flex-shrink: 0;
        }

        .type-title {
          font-size: 15px;
          font-weight: 600;
          color: var(--gray-800);
        }
      }

      .card-description {
        font-size: 13px;
        color: var(--gray-600);
        line-height: 1.5;
        margin-bottom: 0;
      }

      .deprecated-badge {
        background: var(--color-error-100);
        color: var(--color-error-600);
        font-size: 10px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: auto;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        cursor: help;
        transition: all 0.2s ease;

        &:hover {
          background: var(--color-error-200);
          color: var(--color-error-700);
        }
      }
    }
  }

  .chunk-config {
    margin-top: 16px;
    padding: 12px 16px;
    background-color: var(--gray-25);
    border-radius: 6px;
    border: 1px solid var(--gray-150);

    h3 {
      margin-top: 0;
      margin-bottom: 12px;
      color: var(--gray-800);
    }

    .chunk-params {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .param-row {
        display: flex;
        align-items: center;
        gap: 12px;

        label {
          min-width: 80px;
          font-weight: 500;
          color: var(--gray-700);
        }

        .param-hint {
          font-size: 12px;
          color: var(--gray-500);
          margin-left: 8px;
        }
      }
    }
  }
}

.database-container {
  padding: 0;
}

.knowledge-group-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 16px 0 32px;
}

.knowledge-group-section {
  border-top: 1px solid var(--gray-150);
}

.knowledge-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px var(--page-padding) 0;
}

.knowledge-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: var(--gray-700);

  h2 {
    margin: 0;
    color: var(--gray-900);
    font-size: 16px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    min-width: 24px;
    height: 22px;
    padding: 0 8px;
    border-radius: 999px;
    background: var(--gray-100);
    color: var(--gray-600);
    font-size: 12px;
    line-height: 22px;
    text-align: center;
  }
}

.knowledge-group-empty {
  padding: 28px var(--page-padding);
}

.loading-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 300px;
  gap: 16px;
}

.new-database-modal {
  h3 {
    margin-top: 10px;
  }
}
</style>
