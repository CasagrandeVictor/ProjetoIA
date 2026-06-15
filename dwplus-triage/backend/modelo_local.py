"""
Módulo de inferência do Modelo B (classificador local treinado) do DWPLUS Triage.

Carrega o modelo treinado em `treinar_modelo.py` (backend/modelo_atendimento.pkl)
e expõe uma função simples para prever se o atendimento de um chamado foi
"Presencial" ou "Remoto" a partir do texto (título + descrição).

Importante: este módulo NUNCA levanta exceção para quem o importa.
- `modelo_disponivel()` retorna False se o .pkl não existir ou não puder ser carregado.
- `classificar(texto)` retorna None se o modelo não estiver disponível ou se
  qualquer erro ocorrer durante a predição.

Assim, `main.py` pode usar o Modelo B quando disponível e, caso contrário,
continuar com o comportamento atual (Gemini + regras + histórico do usuário)
sem nenhuma quebra.

Nota: a sugestão de "organizacao" continua vindo do Gemini/histórico do
usuário (modelo_organizacao.pkl foi treinado e está salvo, mas não é usado
aqui — o desempenho ficou abaixo do esperado para uso em produção; fica
disponível como material de comparação/discussão acadêmica).
"""

import pickle
import re
import unicodedata
from pathlib import Path
from typing import Optional

MODELO_ATENDIMENTO_PATH = Path(__file__).parent / "modelo_atendimento.pkl"

# Cache singleton — o modelo é carregado do disco apenas na primeira chamada
_modelo_atendimento = None
_modelo_carregado = False


def _limpar_texto(texto: str) -> str:
    """
    Normalização de texto idêntica à usada em `extrair_dataset.py` no treino.
    Precisa ser a mesma para que o TF-IDF do modelo reconheça o vocabulário
    corretamente (minúsculas, sem e-mails/URLs, sem acentos, sem pontuação).
    """
    texto = (texto or "").lower()
    texto = re.sub(r"\S+@\S+", " ", texto)
    texto = re.sub(r"https?://\S+|www\.\S+", " ", texto)

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _carregar_modelo() -> None:
    """Carrega o .pkl do disco uma única vez (lazy loading + cache)."""
    global _modelo_atendimento, _modelo_carregado
    if _modelo_carregado:
        return
    _modelo_carregado = True

    if not MODELO_ATENDIMENTO_PATH.exists():
        return

    try:
        with open(MODELO_ATENDIMENTO_PATH, "rb") as f:
            _modelo_atendimento = pickle.load(f)
    except Exception:
        # Qualquer problema ao carregar (arquivo corrompido, versão incompatível
        # do scikit-learn etc.) → Modelo B fica indisponível, sem quebrar o sistema
        _modelo_atendimento = None


def modelo_disponivel() -> bool:
    """Indica se o Modelo B (atendimento) está treinado e pronto para uso."""
    _carregar_modelo()
    return _modelo_atendimento is not None


def classificar(texto: str) -> Optional[dict]:
    """
    Prevê o tipo de atendimento ("Presencial" ou "Remoto") a partir do texto
    do chamado (geralmente título + descrição).

    Retorna:
        {"atendimento": "Presencial" | "Remoto", "confianca_atend": float}
        ou None se o Modelo B não estiver disponível ou ocorrer algum erro.
    """
    _carregar_modelo()
    if _modelo_atendimento is None:
        return None

    try:
        texto_limpo = _limpar_texto(texto)
        if not texto_limpo:
            return None

        predicao = _modelo_atendimento.predict([texto_limpo])[0]
        probabilidades = _modelo_atendimento.predict_proba([texto_limpo])[0]
        confianca = float(max(probabilidades))

        return {"atendimento": str(predicao), "confianca_atend": confianca}
    except Exception:
        # Nunca propaga erro — quem chamou trata como "Modelo B indisponível"
        return None
