<template>
  <section class="page" data-module="plant">
    <header class="page-head">
      <div>
        <h2>电站档案管理</h2>
        <p class="page-desc">维护光伏电站，围绕电站编号、电站名称、装机容量、并网日期做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记光伏电站</button>
        <button class="btn" type="button" @click="exportRows">导出电站档案清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">详情</button>
            <button class="link" type="button" @click="openEdit(row)">编辑</button>
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无电站档案数据，可先登记光伏电站</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条电站档案记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="detailId !== null" class="modal-mask" @click.self="closeDetail">
      <div class="modal-card">
        <header class="modal-head">
          <h3>电站档案详情</h3>
          <button class="link" type="button" @click="closeDetail">关闭</button>
        </header>
        <p v-if="detailLoading" class="empty-state">正在读取档案详情…</p>
        <dl v-else-if="detail" class="detail-grid">
          <template v-for="column in columns" :key="column">
            <dt>{{ column }}</dt>
            <dd>{{ detail[column] ?? '—' }}</dd>
          </template>
        </dl>
        <footer class="modal-foot">
          <button class="btn" type="button" :disabled="!detail" @click="detail && openEdit(detail)">编辑</button>
        </footer>
      </div>
    </div>

    <div v-if="editingId !== null" class="modal-mask" @click.self="closeEdit">
      <form class="modal-card" @submit.prevent="submitEdit">
        <header class="modal-head">
          <h3>编辑电站档案</h3>
          <button class="link" type="button" @click="closeEdit">取消</button>
        </header>
        <div class="edit-form">
          <label v-for="field in editableFields" :key="field">
            <span>{{ field }}</span>
            <input
              v-model="draft[field]"
              :type="field === '并网日期' ? 'date' : 'text'"
              :required="requiredFields.includes(field)"
            />
          </label>
        </div>
        <footer class="modal-foot">
          <button class="btn ghost" type="button" @click="closeEdit">取消</button>
          <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        </footer>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/plant'
const columns = ["电站编号", "电站名称", "装机容量", "并网日期", "所属区域", "运维负责人", "组件厂家", "电站状态"]
const actions = ["确认并网", "进入维护", "标记退役"]
const statuses = ["建设中", "并网运行", "停运维护", "已退役"]
const stats = [{"label": "运行电站", "value": 0}, {"label": "停运电站", "value": 0}, {"label": "总装机容量", "value": 0}]
// 列表、详情、编辑弹窗只认记录 id 这一个标识；电站编号是普通可编辑字段，不当定位键用。
const editableFields = ["电站编号", "电站名称", "装机容量", "并网日期", "所属区域", "运维负责人", "组件厂家"]
const requiredFields = ["电站编号", "电站名称", "装机容量"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const detailId = ref<number | null>(null)
const detail = ref<Row | null>(null)
const detailLoading = ref(false)
const editingId = ref<number | null>(null)
const draft = ref<Row>({})
const saving = ref(false)

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '光伏电站登记入口尚未接入审批流'
}

async function fetchDetail(id: number) {
  detailLoading.value = true
  try {
    const response = await request(`${ENDPOINT}/${id}`)
    if (!response.ok) {
      throw new Error('电站档案详情读取失败')
    }
    detail.value = await response.json()
  } catch (error) {
    detailId.value = null
    detail.value = null
    errorMessage.value = error instanceof Error ? error.message : '电站档案详情读取失败'
  } finally {
    detailLoading.value = false
  }
}

async function openDetail(row: Row) {
  errorMessage.value = ''
  const id = Number(row.id)
  detailId.value = id
  detail.value = null
  // 详情每次都按 id 重新拉取，不复用列表行对象，避免停留旧值
  await fetchDetail(id)
}

function closeDetail() {
  detailId.value = null
  detail.value = null
}

function openEdit(row: Row) {
  errorMessage.value = ''
  // 打开瞬间锁定记录 id，之后提交只回写这条记录，与列表行序无关
  editingId.value = Number(row.id)
  draft.value = Object.fromEntries(editableFields.map((field) => [field, row[field] ?? '']))
}

function closeEdit() {
  editingId.value = null
  draft.value = {}
}

async function submitEdit() {
  if (editingId.value === null || saving.value) {
    return
  }
  const id = editingId.value
  errorMessage.value = ''
  saving.value = true
  try {
    const response = await request(`${ENDPOINT}/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ values: draft.value }),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok || payload?.ok === false) {
      throw new Error(payload?.message ?? payload?.detail ?? '电站档案保存失败')
    }
    closeEdit()
    await reload()
    // 详情若正打开同一条记录，按 id 重新拉一遍，保证三个入口看到的是同一份数据
    if (detailId.value === id) {
      await fetchDetail(id)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电站档案保存失败'
  } finally {
    saving.value = false
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('电站档案动作未生效，请稍后重试')
    }
    await reload()
    if (detailId.value === Number(row.id)) {
      await fetchDetail(Number(row.id))
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电站档案操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('光伏电站列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电站档案列表读取失败'
  }
}

onMounted(reload)
</script>
