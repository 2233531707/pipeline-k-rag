<template>
  <div class="source-section">
    <div class="section-title">知识库来源 ({{ chunks.length }})</div>
    <KbResultGroupedList
      :chunks="chunks"
      :show-summary="false"
      :show-open-source="true"
      @open-source="handleOpenSource"
    />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import KbResultGroupedList from '@/components/sources/KbResultGroupedList.vue'
import { buildKnowledgeSourceRouteQuery } from '@/utils/knowledgeSources'

defineProps({
  chunks: {
    type: Array,
    default: () => []
  }
})

const router = useRouter()

const handleOpenSource = (chunk) => {
  const query = buildKnowledgeSourceRouteQuery(chunk)
  if (!query) return
  void router.push({
    path: '/workspace',
    query
  })
}
</script>

<style scoped lang="less">
.source-section {
  .section-title {
    font-size: 12px;
    color: var(--gray-700);
    margin-bottom: 8px;
    font-weight: 600;
  }
}
</style>
