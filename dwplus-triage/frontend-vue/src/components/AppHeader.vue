<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="logo">DW+</div>
      <div class="brand-text">
        <h1>DWPLUS Triage</h1>
        <p>Triagem Inteligente de Chamados</p>
      </div>
    </div>

    <nav class="sidebar-nav">
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

    <div class="sidebar-footer">
      <span class="header-badge">v2.0 · Gemini Flash</span>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  modelValue: { type: String, required: true },
})
defineEmits(['update:modelValue'])

const tabs = [
  { id: 'dashboard',  icon: '⚡', label: 'Dashboard' },
  { id: 'chamados',   icon: '📋', label: 'Em Aberto' },
  { id: 'concluidos', icon: '✅', label: 'Concluídos' },
  { id: 'metricas',   icon: '📊', label: 'Métricas' },
  { id: 'playbooks',  icon: '📖', label: 'Playbooks' },
]
</script>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 240px;
  background: var(--card);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  z-index: 10;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 8px 24px;
}

.logo {
  width: 36px;
  height: 36px;
  border-radius: 7px;
  background: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: -1px;
  color: #fff;
  flex-shrink: 0;
}

.brand-text h1 {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.3px;
  color: var(--text);
  line-height: 1.2;
}

.brand-text p {
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 2px;
  line-height: 1.3;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-btn {
  background: transparent;
  color: var(--text-dim);
  border: none;
  border-radius: var(--radius);
  padding: 9px 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition), color var(--transition);
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  width: 100%;
}

.nav-btn:hover {
  color: var(--text);
  background: var(--overlay);
}

.nav-btn.active {
  background: rgba(0, 82, 204, 0.1);
  color: var(--primary);
  font-weight: 600;
}

.nav-icon { font-size: 15px; width: 20px; text-align: center; }

.sidebar-footer {
  margin-top: auto;
  padding: 12px 8px 4px;
}

.header-badge {
  display: inline-block;
  background: var(--overlay);
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
</style>
