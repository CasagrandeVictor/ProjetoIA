<template>
  <div class="playbooks-section">
    <div class="section-header-row">
      <div class="section-title">Playbooks</div>
      <button class="btn-primary btn-sm" @click="mostrarForm ? fecharForm() : abrirFormCriacao()">
        {{ mostrarForm ? '✕ Cancelar' : '+ Novo Playbook' }}
      </button>
    </div>

    <!-- Formulário de criação/edição -->
    <div v-if="mostrarForm" class="form-card">
      <div class="form-title">{{ editandoId ? `Editando: ${editandoId}` : 'Novo Playbook' }}</div>
      <div class="form-group">
        <label class="form-label">ID (único)</label>
        <input v-model="form.id" class="form-input" placeholder="ex: reset_senha" :disabled="!!editandoId" />
      </div>
      <div class="form-group">
        <label class="form-label">Título</label>
        <input v-model="form.titulo" class="form-input" placeholder="ex: Problema de Senha / Login" />
      </div>
      <div class="form-group">
        <label class="form-label">Palavras-chave (separadas por vírgula)</label>
        <input
          v-model="form.palavrasChaveStr"
          class="form-input"
          placeholder="ex: senha, login, acesso, autenticação"
        />
      </div>
      <div class="form-group">
        <label class="form-label">Passos (um por linha)</label>
        <textarea
          v-model="form.passosStr"
          class="form-textarea"
          rows="5"
          placeholder="1. Verificar se o usuário existe no AD&#10;2. Resetar senha via portal&#10;3. Confirmar acesso"
        ></textarea>
      </div>
      <div class="form-actions">
        <button class="btn-primary" :disabled="salvando || !formValido" @click="salvarPlaybook">
          <span v-if="salvando" class="spinner-sm"></span>
          {{ salvando ? 'Salvando...' : (editandoId ? '✓ Salvar Alterações' : '✓ Criar Playbook') }}
        </button>
        <span v-if="erroForm" class="erro-inline">{{ erroForm }}</span>
      </div>
    </div>

    <!-- Erro -->
    <div v-if="erro" class="alert-error">⚠️ {{ erro }}</div>

    <!-- Carregando -->
    <div v-if="loading" class="empty-state">
      <div class="spinner"></div>
      <p>Carregando playbooks...</p>
    </div>

    <!-- Lista vazia -->
    <div v-else-if="playbooks.length === 0 && !mostrarForm" class="empty-state">
      <p style="font-size: 28px; margin-bottom: 8px">📖</p>
      <p>Nenhum playbook cadastrado ainda.</p>
    </div>

    <!-- Lista de playbooks -->
    <div v-else class="playbooks-grid">
      <div v-for="pb in playbooks" :key="pb.id" class="playbook-card">
        <div class="pb-header">
          <div>
            <span class="pb-id">{{ pb.id }}</span>
            <div class="pb-titulo">{{ pb.titulo }}</div>
          </div>
          <div class="pb-actions">
            <button class="btn-secondary-sm" @click="abrirFormEdicao(pb)">Editar</button>
            <button
              class="btn-danger-sm"
              :disabled="deletando === pb.id"
              @click="deletarPlaybook(pb.id)"
            >
              {{ deletando === pb.id ? '...' : '🗑' }}
            </button>
          </div>
        </div>

        <div class="pb-keywords">
          <span v-for="kw in pb.palavras_chave" :key="kw" class="kw-badge">{{ kw }}</span>
        </div>

        <details class="pb-steps-details">
          <summary class="pb-steps-summary">
            {{ pb.passos.length }} passo{{ pb.passos.length !== 1 ? 's' : '' }}
          </summary>
          <ol class="pb-steps">
            <li v-for="(passo, i) in pb.passos" :key="i">{{ passo }}</li>
          </ol>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api } from '../services/api.js'

const props = defineProps({
  playbooks: { type: Array, default: () => [] },
  loading: Boolean,
  erro: String,
})

const emit = defineEmits(['reload'])

const mostrarForm = ref(false)
const editandoId = ref(null)
const salvando = ref(false)
const deletando = ref(null)
const erroForm = ref('')

const formVazio = { id: '', titulo: '', palavrasChaveStr: '', passosStr: '' }
const form = ref({ ...formVazio })

const formValido = computed(() =>
  form.value.id.trim() &&
  form.value.titulo.trim() &&
  form.value.palavrasChaveStr.trim() &&
  form.value.passosStr.trim()
)

function abrirFormCriacao() {
  editandoId.value = null
  erroForm.value = ''
  form.value = { ...formVazio }
  mostrarForm.value = true
}

function abrirFormEdicao(pb) {
  editandoId.value = pb.id
  erroForm.value = ''
  form.value = {
    id: pb.id,
    titulo: pb.titulo,
    palavrasChaveStr: pb.palavras_chave.join(', '),
    passosStr: pb.passos.join('\n'),
  }
  mostrarForm.value = true
}

function fecharForm() {
  mostrarForm.value = false
  editandoId.value = null
  form.value = { ...formVazio }
  erroForm.value = ''
}

async function salvarPlaybook() {
  erroForm.value = ''
  salvando.value = true
  try {
    const palavras_chave = form.value.palavrasChaveStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)

    const passos = form.value.passosStr
      .split('\n')
      .map((s) => s.replace(/^\d+\.\s*/, '').trim())
      .filter(Boolean)

    const payload = {
      id: form.value.id.trim(),
      titulo: form.value.titulo.trim(),
      palavras_chave,
      passos,
    }

    if (editandoId.value) {
      await api.atualizarPlaybook(editandoId.value, payload)
    } else {
      await api.criarPlaybook(payload)
    }

    fecharForm()
    emit('reload')
  } catch (e) {
    erroForm.value = e.message
  } finally {
    salvando.value = false
  }
}

async function deletarPlaybook(id) {
  if (!confirm(`Remover o playbook '${id}'?`)) return
  deletando.value = id
  try {
    await api.deletarPlaybook(id)
    emit('reload')
  } catch (e) {
    alert(e.message)
  } finally {
    deletando.value = null
  }
}
</script>

<style scoped>
.section-header-row {
  display: flex;
  align-items: center;
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
.btn-sm { padding: 8px 16px; font-size: 13px; }

/* Formulário */
.form-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 24px;
}

.form-title {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--primary);
  margin-bottom: 16px;
}

.form-group { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }

.form-label { font-size: 11px; color: var(--text-dim); font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; }

.form-input,
.form-textarea {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 10px 12px;
  font-size: 13px;
  font-family: var(--sans);
  transition: border-color var(--transition);
  resize: vertical;
}

.form-input:focus,
.form-textarea:focus { outline: none; border-color: var(--primary); }

.form-input:disabled { opacity: 0.5; cursor: not-allowed; }

.form-actions { display: flex; align-items: center; gap: 12px; margin-top: 4px; }

.erro-inline { font-size: 12px; color: var(--accent); }

/* Estados */
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

/* Lista de playbooks */
.playbooks-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }

.playbook-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  transition: all var(--transition);
}

.playbook-card:hover { border-color: rgba(101, 84, 192, 0.3); }

.pb-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.pb-id {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  color: var(--secondary);
  background: rgba(101, 84, 192, 0.1);
  border: 1px solid rgba(101, 84, 192, 0.2);
  padding: 2px 7px;
  border-radius: 5px;
  display: inline-block;
  margin-bottom: 6px;
}

.pb-titulo { font-size: 14px; font-weight: 600; color: var(--text); }

.btn-danger-sm {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 6px;
  width: 30px;
  height: 30px;
  cursor: pointer;
  font-size: 13px;
  flex-shrink: 0;
  transition: all var(--transition);
}

.btn-danger-sm:hover { background: rgba(222, 53, 11, 0.1); border-color: var(--accent); }

.pb-actions { display: flex; gap: 8px; flex-shrink: 0; }

.btn-secondary-sm {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 6px;
  padding: 0 12px;
  height: 30px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  transition: all var(--transition);
}

.btn-secondary-sm:hover { color: var(--text); background: var(--overlay); border-color: var(--text-muted); }

.pb-keywords { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }

.kw-badge {
  font-size: 11px;
  background: var(--overlay);
  border: 1px solid var(--border);
  color: var(--text-dim);
  padding: 2px 8px;
  border-radius: 20px;
}

.pb-steps-details { cursor: pointer; }

.pb-steps-summary {
  font-size: 12px;
  color: var(--text-dim);
  font-family: var(--mono);
  padding: 4px 0;
  list-style: none;
}

.pb-steps {
  padding: 10px 0 0 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pb-steps li { font-size: 12px; color: var(--text-dim); line-height: 1.5; }
</style>
