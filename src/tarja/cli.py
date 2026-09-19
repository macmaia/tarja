# tarja/cli.py
# [CLI] EN: command line. Examples:
#   tarja scan contrato.txt                     -> JSON lines, one per finding (value hidden by default)
#   tarja scan contrato.txt --format table      -> readable table
#   tarja scan contrato.txt --show-values       -> include the raw identifier (careful)
#   tarja mask contrato.txt > limpo.txt         -> masked copy, strategy redact
#   tarja mask - --strategy hash --salt s3cr3t < in.txt
#   cat log.txt | tarja scan - --entities BR_CPF,BR_CNPJ --min-score 0.9
# [CLI] PT: linha de comando. Exemplos acima. Por padrao o valor achado NAO sai no output (dado pessoal).
#   --show-values mostra o valor cru, usar c/ cuidado.

from __future__ import annotations

import argparse
import json
import os
import sys

from tarja import __version__
from tarja.detect import find
from tarja.entities import ENTITIES
from tarja.mask import STRATEGIES, mask


def _read(path: str) -> str:
    # [CLI-READ] EN: "-" reads stdin / PT: "-" le do stdin
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _entities(arg: str | None) -> list[str] | None:
    # [CLI-ENTITIES] EN: "BR_CPF,BR_CNPJ" -> list, None = all / PT: "BR_CPF,BR_CNPJ" -> lista, None = todas
    if not arg:
        return None
    return [e.strip().upper() for e in arg.split(",") if e.strip()]


def _build_parser() -> argparse.ArgumentParser:
    # [CLI-PARSER]
    p = argparse.ArgumentParser(
        prog="tarja",
        description="Find and mask Brazilian personal identifiers. / Acha e mascara identificadores brasileiros.",
    )
    p.add_argument("--version", action="version", version=f"tarja {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # EN: shared options / PT: opcoes comuns
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("path", help="file or - for stdin / arquivo ou - p/ stdin")
    common.add_argument(
        "--entities",
        help=f"comma-separated / separadas por virgula. Default: all / todas ({','.join(ENTITIES)})",
    )
    common.add_argument("--min-score", type=float, default=0.0, help="drop below this / descarta abaixo disso")

    # [CLI-SCAN]
    scan = sub.add_parser("scan", parents=[common], help="list findings / lista o q achou")
    scan.add_argument("--format", choices=("jsonl", "table"), default="jsonl")
    scan.add_argument(
        "--show-values",
        action="store_true",
        help="print raw identifiers (personal data!) / mostra o valor cru (dado pessoal!)",
    )

    # [CLI-MASK]
    mk = sub.add_parser("mask", parents=[common], help="print masked text / imprime o texto mascarado")
    mk.add_argument("--strategy", choices=STRATEGIES, default="redact")
    mk.add_argument(
        "--salt",
        default=os.environ.get("TARJA_SALT"),
        help="needed for hash, or set TARJA_SALT / necessario p/ hash, ou use TARJA_SALT",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """EN: Entry point (console script "tarja"). Returns an exit code.
    PT: Ponto de entrada (script "tarja"). Devolve o exit code.
    """
    args = _build_parser().parse_args(argv)
    try:
        text = _read(args.path)
        found = find(text, entities=_entities(args.entities), min_score=args.min_score)
        if args.command == "mask":
            # [CLI-MASK-RUN]
            sys.stdout.write(mask(text, strategy=args.strategy, salt=args.salt, matches=found))
            return 0
        # [CLI-SCAN-RUN]
        if args.format == "jsonl":
            for m in found:
                sys.stdout.write(json.dumps(m.to_dict(include_value=args.show_values), ensure_ascii=False) + "\n")
        else:
            # EN: simple fixed-width table / PT: tabela simples de largura fixa
            sys.stdout.write(f"{'entity':<10} {'start':>7} {'end':>7} {'score':>5}  value\n")
            for m in found:
                shown = m.value if args.show_values else "*" * len(m.value)
                sys.stdout.write(f"{m.entity:<10} {m.start:>7} {m.end:>7} {m.score:>5.2f}  {shown}\n")
        # EN: exit 1 when something was found, handy in CI / PT: exit 1 qdo acha algo, util em CI
        return 1 if found else 0
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        # [CLI-ERROR] EN: clean message instead of a traceback / PT: msg limpa em vez de traceback
        sys.stderr.write(f"tarja: {exc}\n")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
