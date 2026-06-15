"""
Script standalone de extração do dataset de chamados fechados do Jira.

Gera um CSV (`dataset_chamados.csv`) com os chamados já resolvidos/cancelados,
incluindo o texto normalizado (título + descrição) e os dois rótulos que serão
usados no treino do Modelo B (Tarefa 2):

    - organizacao  → label 1 (agência/organização do chamado)
    - atendimento  → label 2 (Presencial / Remota)

Modos de uso:

    # 1) Descobrir o ID do campo customizado de "Presencial/Remota"
    python extrair_dataset.py --listar-campos

    # 2) Extrair o dataset, depois de descobrir o campo acima
    python extrair_dataset.py --campo-atendimento customfield_XXXXX

Não importa nem altera `main.py` — roda de forma independente, usando as
mesmas credenciais do `backend/.env`.
"""

import argparse
import csv
import os
import re
import sys
import io
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Optional

# Força UTF-8 no stdout/stderr para evitar UnicodeEncodeError no Windows (CP1252)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from jira import JIRA


# ─── Credenciais (mesmo padrão do main.py) ───────────────────────────────────

def _exigir_env(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(
            f"Variável de ambiente obrigatória '{nome}' não encontrada. "
            f"Copie .env.example para .env e preencha os valores reais."
        )
    return valor


JIRA_EMAIL = _exigir_env("JIRA_EMAIL")
JIRA_TOKEN = _exigir_env("JIRA_TOKEN")
JIRA_URL = os.getenv("JIRA_URL", "https://dwplus.atlassian.net")

# Palavras-chave usadas para destacar candidatos ao campo "Presencial/Remota"
PALAVRAS_CHAVE_ATENDIMENTO = [
    "atendimento", "modalidade", "presencial", "remoto", "remota",
    "tipo", "forma", "local", "modo", "canal",
]


def get_jira_client() -> JIRA:
    print("🔗 Conectando ao Jira...")
    jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_TOKEN))
    print("✅ Conexão estabelecida.")
    return jira


def detectar_campo_organizacao(jira: JIRA) -> str:
    """Mesma lógica de detecção usada em main.py, duplicada para manter o script standalone."""
    for campo in jira.fields():
        nome = campo["name"].lower()
        if nome in ("organizations", "organização", "organizacao"):
            print(f"✅ Campo organização detectado: {campo['name']} ({campo['id']})")
            return campo["id"]
    print("⚠️  Campo organização não detectado, usando fallback: customfield_10002")
    return "customfield_10002"


# ─── Modo 1: listar campos do Jira ───────────────────────────────────────────

def listar_campos(jira: JIRA):
    print("\n📋 Campos disponíveis no Jira (id ─ nome):\n")
    candidatos = []
    for campo in sorted(jira.fields(), key=lambda c: c["name"].lower()):
        nome_lower = campo["name"].lower()
        is_candidato = any(palavra in nome_lower for palavra in PALAVRAS_CHAVE_ATENDIMENTO)
        marca = "⭐ " if is_candidato else "   "
        print(f"{marca}{campo['id']:<20} {campo['name']}")
        if is_candidato:
            candidatos.append(campo)

    print("\n" + "─" * 60)
    if candidatos:
        print("⭐ Candidatos a campo 'Presencial/Remota' (use o id em --campo-atendimento):")
        for campo in candidatos:
            print(f"   {campo['id']:<20} {campo['name']}")
    else:
        print("⚠️  Nenhum campo candidato encontrado pelas palavras-chave conhecidas.")
        print(f"   Palavras-chave usadas: {', '.join(PALAVRAS_CHAVE_ATENDIMENTO)}")


# ─── Normalização de texto ────────────────────────────────────────────────────

def limpar_texto(texto: str) -> str:
    """
    Normaliza texto para uso em ML: minúsculas, sem e-mails/URLs, sem acentos
    e sem pontuação — mantendo apenas letras, números e espaços simples.
    """
    texto = (texto or "").lower()
    texto = re.sub(r"\S+@\S+", " ", texto)              # remove e-mails
    texto = re.sub(r"https?://\S+|www\.\S+", " ", texto)  # remove URLs

    # Remove acentos (NFKD separa o caractere base do acento; descartamos o acento)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)  # remove pontuação/símbolos
    texto = re.sub(r"\s+", " ", texto).strip()  # colapsa espaços
    return texto


# ─── Extração de valor de campos customizados (organização / atendimento) ────

def _extrair_valor_campo(valor) -> str:
    """
    Campos customizados do Jira podem vir como lista de opções, objeto único
    com atributo `.value` (select) ou `.name` (organização), ou string simples.
    """
    if valor is None:
        return "Não preenchido"
    if isinstance(valor, list):
        if not valor:
            return "Não preenchido"
        valor = valor[0]
    for atributo in ("value", "name"):
        if hasattr(valor, atributo):
            return str(getattr(valor, atributo))
    return str(valor)


# Valores válidos do campo "labels" (Categorias) usado como rótulo Presencial/Remota
_VALORES_ATENDIMENTO = {"presencial", "remoto", "remota"}

# Agências Sicredi seguem o padrão "NN-2604 <nome>" (ex: "01-2604 Sicredi Sureg",
# "07-2604 Tubarão"). Organizações fora desse padrão são clientes externos
# (contabilidades, IDB, SOS Animal etc.) e ficam fora do escopo do Modelo B.
PADRAO_AGENCIA_SICREDI = re.compile(r"^\d{2}-2604")


def _e_agencia_sicredi(organizacao: str) -> bool:
    return bool(PADRAO_AGENCIA_SICREDI.match(organizacao))


def _extrair_atendimento(valor) -> str:
    """
    O campo 'Presencial/Remota' é o campo padrão `labels` (Categorias) do Jira,
    que pode conter outras tags além de 'Presencial'/'Remoto'. Procura
    especificamente por um desses dois valores na lista.
    """
    if not valor:
        return "Não preenchido"
    if isinstance(valor, list):
        for item in valor:
            if str(item).lower() in _VALORES_ATENDIMENTO:
                return str(item)
        return "Não preenchido"
    return _extrair_valor_campo(valor)


# ─── Modo 2: extração do dataset ─────────────────────────────────────────────

def extrair_dataset(jira: JIRA, campo_atendimento: str, campo_organizacao: str,
                     output: Path, limite: Optional[int], apenas_sicredi: bool):
    jql = "statusCategory = Done ORDER BY created DESC"
    campos = f"summary,description,reporter,{campo_organizacao},{campo_atendimento}"

    print(f"\n🔍 JQL: {jql}")
    print(f"📦 Campos solicitados: {campos}\n")

    # Jira Cloud não aceita mais paginação por `startAt` — `enhanced_search_issues`
    # com maxResults=False pagina internamente via nextPageToken e traz tudo.
    todos_issues = jira.enhanced_search_issues(jql, maxResults=False, fields=campos)
    print(f"  ... {len(todos_issues)} chamados obtidos")

    if limite:
        todos_issues = todos_issues[:limite]

    print(f"\n✅ Total de chamados extraídos: {len(todos_issues)}")

    linhas = []
    for issue in todos_issues:
        email = getattr(issue.fields.reporter, "emailAddress", "") if issue.fields.reporter else ""
        dominio = email.split("@")[1].split(".")[0].lower() if "@" in email else ""

        titulo = issue.fields.summary or ""
        descricao = issue.fields.description or ""
        texto_completo = f"{titulo} {descricao}"

        organizacao = _extrair_valor_campo(getattr(issue.fields, campo_organizacao, None))
        atendimento = _extrair_atendimento(getattr(issue.fields, campo_atendimento, None))

        linhas.append({
            "chave": issue.key,
            "titulo": titulo,
            "descricao": descricao,
            "texto_limpo": limpar_texto(texto_completo),
            "dominio": dominio,
            "organizacao": organizacao,
            "atendimento": atendimento,
        })

    if apenas_sicredi:
        antes = len(linhas)
        linhas = [l for l in linhas if _e_agencia_sicredi(l["organizacao"])]
        print(f"\n🔎 Filtro --apenas-sicredi: {antes} → {len(linhas)} chamados "
              f"(removidos {antes - len(linhas)} de organizações fora do padrão 'NN-2604')")

    # ── Grava o CSV ───────────────────────────────────────────────────────────
    with open(output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "chave", "titulo", "descricao", "texto_limpo", "dominio", "organizacao", "atendimento",
        ])
        writer.writeheader()
        writer.writerows(linhas)

    print(f"💾 Dataset salvo em: {output}")

    # ── Relatório de qualidade ───────────────────────────────────────────────
    total = len(linhas)
    com_org = sum(1 for l in linhas if l["organizacao"] != "Não preenchido")
    com_atend = sum(1 for l in linhas if l["atendimento"] != "Não preenchido")

    print("\n" + "═" * 60)
    print("📊 RELATÓRIO DE QUALIDADE DO DATASET")
    print("═" * 60)
    print(f"Total de chamados:                {total}")
    if total:
        print(f"Com organização preenchida:       {com_org} ({100 * com_org / total:.1f}%)")
        print(f"Com atendimento preenchido:       {com_atend} ({100 * com_atend / total:.1f}%)")

    print("\nDistribuição de 'atendimento':")
    for valor, qtd in Counter(l["atendimento"] for l in linhas).most_common():
        print(f"  {valor:<25} {qtd}")

    org_counts = Counter(l["organizacao"] for l in linhas if l["organizacao"] != "Não preenchido")
    classes_poucos_exemplos = sum(1 for q in org_counts.values() if q < 5)
    print(f"\nDistribuição de 'organizacao' ({len(org_counts)} classes, "
          f"{classes_poucos_exemplos} com < 5 exemplos):")
    for org, qtd in org_counts.most_common():
        print(f"  {org:<35} {qtd}")
    print("═" * 60)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extrai dataset de chamados fechados do Jira para treino do Modelo B."
    )
    parser.add_argument(
        "--listar-campos", action="store_true",
        help="Lista todos os campos do Jira, destacando candidatos a 'Presencial/Remota'.",
    )
    parser.add_argument(
        "--campo-atendimento", metavar="customfield_XXXXX",
        help="ID do campo customizado que indica Presencial/Remota (descoberto via --listar-campos).",
    )
    parser.add_argument(
        "--campo-organizacao", metavar="customfield_XXXXX", default=None,
        help="ID do campo de organização. Se omitido, é detectado automaticamente.",
    )
    parser.add_argument(
        "--output", default=None,
        help="Caminho do CSV de saída (padrão: backend/dataset_chamados.csv).",
    )
    parser.add_argument(
        "--limite", type=int, default=None,
        help="Limita o número de chamados extraídos (útil para testes rápidos).",
    )
    parser.add_argument(
        "--apenas-sicredi", action="store_true",
        help="Mantém apenas chamados de organizações no padrão 'NN-2604 <nome>' "
             "(agências Sicredi), descartando clientes externos.",
    )
    args = parser.parse_args()

    if not args.listar_campos and not args.campo_atendimento:
        parser.print_help()
        sys.exit(1)

    jira = get_jira_client()

    if args.listar_campos:
        listar_campos(jira)
        return

    campo_organizacao = args.campo_organizacao or detectar_campo_organizacao(jira)
    output = Path(args.output) if args.output else Path(__file__).parent / "dataset_chamados.csv"

    extrair_dataset(jira, args.campo_atendimento, campo_organizacao, output, args.limite, args.apenas_sicredi)


if __name__ == "__main__":
    main()
