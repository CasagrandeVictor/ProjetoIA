<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('fechar')">
      <div class="modal" role="dialog" aria-modal="true">

        <!-- Cabeçalho do modal -->
        <div class="modal-header">
          <div>
            <span class="chave-tag">{{ chamado.chave }}</span>
            <h2 class="modal-title">{{ chamado.titulo }}</h2>
          </div>
          <button class="btn-close" @click="$emit('fechar')">✕</button>
        </div>

        <!-- Detalhes do chamado -->
        <div class="modal-body">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">Usuário</span>
              <span class="detail-value mono">{{ chamado.usuario_id }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Criado em</span>
              <span class="detail-value mono">{{ chamado.criado_em }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Status</span>
              <span class="detail-value">{{ chamado.status }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Prioridade Jira</span>
              <span class="detail-value">{{ chamado.prioridade }}</span>
            </div>
            <div class="detail-item span-2">
              <span class="detail-label">Organização atual</span>
              <span
                class="detail-value"
                :class="chamado.organizacao_atual === 'Não preenchido' ? 'text-danger' : 'text-success'"
              >{{ chamado.organizacao_atual }}</span>
            </div>
          </div>

          <div v-if="chamado.descricao" class="descricao-block">
            <div class="detail-label" style="margin-bottom: 8px">Descrição</div>
            <p class="descricao-text">{{ chamado.descricao }}</p>
          </div>

          <!-- Seção de análise IA -->
          <div class="ia-section">
            <div class="ia-header">
              <span class="ia-title">Análise de IA</span>
              <span v-if="sugestao?.fonte" class="fonte-badge">{{ sugestao.fonte }}</span>
              <button
                v-if="!sugestao"
                class="btn-primary btn-sm"
                :disabled="carregandoSugestao"
                @click="$emit('gerar-sugestao')"
              >
                <span v-if="carregandoSugestao" class="spinner-sm"></span>
                {{ carregandoSugestao ? 'Analisando...' : '✨ Analisar com IA' }}
              </button>
              <button
                v-else
                class="btn-secondary-sm"
                :disabled="carregandoSugestao"
                @click="$emit('gerar-sugestao')"
              >
                <span v-if="carregandoSugestao" class="spinner-sm"></span>
                {{ carregandoSugestao ? 'Reanalisando...' : '🔄 Reanalisar' }}
              </button>
            </div>

            <!-- Estado carregando -->
            <div v-if="carregandoSugestao && !sugestao" class="ia-loading">
              <div class="spinner"></div>
              <p>Gemini Flash analisando o chamado...</p>
            </div>

            <!-- Erro na sugestão -->
            <div v-if="erroSugestao" class="alert-error">⚠️ {{ erroSugestao }}</div>

            <!-- Resultado da sugestão -->
            <div v-if="sugestao" class="sugestao-content">
              <!-- Métricas da sugestão -->
              <div class="sugestao-metrics">
                <div class="metric-card">
                  <span class="metric-label">Organização sugerida</span>
                  <span class="metric-value text-primary">{{ sugestao.organizacao_sugerida }}</span>
                </div>
                <div class="metric-card">
                  <span class="metric-label">Confiança</span>
                  <div class="confianca-bar">
                    <div
                      class="confianca-fill"
                      :style="{ width: (sugestao.confianca * 100) + '%' }"
                      :class="confiancaClass"
                    ></div>
                  </div>
                  <span class="metric-value">{{ Math.round(sugestao.confianca * 100) }}%</span>
                </div>
                <div v-if="sugestao.categoria" class="metric-card">
                  <span class="metric-label">Categoria</span>
                  <span class="metric-value categoria-tag">{{ sugestao.categoria }}</span>
                </div>
                <div v-if="sugestao.prioridade" class="metric-card">
                  <span class="metric-label">Prioridade sugerida</span>
                  <span class="metric-value" :class="prioridadeClass(sugestao.prioridade)">
                    {{ sugestao.prioridade }}
                  </span>
                </div>
              </div>

              <!-- Justificativa (Gemini) -->
              <div v-if="sugestao.justificativa" class="orientacoes-block justificativa">
                <div class="orientacoes-label">Justificativa da IA</div>
                <p>{{ sugestao.justificativa }}</p>
              </div>

              <!-- Orientações -->
              <div class="orientacoes-block">
                <div class="orientacoes-label">Orientações para o Técnico</div>
                <p>{{ sugestao.orientacoes }}</p>
              </div>

              <!-- Playbook associado -->
              <div v-if="sugestao.playbook_titulo" class="playbook-block">
                <div class="playbook-header">
                  📖 Playbook: <strong>{{ sugestao.playbook_titulo }}</strong>
                </div>
                <ol class="playbook-steps">
                  <li v-for="(passo, i) in sugestao.playbook_passos" :key="i">{{ passo }}</li>
                </ol>
              </div>

              <!-- Ação: aplicar organização sugerida -->
              <div class="modal-actions">
                <div class="action-row">
                  <select v-model="orgEscolhida" class="org-select">
                    <option value="">Selecione a organização...</option>
                    <option
                      v-for="org in organizacoes"
                      :key="org.id"
                      :value="org.nome"
                    >{{ org.nome }}</option>
                  </select>
                  <button
                    class="btn-primary"
                    :disabled="!orgEscolhida || aplicando"
                    @click="aplicar"
                  >
                    <span v-if="aplicando" class="spinner-sm"></span>
                    {{ aplicando ? 'Aplicando...' : '✓ Aplicar e Salvar' }}
                  </button>
                </div>
                <p v-if="!orgEscolhida && sugestao" class="hint-text">
                  Sugestão: <button class="btn-link" @click="orgEscolhida = sugestao.organizacao_sugerida">
                    {{ sugestao.organizacao_sugerida }}
                  </button>
                </p>
              </div>
            </div>
          </div>

          <!-- Seção de atendimento (Presencial/Remoto) -->
          <div class="atendimento-section">
            <div class="ia-header">
              <span class="ia-title">Atendimento</span>
              <span v-if="sugestao?.atendimento" class="fonte-badge">Modelo B</span>
            </div>
            <div class="atendimento-content">
              <p v-if="sugestao?.atendimento" class="hint-text" style="margin-top: 0">
                Modelo B sugere: <strong>{{ sugestao.atendimento }}</strong>
                <span v-if="sugestao.confianca_atendimento">
                  ({{ Math.round(sugestao.confianca_atendimento * 100) }}% confiança)
                </span>
              </p>
              <p v-else class="hint-text" style="margin-top: 0">
                Modelo B não disponível — selecione manualmente.
              </p>

              <div class="atendimento-options">
                <label class="radio-option" :class="{ active: atendimentoEscolhido === 'Presencial' }">
                  <input type="radio" value="Presencial" v-model="atendimentoEscolhido" />
                  Presencial
                </label>
                <label class="radio-option" :class="{ active: atendimentoEscolhido === 'Remoto' }">
                  <input type="radio" value="Remoto" v-model="atendimentoEscolhido" />
                  Remoto
                </label>

                <button
                  class="btn-primary btn-sm-inline"
                  :disabled="!atendimentoEscolhido || salvandoAtendimento"
                  @click="salvarAtendimento"
                >
                  <span v-if="salvandoAtendimento" class="spinner-sm"></span>
                  {{ salvandoAtendimento ? 'Salvando...' : '💾 Salvar atendimento no Jira' }}
                </button>
              </div>

              <p v-if="sucessoAtendimento" class="alert-success">✅ {{ sucessoAtendimento }}</p>
              <p v-if="erroAtendimento" class="alert-error inline">⚠️ {{ erroAtendimento }}</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '../services/api.js'

const props = defineProps({
  chamado: { type: Object, required: true },
  sugestao: { type: Object, default: null },
  organizacoes: { type: Array, default: () => [] },
  carregandoSugestao: Boolean,
  erroSugestao: String,
})

const emit = defineEmits(['fechar', 'gerar-sugestao', 'aplicar'])

const orgEscolhida = ref('')
const aplicando = ref(false)

// Pré-preenche com a sugestão quando ela chega
watch(() => props.sugestao, (s) => {
  if (s && !orgEscolhida.value) {
    orgEscolhida.value = s.organizacao_sugerida || ''
  }
})

async function aplicar() {
  if (!orgEscolhida.value) return
  aplicando.value = true
  try {
    await emit('aplicar', { chave: props.chamado.chave, organizacao: orgEscolhida.value })
  } finally {
    aplicando.value = false
  }
}

// ── Atendimento (Presencial/Remoto) ─────────────────────────────────────────

const atendimentoEscolhido = ref('')
const salvandoAtendimento = ref(false)
const sucessoAtendimento = ref('')
const erroAtendimento = ref('')

// Pré-preenche com a sugestão do Modelo B quando ela chega (se o usuário ainda não escolheu)
watch(() => props.sugestao, (s) => {
  if (s?.atendimento && !atendimentoEscolhido.value) {
    atendimentoEscolhido.value = s.atendimento
  }
}, { immediate: true })

async function salvarAtendimento() {
  if (!atendimentoEscolhido.value) return
  salvandoAtendimento.value = true
  sucessoAtendimento.value = ''
  erroAtendimento.value = ''
  try {
    await api.atualizarAtendimento(props.chamado.chave, atendimentoEscolhido.value)
    sucessoAtendimento.value = `Atendimento salvo como "${atendimentoEscolhido.value}" no Jira.`
  } catch (e) {
    erroAtendimento.value = e.message
  } finally {
    salvandoAtendimento.value = false
  }
}

const confiancaClass = computed(() => {
  const c = props.sugestao?.confianca || 0
  if (c >= 0.8) return 'fill-success'
  if (c >= 0.5) return 'fill-warning'
  return 'fill-danger'
})

function prioridadeClass(p) {
  const map = { Crítica: 'text-danger', Alta: 'text-warning', Média: 'text-primary', Baixa: 'text-success' }
  return map[p] || ''
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  width: 100%;
  max-width: 760px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6);
  animation: slideUp 0.2s ease;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 24px 24px 0;
  gap: 16px;
}

.chave-tag {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
  background: rgba(0, 82, 204, 0.1);
  border: 1px solid rgba(0, 82, 204, 0.2);
  padding: 2px 8px;
  border-radius: 5px;
  display: inline-block;
  margin-bottom: 8px;
}

.modal-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.3;
}

.btn-close {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 8px;
  width: 34px;
  height: 34px;
  cursor: pointer;
  font-size: 14px;
  flex-shrink: 0;
  transition: all var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover { background: rgba(222, 53, 11, 0.1); color: var(--accent); border-color: var(--accent); }

.modal-body { padding: 20px 24px 24px; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.detail-item { display: flex; flex-direction: column; gap: 4px; }
.span-2 { grid-column: span 2; }

.detail-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
}

.detail-value { font-size: 13px; color: var(--text); }
.detail-value.mono { font-family: var(--mono); font-size: 12px; }

.text-danger  { color: var(--accent) !important; }
.text-success { color: var(--success) !important; }
.text-primary { color: var(--primary) !important; }
.text-warning { color: var(--warning) !important; }

.descricao-block {
  background: var(--overlay);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
  margin-bottom: 20px;
}

.descricao-text {
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}

/* ── Seção IA ─────────────────────────────────────────────────────────────── */
.ia-section {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.ia-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(101, 84, 192, 0.06);
  border-bottom: 1px solid var(--border);
}

.ia-title {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--secondary);
}

.fonte-badge {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 20px;
  background: rgba(101, 84, 192, 0.15);
  border: 1px solid rgba(101, 84, 192, 0.3);
  color: var(--secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ia-loading { text-align: center; padding: 40px; color: var(--text-dim); }

.spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--secondary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

.spinner-sm {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

.sugestao-content { padding: 18px; }

.sugestao-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  background: var(--overlay);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metric-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px; }
.metric-value { font-size: 14px; font-weight: 600; color: var(--text); }

.confianca-bar {
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.confianca-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.fill-success { background: var(--success); }
.fill-warning { background: var(--warning); }
.fill-danger  { background: var(--accent); }

.categoria-tag {
  font-family: var(--mono);
  font-size: 12px;
  background: rgba(101, 84, 192, 0.1);
  border: 1px solid rgba(101, 84, 192, 0.2);
  color: var(--secondary);
  padding: 2px 8px;
  border-radius: 5px;
  display: inline-block;
}

.orientacoes-block {
  background: var(--overlay);
  border: 1px solid var(--border);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-sm);
  padding: 14px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.6;
}

.orientacoes-block.justificativa { border-left-color: var(--secondary); }

.orientacoes-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.playbook-block {
  background: rgba(101, 84, 192, 0.06);
  border: 1px solid rgba(101, 84, 192, 0.2);
  border-radius: var(--radius-sm);
  padding: 14px;
  margin-bottom: 16px;
}

.playbook-header { font-size: 13px; color: var(--secondary); margin-bottom: 10px; }

.playbook-steps {
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.playbook-steps li { font-size: 13px; color: var(--text-dim); line-height: 1.5; }

.modal-actions { margin-top: 16px; }

.action-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.org-select {
  flex: 1;
  min-width: 200px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 10px 12px;
  font-size: 13px;
  font-family: var(--sans);
  cursor: pointer;
}

.org-select:focus { outline: none; border-color: var(--primary); }

.btn-primary {
  background: linear-gradient(135deg, var(--primary) 0%, #0747A6 100%);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all var(--transition);
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { box-shadow: 0 4px 16px rgba(0, 82, 204, 0.4); }

.btn-sm { padding: 7px 14px; font-size: 12px; margin-left: auto; }

.btn-secondary-sm {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: var(--radius-sm);
  padding: 7px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  transition: all var(--transition);
}

.btn-secondary-sm:hover { color: var(--text); background: var(--overlay); border-color: var(--text-muted); }
.btn-secondary-sm:disabled { opacity: 0.5; cursor: not-allowed; }

.hint-text { font-size: 12px; color: var(--text-dim); margin-top: 8px; }

.btn-link {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  font-size: 12px;
  padding: 0;
  text-decoration: underline;
}

.alert-error {
  background: rgba(222, 53, 11, 0.1);
  border: 1px solid rgba(222, 53, 11, 0.3);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  color: var(--accent);
  font-size: 13px;
  margin: 12px 18px;
}

.alert-error.inline { margin: 12px 0 0; }

.alert-success {
  background: rgba(0, 135, 90, 0.1);
  border: 1px solid rgba(0, 135, 90, 0.3);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  color: var(--success);
  font-size: 13px;
  margin: 12px 0 0;
}

/* ── Seção Atendimento ────────────────────────────────────────────────────── */
.atendimento-section {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  margin-top: 20px;
}

.atendimento-content { padding: 18px; }

.atendimento-options {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.radio-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-dim);
  cursor: pointer;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 14px;
  transition: all var(--transition);
}

.radio-option.active {
  border-color: var(--primary);
  color: var(--text);
  background: rgba(0, 82, 204, 0.06);
  font-weight: 600;
}

.radio-option input { accent-color: var(--primary); cursor: pointer; }

.btn-sm-inline { padding: 9px 16px; font-size: 13px; margin-left: auto; }
</style>
