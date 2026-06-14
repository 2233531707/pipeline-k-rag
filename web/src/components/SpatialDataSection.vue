<template>
  <div class="spatial-section">
    <div class="spatial-header">
      <div>
        <div class="section-title">空间数据</div>
        <div class="section-subtitle">
          支持 GeoJSON、Shapefile ZIP 与 GPKG；图层数据存储在 PostGIS。
        </div>
      </div>
      <a-space>
        <a-button size="small" :loading="loading" @click="loadAll">
          <template #icon><RefreshCw :size="14" /></template>
          刷新
        </a-button>
        <a-button type="primary" size="small" @click="$emit('upload')">
          <template #icon><Upload :size="14" /></template>
          上传空间数据
        </a-button>
      </a-space>
    </div>

    <div v-if="loading" class="loading-state">
      <a-spin size="small" />
      <span>加载空间数据...</span>
    </div>

    <div v-else class="spatial-workspace">
      <aside class="management-card">
        <a-segmented v-model:value="activeMode" :options="modeOptions" block />

        <div v-if="activeMode === 'layers'" class="management-panel">
          <div class="panel-heading">
            <span>图层管理</span>
            <a-tag>{{ layers.length }}</a-tag>
          </div>
          <a-empty v-if="layers.length === 0" description="暂无空间图层">
            <a-button type="primary" size="small" @click="$emit('upload')">上传空间数据</a-button>
          </a-empty>
          <div v-else class="layer-list">
            <div
              v-for="layer in layers"
              :key="layer.layer_id"
              class="layer-list-item"
              :class="{ active: selectedLayerId === layer.layer_id }"
              role="button"
              tabindex="0"
              @click="selectLayer(layer.layer_id)"
              @keydown.enter="selectLayer(layer.layer_id)"
            >
              <div class="layer-list-main">
                <strong>{{ layer.name }}</strong>
                <span>{{ layer.geometry_type || 'Geometry' }} · {{ layer.feature_count || 0 }} 要素</span>
              </div>
              <a-button
                type="text"
                size="small"
                danger
                aria-label="删除图层"
                @click.stop="confirmDeleteLayer(layer)"
              >
                <Trash2 :size="14" />
              </a-button>
            </div>
          </div>
        </div>

        <div v-else-if="activeMode === 'compositions'" class="management-panel">
          <div class="panel-heading">
            <span>图层组合</span>
            <a-button type="text" size="small" @click="startNewComposition">
              <Plus :size="14" /> 新建
            </a-button>
          </div>
          <a-select
            v-model:value="selectedCompositionId"
            allow-clear
            class="full-width"
            placeholder="选择已有组合"
            @change="selectComposition"
          >
            <a-select-option
              v-for="composition in compositions"
              :key="composition.composition_id"
              :value="composition.composition_id"
            >
              {{ composition.name }}
            </a-select-option>
          </a-select>

          <div class="composition-editor">
            <a-input v-model:value="compositionDraft.name" placeholder="组合名称" />
            <div class="available-layers">
              <a-checkbox
                v-for="layer in layers"
                :key="layer.layer_id"
                :checked="compositionLayerIds.has(layer.layer_id)"
                @change="(event) => toggleCompositionLayer(layer, event.target.checked)"
              >
                {{ layer.name }}
              </a-checkbox>
            </div>

            <div v-if="compositionDraft.items.length" class="composition-items">
              <div
                v-for="(item, index) in compositionDraft.items"
                :key="item.layer_id"
                class="composition-item"
              >
                <div class="composition-item-title">
                  <a-switch v-model:checked="item.visible" size="small" />
                  <span>{{ layerName(item.layer_id) }}</span>
                  <div class="order-actions">
                    <button
                      type="button"
                      :disabled="index === 0"
                      @click="moveCompositionItem(index, -1)"
                    >
                      <ChevronUp :size="13" />
                    </button>
                    <button
                      type="button"
                      :disabled="index === compositionDraft.items.length - 1"
                      @click="moveCompositionItem(index, 1)"
                    >
                      <ChevronDown :size="13" />
                    </button>
                  </div>
                </div>
                <div class="opacity-row">
                  <span>透明度</span>
                  <a-slider v-model:value="item.opacity" :min="0" :max="1" :step="0.1" />
                </div>
              </div>
            </div>

            <a-space>
              <a-button
                type="primary"
                size="small"
                :loading="compositionSaving"
                @click="saveComposition"
              >
                保存组合
              </a-button>
              <a-button
                v-if="selectedCompositionId"
                danger
                size="small"
                @click="confirmDeleteComposition"
              >
                删除
              </a-button>
            </a-space>
          </div>
        </div>

        <div v-else class="management-panel analysis-panel">
          <div class="panel-heading"><span>派生空间分析</span></div>
          <a-select v-model:value="analysisForm.layerAId" placeholder="图层 A" class="full-width">
            <a-select-option v-for="layer in layers" :key="layer.layer_id" :value="layer.layer_id">
              {{ layer.name }}
            </a-select-option>
          </a-select>
          <a-select v-model:value="analysisForm.operation" class="full-width">
            <a-select-option value="intersection">交集 intersection</a-select-option>
            <a-select-option value="union">合并 union</a-select-option>
            <a-select-option value="difference">差集 difference</a-select-option>
          </a-select>
          <a-select v-model:value="analysisForm.layerBId" placeholder="图层 B" class="full-width">
            <a-select-option
              v-for="layer in layers"
              :key="layer.layer_id"
              :value="layer.layer_id"
              :disabled="layer.layer_id === analysisForm.layerAId"
            >
              {{ layer.name }}
            </a-select-option>
          </a-select>
          <a-input v-model:value="analysisForm.targetName" placeholder="派生图层名称" />
          <a-button type="primary" :loading="analysisRunning" @click="runAnalysis">
            <Play :size="14" /> 开始分析
          </a-button>
          <p class="panel-hint">分析在后台任务中执行，结果写入新图层，不修改源图层。</p>
        </div>
      </aside>

      <section class="preview-column">
        <div class="stats-row">
          <div class="stat-card">
            <span>数据源</span>
            <strong>{{ sources.length }}</strong>
          </div>
          <div class="stat-card">
            <span>图层</span>
            <strong>{{ layers.length }}</strong>
          </div>
          <div class="stat-card">
            <span>预览范围</span>
            <strong class="bbox-text">{{ formatBbox(featureBounds) }}</strong>
          </div>
        </div>

        <div class="map-and-detail">
          <div class="map-card">
            <div class="map-toolbar">
              <span>{{ previewTitle }}</span>
              <div class="map-toolbar-actions">
                <span v-if="previewTruncated" class="preview-warning">
                  仅预览前 {{ previewLimit }} 条/层、最多 {{ maxPreviewLayers }} 层
                </span>
                <span class="map-interaction-hint">拖拽平移 · 滚轮或双指缩放</span>
                <a-button size="small" aria-label="缩小地图" @click="zoomMap(0.8)">
                  <Minus :size="14" />
                </a-button>
                <a-button size="small" aria-label="放大地图" @click="zoomMap(1.25)">
                  <Plus :size="14" />
                </a-button>
                <a-button size="small" aria-label="复位地图" @click="resetMapView">
                  <RotateCcw :size="14" />
                </a-button>
              </div>
            </div>
            <div
              ref="mapCanvasRef"
              class="map-canvas"
              :class="{ dragging: mapDragging }"
              @wheel.prevent="onMapWheel"
              @pointerdown="onMapPointerDown"
              @pointermove="onMapPointerMove"
              @pointerup="onMapPointerUp"
              @pointercancel="onMapPointerUp"
              @dblclick.prevent="onMapDoubleClick"
            >
              <a-spin v-if="featuresLoading" size="small" />
              <svg
                v-else-if="renderItems.length"
                ref="previewSvgRef"
                class="preview-svg"
                viewBox="0 0 720 420"
              >
                <rect x="0" y="0" width="720" height="420" rx="12" class="map-bg" />
                <g :transform="mapTransform">
                  <path
                    v-for="item in polygonItems"
                    :key="item.id"
                    :d="item.path"
                    class="geom-polygon"
                    :style="{
                      fill: item.color,
                      fillOpacity: item.opacity,
                      stroke: item.color
                    }"
                    @click.stop="handleFeatureClick(item.feature, item.layerName)"
                  />
                  <polyline
                    v-for="item in lineItems"
                    :key="item.id"
                    :points="item.points"
                    class="geom-line"
                    :style="{ stroke: item.color, strokeOpacity: item.opacity }"
                    @click.stop="handleFeatureClick(item.feature, item.layerName)"
                  />
                  <circle
                    v-for="item in pointItems"
                    :key="item.id"
                    :cx="item.x"
                    :cy="item.y"
                    r="4"
                    class="geom-point"
                    :style="{ fill: item.color, fillOpacity: item.opacity }"
                    @click.stop="handleFeatureClick(item.feature, item.layerName)"
                  />
                </g>
              </svg>
              <a-empty v-else description="请选择图层或图层组合进行预览" />
            </div>
          </div>

          <div class="detail-card">
            <div class="detail-title">
              要素属性
              <span v-if="selectedFeatureLayer">{{ selectedFeatureLayer }}</span>
            </div>
            <a-empty v-if="!selectedFeature" description="点击地图中的要素查看属性" />
            <a-table
              v-else
              size="small"
              :pagination="{ pageSize: 8, size: 'small' }"
              :columns="propertyColumns"
              :data-source="selectedFeatureProperties"
              :row-key="(row) => row.key"
            />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  ChevronDown,
  ChevronUp,
  Layers,
  Minus,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  ScanSearch,
  Trash2,
  Upload
} from 'lucide-vue-next'
import { spatialApi } from '@/apis/knowledge_api'
import { taskerApi } from '@/apis/tasker'
import { useTaskerStore } from '@/stores/tasker'

const props = defineProps({
  kbId: {
    type: String,
    required: true
  }
})

defineEmits(['upload'])

const previewLimit = 500
const maxPreviewLayers = 10
const layerColors = ['#1685ff', '#0f9f6e', '#c97a05', '#d43a43', '#7c3aed', '#0891b2']
const modeOptions = [
  { label: '图层', value: 'layers', icon: Layers },
  { label: '叠加', value: 'compositions', icon: Layers },
  { label: '分析', value: 'analysis', icon: ScanSearch }
]

const taskerStore = useTaskerStore()
const loading = ref(false)
const featuresLoading = ref(false)
const compositionSaving = ref(false)
const analysisRunning = ref(false)
const activeMode = ref('layers')
const sources = ref([])
const layers = ref([])
const compositions = ref([])
const selectedLayerId = ref(null)
const selectedCompositionId = ref(null)
const loadedLayerFeatures = ref({})
const selectedFeature = ref(null)
const selectedFeatureLayer = ref('')
const mapCanvasRef = ref(null)
const previewSvgRef = ref(null)
const mapDragging = ref(false)
const mapView = reactive({ scale: 1, x: 0, y: 0 })
const mapPointers = new Map()
let mapDragDistance = 0
let suppressFeatureClick = false
let analysisRunToken = 0

const compositionDraft = reactive({
  name: '',
  items: []
})

const analysisForm = reactive({
  layerAId: null,
  layerBId: null,
  operation: 'intersection',
  targetName: ''
})

const propertyColumns = [
  { title: '字段', dataIndex: 'key', width: 140 },
  { title: '值', dataIndex: 'value' }
]

const layerMap = computed(() =>
  Object.fromEntries(layers.value.map((layer) => [layer.layer_id, layer]))
)
const selectedLayer = computed(() => layerMap.value[selectedLayerId.value] || null)
const selectedComposition = computed(() =>
  compositions.value.find((item) => item.composition_id === selectedCompositionId.value)
)
const compositionLayerIds = computed(
  () => new Set(compositionDraft.items.map((item) => item.layer_id))
)

const activePreviewLayers = computed(() => {
  if (activeMode.value === 'compositions' && compositionDraft.items.length) {
    return compositionDraft.items.slice(0, maxPreviewLayers).flatMap((item, index) => {
      const layer = layerMap.value[item.layer_id]
      if (!layer || !item.visible) return []
      return [
        {
          ...layer,
          ...item,
          color: item.style_override?.color || layerColors[index % layerColors.length],
          features: loadedLayerFeatures.value[item.layer_id] || []
        }
      ]
    })
  }
  if (!selectedLayer.value) return []
  return [
    {
      ...selectedLayer.value,
      visible: true,
      opacity: 0.8,
      color: layerColors[0],
      features: loadedLayerFeatures.value[selectedLayer.value.layer_id] || []
    }
  ]
})

const previewTitle = computed(() => {
  if (activeMode.value === 'compositions') {
    return compositionDraft.name || selectedComposition.value?.name || '图层组合预览'
  }
  return selectedLayer.value?.name || '图层预览'
})

const previewTruncated = computed(
  () =>
    activePreviewLayers.value.length >= maxPreviewLayers ||
    activePreviewLayers.value.some((layer) => Number(layer.feature_count || 0) > previewLimit)
)

const featureBounds = computed(() => {
  let bounds = null
  for (const layer of activePreviewLayers.value) {
    const bbox = layer.bbox
    if (!Array.isArray(bbox) || bbox.length !== 4) continue
    bounds = bounds
      ? [
          Math.min(bounds[0], bbox[0]),
          Math.min(bounds[1], bbox[1]),
          Math.max(bounds[2], bbox[2]),
          Math.max(bounds[3], bbox[3])
        ]
      : bbox.map(Number)
  }
  return bounds
})

const renderItems = computed(() => {
  if (!featureBounds.value) return []
  return activePreviewLayers.value.flatMap((layer) =>
    (layer.features || []).flatMap((feature) =>
      geometryToItems(feature, featureBounds.value, layer)
    )
  )
})
const polygonItems = computed(() => renderItems.value.filter((item) => item.kind === 'polygon'))
const lineItems = computed(() => renderItems.value.filter((item) => item.kind === 'line'))
const pointItems = computed(() => renderItems.value.filter((item) => item.kind === 'point'))

const selectedFeatureProperties = computed(() =>
  Object.entries(selectedFeature.value?.properties || {}).map(([key, value]) => ({
    key,
    value: value === null || value === undefined ? '' : String(value)
  }))
)

const mapTransform = computed(
  () => `translate(${mapView.x} ${mapView.y}) scale(${mapView.scale})`
)

const clampMapScale = (scale) => Math.min(20, Math.max(0.5, scale))

const eventPointInMap = (event) => {
  const rect = previewSvgRef.value?.getBoundingClientRect()
  if (!rect?.width || !rect?.height) return null
  return {
    x: ((event.clientX - rect.left) / rect.width) * 720,
    y: ((event.clientY - rect.top) / rect.height) * 420
  }
}

const zoomMapAt = (factor, point = { x: 360, y: 210 }) => {
  const nextScale = clampMapScale(mapView.scale * factor)
  if (nextScale === mapView.scale) return
  const worldX = (point.x - mapView.x) / mapView.scale
  const worldY = (point.y - mapView.y) / mapView.scale
  mapView.x = point.x - worldX * nextScale
  mapView.y = point.y - worldY * nextScale
  mapView.scale = nextScale
}

const zoomMap = (factor) => zoomMapAt(factor)

const resetMapView = () => {
  mapView.scale = 1
  mapView.x = 0
  mapView.y = 0
}

const onMapWheel = (event) => {
  const point = eventPointInMap(event)
  if (!point) return
  zoomMapAt(Math.exp(-event.deltaY * 0.0015), point)
}

const onMapDoubleClick = (event) => {
  const point = eventPointInMap(event)
  if (point) zoomMapAt(1.5, point)
}

const onMapPointerDown = (event) => {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  const point = eventPointInMap(event)
  if (!point) return
  if (mapPointers.size === 0) mapDragDistance = 0
  mapPointers.set(event.pointerId, point)
  mapDragging.value = true
}

const onMapPointerMove = (event) => {
  if (!mapPointers.has(event.pointerId)) return
  const point = eventPointInMap(event)
  if (!point) return

  const previousPointers = new Map(mapPointers)
  mapPointers.set(event.pointerId, point)

  if (mapPointers.size === 1) {
    const previous = previousPointers.get(event.pointerId)
    const dx = point.x - previous.x
    const dy = point.y - previous.y
    mapDragDistance += Math.hypot(dx, dy)
    if (mapDragDistance <= 3) return
    mapView.x += dx
    mapView.y += dy
    if (!event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.setPointerCapture?.(event.pointerId)
    }
    return
  }

  const pointerIds = [...mapPointers.keys()].slice(0, 2)
  const [previousA, previousB] = pointerIds.map((id) => previousPointers.get(id))
  const [currentA, currentB] = pointerIds.map((id) => mapPointers.get(id))
  if (!previousA || !previousB) return

  const previousDistance = Math.hypot(
    previousB.x - previousA.x,
    previousB.y - previousA.y
  )
  const currentDistance = Math.hypot(currentB.x - currentA.x, currentB.y - currentA.y)
  if (!previousDistance || !currentDistance) return

  const previousCenter = {
    x: (previousA.x + previousB.x) / 2,
    y: (previousA.y + previousB.y) / 2
  }
  const currentCenter = {
    x: (currentA.x + currentB.x) / 2,
    y: (currentA.y + currentB.y) / 2
  }
  const worldX = (previousCenter.x - mapView.x) / mapView.scale
  const worldY = (previousCenter.y - mapView.y) / mapView.scale
  const nextScale = clampMapScale(mapView.scale * (currentDistance / previousDistance))
  mapView.x = currentCenter.x - worldX * nextScale
  mapView.y = currentCenter.y - worldY * nextScale
  mapView.scale = nextScale
  mapDragDistance += Math.hypot(
    currentCenter.x - previousCenter.x,
    currentCenter.y - previousCenter.y
  )
  if (mapDragDistance > 3 && !event.currentTarget.hasPointerCapture?.(event.pointerId)) {
    event.currentTarget.setPointerCapture?.(event.pointerId)
  }
}

const onMapPointerUp = (event) => {
  mapPointers.delete(event.pointerId)
  if (mapPointers.size) return
  mapDragging.value = false
  if (mapDragDistance > 3) {
    suppressFeatureClick = true
    window.setTimeout(() => {
      suppressFeatureClick = false
    }, 0)
  }
}

const handleFeatureClick = (feature, layerNameValue) => {
  if (suppressFeatureClick) return
  selectFeature(feature, layerNameValue)
}

const loadAll = async () => {
  if (!props.kbId) return
  loading.value = true
  try {
    const [sourceResult, layerResult, compositionResult] = await Promise.all([
      spatialApi.listSources(props.kbId),
      spatialApi.listLayers(props.kbId),
      spatialApi.listCompositions(props.kbId)
    ])
    sources.value = sourceResult || []
    layers.value = layerResult || []
    compositions.value = compositionResult || []
    if (!layers.value.some((layer) => layer.layer_id === selectedLayerId.value)) {
      selectedLayerId.value = layers.value[0]?.layer_id || null
    }
    if (!analysisForm.layerAId) analysisForm.layerAId = layers.value[0]?.layer_id || null
    if (!analysisForm.layerBId) analysisForm.layerBId = layers.value[1]?.layer_id || null
    await loadPreviewFeatures()
  } catch (error) {
    console.error('加载空间数据失败:', error)
    message.error(error.message || '加载空间数据失败')
  } finally {
    loading.value = false
  }
}

const previewLayerIds = () => {
  if (activeMode.value === 'compositions') {
    return compositionDraft.items
      .filter((item) => item.visible)
      .slice(0, maxPreviewLayers)
      .map((item) => item.layer_id)
  }
  return selectedLayerId.value ? [selectedLayerId.value] : []
}

const loadPreviewFeatures = async () => {
  const layerIds = previewLayerIds()
  selectedFeature.value = null
  selectedFeatureLayer.value = ''
  resetMapView()
  if (!layerIds.length) return
  featuresLoading.value = true
  try {
    const results = await Promise.all(
      layerIds.map(async (layerId) => {
        const result = await spatialApi.getLayerFeatures(props.kbId, layerId, {
          limit: previewLimit
        })
        return [layerId, result?.features || []]
      })
    )
    loadedLayerFeatures.value = {
      ...loadedLayerFeatures.value,
      ...Object.fromEntries(results)
    }
  } catch (error) {
    console.error('加载空间要素失败:', error)
    message.error(error.message || '加载空间要素失败')
  } finally {
    featuresLoading.value = false
  }
}

const selectLayer = async (layerId) => {
  selectedLayerId.value = layerId
  await loadPreviewFeatures()
}

const confirmDeleteLayer = (layer) => {
  Modal.confirm({
    title: '删除空间图层',
    content: `确定删除“${layer.name}”及其要素吗？`,
    okType: 'danger',
    onOk: async () => {
      await spatialApi.deleteLayer(props.kbId, layer.layer_id)
      delete loadedLayerFeatures.value[layer.layer_id]
      message.success('图层已删除')
      await loadAll()
    }
  })
}

const startNewComposition = async () => {
  selectedCompositionId.value = null
  compositionDraft.name = ''
  compositionDraft.items = []
  await nextTick()
  await loadPreviewFeatures()
}

const selectComposition = async (compositionId) => {
  const composition = compositions.value.find(
    (item) => item.composition_id === compositionId
  )
  compositionDraft.name = composition?.name || ''
  compositionDraft.items = (composition?.items || []).map((item) => ({
    layer_id: item.layer_id,
    visible: item.visible !== false,
    opacity: Number(item.opacity ?? 1),
    style_override: { ...(item.style_override || {}) }
  }))
  await loadPreviewFeatures()
}

const toggleCompositionLayer = async (layer, checked) => {
  if (checked) {
    compositionDraft.items.push({
      layer_id: layer.layer_id,
      visible: true,
      opacity: 0.8,
      style_override: {}
    })
  } else {
    compositionDraft.items = compositionDraft.items.filter(
      (item) => item.layer_id !== layer.layer_id
    )
  }
  await nextTick()
  await loadPreviewFeatures()
}

const moveCompositionItem = (index, direction) => {
  const target = index + direction
  if (target < 0 || target >= compositionDraft.items.length) return
  const items = [...compositionDraft.items]
  ;[items[index], items[target]] = [items[target], items[index]]
  compositionDraft.items = items
}

const saveComposition = async () => {
  if (!compositionDraft.name.trim()) {
    message.warning('请输入组合名称')
    return
  }
  if (!compositionDraft.items.length) {
    message.warning('请至少选择一个图层')
    return
  }
  compositionSaving.value = true
  try {
    const payload = {
      name: compositionDraft.name.trim(),
      items: compositionDraft.items
    }
    const saved = selectedCompositionId.value
      ? await spatialApi.updateComposition(
          props.kbId,
          selectedCompositionId.value,
          payload
        )
      : await spatialApi.createComposition(props.kbId, payload)
    message.success('图层组合已保存')
    await loadAll()
    selectedCompositionId.value = saved.composition_id
    await selectComposition(saved.composition_id)
  } catch (error) {
    message.error(error.message || '保存图层组合失败')
  } finally {
    compositionSaving.value = false
  }
}

const confirmDeleteComposition = () => {
  const compositionId = selectedCompositionId.value
  if (!compositionId) return
  Modal.confirm({
    title: '删除图层组合',
    content: '只删除组合配置，不会删除原始图层。',
    okType: 'danger',
    onOk: async () => {
      await spatialApi.deleteComposition(props.kbId, compositionId)
      message.success('图层组合已删除')
      await startNewComposition()
      await loadAll()
    }
  })
}

const waitForAnalysisTask = async (taskId, token) => {
  const deadline = Date.now() + 30 * 60 * 1000
  while (Date.now() < deadline && token === analysisRunToken) {
    const response = await taskerApi.fetchTaskDetail(taskId)
    const task = response?.task
    if (task?.status === 'success') return task.result
    if (task?.status === 'failed' || task?.status === 'cancelled') {
      throw new Error(task.error || task.message || '空间分析任务失败')
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  if (token !== analysisRunToken) return null
  throw new Error('空间分析等待超时，请在任务中心查看状态')
}

const runAnalysis = async () => {
  if (!analysisForm.layerAId || !analysisForm.layerBId) {
    message.warning('请选择两个图层')
    return
  }
  if (analysisForm.layerAId === analysisForm.layerBId) {
    message.warning('空间分析需要两个不同图层')
    return
  }
  if (!analysisForm.targetName.trim()) {
    message.warning('请输入派生图层名称')
    return
  }

  const token = ++analysisRunToken
  analysisRunning.value = true
  try {
    const queued = await spatialApi.runAnalysis(props.kbId, {
      layer_a_id: analysisForm.layerAId,
      layer_b_id: analysisForm.layerBId,
      operation: analysisForm.operation,
      target_name: analysisForm.targetName.trim()
    })
    if (!queued?.task_id) throw new Error('空间分析任务提交失败')
    taskerStore.registerQueuedTask({
      task_id: queued.task_id,
      name: `空间分析: ${analysisForm.operation}`,
      task_type: 'knowledge_spatial_analysis',
      payload: { kb_id: props.kbId }
    })
    const result = await waitForAnalysisTask(queued.task_id, token)
    if (!result || token !== analysisRunToken) return
    message.success('派生图层已生成')
    await loadAll()
    activeMode.value = 'layers'
    selectedLayerId.value = result.layer_id
    await loadPreviewFeatures()
  } catch (error) {
    if (token === analysisRunToken) message.error(error.message || '空间分析失败')
  } finally {
    if (token === analysisRunToken) analysisRunning.value = false
  }
}

const layerName = (layerId) => layerMap.value[layerId]?.name || layerId

const selectFeature = (feature, layerNameValue) => {
  selectedFeature.value = feature
  selectedFeatureLayer.value = layerNameValue
}

const formatBbox = (bbox) => {
  if (!Array.isArray(bbox) || bbox.length !== 4) return '-'
  return bbox.map((value) => Number(value).toFixed(4)).join(', ')
}

const projectPoint = ([lng, lat], bounds) => {
  const [west, south, east, north] = bounds
  const width = 720
  const height = 420
  const padding = 28
  const dx = Math.max(east - west, 0.000001)
  const dy = Math.max(north - south, 0.000001)
  return [
    Number((padding + ((lng - west) / dx) * (width - padding * 2)).toFixed(2)),
    Number((height - padding - ((lat - south) / dy) * (height - padding * 2)).toFixed(2))
  ]
}

const coordsToPoints = (coords, bounds) =>
  coords.map((coord) => projectPoint(coord, bounds).join(',')).join(' ')

const ringToPath = (ring, bounds) => {
  if (!Array.isArray(ring) || !ring.length) return ''
  const [first, ...rest] = ring.map((coord) => projectPoint(coord, bounds))
  return `M ${first[0]} ${first[1]} ${rest.map(([x, y]) => `L ${x} ${y}`).join(' ')} Z`
}

const geometryToItems = (feature, bounds, layer) => {
  const geometry = feature.geometry
  if (!geometry?.type) return []
  const id = feature.id || feature.properties?.feature_id || Math.random().toString(36)
  const base = {
    feature,
    color: layer.color,
    opacity: Number(layer.opacity ?? 0.8),
    layerName: layer.name
  }
  const makeId = (suffix) => `${layer.layer_id}-${id}-${suffix}`

  if (geometry.type === 'Point') {
    const [x, y] = projectPoint(geometry.coordinates, bounds)
    return [{ ...base, kind: 'point', id: makeId('point'), x, y }]
  }
  if (geometry.type === 'MultiPoint') {
    return geometry.coordinates.map((coord, index) => {
      const [x, y] = projectPoint(coord, bounds)
      return { ...base, kind: 'point', id: makeId(`point-${index}`), x, y }
    })
  }
  if (geometry.type === 'LineString') {
    return [{
      ...base,
      kind: 'line',
      id: makeId('line'),
      points: coordsToPoints(geometry.coordinates, bounds)
    }]
  }
  if (geometry.type === 'MultiLineString') {
    return geometry.coordinates.map((line, index) => ({
      ...base,
      kind: 'line',
      id: makeId(`line-${index}`),
      points: coordsToPoints(line, bounds)
    }))
  }
  if (geometry.type === 'Polygon') {
    return [{
      ...base,
      kind: 'polygon',
      id: makeId('polygon'),
      path: ringToPath(geometry.coordinates[0], bounds)
    }]
  }
  if (geometry.type === 'MultiPolygon') {
    return geometry.coordinates.map((polygon, index) => ({
      ...base,
      kind: 'polygon',
      id: makeId(`polygon-${index}`),
      path: ringToPath(polygon[0], bounds)
    }))
  }
  return []
}

watch(activeMode, async (mode) => {
  if (mode === 'compositions' && selectedCompositionId.value) {
    await selectComposition(selectedCompositionId.value)
  } else {
    await loadPreviewFeatures()
  }
})

watch(
  () => props.kbId,
  () => {
    sources.value = []
    layers.value = []
    compositions.value = []
    selectedLayerId.value = null
    selectedCompositionId.value = null
    loadedLayerFeatures.value = {}
    loadAll()
  }
)

onMounted(loadAll)
onBeforeUnmount(() => {
  analysisRunToken += 1
})
</script>

<style lang="less" scoped>
.spatial-section {
  height: 100%;
  padding: 16px;
  overflow: auto;
  background: var(--gray-0);
}

.spatial-header,
.panel-heading,
.stats-row,
.map-toolbar,
.composition-item-title,
.opacity-row {
  display: flex;
  align-items: center;
}

.spatial-header {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--gray-1000);
}

.section-subtitle,
.panel-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--gray-500);
}

.loading-state {
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.spatial-workspace {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 14px;
}

.management-card,
.map-card,
.detail-card,
.stat-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  box-shadow: var(--shadow-card);
}

.management-card {
  padding: 12px;
  min-height: 560px;
}

.management-panel,
.composition-editor,
.analysis-panel,
.composition-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.management-panel {
  margin-top: 12px;
}

.panel-heading {
  min-height: 30px;
  justify-content: space-between;
  font-weight: 600;
}

.full-width {
  width: 100%;
}

.layer-list,
.available-layers {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 360px;
  overflow: auto;
}

.layer-list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 8px 9px 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.layer-list-item:hover,
.layer-list-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.layer-list-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.layer-list-main strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-primary);
}

.layer-list-main span,
.opacity-row span {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.composition-item {
  padding: 9px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.composition-item-title {
  gap: 8px;
}

.composition-item-title > span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-actions {
  display: flex;
  gap: 3px;
}

.order-actions button {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-card);
  cursor: pointer;
}

.order-actions button:disabled {
  opacity: 0.35;
  cursor: default;
}

.opacity-row {
  gap: 10px;
  margin-top: 6px;
}

.opacity-row :deep(.ant-slider) {
  flex: 1;
  margin: 5px 4px;
}

.preview-column {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stats-row {
  gap: 10px;
}

.stat-card {
  flex: 1;
  min-width: 0;
  padding: 11px 12px;
}

.stat-card span {
  display: block;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.stat-card strong {
  display: block;
  margin-top: 4px;
  color: var(--color-text-primary);
}

.bbox-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.map-and-detail {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(260px, 0.8fr);
  gap: 12px;
}

.map-toolbar,
.detail-title {
  min-height: 42px;
  padding: 0 12px;
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
}

.map-toolbar {
  justify-content: space-between;
  gap: 12px;
}

.map-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.map-interaction-hint {
  color: var(--color-text-tertiary);
  font-size: 11px;
  font-weight: 400;
}

.preview-warning {
  font-size: 11px;
  color: var(--color-warning);
}

.map-canvas {
  position: relative;
  height: 500px;
  display: grid;
  place-items: center;
  padding: 10px;
  overflow: hidden;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.map-canvas.dragging {
  cursor: grabbing;
}

.preview-svg {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.map-bg {
  fill: var(--color-bg-page);
}

.geom-polygon,
.geom-line,
.geom-point {
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.geom-polygon {
  stroke-width: 1.4;
}

.geom-line {
  fill: none;
  stroke-width: 2.2;
}

.geom-point {
  stroke: #fff;
  stroke-width: 1.2;
}

.geom-polygon:hover,
.geom-line:hover,
.geom-point:hover {
  opacity: 0.65;
}

.detail-card {
  min-width: 0;
  overflow: hidden;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-title span {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.detail-card :deep(.ant-empty) {
  margin-top: 130px;
}

.detail-card :deep(.ant-table-wrapper) {
  padding: 8px;
}

@media (max-width: 1100px) {
  .spatial-workspace,
  .map-and-detail {
    grid-template-columns: 1fr;
  }

  .management-card {
    min-height: auto;
  }
}
</style>
