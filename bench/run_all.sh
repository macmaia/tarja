#!/usr/bin/env bash
# bench/run_all.sh
# [BENCH-RUN-ALL] EN: E4.5-E4.7 for real. Runs every system that has its dependency/credential available,
#   SKIPS (with a message) the ones that don't, then scores everything. Results go to bench/results/.
# [BENCH-RUN-ALL] PT: E4.5-E4.7 de verdade. Roda todo sistema q tem dependencia/credencial disponivel,
#   PULA (c/ aviso) os q nao tem, dps pontua tudo. Resultado vai p/ bench/results/.
#
# EN: usage / PT: uso:  bash bench/run_all.sh [split]   (default: test)
set -u
SPLIT="${1:-test}"
DATA=bench/data/v0.1
OUT=bench/results
mkdir -p "$OUT"

# EN: make sure the data exists / PT: garante q os dados existem
[ -f "$DATA/synthetic_controlled.$SPLIT.jsonl" ] || python -m bench.generate --out "$DATA" >/dev/null

run() {  # $1 = system, rest = extra args / $1 = sistema, resto = args extras
  local sys="$1"; shift
  for f in "$DATA"/*."$SPLIT".jsonl; do
    echo ">> $sys on $(basename "$f")"
    python -m bench.run --system "$sys" --data "$f" --out "$OUT" "$@" || { echo "   FAILED / FALHOU: $sys"; return; }
  done
}
have() { python -c "import $1" 2>/dev/null; }

run tarja
have presidio_analyzer && run presidio-default || echo "-- skip presidio-default (pip install presidio-analyzer + python -m spacy download en_core_web_lg)"
have presidio_br && run presidio-br || echo "-- skip presidio-br (pip install -e packages/presidio-br)"
have spacy && python -c "import spacy; spacy.load('pt_core_news_lg')" 2>/dev/null && run spacy || echo "-- skip spacy (python -m spacy download pt_core_news_lg)"
[ -n "${AZURE_LANGUAGE_KEY:-}" ] && run azure || echo "-- skip azure (AZURE_LANGUAGE_ENDPOINT + AZURE_LANGUAGE_KEY)"
[ -n "${GOOGLE_CLOUD_PROJECT:-}" ] && run google-sdp || echo "-- skip google-sdp (GOOGLE_CLOUD_PROJECT + gcloud auth application-default login)"
for m in ${ANTHROPIC_MODELS:-}; do run llm --provider anthropic --model "$m"; done
[ -z "${ANTHROPIC_MODELS:-}" ] && echo "-- skip anthropic (export ANTHROPIC_API_KEY=... ANTHROPIC_MODELS=\"model-a model-b\")"
for m in ${OPENAI_MODELS:-}; do run llm --provider openai --model "$m"; done
[ -z "${OPENAI_MODELS:-}" ] && echo "-- skip openai (export OPENAI_API_KEY=... OPENAI_MODELS=\"model-a\")"

# [BENCH-RUN-ALL-SCORE] EN: score every prediction file / PT: pontua todo arquivo de previsao
for p in "$OUT"/*__*."$SPLIT".json; do
  gold="$DATA/$(basename "$p" | sed 's/.*__//; s/\.json$/.jsonl/')"
  python -m bench.evaluate --gold "$gold" --pred "$p" | tee -a "$OUT/SUMMARY_$SPLIT.txt"
done
echo "done / pronto: $OUT/SUMMARY_$SPLIT.txt"
