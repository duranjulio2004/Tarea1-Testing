# Tarea 1 — Agentic Test Generation (IIC3745 Testing, PUC)

**Deadline: Thursday 2026-09-24, 23:59 (no-penalty).** Read `Enunciado Tarea 1.pdf`
at the repo root for the full spec — this file is a condensed, practical summary
plus a handoff of everything already built and learned. This repo is
self-contained; you don't need anything outside this folder.

Work is done in pairs. Only one partner needs to submit; the latest submission
is what gets graded if both submit.

## What the assignment actually wants

Build `T1_base/agent.py`, invoked as:
```
python agent.py <path/to/class_file.py> <output_folder>
```
It must, fully automatically (no manual editing of what it generates), for the
given Python file:
1. Generate a pytest test suite using the Gemini API (`google-genai`, model
   **`gemini-3.1-flash-lite`** — no other model is allowed).
2. Run the tests, and if they fail, iteratively ask the model to fix them.
3. Write the final suite to `<output_folder>/test_<ClassName>.py`.
4. Measure and write `<output_folder>/metrics.json`:
   ```json
   {"line_coverage": 0.85, "branch_coverage": 0.55, "mutation_score": 0.60}
   ```
   (fractions 0–1, via `coverage` for the first two and `cosmic-ray` for the
   third.)
5. **Finish within 2 minutes wall-clock, total, per invocation.** This includes
   every LLM call, every retry, coverage, and mutation testing — not just
   generation.

Grading thresholds per file: line coverage ≥80%, branch coverage ≥50%,
mutation score ≥50%. Scored across the 7 `Public_Proyects/` folders (23 files)
plus a held-out set the professors will supply separately.

Other deliverables (see enunciado §8 for the exact list):
- `.zip` of the whole agent project folder (i.e. `T1_base/`, minus `.venv`/`.env`)
- The generated test suites for the public projects (already produced under
  `T1_base/Results/`)
- `README.md` (max 1 page) describing the strategy, design decisions, and
  limitations found — **currently empty, still needs to be written**
- A link to a ~5 min explainer video (both partners must appear) — **not a
  coding task, that's on you two directly**

## Current status (as of this handoff)

**Working and validated:**
- `T1_base/prompt_builder.py` — builds the generation prompt (target file +
  every sibling `.py` in its project folder, minus `__init__.py`) and the
  fix/retry prompt. Design rationale below.
- `T1_base/agent.py` — the full pipeline: generation → pytest → retry loop →
  coverage → mutation testing → `metrics.json`. Confirmed working end-to-end
  on `blackjack/dealer.py` (100%/100%/85.7%) and `mahjong/game.py`
  (100%/100%/68%, larger file, ~39s total — mutation testing scales fine).
- Import resolution (`conftest.py`, auto-generated per output folder) — works
  across every structural variant tried: package-style (`blackjack`, has
  `__init__.py`), no-package (`tree`), and the tricky self-named-module case
  (`svm/svm.py`, file name == folder name — see bugs below).

**Partially working / needs a rerun:**
- `svm/svm.py`: import bug is fixed, 9/10 generated tests pass. The 1 failure
  (`test_predict_errors`, calls `.predict()` before `.fit()`, real
  `AttributeError` in `base.py`) is a genuine LLM test-content issue, not
  infra — legitimate material for the video's "code quality" discussion, but
  don't hand-fix it (that breaks the "no manual edits" rule). Worth another
  retry run to see if the model resolves it on its own; if not, it's fine to
  leave as an honestly-reported limitation.
- `tree/tree.py`: **was mid-run when this handoff was written — the output
  folder was deleted, nothing to pick up, just rerun it from scratch.** This
  is the file that originally surfaced the mutation-testing-timeout problem
  (see "partial mutation results" fix below) — rerun it once to confirm that
  fix actually produces a non-zero `mutation_score` under time pressure,
  since it was never re-verified after being written.

**Not started at all:**
- Only 3 of the 23 target files across the 7 public projects have been run
  even once: `blackjack/dealer.py`, `mahjong/game.py`, `svm/svm.py`. Everything
  else (`gin_rummy/*`, `stock4/*`, `fuzzywuzzy/*`, the rest of `blackjack/*`
  and `mahjong/*`, `tree/base.py`) hasn't been touched. `run_all.sh` will do
  all of them in one go (see below) — just budget real time for it, since
  Gemini has been unreliable (see below) and each file can take anywhere from
  ~10s to ~2min.
- `README.md` is empty.

## Architecture & why it's built this way

### Import resolution (`write_conftest` in `agent.py`)
The public projects use genuinely inconsistent import styles — some do
`from blackjack import Card` (package-qualified, needs the *project's parent
folder* on `sys.path`), others do `from utils import init_deck` (flat sibling
import, needs the *file's own folder* on `sys.path`). Rather than making the
LLM guess or resolve this, `agent.py` computes both directories deterministically
from the target file's path and writes a `conftest.py` into the output folder
that inserts them into `sys.path` before pytest collects anything (pytest
auto-runs any `conftest.py` in a test's directory — no import needed). The
LLM is told to always use the flat form:
`from <module_stem> import <ClassName>` — guaranteed to work regardless of
whether the project has an `__init__.py`.

**Important subtlety, already fixed once, don't reintroduce it:** the two
directories must be inserted with the *file's own folder* ending up **first**
in `sys.path` (highest priority), parent folder second. Do it the other way
and any file whose name matches its own folder name (e.g. `svm/svm.py`) will
have `from svm import X` accidentally resolve to the *package* `svm/__init__.py`
instead of the flat module `svm.py`, since Python's import system just takes
whichever match it finds first in `sys.path` order. This silently breaks
imports with a confusing `ImportError` that has nothing to do with the LLM's
actual code — it already cost a debugging session once.

**Also important:** paths in `conftest.py` are computed relative to the
conftest file's own location on disk (via `Path(__file__).resolve().parent`),
never as an absolute string baked in at generation time — otherwise the whole
thing breaks the moment the project folder is copied/zipped/unzipped
elsewhere (which is exactly what happens at submission time). This was
verified by literally copying the whole `T1_base/` folder to an unrelated
path and confirming tests still passed there.

### Prompt content (`build_generation_prompt` in `prompt_builder.py`)
The prompt includes the target file's full source **plus every other `.py`
file in the same project folder** (minus `__init__.py`, which is just
re-export aliasing with no real logic). This was a deliberate choice over two
alternatives:
- Target file alone: risks the model hallucinating the behavior of classes
  the target file references but doesn't define locally (seen in practice —
  see "hallucination" bug below).
- Precise, resolved-dependency-only inclusion: more surgical, but requires
  writing per-import-style resolution logic that's fragile against the
  held-out project set used for final grading, which we haven't seen.

Full-folder inclusion is a bit wasteful (pulls in files the target doesn't
actually need, e.g. `game.py` when testing `dealer.py`) but robust and simple,
and Gemini's context window makes the waste a non-issue. This was a deliberate
tradeoff, already discussed and accepted — don't "fix" it by adding import-based
filtering unless you have a specific reason to revisit it.

### Test-quality instructions baked into the prompt
The prompt explicitly asks for: boundary/equivalence-partition cases (not just
happy-path calls), full branch coverage (both sides of every `if`, both
taken/skipped loop paths), and — important — **real `numpy.random.RandomState(seed)`
instead of mocking `np_random`**, since several classes take that parameter and
mocking it would produce exactly the "trivial/useless assertions" failure mode
the enunciado's video rubric asks you to critique.

### The retry loop
`MAX_ITERATIONS = 5`, stops early if `remaining time < MIN_SECONDS_FOR_RETRY (20s)`.
Two important, non-obvious things about how it's built:

1. **It's a single persistent `chat` session** (`client.chats.create(...)`),
   not independent one-shot calls — the fix prompt is small (just "here's the
   pytest failure, fix it") and relies on the model remembering the original
   source from turn 1.
2. **This broke once, in a subtle way worth understanding before touching the
   loop again:** if the *first* generation call fails (API error), the code
   used to fall through into the retry loop anyway, sending a "fix your
   failing test" prompt into a chat session that never actually saw the
   source code (because turn 1 never completed). The model had nothing real
   to fix, so it hallucinated a plausible-looking but completely wrong test —
   concretely, for `blackjack/dealer.py` it invented a `dealer_policy(sum,
   np_random)` function returning `"hit"`/`"stick"`, which is the *OpenAI Gym
   `Blackjack-v1`* dealer convention, not this project's actual API at all.
   Fixed via a `generated_ok` flag: if we've never had a successful turn yet,
   retries resend the *original* full-context prompt, not the delta-fix
   prompt. Don't remove this flag or "simplify" the loop back to always using
   the fix prompt.

### Gemini API reliability — expect this, it's not a bug in our code
`gemini-3.1-flash-lite` has hit sustained `503 UNAVAILABLE` ("model
overloaded") errors repeatedly during development — sometimes clearing in a
few seconds, sometimes taking 100+ seconds across many calls. This appears to
be normal shared-capacity contention for this specific (preview-ish) model
under free-tier traffic, not a rare fluke — expect it during your own runs,
and *especially* expect it might happen during grading, which is exactly why
the retry/backoff logic matters and shouldn't be ripped out for being
"unnecessary complexity." `send_with_backoff()` in `agent.py` retries a single
call up to 3x with increasing delay before giving up. Worth a line in
`README.md`'s limitations section.

### Mutation testing (`measure_mutation_score` in `agent.py`)
Uses `cosmic-ray`, invoked via `python -m cosmic_ray.cli` (not the `cosmic-ray`
console script — avoids depending on `.venv/bin` being on `PATH`). Three real
bugs found and fixed here, all non-obvious:

1. **The course-provided `T1_base/cosmic-ray.toml` uses a config schema that
   doesn't match the `cosmic-ray` version `pip install`s today** (8.7.0,
   since `requirements.txt` doesn't pin a version). It has
   `[cosmic-ray.execution-engine]` / a `test-runner` table; the installed
   version wants `[cosmic-ray.distributor]` and a flat `test-command` string.
   `agent.py` no longer uses that root-level file at all — it generates a
   correct one per invocation via `write_cosmic_ray_config()`. The old
   `T1_base/cosmic-ray.toml` is left in place untouched (matches what the
   course handed out) but is vestigial — don't be confused into thinking it's
   load-bearing, and mention the schema mismatch in the README since anyone
   following the starter file literally will hit it.
2. **`shlex.split()` on the `test-command` string breaks if any path in it
   contains a space.** `cosmic-ray` runs the test command through
   `shlex.split()`, not a real shell. This actually bit us for real: this dev
   machine's path includes `Tarea 1` (a space, to match the course's own
   `Actividad 2` folder-naming convention) — every mutant silently failed
   with `FileNotFoundError`, which `cosmic-ray` reports as `"incompetent"`
   (not `killed`/`survived`), and the score computation only counted
   `killed`, so it silently came back as `0.0` instead of erroring loudly.
   Fixed with `shlex.quote()` around `sys.executable` and the test file name
   in `write_cosmic_ray_config()`. **If you rename or move this repo to
   another path with a space in it, this is the first thing to suspect if
   mutation scores mysteriously come back as 0.**
3. **The `local` distributor is fully sequential, not parallel** — one mutant
   at a time, each paying a fresh subprocess's full import cost (`scipy`
   import alone costs a few hundred ms). This means files that import heavier
   libraries take proportionally longer per mutant, not just "more mutants
   because more statements." `tree/tree.py` (imports `scipy.stats`) timed out
   on this basis even though it only has a modest number of statements.
4. **Partial-results fix (written, not yet re-verified — do this first):**
   `cosmic-ray`'s `session.sqlite` is written incrementally as mutants
   complete. The mutation-testing timeout used to discard everything and
   report a flat `0.0` when time ran out mid-run. Now it catches the
   `TimeoutExpired`, and still reads+scores whatever's in `session.sqlite` so
   far — a real partial score is much more honest than a misleading `0.0`
   that implies the tests are bad when they might be fine. **This was the
   very last edit made before this handoff, and the run meant to confirm it
   (`tree/tree.py`) was interrupted before finishing — rerun it first thing.**

## Environment setup (on this new machine)

```bash
cd T1_base
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You'll need your **own** Gemini API key (from https://aistudio.google.com/apikey
— confirm `gemini-3.1-flash-lite` is enabled for it):
```bash
cp .env.example .env
# edit .env, set GEMINI_API_KEY=<your key>
```
`.env` is gitignored on purpose — never commit it.

## Running it

Single file:
```bash
cd T1_base
source .venv/bin/activate
python3 agent.py "Public_Proyects/blackjack/dealer.py" "Results/blackjack/dealer"
```

All public projects (iterates every target file listed in the enunciado, with
a 5s pause between calls for rate limits):
```bash
chmod +x run_all.sh
./run_all.sh
```
This will take a while — budget real time given the API flakiness noted
above. Consider running it in the background / a long-lived terminal rather
than expecting it to finish quickly.

## Priority order for what's left (given the deadline is close)

1. Rerun `tree/tree.py` to confirm the partial-mutation-results fix actually
   produces a non-zero score under time pressure.
2. Run `./run_all.sh` (or file-by-file) across everything untested —
   `gin_rummy`, `stock4`, `fuzzywuzzy`, remaining `blackjack`/`mahjong` files,
   `tree/base.py`. Watch for failures below the grading thresholds and decide
   whether they're worth a manual investigation (not a manual *fix* of
   generated tests — that's against the rules — but it's fine to adjust the
   prompt/agent logic if a whole class of file is failing systematically).
3. Write `README.md` (max 1 page): strategy, key design decisions (the ones
   above), and limitations encountered (Gemini flakiness, cosmic-ray config
   schema mismatch, the sequential/no-parallelism limitation, the
   self-named-module import collision).
4. Package the submission zip — **exclude `.venv/` and `.env`** before
   zipping (see restrictions in the enunciado: don't ship your API key).
5. Record the video (both partners, ~5 min, the 4 discussion points are in
   the enunciado §3 — the svm `predict`-before-`fit` failure and the Gemini
   flakiness are both genuinely good concrete examples to reference there).

## Rules to keep respecting (don't violate these while iterating)

- Only `gemini-3.1-flash-lite`, no other model.
- Never modify files under `Public_Proyects/` — only write into `Results/`.
- Never hand-edit a generated `test_*.py` file — if something's wrong,
  fix the *agent* (prompt or retry logic), rerun, let the model regenerate.
- The whole `agent.py` invocation (generation + retries + coverage + mutation)
  must fit in 2 minutes, not just the LLM calls.
