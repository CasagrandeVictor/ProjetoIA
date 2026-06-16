<template>
  <div class="chamados-section">
    <!-- Controles -->
    <div class="controls">
      <div class="section-header">
        <span class="section-title">{{ titulo }}</span>
        <span v-if="!loading" class="count-badge">{{ chamadosFiltrados.length }}</span>
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

    <!-- Filtros de atendimento -->
    <div v-if="!loading && chamados.length" class="filtros">
      <button
        v-for="f in filtros"
        :key="f.id"
        :class="['btn-filtro', { active: filtroAtivo === f.id }]"
        @click="filtroAtivo = f.id"
      >
        {{ f.label }}
        <span class="filtro-badge">{{ contagemFiltro(f.id) }}</span>
      </button>
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

    <div v-else-if="chamadosFiltrados.length === 0" class="empty-state">
      <p style="font-size: 32px; margin-bottom: 8px">🔍</p>
      <p>Nenhum chamado com o filtro selecionado.</p>
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
            <th class="col-atend">Atendimento</th>
            <th class="col-resumo">Resumo</th>
            <th class="col-descricao">Descrição</th>
            <th class="col-action"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in chamadosFiltrados"
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

            <!-- Atendimento -->
            <td class="col-atend">
              <span
                v-if="c.atendimento"
                class="atend-tag"
                :class="c.atendimento === 'Presencial' ? 'tag-presencial' : 'tag-remoto'"
              >
                {{ c.atendimento }}
              </span>
              <span v-else class="atend-vazio">—</span>
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
import { ref, computed } from 'vue'

const props = defineProps({
  chamados: { type: Array, default: () => [] },
  loading: Boolean,
  dias: { type: Number, default: 90 },
  limite: { type: Number, default: 50 },
  titulo: { type: String, default: 'Chamados' },
})

defineEmits(['selecionar', 'reload'])

// ── Filtros de atendimento ────────────────────────────────────────────────────
const filtroAtivo = ref('todos')

const filtros = [
  { id: 'todos',      label: 'Todos' },
  { id: 'presencial', label: 'Presencial' },
  { id: 'remoto',     label: 'Remoto' },
  { id: 'pendente',   label: 'Sem atendimento' },
]

const chamadosFiltrados = computed(() => {
  if (filtroAtivo.value === 'presencial') return props.chamados.filter(c => c.atendimento === 'Presencial')
  if (filtroAtivo.value === 'remoto')     return props.chamados.filter(c => c.atendimento === 'Remoto')
  if (filtroAtivo.value === 'pendente')   return props.chamados.filter(c => !c.atendimento)
  return props.chamados
})

function contagemFiltro(id) {
  if (id === 'todos')      return props.chamados.length
  if (id === 'presencial') return props.chamados.filter(c => c.atendimento === 'Presencial').length
  if (id === 'remoto')     return props.chamados.filter(c => c.atendimento === 'Remoto').length
  if (id === 'pendente')   return props.chamados.filter(c => !c.atendimento).length
  return 0
}

function formatarData(data) {
  if (!data) return '—'
  const meses = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
  const [ano, mes, dia] = data.split('-')
  if (!ano || !mes || !dia) return data
  return `${dia}/${meses[parseInt(mes) - 1]}/${ano.slice(2)}`
}
</script>

<style scoped>
/* ── Controles ────────────────────────────────────────────────────────── */
.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
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

/* ── Filtros ──────────────────────────────────────────────────────────── */
.filtros {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.btn-filtro {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all var(--transition);
}

.btn-filtro:hover { color: var(--text); background: var(--overlay); }

.btn-filtro.active {
  background: rgba(0, 82, 204, 0.1);
  border-color: rgba(0, 82, 204, 0.3);
  color: var(--primary);
}

.filtro-badge {
  background: var(--overlay);
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 10px;
  font-family: var(--mono);
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
.col-chave    { width: 90px; }
.col-criado   { width: 80px; }
.col-relator  { width: 170px; }
.col-org      { width: 155px; }
.col-atend    { width: 105px; }
.col-resumo   { width: 190px; }
.col-descricao { min-width: 150px; }
.col-action   { width: 110px; text-align: right; }

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
.chave-link {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
}

.relator-text {
  font-size: 12px;
  color: var(--text-dim);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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

/* Tags de atendimento */
.atend-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 3px;
  white-space: nowrap;
}

.tag-presencial {
  background: rgba(255, 139, 0, 0.12);
  color: var(--warning);
  border: 1px solid rgba(255, 139, 0, 0.25);
}

.tag-remoto {
  background: rgba(0, 82, 204, 0.1);
  color: var(--primary);
  border: 1px solid rgba(0, 82, 204, 0.2);
}

.atend-vazio {
  color: var(--text-muted);
  font-size: 12px;
}

.resumo-link {
  color: var(--primary);
  font-weight: 500;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.descricao-text {
  color: var(--text-dim);
  font-size: 12px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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
