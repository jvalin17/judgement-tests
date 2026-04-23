# Test Audit

Last updated: 2026-04-23

**674 tests** (442 backend + 232 frontend) covering **216 public methods/exports**.

| Layer | Methods | Tested | Untested | Coverage |
|-------|---------|--------|----------|----------|
| Backend | 135 | 118 | 17 | 87.4% |
| Frontend | 81 | 55 | 26 | 67.9% |
| **Total** | **216** | **173** | **43** | **80.1%** |

---

## Backend Coverage (135 methods, 87.4%)

### Fully Tested (100%)

| File | Methods | Test File |
|------|---------|-----------|
| `game/trick_resolver.py` | 1 | `test_trick_resolver.py` |
| `game/scorer.py` | 1 | `test_scorer.py` |
| `game/round_manager.py` | 8 | `test_round_manager.py` |
| `game/engine.py` | 11 | `test_engine.py`, `test_engine_correctness.py` |
| `game/round_config_loader.py` | 1 | `test_round_config.py` |
| `game/deck.py` | 3 | `test_deck.py` |
| `game/validators.py` | 4 | `test_validators.py` |
| `models/game.py` | 2 | `test_round_config.py` |
| `ai/base.py` | 2 | `test_ai.py` |
| `ai/card_play.py` | 4 | `test_card_play.py` |
| `ai/easy.py` | 2 | `test_ai.py` |
| `ai/medium.py` | 2 | `test_ai.py` |
| `ai/hard.py` | 2 | `test_ai.py` |
| `ai/smart_hard.py` | 2 | `test_smart_ai.py` |
| `ai/hand_evaluator.py` | 1 | `test_ai.py` |
| `ai/personality.py` | 1 | `test_ai.py` |
| `ai/opponent_model.py` | 5 | `test_ai.py` |
| `ml/utils.py` | 2 | `test_analysis.py`, `test_information_isolation.py` |
| `ml/learning/neighbor_model.py` | 4 | `test_smart_ai.py` |
| `ml/learning/features.py` | 4 | `test_smart_ai.py`, `test_information_isolation.py` |
| `ml/learning/decision_collector.py` | 6 | `test_smart_ai.py`, `test_information_isolation.py` |
| `ml/analysis/fingerprint.py` | 2 | `test_analysis.py` |
| `ml/analysis/persona_loader.py` | 3 | `test_analysis.py` |
| `ml/analysis/persona_match.py` | 4 | `test_analysis.py` |
| `api/rest.py` | 13 | `test_api_rest.py`, `test_edge_cases.py`, `test_multiplayer_integration.py` |
| `api/websocket.py` | 5 | `test_websocket_game.py` |
| `game_manager.py` | 13 | `test_api_rest.py`, `test_game_manager_unit.py`, `test_multiplayer_integration.py` |

### Partially Tested

| File | Tested | Total | Untested Methods |
|------|--------|-------|------------------|
| `models/events.py` | 14 | 18 | `player_left_event`, `auto_start_countdown_event`, `game_starting_event`, `mascot_persona_awarded_event` |
| `ml/data_store.py` | 3 | 4 | `get_default_store` |

### Untested (0%)

| File | Methods | What's Missing |
|------|---------|----------------|
| `models/card.py` | 3 | `__hash__`, `__eq__`, `__str__` (implicitly exercised but no dedicated tests) |
| `api/update.py` | 4 | `get_version`, `get_update_status`, `check_for_update`, `apply_update` |
| `api/data_sharing.py` | 5 | `share_preview`, `share_data`, `share_status`, `check_community_data`, `download_community_data` |
| `main.py` | 2 | `health_check`, `serve_spa` |

---

## Frontend Coverage (81 exports, 67.9%)

### Fully Tested

| File | Exports | Test File |
|------|---------|-----------|
| `types/card.ts` | 8 | `card.test.ts` |
| `types/settings.ts` | 9 | `settings.test.ts` |
| `services/api.ts` | 20 | `api.test.ts` |
| `hooks/useGame.ts` | 1 | `useGame.test.ts` |
| `context/SettingsContext.tsx` | 2 | `SettingsContext.test.tsx` |
| `components/common/Card.tsx` | 2 | `Card.test.tsx` |
| `components/common/Button.tsx` | 1 | `Button.test.tsx` |
| `components/common/Modal.tsx` | 1 | `Modal.test.tsx` |
| `components/common/SuitIcon.tsx` | 1 | `SuitIcon.test.tsx` |
| `components/common/SettingsModal.tsx` | 1 | `SettingsModal.test.tsx` |
| `components/game/BidSelector.tsx` | 1 | `BidSelector.test.tsx` |
| `components/game/PlayerHand.tsx` | 1 | `PlayerHand.test.tsx` |
| `components/game/TrickArea.tsx` | 1 | `TrickArea.test.tsx` |
| `components/game/PlayerInfo.tsx` | 1 | `PlayerInfo.test.tsx` |
| `components/game/RoundInfo.tsx` | 1 | `RoundInfo.test.tsx` |
| `components/game/OpponentArea.tsx` | 1 | `OpponentArea.test.tsx` |
| `components/scoreboard/Scoreboard.tsx` | 1 | `Scoreboard.test.tsx` |
| `components/scoreboard/FinalResults.tsx` | 1 | `FinalResults.test.tsx` |

### Untested

**High priority (logic/behavior):**

| File | Export | Why it matters |
|------|--------|----------------|
| `types/game.ts` | `isMyTurn` | Function with conditional logic |
| `services/websocket.ts` | `GameWebSocket` | Reconnect logic, message handling |
| `hooks/useWebSocket.ts` | `useWebSocket` | WS lifecycle management |
| `context/GameContext.tsx` | `GameProvider`, `useGameContext` | Wiring layer for all components |
| `components/game/GameBoard.tsx` | `GameBoard` | Main game container |
| `components/game/OpponentArea.tsx` | `StatBadge`, `getAvatarColor`, `getInitials` | Helper functions with logic |
| `components/lobby/PlayerSetup.tsx` | `PlayerSetup`, `createDefaultAiPlayer`, `createDefaultHumanPlayer` | Game creation forms |

**Medium priority (UI components):**

| File | Export |
|------|--------|
| `components/lobby/GameLobby.tsx` | `GameLobby` |
| `components/lobby/WaitingRoom.tsx` | `WaitingRoom` |
| `components/lobby/JoinGameForm.tsx` | `JoinGameForm` |
| `components/lobby/QuickPlayForm.tsx` | `QuickPlayForm` |
| `components/lobby/VariantSelector.tsx` | `VariantSelector` |
| `components/common/SuitSvg.tsx` | `SuitSvg` |
| `components/common/FaceCardArt.tsx` | `FaceCardArt` |

**Low priority (constants, no logic):**

| File | Export |
|------|--------|
| `types/game.ts` | `PlayerType`, `AIDifficulty`, `VARIANT_LABELS`, `VARIANT_MAX_PLAYERS` |
| `types/events.ts` | `ClientAction` |
| `services/websocket.ts` | `ConnectionStatus` |
| `services/audio.ts` | `playVictorySound`, `playGoodGameSound` |
| `components/common/SettingsModal.tsx` | `CARD_BACK_DESIGN_CLASS` |
| `components/common/pipLayouts.ts` | `PIP_LAYOUTS` |

---

## Test File Index

### Backend (442 tests)

| File | Tests | Coverage Area |
|------|-------|---------------|
| `test_analysis.py` | 86 | Fingerprinting, cosine similarity, persona tiers |
| `test_round_manager.py` | 60 | Round lifecycle, bid/play validation, dealer constraints |
| `test_api_rest.py` | 40 | REST endpoints, lobby, quick-join, AI auto-play |
| `test_card_play.py` | 33 | `would_win`, `best_winning_card`, `dump_lowest` |
| `test_ai.py` | 32 | All difficulty levels, hand eval, personality |
| `test_game_manager_unit.py` | 25 | Speed/nerf, persona assignment, AI delays |
| `test_smart_ai.py` | 23 | Features, kNN, collector, integration |
| `test_edge_cases.py` | 22 | Invalid inputs, duplicate names, boundaries |
| `test_engine_correctness.py` | 18 | Extra state machine coverage |
| `test_validators.py` | 18 | Bid constraints, follow-suit, forbidden bids |
| `test_engine.py` | 17 | Full game flow, state transitions |
| `test_information_isolation.py` | 15 | AI never sees other hands |
| `test_websocket_game.py` | 13 | WS connect, play, stuck detect, reconnect |
| `test_round_config.py` | 12 | JSON config loading, bridge tests |
| `test_deck.py` | 9 | Deck creation, shuffle, deal |
| `test_scorer.py` | 7 | Scoring formula |
| `test_trick_resolver.py` | 6 | Trick winner logic |
| `test_multiplayer_integration.py` | 6 | Lobby-to-play multiplayer flow |

### Frontend (232 tests)

| File | Tests | Coverage Area |
|------|-------|---------------|
| `components/game/*` | 62 | BidSelector, OpponentArea, PlayerHand, PlayerInfo, RoundInfo, TrickArea |
| `components/common/*` | 37 | Button, Card, CardBack, Modal, SuitIcon, SettingsModal |
| `services/api.test.ts` | 27 | All REST client functions, error handling |
| `hooks/useGame.test.ts` | 21 | Reducer: all event types, buffering, replay |
| `components/scoreboard/*` | 18 | Scoreboard, FinalResults |
| `types/*` | 12 | Card helpers, settings enums, variant labels |
| `context/SettingsContext.test.tsx` | 8 | Provider, CSS variables, update functions |

---

## Recommended Next Tests

To reach **90%+ coverage**, prioritize:

1. **`api/update.py`** (4 methods) — mock GitHub API responses, test version comparison
2. **`api/data_sharing.py`** (5 methods) — mock file I/O and GitHub API
3. **Lobby components** (6 components) — GameLobby, WaitingRoom, JoinGameForm, QuickPlayForm, PlayerSetup, VariantSelector
4. **`GameWebSocket`** — reconnect logic, message parsing, error handling
5. **`GameBoard`** — renders correct phase, passes props to children
6. **`GameContext`** — provider wiring, hook usage outside provider
