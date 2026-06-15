<template>
  <div class="comparacao-section">
    <div class="section-header-row">
      <div class="section-title">Comparação de Modelos</div>
      <span class="badge" :class="status?.modelo_b_disponivel ? 'badge-ok' : 'badge-off'">
        Modelo B: {{ status?.modelo_b_disponivel ? 'disponível' : 'não treinado' }}
      </span>
    </div>

    <p class="hint">
      Ferramenta de avaliação acadêmica: roda a sugestão atual (Gemini/regras + histórico do
      usuário) e o Modelo B (classificador local treinado) sobre um chamado já concluído e
      compara ambos com os valores reais registrados no Jira (organização e atendimento
      Presencial/Remoto).
    </p>

    <div class="busca-row">
      <input
        v-model="chaveInput"
        class="form-input"
        placeholder="Chave do chamado (ex: AT-5139)"
        @keyup.enter="comparar"
      />
      <button class="btn-primary" :disabled="carregando || !chaveInput.trim()" @click="comparar">
        <span v-if="carregando" class="spinner-sm"></span>
        {{ carregando ? 'Comparando...' : 'Comparar' }}
      </button>
    </div>

    <div v-if="erro" class="alert-error">⚠️ {{ erro }}</div>

    <div v-if="resultado" class="resultado-card">
      <div class="resultado-header">
        Chamado <span class="chave-badge">{{ resultado.chave }}</span>
      </div>

      <table class="comparacao-table">
        <thead>
          <tr>
            <th>Campo</th>
            <th>Modelo</th>
            <th>Previsto</th>
            <th>Valor Real (Jira)</th>
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Organização</td>
            <td>
              Modelo A (Gemini/regras)
              <span class="fonte-tag">{{ resultado.organizacao.fonte_modelo_a }}</span>
            </td>
            <td>{{ resultado.organizacao.modelo_a }}</td>
            <td>{{ resultado.organizacao.real }}</td>
            <td>
              <span class="resultado-badge" :class="classeResultado(resultado.organizacao.correto)">
                {{ textoResultado(resultado.organizacao.correto) }}
              </span>
            </td>
          </tr>
          <tr>
            <td>Atendimento</td>
            <td>
              Modelo B (local)
              <span v-if="resultado.atendimento.confianca_modelo_b" class="fonte-tag">
                {{ (resultado.atendimento.confianca_modelo_b * 100).toFixed(0) }}% confiança
              </span>
            </td>
            <td>{{ resultado.atendimento.modelo_b ?? '—' }}</td>
            <td>{{ resultado.atendimento.real }}</td>
            <td>
              <span class="resultado-badge" :class="classeResultado(resultado.atendimento.correto)">
                {{ textoResultado(resultado.atendimento.correto) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../services/api.js'

const status = ref(null)
const chaveInput = ref('')
const resultado = ref(null)
const carregando = ref(false)
const erro = ref('')

function classeResultado(correto) {
  if (correto === true) return 'badge-ok'
  if (correto === false) return 'badge-erro'
  return 'badge-na'
}

function textoResultado(correto) {
  if (correto === true) return '✅ Correto'
  if (correto === false) return '❌ Incorreto'
  return '— Sem valor real'
}

async function comparar() {
  const chave = chaveInput.value.trim().toUpperCase()
  if (!chave) return
  carregando.value = true
  erro.value = ''
  resultado.value = null
  try {
    resultado.value = await api.compararModelos(chave)
  } catch (e) {
    erro.value = e.message
  } finally {
    carregando.value = false
  }
}

onMounted(async () => {
  try {
    status.value = await api.statusModelo()
  } catch {
    // Não crítico — badge fica oculta/indefinida
  }
})
</script>

<style scoped>
.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.hint {
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.5;
  margin-bottom: 20px;
  max-width: 720px;
}

.badge {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--mono);
  padding: 4px 10px;
  border-radius: 20px;
  letter-spacing: 0.5px;
}

.badge-ok { background: rgba(0, 135, 90, 0.1); color: var(--success); border: 1px solid rgba(0, 135, 90, 0.25); }
.badge-off { background: rgba(255, 139, 0, 0.1); color: var(--warning); border: 1px solid rgba(255, 139, 0, 0.25); }
.badge-erro { background: rgba(222, 53, 11, 0.1); color: var(--accent); border: 1px solid rgba(222, 53, 11, 0.25); }
.badge-na { background: var(--overlay); color: var(--text-muted); border: 1px solid var(--border); }

.busca-row {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  max-width: 480px;
}

.form-input {
  flex: 1;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 10px 12px;
  font-size: 13px;
  font-family: var(--sans);
  transition: border-color var(--transition);
}

.form-input:focus { outline: none; border-color: var(--primary); }

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
  white-space: nowrap;
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner-sm {
  width: 13px; height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

.alert-error {
  background: rgba(222, 53, 11, 0.1);
  border: 1px solid rgba(222, 53, 11, 0.3);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  color: var(--accent);
  font-size: 13px;
  margin-bottom: 16px;
}

.resultado-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  max-width: 820px;
}

.resultado-header {
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 14px;
}

.chave-badge {
  font-family: var(--mono);
  font-weight: 700;
  color: var(--primary);
  background: rgba(0, 82, 204, 0.08);
  border: 1px solid rgba(0, 82, 204, 0.2);
  padding: 2px 8px;
  border-radius: 5px;
}

.comparacao-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.comparacao-table th,
.comparacao-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}

.comparacao-table th {
  font-family: var(--mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-dim);
  font-weight: 600;
}

.comparacao-table tbody tr:last-child td { border-bottom: none; }

.fonte-tag {
  display: inline-block;
  font-size: 10px;
  font-family: var(--mono);
  color: var(--text-muted);
  background: var(--overlay);
  border: 1px solid var(--border);
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: 6px;
}

.resultado-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
}
</style>
