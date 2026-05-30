<template>
  <div class="chamados-section">
    <!-- Controles -->
    <div class="controls">
      <div class="section-header">
        <span class="section-title">Chamados</span>
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

    <!-- Tabela de chamados -->
    <div v-else class="chamados-grid">
      <div
        v-for="c in chamados"
        :key="c.chave"
        class="chamado-row"
        :class="{ 'sem-org': c.organizacao_atual === 'Não preenchido' }"
        @click="$emit('selecionar', c)"
      >
        <div class="chamado-chave">
          <span class="chave-tag">{{ c.chave }}</span>
        </div>

        <div class="chamado-info">
          <div class="chamado-titulo">{{ c.titulo }}</div>
          <div class="chamado-meta">
            <span class="meta-item">👤 {{ c.usuario_id }}</span>
            <span class="meta-item">🗓 {{ c.criado_em }}</span>
          </div>
        </div>

        <div class="chamado-org">
          <span
            class="org-badge"
            :class="c.organizacao_atual === 'Não preenchido' ? 'org-vazia' : 'org-ok'"
          >
            {{ c.organizacao_atual === 'Não preenchido' ? '⚠ Pendente' : c.organizacao_atual }}
          </span>
        </div>

        <div class="chamado-status">
          <span class="status-pill" :class="statusClass(c.status)">{{ c.status }}</span>
        </div>

        <div class="chamado-action">
          <button class="btn-ia" @click.stop="$emit('selecionar', c)">Analisar IA →</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  chamados: { type: Array, default: () => [] },
  loading: Boolean,
  dias: { type: Number, default: 90 },
  limite: { type: Number, default: 50 },
})

defineEmits(['selecionar', 'reload'])

function statusClass(status) {
  const s = (status || '').toLowerCase()
  if (s.includes('open') || s.includes('aberto')) return 'status-open'
  if (s.includes('progress') || s.includes('andamento')) return 'status-progress'
  if (s.includes('done') || s.includes('resolvido') || s.includes('fechado')) return 'status-done'
  return 'status-default'
}
</script>

<style scoped>
.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
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
  background: rgba(10, 132, 255, 0.15);
  border: 1px solid rgba(10, 132, 255, 0.2);
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
  padding: 8px 16px;
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
  border-color: rgba(255, 255, 255, 0.2);
}

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

.chamados-grid { display: flex; flex-direction: column; gap: 8px; }

.chamado-row {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
  display: grid;
  grid-template-columns: 100px 1fr auto auto auto;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all var(--transition);
}

.chamado-row:hover {
  border-color: rgba(10, 132, 255, 0.3);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  transform: translateX(3px);
}

.chamado-row.sem-org { border-left: 3px solid var(--accent); }

.chave-tag {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  background: rgba(10, 132, 255, 0.1);
  border: 1px solid rgba(10, 132, 255, 0.2);
  padding: 3px 8px;
  border-radius: 6px;
}

.chamado-titulo {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.chamado-meta { display: flex; gap: 12px; margin-top: 4px; }

.meta-item { font-size: 11px; color: var(--text-dim); font-family: var(--mono); }

.org-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.org-ok {
  background: rgba(52, 199, 89, 0.12);
  border: 1px solid rgba(52, 199, 89, 0.25);
  color: var(--success);
}

.org-vazia {
  background: rgba(255, 55, 95, 0.12);
  border: 1px solid rgba(255, 55, 95, 0.25);
  color: var(--accent);
}

.status-pill {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--mono);
  padding: 3px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.status-open     { background: rgba(10, 132, 255, 0.15); color: var(--primary); }
.status-progress { background: rgba(255, 159, 10, 0.15); color: var(--warning); }
.status-done     { background: rgba(52, 199, 89, 0.15);  color: var(--success); }
.status-default  { background: rgba(142, 142, 147, 0.15); color: var(--text-dim); }

.btn-ia {
  background: linear-gradient(135deg, var(--primary) 0%, #0066cc 100%);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 7px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition);
}

.btn-ia:hover { box-shadow: 0 4px 16px rgba(10, 132, 255, 0.4); transform: translateY(-1px); }
</style>
