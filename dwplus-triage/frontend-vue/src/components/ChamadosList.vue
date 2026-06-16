<template>
  <div class="chamados-section">
    <!-- Controles -->
    <div class="controls">
      <div class="section-header">
        <span class="section-title">{{ titulo }}</span>
        <span v-if="!loading" class="count-badge">{{ chamados.length }}</span>
      </div>
      <div class="controls-right">
        <span class="filter-info">{{ dias }}d · {{ limite }} max</span>
        <button class="btn-secondary" @click="$emit('reload')">
          <span v-if="loading" class="spinner-sm"></span>
          <span v-else>↻</span>
          Atualizar
        </button>
      </div>
    </div>

    <!-- Estado vazio / carregando -->
    <div v-if="loading" class="empty-state">
      <div class="spinner"></div>
      <p>Buscando chamados no Jira...</p>
    </div>

    <div v-else-if="chamados.length === 0" class="empty-state">
      <p style="font-size: 32px; margin-bottom: 8px">📭</p>
      <p>Nenhum chamado encontrado nos últimos {{ dias }} dias.</p>
    </div>

    <!-- Tabela estilo Jira -->
    <div v-else class="table-wrapper">
      <table class="jira-table">
        <thead>
          <tr>
            <th class="col-chave">Chave</th>
            <th class="col-criado">Criado</th>
            <th class="col-relator">Relator</th>
            <th class="col-org">Organizations</th>
            <th class="col-resumo">Resumo</th>
            <th class="col-descricao">Descrição</th>
            <th class="col-action"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in chamados"
            :key="c.chave"
            class="jira-row"
            :class="{ 'sem-org': c.organizacao_atual === 'Não preenchido' }"
            @click="$emit('selecionar', c)"
          >
            <!-- Chave -->
            <td class="col-chave">
              <span class="chave-link">{{ c.chave }}</span>
            </td>

            <!-- Criado -->
            <td class="col-criado">{{ formatarData(c.criado_em) }}</td>

            <!-- Relator -->
            <td class="col-relator">
              <span class="relator-text" :title="c.email">{{ c.email }}</span>
            </td>

            <!-- Organizations -->
            <td class="col-org">
              <span
                class="org-tag"
                :class="c.organizacao_atual === 'Não preenchido' ? 'org-vazia' : 'org-ok'"
              >
                {{ c.organizacao_atual === 'Não preenchido' ? '—' : c.organizacao_atual }}
              </span>
            </td>

            <!-- Resumo -->
            <td class="col-resumo">
              <span class="resumo-link">{{ c.titulo }}</span>
            </td>

            <!-- Descrição -->
            <td class="col-descricao">
              <span class="descricao-text">{{ c.descricao }}</span>
            </td>

            <!-- Ação -->
            <td class="col-action" @click.stop>
              <button class="btn-ia" @click="$emit('selecionar', c)">Analisar IA →</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
defineProps({
  chamados: { type: Array, default: () => [] },
  loading: Boolean,
  dias: { type: Number, default: 90 },
  limite: { type: Number, default: 50 },
  titulo: { type: String, default: 'Chamados' },
})

defineEmits(['selecionar', 'reload'])

function formatarData(data) {
  if (!data) return '—'
  // "2026-06-16" → "16/jun/26"
  const meses = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
  const [ano, mes, dia] = data.split('-')
  if (!ano || !mes || !dia) return data
  return `${dia}/${meses[parseInt(mes) - 1]}/${ano.slice(2)}`
}

function statusClass(status) {
  const s = (status || '').toLowerCase()
  if (s.includes('open') || s.includes('aberto')) return 'status-open'
  if (s.includes('progress') || s.includes('andamento')) return 'status-progress'
  if (s.includes('done') || s.includes('resolvido') || s.includes('fechado') || s.includes('cancelado')) return 'status-done'
  if (s.includes('aguardando')) return 'status-waiting'
  return 'status-default'
}

function prioClass(p) {
  const v = (p || '').toLowerCase()
  if (v.includes('alta') || v.includes('high') || v.includes('urgente')) return 'prio-high'
  if (v.includes('baixa') || v.includes('low')) return 'prio-low'
  return 'prio-medium'
}

function prioSimbolo(p) {
  const v = (p || '').toLowerCase()
  if (v.includes('alta') || v.includes('high') || v.includes('urgente')) return '↑'
  if (v.includes('baixa') || v.includes('low')) return '↓'
  return '='
}
</script>

<style scoped>
/* ── Controles ────────────────────────────────────────────────────────── */
.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.controls-right {
  margin-left: auto;
  display: flex;
  gap: 12px;
  align-items: center;
}

.section-header { display: flex; align-items: center; gap: 10px; }

.section-title {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.count-badge {
  background: rgba(0, 82, 204, 0.12);
  border: 1px solid rgba(0, 82, 204, 0.2);
  color: var(--primary);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
}

.filter-info {
  font-size: 12px;
  color: var(--text-dim);
  font-family: var(--mono);
}

.btn-secondary {
  background: transparent;
  color: var(--text-dim);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all var(--transition);
}

.btn-secondary:hover {
  color: var(--text);
  background: var(--overlay);
  border-color: var(--text-muted);
}

/* ── Estados ──────────────────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-dim);
}

.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

.spinner-sm {
  width: 14px; height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Wrapper da tabela ────────────────────────────────────────────────── */
.table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--card);
}

/* ── Tabela ───────────────────────────────────────────────────────────── */
.jira-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  color: var(--text);
  table-layout: fixed;
}

/* Cabeçalho */
.jira-table thead tr {
  background: #F4F5F7;
  border-bottom: 2px solid var(--border);
}

.jira-table th {
  padding: 8px 10px;
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  white-space: nowrap;
  user-select: none;
}

/* Larguras das colunas */
.col-t       { width: 32px;  text-align: center; }
.col-chave   { width: 96px; }
.col-criado  { width: 84px; }
.col-relator { width: 180px; }
.col-org     { width: 160px; }
.col-p       { width: 32px;  text-align: center; }
.col-resumo  { width: 200px; }
.col-descricao { min-width: 160px; }
.col-status  { width: 160px; }
.col-action  { width: 110px; text-align: right; }

/* Linhas */
.jira-row {
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background var(--transition);
}

.jira-row:last-child { border-bottom: none; }

.jira-row:hover { background: #EAF2FF; }

.jira-row.sem-org { border-left: 3px solid var(--accent); }

.jira-table td {
  padding: 8px 10px;
  vertical-align: middle;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Células ──────────────────────────────────────────────────────────── */

/* Ícone de tipo */
.type-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.type-icon.prio-high    { color: #DE350B; }
.type-icon.prio-medium  { color: #FF8B00; }
.type-icon.prio-low     { color: #0052CC; }

/* Chave */
.chave-link {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
}

.chave-link:hover { text-decoration: underline; }

/* Data */
.col-criado td, .jira-table td.col-criado {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--mono);
}

/* Relator */
.relator-text {
  font-size: 12px;
  color: var(--text-dim);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Organização */
.org-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.org-ok {
  background: rgba(0, 82, 204, 0.1);
  color: var(--primary);
  border: 1px solid rgba(0, 82, 204, 0.2);
}

.org-vazia {
  background: rgba(222, 53, 11, 0.08);
  color: var(--accent);
  border: 1px solid rgba(222, 53, 11, 0.2);
}

/* Prioridade */
.prio-icon {
  font-size: 14px;
  font-weight: 700;
  font-family: var(--mono);
}

.prio-icon.prio-high   { color: #DE350B; }
.prio-icon.prio-medium { color: #FF8B00; }
.prio-icon.prio-low    { color: #0052CC; }

/* Resumo */
.resumo-link {
  color: var(--primary);
  font-weight: 500;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resumo-link:hover { text-decoration: underline; }

/* Descrição */
.descricao-text {
  color: var(--text-dim);
  font-size: 12px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status */
.status-pill {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--mono);
  padding: 3px 8px;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  white-space: nowrap;
}

.status-open    { background: rgba(0, 82, 204, 0.12);  color: var(--primary); }
.status-progress { background: rgba(255, 139, 0, 0.12); color: var(--warning); }
.status-done    { background: rgba(0, 135, 90, 0.12);  color: var(--success); }
.status-waiting { background: rgba(94, 108, 132, 0.12); color: var(--text-dim); }
.status-default { background: rgba(94, 108, 132, 0.12); color: var(--text-dim); }

/* Botão IA */
.btn-ia {
  background: linear-gradient(135deg, var(--primary) 0%, #0747A6 100%);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 5px 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition);
}

.btn-ia:hover {
  box-shadow: 0 3px 10px rgba(0, 82, 204, 0.4);
  transform: translateY(-1px);
}
</style>
