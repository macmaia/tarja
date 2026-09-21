# tarja/cli.py
# [CLI] command line. Examples:
#   tarja scan contrato.txt                     -> JSON lines, one per finding (value hidden by default)
#   tarja scan contrato.txt --format table      -> readable table
#   tarja scan contrato.txt --show-values       -> include the raw identifier (careful)
#   tarja mask contrato.txt > limpo.txt         -> masked copy, strategy redact
#   tarja mask - --strategy pseudonym_stable --salt "$TARJA_SALT" < in.txt
#   cat log.txt | tarja scan - --entities BR_CPF,BR_CNPJ --min-score 0.9

from __future__ import annotations

import argparse
import json
import os
import sys

from tarja import __version__
from tarja.detect import find
from tarja.entities import ENTITIES
from tarja.mask import STRATEGIES, STRATEGY_ALIASES, mask

# [CLI-LIMIT] input cap, so a huge file or endless pipe can't exhaust memory (override with --max-mb)
DEFAULT_MAX_MB = 50


def _read(path: str, max_mb: float = DEFAULT_MAX_MB) -> str:
    # [CLI-READ] "-" reads stdin, both capped at max_mb (read one char over the cap to detect it)
    limit = int(max_mb * 1024 * 1024)
    if path == "-":
        text = sys.stdin.read(limit + 1)
    else:
        with open(path, encoding="utf-8") as fh:
            text = fh.read(limit + 1)
    if len(text) > limit:
        raise ValueError(f"input larger than {max_mb:g} MB, use --max-mb or split the file")
    return text


def _entities(arg: str | None) -> list[str] | None:
    # [CLI-ENTITIES] "BR_CPF,BR_CNPJ" -> list, None = all
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

    # shared options
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("path", help="file or - for stdin / arquivo ou - p/ stdin")
    common.add_argument(
        "--entities",
        help=f"comma-separated / separadas por virgula. Default: all / todas ({','.join(ENTITIES)})",
    )
    common.add_argument("--min-score", type=float, default=0.0, help="drop below this / descarta abaixo disso")
    common.add_argument(
        "--max-mb",
        type=float,
        default=DEFAULT_MAX_MB,
        help=f"input size cap in MB, default {DEFAULT_MAX_MB} / limite de entrada em MB",
    )

    # [CLI-SCAN]
    scan = sub.add_parser("scan", parents=[common], help="list findings / lista o q achou")
    scan.add_argument("--format", choices=("jsonl", "table"), default="jsonl")
    scan.add_argument(
        "--show-values",
        action="store_true",
        help="print raw identifiers (personal data!) / mostra o valor cru (dado pessoal!)",
    )

    scan.add_argument(
        "--suspect",
        action="store_true",
        help="also report ID-shaped values with a wrong check digit (score 0) / reporta tb formato de ID c/ DV errado",
    )

    # [CLI-MASK]
    mk = sub.add_parser("mask", parents=[common], help="print masked text / imprime o texto mascarado")
    mk.add_argument("--strategy", choices=(*STRATEGIES, *STRATEGY_ALIASES), default="redact")
    mk.add_argument(
        "--salt",
        default=os.environ.get("TARJA_SALT"),
        help="secret key for pseudonym_stable, or set TARJA_SALT / chave secreta, ou use TARJA_SALT",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """EN: Entry point (console script "tarja"). Returns an exit code.
    PT: Ponto de entrada (script "tarja"). Devolve o exit code.
    """
    args = _build_parser().parse_args(argv)
    try:
        text = _read(args.path, args.max_mb)
        # [CLI-SUSPECT] only scan reports suspects, mask never touches them
        suspect = args.command == "scan" and args.suspect
        found = find(text, entities=_entities(args.entities), min_score=args.min_score, report_invalid=suspect)
        if args.command == "mask":
            # [CLI-MASK-RUN]
            sys.stdout.write(mask(text, strategy=args.strategy, salt=args.salt, matches=found))
            return 0
        # [CLI-SCAN-RUN]
        if args.format == "jsonl":
            for m in found:
                sys.stdout.write(json.dumps(m.to_dict(include_value=args.show_values), ensure_ascii=False) + "\n")
        else:
            # simple fixed-width table
            sys.stdout.write(f"{'entity':<10} {'start':>7} {'end':>7} {'score':>5}  value\n")
            for m in found:
                shown = m.value if args.show_values else "*" * len(m.value)
                sys.stdout.write(f"{m.entity:<10} {m.start:>7} {m.end:>7} {m.score:>5.2f}  {shown}\n")
        # exit 1 when something was found, handy in CI
        return 1 if found else 0
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        # [CLI-ERROR] clean message instead of a traceback
        sys.stderr.write(f"tarja: {exc}\n")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
