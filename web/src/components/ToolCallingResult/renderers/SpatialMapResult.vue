<template>
  <BaseToolCall :tool-call="toolCall" :hide-params="false">
    <template #header>
      <div class="sep-header">
        <span class="note">show_spatial_map</span>
        <span class="separator" v-if="mapTitle">|</span>
        <span class="description" v-if="mapTitle">{{ mapTitle }}</span>
      </div>
    </template>
    <template #result>
      <div class="spatial-map-result">
        <!-- 加载状态 -->
        <div v-if="isLoading" class="state-loading">
          <Loader2 class="spin-icon" :size="16" />
          <span>加载地图数据...</span>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="mapError" class="state-error">
          <AlertCircle :size="16" />
          <span>{{ mapError }}</span>
        </div>

        <!-- 空状态 -->
        <div v-else-if="!hasLayers" class="state-empty">
          <Map :size="16" />
          <span>暂无可显示的空间图层</span>
        </div>

        <!-- 地图 -->
        <template v-else>
          <div class="map-toolbar">
            <span class="map-title">{{ mapTitle }}</span>
            <span v-if="layerCount > 1000" class="overlimit-hint">
              要素过多 ({{ layerCount }})，仅显示前 1000 条
            </span>
          </div>

          <div class="map-stage">
            <div ref="mapContainerRef" class="map-container"></div>
            <div v-if="isFetchingLayers" class="map-loading-overlay">
              <Loader2 class="spin-icon" :size="18" />
              <span>加载图层要素...</span>
            </div>
            <aside v-if="popupFeature" class="feature-drawer">
              <div class="drawer-header">
                <div>
                  <strong>要素详情</strong>
                  <span v-if="selectedLayerName">{{ selectedLayerName }}</span>
                </div>
                <button type="button" class="drawer-close" aria-label="关闭要素详情" @click="closeFeatureDetails">
                  <X :size="14" />
                </button>
              </div>
              <div class="drawer-props">
                <div
                  v-for="(val, key) in popupFeature.properties"
                  :key="key"
                  class="drawer-row"
                >
                  <span class="drawer-key">{{ key }}</span>
                  <span class="drawer-val">{{ val }}</span>
                </div>
              </div>
            </aside>
          </div>

          <!-- 图层面板 -->
          <div v-if="layers.length > 1" class="layer-panel">
            <div
              v-for="(layer, idx) in orderedLayers"
              :key="layer.layer_id"
              class="layer-row"
              :class="{ hidden: !layer.visible }"
            >
              <a-checkbox
                :checked="layer.visible"
                size="small"
                @change="() => toggleLayer(idx)"
              />
              <span
                class="layer-color"
                :style="{ background: layer.color }"
              />
              <span class="layer-name">{{ layer.name }}</span>
              <span class="layer-count">{{ layer.feature_count || 0 }} 要素</span>
              <div class="layer-order-actions">
                <button
                  type="button"
                  :disabled="idx === 0"
                  aria-label="上移图层"
                  @click="moveLayer(idx, -1)"
                >
                  <ChevronUp :size="13" />
                </button>
                <button
                  type="button"
                  :disabled="idx === orderedLayers.length - 1"
                  aria-label="下移图层"
                  @click="moveLayer(idx, 1)"
                >
                  <ChevronDown :size="13" />
                </button>
              </div>
              <a-slider
                v-model:value="layer.opacity"
                :min="0"
                :max="1"
                :step="0.1"
                style="width: 80px; margin-left: auto"
                @change="() => updateLayerOpacity(idx)"
              />
            </div>
          </div>

        </template>
      </div>
    </template>
  </BaseToolCall>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { AlertCircle, ChevronDown, ChevronUp, Loader2, Map, X } from 'lucide-vue-next'
import BaseToolCall from '../BaseToolCall.vue'
import { resolvePreviewAssetUrl } from '@/utils/desktopAssets'

const props = defineProps({
  toolCall: {
    type: Object,
    required: true
  }
})

const mapContainerRef = ref(null)
let mapInstance = null
let maplibreApi = null
let mapPopup = null

const popupFeature = ref(null)
const selectedLayerName = ref('')
const runtimeError = ref(null)
const isFetchingLayers = ref(false)

const orderedLayers = ref([])
const layerColors = [
  '#1685ff', '#0f9f6e', '#c97a05', '#d43a43', '#7c3aed',
  '#db2777', '#0891b2', '#65a30d', '#ca8a04', '#9333ea'
]

const resultContent = computed(() => {
  const c = props.toolCall.tool_call_result?.content
  if (!c) return null
  return typeof c === 'object' ? c : (() => { try { return JSON.parse(c) } catch { return null } })()
})

const parsed = computed(() => {
  const c = resultContent.value
  if (!c) return null
  return c.content || c
})

const mapTitle = computed(() => parsed.value?.title || '空间数据地图')
const layers = computed(() => parsed.value?.layers || [])
const mapConfig = computed(() => parsed.value?.map_config || {})
const bounds = computed(() => parsed.value?.bounds || null)
const mapError = computed(() => parsed.value?.error || runtimeError.value)
const isLoading = computed(() => !parsed.value && !mapError.value)
const hasLayers = computed(() => layers.value.length > 0)
const layerCount = computed(() => layers.value.reduce((sum, l) => sum + (l.feature_count || 0), 0))

const toggleLayer = (idx) => {
  orderedLayers.value[idx].visible = !orderedLayers.value[idx].visible
  updateMapLayerVisibility(idx)
}

const getRenderLayerIds = (layer) => {
  const sourceId = 'source-' + layer.layer_id
  const geomType = (layer.geometry_type || '').toLowerCase()
  if (geomType.includes('polygon')) return [sourceId + '-fill', sourceId + '-line']
  if (geomType.includes('line')) return [sourceId + '-line']
  return [sourceId + '-circle']
}

const syncLayerOrder = () => {
  if (!mapInstance) return
  for (let idx = orderedLayers.value.length - 1; idx >= 0; idx -= 1) {
    getRenderLayerIds(orderedLayers.value[idx]).forEach((layerId) => {
      if (mapInstance.getLayer(layerId)) mapInstance.moveLayer(layerId)
    })
  }
}

const moveLayer = (idx, direction) => {
  const targetIdx = idx + direction
  if (targetIdx < 0 || targetIdx >= orderedLayers.value.length) return
  const nextLayers = [...orderedLayers.value]
  ;[nextLayers[idx], nextLayers[targetIdx]] = [nextLayers[targetIdx], nextLayers[idx]]
  orderedLayers.value = nextLayers
  syncLayerOrder()
}

const updateLayerOpacity = (idx) => {
  if (!mapInstance) return
  const layer = orderedLayers.value[idx]
  const sourceId = `source-${layer.layer_id}`
  if (mapInstance.getLayer(`${sourceId}-fill`)) {
    mapInstance.setPaintProperty(`${sourceId}-fill`, 'fill-opacity', layer.opacity)
  }
  if (mapInstance.getLayer(`${sourceId}-line`)) {
    mapInstance.setPaintProperty(`${sourceId}-line`, 'line-opacity', layer.opacity)
  }
  if (mapInstance.getLayer(`${sourceId}-circle`)) {
    mapInstance.setPaintProperty(`${sourceId}-circle`, 'circle-opacity', layer.opacity)
  }
}

const updateMapLayerVisibility = (idx) => {
  if (!mapInstance) return
  const layer = orderedLayers.value[idx]
  const visibility = layer.visible ? 'visible' : 'none'
  const sourceId = `source-${layer.layer_id}`
  ;['fill', 'line', 'circle'].forEach((suffix) => {
    const lid = `${sourceId}-${suffix}`
    if (mapInstance.getLayer(lid)) {
      mapInstance.setLayoutProperty(lid, 'visibility', visibility)
    }
  })
}

const fetchLayerFeatures = async (layer, kbId) => {
  const { spatialApi } = await import('@/apis/knowledge_api')
  const result = await spatialApi.getLayerFeatures(kbId, layer.layer_id, { limit: 1000 })
  return result?.features || []
}

const showFeatureDetails = (event, layer) => {
  const feature = event.features?.[0]
  if (!feature) return

  const popupFields = Array.isArray(layer.popup_fields) ? layer.popup_fields : []
  popupFeature.value = popupFields.length
    ? {
        ...feature,
        properties: Object.fromEntries(
          popupFields.filter((key) => key in (feature.properties || {})).map((key) => [
            key,
            feature.properties[key]
          ])
        )
      }
    : feature
  selectedLayerName.value = layer.name || layer.layer_id
  mapPopup?.remove()
  if (maplibreApi && mapInstance && event.lngLat) {
    mapPopup = new maplibreApi.Popup({ closeButton: false, offset: 8 })
      .setLngLat(event.lngLat)
      .setText(selectedLayerName.value)
      .addTo(mapInstance)
  }
}

const closeFeatureDetails = () => {
  popupFeature.value = null
  selectedLayerName.value = ''
  mapPopup?.remove()
  mapPopup = null
}

const initMap = async () => {
  if (!mapContainerRef.value || !hasLayers.value) return

  const kbId = parsed.value?.kb_id
  if (!kbId) {
    runtimeError.value = '地图结果缺少知识库标识'
    return
  }

  runtimeError.value = null
  isFetchingLayers.value = true

  try {
    const allLayerData = await Promise.all(
      layers.value.slice(0, 10).map(async (layer, idx) => {
        const features = await fetchLayerFeatures(layer, kbId)
        const style = layer.style || {}
        return {
        ...layer,
        features,
          visible: layer.visible !== false,
          opacity: Math.max(0, Math.min(1, Number(layer.opacity ?? 0.8))),
          color:
            style.color ||
            style.fill_color ||
            style.line_color ||
            layerColors[idx % layerColors.length]
        }
      })
    )
    orderedLayers.value = allLayerData

    await nextTick()

    const maplibre = await import('maplibre-gl')
    await import('maplibre-gl/dist/maplibre-gl.css')
    maplibreApi = maplibre.default

    const config = mapConfig.value
    mapInstance = new maplibreApi.Map({
      container: mapContainerRef.value,
      style: resolvePreviewAssetUrl(
        config.map_style || 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
      ),
      center: config.center || [0, 0],
      zoom: config.zoom || 12
    })
    mapInstance.addControl(new maplibreApi.NavigationControl(), 'top-right')

    mapInstance.on('load', () => {
      try {
        orderedLayers.value.forEach((layer) => {
          const sourceId = 'source-' + layer.layer_id
          mapInstance.addSource(sourceId, {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: layer.features || [] }
          })

          const geomType = (layer.geometry_type || '').toLowerCase()
          if (geomType.includes('polygon')) {
            mapInstance.addLayer({
              id: sourceId + '-fill',
              type: 'fill',
              source: sourceId,
              layout: { visibility: layer.visible ? 'visible' : 'none' },
              paint: { 'fill-color': layer.color, 'fill-opacity': layer.opacity }
            })
            mapInstance.addLayer({
              id: sourceId + '-line',
              type: 'line',
              source: sourceId,
              layout: { visibility: layer.visible ? 'visible' : 'none' },
              paint: {
                'line-color': layer.color,
                'line-width': 1,
                'line-opacity': layer.opacity
              }
            })
          } else if (geomType.includes('line')) {
            mapInstance.addLayer({
              id: sourceId + '-line',
              type: 'line',
              source: sourceId,
              layout: { visibility: layer.visible ? 'visible' : 'none' },
              paint: {
                'line-color': layer.color,
                'line-width': 2,
                'line-opacity': layer.opacity
              }
            })
          } else {
            mapInstance.addLayer({
              id: sourceId + '-circle',
              type: 'circle',
              source: sourceId,
              layout: { visibility: layer.visible ? 'visible' : 'none' },
              paint: {
                'circle-color': layer.color,
                'circle-radius': 5,
                'circle-opacity': layer.opacity
              }
            })
          }

          getRenderLayerIds(layer).forEach((layerId) => {
            mapInstance.on('click', layerId, (event) => showFeatureDetails(event, layer))
            mapInstance.on('mouseenter', layerId, () => {
              mapInstance.getCanvas().style.cursor = 'pointer'
            })
            mapInstance.on('mouseleave', layerId, () => {
              mapInstance.getCanvas().style.cursor = ''
            })
          })
        })

        syncLayerOrder()
        if (bounds.value && bounds.value.length === 4) {
          const [west, south, east, north] = bounds.value
          mapInstance.fitBounds([[west, south], [east, north]], { padding: 40 })
        }
        isFetchingLayers.value = false
      } catch (error) {
        runtimeError.value = '地图图层加载失败: ' + (error.message || error)
        isFetchingLayers.value = false
      }
    })
  } catch (error) {
    runtimeError.value = '地图初始化失败: ' + (error.message || error)
    isFetchingLayers.value = false
  }
}

const destroyMap = () => {
  closeFeatureDetails()
  isFetchingLayers.value = false
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
}

watch(() => parsed.value, async (val) => {
  if (val && !val.error && hasLayers.value) {
    destroyMap()
    await nextTick()
    initMap()
  }
}, { immediate: true })

onMounted(() => {
  if (parsed.value && !parsed.value.error && hasLayers.value) {
    initMap()
  }
})

onUnmounted(() => {
  destroyMap()
})

// 暴露 refreshGraph 方法供 ToolCallRenderer 调用
defineExpose({ refreshGraph: initMap })
</script>

<style lang="less" scoped>
.spatial-map-result {
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

.map-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--gray-25);
  border-bottom: 1px solid var(--gray-100);

  .map-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--gray-700);
  }

  .overlimit-hint {
    font-size: 11px;
    color: var(--color-warning, #c97a05);
    margin-left: auto;
  }
}

.map-stage {
  position: relative;
  min-height: 360px;
}

.map-container {
  width: 100%;
  height: 360px;
  border-bottom: 1px solid var(--gray-100);
}

.map-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--gray-600);
  background: color-mix(in srgb, var(--gray-0) 82%, transparent);
  z-index: 5;
}

.feature-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(320px, 72%);
  display: flex;
  flex-direction: column;
  background: var(--panel, #fff);
  border-left: 1px solid var(--gray-100);
  box-shadow: var(--shadow-md);
  z-index: 6;

  .drawer-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--gray-100);

    div {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }

    strong {
      color: var(--gray-800);
      font-size: 13px;
    }

    span {
      color: var(--gray-500);
      font-size: 11px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .drawer-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    color: var(--gray-500);
    background: transparent;
    border: 0;
    border-radius: var(--radius-sm);
    cursor: pointer;

    &:hover {
      color: var(--gray-700);
      background: var(--gray-50);
    }
  }

  .drawer-props {
    flex: 1;
    overflow-y: auto;
    padding: 6px 12px 12px;
  }

  .drawer-row {
    display: grid;
    grid-template-columns: minmax(80px, 0.45fr) minmax(0, 1fr);
    gap: 8px;
    padding: 5px 0;
    font-size: 11px;
    line-height: 1.5;
    border-bottom: 1px solid var(--gray-50);
  }

  .drawer-key {
    color: var(--gray-600);
    font-weight: 500;
    word-break: break-word;
  }

  .drawer-val {
    color: var(--gray-800);
    word-break: break-all;
  }
}

.layer-panel {
  padding: 8px 12px;

  .layer-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 12px;

    &.hidden {
      opacity: 0.4;
    }

    .layer-color {
      width: 12px;
      height: 12px;
      border-radius: 3px;
      flex-shrink: 0;
    }

    .layer-name {
      color: var(--gray-700);
      font-weight: 500;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .layer-count {
      color: var(--gray-500);
      font-size: 11px;
      white-space: nowrap;
    }

    .layer-order-actions {
      display: inline-flex;
      gap: 2px;

      button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        padding: 0;
        color: var(--gray-500);
        background: transparent;
        border: 1px solid var(--gray-100);
        border-radius: 4px;
        cursor: pointer;

        &:hover:not(:disabled) {
          color: var(--main-600);
          border-color: var(--main-200);
        }

        &:disabled {
          opacity: 0.35;
          cursor: not-allowed;
        }
      }
    }
  }
}

</style>
