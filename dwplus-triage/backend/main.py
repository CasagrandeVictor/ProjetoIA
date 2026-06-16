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

import modelo_local  # Modelo B — classificador local treinado (atendimento)

# Credenciais — lidas exclusivamente de variáveis de ambiente / arquivo .env
# NUNCA insira tokens ou senhas diretamente no código-fonte


def _exigir_env(nome: str) -> str:
    """Lê variável obrigatória e lança erro amigável se ausente."""
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(
            f"Variável de ambiente obrigatória '{nome}' não encontrada. "
            f"Copie .env.example para .env e preencha os valores reais."
        )
    return valor


JIRA_EMAIL = _exigir_env("JIRA_EMAIL")
JIRA_TOKEN = _exigir_env("JIRA_TOKEN")
JIRA_URL   = os.getenv("JIRA_URL", "https://dwplus.atlassian.net")
# GEMINI_API_KEY é opcional — se ausente o sistema usa IA de regras como fallback

TRAINING_DATA_PATH = Path(__file__).parent / "training_data.json"
PLAYBOOKS_PATH     = Path(__file__).parent / "playbooks.json"
ANALISES_PATH      = Path(__file__).parent / "analises_cache.json"

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
    # Label de atendimento lida diretamente do Jira (campo labels)
    # None quando o chamado ainda não tem a label definida
    atendimento: Optional[str] = None  # "Presencial" | "Remoto" | None


class SugestaoIA(BaseModel):
    organizacao_sugerida: str
    confianca: float
    orientacoes: str
    fonte: str  # "gemini" | "treinamento_email" | "treinamento_dominio" | "dominio" | "desconhecido" | "historico_usuario"
    playbook_titulo: Optional[str] = None
    playbook_passos: Optional[List[str]] = None
    # Campos adicionados pelo Gemini (None quando usa IA de regras)
    categoria: Optional[str] = None
    prioridade: Optional[str] = None
    justificativa: Optional[str] = None
    # Campos do Modelo B (classificador local treinado) — None se o modelo
    # ainda não foi treinado/disponível (backend/modelo_atendimento.pkl ausente)
    atendimento: Optional[str] = None  # "Presencial" | "Remoto"
    confianca_atendimento: Optional[float] = None


class AtualizacaoChamado(BaseModel):
    chave: str
    organizacao: str
    comentario: Optional[str] = None


class AtualizacaoAtendimento(BaseModel):
    atendimento: str  # "Presencial" | "Remoto"


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


def _extrair_chamado_raw_metricas(issue, campo_org: str) -> dict:
    """
    Extração leve para métricas: preserva o timestamp COMPLETO (não trunca em [:10])
    para permitir cálculos por hora do dia. Retorna dict simples (sem Pydantic).
    """
    email = getattr(issue.fields.reporter, "emailAddress", "desconhecido@dwplus.com.br")
    org_bruta = getattr(issue.fields, campo_org, None)
    nome_org = "Não preenchido"
    if org_bruta:
        if isinstance(org_bruta, list) and org_bruta:
            nome_org = getattr(org_bruta[0], "name", str(org_bruta[0]))
        else:
            nome_org = str(org_bruta)
    return {
        "chave": issue.key,
        "email": email,
        # Timestamp completo: "2024-03-15T14:32:00.000+0000"
        "criado_em": str(issue.fields.created) if issue.fields.created else "",
        "organizacao_atual": nome_org,
        "status": getattr(issue.fields.status, "name", "Desconhecido") if issue.fields.status else "Desconhecido",
    }


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
        atendimento=_extrair_atendimento_real(issue),
    )


# Valores reconhecidos no campo padrão "labels" do Jira como atendimento
# Presencial/Remoto (mesmo critério usado em extrair_dataset.py para o treino)
_VALORES_ATENDIMENTO = {"presencial", "remoto", "remota"}

# Labels EXATAS usadas para SALVAR o atendimento no Jira — capitalização
# confirmada a partir do dataset real extraído (extrair_dataset.py / TAREFA 1)
LABEL_PRESENCIAL = "Presencial"
LABEL_REMOTO = "Remoto"


def _extrair_atendimento_real(issue) -> Optional[str]:
    """Retorna 'Presencial'/'Remoto' a partir das labels do chamado, ou None se ausente."""
    for label in getattr(issue.fields, "labels", None) or []:
        if str(label).lower() in _VALORES_ATENDIMENTO:
            return str(label)
    return None


# ─── Base de Treinamento ─────────────────────────────────────────────────────

def _carregar_dados_treinamento() -> dict:
    """Lê o JSON completo de training_data.json (todas as chaves, não só 'examples')."""
    if TRAINING_DATA_PATH.exists():
        try:
            with open(TRAINING_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _carregar_treinamento() -> list:
    return _carregar_dados_treinamento().get("examples", [])


def _salvar_treinamento(examples: list):
    dados = _carregar_dados_treinamento()
    dados["examples"] = examples
    dados["total"] = len(examples)
    dados["atualizado_em"] = datetime.now().isoformat()
    with open(TRAINING_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ─── Feedback do Modelo B (atendimento) ──────────────────────────────────────

def _carregar_feedback_atendimento() -> list:
    return _carregar_dados_treinamento().get("examples_atendimento", [])


def _salvar_feedback_atendimento(examples: list):
    dados = _carregar_dados_treinamento()
    dados["examples_atendimento"] = examples
    dados["total_atendimento"] = len(examples)
    dados["atualizado_em"] = datetime.now().isoformat()
    with open(TRAINING_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _registrar_feedback_atendimento(
    chamado: ChamadoJira,
    atendimento_sugerido: Optional[str],
    confianca_sugerido: Optional[float],
    atendimento_escolhido: str,
):
    """Registra o que o Modelo B sugeriu vs. o que o humano confirmou/corrigiu — dado para melhoria futura do modelo."""
    examples = _carregar_feedback_atendimento()
    examples.append({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "chave": chamado.chave,
        "titulo": chamado.titulo,
        "descricao": chamado.descricao[:500],
        "atendimento_sugerido": atendimento_sugerido,
        "confianca_sugerido": confianca_sugerido,
        "atendimento_escolhido": atendimento_escolhido,
        "sugestao_aplicada": atendimento_sugerido == atendimento_escolhido,
    })
    _salvar_feedback_atendimento(examples)
    print(f"📝 Feedback de atendimento registrado: {chamado.chave} → {atendimento_escolhido} (sugerido: {atendimento_sugerido})")


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


# ─── Cache de análises de IA ─────────────────────────────────────────────────
# Evita reprocessar (e gastar cota do Gemini) sempre que o técnico reabre um
# chamado já analisado — a sugestão fica salva e só é refeita sob pedido.

def _carregar_analises() -> dict:
    if ANALISES_PATH.exists():
        try:
            with open(ANALISES_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("analises", {})
        except Exception:
            pass
    return {}


def _salvar_analise(chave: str, sugestao: "SugestaoIA"):
    analises = _carregar_analises()
    analises[chave] = {
        "sugestao": sugestao.model_dump(),
        "gerado_em": datetime.now().isoformat(),
    }
    with open(ANALISES_PATH, "w", encoding="utf-8") as f:
        json.dump({"analises": analises}, f, ensure_ascii=False, indent=2)


def _buscar_analise_salva(chave: str) -> Optional[dict]:
    return _carregar_analises().get(chave)


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


def _buscar_organizacao_historica(jira: JIRA, email: str, campo_org: str) -> Optional[dict]:
    """
    Busca no Jira chamados FECHADOS do mesmo solicitante (mesmo e-mail) que já
    têm a organização preenchida, e retorna a organização mais frequente entre
    eles. Esse é um sinal muito mais forte e determinístico do que inferir a
    organização pelo domínio do e-mail — garante que o mesmo usuário sempre
    receba a mesma sugestão de organização, alinhada ao seu próprio histórico.
    """
    try:
        email_escapado = email.replace('"', '\\"')
        jql = f'reporter = "{email_escapado}" AND status in ("Resolvido", "cancelado") ORDER BY created DESC'
        issues = jira.search_issues(jql, maxResults=20, fields=f"reporter,{campo_org},summary,status")
    except Exception:
        return None

    organizacoes = []
    for issue in issues:
        org_bruta = getattr(issue.fields, campo_org, None)
        nome_org = None
        if org_bruta:
            if isinstance(org_bruta, list) and org_bruta:
                nome_org = getattr(org_bruta[0], "name", str(org_bruta[0]))
            else:
                nome_org = str(org_bruta)
        if nome_org and nome_org != "Não preenchido":
            organizacoes.append(nome_org)

    if not organizacoes:
        return None

    contagem = Counter(organizacoes)
    org_mais_comum, votos = contagem.most_common(1)[0]
    return {
        "organizacao": org_mais_comum,
        "ocorrencias": votos,
        "total_chamados": len(organizacoes),
    }


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


def _aplicar_modelo_b(sugestao: SugestaoIA, texto: str) -> SugestaoIA:
    """
    Preenche os campos `atendimento`/`confianca_atendimento` da sugestão usando
    o Modelo B (classificador local treinado em treinar_modelo.py). Se o modelo
    não estiver disponível (.pkl ausente) ou houver qualquer erro, os campos
    permanecem None — não afeta organização, categoria, prioridade nem orientações.
    """
    if modelo_local.modelo_disponivel():
        resultado = modelo_local.classificar(texto)
        if resultado:
            sugestao.atendimento = resultado["atendimento"]
            sugestao.confianca_atendimento = resultado["confianca_atend"]
    return sugestao


def _orientacoes_do_playbook(playbook: dict) -> str:
    """
    Texto curto de orientação quando há playbook — o passo a passo em si é
    exibido no bloco dedicado de playbook da interface (sem repetir aqui).
    """
    return f"Playbook identificado: '{playbook['titulo']}'. Siga o passo a passo detalhado logo abaixo."


def _gerar_sugestao_unificada(chamado: ChamadoJira) -> SugestaoIA:
    """
    Sempre busca primeiro um playbook compatível por palavra-chave — se encontrado,
    seu passo a passo vira a orientação principal (de forma determinística: o mesmo
    conjunto de palavras-chave sempre resulta no mesmo playbook, garantindo que
    chamados parecidos recebam exatamente o mesmo passo a passo ao longo do tempo).

    Para os demais campos (organização, categoria, prioridade, justificativa),
    despacha para Gemini quando GEMINI_API_KEY estiver configurada; caso contrário
    usa a lógica de regras (gerar_sugestao_ia).
    """
    texto = (chamado.titulo + " " + chamado.descricao).lower()
    playbook = _buscar_playbook(texto)

    # Busca no Jira chamados fechados anteriores do MESMO usuário — se ele já
    # teve chamados resolvidos com organização preenchida, essa é a fonte mais
    # confiável (e determinística) para sugerir a organização agora.
    historico_org = None
    jira_cliente = None
    try:
        jira_cliente = get_jira_client()
        campo_org = detectar_campo_organizacao(jira_cliente)
        historico_org = _buscar_organizacao_historica(jira_cliente, chamado.email, campo_org)
    except Exception as e:
        print(f"⚠️  Não foi possível consultar histórico do usuário no Jira: {e}")

    if not os.getenv("GEMINI_API_KEY"):
        sugestao = gerar_sugestao_ia(chamado)
        if playbook:
            sugestao.orientacoes = _orientacoes_do_playbook(playbook)
        if historico_org:
            sugestao.organizacao_sugerida = historico_org["organizacao"]
            sugestao.confianca = min(0.99, 0.90 + 0.02 * historico_org["ocorrencias"])
            sugestao.fonte = "historico_usuario"
        return _aplicar_modelo_b(sugestao, texto)

    from llm_gemini import analisar_chamado

    # Tenta carregar organizações válidas para guiar o Gemini (não bloqueante)
    orgs_validas: list = []
    try:
        orgs_validas = list(_obter_orgs_jira(jira_cliente or get_jira_client()).keys())
    except Exception as e:
        print(f"⚠️  Não foi possível carregar organizações para o Gemini: {e}")

    resultado = analisar_chamado(chamado.model_dump(), orgs_validas, playbook)

    orientacoes = _orientacoes_do_playbook(playbook) if playbook else resultado["orientacoes"]

    organizacao_sugerida = resultado["organizacao_sugerida"]
    confianca = resultado["confianca"]
    justificativa = resultado.get("justificativa")
    fonte = "gemini"

    # Histórico do próprio usuário tem prioridade sobre a inferência da IA —
    # garante consistência: o mesmo solicitante sempre cai na mesma organização.
    if historico_org:
        organizacao_sugerida = historico_org["organizacao"]
        confianca = min(0.99, 0.90 + 0.02 * historico_org["ocorrencias"])
        fonte = "historico_usuario"
        justificativa = (
            f"O usuário '{chamado.usuario_id}' já teve {historico_org['total_chamados']} "
            f"chamado(s) fechado(s) anteriormente, sendo {historico_org['ocorrencias']} "
            f"associado(s) à organização '{historico_org['organizacao']}'. "
            "Mantendo a sugestão alinhada ao histórico do próprio usuário."
        )

    sugestao = SugestaoIA(
        organizacao_sugerida=organizacao_sugerida,
        confianca=confianca,
        orientacoes=orientacoes,
        fonte=fonte,
        categoria=resultado.get("categoria"),
        prioridade=resultado.get("prioridade"),
        justificativa=justificativa,
        playbook_titulo=playbook["titulo"] if playbook else None,
        playbook_passos=playbook["passos"] if playbook else None,
    )
    return _aplicar_modelo_b(sugestao, texto)


# ─── Endpoints ───────────────────────────────────────────────────────────────

_STATUS_GRUPOS = {
    "aberto": ["Aberto", "Aguardando pelo suporte"],
    "concluido": ["Resolvido", "cancelado"],
}


@app.get("/chamados", response_model=List[ChamadoJira], summary="Lista chamados do Jira")
def listar_chamados(dias: int = 90, limite: int = 50, status_grupo: Optional[str] = None):
    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)

        jql = f"created >= -{dias}d"
        status_nomes = _STATUS_GRUPOS.get(status_grupo)
        if status_nomes:
            lista = ", ".join(f'"{nome}"' for nome in status_nomes)
            jql += f" AND status in ({lista})"
        jql += " ORDER BY created DESC"

        issues = jira.search_issues(jql, maxResults=limite)
        return [_extrair_chamado(i, campo_org) for i in issues]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar chamados: {exc}")


@app.get("/chamados/atendimento-pendente", summary="Lista chamados sem label de atendimento + sugestão do Modelo B")
def chamados_atendimento_pendente(dias: int = 90, limite: int = 200):
    """
    Pega os chamados em aberto, filtra os que ainda NÃO têm label
    Presencial/Remoto, roda APENAS o Modelo B local em cada um e devolve
    a sugestão com confiança. NUNCA chama o Gemini — inferência local pura.

    Precisa estar definido antes de /chamados/{chave} para o FastAPI não
    capturar 'atendimento-pendente' como valor do parâmetro {chave}.
    """
    if not modelo_local.modelo_disponivel():
        return {"disponivel": False, "chamados": []}

    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        # Reutiliza os mesmos status da aba "Em Aberto"
        status_aberto = ", ".join(f'"{s}"' for s in _STATUS_GRUPOS["aberto"])
        issues = jira.search_issues(
            f"created >= -{dias}d AND status in ({status_aberto}) ORDER BY created DESC",
            maxResults=limite,
            fields=f"summary,description,reporter,labels,{campo_org},status",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar chamados: {exc}")

    resultado = []
    for issue in issues:
        # Descarta chamados que já têm label de atendimento
        labels = list(getattr(issue.fields, "labels", None) or [])
        if any(lb in (LABEL_PRESENCIAL, LABEL_REMOTO) for lb in labels):
            continue

        titulo = issue.fields.summary or ""
        descricao = issue.fields.description or ""
        email = getattr(issue.fields.reporter, "emailAddress", "desconhecido@dwplus.com.br")

        classificacao = modelo_local.classificar(f"{titulo} {descricao}")

        resultado.append({
            "chave": issue.key,
            "titulo": titulo,
            "descricao": descricao[:300],
            "relator": email,
            "atendimento_sugerido": classificacao["atendimento"] if classificacao else None,
            "confianca": round(classificacao["confianca_atend"], 4) if classificacao else None,
            # revisar=True quando confiança baixa (<70%) ou modelo não classificou
            "revisar": (classificacao["confianca_atend"] < 0.70) if classificacao else True,
        })

    return {"disponivel": True, "chamados": resultado}


@app.get("/chamados/{chave}", response_model=ChamadoJira, summary="Busca chamado por chave")
def buscar_chamado(chave: str):
    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issue = jira.issue(chave)
        return _extrair_chamado(issue, campo_org)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Chamado {chave} não encontrado: {exc}")


@app.get("/chamados/{chave}/sugestao", summary="Recupera análise de IA já salva (sem reprocessar)")
def obter_sugestao_salva(chave: str):
    """
    Retorna a última análise salva para o chamado, se existir — não chama a IA
    novamente. O frontend usa isso para evitar reanalisar toda vez que o
    técnico reabre um chamado já analisado anteriormente.
    """
    salva = _buscar_analise_salva(chave)
    if not salva:
        raise HTTPException(status_code=404, detail="Nenhuma análise salva para este chamado.")
    return salva


@app.post("/chamados/{chave}/sugestao", response_model=SugestaoIA, summary="Gera (ou regenera) sugestão de IA")
def gerar_sugestao(chave: str):
    """
    Usa Gemini Flash quando GEMINI_API_KEY estiver configurada; fallback para regras.
    A sugestão gerada é salva e passa a ser reaproveitada nas próximas aberturas
    do chamado — para reanalisar, o técnico aciona este endpoint explicitamente.
    """
    chamado = buscar_chamado(chave)
    try:
        sugestao = _gerar_sugestao_unificada(chamado)
        _salvar_analise(chave, sugestao)
        return sugestao
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar sugestão: {exc}")


@app.get("/modelo/status", summary="Status do Modelo B (classificador local treinado)")
def status_modelo():
    """Indica se o Modelo B (atendimento Presencial/Remoto) está treinado e disponível."""
    return {
        "modelo_b_disponivel": modelo_local.modelo_disponivel(),
        "alvo": "atendimento (Presencial/Remoto)",
        "arquivo": modelo_local.MODELO_ATENDIMENTO_PATH.name,
    }


@app.get("/chamados/{chave}/comparar", summary="Compara Modelo B vs Gemini/regras vs valor real (avaliação)")
def comparar_modelos(chave: str):
    """
    Roda o fluxo normal de sugestão (Gemini/regras + histórico do usuário, aqui
    chamado de "Modelo A") e o Modelo B (classificador local treinado) sobre o
    mesmo chamado, e compara ambos com os valores reais já registrados no Jira
    (organização do chamado e label Presencial/Remoto).

    Ferramenta de avaliação para a defesa acadêmica — não faz parte do fluxo
    diário de triagem.
    """
    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issue = jira.issue(chave)
        chamado = _extrair_chamado(issue, campo_org)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Chamado {chave} não encontrado: {exc}")

    sugestao = _gerar_sugestao_unificada(chamado)

    real_organizacao = chamado.organizacao_atual
    real_atendimento = _extrair_atendimento_real(issue)

    return {
        "chave": chave,
        "modelo_b_disponivel": modelo_local.modelo_disponivel(),
        "organizacao": {
            "modelo_a": sugestao.organizacao_sugerida,
            "fonte_modelo_a": sugestao.fonte,
            "real": real_organizacao,
            "correto": (
                sugestao.organizacao_sugerida == real_organizacao
                if real_organizacao != "Não preenchido" else None
            ),
        },
        "atendimento": {
            "modelo_b": sugestao.atendimento,
            "confianca_modelo_b": sugestao.confianca_atendimento,
            "real": real_atendimento,
            "correto": (
                sugestao.atendimento == real_atendimento
                if sugestao.atendimento and real_atendimento != "Não preenchido" else None
            ),
        },
    }


@app.put("/chamados/{chave}", summary="Atualiza chamado no Jira")
def atualizar_chamado(chave: str, atualizacao: AtualizacaoChamado):
    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issue = jira.issue(chave)

        # ── 1. Tenta atualizar o campo organização no Jira ────────────────────
        # O campo "Organizations" (sd-customerorganization) espera uma matriz
        # com os IDs das organizações como strings simples — ex: ["10"] — e não
        # objetos {"id": ...} ou {"name": ...} (o Jira rejeita esses formatos
        # com "Especifique o valor para Organizations na matriz").
        org_atualizada_no_campo = False
        orgs_disponiveis = _obter_orgs_jira(jira)
        org_id = orgs_disponiveis.get(atualizacao.organizacao)

        if org_id:
            try:
                issue.update(fields={campo_org: [org_id]})
                org_atualizada_no_campo = True
                print(f"✅ Campo organização atualizado: {atualizacao.organizacao} (id={org_id})")
            except Exception as e:
                print(f"⚠️  Falha ao atualizar campo organização: {e}")

        # ── 2. Adiciona comentário de triagem ─────────────────────────────────
        campo_status = "✅ Campo atualizado no Jira" if org_atualizada_no_campo else "⚠️ Apenas registrado em comentário"
        comentario_final = atualizacao.comentario or (
            f"[DWPLUS Triage] Organização identificada: {atualizacao.organizacao}\n{campo_status}"
        )
        jira.add_comment(issue, comentario_final)

        # ── 3. Registra feedback na base de treinamento ───────────────────────
        chamado_atual = _extrair_chamado(issue, campo_org)
        sugestao_atual = _gerar_sugestao_unificada(chamado_atual)
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


@app.put("/chamados/{chave}/atendimento", summary="Atualiza a label de atendimento (Presencial/Remoto) no Jira")
def atualizar_atendimento(chave: str, atualizacao: AtualizacaoAtendimento):
    """
    Atualiza a label de atendimento (Presencial/Remoto) do chamado no Jira.

    IMPORTANTE: o campo `labels` do Jira é uma LISTA — um chamado pode ter
    outras labels além de Presencial/Remoto (ex: "Urgente", "TI"). Por isso,
    em vez de sobrescrever a lista inteira, removemos apenas a label de
    atendimento antiga (se existir) e adicionamos a nova, preservando todas
    as demais labels do chamado.

    Não afeta o campo Organização (PUT /chamados/{chave} continua igual).
    """
    valor = atualizacao.atendimento
    if valor not in (LABEL_PRESENCIAL, LABEL_REMOTO):
        raise HTTPException(
            status_code=400,
            detail=f"Valor inválido para atendimento: '{valor}'. Use '{LABEL_PRESENCIAL}' ou '{LABEL_REMOTO}'.",
        )

    try:
        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issue = jira.issue(chave)

        # Preserva todas as labels que não sejam de atendimento, e adiciona a nova
        labels_atuais = list(getattr(issue.fields, "labels", None) or [])
        labels_preservadas = [l for l in labels_atuais if l not in (LABEL_PRESENCIAL, LABEL_REMOTO)]
        novas_labels = labels_preservadas + [valor]

        issue.update(fields={"labels": novas_labels})
        print(f"✅ Atendimento atualizado: {chave} → {valor} (labels: {novas_labels})")

        # Registra feedback: o que o Modelo B sugeriu vs. o que o humano escolheu
        chamado = _extrair_chamado(issue, campo_org)
        sugestao_b = modelo_local.classificar(f"{chamado.titulo} {chamado.descricao}")
        _registrar_feedback_atendimento(
            chamado=chamado,
            atendimento_sugerido=sugestao_b["atendimento"] if sugestao_b else None,
            confianca_sugerido=sugestao_b["confianca_atend"] if sugestao_b else None,
            atendimento_escolhido=valor,
        )

        return {
            "mensagem": f"Atendimento do chamado {chave} atualizado para '{valor}'.",
            "chave": chave,
            "atendimento": valor,
            "labels": novas_labels,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar atendimento: {exc}")


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


@app.get("/metricas", summary="Métricas de volume de chamados (por hora, dia da semana, mês)")
def metricas_chamados(dias: int = 90, limite: int = 500):
    """
    Busca chamados com timestamp COMPLETO (não truncado) para calcular
    distribuição por hora do dia, dia da semana e mês.
    """
    try:
        from metricas_chamados import calcular_metricas

        jira = get_jira_client()
        campo_org = detectar_campo_organizacao(jira)
        issues = jira.search_issues(
            f"created >= -{dias}d ORDER BY created DESC",
            maxResults=limite,
        )
        chamados_raw = [_extrair_chamado_raw_metricas(i, campo_org) for i in issues]
        metricas = calcular_metricas(chamados_raw)
        metricas["periodo_dias"] = dias
        metricas["total_analisado"] = len(chamados_raw)
        return metricas
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular métricas: {exc}")


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


@app.put("/playbooks/{playbook_id}", response_model=Playbook, summary="Atualiza um playbook existente")
def atualizar_playbook(playbook_id: str, playbook: Playbook):
    if playbook.id != playbook_id:
        raise HTTPException(status_code=400, detail="O id do playbook não pode ser alterado.")

    playbooks = _carregar_playbooks()
    indice = next((i for i, p in enumerate(playbooks) if p["id"] == playbook_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail=f"Playbook '{playbook_id}' não encontrado.")

    playbooks[indice] = playbook.dict()
    _salvar_playbooks(playbooks)
    print(f"✏️  Playbook atualizado: {playbook_id} ({len(playbook.palavras_chave)} palavras-chave)")
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
