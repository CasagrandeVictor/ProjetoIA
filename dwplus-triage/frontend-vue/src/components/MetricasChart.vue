<template>
  <div class="metricas-section">
    <div class="section-header-row">
      <div>
        <div class="section-title">Métricas de Volume</div>
        <div class="section-sub" v-if="metricas">
          Últimos {{ metricas.periodo_dias }}d · {{ metricas.total_analisado }} chamados analisados
        </div>
      </div>
      <button class="btn-secondary" @click="$emit('reload')">
        <span v-if="loading" class="spinner-sm"></span>
        <span v-else>↻</span>
        Atualizar
      </button>
    </div>

    <!-- Carregando -->
    <div v-if="loading" class="empty-state">
      <div class="spinner"></div>
      <p>Calculando métricas...</p>
    </div>

    <!-- Erro -->
    <div v-else-if="erro" class="alert-error">⚠️ {{ erro }}</div>

    <!-- Dados -->
    <div v-else-if="metricas">
      <!-- Cards de resumo -->
      <div class="resumo-grid">
        <div class="resumo-card">
          <span class="resumo-label">Média / Dia</span>
          <span class="resumo-value">{{ metricas.resumo?.media_por_dia }}</span>
        </div>
        <div class="resumo-card">
          <span class="resumo-label">Média / Semana</span>
          <span class="resumo-value">{{ metricas.resumo?.media_por_semana }}</span>
        </div>
        <div class="resumo-card">
          <span class="resumo-label">Média / Mês</span>
          <span class="resumo-value">{{ metricas.resumo?.media_por_mes }}</span>
        </div>
        <div class="resumo-card accent">
          <span class="resumo-label">Hora de Pico</span>
          <span class="resumo-value">
            {{ metricas.hora_pico !== null ? metricas.hora_pico + 'h' : '—' }}
          </span>
        </div>
        <div class="resumo-card accent2">
          <span class="resumo-label">Dia de Pico</span>
          <span class="resumo-value">{{ metricas.dia_semana_pico || '—' }}</span>
        </div>
      </div>

      <!-- Gráficos -->
      <div class="charts-grid">
        <!-- Por hora -->
        <div class="chart-card">
          <div class="chart-title">Chamados por Hora do Dia</div>
          <Bar :data="horaData" :options="barOpts" class="chart-canvas" />
        </div>

        <!-- Por dia da semana -->
        <div class="chart-card">
          <div class="chart-title">Chamados por Dia da Semana</div>
          <Bar :data="diaData" :options="barOpts" class="chart-canvas" />
        </div>

        <!-- Por mês (linha) -->
        <div class="chart-card wide">
          <div class="chart-title">Evolução Mensal</div>
          <Line :data="mesData" :options="lineOpts" class="chart-canvas" />
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>Nenhum dado disponível.</p>
      <button class="btn-primary" @click="$emit('reload')">Carregar métricas</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Bar, Line } from 'vue-chartjs'

// Registra os módulos necessários do Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  metricas: { type: Object, default: null },
  loading: Boolean,
  erro: String,
})

defineEmits(['reload'])

// Opções compartilhadas para gráficos de barras
const barOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: '#1A1A1A', borderColor: '#2C2C2C', borderWidth: 1, titleColor: '#F5F5F7', bodyColor: '#8E8E93' },
  },
  scales: {
    x: { ticks: { color: '#8E8E93', font: { size: 11 } }, grid: { color: '#2C2C2C' } },
    y: { ticks: { color: '#8E8E93', font: { size: 11 } }, grid: { color: '#2C2C2C' }, beginAtZero: true },
  },
}

const lineOpts = {
  ...barOpts,
  plugins: {
    ...barOpts.plugins,
    legend: { display: false },
  },
  elements: {
    line: { tension: 0.35 },
    point: { radius: 4, hoverRadius: 6 },
  },
}

// Dados para gráfico por hora
const horaData = computed(() => {
  if (!props.metricas) return { labels: [], datasets: [] }
  const horas = Array.from({ length: 24 }, (_, i) => `${i}h`)
  const valores = Array.from({ length: 24 }, (_, i) => props.metricas.por_hora?.[String(i)] || 0)
  const pico = props.metricas.hora_pico
  return {
    labels: horas,
    datasets: [{
      data: valores,
      backgroundColor: horas.map((_, i) =>
        i === pico ? 'rgba(255, 159, 10, 0.8)' : 'rgba(10, 132, 255, 0.6)'
      ),
      borderColor: horas.map((_, i) =>
        i === pico ? '#FF9F0A' : '#0A84FF'
      ),
      borderWidth: 1,
      borderRadius: 4,
    }],
  }
})

// Dados para gráfico por dia da semana
const diaData = computed(() => {
  if (!props.metricas) return { labels: [], datasets: [] }
  const dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
  const pico = props.metricas.dia_semana_pico
  return {
    labels: dias,
    datasets: [{
      data: dias.map((d) => props.metricas.por_dia_semana?.[d] || 0),
      backgroundColor: dias.map((d) =>
        d === pico ? 'rgba(255, 159, 10, 0.8)' : 'rgba(94, 92, 230, 0.6)'
      ),
      borderColor: dias.map((d) =>
        d === pico ? '#FF9F0A' : '#5E5CE6'
      ),
      borderWidth: 1,
      borderRadius: 4,
    }],
  }
})

// Dados para gráfico mensal (linha)
const mesData = computed(() => {
  if (!props.metricas?.por_mes) return { labels: [], datasets: [] }
  const entries = Object.entries(props.metricas.por_mes)
  return {
    labels: entries.map(([k]) => k),
    datasets: [{
      data: entries.map(([, v]) => v),
      fill: true,
      backgroundColor: 'rgba(52, 199, 89, 0.1)',
      borderColor: '#34C759',
      pointBackgroundColor: '#34C759',
      borderWidth: 2,
    }],
  }
})
</script>

<style scoped>
.section-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.section-title {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.section-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; font-family: var(--mono); }

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

.btn-secondary:hover { color: var(--text); border-color: rgba(255, 255, 255, 0.2); }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-dim); }

.spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
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

.resumo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 28px;
}

.resumo-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.resumo-card.accent  { border-left: 3px solid var(--warning); }
.resumo-card.accent2 { border-left: 3px solid var(--secondary); }

.resumo-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px; }
.resumo-value { font-family: var(--mono); font-size: 24px; font-weight: 700; color: var(--text); }

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}

.chart-card.wide { grid-column: 1 / -1; }

.chart-title {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 16px;
}

.chart-canvas { height: 220px !important; }

.alert-error {
  background: rgba(255, 55, 95, 0.1);
  border: 1px solid rgba(255, 55, 95, 0.3);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  color: var(--accent);
  font-size: 13px;
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary) 0%, #0066cc 100%);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 12px;
}
</style>
