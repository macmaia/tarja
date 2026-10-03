#!/usr/bin/env bash
# tools/facts.sh
# EN: one-line answers to the questions that get guessed. Every one of them was, in this project, answered
#   from memory or from the working tree instead of from the thing being talked about, and the guess was
#   wrong eight times in one session. This file does not prevent that. It removes the excuse, by making the
#   command shorter than the sentence it replaces.
#
#   The distinction it exists to enforce: the working tree is not the index, the index is not HEAD, HEAD is
#   not origin, and none of them is what a user installed from PyPI. A claim about what is PUBLISHED has to
#   come from the published thing.
#   PT: respostas de uma linha p/ as perguntas q costumam ser adivinhadas. Isto nao previne o chute, so faz o
#   comando ficar mais curto q a frase q ele substitui. Arvore de trabalho nao e indice, indice nao e HEAD,
#   HEAD nao e origin, e nenhum deles e o q o usuario instalou.
#
# usage: bash tools/facts.sh <target>
# [FACTS] file anchor.
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-help}" in

  published)   # EN: what is on the default branch at the remote, not on disk
    git fetch -q origin main 2>/dev/null || true
    echo "origin/main = $(git rev-parse --short origin/main)  $(git log -1 --format=%s origin/main)" ;;

  dirty)       # EN: what differs between disk, index and HEAD. An empty answer is the only safe one before
               #   saying anything about what the project currently does.
    git status --porcelain || true ;;

  ahead)       # EN: commits here that the remote does not have. A fix that is not here is not deployed.
    git log --oneline origin/main..HEAD 2>/dev/null || echo "(no origin/main)" ;;

  file)        # EN: a file as PUBLISHED, not as edited. bash tools/facts.sh file README.md
    git show "origin/main:${2:?need a path}" ;;

  tests)       # EN: how many tests exist on disk, and how many test files git is tracking. The two can
               #   disagree, and the day they did, a rename staged with `git add -u` would have deleted 74
               #   tests while the suite stayed green.
    echo "collected: $(PYTHONPATH=src:. python -m unittest discover -s tests 2>&1 | grep -oE 'Ran [0-9]+' | grep -oE '[0-9]+')"
    echo "tracked test files: $(git ls-files 'tests/test_*.py' | wc -l | tr -d ' ')"
    echo "test files on disk:  $(ls tests/test_*.py | wc -l | tr -d ' ')" ;;

  version)     # EN: the version in the source, the newest tag, and what PyPI actually serves
    echo "source: $(PYTHONPATH=src python -c 'import tarja; print(tarja.__version__)')"
    echo "tag:    $(git tag --sort=-v:refname | grep -E '^v' | head -1)"
    echo "pypi:   $(pip index versions tarja 2>/dev/null | head -1 || echo '(offline)')" ;;

  ci)          # EN: the last run of each workflow. A fix recorded without the run id that proves it is a
               #   hypothesis, not a fix.
    gh run list --limit 6 --json workflowName,status,conclusion,headSha,databaseId \
      --jq '.[] | "\(.workflowName) \(.status) \(.conclusion // "-") \(.headSha[0:7]) run=\(.databaseId)"' ;;

  *)
    echo "targets: published dirty ahead file <path> tests version ci"
    echo "  every one answers from the thing itself, not from the working tree." ;;
esac
