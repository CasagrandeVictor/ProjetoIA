<template>
  <div class="dashboard">
    <!-- Cards de estatísticas -->
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-label">Em Aberto</span>
        <div class="stat-value" :class="{ 'loading-val': loading }">
          {{ loading ? '—' : stats.total }}
        </div>
        <span class="stat-icon">📋</span>
      </div>

      <div class="stat-card danger">
        <span class="stat-label">Sem Organização</span>
        <div class="stat-value" :class="{ 'loading-val': loading }">
          {{ loading ? '—' : stats.sem_organizacao }}
        </div>
        <span class="stat-icon">⚠️</span>
      </div>

      <div class="stat-card" :class="percentualClass">
        <span class="stat-label">% Pendente</span>
        <div class="stat-value" :class="{ 'loading-val': loading }">
          {{ loading ? '—' : stats.percentual_pendente + '%' }}
        </div>
        <span class="stat-icon">📊</span>
      </div>

      <div class="stat-card success">
        <span class="stat-label">Com Organização</span>
        <div class="stat-value" :class="{ 'loading-val': loading }">
          {{ loading ? '—' : stats.total - stats.sem_organizacao }}
        </div>
        <span class="stat-icon">✅</span>
      </div>
    </div>

    <!-- Erro amigável -->
    <div v-if="erro" class="alert-error">
      ⚠️ {{ erro }}
      <button class="btn-link" @click="$emit('reload')">Tentar novamente</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({ total: 0, sem_organizacao: 0, percentual_pendente: 0 }),
  },
  loading: Boolean,
  erro: String,
})

defineEmits(['reload'])

const percentualClass = computed(() => {
  const p = props.stats.percentual_pendente || 0
  if (p >= 50) return 'danger'
  if (p >= 20) return 'warning'
  return 'success'
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  position: relative;
  overflow: hidden;
  transition: transform var(--transition), border-color var(--transition), box-shadow var(--transition);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--card-accent, linear-gradient(90deg, var(--primary), var(--secondary)));
  opacity: 0;
  transition: opacity var(--transition);
}

.stat-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4); }
.stat-card:hover::before { opacity: 1; }

.stat-card.danger  { --card-accent: linear-gradient(90deg, var(--accent), #ff6b8a); }
.stat-card.warning { --card-accent: linear-gradient(90deg, var(--warning), #ffcc00); }
.stat-card.success { --card-accent: linear-gradient(90deg, var(--success), #68d391); }

.stat-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--text-dim);
  margin-bottom: 10px;
  display: block;
}

.stat-value {
  font-family: var(--mono);
  font-size: 38px;
  font-weight: 700;
  line-height: 1;
  color: var(--text);
}

.stat-value.loading-val { opacity: 0.3; }

.stat-icon {
  position: absolute;
  right: 20px; top: 20px;
  font-size: 22px;
  opacity: 0.25;
}

.alert-error {
  background: rgba(222, 53, 11, 0.1);
  border: 1px solid rgba(222, 53, 11, 0.3);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  color: var(--accent);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-link {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  font-size: 13px;
  padding: 0;
  text-decoration: underline;
}
</style>
