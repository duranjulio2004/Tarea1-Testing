import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from prompt_builder import build_generation_prompt, build_fix_prompt

load_dotenv()

TIME_BUDGET_SECONDS = 120
MAX_ITERATIONS = 5
MIN_SECONDS_FOR_RETRY = 20      # don't start a retry that leaves no room for metrics
MIN_SECONDS_FOR_MUTATION = 15   # below this, skip mutation testing rather than risk timing out mid-run
API_RETRY_ATTEMPTS = 3          # transient-error retries for a single Gemini call
API_RETRY_BACKOFF = 2.0         # seconds, multiplied by attempt number

CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    match = CODE_BLOCK_RE.search(text)
    return match.group(1) if match else text


def send_with_backoff(chat, prompt, max_attempts=API_RETRY_ATTEMPTS, backoff=API_RETRY_BACKOFF):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return chat.send_message(prompt)
        except Exception as e:
            last_error = e
            print(f"  [warn] Gemini call failed (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                time.sleep(backoff * attempt)
    raise last_error


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


def write_cosmic_ray_config(class_file: Path, test_file: Path, output_folder: Path, per_mutant_timeout: float) -> Path:
    rel_module = os.path.relpath(class_file, output_folder)
    config_path = output_folder / "cosmic-ray.toml"
    config_path.write_text(f'''[cosmic-ray]
module-path = "{rel_module}"
timeout = {per_mutant_timeout}
excluded-modules = []
test-command = "{shlex.quote(sys.executable)} -m pytest -x -q {shlex.quote(test_file.name)}"

[cosmic-ray.distributor]
name = "local"
''')
    return config_path


def measure_mutation_score(class_file: Path, test_file: Path, output_folder: Path, timeout: float):
    if timeout < MIN_SECONDS_FOR_MUTATION:
        print(f"  [warn] skipping mutation testing, only {timeout:.1f}s left")
        return 0.0

    config_path = write_cosmic_ray_config(class_file, test_file, output_folder, per_mutant_timeout=10.0)
    session_path = output_folder / "session.sqlite"
    session_path.unlink(missing_ok=True)
    cr = [sys.executable, "-m", "cosmic_ray.cli"]
    try:
        subprocess.run(
            cr + ["init", config_path.name, session_path.name],
            cwd=output_folder, capture_output=True, text=True, timeout=30,
        )
        planned = count_planned_mutants(session_path)

        try:
            subprocess.run(
                cr + ["exec", config_path.name, session_path.name],
                cwd=output_folder, capture_output=True, text=True, timeout=max(timeout - 5, 5),
            )
        except subprocess.TimeoutExpired:
            # session.sqlite is written incrementally as mutants complete, so
            # whatever finished before the timeout is still on disk and usable --
            # a partial real score beats discarding everything and reporting 0.0.
            print(f"  [warn] mutation testing timed out; using partial results")

        dump = subprocess.run(
            cr + ["dump", session_path.name],
            cwd=output_folder, capture_output=True, text=True, timeout=30,
        )
        killed = total = 0
        for line in dump.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            result = item[1] if isinstance(item, list) and len(item) > 1 else None
            outcome = result.get("test_outcome") if result else None
            if outcome in ("killed", "survived"):
                total += 1
                if outcome == "killed":
                    killed += 1
            elif outcome == "incompetent":
                print(f"  [warn] mutant marked incompetent (infra failure, excluded from score)")

        if planned and total < planned:
            print(f"  [warn] only {total}/{planned} mutants measured before time ran out")
        return (killed / total) if total else 0.0
    except Exception as e:
        print(f"  [warn] mutation testing failed: {e}")
        return 0.0
    finally:
        session_path.unlink(missing_ok=True)
        config_path.unlink(missing_ok=True)


def count_planned_mutants(session_path: Path) -> int:
    try:
        import sqlite3
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
    try:
        response = send_with_backoff(chat, prompt)
        code = extract_code(response.text)
        generated_ok = True
    except Exception as e:
        print(f"  [warn] no se pudo generar la suite inicial: {e}")
        code = "# generation failed: could not reach Gemini API\n"
    test_file.write_text(code)

    passed, output = run_pytest(test_file, output_folder)
    iteration = 1
    print(f"[{elapsed():.1f}s] Intento {iteration}: {'PASSED' if passed else 'FAILED'}")

    while not passed and iteration < MAX_ITERATIONS and remaining() > MIN_SECONDS_FOR_RETRY:
        try:
            # If we never got a successful turn yet, there is nothing real for the
            # model to "fix" -- resend the original full-context prompt instead of
            # a delta-fix prompt, or the model ends up improvising with no source
            # code in its actual conversation history.
            next_prompt = prompt if not generated_ok else build_fix_prompt(output)
            response = send_with_backoff(chat, next_prompt)
            code = extract_code(response.text)
            test_file.write_text(code)
            generated_ok = True
        except Exception as e:
            print(f"  [warn] fallo la llamada a Gemini en el intento {iteration + 1}: {e}")
            break
        passed, output = run_pytest(test_file, output_folder)
        iteration += 1
        print(f"[{elapsed():.1f}s] Intento {iteration}: {'PASSED' if passed else 'FAILED'}")

    print(f"[{elapsed():.1f}s] Suite final: {'PASSED' if passed else 'FAILED'} tras {iteration} intento(s)")

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
    main(args.ruta_archivo, args.output_folder)
