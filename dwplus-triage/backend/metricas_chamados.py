"""
Módulo de métricas de volume de chamados.
Puxa chamados do Jira com timestamp COMPLETO (não só a data) para permitir
análise por hora do dia. Gera CSV e PNG opcionalmente.
"""

import os
import csv
import logging
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Nomes legíveis para dias da semana (0=segunda, 6=domingo)
_DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _parse_timestamp_jira(ts: str) -> Optional[datetime]:
    """
    Converte o timestamp do Jira (ISO 8601 com offset) para datetime aware.
    Preserva o timestamp COMPLETO, incluindo hora, para análises horárias.
    """
    if not ts:
        return None
    try:
        # Formato típico do Jira: "2024-03-15T14:32:00.000+0000"
        # ou "2024-03-15T14:32:00.000-0300"
        ts_limpo = ts.strip()
        # Python aceita "+00:00" mas não "+0000"; normaliza o offset
        if len(ts_limpo) > 5 and ts_limpo[-5] in ("+", "-") and ":" not in ts_limpo[-5:]:
            ts_limpo = ts_limpo[:-2] + ":" + ts_limpo[-2:]
        return datetime.fromisoformat(ts_limpo)
    except Exception:
        try:
            # Fallback sem timezone
            return datetime.fromisoformat(ts[:19])
        except Exception:
            return None


def calcular_metricas(chamados_raw: list) -> dict:
    """
    Recebe lista de dicionários de chamados (ChamadoJira.model_dump()) e calcula
    todas as métricas de volume. Os chamados devem ter o campo 'criado_em' com
    o timestamp COMPLETO (não truncado em [:10]).

    Retorna dict com:
        - resumo: total, por_dia_media, por_semana_media, por_mes_media
        - por_hora: {0..23: contagem}
        - por_dia_semana: {nome_dia: contagem}
        - por_mes: {"YYYY-MM": contagem}
        - hora_pico: hora com mais chamados
        - dia_semana_pico: dia da semana com mais chamados
    """
    if not chamados_raw:
        return _metricas_vazias()

    timestamps = []
    for c in chamados_raw:
        ts_str = c.get("criado_em", "")
        dt = _parse_timestamp_jira(ts_str)
        if dt:
            # Normaliza para UTC para evitar distorções de fuso
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            timestamps.append(dt)

    if not timestamps:
        return _metricas_vazias()

    # ── Contagens por agrupamento ─────────────────────────────────────────────
    por_hora: dict[int, int] = defaultdict(int)
    por_dia_semana: dict[int, int] = defaultdict(int)
    por_dia: dict[str, int] = defaultdict(int)     # "YYYY-MM-DD"
    por_semana: dict[str, int] = defaultdict(int)  # "YYYY-Www"
    por_mes: dict[str, int] = defaultdict(int)     # "YYYY-MM"

    for dt in timestamps:
        por_hora[dt.hour] += 1
        por_dia_semana[dt.weekday()] += 1
        por_dia[dt.strftime("%Y-%m-%d")] += 1
        por_semana[dt.strftime("%Y-W%V")] += 1
        por_mes[dt.strftime("%Y-%m")] += 1

    total = len(timestamps)
    n_dias = len(por_dia) or 1
    n_semanas = len(por_semana) or 1
    n_meses = len(por_mes) or 1

    # ── Hora e dia de pico ────────────────────────────────────────────────────
    hora_pico = max(por_hora, key=por_hora.get) if por_hora else None
    dia_idx_pico = max(por_dia_semana, key=por_dia_semana.get) if por_dia_semana else None

    return {
        "resumo": {
            "total": total,
            "media_por_dia": round(total / n_dias, 2),
            "media_por_semana": round(total / n_semanas, 2),
            "media_por_mes": round(total / n_meses, 2),
        },
        "por_hora": {str(h): por_hora.get(h, 0) for h in range(24)},
        "por_dia_semana": {
            _DIAS_SEMANA[i]: por_dia_semana.get(i, 0) for i in range(7)
        },
        "por_mes": dict(sorted(por_mes.items())),
        "hora_pico": hora_pico,
        "dia_semana_pico": _DIAS_SEMANA[dia_idx_pico] if dia_idx_pico is not None else None,
    }


def _metricas_vazias() -> dict:
    return {
        "resumo": {"total": 0, "media_por_dia": 0, "media_por_semana": 0, "media_por_mes": 0},
        "por_hora": {str(h): 0 for h in range(24)},
        "por_dia_semana": {d: 0 for d in _DIAS_SEMANA},
        "por_mes": {},
        "hora_pico": None,
        "dia_semana_pico": None,
    }


def exportar_csv(chamados_raw: list, caminho: Optional[Path] = None) -> Path:
    """Exporta os chamados com timestamp completo para CSV."""
    caminho = caminho or (Path(__file__).parent / "metricas_chamados.csv")
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "chave", "criado_em", "hora", "dia_semana", "mes", "organizacao_atual", "status"
        ])
        writer.writeheader()
        for c in chamados_raw:
            ts_str = c.get("criado_em", "")
            dt = _parse_timestamp_jira(ts_str)
            if dt and dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            writer.writerow({
                "chave": c.get("chave", ""),
                "criado_em": dt.isoformat() if dt else ts_str,
                "hora": dt.hour if dt else "",
                "dia_semana": _DIAS_SEMANA[dt.weekday()] if dt else "",
                "mes": dt.strftime("%Y-%m") if dt else "",
                "organizacao_atual": c.get("organizacao_atual", ""),
                "status": c.get("status", ""),
            })
    logger.info("CSV de métricas exportado: %s", caminho)
    return caminho


def exportar_grafico_png(metricas: dict, caminho: Optional[Path] = None) -> Optional[Path]:
    """
    Gera gráfico PNG com 3 subplots: chamados por hora, por dia da semana e por mês.
    Retorna None silenciosamente se matplotlib não estiver instalado.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # backend sem display (servidor headless)
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib não instalado — gráfico PNG não será gerado.")
        return None

    caminho = caminho or (Path(__file__).parent / "metricas_chamados.png")

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Métricas de Chamados — DWPLUS Triage", fontsize=14, fontweight="bold")

    # Subplot 1: por hora
    horas = list(range(24))
    valores_hora = [metricas["por_hora"].get(str(h), 0) for h in horas]
    hora_pico = metricas.get("hora_pico")
    cores_hora = ["#0A84FF" if h != hora_pico else "#FF9F0A" for h in horas]
    axes[0].bar(horas, valores_hora, color=cores_hora)
    axes[0].set_title("Por Hora do Dia")
    axes[0].set_xlabel("Hora")
    axes[0].set_ylabel("Chamados")
    axes[0].set_xticks(range(0, 24, 2))
    if hora_pico is not None:
        axes[0].axvline(hora_pico, color="#FF9F0A", linestyle="--", alpha=0.6)

    # Subplot 2: por dia da semana
    dias = _DIAS_SEMANA
    valores_dia = [metricas["por_dia_semana"].get(d, 0) for d in dias]
    dia_pico = metricas.get("dia_semana_pico")
    cores_dia = ["#5E5CE6" if d != dia_pico else "#FF9F0A" for d in dias]
    axes[1].bar(dias, valores_dia, color=cores_dia)
    axes[1].set_title("Por Dia da Semana")
    axes[1].set_xlabel("Dia")
    axes[1].set_ylabel("Chamados")
    axes[1].tick_params(axis="x", rotation=30)

    # Subplot 3: por mês
    meses = list(metricas["por_mes"].keys())
    valores_mes = list(metricas["por_mes"].values())
    if meses:
        axes[2].bar(meses, valores_mes, color="#30D158")
        axes[2].set_title("Por Mês")
        axes[2].set_xlabel("Mês")
        axes[2].set_ylabel("Chamados")
        axes[2].tick_params(axis="x", rotation=30)
    else:
        axes[2].text(0.5, 0.5, "Sem dados", ha="center", va="center")
        axes[2].set_title("Por Mês")

    plt.tight_layout()
    plt.savefig(caminho, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info("Gráfico PNG exportado: %s", caminho)
    return caminho
