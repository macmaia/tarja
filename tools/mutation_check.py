# tools/mutation_check.py
# [MUTATION] proves the tests really test something. Each mutant breaks one rule on purpose (wrong weight,
#   skipped check digit, context ignored...), runs the whole suite on a temp copy, and expects it to FAIL.
#   A "SURVIVED" line means a bug of that kind would slip through: add a test. Run: python tools/mutation_check.py

import os
import re
import shutil
import subprocess
import sys
import tempfile

# repo root
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# [MUTATION-LIST] (name, file, original snippet, mutated snippet)
M = [
    (
        "cpf always valid",
        "src/tarja/validators/cpf.py",
        "    return compute_check_digits(v[:9]) == v[9:]",
        "    return True",
    ),
    (
        "cpf remainder<2 -> 1",
        "src/tarja/validators/cpf.py",
        "return 0 if remainder < 2 else 11 - remainder",
        "return 1 if remainder < 2 else 11 - remainder",
    ),
    (
        "cnpj weight swap",
        "src/tarja/validators/cnpj.py",
        "_W1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)",
        "_W1 = (4, 5, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)",
    ),
    ("cnpj ignore letters (int)", "src/tarja/validators/cnpj.py", "(ord(c) - 48) * w", "(ord(c) - 47) * w"),
    (
        "cns definitive mod-only",
        "src/tarja/validators/cns.py",
        "        return definitive_from_pis(v[:11]) == v",
        "        return weighted_sum(v) % 11 == 0",
    ),
    (
        "nis 10->0 removed",
        "src/tarja/validators/nis.py",
        'return "0" if digit >= 10 else str(digit)',
        "return str(digit % 10)",
    ),
    ("cnj 98->97", "src/tarja/validators/cnj.py", "98 - int(sequence", "97 - int(sequence"),
    ("cnm 98->99", "src/tarja/validators/cnm.py", "98 - int(base14", "99 - int(base14"),
    ("titulo sp/mg rule off", "src/tarja/validators/titulo.py", 'sp_mg = state2 in ("01", "02")', "sp_mg = False"),
    ("cnh discount off", "src/tarja/validators/cnh.py", "d1, discount = 0, 2", "d1, discount = 0, 0"),
    ("renavam *10 off", "src/tarja/validators/renavam.py", ") * 10 % 11", ") % 11"),
    ("cib mod31->29", "src/tarja/validators/cib.py", ")) % 31", ")) % 29"),
    ("telefone ddd off", "src/tarja/validators/telefone.py", 'return v[:2] in DDDS and v[2] == "9"', 'return v[2] == "9"'),
    ("cep range off", "src/tarja/validators/cep.py", "int(v) >= 1000000", "int(v) >= 0"),
    (
        "context never",
        "src/tarja/detect.py",
        "return _context_regex(spec.context_words).search(window) is not None",
        "return False",
    ),
    ("context substring", "src/tarja/detect.py", "(?<![0-9a-z])(?:{alternatives})(?![0-9a-z])", "(?:{alternatives})"),
    ("context_required ignored", "src/tarja/detect.py", "if spec.context_required and not ctx:", "if False:"),
    (
        "dv check skipped",
        "src/tarja/detect.py",
        "if spec.validator is not None and not spec.validator(m.group(0)):",
        "if False:",
    ),
    (
        "overlap off",
        "src/tarja/detect.py",
        "        if all(m.end <= k.start or m.start >= k.end for k in kept):",
        "        if True:",
    ),
    ("overlap tier ignored", "src/tarja/detect.py", "return (TIER_RANK.get(m.tier, 9), -m.score", "return (0, -m.score"),
    ("normalise off", "src/tarja/normalise.py", "    if text.isascii():\n        return text", "    return text"),
    (
        "fold no accents strip",
        "src/tarja/normalise.py",
        'unicodedata.normalize("NFD", c.lower()[:1] or c)[0]',
        "c.lower()[:1] or c",
    ),
    ("pseudonym not consistent", "src/tarja/mask.py", "        if k not in labels:", "        if True:"),
    ("hash ignores salt", "src/tarja/mask.py", "hmac.new(key,", "hmac.new(b'x',"),
    ("cli shows values", "src/tarja/cli.py", "include_value=args.show_values", "include_value=True"),
    ("cli exit code", "src/tarja/cli.py", "return 1 if found else 0", "return 0"),
    ("registry drift", "src/tarja/entities.py", "score_without_context=0.85,", "score_without_context=0.84,"),
    # [MUTATION-E9] code added after E2 (board round 2, 19/09/2026)
    ("vault collision check off", "src/tarja/vault.py", "if self._canon.get(tok, canon) != canon:", "if False:"),
    ("vault tokenises suspects", "src/tarja/vault.py", "if not m.valid_dv or m.end > edge:", "if m.end > edge:"),
    ("vault overlap guard off", "src/tarja/vault.py", "if not m.valid_dv or m.end > edge:", "if not m.valid_dv:"),
    ("vault 48-bit tokens", "src/tarja/vault.py", "TOKEN_HEX = 24", "TOKEN_HEX = 12"),
    ("adjacent context off", "src/tarja/detect.py", "if spec.context_before or spec.context_after:", "if False:"),
    ("suspects from any pattern", "src/tarja/detect.py", "pat.score >= SUSPECT_MIN_PATTERN_SCORE", "pat.score >= 0"),
    ("register N1 without validator", "src/tarja/registry.py", 'if tier == "N1" and validator is None:', "if False:"),
    ("unregister built-in allowed", "src/tarja/registry.py", "if entity_id in BUILTIN_IDS:", "if False:"),
    ("short salt silent", "src/tarja/mask.py", "< MIN_SALT_BYTES:", "< 0:"),
    ("cli size cap off", "src/tarja/cli.py", "if len(text) > limit:", "if False:"),
    ("reference cpf weights", "bench/reference.py", "list(range(10, 1, -1))", "list(range(9, 0, -1))"),
]


def main() -> int:
    """EN: Run every mutant, print the table, exit 1 if any survived. PT: Roda todos, imprime, exit 1 se algum sobreviveu."""
    results = []
    # [MUTATION-BASELINE] the unmutated suite must pass first, or every mutant would look "killed"
    base = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=R,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(["src", "."])},
        capture_output=True,
        text=True,
    )
    if base.returncode != 0:
        print("baseline suite fails, fix it before mutation testing")
        print(base.stderr[-2000:])
        return 2
    for name, rel, original, mutated in M:
        with tempfile.TemporaryDirectory() as tmp:
            # copy only what the tests need
            for d in ("src", "tests", "spec", "bench"):
                shutil.copytree(os.path.join(R, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("*.jsonl"))
            path = os.path.join(tmp, rel)
            with open(path, encoding="utf-8") as fh:
                code = fh.read()
            if original not in code:
                results.append((name, "PATTERN NOT FOUND"))
                continue
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(code.replace(original, mutated, 1))
            env = {**os.environ, "PYTHONPATH": os.pathsep.join(["src", "."])}
            run = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
            )
            m = re.search(r"FAILED \((.*)\)", run.stderr)
            results.append((name, "KILLED " + m.group(1) if m else "SURVIVED"))
    for name, verdict in results:
        print(f"{verdict:40} {name}")
    bad = [n for n, v in results if not v.startswith("KILLED")]
    print(f"\n{len(results) - len(bad)}/{len(results)} mutants killed / mutantes mortos")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
