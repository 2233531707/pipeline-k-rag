<template>
  <div class="desktop-connection-view">
    <main class="connection-main">
      <section class="connection-panel">
        <header class="panel-header">
          <p class="eyebrow">Desktop Client</p>
          <h1>连接独立后端服务器</h1>
          <p class="description">
            输入独立后端服务器地址。连接成功后，客户端会进入登录页或独立后端服务器首启初始化流程。
          </p>
        </header>

        <a-form layout="vertical" :model="{ backendUrl }" @finish="handleSaveAndContinue">
          <a-form-item
            label="后端服务器地址"
            name="backendUrl"
            :rules="[{ required: true, message: '请输入后端服务器地址' }]"
          >
            <a-input
              v-model:value="backendUrl"
              placeholder="https://server.example.com"
              size="large"
            />
          </a-form-item>

          <div v-if="currentBackendUrl" class="current-target">
            当前已保存地址：{{ currentBackendUrl }}
          </div>

          <a-alert v-if="resultMessage" :type="resultType" :message="resultMessage" show-icon />

          <div class="action-row">
            <a-button size="large" @click="handleHealthCheck" :loading="checking">
              检查连接
            </a-button>
            <a-button type="primary" html-type="submit" size="large" :loading="saving">
              保存并继续
            </a-button>
          </div>
        </a-form>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { healthApi } from '@/apis/system_api'
import {
  getBackendUrl,
  notifyDesktopBackendChanged,
  normalizeBackendUrl,
  setConnectionConfig
} from '@/runtime/desktop'
import { useUserStore } from '@/stores/user'
import { useInfoStore } from '@/stores/info'

const router = useRouter()
const userStore = useUserStore()
const infoStore = useInfoStore()

const backendUrl = ref('')
const currentBackendUrl = ref('')
const checking = ref(false)
const saving = ref(false)
const resultMessage = ref('')
const resultType = ref('success')

onMounted(() => {
  const savedBackendUrl = getBackendUrl()
  backendUrl.value = savedBackendUrl
  currentBackendUrl.value = savedBackendUrl
})

const runHealthCheck = async (targetUrl) => {
  const response = await healthApi.checkHealth({ baseUrl: targetUrl })
  if (response.status !== 'ok') {
    throw new Error(response.message || '服务端状态异常')
  }
  return response
}

const handleHealthCheck = async () => {
  try {
    checking.value = true
    resultMessage.value = ''

    const normalized = normalizeBackendUrl(backendUrl.value)
    await runHealthCheck(normalized)
    resultType.value = 'success'
    resultMessage.value = '连接成功，可以继续进入登录流程。'
  } catch (error) {
    resultType.value = 'error'
    resultMessage.value = error.message || '连接失败，请检查服务器地址'
  } finally {
    checking.value = false
  }
}

const handleSaveAndContinue = async () => {
  try {
    saving.value = true
    resultMessage.value = ''

    const normalized = normalizeBackendUrl(backendUrl.value)
    await runHealthCheck(normalized)
    const previousBackendUrl = currentBackendUrl.value
    const backendChanged = Boolean(previousBackendUrl && previousBackendUrl !== normalized)

    await setConnectionConfig({ backendUrl: normalized })
    currentBackendUrl.value = normalized

    if (backendChanged) {
      userStore.logout()
      notifyDesktopBackendChanged({
        previousBackendUrl,
        nextBackendUrl: normalized
      })
      message.info('服务器地址已变更，请重新登录')
    }

    await infoStore.loadInfoConfig(true)
    message.success('服务器地址已保存')
    router.push(userStore.isLoggedIn ? '/agent' : '/login')
  } catch (error) {
    resultType.value = 'error'
    resultMessage.value = error.message || '保存失败，请检查服务器地址'
  } finally {
    saving.value = false
  }
}
</script>

<style lang="less" scoped>
.desktop-connection-view {
  min-height: 100vh;
  display: flex;
  background:
    radial-gradient(circle at top right, var(--main-50), transparent 32%),
    linear-gradient(180deg, var(--gray-20), var(--gray-0));
}

.connection-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.connection-panel {
  width: 100%;
  max-width: 560px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 20px 40px var(--shadow-1);
}

.panel-header {
  margin-bottom: 24px;

  .eyebrow {
    margin: 0 0 8px;
    font-size: 12px;
    font-weight: 600;
    color: var(--main-color);
    text-transform: uppercase;
  }

  h1 {
    margin: 0 0 12px;
    font-size: 28px;
    line-height: 1.2;
    color: var(--gray-900);
  }

  .description {
    margin: 0;
    color: var(--gray-600);
    line-height: 1.6;
  }
}

.current-target {
  margin: -8px 0 16px;
  font-size: 13px;
  color: var(--gray-500);
}

.action-row {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

@media (max-width: 640px) {
  .connection-main {
    padding: 20px;
  }

  .connection-panel {
    padding: 24px;
  }

  .action-row {
    flex-direction: column;
  }
}
</style>
