<template>
  <div class="app">
    <AppHeader v-model="abaAtiva" />

    <!-- Tab: Dashboard -->
    <section v-if="abaAtiva === 'dashboard'">
      <Dashboard
        :stats="stats"
        :loading="carregandoStats"
        :erro="erroStats"
        @reload="carregarStats"
      />
    </section>

    <!-- Tab: Chamados em aberto -->
    <section v-if="abaAtiva === 'chamados'">
      <ChamadosList
        titulo="Em Aberto"
        :chamados="chamados"
        :loading="carregandoChamados"
        :dias="diasFiltro"
        :limite="limiteFiltro"
        @selecionar="abrirModal"
        @reload="carregarChamados"
      />
    </section>

    <!-- Tab: Chamados concluídos -->
    <section v-if="abaAtiva === 'concluidos'">
      <ChamadosList
        titulo="Concluídos"
        :chamados="chamadosConcluidos"
        :loading="carregandoChamadosConcluidos"
        :dias="diasFiltro"
        :limite="limiteFiltro"
        @selecionar="abrirModal"
        @reload="carregarChamadosConcluidos"
      />
    </section>

    <!-- Tab: Métricas -->
    <section v-if="abaAtiva === 'metricas'">
      <MetricasChart
        :metricas="metricas"
        :loading="carregandoMetricas"
        :erro="erroMetricas"
        @reload="carregarMetricas"
      />
    </section>

    <!-- Tab: Playbooks -->
    <section v-if="abaAtiva === 'playbooks'">
      <PlaybooksPanel
        :playbooks="playbooks"
        :loading="carregandoPlaybooks"
        :erro="erroPlaybooks"
        @reload="carregarPlaybooks"
      />
    </section>

    <!-- Tab: Triagem de Atendimento (Modelo B em lote) -->
    <section v-if="abaAtiva === 'triagem-atendimento'">
      <TriagemAtendimento />
    </section>

    <!-- Tab: Comparação de Modelos (avaliação acadêmica) -->
    <section v-if="abaAtiva === 'comparacao'">
      <ComparacaoModelos />
    </section>

    <!-- Modal de detalhe do chamado -->
    <ChamadoModal
      v-if="chamadoSelecionado"
      :chamado="chamadoSelecionado"
      :sugestao="sugestaoAtual"
      :organizacoes="organizacoes"
      :carregando-sugestao="carregandoSugestao"
      :erro-sugestao="erroSugestao"
      @fechar="fecharModal"
      @gerar-sugestao="gerarSugestao"
      @aplicar="aplicarOrganizacao"
    />

    <!-- Toast de notificação -->
    <Transition name="toast">
      <div v-if="toast" class="toast" :class="toast.tipo">
        {{ toast.mensagem }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { api } from './services/api.js'
import AppHeader from './components/AppHeader.vue'
import Dashboard from './components/Dashboard.vue'
import ChamadosList from './components/ChamadosList.vue'
import ChamadoModal from './components/ChamadoModal.vue'
import MetricasChart from './components/MetricasChart.vue'
import PlaybooksPanel from './components/PlaybooksPanel.vue'
import ComparacaoModelos from './components/ComparacaoModelos.vue'
import TriagemAtendimento from './components/TriagemAtendimento.vue'

// ── Estado de navegação ───────────────────────────────────────────────────────
const abaAtiva = ref('dashboard')

// ── Estado: Stats ─────────────────────────────────────────────────────────────
const stats = ref({ total: 0, sem_organizacao: 0, percentual_pendente: 0 })
const carregandoStats = ref(false)
const erroStats = ref('')

// ── Estado: Chamados ──────────────────────────────────────────────────────────
const chamados = ref([])
const carregandoChamados = ref(false)
const diasFiltro = ref(90)
const limiteFiltro = ref(50)

// ── Estado: Chamados concluídos ───────────────────────────────────────────────
const chamadosConcluidos = ref([])
const carregandoChamadosConcluidos = ref(false)

// ── Estado: Métricas ──────────────────────────────────────────────────────────
const metricas = ref(null)
const carregandoMetricas = ref(false)
const erroMetricas = ref('')

// ── Estado: Playbooks ─────────────────────────────────────────────────────────
const playbooks = ref([])
const carregandoPlaybooks = ref(false)
const erroPlaybooks = ref('')

// ── Estado: Modal ─────────────────────────────────────────────────────────────
const chamadoSelecionado = ref(null)
const sugestaoAtual = ref(null)
const carregandoSugestao = ref(false)
const erroSugestao = ref('')
const organizacoes = ref([])

// ── Toast ─────────────────────────────────────────────────────────────────────
const toast = ref(null)

function mostrarToast(mensagem, tipo = 'success', duracao = 3500) {
  toast.value = { mensagem, tipo }
  setTimeout(() => { toast.value = null }, duracao)
}

// ── Carregamentos ─────────────────────────────────────────────────────────────

async function carregarStats() {
  carregandoStats.value = true
  erroStats.value = ''
  try {
    stats.value = await api.stats()
  } catch (e) {
    erroStats.value = e.message
  } finally {
    carregandoStats.value = false
  }
}

async function carregarChamados() {
  carregandoChamados.value = true
  try {
    chamados.value = await api.listarChamados(diasFiltro.value, limiteFiltro.value, 'aberto')
  } catch (e) {
    mostrarToast('Erro ao carregar chamados: ' + e.message, 'error')
  } finally {
    carregandoChamados.value = false
  }
}

async function carregarChamadosConcluidos() {
  carregandoChamadosConcluidos.value = true
  try {
    chamadosConcluidos.value = await api.listarChamados(diasFiltro.value, limiteFiltro.value, 'concluido')
  } catch (e) {
    mostrarToast('Erro ao carregar chamados concluídos: ' + e.message, 'error')
  } finally {
    carregandoChamadosConcluidos.value = false
  }
}

async function carregarMetricas() {
  carregandoMetricas.value = true
  erroMetricas.value = ''
  try {
    metricas.value = await api.metricas()
  } catch (e) {
    erroMetricas.value = e.message
  } finally {
    carregandoMetricas.value = false
  }
}

async function carregarPlaybooks() {
  carregandoPlaybooks.value = true
  erroPlaybooks.value = ''
  try {
    playbooks.value = await api.listarPlaybooks()
  } catch (e) {
    erroPlaybooks.value = e.message
  } finally {
    carregandoPlaybooks.value = false
  }
}

async function carregarOrganizacoes() {
  try {
    organizacoes.value = await api.listarOrganizacoes()
  } catch {
    // Não crítico — select de org ficará vazio mas não quebra
  }
}

// ── Modal ─────────────────────────────────────────────────────────────────────

async function abrirModal(chamado) {
  chamadoSelecionado.value = chamado
  sugestaoAtual.value = null
  erroSugestao.value = ''

  // Reaproveita a análise salva anteriormente — evita reprocessar (e gastar
  // cota da IA) toda vez que o técnico reabre o mesmo chamado
  carregandoSugestao.value = true
  try {
    const salva = await api.buscarSugestaoSalva(chamado.chave)
    if (salva && chamadoSelecionado.value?.chave === chamado.chave) {
      sugestaoAtual.value = salva.sugestao
    }
  } catch {
    // Sem análise salva — o técnico pode gerar uma nova pelo botão
  } finally {
    carregandoSugestao.value = false
  }
}

function fecharModal() {
  chamadoSelecionado.value = null
  sugestaoAtual.value = null
}

async function gerarSugestao() {
  if (!chamadoSelecionado.value) return
  carregandoSugestao.value = true
  erroSugestao.value = ''
  try {
    sugestaoAtual.value = await api.gerarSugestao(chamadoSelecionado.value.chave)
  } catch (e) {
    erroSugestao.value = e.message
  } finally {
    carregandoSugestao.value = false
  }
}

async function aplicarOrganizacao({ chave, organizacao }) {
  try {
    await api.atualizarChamado(chave, organizacao)
    mostrarToast(`Organização '${organizacao}' aplicada ao chamado ${chave}!`)
    fecharModal()
    // Recarrega chamados e stats para refletir a mudança
    carregarChamados()
    carregarStats()
  } catch (e) {
    mostrarToast('Erro ao aplicar organização: ' + e.message, 'error')
  }
}

// ── Inicialização ─────────────────────────────────────────────────────────────

// Carrega cada aba sob demanda, na primeira vez que ela é acessada
const abasJaCarregadas = new Set()

watch(abaAtiva, (aba) => {
  if (abasJaCarregadas.has(aba)) return
  abasJaCarregadas.add(aba)

  if (aba === 'concluidos') carregarChamadosConcluidos()
  else if (aba === 'metricas') carregarMetricas()
  else if (aba === 'playbooks') carregarPlaybooks()
})

onMounted(() => {
  abasJaCarregadas.add('dashboard')
  carregarStats()
  carregarChamados()
  carregarOrganizacoes()
})
</script>

<style scoped>
section { animation: fadeIn 0.25s ease; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: none; }
}

.toast {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 2000;
  padding: 14px 20px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  max-width: 380px;
}

.toast.success {
  background: rgba(0, 135, 90, 0.15);
  border: 1px solid rgba(0, 135, 90, 0.35);
  color: var(--success);
}

.toast.error {
  background: rgba(222, 53, 11, 0.15);
  border: 1px solid rgba(222, 53, 11, 0.35);
  color: var(--accent);
}

.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(16px); }
</style>
