# tarja/cli.py
# [CLI] command line. Examples:
#   tarja scan contrato.txt                     -> JSON lines, one per finding (value hidden by default)
#   tarja scan contrato.txt --format table      -> readable table
#   tarja scan contrato.txt --show-values       -> include the raw identifier (careful)
#   tarja mask contrato.txt > limpo.txt         -> masked copy, strategy redact
#   tarja mask - --strategy pseudonym_stable --salt "$TARJA_SALT" < in.txt
#   cat log.txt | tarja scan - --entities BR_CPF,BR_CNPJ   -> exit 1 if anything at all was found (the gate)
#   tarja scan contrato.txt --report-min-score 0.9          -> filters the REPORT, never the exit code

from __future__ import annotations

import argparse
import json
import os
import sys

from tarja import __version__
from tarja.detect import find
from tarja.entities import ENTITIES
from tarja.mask import STRATEGIES, mask

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


# [CLI-SCORE] EN: argparse type for every score flag. A bare type=float accepts "nan", and NaN makes every
#   comparison False, so --min-score nan silently dropped every finding and returned exit 0. A check a typo
#   can disable is not a check. Range is refused for the same reason: a score is always in [0, 1], so "5" is
#   a mistake, not a strict setting, and "-1" is not a loose one.
#   PT: argparse type p/ todo flag de score. type=float aceitava "nan", e NaN desligava o portao em silencio.
def _score(raw: str) -> float:
    bad = f"must be a number between 0.0 and 1.0, got {raw!r} / precisa ser numero entre 0.0 e 1.0, recebido {raw!r}"
    try:
        value = float(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(bad) from None
    # NaN fails its own equality, and the range test rejects inf and -inf
    if value != value or not (0.0 <= value <= 1.0):
        raise argparse.ArgumentTypeError(bad)
    return value


# [CLI-MB] EN: same reasoning as _score. A bare type=float accepts "inf", and int(inf * 1024 * 1024) raises
#   OverflowError, which is not in main's except clause, so the user got a traceback and exit 1, which is
#   indistinguishable from "personal data found". A negative value produced "input larger than -1 MB".
#   PT: mesma razao do _score. type=float aceitava "inf" e o int() estourava OverflowError fora do except.
def _max_mb(raw: str) -> float:
    bad = f"must be a positive number of megabytes, got {raw!r} / precisa ser numero positivo de megabytes, recebido {raw!r}"
    try:
        value = float(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(bad) from None
    # NaN fails its own equality, and the upper bound rejects inf
    if value != value or not (0.0 < value <= 1024.0):
        raise argparse.ArgumentTypeError(bad)
    return value


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
    # [CLI-THRESHOLD-SCAN-ONLY] EN: these live on scan, not on the shared options. On mask they were always
    #   refused with exit 2, and a flag that --help advertises and the command always rejects is one step
    #   before the defect this release removes. PT: ficam no scan. No mask eram sempre recusados, e flag que
    #   o --help anuncia e o comando sempre recusa e a mesma forma do defeito, um passo antes.
    threshold = argparse.ArgumentParser(add_help=False)
    threshold.add_argument(
        "--report-min-score",
        type=_score,
        default=None,
        help="hide findings below this FROM THE REPORT. It never changes the exit code "
        "/ esconde do RELATORIO o q esta abaixo disso. Nunca muda o exit code",
    )
    # [CLI-MIN-SCORE-DEPRECATED] EN: the old name read as "the minimum score I care about", which is why
    #   raising it was expected to be conservative and did the opposite: it dropped the finding from the
    #   report AND flipped exit 1 to exit 0, so `tarja scan f.txt && send.sh` sent the file. Renamed, not
    #   just re-documented, because the name was the defect. Removal target 1.0.0.
    #   PT: o nome antigo se lia como "score minimo q me interessa", e por isso subir parecia conservador e
    #   era o contrario. Renomeado pq o nome era o defeito. Remocao prevista p/ a 1.0.0.
    threshold.add_argument(
        "--min-score",
        type=_score,
        default=None,
        help="deprecated alias for --report-min-score / nome antigo de --report-min-score",
    )
    common.add_argument(
        "--suspect",
        action="store_true",
        help="scan: also report ID-shaped values with a wrong check digit (score 0). mask: also mask them "
        "/ scan: reporta tb formato de ID c/ DV errado. mask: mascara eles tb",
    )
    common.add_argument(
        "--max-mb",
        type=_max_mb,
        default=DEFAULT_MAX_MB,
        help=f"input size cap in MB, default {DEFAULT_MAX_MB} / limite de entrada em MB",
    )

    # [CLI-SCAN]
    scan = sub.add_parser("scan", parents=[common, threshold], help="list findings / lista o q achou")
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
        help="secret key for pseudonym_stable, or set TARJA_SALT / chave secreta, ou use TARJA_SALT",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """EN: Entry point (console script "tarja"). Returns an exit code.
    PT: Ponto de entrada (script "tarja"). Devolve o exit code.
    """
    args = _build_parser().parse_args(argv)
    # [CLI-MIN-SCORE-ALIAS] EN: stderr, not DeprecationWarning, which Python hides by default, so on a
    #   command line it is a warning nobody receives. PT: stderr, pq DeprecationWarning nao aparece na CLI.
    if getattr(args, "min_score", None) is not None:
        if getattr(args, "report_min_score", None) is not None:
            sys.stderr.write("tarja: pass either --min-score or --report-min-score, not both / passe um dos dois\n")
            return 2
        sys.stderr.write(
            "tarja: warning: --min-score was renamed to --report-min-score and goes away in 1.0.0. It filters "
            "the REPORT and never the exit code. / aviso: --min-score virou --report-min-score e sai na "
            "1.0.0. Filtra o RELATORIO, nunca o exit code.\n"
        )
        args.report_min_score = args.min_score
    # [CLI-MASK-NO-THRESHOLD] EN: mask has no report and therefore no threshold flag at all, so there is
    #   nothing to refuse here. Until 0.8.0 the threshold fed the mask, and `mask --min-score 0.9` left a
    #   0.50 BR_CEP unmasked in the output file, silently, with exit 0.
    #   PT: o mask nao tem relatorio nem flag de limiar. Antes o limiar alimentava a mascara e deixava valor
    #   em claro no arquivo de saida, em silencio.
    if getattr(args, "report_min_score", None) is None:
        args.report_min_score = 0.0
    try:
        text = _read(args.path, args.max_mb)
        # [CLI-GATE] EN: find runs ONCE with NO threshold, and the threshold filters the REPORT only. Until
        #   0.8.0 the same filtered list fed the report, the mask AND the exit code, so --min-score 0.9 hid a
        #   0.50 finding and turned exit 1 into exit 0. That flips `tarja scan f.txt && send.sh` from
        #   fail-closed to fail-open: raising a report filter opened the send gate. A display option must
        #   never decide whether data leaves the machine.
        #   PT: o find roda UMA vez sem limiar, e o limiar filtra so o RELATORIO. Opcao de exibicao nunca
        #   decide se o dado sai da maquina.
        found = find(text, entities=_entities(args.entities), min_score=0.0, report_invalid=True)
        # [CLI-SUSPECT] EN: a suspect is an ID-shaped run that fails its check digit, usually a typo or OCR
        #   noise on a REAL identifier. scan reports them on --suspect. mask MASKS them on --suspect, and
        #   otherwise says how many it left behind: until 0.8.0 mask forced report_invalid=False, so such a
        #   value left mask in cleartext, with exit 0, and residual() called the file clean, which is a green
        #   light over personal data. Masking by default is not the answer, because an invoice or protocol
        #   number in CPF shape is a suspect too, and mask output replaces the document.
        #   PT: suspeito e formato de ID c/ DV errado, normalmente erro de digitacao num identificador REAL.
        #   O default e AVISAR, nao apagar, pq nota fiscal e protocolo em forma de CPF tb sao suspeitos.
        n_suspect = sum(1 for m in found if not m.valid_dv)
        if not args.suspect:
            found = [m for m in found if m.valid_dv]
        if args.command == "mask":
            # [CLI-MASK-RUN]
            if not args.suspect and n_suspect:
                sys.stderr.write(
                    f"tarja: warning: {n_suspect} ID-shaped value(s) with a wrong check digit left UNMASKED, "
                    f"residual() will not see them by default. Use --suspect to mask them. / aviso: "
                    f"{n_suspect} valor(es) c/ cara de ID e DV errado ficaram SEM MASCARA.\n"
                )
            sys.stdout.write(mask(text, strategy=args.strategy, salt=args.salt, matches=found))
            return 0
        # [CLI-REPORT] EN: the threshold applies to valid matches only, the same rule find() documents: a
        #   suspect always scores 0 and is never filtered out by a threshold.
        #   PT: o limiar vale so p/ match valido. Suspeito pontua 0 e nunca e filtrado por limiar.
        report = [m for m in found if m.score >= args.report_min_score or not m.valid_dv]
        # [CLI-SCAN-RUN]
        if args.format == "jsonl":
            for m in report:
                sys.stdout.write(json.dumps(m.to_dict(include_value=args.show_values), ensure_ascii=False) + "\n")
        else:
            # simple fixed-width table
            sys.stdout.write(f"{'entity':<10} {'start':>7} {'end':>7} {'score':>5}  value\n")
            for m in report:
                shown = m.value if args.show_values else "*" * len(m.value)
                sys.stdout.write(f"{m.entity:<10} {m.start:>7} {m.end:>7} {m.score:>5.2f}  {shown}\n")
        # [CLI-SCAN-SUSPECT-WARN] EN: mask warned about unmasked suspects and scan did not, so
        #   `tarja scan f.txt && send.sh` still sent a file whose only finding was a mistyped CPF, which is
        #   the class of defect this release closes. Suspects stay OUT of the exit code without --suspect,
        #   because an invoice number in CPF shape would block every pipeline, but silence is not an option.
        #   PT: o mask avisava e o scan nao, entao um CPF digitado errado passava calado pelo portao.
        if not args.suspect and n_suspect:
            sys.stderr.write(
                f"tarja: warning: {n_suspect} ID-shaped value(s) with a wrong check digit NOT reported and "
                f"NOT counted in the exit code. Use --suspect to see them. / aviso: {n_suspect} valor(es) c/ "
                f"cara de ID e DV errado nao foram reportados nem contados no exit code.\n"
            )
        # [CLI-EXIT] exit 1 over the set of VALID candidates, before the report threshold. Handy in CI.
        return 1 if found else 0
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        # [CLI-ERROR] clean message instead of a traceback
        sys.stderr.write(f"tarja: {exc}\n")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
