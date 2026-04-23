# Judgement Test Suite

Comprehensive test suite for [jvalin17/judgement](https://github.com/jvalin17/judgement). Runs automatically on every push to `main` via GitHub Actions.

## What's here

Exhaustive tests covering edge cases, AI strategies, ML analysis, component rendering, and integration flows. The main repo keeps basic smoke tests for quick local runs.

| Category | Tests | Coverage |
|----------|-------|----------|
| Backend — AI strategies | 32 | All difficulty levels, hand eval, personality |
| Backend — Analysis/Persona | 86 | Fingerprint, cosine similarity, persona matching |
| Backend — Round manager | 60 | Full round lifecycle, bid/play validation |
| Backend — Card play helpers | 33 | would_win, best_winning_card, dump_lowest |
| Backend — Game manager | 25 | Speed, nerf, persona, delays |
| Backend — Smart AI (ML) | 23 | Features, kNN, collector, integration |
| Backend — Edge cases | 22 | Invalid inputs, duplicate names, errors |
| Backend — Engine correctness | 18 | Extra state machine coverage |
| Backend — Info isolation | 15 | AI never sees other hands |
| Backend — Multiplayer | 6 | Full lobby-to-play flow |
| Frontend — Components | 112 | All UI components (common, game, lobby, scoreboard) |
| Frontend — Types | 42 | Card, settings, variant type helpers |

## Running locally

Clone both repos side by side:

```bash
git clone https://github.com/jvalin17/judgement.git
git clone https://github.com/jvalin17/judgement-tests.git
```

Run the test suite:

```bash
cd judgement
./run-test-suite.sh
```

Or manually:

```bash
# Backend
cd judgement
python3 -m pytest ../judgement-tests/backend/ -v

# Frontend
cd judgement/frontend
npx vitest run --config ../../judgement-tests/vitest.config.ts
```

## CI

The main repo has a GitHub Actions workflow (`.github/workflows/test-suite.yml`) that:

1. Checks out both repos
2. Installs dependencies
3. Runs smoke tests (main repo)
4. Runs full test suite (this repo)
5. Reports pass/fail on every commit
