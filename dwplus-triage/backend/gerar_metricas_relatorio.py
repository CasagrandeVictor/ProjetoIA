"""
=============================================================
gerar_metricas_relatorio.py
=============================================================
Roda sobre o dataset_chamados.csv e imprime, prontos para o relatório:
  1) Distribuição das classes de atendimento
  2) Métricas do modelo de atendimento (accuracy, precision, recall, F1)
  3) MATRIZ DE CONFUSÃO do atendimento (Presencial/Remoto)
  4) PALAVRAS MAIS DECISIVAS por classe
  5) Resumo da análise de erros (quantos e quais casos erra)

COMO USAR:
  1. Coloque este arquivo na pasta backend/ (onde está o dataset_chamados.csv)
  2. pip install pandas scikit-learn
  3. python gerar_metricas_relatorio.py
  4. Copie TODA a saída e me mande aqui.

Obs: usa o MultinomialNB (vencedor do atendimento). Reproduz o mesmo
pré-processamento e split do treino original.
=============================================================
"""

import pandas as pd
import numpy as np
import unicodedata, re, sys
from pathlib import Path

# Fix encoding no Windows (terminal cp1252 nao suporta alguns caracteres UTF-8)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

CSV = Path(__file__).parent / "dataset_chamados.csv"
COL_ATEND = "atendimento"     # ajuste se o nome da coluna for outro
COL_TEXTO = "texto_limpo"     # ajuste se necessário
SEED = 42


def normalizar(t):
    if not isinstance(t, str): return ""
    t = unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode("utf-8").lower()
    t = re.sub(r"\S+@\S+", " ", t); t = re.sub(r"http\S+", " ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t); return re.sub(r"\s+", " ", t).strip()


def main():
    if not CSV.exists():
        sys.exit(f"❌ Não encontrei {CSV.name}. Rode o extrair_dataset.py primeiro ou ajuste o caminho.")
    df = pd.read_csv(CSV)

    # Coluna de texto: usa texto_limpo se existir, senão monta de título+descrição
    if COL_TEXTO in df.columns:
        X_raw = df[COL_TEXTO].fillna("")
    else:
        X_raw = (df.get("titulo", "").fillna("") + " " + df.get("descricao", "").fillna("")).apply(normalizar)

    if COL_ATEND not in df.columns:
        sys.exit(f"❌ Não achei a coluna '{COL_ATEND}'. Colunas disponíveis: {list(df.columns)}")

    # Descarta linhas sem rótulo de atendimento e "Não preenchido"
    # (mesmo filtro do treinar_modelo.py — o modelo real nunca viu essa classe)
    y_raw = df[COL_ATEND].astype(str).str.strip()
    mask = df[COL_ATEND].notna() & (y_raw != "") & (y_raw != "Não preenchido")
    X = X_raw[mask]
    y = y_raw[mask]

    nao_preenchidos = (y_raw == "Não preenchido").sum()
    print(f"  (excluidos {nao_preenchidos} registros 'Não preenchido' — igual ao treino original)")

    print("=" * 60)
    print("1) DISTRIBUIÇÃO DAS CLASSES DE ATENDIMENTO")
    print("=" * 60)
    vc = y.value_counts()
    for k, v in vc.items():
        print(f"  {k:15s}: {v}  ({v/len(y)*100:.1f}%)")
    print(f"  TOTAL: {len(y)}")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=5000)),
        ("clf", MultinomialNB()),
    ])
    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_te)

    print("\n" + "=" * 60)
    print("2) MÉTRICAS DO MODELO DE ATENDIMENTO (MultinomialNB)")
    print("=" * 60)
    print(f"Acurácia (teste): {accuracy_score(y_te, pred):.4f}")
    print(classification_report(y_te, pred, zero_division=0, digits=3))

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    cv = cross_val_score(pipe, X, y, cv=skf, scoring="f1_macro")
    print(f"F1-macro (CV 5-fold): média {cv.mean():.3f}  desvio {cv.std():.3f}")
    print(f"  folds: {[f'{s:.3f}' for s in cv]}")

    print("\n" + "=" * 60)
    print("3) MATRIZ DE CONFUSÃO (linhas=real, colunas=previsto)")
    print("=" * 60)
    labels = sorted(y.unique())
    cm = confusion_matrix(y_te, pred, labels=labels)
    print("Ordem das classes:", labels)
    cm_df = pd.DataFrame(cm, index=[f"real:{l}" for l in labels], columns=[f"prev:{l}" for l in labels])
    print(cm_df.to_string())
    total = cm.sum(); erros = total - np.trace(cm)
    print(f"\nTotal no teste: {total}  |  Acertos: {np.trace(cm)}  |  Erros: {erros}  ({erros/total*100:.1f}%)")

    print("\n" + "=" * 60)
    print("4) PALAVRAS MAIS DECISIVAS POR CLASSE")
    print("=" * 60)
    tfidf = pipe.named_steps["tfidf"]; clf = pipe.named_steps["clf"]
    vocab = np.array(tfidf.get_feature_names_out())
    # Para NB: log-prob por classe; pega os termos de maior peso relativo
    for i, classe in enumerate(clf.classes_):
        if clf.feature_log_prob_.shape[0] == 2:
            # diferença entre as duas classes destaca o que é característico
            outro = 1 - i
            score = clf.feature_log_prob_[i] - clf.feature_log_prob_[outro]
        else:
            score = clf.feature_log_prob_[i]
        top = np.argsort(score)[-12:][::-1]
        print(f"\n  [{classe}] termos mais associados:")
        print("   " + ", ".join(vocab[top]))

    print("\n" + "=" * 60)
    print("5) RESUMO PARA O RELATÓRIO")
    print("=" * 60)
    print(f"- Dataset: {len(df)} chamados | com rótulo de atendimento: {len(y)}")
    print(f"- Classes: {dict(vc)}")
    print(f"- Acurácia teste: {accuracy_score(y_te, pred):.1%}")
    print(f"- F1-macro CV: {cv.mean():.1%} (±{cv.std():.1%})")
    print(f"- Erros no teste: {erros}/{total} ({erros/total*100:.1f}%)")
    print("\n✅ Copie TODA esta saída e mande no chat.")


if __name__ == "__main__":
    main()
