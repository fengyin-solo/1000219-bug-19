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

    <div v-if="detail" class="modal-mask" @click.self="closeDetail">
      <div class="modal-card" role="dialog" aria-label="电站档案详情">
        <header class="modal-head">
          <h3>电站档案详情</h3>
          <button class="link" type="button" @click="closeDetail">关闭</button>
        </header>
        <dl class="detail-grid">
          <template v-for="column in columns" :key="column">
            <dt>{{ column }}</dt>
            <dd>{{ detail[column] ?? '—' }}</dd>
          </template>
        </dl>
        <footer class="modal-foot">
          <button class="btn primary" type="button" @click="openEdit(detail)">编辑此档案</button>
        </footer>
      </div>
    </div>

    <div v-if="editing" class="modal-mask" @click.self="closeEdit">
      <div class="modal-card" role="dialog" aria-label="电站档案编辑">
        <header class="modal-head">
          <h3>{{ editing.id == null ? '登记光伏电站' : `编辑电站档案 #${editing.id}` }}</h3>
          <button class="link" type="button" @click="closeEdit">取消</button>
        </header>
        <form class="edit-form" @submit.prevent="saveEdit">
          <label v-for="field in editFields" :key="field" class="edit-item">
            <span>{{ field }}</span>
            <input
              v-model="editing[field]"
              :type="field === '并网日期' ? 'date' : 'text'"
              :placeholder="`请输入${field}`"
            />
          </label>
          <footer class="modal-foot">
            <button class="btn primary" type="submit" :disabled="saving">
              {{ saving ? '保存中…' : '保存' }}
            </button>
            <button class="btn ghost" type="button" @click="closeEdit">取消</button>
          </footer>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/plant'
const columns = ["电站编号", "电站名称", "装机容量", "并网日期", "所属区域", "运维负责人", "组件厂家", "电站状态"]
const editFields = ["电站编号", "电站名称", "装机容量", "并网日期", "所属区域", "运维负责人", "组件厂家"]
const actions = ["确认并网", "进入维护", "标记退役"]
const statuses = ["建设中", "并网运行", "停运维护", "已退役"]
const stats = [{"label": "运行电站", "value": 0}, {"label": "停运电站", "value": 0}, {"label": "总装机容量", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const detail = ref<Row | null>(null)
const editing = ref<Row | null>(null)
const saving = ref(false)

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function blankForm(): Row {
  const form: Row = { id: null }
  for (const field of editFields) {
    form[field] = ''
  }
  return form
}

function openCreate() {
  errorMessage.value = ''
  editing.value = blankForm()
}

function closeDetail() {
  detail.value = null
}

function closeEdit() {
  editing.value = null
}

async function fetchEntry(id: string | number): Promise<Row> {
  const response = await request(`${ENDPOINT}/${id}`)
  if (!response.ok) {
    throw new Error('电站档案读取失败，请刷新列表后重试')
  }
  return (await response.json()) as Row
}

async function openDetail(row: Row) {
  errorMessage.value = ''
  try {
    // 一律按记录 id 取最新详情，不用列表行里的旧快照
    detail.value = await fetchEntry(row.id as number)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电站档案详情读取失败'
  }
}

async function openEdit(row: Row) {
  errorMessage.value = ''
  try {
    // 编辑前按 id 重新取数，避免把上一行或上一次提交的旧值带进表单
    const fresh = await fetchEntry(row.id as number)
    const form: Row = { id: fresh.id }
    for (const field of editFields) {
      form[field] = fresh[field] ?? ''
    }
    detail.value = null
    editing.value = form
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电站档案读取失败，无法编辑'
  }
}

async function saveEdit() {
  if (!editing.value || saving.value) {
    return
  }
  errorMessage.value = ''
  saving.value = true
  const id = editing.value.id
  const values: Record<string, string | number | null> = {}
  for (const field of editFields) {
    values[field] = editing.value[field]
  }
  try {
    // id 为空走登记，否则按记录 id 回写，两个入口共用同一份标识
    const isCreate = id === null || id === undefined || id === ''
    const response = await request(isCreate ? ENDPOINT : `${ENDPOINT}/${id}`, {
      method: isCreate ? 'POST' : 'PUT',
      body: JSON.stringify({ values }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message ?? '电站档案保存未生效，请稍后重试')
    }
    editing.value = null
    await reload()
    // 详情弹窗若正开着同一条记录，用回写结果同步刷新，不留旧值
    if (detail.value && payload.entry && String(detail.value.id) === String(payload.entry.id)) {
      detail.value = payload.entry as Row
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

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.modal-card {
  background: #fff;
  border-radius: 8px;
  border: 1px solid var(--border);
  padding: 16px 20px;
  width: 520px;
  max-width: calc(100vw - 48px);
  max-height: calc(100vh - 96px);
  overflow: auto;
}
.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.modal-head h3 {
  margin: 0;
  font-size: 15px;
}
.detail-grid {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 8px 12px;
  margin: 0;
  font-size: 13px;
}
.detail-grid dt {
  color: var(--muted);
}
.detail-grid dd {
  margin: 0;
}
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.edit-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.edit-item span {
  width: 72px;
  color: var(--muted);
}
.edit-item input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
}
.modal-foot {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
