import os
import sys
import io
import json
import uuid
from datetime import datetime
from pathlib import Path
from collections import Counter

# Força UTF-8 no stdout/stderr para evitar UnicodeEncodeError no Windows (CP1252)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")  # carrega backend/.env se existir

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from jira import JIRA

# Credenciais — lidas exclusivamente de variáveis de ambiente / arquivo .env
JIRA_EMAIL = os.environ["JIRA_EMAIL"]
JIRA_TOKEN = os.environ["JIRA_TOKEN"]
JIRA_URL   = os.getenv("JIRA_URL", "https://dwplus.atlassian.net")

TRAINING_DATA_PATH = Path(__file__).parent / "training_data.json"
PLAYBOOKS_PATH     = Path(__file__).parent / "playbooks.json"

app = FastAPI(
    title="DWPLUS Triage API",
    description="Sistema inteligente de triagem de chamados Jira",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Modelos Pydantic ────────────────────────────────────────────────────────

class ChamadoJira(BaseModel):
    chave: str
    usuario_id: str
    email: str
    titulo: str
    descricao: str
    organizacao_atual: str
    criado_em: str
    status: str
    prioridade: str


class SugestaoIA(BaseModel):
    organizacao_sugerida: str
    confianca: float
    orientacoes: str
    fonte: str  # "treinamento_email" | "treinamento_dominio" | "dominio" | "desconhecido"
    playbook_titulo: Optional[str] = None
    playbook_passos: Optional[List[str]] = None


class AtualizacaoChamado(BaseModel):
    chave: str
    organizacao: str
    comentario: Optional[str] = None


class Playbook(BaseModel):
    id: str
    palavras_chave: List[str]
    titulo: str
    passos: List[str]


# ─── Singleton Jira + cache do campo organização ─────────────────────────────

_jira_client: Optional[JIRA] = None
_campo_organizacao: Optional[str] = None
_orgs_jira_cache: Optional[dict] = None  # {nome: id}


def get_jira_client() -> JIRA:
    global _jira_client
    if _jira_client is None:
        print("🔗 Conectando ao Jira...")
        _jira_client = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_TOKEN))
        print("✅ Conexão estabelecida.")
    return _jira_client


def detectar_campo_organizacao(jira: JIRA) -> str:
    global _campo_organizacao
    if _campo_organizacao:
        return _campo_organizacao

    for campo in jira.fields():
        nome = campo["name"].lower()
        if nome in ("organizations", "organização", "organizacao"):
            _campo_organizacao = campo["id"]
            print(f"✅ Campo organização detectado: {campo['name']} ({_campo_organizacao})")
            return _campo_organizacao

    _campo_organizacao = "customfield_10002"
    print(f"⚠️  Campo organização não detectado, usando fallback: {_campo_organizacao}")
    return _campo_organizacao


def _extrair_chamado(issue, campo_org: str) -> ChamadoJira:
    email = getattr(issue.fields.reporter, "emailAddress", "desconhecido@dwplus.com.br")
    usuario_id = email.split("@")[0] if "@" in email else email

    org_bruta = getattr(issue.fields, campo_org, None)
    nome_org = "Não preenchido"
    if org_bruta:
        if isinstance(org_bruta, list) and org_bruta:
            nome_org = getattr(org_bruta[0], "name", str(org_bruta[0]))
        else:
            nome_org = str(org_bruta)

    status = (
        getattr(issue.fields.status, "name", "Desconhecido")
        if issue.fields.status else "Desconhecido"
    )
    prioridade = (
        getattr(issue.fields.priority, "name", "Média")
        if issue.fields.priority else "Média"
    )
    criado_em = str(issue.fields.created)[:10] if issue.fields.created else ""

    return ChamadoJira(
        chave=issue.key,
        usuario_id=usuario_id,
        email=email,
        titulo=issue.fields.summary,
        descricao=issue.fields.description or "",
        organizacao_atual=nome_org,
        criado_em=criado_em,
        status=status,
        prioridade=prioridade,
    )


# ─── Base de Treinamento ─────────────────────────────────────────────────────

def _carregar_treinamento() -> list:
    if TRAINING_DATA_PATH.exists():
        try:
            with open(TRAINING_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("examples", [])
        except Exception:
            pass
    return []


def _salvar_treinamento(examples: list):
    with open(TRAINING_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"examples": examples, "total": len(examples), "atualizado_em": datetime.now().isoformat()},
            f, ensure_ascii=False, indent=2,
        )


def _registrar_feedback(chamado: ChamadoJira, org_sugerida: str, org_escolhida: str, confianca: float, fonte: str):
    examples = _carregar_treinamento()
    dominio_completo = chamado.email.split("@")[1] if "@" in chamado.email else ""
    examples.append({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "chave": chamado.chave,
        "email": chamado.email.lower(),
        "dominio": dominio_completo.split(".")[0].lower(),
        "titulo": chamado.titulo,
        "descricao": chamado.descricao[:500],
        "organizacao_sugerida": org_sugerida,
        "organizacao_escolhida": org_escolhida,
        "sugestao_aplicada": org_sugerida == org_escolhida,
        "confianca_sugestao": confianca,
        "fonte": fonte,
    })
    _salvar_treinamento(examples)
    print(f"📝 Feedback registrado: {chamado.chave} → {org_escolhida} (sugerida: {org_sugerida})")


# ─── Playbooks ───────────────────────────────────────────────────────────────

def _carregar_playbooks() -> list:
    if PLAYBOOKS_PATH.exists():
        try:
            with open(PLAYBOOKS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("playbooks", [])
        except Exception:
            pass
    return []


def _salvar_playbooks(playbooks: list):
    with open(PLAYBOOKS_PATH, "w", encoding="utf-8") as f:
        json.dump({"playbooks": playbooks}, f, ensure_ascii=False, indent=2)


def _buscar_playbook(texto: str) -> Optional[dict]:
    """Retorna o primeiro playbook cujas palavras-chave são encontradas no texto."""
    texto_lower = texto.lower()
    for pb in _carregar_playbooks():
        if any(kw.lower() in texto_lower for kw in pb.get("palavras_chave", [])):
            return pb
    return None


# ─── Lookup de organizações no Jira ─────────────────────────────────────────

def _obter_orgs_jira(jira: JIRA) -> dict:
    """Retorna {nome_org: id_org} consultando a API do Jira Service Management."""
    global _orgs_jira_cache
    if _orgs_jira_cache is not None:
        return _orgs_jira_cache

    _orgs_jira_cache = {}
    try:
        resp = jira._session.get(
            f"{JIRA_URL}/rest/servicedeskapi/organization",
            headers={"X-ExperimentalApi": "opt-in"},
            params={"maxResults": 100},
        )
        if resp.status_code == 200:
            for org in resp.json().get("values", []):
                _orgs_jira_cache[org["name"]] = str(org["id"])
            print(f"✅ {len(_orgs_jira_cache)} organizações carregadas do Jira")
        else:
            print(f"⚠️  Não foi possível buscar organizações do Jira (status {resp.status_code})")
    except Exception as e:
        print(f"⚠️  Erro ao buscar organizações do Jira: {e}")

    return _orgs_jira_cache


# ─── IA de Triagem ───────────────────────────────────────────────────────────

_DOMINIOS_CONHECIDOS = {
    "sicredi": "Sicredi",
    "banrisul": "Banrisul",
    "bradesco": "Bradesco",
    "itau": "Itaú Unibanco",
    "santander": "Santander Brasil",
    "bb": "Banco do Brasil",
    "caixa": "Caixa Econômica Federal",
    "ambev": "Ambev",
    "petrobras": "Petrobras",
    "vale": "Vale S.A.",
    "embraer": "Embraer",
    "dwplus": "DW+ Tecnologia",
}


def gerar_sugestao_ia(chamado: ChamadoJira) -> SugestaoIA:
    email_lower = chamado.email.lower()
    dominio_completo = chamado.email.split("@")[1] if "@" in chamado.email else ""
    dominio_base = dominio_completo.split(".")[0].lower()

    # ── 1. Consulta base de treinamento ──────────────────────────────────────
    examples = _carregar_treinamento()

    same_email = [e for e in examples if e.get("email", "") == email_lower]
    if same_email:
        contagem = Counter(e["organizacao_escolhida"] for e in same_email)
        org_sugerida, votos = contagem.most_common(1)[0]
        confianca = min(0.98, 0.80 + 0.03 * votos)
        fonte = "treinamento_email"
    else:
        same_domain = [e for e in examples if e.get("dominio", "") == dominio_base]
        if same_domain:
            contagem = Counter(e["organizacao_escolhida"] for e in same_domain)
            org_sugerida, votos = contagem.most_common(1)[0]
            confianca = min(0.90, 0.70 + 0.02 * votos)
            fonte = "treinamento_dominio"
        elif dominio_base in _DOMINIOS_CONHECIDOS:
            org_sugerida = _DOMINIOS_CONHECIDOS[dominio_base]
            confianca = 0.85
            fonte = "dominio"
        else:
            org_sugerida = f"Organização {dominio_base.upper() or 'Desconhecida'}"
            confianca = 0.40
            fonte = "desconhecido"

    # ── 2. Ajuste se organização já preenchida no chamado ────────────────────
    if chamado.organizacao_atual not in ("Não preenchido", "", None):
        if chamado.organizacao_atual == org_sugerida:
            confianca = min(0.99, confianca + 0.05)

    # ── 3. Busca playbook por palavras-chave ─────────────────────────────────
    texto = (chamado.titulo + " " + chamado.descricao).lower()
    playbook = _buscar_playbook(texto)
    playbook_titulo = playbook["titulo"] if playbook else None
    playbook_passos = playbook["passos"] if playbook else None

    # ── 4. Orientações genéricas (quando não há playbook) ────────────────────
    if playbook:
        orientacoes = (
            f"Playbook identificado para '{playbook['titulo']}'. "
            f"Siga o passo a passo abaixo para resolver o chamado do usuário '{chamado.usuario_id}'."
        )
    elif any(p in texto for p in ("senha", "password", "acesso", "login", "autenticação")):
        orientacoes = (
            f"Verificar credenciais do usuário '{chamado.usuario_id}' na organização {org_sugerida}. "
            "Checar logs de autenticação e possível bloqueio de conta. "
            "Solicitar redefinição de senha via canal seguro se necessário."
        )
    elif any(p in texto for p in ("erro", "error", "falha", "exception", "crash")):
        orientacoes = (
            f"Analisar stack trace reportado pelo usuário '{chamado.usuario_id}'. "
            "Verificar logs do servidor no período informado. "
            "Confirmar versão do sistema em uso pela organização e checar changelogs recentes."
        )
    elif any(p in texto for p in ("lento", "lentidão", "performance", "demora", "timeout")):
        orientacoes = (
            "Coletar métricas de latência e throughput do ambiente do cliente. "
            f"Verificar consumo de recursos (CPU/memória) associado ao tenant da organização {org_sugerida}. "
            "Avaliar necessidade de escalonamento de infraestrutura."
        )
    elif any(p in texto for p in ("relatório", "relatorio", "exportar", "download", "arquivo")):
        orientacoes = (
            f"Checar permissões de exportação do usuário '{chamado.usuario_id}'. "
            "Verificar integridade dos dados no módulo de relatórios. "
            "Confirmar se o problema é pontual ou afeta toda a organização."
        )
    else:
        orientacoes = (
            f"Revisar histórico de chamados da organização {org_sugerida} para identificar padrão. "
            f"Contatar o usuário '{chamado.usuario_id}' para coletar mais detalhes do ambiente. "
            "Escalar para equipe especialista se não houver solução em primeiro nível."
        )

    return SugestaoIA(
        organizacao_sugerida=org_sugerida,
        confianca=confianca,
        orientacoes=orientacoes,
        fonte=fonte,
        playbook_titulo=playbook_titulo,
        playbook_passos=playbook_passos,
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/chamados", response_model=List[ChamadoJira], summary="Lista chamados do Jira")
def listar_chamados(dias: int = 90, limite: int = 50):
    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issues = jira.search_issues(
            f"created >= -{dias}d ORDER BY created DESC",
            maxResults=limite,
        )
        return [_extrair_chamado(i, campo_org) for i in issues]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar chamados: {exc}")


@app.get("/chamados/{chave}", response_model=ChamadoJira, summary="Busca chamado por chave")
def buscar_chamado(chave: str):
    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issue = jira.issue(chave)
        return _extrair_chamado(issue, campo_org)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Chamado {chave} não encontrado: {exc}")


@app.post("/chamados/{chave}/sugestao", response_model=SugestaoIA, summary="Gera sugestão de IA")
def gerar_sugestao(chave: str):
    chamado = buscar_chamado(chave)
    try:
        return gerar_sugestao_ia(chamado)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar sugestão: {exc}")


@app.put("/chamados/{chave}", summary="Atualiza chamado no Jira")
def atualizar_chamado(chave: str, atualizacao: AtualizacaoChamado):
    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issue = jira.issue(chave)

        # ── 1. Tenta atualizar o campo organização no Jira ────────────────────
        org_atualizada_no_campo = False
        orgs_disponiveis = _obter_orgs_jira(jira)
        org_id = orgs_disponiveis.get(atualizacao.organizacao)

        if org_id:
            try:
                issue.update(fields={campo_org: [{"id": org_id}]})
                org_atualizada_no_campo = True
                print(f"✅ Campo organização atualizado: {atualizacao.organizacao} (id={org_id})")
            except Exception as e:
                print(f"⚠️  Falha via issue.update: {e}")

        if not org_atualizada_no_campo and org_id:
            try:
                resp = jira._session.post(
                    f"{JIRA_URL}/rest/servicedeskapi/request/{chave}/organization",
                    json={"organizationId": org_id},
                    headers={"Content-Type": "application/json", "X-ExperimentalApi": "opt-in"},
                )
                if resp.status_code in (200, 201, 204):
                    org_atualizada_no_campo = True
                    print(f"✅ Organização atribuída via Service Desk API")
            except Exception as e:
                print(f"⚠️  Falha via Service Desk API: {e}")

        # ── 2. Adiciona comentário de triagem ─────────────────────────────────
        campo_status = "✅ Campo atualizado no Jira" if org_atualizada_no_campo else "⚠️ Apenas registrado em comentário"
        comentario_final = atualizacao.comentario or (
            f"[DWPLUS Triage] Organização identificada: {atualizacao.organizacao}\n{campo_status}"
        )
        jira.add_comment(issue, comentario_final)

        # ── 3. Registra feedback na base de treinamento ───────────────────────
        chamado_atual = _extrair_chamado(issue, campo_org)
        sugestao_atual = gerar_sugestao_ia(chamado_atual)
        _registrar_feedback(
            chamado=chamado_atual,
            org_sugerida=sugestao_atual.organizacao_sugerida,
            org_escolhida=atualizacao.organizacao,
            confianca=sugestao_atual.confianca,
            fonte=sugestao_atual.fonte,
        )

        return {
            "mensagem": f"Chamado {chave} atualizado com sucesso.",
            "chave": chave,
            "organizacao": atualizacao.organizacao,
            "campo_atualizado_no_jira": org_atualizada_no_campo,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar chamado: {exc}")


@app.get("/stats", summary="Estatísticas gerais dos chamados")
def estatisticas(dias: int = 90, limite: int = 100):
    try:
        chamados = listar_chamados(dias=dias, limite=limite)
        total = len(chamados)
        sem_org = sum(1 for c in chamados if c.organizacao_atual == "Não preenchido")
        percentual = round(sem_org / total * 100, 1) if total > 0 else 0.0
        return {
            "total": total,
            "sem_organizacao": sem_org,
            "percentual_pendente": percentual,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular estatísticas: {exc}")


@app.get("/organizacoes", summary="Lista organizações disponíveis no Jira")
def listar_organizacoes():
    try:
        jira = get_jira_client()
        orgs = _obter_orgs_jira(jira)
        return [{"nome": nome, "id": org_id} for nome, org_id in sorted(orgs.items())]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar organizações: {exc}")


@app.get("/playbooks", response_model=List[Playbook], summary="Lista playbooks cadastrados")
def listar_playbooks():
    return _carregar_playbooks()


@app.post("/playbooks", response_model=Playbook, summary="Cadastra novo playbook")
def criar_playbook(playbook: Playbook):
    playbooks = _carregar_playbooks()
    if any(p["id"] == playbook.id for p in playbooks):
        raise HTTPException(status_code=400, detail=f"Playbook com id '{playbook.id}' já existe.")
    playbooks.append(playbook.dict())
    _salvar_playbooks(playbooks)
    print(f"✅ Playbook criado: {playbook.id} ({len(playbook.palavras_chave)} palavras-chave)")
    return playbook


@app.delete("/playbooks/{playbook_id}", summary="Remove um playbook")
def deletar_playbook(playbook_id: str):
    playbooks = _carregar_playbooks()
    novos = [p for p in playbooks if p["id"] != playbook_id]
    if len(novos) == len(playbooks):
        raise HTTPException(status_code=404, detail=f"Playbook '{playbook_id}' não encontrado.")
    _salvar_playbooks(novos)
    return {"mensagem": f"Playbook '{playbook_id}' removido com sucesso."}


@app.get("/training-data", summary="Exporta base de treinamento da IA")
def exportar_treinamento():
    examples = _carregar_treinamento()
    total = len(examples)
    acertos = sum(1 for e in examples if e.get("sugestao_aplicada")) if total else 0
    return {
        "total": total,
        "acertos_sugestao": acertos,
        "taxa_acerto": round(acertos / total * 100, 1) if total else 0.0,
        "examples": examples,
    }


# ─── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    print(f"🚀 Iniciando DWPLUS Triage API em http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=False)
