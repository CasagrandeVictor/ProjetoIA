/**
 * Serviço centralizado de comunicação com a API DWPLUS Triage.
 * URL base configurável via variável de ambiente VITE_API_URL.
 * Fallback: http://localhost:8000
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Interceptor: normaliza erros da API para mensagens legíveis
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const mensagem =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'Erro desconhecido'
    return Promise.reject(new Error(mensagem))
  }
)

export const api = {
  // ── Chamados ──────────────────────────────────────────────────────────────

  listarChamados(dias = 90, limite = 50) {
    return http.get('/chamados', { params: { dias, limite } }).then((r) => r.data)
  },

  buscarChamado(chave) {
    return http.get(`/chamados/${chave}`).then((r) => r.data)
  },

  gerarSugestao(chave) {
    return http.post(`/chamados/${chave}/sugestao`).then((r) => r.data)
  },

  atualizarChamado(chave, organizacao, comentario = null) {
    return http
      .put(`/chamados/${chave}`, { chave, organizacao, comentario })
      .then((r) => r.data)
  },

  // ── Estatísticas & Métricas ───────────────────────────────────────────────

  stats(dias = 90, limite = 100) {
    return http.get('/stats', { params: { dias, limite } }).then((r) => r.data)
  },

  metricas(dias = 90, limite = 500) {
    return http.get('/metricas', { params: { dias, limite } }).then((r) => r.data)
  },

  // ── Organizações ─────────────────────────────────────────────────────────

  listarOrganizacoes() {
    return http.get('/organizacoes').then((r) => r.data)
  },

  // ── Playbooks ─────────────────────────────────────────────────────────────

  listarPlaybooks() {
    return http.get('/playbooks').then((r) => r.data)
  },

  criarPlaybook(playbook) {
    return http.post('/playbooks', playbook).then((r) => r.data)
  },

  deletarPlaybook(id) {
    return http.delete(`/playbooks/${id}`).then((r) => r.data)
  },

  // ── Dados de treinamento ──────────────────────────────────────────────────

  exportarTreinamento() {
    return http.get('/training-data').then((r) => r.data)
  },
}
