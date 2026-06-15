"""
Script standalone de treino do Modelo B (classificador local) do DWPLUS Triage.

Lê `backend/dataset_chamados.csv` (gerado por `extrair_dataset.py`) e treina,
para cada um dos dois alvos abaixo, três classificadores diferentes — comparando
suas métricas para escolher o melhor:

    - organizacao  → qual agência Sicredi abriu o chamado
    - atendimento  → o chamado foi resolvido Presencial ou Remoto

Os modelos vencedores são salvos em `backend/modelo_organizacao.pkl` e
`backend/modelo_atendimento.pkl`, usados depois por `modelo_local.py` (Tarefa 3).

Uso:
    python treinar_modelo.py
"""

import pickle
import sys
import io
from pathlib import Path
from collections import Counter
import csv

import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score

# Força UTF-8 no stdout/stderr para evitar UnicodeEncodeError no Windows (CP1252)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


DATASET_PATH = Path(__file__).parent / "dataset_chamados.csv"
RANDOM_STATE = 42


# ─── Carregamento dos dados ───────────────────────────────────────────────────

def carregar_dataset() -> list[dict]:
    with open(DATASET_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ─── Definição dos modelos a comparar ────────────────────────────────────────

def construir_pipelines() -> dict[str, Pipeline]:
    """
    Cada pipeline encapsula a vetorização TF-IDF + o classificador, garantindo
    que o TF-IDF seja "refeito" em cada fold da validação cruzada (evita
    vazamento de dados do conjunto de teste para o treino).

    O LinearSVC não possui `predict_proba` nativamente — por isso ele é
    encapsulado em `CalibratedClassifierCV`, que calibra as saídas em
    probabilidades. Assim, os três modelos expõem a mesma interface
    (`predict_proba`), o que simplifica a inferência no `modelo_local.py`.
    """
    vetorizador = lambda: TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=5000)

    return {
        "MultinomialNB": Pipeline([
            ("tfidf", vetorizador()),
            ("clf", MultinomialNB()),
        ]),
        "LinearSVC (calibrado)": Pipeline([
            ("tfidf", vetorizador()),
            ("clf", CalibratedClassifierCV(LinearSVC(class_weight="balanced"), cv=3)),
        ]),
        "RandomForest": Pipeline([
            ("tfidf", vetorizador()),
            ("clf", RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
        ]),
    }


# ─── Treino + comparação para um alvo (organizacao OU atendimento) ───────────

def treinar_e_comparar(linhas: list[dict], coluna_label: str, arquivo_saida: Path):
    print("\n" + "█" * 70)
    print(f"  ALVO: {coluna_label}")
    print("█" * 70)

    # Remove linhas sem texto ou sem rótulo válido
    dados = [
        (l["texto_limpo"], l[coluna_label])
        for l in linhas
        if l["texto_limpo"].strip() and l[coluna_label] not in ("", "Não preenchido")
    ]
    X = np.array([d[0] for d in dados])
    y = np.array([d[1] for d in dados])

    print(f"\nTotal de exemplos válidos: {len(y)}")
    print("Distribuição das classes:")
    for classe, qtd in Counter(y).most_common():
        print(f"  {classe:<35} {qtd}")

    # Split treino/teste estratificado — mantém a proporção das classes nos dois conjuntos
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE,
    )
    print(f"\nSplit: {len(X_train)} treino / {len(X_test)} teste")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    melhor_nome = None
    melhor_pipeline = None
    melhor_f1_cv = -1.0

    for nome, pipeline in construir_pipelines().items():
        print("\n" + "─" * 70)
        print(f"Modelo: {nome}")
        print("─" * 70)

        # Treina no conjunto de treino e avalia no conjunto de teste
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        print("\nRelatório de classificação (conjunto de teste):")
        print(classification_report(y_test, y_pred, zero_division=0))

        print("Matriz de confusão (linhas = real, colunas = previsto):")
        labels_ordenadas = sorted(set(y))
        matriz = confusion_matrix(y_test, y_pred, labels=labels_ordenadas)
        largura = max(len(l) for l in labels_ordenadas)
        print(" " * (largura + 2) + " ".join(f"{l[:6]:>6}" for l in labels_ordenadas))
        for label, linha in zip(labels_ordenadas, matriz):
            print(f"{label:<{largura}} " + " ".join(f"{v:>6}" for v in linha))

        # Validação cruzada (5 folds) no dataset completo — mede a estabilidade
        # do modelo em diferentes divisões dos dados, não só uma
        scores_cv = cross_val_score(pipeline, X, y, cv=cv, scoring="f1_macro")
        f1_cv_media, f1_cv_desvio = scores_cv.mean(), scores_cv.std()
        print(f"\nValidação cruzada (5 folds, f1_macro): "
              f"média={f1_cv_media:.4f}  desvio={f1_cv_desvio:.4f}")
        print(f"  scores por fold: {[round(s, 4) for s in scores_cv]}")

        if f1_cv_media > melhor_f1_cv:
            melhor_f1_cv = f1_cv_media
            melhor_nome = nome
            melhor_pipeline = pipeline

    print("\n" + "═" * 70)
    print(f"🏆 Melhor modelo para '{coluna_label}': {melhor_nome} "
          f"(f1_macro médio na validação cruzada = {melhor_f1_cv:.4f})")
    print("═" * 70)

    # Refit do melhor modelo usando TODOS os dados disponíveis (treino + teste),
    # para o modelo salvo aproveitar o máximo de informação possível em produção.
    melhor_pipeline.fit(X, y)
    with open(arquivo_saida, "wb") as f:
        pickle.dump(melhor_pipeline, f)
    print(f"💾 Modelo salvo em: {arquivo_saida}")


# ─── Ponto de entrada ─────────────────────────────────────────────────────────

def main():
    if not DATASET_PATH.exists():
        print(f"❌ Dataset não encontrado em {DATASET_PATH}. "
              f"Rode primeiro: python extrair_dataset.py --campo-atendimento labels --apenas-sicredi")
        sys.exit(1)

    linhas = carregar_dataset()
    print(f"📂 Dataset carregado: {len(linhas)} chamados")

    treinar_e_comparar(linhas, "organizacao", Path(__file__).parent / "modelo_organizacao.pkl")
    treinar_e_comparar(linhas, "atendimento", Path(__file__).parent / "modelo_atendimento.pkl")


if __name__ == "__main__":
    main()
