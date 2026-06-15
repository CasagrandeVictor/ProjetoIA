# DWPLUS Triage — Sistema Inteligente de Chamados Jira

Sistema web de triagem automatizada de chamados do Jira com análise por IA (Gemini Flash), métricas de volume e interface Vue 3 moderna.

---

## Funcionalidades

- Listagem de chamados do Jira em tempo real (abas "Em Aberto" e "Concluídos", últimos 90 dias)
- Análise inteligente via **Gemini Flash** — sugestão de organização, categoria, prioridade e orientações técnicas detalhadas
- Verificação de histórico do usuário: antes de sugerir, o sistema busca chamados fechados anteriores do mesmo solicitante no Jira para manter a organização consistente
- Fallback automático para triagem por regras quando `GEMINI_API_KEY` não estiver configurada
- Cache de análises: a sugestão de IA é salva por chamado (`analises_cache.json`) e reaproveitada ao reabrir o chamado — botão "🔄 Reanalisar" força uma nova geração quando necessário
- **Modelo B (classificador local treinado)**: além do Gemini, um modelo de Machine Learning (TF-IDF + LinearSVC/MultinomialNB, treinado com dados reais de chamados fechados) prevê se o atendimento será **Presencial ou Remoto** a partir do texto do chamado — totalmente offline e opcional (ver seção [Modelo B](#modelo-b--classificador-local-treinado))
- Tela de **Comparação de Modelos** (acesso discreto, ferramenta de avaliação): compara a sugestão atual (Gemini/regras) e o Modelo B com os valores reais já registrados no Jira
- Aplicação da sugestão atualiza diretamente o campo Organização do chamado no Jira (com comentário de registro)
- Base de playbooks: orientações passo a passo por tipo de problema (CRUD completo)
- Feedback loop: cada triagem confirmada é registrada para melhoria contínua
- Métricas de volume: média por dia/semana/mês, pico por hora e por dia da semana
- Interface Vue 3 com layout estilo Jira (tema claro, navegação lateral) e gráficos interativos (Chart.js)
- Privacidade: apenas o domínio do e-mail é enviado ao LLM (nunca e-mail completo ou token)

---

## Pré-requisitos

- **Python 3.9+**
- **Node.js 18+** (para o frontend Vue)
- Acesso ao Jira Cloud com token de API
- Chave da API Gemini (opcional — obtida em [aistudio.google.com](https://aistudio.google.com/app/apikey))

---

## Instalação

### 1. Configure as credenciais

```bash
# Na raiz do projeto
cp .env.example backend/.env

# Edite backend/.env com suas credenciais:
# JIRA_EMAIL, JIRA_TOKEN, JIRA_URL, GEMINI_API_KEY (opcional)
```

### 2. Instale as dependências do backend

```bash
cd backend

# Crie e ative o virtualenv
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Instale as dependências do frontend Vue

```bash
cd frontend-vue
npm install
```

---

## Como Rodar

### Backend (FastAPI)

```bash
cd backend

# Windows (venv ativado)
venv\Scripts\python main.py

# Linux / macOS
venv/bin/python main.py

# Ou via uvicorn com reload automático
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API disponível em: `http://localhost:8000`  
Documentação Swagger: `http://localhost:8000/docs`

### Frontend Vue 3

```bash
cd frontend-vue
npm run dev
```

Interface disponível em: `http://localhost:5173`

> O frontend legado (`frontend/index.html`) continua funcional. Sirva com `python -m http.server 8080` dentro da pasta `frontend/`.

---

## Estrutura do Projeto

```
dwplus-triage/
├── backend/
│   ├── main.py                # API FastAPI — todos os endpoints
│   ├── llm_gemini.py          # Integração Gemini Flash (google-genai SDK)
│   ├── metricas_chamados.py   # Cálculo de métricas de volume + exportação CSV/PNG
│   ├── extrair_dataset.py     # [Modelo B] Script standalone — extrai dataset do Jira
│   ├── treinar_modelo.py      # [Modelo B] Script standalone — treina e compara classificadores
│   ├── modelo_local.py        # [Modelo B] Módulo de inferência (usado por main.py)
│   ├── modelo_atendimento.pkl # [Modelo B] Modelo treinado (gerado, não commitado)
│   ├── dataset_chamados.csv   # [Modelo B] Dataset extraído (gerado, não commitado)
│   ├── playbooks.json         # Base de conhecimento (palavras-chave + passos)
│   ├── analises_cache.json    # Cache de análises de IA por chamado (gerado em runtime)
│   ├── training_data.json     # Histórico de feedback para treinamento (gerado em runtime)
│   ├── requirements.txt       # Dependências Python
│   └── venv/                  # Virtualenv (não commitado)
├── frontend-vue/              # Interface Vue 3 + Vite
│   ├── src/
│   │   ├── style.css          # Tokens de design (tema claro estilo Jira)
│   │   ├── services/api.js    # Chamadas à API centralizadas (axios)
│   │   └── components/
│   │       ├── AppHeader.vue          # Navegação lateral por abas
│   │       ├── Dashboard.vue          # Cards de estatísticas
│   │       ├── ChamadosList.vue       # Tabela de chamados
│   │       ├── ChamadoModal.vue       # Detalhe + análise IA + aplicar organização
│   │       ├── MetricasChart.vue      # Gráficos por hora / dia / mês
│   │       ├── PlaybooksPanel.vue     # CRUD de playbooks
│   │       └── ComparacaoModelos.vue  # [Modelo B] Tela de avaliação (Modelo A vs B vs real)
│   └── .env.example
├── frontend/
│   └── index.html             # Frontend legado (mantido como referência)
├── .env.example               # Modelo de variáveis de ambiente
├── .gitignore
└── README.md
```

---

## Variáveis de Ambiente

Copie `.env.example` para `backend/.env` e preencha:

| Variável         | Obrigatória | Descrição                                         |
|------------------|-------------|---------------------------------------------------|
| `JIRA_EMAIL`     | Sim         | E-mail da conta Jira                              |
| `JIRA_TOKEN`     | Sim         | Token de API do Jira (gerado em id.atlassian.net) |
| `JIRA_URL`       | Não         | URL do Jira (padrão: `https://dwplus.atlassian.net`) |
| `GEMINI_API_KEY` | Não         | Chave Gemini — sem ela usa triagem por regras     |
| `API_HOST`       | Não         | Host da API (padrão: `0.0.0.0`)                   |
| `API_PORT`       | Não         | Porta da API (padrão: `8000`)                     |

Para o frontend Vue, crie `frontend-vue/.env`:

| Variável       | Padrão                  | Descrição               |
|----------------|-------------------------|-------------------------|
| `VITE_API_URL` | `http://localhost:8000` | URL base do backend     |

---

## API — Endpoints

| Método | Endpoint                     | Descrição                                         |
|--------|------------------------------|---------------------------------------------------|
| GET    | `/chamados`                  | Lista chamados (params: `dias`, `limite`)         |
| GET    | `/chamados/{chave}`          | Busca chamado por chave                           |
| GET    | `/chamados/{chave}/sugestao` | Recupera análise de IA já salva (sem reprocessar) — 404 se não houver |
| POST   | `/chamados/{chave}/sugestao` | Gera (ou regenera) e salva a análise de IA (Gemini, regras ou histórico do usuário) |
| PUT    | `/chamados/{chave}`          | Atualiza o campo Organização no Jira + registra feedback |
| GET    | `/stats`                     | Estatísticas gerais (total, sem org, % pendente)  |
| GET    | `/metricas`                  | Métricas de volume por hora, dia da semana e mês  |
| GET    | `/organizacoes`              | Lista organizações do Jira Service Management     |
| GET    | `/playbooks`                 | Lista playbooks cadastrados                       |
| POST   | `/playbooks`                 | Cria novo playbook                                |
| DELETE | `/playbooks/{id}`            | Remove playbook                                   |
| GET    | `/training-data`             | Exporta base de feedback de treinamento           |
| GET    | `/modelo/status`              | Status do Modelo B (treinado/disponível ou não)  |
| GET    | `/chamados/{chave}/comparar`  | [Avaliação] Compara Modelo A (Gemini/regras) e Modelo B com os valores reais do Jira |
| GET    | `/docs`                      | Documentação interativa (Swagger UI)              |

---

## Modelos de Dados

### Sugestão de IA (`SugestaoIA`)

```json
{
  "organizacao_sugerida": "Sicredi",
  "confianca": 0.91,
  "orientacoes": "Verificar credenciais do usuário na organização Sicredi...",
  "fonte": "gemini",
  "categoria": "Acesso/Autenticação",
  "prioridade": "Alta",
  "justificativa": "Domínio sicredi.com.br e descrição indicam problema de login",
  "playbook_titulo": null,
  "playbook_passos": null,
  "atendimento": "Remoto",
  "confianca_atendimento": 0.93
}
```

Valores possíveis para `fonte`: `gemini`, `historico_usuario` (o solicitante já teve chamados fechados — a sugestão é alinhada ao histórico dele), `treinamento_email`, `treinamento_dominio`, `dominio` ou `desconhecido` (fallback por regras).

Os campos `atendimento` e `confianca_atendimento` vêm do **Modelo B** (classificador local treinado) e ficam `null` quando `backend/modelo_atendimento.pkl` não existe — veja a seção [Modelo B](#modelo-b--classificador-local-treinado).

Cada análise gerada via `POST /chamados/{chave}/sugestao` é persistida em `backend/analises_cache.json` (chave → `{ "sugestao": ..., "gerado_em": "<timestamp ISO>" }`) e reaproveitada por `GET /chamados/{chave}/sugestao` até que o usuário clique em "🔄 Reanalisar" na interface.

### Métricas (`GET /metricas`)

```json
{
  "resumo": { "total": 120, "media_por_dia": 1.33, "media_por_semana": 9.23, "media_por_mes": 40.0 },
  "por_hora": { "0": 2, "8": 18, "9": 22, "10": 19, "..." : "..." },
  "por_dia_semana": { "Segunda": 28, "Terça": 31, "..." : "..." },
  "por_mes": { "2024-11": 38, "2024-12": 42, "2025-01": 40 },
  "hora_pico": 9,
  "dia_semana_pico": "Terça"
}
```

---

## Modelo B — Classificador Local Treinado

Além do Gemini, o sistema conta com um segundo modelo de IA ("Modelo B"): um
classificador de Machine Learning **treinado com dados reais** de chamados
fechados do Jira, que prevê se o **atendimento será Presencial ou Remoto** a
partir do texto (título + descrição) do chamado. Ele roda 100% local/offline
(sem custo de API) e é totalmente **opcional** — se os arquivos `.pkl` não
existirem, o sistema continua funcionando exatamente como antes (apenas
Gemini/regras + histórico do usuário), sem nenhuma quebra.

> A sugestão de **organização** continua vindo do Gemini + histórico do
> usuário (já existente). Um classificador de organização também foi treinado
> (`modelo_organizacao.pkl`) durante o desenvolvimento, mas seu desempenho
> ficou abaixo do necessário para uso em produção (f1-macro ≈ 0.31 em 30
> classes) — fica disponível apenas como material de comparação/discussão
> acadêmica.

### 1. Extrair o dataset (`extrair_dataset.py`)

Script standalone — não altera nem depende do `main.py`. Usa as mesmas
credenciais do `backend/.env`.

```bash
cd backend

# 1) Descobrir os campos do Jira (opcional — usado para investigação)
venv\Scripts\python extrair_dataset.py --listar-campos

# 2) Extrair o dataset de chamados fechados, mantendo apenas agências Sicredi
#    (padrão "NN-2604 <nome>"; o campo "Presencial/Remoto" vem das labels do Jira)
venv\Scripts\python extrair_dataset.py --campo-atendimento labels --apenas-sicredi
```

Gera `backend/dataset_chamados.csv` (gitignored) com as colunas `chave`,
`titulo`, `descricao`, `texto_limpo`, `dominio`, `organizacao`, `atendimento`,
além de imprimir um relatório de qualidade (totais, % preenchido, distribuição
de classes).

### 2. Treinar o Modelo B (`treinar_modelo.py`)

```bash
cd backend
venv\Scripts\python treinar_modelo.py
```

Para os alvos `organizacao` e `atendimento`, o script:

- Faz `train_test_split` estratificado (80/20) e validação cruzada (5 folds, `f1_macro`)
- Treina e compara 3 algoritmos: `MultinomialNB`, `LinearSVC` (calibrado) e `RandomForest`, todos sobre TF-IDF (uni+bigramas)
- Imprime relatório de classificação, matriz de confusão e métricas de cada modelo
- Salva o melhor modelo de cada alvo em `backend/modelo_atendimento.pkl` e `backend/modelo_organizacao.pkl` (gitignored)

### 3. Inferência (`modelo_local.py`)

Importado automaticamente por `main.py`. Expõe:

- `modelo_disponivel()` → `True` se `modelo_atendimento.pkl` existe e carrega corretamente
- `classificar(texto)` → `{"atendimento": "Presencial"|"Remoto", "confianca_atend": float}` ou `None`

Nunca levanta exceção — qualquer falha resulta em `None`/`False`, e o sistema
cai de volta no comportamento padrão (Gemini/regras).

### 4. Usando o Modelo B

- `POST /chamados/{chave}/sugestao` passa a incluir `atendimento` e
  `confianca_atendimento` na resposta (campos `null` se o Modelo B não estiver disponível)
- `GET /modelo/status` informa se o Modelo B está treinado/disponível
- `GET /chamados/{chave}/comparar` roda o Modelo A (Gemini/regras + histórico)
  e o Modelo B no mesmo chamado e compara ambos com os valores reais do Jira
  (organização e label Presencial/Remoto) — usado pela aba **🧪 Comparação
  (Modelo B)** no frontend (acesso discreto, ferramenta de avaliação/defesa
  acadêmica, não é uso diário)

---

## Troubleshooting

| Problema | Causa provável | Solução |
|---|---|---|
| `RuntimeError: Variável 'JIRA_EMAIL' não encontrada` | `.env` não criado ou vazio | Copie `.env.example` → `backend/.env` e preencha |
| `401 Unauthorized` | Token Jira inválido ou expirado | Gere novo token em `id.atlassian.net` → Segurança → Tokens de API |
| `404 Not Found` em chamado | Chave inválida ou sem permissão | Verifique permissões do usuário no projeto Jira |
| Gemini retorna fallback | `GEMINI_API_KEY` inválida ou cota esgotada | Verifique a chave em `aistudio.google.com` |
| CORS Error no frontend | Backend não iniciado | Confirme que `python main.py` está rodando na porta 8000 |
| Gráfico PNG não gerado | `matplotlib` não instalado | `pip install matplotlib` no venv |
| `atendimento`/`confianca_atendimento` sempre `null` | `backend/modelo_atendimento.pkl` não existe | Rode `extrair_dataset.py` e `treinar_modelo.py` (seção [Modelo B](#modelo-b--classificador-local-treinado)) |

---

## Segurança

- Credenciais lidas **exclusivamente** de variáveis de ambiente — nunca hardcoded.
- O arquivo `backend/.env` está no `.gitignore` e **nunca deve ser commitado**.
- O LLM recebe apenas: domínio do e-mail, título e descrição do chamado. E-mail completo e tokens ficam no servidor.

---

## Equipe

| Nome | Papel |
|------|-------|
| Lara da Rosa Reck | Desenvolvimento & Pesquisa |
| Davi Novakoski Magagnin | Desenvolvimento & Arquitetura |
| Lucas Scholze Hoffmann | Desenvolvimento & Integração |
| Victor Casagrande Correa | Desenvolvimento & IA |

---

*DWPLUS Tecnologia — Sistema desenvolvido para otimizar o processo de triagem de chamados de suporte.*
