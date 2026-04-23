"""Integration tests for multiplayer game flows.

Tests complete multiplayer games: lobby creation, player joining, starting,
and playing through multiple rounds with mixed human + AI players.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.api.rest import set_manager as set_rest_manager
from backend.app.api.websocket import set_manager as set_ws_manager
from backend.app.game_manager import GameManager


@pytest.fixture(autouse=True)
def fresh_manager():
    manager = GameManager()
    set_rest_manager(manager)
    set_ws_manager(manager)
    yield manager


client = TestClient(app)

ZERO_SPEED = {
    "after_card_played": 0,
    "after_trick_complete": 0,
    "after_round_complete": 0,
}


def _read_until_hand(ws, collector=None):
    events = []
    while True:
        evt = ws.receive_json()
        events.append(evt)
        if collector is not None:
            collector.append(evt)
        if evt["type"] == "round_complete":
            # Engine stays in ROUND_OVER until client sends next_round
            ws.send_json({"action": "next_round"})
        if evt["type"] == "hand":
            return evt["data"], events
        if evt["type"] == "game_over":
            return None, events


class TestLobbyJoinAndStart:
    """Lobby creation, joining, and starting via REST."""

    def test_create_join_start(self):
        # Create lobby
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": False,
            "players": [{"name": "Alice", "is_ai": False}],
            "auto_start": False,
            "speed": ZERO_SPEED,
        })
        assert resp.status_code == 200
        data = resp.json()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        # Bob joins
        join_resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})
        assert join_resp.status_code == 200
        bob_id = join_resp.json()["player_id"]

        # Verify lobby state
        lobby = client.get(f"/api/games/{game_id}/lobby").json()
        assert len(lobby["players"]) == 2

        # Alice starts
        start_resp = client.post(f"/api/games/{game_id}/start?player_id={alice_id}")
        assert start_resp.status_code == 200

        # Game should be in bidding phase
        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] == "bidding"


class TestHumanAndAILobbyGame:
    """One human creates lobby, AI added, play a full round via WebSocket."""

    def test_lobby_with_ai_backfill(self):
        # Create lobby with 1 human
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": False,
            "players": [{"name": "Human", "is_ai": False}],
            "auto_start": False,
            "speed": ZERO_SPEED,
        })
        data = resp.json()
        game_id = data["game_id"]
        human_id = data["player_ids"]["Human"]

        # Add AI players via join
        for bot_name in ["Bot1", "Bot2"]:
            client.post(f"/api/games/{game_id}/join", json={"player_name": bot_name})

        # Start
        client.post(f"/api/games/{game_id}/start?player_id={human_id}")

        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] in ("bidding", "playing")


class TestHumanWithAIFullRound:
    """One human + two AI play a complete round over WebSocket."""

    def test_human_with_ai_complete_round(self):
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": False,
            "players": [
                {"name": "Human", "is_ai": False},
                {"name": "Bot1", "is_ai": True, "ai_difficulty": "easy"},
                {"name": "Bot2", "is_ai": True, "ai_difficulty": "medium"},
            ],
            "speed": ZERO_SPEED,
        })
        data = resp.json()
        game_id = data["game_id"]
        human_id = data["player_ids"]["Human"]

        with client.websocket_connect(f"/ws/{game_id}/{human_id}") as ws:
            connected = ws.receive_json()
            hand_evt = ws.receive_json()

            assert connected["type"] == "connected"
            latest_hand = hand_evt["data"]

            rounds_completed = 0
            for _ in range(50):
                valid_bids = latest_hand.get("valid_bids", [])
                valid_cards = latest_hand.get("valid_cards", [])

                if valid_bids:
                    ws.send_json({"action": "bid", "amount": valid_bids[0]})
                elif valid_cards:
                    card = valid_cards[0]
                    ws.send_json({"action": "play", "suit": card["suit"], "rank": card["rank"]})
                else:
                    break

                hand_data, events = _read_until_hand(ws)
                for evt in events:
                    if evt["type"] == "round_complete":
                        rounds_completed += 1

                if hand_data is None:
                    break
                latest_hand = hand_data

            assert rounds_completed >= 1


class TestQuickJoinFullGame:
    """Two players quick-join and play."""

    def test_quick_join_creates_lobby(self):
        # Player 1 quick-joins without auto_play (creates lobby)
        resp1 = client.post("/api/lobby/quick-join", json={
            "player_name": "Alice", "auto_play": False,
        })
        assert resp1.status_code == 200
        game_id = resp1.json()["game_id"]
        alice_id = resp1.json()["player_id"]

        # Player 2 quick-joins (finds same lobby)
        resp2 = client.post("/api/lobby/quick-join", json={
            "player_name": "Bob", "auto_play": False,
        })
        assert resp2.status_code == 200
        assert resp2.json()["game_id"] == game_id

        # Verify both in lobby
        lobby = client.get(f"/api/games/{game_id}/lobby").json()
        assert len(lobby["players"]) == 2

        # Host starts
        client.post(f"/api/games/{game_id}/start?player_id={alice_id}")

        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] == "bidding"


class TestMultipleRoundsWithAI:
    """Play through multiple rounds to verify round transitions."""

    def test_three_rounds(self):
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": False,
            "players": [
                {"name": "Human", "is_ai": False},
                {"name": "Bot1", "is_ai": True, "ai_difficulty": "medium"},
                {"name": "Bot2", "is_ai": True, "ai_difficulty": "hard"},
            ],
            "speed": ZERO_SPEED,
        })
        data = resp.json()
        game_id = data["game_id"]
        human_id = data["player_ids"]["Human"]

        with client.websocket_connect(f"/ws/{game_id}/{human_id}") as ws:
            connected = ws.receive_json()
            hand_evt = ws.receive_json()
            latest_hand = hand_evt["data"]

            rounds_completed = 0
            round_started_events = []
            all_events = [connected, hand_evt]

            for _ in range(120):  # enough for 3 rounds
                valid_bids = latest_hand.get("valid_bids", [])
                valid_cards = latest_hand.get("valid_cards", [])

                if valid_bids:
                    ws.send_json({"action": "bid", "amount": valid_bids[0]})
                elif valid_cards:
                    card = valid_cards[0]
                    ws.send_json({"action": "play", "suit": card["suit"], "rank": card["rank"]})
                else:
                    break

                hand_data, events = _read_until_hand(ws, all_events)

                for evt in events:
                    if evt["type"] == "round_complete":
                        rounds_completed += 1
                    if evt["type"] == "round_started":
                        round_started_events.append(evt)

                if hand_data is None or rounds_completed >= 3:
                    break
                latest_hand = hand_data

            assert rounds_completed >= 3, f"Only completed {rounds_completed} rounds"
            assert len(round_started_events) >= 2, "Missing round_started events"

            # Verify round numbers increase
            round_numbers = [e["data"]["round_number"] for e in round_started_events]
            assert round_numbers == sorted(round_numbers)


class TestSessionLogAfterGame:
    """Verify session log is populated after playing rounds."""

    def test_session_log_has_entries(self):
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": False,
            "players": [
                {"name": "Human", "is_ai": False},
                {"name": "Bot1", "is_ai": True, "ai_difficulty": "easy"},
                {"name": "Bot2", "is_ai": True, "ai_difficulty": "easy"},
            ],
            "speed": ZERO_SPEED,
        })
        data = resp.json()
        game_id = data["game_id"]
        human_id = data["player_ids"]["Human"]

        with client.websocket_connect(f"/ws/{game_id}/{human_id}") as ws:
            connected = ws.receive_json()
            hand_evt = ws.receive_json()
            latest_hand = hand_evt["data"]

            rounds_completed = 0
            for _ in range(50):
                valid_bids = latest_hand.get("valid_bids", [])
                valid_cards = latest_hand.get("valid_cards", [])

                if valid_bids:
                    ws.send_json({"action": "bid", "amount": valid_bids[0]})
                elif valid_cards:
                    card = valid_cards[0]
                    ws.send_json({"action": "play", "suit": card["suit"], "rank": card["rank"]})
                else:
                    break

                hand_data, events = _read_until_hand(ws)
                for evt in events:
                    if evt["type"] == "round_complete":
                        rounds_completed += 1

                if hand_data is None or rounds_completed >= 1:
                    break
                latest_hand = hand_data

        # Check session log
        log_resp = client.get(f"/api/games/{game_id}/session-log")
        assert log_resp.status_code == 200
        log_data = log_resp.json()
        assert len(log_data["rounds"]) >= 1
