# DWPLUS Triage — Sistema Inteligente de Chamados Jira

Sistema web profissional para triagem automatizada de chamados do Jira, com análise de IA integrada para sugestão de organização e orientações técnicas.

---

## Funcionalidades

- ✅ Listagem de chamados do Jira em tempo real (últimos 90 dias)
- ✅ Auto-detecção do campo "Organização" via API do Jira
- ✅ Análise inteligente (mock IA) com sugestão de organização por domínio de e-mail
- ✅ Orientações contextuais automáticas baseadas no conteúdo do chamado
- ✅ Aplicação de sugestões com comentário no chamado via API
- ✅ Exportação de dados para CSV com BOM UTF-8
- ✅ Estatísticas em tempo real (total, sem organização, percentual pendente)
- ✅ Interface dark mode responsiva e moderna
- ✅ Animações CSS nativas sem dependências externas

---

## Pré-requisitos

- Python 3.9+
- Acesso ao Jira Cloud (token de API)
- Navegador moderno (Chrome, Firefox, Edge, Safari)

---

## Instalação

### 1. Clone o projeto

```bash
git clone https://github.com/dwplus/triage.git
cd dwplus-triage
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env com suas credenciais reais
```

### 3. Instale as dependências do backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

---

## Como Usar

### Iniciar o Backend (FastAPI)

```bash
cd backend
# Com venv ativado:
python main.py
# Ou via uvicorn diretamente:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

O backend estará disponível em: `http://localhost:8000`  
Documentação interativa: `http://localhost:8000/docs`

### Iniciar o Frontend

```bash
cd frontend

# Python (recomendado)
python -m http.server 8080

# Node.js (alternativa)
npx serve -p 8080 .
```

Acesse no navegador: `http://localhost:8080`

### Iniciar tudo de uma vez (Linux/macOS)

```bash
chmod +x start.sh
./start.sh
```

---

## Estrutura dos Dados

### Chamado (`ChamadoJira`)

```json
{
  "chave": "DWP-1234",
  "usuario_id": "joao.silva",
  "email": "joao.silva@sicredi.com.br",
  "titulo": "Erro ao acessar o módulo financeiro",
  "descricao": "Ao tentar acessar o módulo...",
  "organizacao_atual": "Não preenchido",
  "criado_em": "2024-01-15",
  "status": "Em andamento",
  "prioridade": "Alta"
}
```

### Sugestão de IA (`SugestaoIA`)

```json
{
  "organizacao_sugerida": "Sicredi",
  "confianca": 0.85,
  "orientacoes": "Verificar credenciais do usuário 'joao.silva' na organização Sicredi..."
}
```

### Atualização de Chamado (`AtualizacaoChamado`)

```json
{
  "chave": "DWP-1234",
  "organizacao": "Sicredi",
  "comentario": "[DWPLUS Triage IA] Organização sugerida: Sicredi\n\nOrientações: ..."
}
```

### Estatísticas (`GET /stats`)

```json
{
  "total": 48,
  "sem_organizacao": 12,
  "percentual_pendente": 25.0
}
```

---

## API Endpoints

| Método | Endpoint                        | Descrição                         |
|--------|---------------------------------|-----------------------------------|
| GET    | `/chamados`                     | Lista chamados (params: dias, limite) |
| GET    | `/chamados/{chave}`             | Busca chamado específico por chave |
| POST   | `/chamados/{chave}/sugestao`    | Gera sugestão de IA para o chamado |
| PUT    | `/chamados/{chave}`             | Atualiza chamado e adiciona comentário |
| GET    | `/stats`                        | Retorna estatísticas gerais       |
| GET    | `/docs`                         | Documentação interativa (Swagger) |

---

## Estrutura do Projeto

```
dwplus-triage/
├── backend/
│   ├── main.py              # API FastAPI completa
│   └── requirements.txt     # Dependências Python
├── frontend/
│   └── index.html           # Aplicação SPA (HTML + CSS + JS)
├── README.md
├── start.sh                 # Script de inicialização
├── .env.example             # Exemplo de variáveis de ambiente
└── .gitignore
```

---

## Segurança

**Nunca commite o arquivo `.env` com credenciais reais.**

Configure as credenciais via variáveis de ambiente:

```bash
export JIRA_EMAIL="seu_email@empresa.com"
export JIRA_TOKEN="seu_token_jira"
export JIRA_URL="https://suaempresa.atlassian.net"
```

O backend usa `os.getenv()` com fallback para valores hardcoded (apenas para desenvolvimento).  
Em produção, remova os valores hardcoded e use exclusivamente variáveis de ambiente ou um vault de secrets.

---

## Troubleshooting

| Problema | Causa Provável | Solução |
|---|---|---|
| `Connection refused` no frontend | Backend não iniciado | Verifique se `python main.py` está rodando |
| `401 Unauthorized` | Token Jira inválido ou expirado | Gere um novo token em `id.atlassian.com` |
| `404 Not Found` em chamado | Chave inválida ou sem acesso | Verifique permissões no projeto Jira |
| Campo organização não detectado | Nome de campo customizado | Verifique o ID correto em `Configurações > Campos` no Jira |
| CORS Error | Frontend em porta diferente | O backend já aceita `allow_origins=["*"]` |

---

## Próximos Passos

- [ ] Implementar modelo de ML real (scikit-learn ou HuggingFace) para classificação
- [ ] Integração com LLM + RAG (Retrieval-Augmented Generation) para orientações precisas
- [ ] Banco de dados PostgreSQL para histórico de triagens e feedback loop
- [ ] Autenticação JWT para múltiplos usuários
- [ ] Dashboard com gráficos históricos (Chart.js)
- [ ] Webhook Jira para triagem automática em tempo real
- [ ] Integração com Slack/Teams para notificações

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
