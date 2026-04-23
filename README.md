# Judgement Test Suite & Dev Skills

[![Full Test Suite](https://github.com/jvalin17/judgement/actions/workflows/test-suite.yml/badge.svg)](https://github.com/jvalin17/judgement/actions/workflows/test-suite.yml)

Test suite and Claude Code dev skills for [jvalin17/judgement](https://github.com/jvalin17/judgement) — a trick-taking card game with AI opponents. Runs automatically on every push to `main` via GitHub Actions.

All tests for the Judgement project live here — the main repo has zero test files. This keeps the game repo light and all test coverage in one place, plus dev workflow skills that automate test writing and shipping.

---

## Test Coverage

### Backend (442 tests)

| File | Tests | What it covers |
|------|-------|----------------|
| `test_analysis.py` | 86 | Play style fingerprinting, cosine similarity, persona tier matching |
| `test_round_manager.py` | 60 | Full round lifecycle, bid/play validation, dealer constraints |
| `test_api_rest.py` | 40 | REST endpoints, lobby, quick-join, AI auto-play |
| `test_card_play.py` | 33 | `would_win`, `best_winning_card`, `dump_lowest` helpers |
| `test_ai.py` | 32 | All difficulty levels, hand evaluation, personality system |
| `test_game_manager_unit.py` | 25 | Speed/nerf adjustment, persona assignment, AI delays |
| `test_smart_ai.py` | 23 | Feature extraction, kNN model, decision collector, integration |
| `test_edge_cases.py` | 22 | Invalid inputs, duplicate names, boundary conditions |
| `test_engine_correctness.py` | 18 | Extra state machine coverage |
| `test_validators.py` | 18 | Bid constraints, follow-suit, forbidden bids |
| `test_engine.py` | 17 | Full game flow, state transitions |
| `test_information_isolation.py` | 15 | AI never sees other players' hands |
| `test_websocket_game.py` | 13 | WS connect, two-round play, stuck detect, reconnect |
| `test_round_config.py` | 12 | JSON config loading, bridge tests vs runtime |
| `test_deck.py` | 9 | Deck creation, shuffle, deal |
| `test_scorer.py` | 7 | Scoring formula |
| `test_trick_resolver.py` | 6 | Trick winner logic |
| `test_multiplayer_integration.py` | 6 | Full lobby-to-play multiplayer flow |

### Frontend (232 tests)

| File | Tests | What it covers |
|------|-------|----------------|
| `components/game/` | 62 | BidSelector, OpponentArea, PlayerHand, PlayerInfo, RoundInfo, TrickArea |
| `components/common/` | 37 | Button, Card, CardBack, Modal, SuitIcon, SettingsModal |
| `services/api` | 27 | All REST client functions, error handling, fallback messages |
| `hooks/useGame` | 21 | Reducer: all event types, buffering, replay |
| `components/scoreboard/` | 18 | Scoreboard table, FinalResults with rankings |
| `types/` | 12 | Card display helpers, settings enums, variant labels/limits |
| `context/SettingsContext` | 8 | Settings provider, CSS variable injection, update functions |

---

## Running Locally

Clone both repos side by side:

```bash
git clone https://github.com/jvalin17/judgement.git
git clone https://github.com/jvalin17/judgement-tests.git
```

Run everything (smoke + suite):

```bash
cd judgement
./scripts/run-test-suite.sh
```

Or run just the suite tests manually:

```bash
# Backend suite
cd judgement
JUDGEMENT_REPO=$(pwd) python3 -m pytest ../judgement-tests/backend/ -v

# Frontend suite (copies test files into main repo, runs, cleans up)
# Use run-test-suite.sh — it handles the copy/cleanup automatically
```

### How it works

- **Backend:** `conftest.py` adds the main repo to `sys.path` via `JUDGEMENT_REPO` env var (or auto-detects sibling `judgement/` directory). Tests import directly from `backend.app.*`.
- **Frontend:** Suite test files are copied into the main repo's `frontend/src/` at runtime so that relative imports resolve against the actual source tree. The `run-test-suite.sh` script handles this copy and cleanup.

---

## Claude Code Skills

This repo includes dev workflow skills. To use them, launch Claude Code with this repo as an additional directory:

```bash
claude --add-dir ../judgement-tests
```

| Skill | Command | What it does |
|-------|---------|-------------|
| **write-tests** | `/write-tests` | Analyzes code changes, generates unit and integration tests, adds them to this repo. Run after every feature, fix, or refactor. |
| **test-suite** | `/test-suite` | Clones this repo (if needed), runs all tests (smoke + suite), blocks if anything fails. |
| **ship-checklist** | `/ship-checklist` | Full pre-push checklist: write tests, run suite, update docs, commit. |

### Dev workflow

```
1. Write code in judgement/
2. /write-tests          ← generates tests here
3. /test-suite           ← runs all tests, blocks if any fail
4. /ship-checklist       ← docs, release notes, commit, push
```

Or just run `/ship-checklist` — it calls the other two in order.

### Contributing skills

Add a directory under `.claude/skills/<skill-name>/` with a `SKILL.md` file and open a PR. See existing skills for the format.

---

## CI

The main repo's GitHub Actions workflow ([`test-suite.yml`](https://github.com/jvalin17/judgement/blob/main/.github/workflows/test-suite.yml)) runs on every push to `main`:

1. Checks out both repos
2. Runs all 674 tests (442 backend + 232 frontend)
3. TypeScript check
4. Test summary reported via JUnit XML
