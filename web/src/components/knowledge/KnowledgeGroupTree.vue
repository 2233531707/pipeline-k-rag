<template>
  <div class="knowledge-group-node">
    <div class="knowledge-group-header">
      <button type="button" class="knowledge-group-toggle" @click="$emit('toggle-group', group.group_id)">
        <ChevronRight :size="16" :class="{ expanded: isExpanded }" />
        <FolderTree :size="18" />
        <span class="knowledge-group-name">{{ group.name }}</span>
        <span class="knowledge-group-count">{{ totalCount }}</span>
      </button>
      <div class="knowledge-group-actions">
        <a-button
          type="text"
          class="lucide-icon-btn"
          :disabled="!kbTypes.length"
          @click="$emit('create-group', group.group_id)"
        >
          <FolderPlus :size="16" /> 新建子分组
        </a-button>
        <a-button
          type="text"
          class="lucide-icon-btn"
          :disabled="!kbTypes.length"
          @click="$emit('create-database', group.group_id)"
        >
          <Plus :size="16" /> 新建知识库
        </a-button>
        <a-button
          v-if="!group.is_default"
          type="text"
          class="lucide-icon-btn"
          @click="$emit('rename-group', group)"
        >
          <Pencil :size="16" /> 重命名
        </a-button>
        <a-button
          v-if="!group.is_default"
          type="text"
          danger
          class="lucide-icon-btn"
          @click="$emit('delete-group', group)"
        >
          <Trash2 :size="16" /> 删除
        </a-button>
      </div>
    </div>

    <div v-show="isExpanded" class="knowledge-group-body">
      <ExtensionCardGrid v-if="group.databases.length">
        <InfoCard
          v-for="database in group.databases"
          :key="database.kb_id"
          :title="database.name"
          :subtitle="cardSubtitle(database)"
          :description="database.description || '暂无描述'"
          :tags="cardTags(database)"
          @click="$emit('navigate-database', database)"
        >
          <template #icon>
            <component :is="getKbTypeIcon(database.kb_type || 'milvus')" :size="20" />
          </template>
          <template #status />
          <template #footer>
            <a-select
              :value="database.group_id"
              size="small"
              class="database-group-select"
              :options="knowledgeGroupOptions"
              @click.stop
              @change="(groupId) => $emit('move-database', database, groupId)"
            />
          </template>
        </InfoCard>
      </ExtensionCardGrid>

      <div v-for="child in group.children" :key="child.group_id" class="knowledge-group-children">
        <KnowledgeGroupTree
          :group="child"
          :kb-types="kbTypes"
          :knowledge-group-options="knowledgeGroupOptions"
          :expanded-group-ids="expandedGroupIds"
          :card-subtitle="cardSubtitle"
          :card-tags="cardTags"
          :get-kb-type-icon="getKbTypeIcon"
          @toggle-group="$emit('toggle-group', $event)"
          @create-group="$emit('create-group', $event)"
          @create-database="$emit('create-database', $event)"
          @rename-group="$emit('rename-group', $event)"
          @delete-group="$emit('delete-group', $event)"
          @move-database="handleMoveDatabase"
          @navigate-database="$emit('navigate-database', $event)"
        />
      </div>

      <a-empty
        v-if="!group.databases.length && !group.children.length"
        :image="false"
        description="该分组暂无内容"
        class="knowledge-group-empty"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ChevronRight, FolderTree, FolderPlus, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import ExtensionCardGrid from '@/components/extensions/ExtensionCardGrid.vue'
import InfoCard from '@/components/shared/InfoCard.vue'

const props = defineProps({
  group: { type: Object, required: true },
  kbTypes: { type: Array, required: true },
  knowledgeGroupOptions: { type: Array, required: true },
  expandedGroupIds: { type: Object, required: true },
  cardSubtitle: { type: Function, required: true },
  cardTags: { type: Function, required: true },
  getKbTypeIcon: { type: Function, required: true }
})

const emit = defineEmits([
  'toggle-group',
  'create-group',
  'create-database',
  'rename-group',
  'delete-group',
  'move-database',
  'navigate-database'
])

const handleMoveDatabase = (database, groupId) => {
  // Keep recursive event payload explicit for Vue template stability.
  emit('move-database', database, groupId)
}

const isExpanded = computed(() => props.expandedGroupIds.has(props.group.group_id))

const totalCount = computed(() => {
  const countChildren = (group) =>
    (group.databases?.length || 0) +
    (group.children || []).reduce((sum, child) => sum + countChildren(child), 0)
  return countChildren(props.group)
})
</script>

<style lang="less" scoped>
.knowledge-group-node {
  display: flex;
  flex-direction: column;
}

.knowledge-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px var(--page-padding) 0;
}

.knowledge-group-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--gray-800);
  cursor: pointer;
}

.knowledge-group-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--gray-900);
}

.knowledge-group-count {
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

.knowledge-group-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.knowledge-group-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.knowledge-group-children {
  margin-left: 28px;
  border-left: 1px solid var(--gray-150);
}

.knowledge-group-empty {
  padding: 20px var(--page-padding);
}

.expanded {
  transform: rotate(90deg);
}
</style>
