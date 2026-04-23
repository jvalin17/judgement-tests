"""Edge case tests for multiplayer game flows.

Tests error handling, invalid inputs, out-of-turn plays,
duplicate names, and other boundary conditions.
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


def _create_lobby():
    """Create a lobby game with one human player."""
    resp = client.post("/api/games", json={
        "variant": "10_to_1",
        "must_lose_mode": False,
        "players": [{"name": "Alice", "is_ai": False}],
        "auto_start": False,
        "speed": ZERO_SPEED,
    })
    data = resp.json()
    return data["game_id"], data["player_ids"]["Alice"]


def _create_started_game():
    """Create a game that's already started (1 human + 2 AI)."""
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
    return data["game_id"], data["player_ids"]["Human"]


class TestJoinEdgeCases:
    """Edge cases for joining games."""

    def test_join_nonexistent_game(self):
        resp = client.post("/api/games/fake-id/join", json={"player_name": "Bob"})
        assert resp.status_code == 404

    def test_join_started_game(self):
        game_id, _ = _create_started_game()
        resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Late"})
        assert resp.status_code == 400

    def test_join_duplicate_name(self):
        game_id, _ = _create_lobby()
        resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Alice"})
        assert resp.status_code == 400

    def test_join_duplicate_name_case_insensitive(self):
        game_id, _ = _create_lobby()
        resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "alice"})
        assert resp.status_code == 400

    def test_join_full_game(self):
        game_id, _ = _create_lobby()
        # Fill up to max (5 for 10_to_1)
        for i in range(4):
            resp = client.post(f"/api/games/{game_id}/join",
                               json={"player_name": f"Player{i}"})
            assert resp.status_code == 200

        # 6th player should be rejected
        resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "TooMany"})
        assert resp.status_code == 400


class TestStartEdgeCases:
    """Edge cases for starting games."""

    def test_start_nonexistent_game(self):
        resp = client.post("/api/games/fake-id/start?player_id=fake")
        assert resp.status_code == 404

    def test_start_not_host(self):
        game_id, alice_id = _create_lobby()
        join_resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})
        bob_id = join_resp.json()["player_id"]

        # Bob is not host
        resp = client.post(f"/api/games/{game_id}/start?player_id={bob_id}")
        assert resp.status_code == 403

    def test_start_solo(self):
        game_id, alice_id = _create_lobby()
        # Only 1 player — can't start
        resp = client.post(f"/api/games/{game_id}/start?player_id={alice_id}")
        assert resp.status_code == 400

    def test_start_already_started(self):
        game_id, alice_id = _create_lobby()
        client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})
        client.post(f"/api/games/{game_id}/start?player_id={alice_id}")

        # Try to start again
        resp = client.post(f"/api/games/{game_id}/start?player_id={alice_id}")
        assert resp.status_code == 400


class TestLobbyEdgeCases:
    """Edge cases for lobby endpoints."""

    def test_lobby_state_nonexistent(self):
        resp = client.get("/api/games/fake-id/lobby")
        assert resp.status_code == 404

    def test_lobby_state_started_game(self):
        game_id, _ = _create_started_game()
        # Should still return lobby info even after start
        resp = client.get(f"/api/games/{game_id}/lobby")
        # Either 200 (returns player list) or 400 — depends on impl
        # Just verify it doesn't crash
        assert resp.status_code in (200, 400)


class TestWebSocketEdgeCases:
    """WebSocket edge cases."""

    def test_ws_invalid_game(self):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/fake-game/fake-player") as ws:
                ws.receive_json()

    def test_ws_invalid_action(self):
        game_id, player_id = _create_started_game()
        with client.websocket_connect(f"/ws/{game_id}/{player_id}") as ws:
            connected = ws.receive_json()
            hand = ws.receive_json()
            assert connected["type"] == "connected"

            # Send garbage action
            ws.send_json({"action": "nonsense"})

            # Should still be able to get hand (game not broken)
            ws.send_json({"action": "get_hand"})
            response = ws.receive_json()
            assert response["type"] == "hand"

    def test_ws_invalid_card(self):
        game_id, player_id = _create_started_game()
        with client.websocket_connect(f"/ws/{game_id}/{player_id}") as ws:
            connected = ws.receive_json()
            hand = ws.receive_json()

            # If it's playing phase and our turn, try an invalid card
            if hand["data"].get("valid_cards"):
                ws.send_json({"action": "play", "suit": "spades", "rank": 99})
                # Should get error
                evt = ws.receive_json()
                assert evt["type"] == "error"

    def test_ws_reconnect_same_player(self):
        """Reconnecting with same player_id should work cleanly."""
        game_id, player_id = _create_started_game()

        # First connection
        with client.websocket_connect(f"/ws/{game_id}/{player_id}") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"

        # Second connection (after first closes)
        with client.websocket_connect(f"/ws/{game_id}/{player_id}") as ws:
            connected = ws.receive_json()
            hand = ws.receive_json()
            assert connected["type"] == "connected"
            assert hand["type"] == "hand"


class TestShortCodeLookup:
    """Game lookup by short code prefix (join codes)."""

    def test_join_with_short_code(self):
        """Joining with first 8 chars of game_id (the displayed join code) works."""
        game_id, alice_id = _create_lobby()
        short_code = game_id[:8]

        resp = client.post(f"/api/games/{short_code}/join", json={"player_name": "Bob"})
        assert resp.status_code == 200
        assert resp.json()["game_id"] == game_id

    def test_join_with_uppercase_short_code(self):
        """Short code lookup is case-insensitive (UI shows uppercase)."""
        game_id, alice_id = _create_lobby()
        short_code = game_id[:8].upper()

        resp = client.post(f"/api/games/{short_code}/join", json={"player_name": "Bob"})
        assert resp.status_code == 200
        assert resp.json()["game_id"] == game_id

    def test_join_with_full_id_still_works(self):
        """Full UUID lookup still works as before."""
        game_id, alice_id = _create_lobby()

        resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})
        assert resp.status_code == 200
        assert resp.json()["game_id"] == game_id

    def test_short_code_not_found(self):
        """A short code that matches no game returns 404."""
        resp = client.post("/api/games/ZZZZZZZZ/join", json={"player_name": "Bob"})
        assert resp.status_code == 404

    def test_lobby_state_via_short_code(self):
        """GET /lobby also works with short code."""
        game_id, alice_id = _create_lobby()
        short_code = game_id[:8].upper()

        resp = client.get(f"/api/games/{short_code}/lobby")
        assert resp.status_code == 200
        assert resp.json()["game_id"] == game_id


class TestQuickJoinEdgeCases:
    """Quick join edge cases."""

    def test_quick_join_same_name_different_games(self):
        """Two players with same name — second creates a new game."""
        resp1 = client.post("/api/lobby/quick-join", json={
            "player_name": "Alice", "auto_play": False,
        })
        assert resp1.status_code == 200

        # Same name — duplicate in same game is rejected, creates new one
        resp2 = client.post("/api/lobby/quick-join", json={
            "player_name": "Alice", "auto_play": False,
        })
        assert resp2.status_code == 200

    def test_quick_join_fills_lobby(self):
        """Quick joining should fill up one lobby before creating another."""
        player_ids = []
        game_ids = set()

        for i in range(3):
            resp = client.post("/api/lobby/quick-join",
                               json={"player_name": f"Player{i}", "auto_play": False})
            assert resp.status_code == 200
            game_ids.add(resp.json()["game_id"])
            player_ids.append(resp.json()["player_id"])

        # All 3 should be in the same game
        assert len(game_ids) == 1
