"""
Módulo de análise de chamados via Gemini Flash (google-genai SDK).
Privacidade: envia ao LLM apenas o DOMÍNIO do e-mail (nunca o e-mail completo
nem o token do Jira). O sistema nunca quebra — qualquer falha ativa o fallback.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# Cliente singleton inicializado de forma lazy
_gemini_client = None


def _get_client():
    """Retorna (ou cria) o cliente Gemini. Lazy init para não falhar no import."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai  # importação lazy — só carrega se a chave existir

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não está configurada nas variáveis de ambiente")
        _gemini_client = genai.Client(api_key=api_key)
        logger.info("Cliente Gemini Flash inicializado com sucesso.")
    return _gemini_client


def analisar_chamado(chamado: dict, organizacoes_validas: list) -> dict:
    """
    Analisa um chamado via Gemini 2.0 Flash e retorna triagem estruturada.

    Parâmetros:
        chamado: dicionário com os dados do chamado (ChamadoJira.dict()).
        organizacoes_validas: lista de nomes de organizações cadastradas no Jira.

    Retorno: dict com keys:
        organizacao_sugerida, confianca, categoria, prioridade,
        orientacoes, justificativa.

    Nunca lança exceção — qualquer erro ativa o fallback seguro.
    """
    try:
        from google import genai  # noqa: F401 (confirma que o SDK está instalado)
        from google.genai import types

        client = _get_client()

        # ── Privacidade: extrai só o domínio, descarta o e-mail completo ──────
        email = chamado.get("email", "")
        dominio = email.split("@")[1] if "@" in email else "desconhecido"

        # Monta lista legível de organizações para guiar o modelo
        if organizacoes_validas:
            orgs_linhas = "\n".join(f"  - {org}" for org in sorted(organizacoes_validas))
        else:
            orgs_linhas = "  (nenhuma organização cadastrada no sistema)"

        prompt = f"""Você é um especialista em triagem de chamados de suporte técnico empresarial.

Analise o chamado abaixo e produza uma triagem completa em JSON.

=== DADOS DO CHAMADO ===
Título: {chamado.get('titulo', '')}
Descrição: {chamado.get('descricao', '')[:1200]}
Domínio do solicitante: {dominio}
Status atual: {chamado.get('status', '')}
Prioridade registrada: {chamado.get('prioridade', '')}
Organização já preenchida: {chamado.get('organizacao_atual', 'Não preenchido')}

=== ORGANIZAÇÕES DISPONÍVEIS NO SISTEMA ===
{orgs_linhas}

=== INSTRUÇÕES ===
1. Escolha a organização que melhor representa o solicitante (prefira as da lista acima; infira pelo domínio se necessário).
2. Classifique a categoria técnica do problema.
3. Avalie a prioridade real com base no impacto descrito (pode diferir da registrada).
4. Forneça orientações práticas e detalhadas para o técnico de N1/N2 resolver o chamado.
5. Justifique brevemente a análise.

Responda APENAS com o JSON abaixo, sem markdown, sem texto extra:
{{
  "organizacao_sugerida": "nome da organização",
  "confianca": 0.85,
  "categoria": "Acesso/Autenticação",
  "prioridade": "Média",
  "orientacoes": "passo a passo detalhado para o técnico",
  "justificativa": "motivo da escolha de organização e categoria"
}}

Valores válidos para categoria: Acesso/Autenticação | Infraestrutura | Software/Sistema | Hardware | Rede | Relatórios/Dados | Outro
Valores válidos para prioridade: Baixa | Média | Alta | Crítica"""

        # ── Chama o Gemini Flash com saída JSON estruturada ───────────────────
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )

        resultado = json.loads(response.text)

        # Valida presença de todos os campos obrigatórios
        campos_obrigatorios = [
            "organizacao_sugerida", "confianca", "categoria",
            "prioridade", "orientacoes", "justificativa"
        ]
        ausentes = [c for c in campos_obrigatorios if c not in resultado]
        if ausentes:
            raise ValueError(f"Campos ausentes na resposta do Gemini: {ausentes}")

        # Normaliza confiança para o intervalo [0.0, 1.0]
        resultado["confianca"] = max(0.0, min(1.0, float(resultado["confianca"])))

        logger.info(
            "Gemini: org='%s' confianca=%.2f categoria='%s' prioridade='%s'",
            resultado["organizacao_sugerida"],
            resultado["confianca"],
            resultado["categoria"],
            resultado["prioridade"],
        )
        return resultado

    except Exception as exc:
        # ── Fallback seguro: o sistema nunca quebra ───────────────────────────
        logger.error("Falha na análise via Gemini (ativando fallback): %s", exc)
        return {
            "organizacao_sugerida": "Revisão Manual Necessária",
            "confianca": 0.0,
            "categoria": "Outro",
            "prioridade": "Média",
            "orientacoes": (
                "A análise automática via IA encontrou um problema. "
                "Por favor, revise este chamado manualmente e atribua a organização correta."
            ),
            "justificativa": f"Fallback ativado — erro na API Gemini: {str(exc)[:300]}",
        }
