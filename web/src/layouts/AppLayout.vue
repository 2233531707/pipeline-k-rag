<script setup>
import { ref, onMounted, onBeforeUnmount, computed, provide, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  BarChart3,
  ClipboardList,
  LibraryBig,
  Box,
  FolderKanban,
  PanelLeftClose,
  PanelLeftOpen,
  MessageCirclePlus,
  MapPinned
} from 'lucide-vue-next'

import { useConfigStore } from '@/stores/config'
import { useAgentStore } from '@/stores/agent'
import { useChatThreadsStore } from '@/stores/chatThreads'
import { useChatUIStore } from '@/stores/chatUI'
import { useDatabaseStore } from '@/stores/database'
import { useInfoStore } from '@/stores/info'
import { useTaskerStore } from '@/stores/tasker'
import { useUserStore } from '@/stores/user'
import { storeToRefs } from 'pinia'
import UserInfoComponent from '@/components/UserInfoComponent.vue'
import DebugComponent from '@/components/DebugComponent.vue'
import TaskCenterDrawer from '@/components/TaskCenterDrawer.vue'
import SettingsModal from '@/components/SettingsModal.vue'
import ConversationNavSection from '@/components/ConversationNavSection.vue'
import {
  isNavItemActive as isRouteNavItemActive,
  resolveRouterLinkActiveClass
} from '@/utils/sidebarNav'

const configStore = useConfigStore()
const agentStore = useAgentStore()
const chatThreadsStore = useChatThreadsStore()
const chatUIStore = useChatUIStore()
const databaseStore = useDatabaseStore()
const infoStore = useInfoStore()
const taskerStore = useTaskerStore()
const userStore = useUserStore()
const { activeCount: activeCountRef, isDrawerOpen } = storeToRefs(taskerStore)
const { threads, currentThreadId, hasMoreThreads, isLoadingMoreThreads } =
  storeToRefs(chatThreadsStore)

// Add state for debug modal
const showDebugModal = ref(false)

// Add state for settings modal
const showSettingsModal = ref(false)
const settingsInitialTab = ref('')

const { sidebarCollapsed, sidebarWidth } = storeToRefs(chatUIStore)
const isResizingSidebar = ref(false)
const sidebarResizeStep = 16

// Provide settings modal methods to child components
const openSettingsModal = (tab) => {
  settingsInitialTab.value = tab || (userStore.isAdmin ? 'base' : 'account')
  showSettingsModal.value = true
}

// Handle debug modal close
const handleDebugModalClose = () => {
  showDebugModal.value = false
}

const getRemoteConfig = async () => {
  if (!userStore.isAdmin) return
  try {
    await configStore.refreshConfig()
  } catch (error) {
    console.warn('加载系统配置失败:', error)
  }
}

const getRemoteDatabase = async () => {
  try {
    await databaseStore.loadDatabases()
  } catch (error) {
    console.warn('加载知识库列表失败:', error)
  }
}

const getViewportWidth = () => (typeof window === 'undefined' ? undefined : window.innerWidth)

const syncSidebarWidthToViewport = () => {
  chatUIStore.setSidebarWidth(sidebarWidth.value, getViewportWidth())
}

const applySidebarWidth = (width) => {
  chatUIStore.setSidebarWidth(width, getViewportWidth())
}

const handleSidebarResizeMove = (event) => {
  if (!isResizingSidebar.value) return
  applySidebarWidth(event.clientX)
}

const stopSidebarResize = () => {
  if (!isResizingSidebar.value) return
  isResizingSidebar.value = false
  window.removeEventListener('pointermove', handleSidebarResizeMove)
  window.removeEventListener('pointerup', stopSidebarResize)
  window.removeEventListener('pointercancel', stopSidebarResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

const startSidebarResize = (event) => {
  if (sidebarCollapsed.value) return
  event.preventDefault()
  isResizingSidebar.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', handleSidebarResizeMove)
  window.addEventListener('pointerup', stopSidebarResize)
  window.addEventListener('pointercancel', stopSidebarResize)
  applySidebarWidth(event.clientX)
}

const nudgeSidebarWidth = (delta) => {
  applySidebarWidth(sidebarWidth.value + delta)
}

const resetSidebarWidth = () => {
  chatUIStore.resetSidebarWidth()
  syncSidebarWidthToViewport()
}

onMounted(async () => {
  syncSidebarWidthToViewport()
  window.addEventListener('resize', syncSidebarWidthToViewport)
  // 加载信息配置与知识库数据无依赖，可并行
  await Promise.all([infoStore.loadInfoConfig(), getRemoteDatabase()])
  await initAgentNavigation()
  // 仅管理员加载系统配置和任务中心数据
  if (userStore.isAdmin) {
    await getRemoteConfig()
    taskerStore.loadTasks()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncSidebarWidthToViewport)
  stopSidebarResize()
})

const route = useRoute()
const router = useRouter()

const activeTaskCount = computed(() => activeCountRef.value || 0)
const layoutStyle = computed(() => ({
  '--sidebar-width': `${sidebarWidth.value}px`
}))
const organizationName = computed(() => {
  return infoStore.organization.name || infoStore.branding.name || '地下管网知识模型数据库'
})

// 下面是导航菜单部分，添加智能体项
const mainList = computed(() => {
  const items = [
    {
      name: '创建新对话',
      path: '/agent',
      icon: MessageCirclePlus,
      activeIcon: MessageCirclePlus,
      action: true
    }
  ]

  items.push({
    name: '工作区',
    path: '/workspace',
    icon: FolderKanban,
    activeIcon: FolderKanban
  })

  items.push({
    name: '智能体扩展',
    path: '/extensions?tab=skills',
    activePaths: ['/extensions'],
    activeTabs: ['skills', 'tools', 'mcp'],
    icon: LibraryBig,
    activeIcon: LibraryBig
  })

  items.push({
    name: '智能体管理',
    path: '/model-manage',
    icon: Box,
    activeIcon: Box
  })

  if (userStore.isAdmin) {
    items.push({
      name: '知识模型数据库',
      path: '/extensions?tab=knowledge',
      activePaths: ['/extensions'],
      activeTabs: ['knowledge'],
      icon: MapPinned,
      activeIcon: MapPinned
    })

    items.push({
      name: '数据总览',
      path: '/dashboard',
      icon: BarChart3,
      activeIcon: BarChart3
    })
  }

  return items
})

const isNavItemActive = (item) => isRouteNavItemActive(item, route)

const setSidebarCollapsed = (collapsed) => {
  sidebarCollapsed.value = collapsed
}

const toggleSidebar = () => {
  setSidebarCollapsed(!sidebarCollapsed.value)
}

const initAgentNavigation = async () => {
  try {
    if (!agentStore.isInitialized) {
      await agentStore.initialize()
    }
    await chatThreadsStore.loadThreads()
  } catch (error) {
    console.warn('加载对话导航失败:', error)
  }
}

const handleSelectChat = (threadId) => {
  if (!threadId) return
  chatThreadsStore.setCurrentThreadId(threadId)
  router.push({ name: 'AgentCompWithThreadId', params: { thread_id: threadId } })
}

const handleDeleteChat = async (threadId) => {
  if (!threadId) return
  try {
    await chatThreadsStore.deleteThread(threadId)
    if (route.params.thread_id === threadId) {
      await router.replace({ name: 'AgentComp' })
    }
  } catch (error) {
    console.warn('删除对话失败:', error)
  }
}

const handleRenameChat = async ({ chatId, title }) => {
  try {
    await chatThreadsStore.updateThread(chatId, title)
  } catch (error) {
    console.warn('重命名对话失败:', error)
  }
}

const handleTogglePinChat = async (threadId) => {
  const thread = threads.value.find((item) => item.id === threadId)
  if (!thread) return
  try {
    await chatThreadsStore.updateThread(threadId, null, !thread.is_pinned)
    await chatThreadsStore.loadThreads()
    if (currentThreadId.value) {
      chatThreadsStore.setCurrentThreadId(currentThreadId.value)
    }
  } catch (error) {
    console.warn('更新置顶状态失败:', error)
  }
}

watch(
  () => [route.path, route.params.thread_id],
  () => {
    if (!route.path.startsWith('/agent')) return
    const threadId = typeof route.params.thread_id === 'string' ? route.params.thread_id : null
    chatThreadsStore.setCurrentThreadId(threadId)
  },
  { immediate: true }
)

// Provide settings modal methods to child components
provide('settingsModal', {
  openSettingsModal
})
</script>

<template>
  <div
    class="app-layout"
    :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-resizing': isResizingSidebar }"
    :style="layoutStyle"
  >
    <div class="header">
      <div class="sidebar-brand" @click.stop>
        <router-link v-if="!sidebarCollapsed" to="/" class="brand-link">
          <img :src="infoStore.organization.avatar" class="brand-avatar" />
          <span class="brand-name">{{ organizationName }}</span>
        </router-link>
        <button
          v-else
          type="button"
          class="brand-link brand-expand-button"
          aria-label="展开侧边栏"
          @click="setSidebarCollapsed(false)"
        >
          <img :src="infoStore.organization.avatar" class="brand-avatar brand-avatar-image" />
          <PanelLeftOpen class="brand-expand-icon" size="20" />
        </button>
        <button
          v-if="!sidebarCollapsed"
          type="button"
          class="sidebar-toggle"
          aria-label="折叠侧边栏"
          @click="toggleSidebar"
        >
          <PanelLeftClose size="18" />
        </button>
      </div>
      <div class="nav">
        <div v-if="!sidebarCollapsed" class="nav-section-label">工作</div>
        <!-- 使用mainList渲染导航项 -->
        <RouterLink
          v-for="(item, index) in mainList"
          :key="index"
          :to="item.path"
          v-show="!item.hidden"
          class="nav-item"
          :class="{ active: isNavItemActive(item), 'primary-action': item.action }"
          :active-class="resolveRouterLinkActiveClass(item)"
          @click.stop
        >
          <a-tooltip placement="right" :open="sidebarCollapsed ? undefined : false">
            <template #title>{{ item.name }}</template>
            <component
              class="icon"
              :is="isNavItemActive(item) ? item.activeIcon : item.icon"
              size="18"
            />
          </a-tooltip>
          <span class="nav-text">{{ item.name }}</span>
        </RouterLink>
      </div>
      <div class="fill">
        <ConversationNavSection
          v-if="!sidebarCollapsed"
          class="sidebar-conversations"
          :current-chat-id="currentThreadId"
          :chats-list="threads"
          :has-more-chats="hasMoreThreads"
          :is-loading-more="isLoadingMoreThreads"
          @select-chat="handleSelectChat"
          @delete-chat="handleDeleteChat"
          @rename-chat="handleRenameChat"
          @toggle-pin="handleTogglePinChat"
          @load-more-chats="() => chatThreadsStore.loadMoreThreads()"
        />
      </div>
      <div class="foo">
        <!-- 用户信息组件 -->
        <div class="nav-item user-info" @click.stop>
          <UserInfoComponent :show-role="!sidebarCollapsed">
            <template v-if="userStore.isAdmin" #actions>
              <a-tooltip placement="top" title="任务中心">
                <button
                  class="user-task-center"
                  :class="{ active: isDrawerOpen }"
                  type="button"
                  aria-label="任务中心"
                  @click.stop="taskerStore.openDrawer()"
                >
                  <a-badge
                    :count="activeTaskCount"
                    :overflow-count="99"
                    class="task-center-badge"
                    size="small"
                  >
                    <ClipboardList class="icon" size="16" />
                  </a-badge>
                </button>
              </a-tooltip>
            </template>
          </UserInfoComponent>
        </div>
      </div>
      <button
        v-if="!sidebarCollapsed"
        type="button"
        class="sidebar-resize-handle"
        aria-label="调整侧边栏宽度"
        @pointerdown="startSidebarResize"
        @keydown.left.prevent="nudgeSidebarWidth(-sidebarResizeStep)"
        @keydown.right.prevent="nudgeSidebarWidth(sidebarResizeStep)"
        @dblclick="resetSidebarWidth"
      />
    </div>
    <router-view v-slot="{ Component, route }" id="app-router-view">
      <keep-alive v-if="route.meta.keepAlive !== false">
        <component :is="Component" />
      </keep-alive>
      <component :is="Component" v-else />
    </router-view>

    <!-- Debug Modal -->
    <a-modal
      v-model:open="showDebugModal"
      title="调试面板"
      width="90%"
      :footer="null"
      @cancel="handleDebugModalClose"
      :maskClosable="true"
      :destroyOnClose="true"
      class="debug-modal"
    >
      <DebugComponent />
    </a-modal>
    <TaskCenterDrawer v-if="userStore.isAdmin" />
    <SettingsModal
      v-model:visible="showSettingsModal"
      :initial-tab="settingsInitialTab"
      @close="() => (showSettingsModal = false)"
    />
  </div>
</template>

<style lang="less" scoped>
// Less 变量定义
@sidebar-width: var(--sidebar-width);
@sidebar-collapsed-width: var(--sidebar-collapsed-width);
@sidebar-padding: 10px 12px;
@sidebar-item-height: 38px;
@sidebar-item-padding-x: 10px;
@sidebar-icon-size: 16px;

.app-layout {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100vh;
  min-width: var(--min-width);
}

.app-layout.sidebar-resizing {
  cursor: col-resize;

  .header {
    transition: none;
  }
}

div.header,
#app-router-view {
  height: 100%;
  max-width: 100%;
}

#app-router-view {
  flex: 1 1 auto;
  overflow: auto;
  background: var(--color-bg-page);
}

.header {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 0 0 @sidebar-width;
  justify-content: flex-start;
  align-items: stretch;
  gap: 12px;
  background-color: var(--color-bg-sidebar);
  height: 100%;
  width: @sidebar-width;
  border-right: 1px solid var(--color-border);
  padding: @sidebar-padding;
  overflow: hidden;
  user-select: none;
  transition:
    width 0.18s ease,
    flex-basis 0.18s ease;

  .sidebar-resize-handle {
    position: absolute;
    top: 0;
    right: -4px;
    bottom: 0;
    z-index: 3;
    width: 8px;
    padding: 0;
    border: 0;
    background: transparent;
    cursor: col-resize;

    &::after {
      position: absolute;
      top: 8px;
      right: 3px;
      bottom: 8px;
      width: 2px;
      border-radius: 2px;
      background: var(--main-color);
      content: '';
      opacity: 0;
      transition: opacity 0.16s ease;
    }

    &:hover::after,
    &:focus-visible::after {
      opacity: 1;
    }

    &:focus-visible {
      outline: none;
    }
  }

  .nav {
    display: flex;
    flex: 0 0 auto;
    flex-direction: column;
    justify-content: flex-start;
    align-items: stretch;
    position: relative;
    gap: 4px;
  }

  .nav-section-label {
    padding: 0 10px 4px;
    color: var(--color-text-tertiary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    line-height: 18px;
    text-transform: uppercase;
  }

  .sidebar-conversations {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .sidebar-brand,
  :deep(.conversation-nav-section:not(.sidebar-conversations)),
  .github,
  .user-info {
    flex-shrink: 0;
  }

  .fill {
    flex: 1 1 0;
    min-height: 0;
  }

  .sidebar-brand {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 42px;
    gap: 8px;
  }

  .brand-link {
    display: flex;
    flex: 1 1 auto;
    align-items: center;
    min-width: 0;
    height: @sidebar-item-height;
    color: var(--gray-900);
    text-decoration: none;
    border: 0;
    background: transparent;
    padding: 0 4px;
    cursor: pointer;
  }

  .brand-avatar {
    flex: 0 0 30px;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    object-fit: cover;
  }

  .brand-name {
    min-width: 0;
    margin-left: 10px;
    overflow: hidden;
    color: var(--color-text-primary);
    font-size: 15px;
    font-weight: 700;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .sidebar-toggle {
    display: inline-flex;
    flex: 0 0 32px;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 1px solid transparent;
    border-radius: 8px;
    background: transparent;
    color: var(--gray-600);
    cursor: pointer;
    transition:
      background-color 0.2s ease,
      border-color 0.2s ease,
      color 0.2s ease;

    &:hover,
    &:focus-visible {
      border-color: var(--main-50);
      background: var(--main-20);
      color: var(--main-color);
      outline: none;
    }
  }

  .nav-item {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    width: 100%;
    height: @sidebar-item-height;
    padding: 0 @sidebar-item-padding-x;
    border: 1px solid transparent;
    border-radius: 8px;
    background-color: transparent;
    color: var(--color-text-secondary);
    font-size: 14px;
    font-weight: 450;
    transition:
      background-color 0.2s ease-in-out,
      border-color 0.2s ease-in-out,
      color 0.2s ease-in-out;
    margin: 0;
    text-decoration: none;
    cursor: pointer;
    outline: none;

    .icon {
      flex: 0 0 @sidebar-icon-size;
      width: @sidebar-icon-size;
      height: @sidebar-icon-size;
    }

    .nav-text {
      min-width: 0;
      max-width: calc(var(--sidebar-width) - 74px);
      margin-left: 8px;
      overflow: hidden;
      line-height: 20px;
      font-weight: 450;
      text-overflow: ellipsis;
      white-space: nowrap;
      transition:
        opacity 0.12s ease,
        margin-left 0.18s ease,
        max-width 0.18s ease;
    }

    & > svg:focus {
      outline: none;
    }
    & > svg:focus-visible {
      outline: none;
    }

    &.active {
      border-color: transparent;
      background-color: var(--brand-50);
      font-weight: 600;
      color: var(--main-color);
    }

    &.primary-action {
      margin-bottom: 8px;
      border-color: var(--color-primary);
      background-color: var(--color-primary);
      color: var(--gray-0);
      box-shadow: 0 4px 10px color-mix(in srgb, var(--color-primary) 18%, transparent);

      &:hover {
        border-color: var(--color-primary-hover);
        background-color: var(--color-primary-hover);
        color: var(--gray-0);
        box-shadow: 0 5px 12px color-mix(in srgb, var(--color-primary) 24%, transparent);
      }
    }

    &.warning {
      color: var(--color-error-500);
    }

    &:hover {
      border-color: transparent;
      background-color: var(--gray-50);
      color: var(--main-color);
    }

    &.api-docs {
      padding: 10px 12px;
    }
    &.docs {
      display: none;
    }
    &.theme-toggle-nav {
      .theme-toggle-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        cursor: pointer;
        color: var(--gray-1000);
        transition: color 0.2s ease-in-out;

        &:hover {
          color: var(--main-color);
        }
      }
    }
    &.user-info {
      margin-bottom: 8px;
      height: auto;
      padding: 8px 3px 0;
      overflow: hidden;
      border-top: 1px solid var(--color-border);
      border-radius: 0;

      :deep(.user-info-component) {
        width: 100%;
      }

      :deep(.user-info-dropdown) {
        width: 100%;
        height: @sidebar-item-height;
        border-radius: 8px;
        transition:
          background-color 0.2s ease,
          color 0.2s ease;
      }

      :deep(.user-info-dropdown:hover) {
        background: var(--main-20);
        color: var(--main-color);
      }
      :deep(.user-name) {
        flex: 1 1 auto;
      }

      :deep(.user-task-center) {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        padding: 0;
        border: 1px solid transparent;
        border-radius: 6px;
        background: transparent;
        color: var(--gray-600);
        cursor: pointer;
        transition:
          background-color 0.2s ease,
          color 0.2s ease;

        &:hover,
        &.active {
          background: var(--main-30);
          color: var(--main-color);
        }

        .task-center-badge {
          display: flex;
          justify-content: center;
        }

        .icon {
          display: block;
          width: 16px;
          height: 16px;
        }
      }
    }
  }
}

.app-layout.sidebar-collapsed {
  .header {
    flex-basis: @sidebar-collapsed-width;
    width: @sidebar-collapsed-width;
    align-items: stretch;
    padding: @sidebar-padding;

    .sidebar-brand {
      justify-content: flex-start;
      width: 100%;
    }

    .brand-expand-button {
      flex: 0 0 @sidebar-item-height;
      justify-content: center;
      width: @sidebar-item-height;
      padding: 0 6px;
      border-radius: 8px;

      .brand-expand-icon {
        display: none;
        width: @sidebar-icon-size;
        height: @sidebar-icon-size;
        color: var(--main-color);
      }

      &:hover,
      &:focus-visible {
        background: var(--main-20);
        outline: none;

        .brand-avatar-image {
          display: none;
        }

        .brand-expand-icon {
          display: block;
        }
      }
    }

    .nav {
      align-items: stretch;
      width: 100%;
    }

    .nav-item {
      justify-content: flex-start;
      width: @sidebar-item-height;
      padding: 0 10px;

      .nav-text {
        max-width: 0;
        margin-left: 0;
        opacity: 0;
        pointer-events: none;
      }

      &.user-info {
        padding: 0;
        :deep(.user-info-actions) {
          display: none;
        }
      }
    }
  }
}
</style>
