<template>
  <header class="app-header">
    <div class="logo">DW+</div>
    <div class="header-text">
      <h1>DWPLUS Triage</h1>
      <p>Sistema Inteligente de Triagem de Chamados</p>
    </div>
    <nav class="header-nav">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['nav-btn', { active: modelValue === tab.id }]"
        @click="$emit('update:modelValue', tab.id)"
      >
        <span class="nav-icon">{{ tab.icon }}</span>
        {{ tab.label }}
      </button>
    </nav>
    <span class="header-badge">v2.0 · Gemini Flash</span>
  </header>
</template>

<script setup>
defineProps({
  modelValue: { type: String, required: true },
})
defineEmits(['update:modelValue'])

const tabs = [
  { id: 'dashboard',  icon: '⚡', label: 'Dashboard' },
  { id: 'chamados',   icon: '📋', label: 'Chamados' },
  { id: 'metricas',   icon: '📊', label: 'Métricas' },
  { id: 'playbooks',  icon: '📖', label: 'Playbooks' },
]
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 28px 0 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 36px;
  flex-wrap: wrap;
}

.logo {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-weight: 700;
  font-size: 17px;
  letter-spacing: -1px;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 0 24px rgba(10, 132, 255, 0.35);
}

.header-text h1 {
  font-family: var(--mono);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.5px;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-text p {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 2px;
}

.header-nav {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.nav-btn {
  background: transparent;
  color: var(--text-dim);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.nav-btn:hover {
  color: var(--text);
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.04);
}

.nav-btn.active {
  background: rgba(10, 132, 255, 0.15);
  border-color: rgba(10, 132, 255, 0.4);
  color: var(--primary);
}

.nav-icon { font-size: 14px; }

.header-badge {
  background: rgba(10, 132, 255, 0.12);
  border: 1px solid rgba(10, 132, 255, 0.25);
  color: var(--primary);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
</style>
