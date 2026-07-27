import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const instance = axios.create({
  baseURL: '',
  timeout: 60000
})

instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

instance.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.detail || error.message || '请求失败'

    if (status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      ElMessage.warning('登录已过期，请重新登录')
      window.location.href = '/login'
    } else if (status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else if (status === 404) {
      ElMessage.error('请求的资源不存在')
    } else if (status === 422) {
      ElMessage.error('请求参数错误')
    } else if (status && status >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else if (!error.response) {
      ElMessage.error('网络连接失败，请检查网络')
    }

    return Promise.reject(error)
  }
)

export default instance
