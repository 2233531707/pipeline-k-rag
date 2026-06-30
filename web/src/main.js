import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { useInfoStore } from '@/stores/info'
import { useUserStore } from '@/stores/user'

import App from './App.vue'
import router from './router'
import { initializeDesktopRuntime, hasConfiguredBackendUrl, isDesktopMode } from './runtime/desktop'

import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import '@/assets/css/main.css'

await initializeDesktopRuntime()

const app = createApp(App)
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

app.use(pinia)
const userStore = useUserStore()
userStore.hydratePersistedAuth()
app.use(router)
app.use(Antd)

// 预加载信息配置
const infoStore = useInfoStore()
if (!isDesktopMode() || hasConfiguredBackendUrl()) {
  infoStore.loadInfoConfig()
}

app.mount('#app')
