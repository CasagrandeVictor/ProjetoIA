# DWPLUS Triage — Frontend Vue 3

Interface moderna em Vue 3 + Vite para o sistema de triagem de chamados Jira com IA Gemini Flash.

## Pré-requisitos

- Node.js >= 18
- Backend FastAPI rodando (ver `../backend/`)

## Configuração

```bash
# Copie o arquivo de variáveis de ambiente
cp .env.example .env

# Edite VITE_API_URL se o backend não estiver em localhost:8000
```

## Rodando em desenvolvimento

```bash
npm install
npm run dev
```

Acesse: http://localhost:5173

## Build para produção

```bash
npm run build
# Arquivos gerados em: dist/
```

## Estrutura

```
src/
├── services/
│   └── api.js          # Todas as chamadas à API centralizadas aqui
├── components/
│   ├── AppHeader.vue   # Navegação por abas
│   ├── Dashboard.vue   # Cards de estatísticas (total, sem org, % pendente)
│   ├── ChamadosList.vue    # Tabela de chamados
│   ├── ChamadoModal.vue    # Detalhe + análise IA + aplicar organização
│   ├── MetricasChart.vue   # Gráficos por hora, dia da semana e mês (Chart.js)
│   └── PlaybooksPanel.vue  # Listar / criar / deletar playbooks
└── App.vue             # Orquestração e estado global
```

## Variáveis de ambiente

| Variável       | Padrão                  | Descrição                    |
|----------------|-------------------------|------------------------------|
| `VITE_API_URL` | `http://localhost:8000` | URL base do backend FastAPI  |
