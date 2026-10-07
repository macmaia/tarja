# tools/mutation_check.py
# [MUTATION] proves the tests really test something. Each mutant breaks one rule on purpose (wrong weight,
#   skipped check digit, context ignored...), runs the whole suite on a temp copy, and expects it to FAIL.
#   A "SURVIVED" line means a bug of that kind would slip through: add a test. Run: python tools/mutation_check.py

import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

# repo root
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# [MUTATION-LIST] (name, file, original snippet, mutated snippet)
M = [
    # [MUTATION-R3] the four defects the 3rd code review confirmed on 24/09/2026
    # [MUTATION-R3-B] the two decisions from that review, implemented the same day
    (
        "reveal goes back to strict matching",
        "src/tarja/vault.py",
        "        return TOKEN_RE_LENIENT.sub(put_back, text)",
        "        return TOKEN_RE.sub(put_back, text)",
    ),
    (
        "canonical token keeps the whitespace",
        "src/tarja/vault.py",
        '    digest = re.sub(r"\\s+", "", digest).lower()',
        "    digest = digest.lower()",
    ),
    (
        "regex safety check does nothing",
        "src/tarja/registry.py",
        "            if repeated and (_top_level_quantifier(body) or _duplicate_branches(body)):",
        "            if False:",
    ),
    (
        "unsafe_regex escape is always on",
        "src/tarja/registry.py",
        "    if not unsafe_regex:",
        "    if False:",
    ),
    # [MUT-SERIAL] restoring __dict__ undoes the whole reason Match stopped being a dataclass: vars() and
    #   asdict() start answering again, and those are what a log pipeline calls.
    # [MUT-EVADED] turning the extra pass off restores the evasion: one invisible character hides an
    #   identifier again, and find() returns nothing rather than a suspect.
    (
        "invisible characters hide identifiers again",
        "src/tarja/detect.py",
        "    found.extend(_evaded_candidates(text, ids, report_invalid))",
        "    found.extend([])",
    ),
    # [MUT-EVADED-BAR] without the higher bar, joining across a removed character invents findings on text
    #   where a soft hyphen sat at a line break.
    (
        "evaded match needs no check digit or context",
        "src/tarja/detect.py",
        'if ENTITIES[eid].tier != "N1" and not m.has_context:',
        "if False:",
    ),
    (
        "Match leaks through vars and asdict",
        "src/tarja/detect.py",
        '    __slots__ = ("entity", "start", "end", "_value",',
        '    __slots__ = ("__dict__", "entity", "start", "end", "_value",',
    ),
    (
        "Match repr shows the value again",
        "src/tarja/detect.py",
        '            f"pattern={self.pattern} context={self.has_context}{keep}, value hidden/valor oculto)"',
        '            f"pattern={self.pattern} context={self.has_context}{keep}, value={self.value})"',
    ),
    (
        "overlap sweep ignores the left neighbour",
        "src/tarja/detect.py",
        "        if i and kept[i - 1].end > m.start:",
        "        if False:",
    ),
    (
        "overlap sweep ignores the right neighbour",
        "src/tarja/detect.py",
        "        if i < len(kept) and m.end > kept[i].start:",
        "        if False:",
    ),
    (
        "input size limit does nothing",
        "src/tarja/detect.py",
        "    if max_chars is not None and len(text) > max_chars:",
        "    if False:",
    ),
    (
        "purge keeps expired values",
        "src/tarja/vault.py",
        "        while self._expiring and self._expiring[0][0] <= now:",
        "        while False:",
    ),
    (
        "purge drops values a live scope still needs",
        "src/tarja/vault.py",
        "        gone = [tok for tok in self._map if tok not in live]",
        "        gone = list(self._map)",
    ),
    (
        "exact repeat is not treated as a repeat",
        "src/tarja/registry.py",
        "        return int(inner) >= 2",
        "        return False",
    ),
    (
        "an exact inner count counts as variable",
        "src/tarja/registry.py",
        "        return True if not high.strip() else int(high) > int(low or 0)",
        "        return True",
    ),
    (
        # [MUT-DECIDE-DEFAULT] the default policy of the new primitive. Flipping it is silent: every test
        #   that passes on_suspect explicitly keeps passing.
        "decide allows suspect by default",
        "src/tarja/decide.py",
        '    on_suspect: str = "block",',
        '    on_suspect: str = "allow",',
    ),
    (
        # [MUT-DECIDE-BOOL] the sabotage that attribute tests cannot see. Decision.allowed stays correct
        #   and every `if not decide(text)` stops gating.
        "Decision is always truthy",
        "src/tarja/decide.py",
        "        return self.allowed\n",
        "        return True\n",
    ),
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
        # [MUTATION-OVERLAP-OFF] rewritten on 24/09/2026: the all-pairs check became a sorted sweep, so the
        #   way to disable overlap resolution now is to make the insertion unconditional.
        "overlap off",
        "src/tarja/detect.py",
        "        starts.insert(i, m.start)\n        kept.insert(i, m)",
        "        starts.append(m.start)\n        kept.append(m)",
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
    ("stable pseudonym ignores key", "src/tarja/mask.py", "hmac.new(key,", "hmac.new(b'x',"),
    ("cli shows values", "src/tarja/cli.py", "include_value=args.show_values", "include_value=True"),
    ("cli exit code", "src/tarja/cli.py", "return 1 if found else 0", "return 0"),
    ("registry drift", "src/tarja/entities.py", "score_without_context=0.85,", "score_without_context=0.84,"),
    # [MUTATION-E9] code added after E2 (2nd code review, 19/09/2026)
    ("vault collision check off", "src/tarja/vault.py", "if self._canon.get(tok, canon) != canon:", "if False:"),
    ("vault tokenises suspects", "src/tarja/vault.py", "if not m.valid_dv or m.end > edge:", "if m.end > edge:"),
    ("vault overlap guard off", "src/tarja/vault.py", "if not m.valid_dv or m.end > edge:", "if not m.valid_dv:"),
    ("vault 48-bit tokens", "src/tarja/vault.py", "TOKEN_HEX = 24", "TOKEN_HEX = 12"),
    ("adjacent context off", "src/tarja/detect.py", "if spec.context_before or spec.context_after:", "if False:"),
    ("suspects from any pattern", "src/tarja/detect.py", "pat.score >= SUSPECT_MIN_PATTERN_SCORE", "pat.score >= 0"),
    ("register N1 without validator", "src/tarja/registry.py", 'if tier == "N1" and validator is None:', "if False:"),
    ("unregister built-in allowed", "src/tarja/registry.py", "if entity_id in BUILTIN_IDS:", "if False:"),
    ("short salt accepted", "src/tarja/mask.py", "if len(key) < MIN_SALT_BYTES:", "if False:"),
    ("low-entropy salt accepted", "src/tarja/mask.py", "if len(set(key)) < MIN_SALT_DISTINCT:", "if False:"),
    ("placeholder salt accepted", "src/tarja/mask.py", "for w in WEAK_SALTS)", "for w in ())"),
    # [MUT-R4] 4th code review, 29/09/2026: the three mutants above cover mask(salt=), and the Vault was the path
    #   without the guard, so it needs its own mutant or the fix can be reverted silently.
    ("vault key not checked", "src/tarja/vault.py", "self._key = check_salt(key)", "self._key = key"),
    ("gate follows the report filter", "src/tarja/cli.py", "return 1 if found else 0", "return 1 if report else 0"),
    # [MUT-B4-MASK] the old mutant targeted a guard that no longer exists: the threshold flags moved to the
    #   scan subparser, so mask cannot receive one. The mutant that matters now is handing them back to mask.
    (
        "threshold flags offered on mask",
        "src/tarja/cli.py",
        'mk = sub.add_parser("mask", parents=[common]',
        'mk = sub.add_parser("mask", parents=[common, threshold]',
    ),
    ("score flag accepts nan", "src/tarja/cli.py", "if value != value or not (0.0 <= value <= 1.0):", "if False:"),
    ("max-mb accepts inf", "src/tarja/cli.py", "if value != value or not (0.0 < value <= 1024.0):", "if False:"),
    ("scan suspect warning removed", "src/tarja/cli.py", "if not args.suspect and n_suspect:", "if False:"),
    ("residual drops valid_dv", "src/tarja/vault.py", "m.valid_dv) for m in found]", "True) for m in found]"),
    (
        "residual ignores report_invalid",
        "src/tarja/vault.py",
        "find(blanked, min_score=min_score, report_invalid=report_invalid)",
        "find(blanked, min_score=min_score)",
    ),
    ("mask suspect warning removed", "src/tarja/cli.py", "if not args.suspect and n_suspect:", "if False:"),
    (
        # [MUTATION-SALT-PT] the guard used to be English only, in a library for Portuguese text
        "weak salt list forgets Portuguese",
        "src/tarja/mask.py",
        '    "chave", "exemplo", "minhachave", "minha-chave", "minhasenha", "minha-senha", "mude-me", "mudeme",',
        '    "zzz-placeholder-inexistente",',
    ),
    ("cli size cap off", "src/tarja/cli.py", "if len(text) > limit:", "if False:"),
    # [MUTATION-CARTAO] 0.6: the issuer prefix is what keeps Luhn from firing on every 10th long number
    (
        "cartao brand check off",
        "src/tarja/validators/cartao.py",
        "return brand(v) is not None if require_brand else True",
        "return True",
    ),
    (
        "cartao ignores length",
        "src/tarja/validators/cartao.py",
        "if len(v) in lengths and low <= v[: len(low)] <= high:",
        "if low <= v[: len(low)] <= high:",
    ),
    # [MUTATION-07] key generation marker and registry freeze, added in 0.7
    (
        "token drops the key id",
        "src/tarja/vault.py",
        'return f"<{entity}:{self._key_id}:{digest[:TOKEN_HEX]}>"',
        'return f"<{entity}:{digest[:TOKEN_HEX]}>"',
    ),
    (
        "key id ignores the key",
        "src/tarja/vault.py",
        "return hmac.new(key, KEY_ID_LABEL, hashlib.sha256).hexdigest()[:KEY_ID_HEX]",
        "return '0' * KEY_ID_HEX",
    ),
    (
        "mask label drops the key id",
        "src/tarja/mask.py",
        'return f"<{m.entity}:{kid}:{digest}>"',
        'return f"<{m.entity}:{digest}>"',
    ),
    ("freeze does nothing", "src/tarja/registry.py", "    if _FROZEN:", "    if False:"),
    ("reference cpf weights", "bench/reference.py", "list(range(10, 1, -1))", "list(range(9, 0, -1))"),
]


# [MUTATION-SPEED] EN: why this used to take a quarter of an hour, measured 01/10/2026 on the repository as
#   it stands. Copying the tree costs 0.10s per mutant, which is nothing. Running the suite costs 5.37s, and
#   it ran 71 times, in sequence, to the very end. That is the whole bill.
#
#   But a mutant is killed the moment ONE test fails, and everything after that first failure is work whose
#   answer is already known. With unittest's failfast the same two mutants measured 0.95s and 1.11s instead
#   of 5.31s and 5.35s, an 80% cut each, and the run goes from about 15 minutes to about 3.
#
#   What failfast costs, and it is real: the table below prints "failures=22" or "failures=1", which says how
#   many tests caught each mutant. A mutant caught by twenty-two tests is covered from every side; one caught
#   by a single test hangs by a thread, and that is worth seeing. Failfast always reports one. So the depth
#   number is not deleted, it moves behind --thorough, for when the question is coverage depth rather than
#   whether anything survived.
#   PT: o custo era a suite rodando inteira 71x. Mutante morre no 1o teste q falha, e o resto e trabalho cuja
#   resposta ja se sabe. Com failfast cai 80%. O q se perde e o "failures=22", q diz por quantos lados o
#   mutante foi pego, e isso continua no --thorough.
WORKERS = max(1, (os.cpu_count() or 2) - 1)


def _run_one(job: tuple, thorough: bool, only: str = "") -> tuple[str, str, str]:
    """EN: Copy the tree, apply one mutation, run the suite. PT: Copia, muta, roda."""
    name, rel, original, mutated = job
    with tempfile.TemporaryDirectory() as tmp:
        # [MUT-COPY] examples/ goes too: tests/test_revisao4.py reads it, and without it three tests
        #   skipped silently on every mutation run, which is a test that reports success by not running.
        for d in ("src", "tests", "spec", "bench", "examples"):
            shutil.copytree(os.path.join(R, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("*.jsonl"))
        shutil.copy(os.path.join(R, "README.md"), os.path.join(tmp, "README.md"))
        path = os.path.join(tmp, rel)
        with open(path, encoding="utf-8") as fh:
            code = fh.read()
        if original not in code:
            return name, "PATTERN NOT FOUND", ""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code.replace(original, mutated, 1))
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
        if only:
            # [MUT-COLUMN] one named test against every mutant. This is the direction a NEW test has to pass:
            #   "does anything break when I break the code this test claims to protect". The gate below runs
            #   the other direction and cannot answer it, because with failfast a redundant test never shows
            #   up as the first killer when an older test runs before it.
            cmd = [sys.executable, "-m", "unittest", only]
        elif not thorough:
            cmd.append("-f")
        # [MUT-PATH] tests/ has no __init__.py, so `unittest <module>.<Class>.<test>` only resolves with
        #   tests/ on the path. Without it the import fails, unittest reports FAILED, and every mutant looks
        #   killed. Caught 01/10/2026 on the first run of --for-test: three unrelated tests each "killed"
        #   all 71 mutants, including "freeze does nothing" and "reference cpf weights". A checker that
        #   certifies everything is worse than no checker, because it reports success.
        #   PT: sem o tests/ no path o import falha, o unittest diz FAILED e todo mutante parece morto.
        path = os.pathsep.join(["src", ".", "tests"])
        run = subprocess.run(
            cmd,
            cwd=tmp,
            env={**os.environ, "PYTHONPATH": path},
            capture_output=True,
            text=True,
        )
        if only and re.search(r"(ModuleNotFoundError|AttributeError: module|Failed to import)", run.stderr):
            # [MUT-COLUMN-GUARD] an id that does not resolve must not read as a kill
            raise SystemExit(f"--for-test could not load {only!r}:\n{run.stderr[-600:]}")
        m = re.search(r"FAILED \((.*)\)", run.stderr)
        if not m:
            return name, "SURVIVED", ""
        # [MUT-KILLER] EN: which test caught it. Parsed from the runner's own report lines rather than
        #   guessed, and only the first one is kept, because with failfast there is only ever one.
        killer = re.search(r"^(?:FAIL|ERROR): (\S+) \(([\w.]+)\)", run.stderr, re.M)
        who = f"{killer.group(2)}.{killer.group(1)}" if killer else ""
        return name, "KILLED " + m.group(1), who


def main(argv: list[str] | None = None) -> int:
    """EN: Run every mutant, print the table, exit 1 if any survived.
    PT: Roda todos, imprime, exit 1 se algum sobreviveu.

    --thorough  run each mutant against the FULL suite, so the table says how many tests caught it.
                Slower by roughly five times. Use it when the question is how deeply a mutant is covered.
    --serial    one at a time, for a readable traceback when something is wrong with the harness itself.
    """
    argv = sys.argv[1:] if argv is None else argv
    thorough = "--thorough" in argv
    workers = 1 if "--serial" in argv else WORKERS

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

    started = time.time()
    # [MUT-ONLY] --for-test tests.test_x.TestY.test_z
    only = ""
    for i, a in enumerate(argv):
        if a == "--for-test" and i + 1 < len(argv):
            only = argv[i + 1]
    if workers == 1 or only:
        results = [_run_one(job, thorough, only) for job in M]
    else:
        # [MUTATION-PARALLEL] each mutant works in its own temporary tree and shares nothing, so this is
        #   embarrassingly parallel. Order is restored below so the table reads the same every run.
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda job: _run_one(job, thorough, only), M))

    if only:
        # [MUT-COLUMN-REPORT] a new test earns its place by breaking when the code breaks. One that kills
        #   nothing is not necessarily wrong, but it is not evidence of anything either, and four tests in
        #   this project passed in the exact case they were written to catch.
        killed = [n for n, v, _ in results if v.startswith("KILLED")]
        print(f"{only}\n  kills {len(killed)} of {len(results)} mutants")
        for n in killed:
            print(f"    {n}")
        if not killed:
            print("  KILLS NOTHING. Either the test asserts something no mutant touches, or it cannot fail.")
        print(f"  {time.time() - started:.0f}s")
        return 0 if killed else 1

    for name, verdict, _ in results:
        print(f"{verdict:40} {name}")
    bad = [n for n, v, _ in results if not v.startswith("KILLED")]
    mode = "thorough" if thorough else "failfast"

    # [MUT-MAP] who caught what, written out so the next person can ask "which test protects this" without
    #   re-running anything. It is the first killer only, which is what failfast can honestly report.
    mapping = {n: w for n, v, w in results if v.startswith("KILLED") and w}
    (os.path.join(R, "spec", "mutation_map.json"))
    with open(os.path.join(R, "spec", "mutation_map.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(mapping.items())), fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\n{len(results) - len(bad)}/{len(results)} mutants killed / mutantes mortos")
    print(f"{time.time() - started:.0f}s, {mode}, {workers} worker(s)")
    print(f"{len(mapping)} killers recorded in spec/mutation_map.json")
    print("--thorough counts how many tests caught each. --for-test <id> asks what one test protects.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
