<template>
  <div class="triagem-section">
    <!-- Cabeçalho -->
    <div class="controls">
      <div class="section-header">
        <span class="section-title">Triagem Atendimento</span>
        <span v-if="!carregando && modeloDisponivel && chamados.length" class="count-badge">
          {{ chamadosFiltrados.length }}
        </span>
      </div>
      <div class="controls-right">
        <span class="filter-info">Chamados sem label Presencial/Remoto</span>
        <button class="btn-secondary" @click="carregar" :disabled="carregando">
          <span v-if="carregando" class="spinner-sm"></span>
          <span v-else>↻</span>
          Atualizar
        </button>
      </div>
    </div>

    <!-- Modelo B indisponível -->
    <div v-if="!carregando && !modeloDisponivel" class="aviso-modelo">
      <p class="aviso-icone">⚠️</p>
      <p class="aviso-titulo">Modelo B não está disponível</p>
      <p class="aviso-desc">
        O classificador local (Presencial/Remoto) precisa ser treinado.<br>
        Execute <code>python treinar_modelo.py</code> no backend e reinicie o servidor.
      </p>
    </div>

    <!-- Carregando -->
    <div v-else-if="carregando" class="empty-state">
      <div class="spinner"></div>
      <p>Classificando chamados com o Modelo B...</p>
    </div>

    <!-- Nenhum pendente -->
    <div v-else-if="modeloDisponivel && chamados.length === 0" class="empty-state">
      <p style="font-size: 32px; margin-bottom: 8px">✅</p>
      <p>Todos os chamados em aberto já têm atendimento definido no Jira.</p>
    </div>

    <!-- Tabela com pendentes -->
    <template v-else-if="chamados.length">
      <!-- Filtros de confiança -->
      <div class="filtros">
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

      <div class="table-wrapper">
        <table class="jira-table">
          <thead>
            <tr>
              <th class="col-chave">Chave</th>
              <th class="col-relator">Relator</th>
              <th class="col-resumo">Resumo</th>
              <th class="col-sugestao">Sugestão Modelo B</th>
              <th class="col-select">Atendimento</th>
              <th class="col-action"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in chamadosFiltrados"
              :key="c.chave"
              class="jira-row"
              :class="{ 'revisar': c.revisar }"
            >
              <!-- Chave -->
              <td class="col-chave">
                <span class="chave-link">{{ c.chave }}</span>
              </td>

              <!-- Relator -->
              <td class="col-relator">
                <span class="relator-text" :title="c.relator">{{ c.relator }}</span>
              </td>

              <!-- Resumo + descrição -->
              <td class="col-resumo">
                <span class="resumo-link">{{ c.titulo }}</span>
                <span class="descricao-text">{{ c.descricao }}</span>
              </td>

              <!-- Sugestão do Modelo B -->
              <td class="col-sugestao">
                <div class="sugestao-wrapper">
                  <span
                    class="atend-tag"
                    :class="c.atendimento_sugerido === 'Presencial' ? 'tag-presencial' : 'tag-remoto'"
                  >
                    {{ c.atendimento_sugerido || '—' }}
                  </span>
                  <span v-if="c.confianca !== null" class="conf-pct">
                    {{ Math.round(c.confianca * 100) }}%
                  </span>
                  <span v-if="c.revisar" class="revisar-icon" title="Confiança baixa — revise manualmente">⚠️</span>
                </div>
              </td>

              <!-- Seletor Presencial/Remoto -->
              <td class="col-select">
                <select
                  v-model="escolhas[c.chave]"
                  class="select-atend"
                  @click.stop
                >
                  <option value="Presencial">Presencial</option>
                  <option value="Remoto">Remoto</option>
                </select>
              </td>

              <!-- Botão salvar -->
              <td class="col-action" @click.stop>
                <button
                  class="btn-salvar"
                  :class="{ 'salvando': salvando[c.chave] }"
                  :disabled="!!salvando[c.chave]"
                  @click="salvar(c)"
                >
                  <span v-if="salvando[c.chave]" class="spinner-sm"></span>
                  <span v-else>Salvar no Jira</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Legenda -->
      <div class="legenda">
        <span class="legenda-item"><span class="revisar-icon">⚠️</span> Confiança &lt; 70% — recomenda revisão manual</span>
        <span class="legenda-item"><span class="conf-pct">88%</span> = confiança estimada do Modelo B</span>
      </div>
    </template>

    <!-- Toast interno -->
    <Transition name="toast">
      <div v-if="toast" class="toast" :class="toast.tipo">{{ toast.mensagem }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../services/api.js'

// ── Estado ────────────────────────────────────────────────────────────────────
const carregando    = ref(false)
const modeloDisponivel = ref(true)
const chamados      = ref([])   // lista completa retornada pelo backend
const escolhas      = ref({})   // { chave: "Presencial" | "Remoto" }
const salvando      = ref({})   // { chave: true } enquanto a requisição está em voo
const toast         = ref(null)
const filtroAtivo   = ref('todos')

const filtros = [
  { id: 'todos',      label: 'Todos' },
  { id: 'revisar',    label: '⚠️ Revisar' },
  { id: 'presencial', label: 'Presencial' },
  { id: 'remoto',     label: 'Remoto' },
]

// ── Computed ──────────────────────────────────────────────────────────────────
const chamadosFiltrados = computed(() => {
  if (filtroAtivo.value === 'revisar')    return chamados.value.filter(c => c.revisar)
  if (filtroAtivo.value === 'presencial') return chamados.value.filter(c => c.atendimento_sugerido === 'Presencial')
  if (filtroAtivo.value === 'remoto')     return chamados.value.filter(c => c.atendimento_sugerido === 'Remoto')
  return chamados.value
})

function contagemFiltro(id) {
  if (id === 'todos')      return chamados.value.length
  if (id === 'revisar')    return chamados.value.filter(c => c.revisar).length
  if (id === 'presencial') return chamados.value.filter(c => c.atendimento_sugerido === 'Presencial').length
  if (id === 'remoto')     return chamados.value.filter(c => c.atendimento_sugerido === 'Remoto').length
  return 0
}

// ── Carregamento ──────────────────────────────────────────────────────────────
async function carregar() {
  carregando.value = true
  try {
    const resp = await api.atendimentoPendente()
    modeloDisponivel.value = resp.disponivel

    if (resp.disponivel) {
      chamados.value = resp.chamados

      // Pré-seleciona o seletor de cada linha com a sugestão do Modelo B
      const novasEscolhas = {}
      for (const c of resp.chamados) {
        novasEscolhas[c.chave] = c.atendimento_sugerido || 'Remoto'
      }
      escolhas.value = novasEscolhas
    }
  } catch (e) {
    mostrarToast('Erro ao carregar: ' + e.message, 'error')
  } finally {
    carregando.value = false
  }
}

// ── Salvar label no Jira ──────────────────────────────────────────────────────
async function salvar(chamado) {
  const atendimento = escolhas.value[chamado.chave]
  if (!atendimento) return

  salvando.value = { ...salvando.value, [chamado.chave]: true }
  try {
    await api.atualizarAtendimento(chamado.chave, atendimento)
    // Remove o chamado da lista — ele agora tem a label e sai dos pendentes
    chamados.value = chamados.value.filter(c => c.chave !== chamado.chave)
    mostrarToast(`${chamado.chave} salvo como "${atendimento}" no Jira.`, 'success')
  } catch (e) {
    mostrarToast(`Erro ao salvar ${chamado.chave}: ` + e.message, 'error')
  } finally {
    const copia = { ...salvando.value }
    delete copia[chamado.chave]
    salvando.value = copia
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function mostrarToast(mensagem, tipo = 'success') {
  toast.value = { mensagem, tipo }
  setTimeout(() => { toast.value = null }, 3500)
}

onMounted(carregar)
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

.btn-secondary:hover:not(:disabled) {
  color: var(--text);
  background: var(--overlay);
  border-color: var(--text-muted);
}

.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Aviso modelo indisponível ───────────────────────────────────────── */
.aviso-modelo {
  text-align: center;
  padding: 60px 20px;
  background: var(--card);
  border: 1px solid rgba(222, 53, 11, 0.25);
  border-radius: var(--radius);
}

.aviso-icone { font-size: 36px; margin-bottom: 10px; }

.aviso-titulo {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 8px;
}

.aviso-desc {
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.6;
}

.aviso-desc code {
  font-family: var(--mono);
  background: var(--overlay);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

/* ── Estado vazio / carregando ───────────────────────────────────────── */
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
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Filtros ─────────────────────────────────────────────────────────── */
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

/* ── Tabela ──────────────────────────────────────────────────────────── */
.table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--card);
}

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

/* Larguras */
.col-chave    { width: 96px; }
.col-relator  { width: 190px; }
.col-resumo   { min-width: 200px; }
.col-sugestao { width: 150px; }
.col-select   { width: 130px; }
.col-action   { width: 130px; text-align: right; }

.jira-row {
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}

.jira-row:last-child { border-bottom: none; }
.jira-row:hover { background: #EAF2FF; }

/* Linha de baixa confiança: destaque laranja na borda esquerda */
.jira-row.revisar { border-left: 3px solid var(--warning); }

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
}

.col-resumo td, .jira-table td.col-resumo {
  white-space: normal;
}

.resumo-link {
  color: var(--primary);
  font-weight: 500;
  font-size: 13px;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.descricao-text {
  font-size: 11px;
  color: var(--text-dim);
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

/* Sugestão */
.sugestao-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

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

.conf-pct {
  font-size: 11px;
  font-family: var(--mono);
  color: var(--text-muted);
}

.revisar-icon { font-size: 14px; }

/* Seletor */
.select-atend {
  width: 100%;
  padding: 5px 8px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  transition: border-color var(--transition);
}

.select-atend:focus {
  outline: none;
  border-color: var(--primary);
}

/* Botão salvar */
.btn-salvar {
  background: linear-gradient(135deg, var(--success) 0%, #006644 100%);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 6px 14px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all var(--transition);
}

.btn-salvar:hover:not(:disabled) {
  box-shadow: 0 3px 10px rgba(0, 135, 90, 0.4);
  transform: translateY(-1px);
}

.btn-salvar:disabled,
.btn-salvar.salvando {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

/* ── Legenda ──────────────────────────────────────────────────────────── */
.legenda {
  display: flex;
  gap: 20px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.legenda-item {
  font-size: 11px;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ── Toast ────────────────────────────────────────────────────────────── */
.toast {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 2000;
  padding: 14px 20px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  max-width: 380px;
}

.toast.success {
  background: rgba(0, 135, 90, 0.12);
  border: 1px solid rgba(0, 135, 90, 0.3);
  color: var(--success);
}

.toast.error {
  background: rgba(222, 53, 11, 0.12);
  border: 1px solid rgba(222, 53, 11, 0.3);
  color: var(--accent);
}

.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(16px); }
</style>
