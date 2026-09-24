import argparse
import ast
import json
import os
import re
import shlex
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import httpx
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from prompt_builder import build_generation_prompt, build_fix_prompt

load_dotenv()

TIME_BUDGET_SECONDS = 240       # 4 min per file (raised from 2 by the course due to API load)
MAX_ITERATIONS = 5
MIN_SECONDS_FOR_RETRY = 20      # don't start a retry that leaves no room for metrics
MIN_SECONDS_FOR_MUTATION = 15   # below this, skip mutation testing rather than risk timing out mid-run
MAX_MUTATION_WORKERS = 8        # parallel cosmic-ray workers (capped by CPU count)
MIN_MUTANT_TIMEOUT = 3.0        # seconds; per-mutant timeout = max(this, factor x baseline suite time)
MUTANT_TIMEOUT_FACTOR = 3.0
API_RETRY_BACKOFF = 2.0         # seconds, multiplied by attempt number...
API_MAX_BACKOFF_STEPS = 3       # ...up to this many steps (so at most 6s between attempts)
API_CALL_TIMEOUT = 60           # cap for a single Gemini request, seconds
MIN_SECONDS_FOR_API_CALL = 10   # don't start a request that can't realistically finish
RESERVED_FOR_METRICS = 60       # generation/fix calls must end by budget minus this

CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    match = CODE_BLOCK_RE.search(text)
    return match.group(1) if match else text


def send_with_backoff(chat, prompt, deadline, backoff=API_RETRY_BACKOFF):
    """Send one message, retrying transient errors (e.g. 503 "model overloaded")
    for as long as time allows -- but never past `deadline` (a time.time() value).
    Under load a 503 can take ~45s to come back, so without a per-call timeout a
    few attempts alone blew the 2-minute budget."""
    last_error = TimeoutError("no time left for a Gemini call")
    attempt = 0
    while True:
        call_timeout = min(deadline - time.time(), API_CALL_TIMEOUT)
        if call_timeout < MIN_SECONDS_FOR_API_CALL:
            break
        attempt += 1
        try:
            config = types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=int(call_timeout * 1000)),
            )
            return chat.send_message(prompt, config=config)
        except Exception as e:
            last_error = e
            print(f"  [warn] Gemini call failed (attempt {attempt}): {str(e)[:120]}")
            time.sleep(min(backoff * min(attempt, API_MAX_BACKOFF_STEPS), max(deadline - time.time(), 0)))
    raise last_error


def is_high_demand_error(e: Exception) -> bool:
    """503 "high demand" / 504 or any timeout: the API couldn't serve us in
    time, as opposed to an agent bug or a bad request (400, 401, ...)."""
    if isinstance(e, errors.APIError):
        return e.code in (503, 504)
    return isinstance(e, (TimeoutError, httpx.TimeoutException))


def write_conftest(class_file: Path, output_folder: Path) -> None:
    own_dir = class_file.parent
    parent_dir = own_dir.parent
    rel_own = os.path.relpath(own_dir, output_folder)
    rel_parent = os.path.relpath(parent_dir, output_folder)
    content = f'''import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_own_dir = (_here / "{rel_own}").resolve()
_parent_dir = (_here / "{rel_parent}").resolve()

for _p in (str(_parent_dir), str(_own_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
'''
    if (own_dir / "__init__.py").exists():
        # Some projects have circular imports that only resolve when the package's
        # __init__ is the entry point (e.g. gin_rummy: action_event -> gin_rummy ->
        # ... -> move -> `from action_event import *` on a half-loaded module).
        # Import the package first, the way the project itself expects; if that
        # fails, tests just run as they would have without it.
        content += f'''
try:
    __import__("{own_dir.name}")
except Exception:
    pass
'''
    (output_folder / "conftest.py").write_text(content)


def run_pytest(test_file: Path, output_folder: Path, timeout: float = 30):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            cwd=output_folder,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "pytest timed out"


def count_passing(pytest_output: str) -> int:
    match = re.search(r"(\d+) passed", pytest_output)
    return int(match.group(1)) if match else 0


def find_failing_tests(test_file: Path, output_folder: Path, timeout: float = 30):
    """Return {(class_name_or_None, function_name)} for every failing/erroring test,
    or None if the results couldn't be read (e.g. the file doesn't even collect)."""
    report = output_folder / "pytest-report.xml"
    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", test_file.name, "-q", f"--junitxml={report.name}"],
            cwd=output_folder, capture_output=True, text=True, timeout=timeout,
        )
        root = ET.parse(report).getroot()
        failing = set()
        total = 0
        for case in root.iter("testcase"):
            total += 1
            if case.find("failure") is None and case.find("error") is None:
                continue
            # classname is "test_x" or "test_x.TestSomething"; name may carry "[param]"
            parts = case.get("classname", "").split(".")
            cls = parts[-1] if len(parts) > 1 and parts[-1] != test_file.stem else None
            failing.add((cls, case.get("name", "").split("[")[0]))
        if total == 0:
            return None
        return failing
    except Exception as e:
        print(f"  [warn] could not read pytest results: {e}")
        return None
    finally:
        report.unlink(missing_ok=True)


def prune_failing_tests(test_file: Path, failing) -> int:
    """Delete the failing test functions (with their decorators) from the file,
    editing by line ranges so comments and formatting elsewhere are preserved.
    Returns the number of test functions removed."""
    source = test_file.read_text()
    tree = ast.parse(source)
    ranges = []

    def collect(body, cls_name):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (cls_name, node.name) in failing:
                start = min([d.lineno for d in node.decorator_list] + [node.lineno])
                ranges.append((start, node.end_lineno))

    collect(tree.body, None)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            collect(node.body, node.name)

    lines = source.splitlines(keepends=True)
    for start, end in sorted(ranges, reverse=True):
        del lines[start - 1:end]
    test_file.write_text("".join(lines))
    return len(ranges)


def measure_coverage(class_file: Path, test_file: Path, output_folder: Path, timeout: float):
    coverage_json = output_folder / "coverage.json"
    try:
        subprocess.run(
            [sys.executable, "-m", "coverage", "run", "--branch",
             f"--include={class_file}", "-m", "pytest", "-q", test_file.name],
            cwd=output_folder, capture_output=True, text=True, timeout=timeout,
        )
        subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", str(coverage_json)],
            cwd=output_folder, capture_output=True, text=True, timeout=30,
        )
        data = json.loads(coverage_json.read_text())
        files = data.get("files", {})
        entry = files.get(str(class_file)) or next(iter(files.values()), None)
        if entry is None:
            return 0.0, 0.0
        summary = entry["summary"]
        line_cov = summary.get("percent_statements_covered", summary.get("percent_covered", 0.0)) / 100
        branch_cov = summary.get("percent_branches_covered", 0.0) / 100
        return line_cov, branch_cov
    except Exception as e:
        print(f"  [warn] coverage measurement failed: {e}")
        return 0.0, 0.0
    finally:
        (output_folder / ".coverage").unlink(missing_ok=True)
        coverage_json.unlink(missing_ok=True)


def cosmic_ray_test_command(test_file_name: str) -> str:
    # cosmic-ray runs this through shlex.split(), not a shell -- quote paths so a
    # space anywhere in them (e.g. "Tarea 1") doesn't break every mutant.
    return f"{shlex.quote(sys.executable)} -m pytest -x -q -p no:cacheprovider {shlex.quote(test_file_name)}"


def write_cosmic_ray_config(module_path: str, test_file_name: str, config_dir: Path, per_mutant_timeout: float) -> Path:
    config_path = config_dir / "cosmic-ray.toml"
    config_path.write_text(f'''[cosmic-ray]
module-path = "{module_path}"
timeout = {per_mutant_timeout:.1f}
excluded-modules = []
test-command = "{cosmic_ray_test_command(test_file_name)}"

[cosmic-ray.distributor]
name = "local"
''')
    return config_path


def setup_mutation_worker(class_file: Path, test_file: Path, worker_dir: Path) -> Path:
    """Build an isolated sandbox for one cosmic-ray worker:

        worker_dir/<project>/...   copy of the whole project folder (gets mutated)
        worker_dir/_cr_tests/      test file + conftest pointing at the copy

    cosmic-ray mutates the target file in place, so each parallel worker needs its
    own copy -- and the real project source is never touched at all. Returns the
    tests dir (cosmic-ray's cwd)."""
    project_dir = class_file.parent
    shutil.copytree(project_dir, worker_dir / project_dir.name,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    tests_dir = worker_dir / "_cr_tests"
    tests_dir.mkdir()
    shutil.copy2(test_file, tests_dir / test_file.name)
    write_conftest(worker_dir / project_dir.name / class_file.name, tests_dir)
    return tests_dir


def keep_only_shard(session_path: Path, shard: int, num_shards: int) -> None:
    """Delete every work item not in this worker's shard (deterministic order, so
    the shards across workers are disjoint and together cover every mutant)."""
    con = sqlite3.connect(session_path)
    job_ids = [row[0] for row in con.execute(
        "SELECT job_id FROM mutation_specs "
        "ORDER BY operator_name, occurrence, start_pos_row, start_pos_col, job_id")]
    drop = [(j,) for i, j in enumerate(job_ids) if i % num_shards != shard]
    con.executemany("DELETE FROM mutation_specs WHERE job_id = ?", drop)
    con.executemany("DELETE FROM work_items WHERE job_id = ?", drop)
    con.commit()
    con.close()


def read_mutation_outcomes(session_path: Path):
    """Return (killed, survived, incompetent) counts from a cosmic-ray session."""
    con = sqlite3.connect(session_path, timeout=1)
    rows = con.execute("SELECT test_outcome, COUNT(*) FROM work_results GROUP BY test_outcome").fetchall()
    con.close()
    counts = {str(outcome).lower(): n for outcome, n in rows}
    return counts.get("killed", 0), counts.get("survived", 0), counts.get("incompetent", 0)


def measure_mutation_score(class_file: Path, test_file: Path, output_folder: Path, timeout: float):
    if timeout < MIN_SECONDS_FOR_MUTATION:
        print(f"  [warn] skipping mutation testing, only {timeout:.1f}s left")
        return 0.0

    deadline = time.time() + timeout - 3
    num_workers = max(1, min(os.cpu_count() or 1, MAX_MUTATION_WORKERS))
    cr = [sys.executable, "-m", "cosmic_ray.cli"]
    # One BLAS thread per worker: N workers x N numpy threads would just thrash.
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    module_path = f"../{class_file.parent.name}/{class_file.name}"

    with tempfile.TemporaryDirectory(prefix="cr_") as tmp:
        workers = []
        procs = []
        try:
            tests_dirs = [setup_mutation_worker(class_file, test_file, Path(tmp) / f"w{i}")
                          for i in range(num_workers)]

            # Baseline run of the unmutated suite inside the sandbox. It must pass --
            # otherwise every mutant would count as "killed" and inflate the score --
            # and its duration sets the per-mutant timeout. Timed-out mutants count
            # as killed, so a tight timeout stops infinite-loop mutants from hogging
            # a worker for the full default.
            baseline_start = time.time()
            baseline = subprocess.run(
                shlex.split(cosmic_ray_test_command(test_file.name)),
                cwd=tests_dirs[0], capture_output=True, text=True, env=env,
                timeout=max(deadline - time.time(), 1),
            )
            baseline_seconds = time.time() - baseline_start
            if baseline.returncode != 0:
                print(f"  [warn] suite fails inside the mutation sandbox; skipping mutation testing")
                return 0.0
            per_mutant_timeout = max(MIN_MUTANT_TIMEOUT, MUTANT_TIMEOUT_FACTOR * baseline_seconds)

            for tests_dir in tests_dirs:
                config = write_cosmic_ray_config(module_path, test_file.name, tests_dir, per_mutant_timeout)
                workers.append((tests_dir, config, tests_dir / "session.sqlite"))

            # Every worker has the same layout, so one `init` serves all of them.
            first_dir, first_config, first_session = workers[0]
            subprocess.run(cr + ["init", first_config.name, first_session.name],
                           cwd=first_dir, capture_output=True, text=True, env=env,
                           timeout=max(deadline - time.time(), 1))
            planned = count_planned_mutants(first_session)
            # Copy the full session to every worker *before* sharding any of them --
            # sharding the first one in place and then copying it would hand the
            # others an already-pruned session (and silently drop most mutants).
            for _, _, session in workers[1:]:
                shutil.copy2(first_session, session)
            for i, (_, _, session) in enumerate(workers):
                keep_only_shard(session, i, num_workers)

            for tests_dir, config, session in workers:
                procs.append(subprocess.Popen(
                    cr + ["exec", config.name, session.name],
                    cwd=tests_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True, env=env,
                ))
            timed_out = False
            for proc in procs:
                try:
                    proc.wait(timeout=max(deadline - time.time(), 0.1))
                except subprocess.TimeoutExpired:
                    timed_out = True
                    break
            if timed_out:
                # session.sqlite is written incrementally as mutants complete, and
                # cosmic-ray runs them in random order -- so what finished is a random
                # sample, and its score is a fair estimate (beats reporting 0.0).
                print(f"  [warn] mutation testing timed out; using partial results")

            killed = survived = incompetent = 0
            for _, _, session in workers:
                k, s, inc = read_mutation_outcomes(session)
                killed, survived, incompetent = killed + k, survived + s, incompetent + inc
            total = killed + survived
            if incompetent:
                print(f"  [warn] {incompetent} mutant(s) incompetent (infra failure, excluded from score)")
            if planned and total < planned:
                print(f"  [warn] only {total}/{planned} mutants measured before time ran out")
            print(f"  mutantes: {killed} killed / {survived} survived "
                  f"({num_workers} workers, timeout {per_mutant_timeout:.1f}s/mutante)")
            return (killed / total) if total else 0.0
        except Exception as e:
            print(f"  [warn] mutation testing failed: {e}")
            return 0.0
        finally:
            # Kill whole process groups, not just cosmic-ray, so no pytest it spawned
            # outlives us.
            for proc in procs:
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except OSError:
                        # e.g. EPERM on macOS when the group is already exiting
                        proc.kill()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass


def count_planned_mutants(session_path: Path) -> int:
    try:
        con = sqlite3.connect(session_path)
        count = con.execute("SELECT COUNT(*) FROM mutation_specs").fetchone()[0]
        con.close()
        return count
    except Exception:
        return 0


def main(class_file_arg: str, output_folder_arg: str):
    start = time.time()

    def elapsed():
        return time.time() - start

    def remaining():
        return TIME_BUDGET_SECONDS - elapsed()

    class_file = Path(class_file_arg).resolve()
    output_folder = Path(output_folder_arg).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    module_stem = class_file.stem
    test_file = output_folder / f"test_{module_stem}.py"

    write_conftest(class_file, output_folder)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: No se encontro la variable GEMINI_API_KEY en el entorno.")
        sys.exit(1)

    client = genai.Client()
    chat = client.chats.create(model="gemini-3.1-flash-lite")

    print(f"[{elapsed():.1f}s] Generando suite inicial para {module_stem}.py...")
    prompt = build_generation_prompt(class_file, class_file.parent)
    generated_ok = False
    last_api_error = None
    llm_deadline = start + TIME_BUDGET_SECONDS - RESERVED_FOR_METRICS
    try:
        response = send_with_backoff(chat, prompt, llm_deadline)
        code = extract_code(response.text)
        generated_ok = True
    except Exception as e:
        last_api_error = e
        print(f"  [warn] no se pudo generar la suite inicial: {e}")
        code = "# generation failed: could not reach Gemini API\n"
    test_file.write_text(code)

    passed, output = run_pytest(test_file, output_folder)
    iteration = 1
    print(f"[{elapsed():.1f}s] Intento {iteration}: {'PASSED' if passed else 'FAILED'}")
    # A "fix" can make things worse (e.g. a syntax error), so remember the version
    # with the most passing tests and fall back to it if we run out of retries.
    best_code, best_passing = code, count_passing(output)

    while not passed and iteration < MAX_ITERATIONS and remaining() > MIN_SECONDS_FOR_RETRY:
        try:
            # If we never got a successful turn yet, there is nothing real for the
            # model to "fix" -- resend the original full-context prompt instead of
            # a delta-fix prompt, or the model ends up improvising with no source
            # code in its actual conversation history.
            next_prompt = prompt if not generated_ok else build_fix_prompt(output)
            response = send_with_backoff(chat, next_prompt, llm_deadline)
            code = extract_code(response.text)
            test_file.write_text(code)
            generated_ok = True
        except Exception as e:
            last_api_error = e
            print(f"  [warn] fallo la llamada a Gemini en el intento {iteration + 1}: {e}")
            break
        passed, output = run_pytest(test_file, output_folder)
        iteration += 1
        print(f"[{elapsed():.1f}s] Intento {iteration}: {'PASSED' if passed else 'FAILED'}")
        if count_passing(output) > best_passing:
            best_code, best_passing = code, count_passing(output)

    if not generated_ok:
        # Gemini never answered, so there is no suite at all -- the failure is the
        # API's, not the agent's. Report it as such instead of fake 0.0 metrics.
        test_file.write_text("# generation failed: could not reach Gemini API\n")
        print(f"[{elapsed():.1f}s] ERROR de la API de Gemini: {type(last_api_error).__name__}: {last_api_error}")
        if last_api_error is not None and is_high_demand_error(last_api_error):
            metrics = {"error": "High demand"}
            (output_folder / "metrics.json").write_text(json.dumps(metrics, indent=2))
            print(f"[{elapsed():.1f}s] Listo. metrics.json: {metrics}")
            return False, metrics

    print(f"[{elapsed():.1f}s] Suite final: {'PASSED' if passed else 'FAILED'} tras {iteration} intento(s)")

    if not passed and best_code != code:
        print(f"  volviendo a la mejor version ({best_passing} tests pasando)")
        test_file.write_text(best_code)

    if not passed:
        # Out of retries: keep the tests that do pass instead of throwing the whole
        # suite away. Failing tests must go (not just be ignored) -- a test that
        # always fails would "kill" every mutant and inflate the mutation score.
        failing = find_failing_tests(test_file, output_folder)
        if failing:
            removed = prune_failing_tests(test_file, failing)
            passed, output = run_pytest(test_file, output_folder)
            print(f"[{elapsed():.1f}s] Se eliminaron {removed} test(s) fallidos; "
                  f"suite restante: {'PASSED' if passed else 'FAILED'}")

    if passed:
        print(f"[{elapsed():.1f}s] Midiendo cobertura...")
        line_cov, branch_cov = measure_coverage(
            class_file, test_file, output_folder, timeout=max(remaining() - 10, 5)
        )

        print(f"[{elapsed():.1f}s] Corriendo mutation testing (cosmic-ray)...")
        mutation_score = measure_mutation_score(
            class_file, test_file, output_folder, timeout=remaining() - 5
        )
    else:
        print("  [warn] la suite no paso pytest; se omiten metricas de cobertura/mutacion")
        line_cov = branch_cov = mutation_score = 0.0

    metrics = {
        "line_coverage": round(line_cov, 4),
        "branch_coverage": round(branch_cov, 4),
        "mutation_score": round(mutation_score, 4),
    }
    (output_folder / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"[{elapsed():.1f}s] Listo. metrics.json: {metrics}")
    return passed, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente basado en LLM para generacion iterativa de tests.")
    parser.add_argument("ruta_archivo", type=str)
    parser.add_argument("output_folder", type=str)
    args = parser.parse_args()
    # Turn SIGTERM into a normal exit so `finally` blocks (source restore) still run.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))
    main(args.ruta_archivo, args.output_folder)
