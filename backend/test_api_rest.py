import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.rest import set_manager
from backend.app.game_manager import GameManager


@pytest.fixture(autouse=True)
def fresh_manager():
    manager = GameManager()
    set_manager(manager)
    yield manager


client = TestClient(app)


def _create_game(players=None, variant="10_to_1", must_lose=False):
    if players is None:
        players = [
            {"name": "Alice", "is_ai": False},
            {"name": "Bot1", "is_ai": True, "ai_difficulty": "easy"},
            {"name": "Bot2", "is_ai": True, "ai_difficulty": "medium"},
        ]
    return client.post("/api/games", json={
        "variant": variant,
        "must_lose_mode": must_lose,
        "players": players,
    })


class TestRouteRegistration:
    """Verify all expected routes are registered on the app.

    Catches: server started with wrong module path, missing router includes,
    or routers accidentally removed from main.py.
    """

    EXPECTED_ROUTES = [
        # Core game endpoints
        "/api/games",
        "/api/games/{game_id}",
        "/api/games/{game_id}/hand/{player_id}",
        "/api/games/{game_id}/bid",
        "/api/games/{game_id}/play",
        "/api/games/{game_id}/session-log",
        # Multiplayer endpoints
        "/api/games/{game_id}/join",
        "/api/games/{game_id}/start",
        "/api/games/{game_id}/lobby",
        # Lobby listing / quick-join
        "/api/lobby",
        "/api/lobby/quick-join",
        # WebSocket
        "/ws/{game_id}/{player_id}",
        # Health
        "/health",
    ]

    def test_all_routes_registered(self):
        registered = set()
        for route in app.routes:
            if hasattr(route, "path"):
                registered.add(route.path)
            if hasattr(route, "routes"):
                for sub in route.routes:
                    if hasattr(sub, "path"):
                        registered.add(sub.path)

        missing = [r for r in self.EXPECTED_ROUTES if r not in registered]
        assert not missing, f"Routes missing from app: {missing}"

    def test_lobby_quick_join_reachable(self):
        """Quick-join must return 200, not 404 — catches missing lobby_router."""
        resp = client.post("/api/lobby/quick-join", json={"player_name": "RouteTest"})
        assert resp.status_code == 200

    def test_lobby_list_reachable(self):
        """Lobby list must return 200, not 404."""
        resp = client.get("/api/lobby")
        assert resp.status_code == 200


class TestCreateGame:
    def test_create_game_success(self):
        resp = _create_game()
        assert resp.status_code == 200
        data = resp.json()
        assert "game_id" in data
        assert "Alice" in data["player_ids"]
        assert "Bot1" in data["player_ids"]

    def test_create_game_too_few_players(self):
        resp = _create_game(players=[{"name": "Solo"}])
        assert resp.status_code == 400

    def test_create_game_must_lose(self):
        resp = _create_game(must_lose=True)
        assert resp.status_code == 200


class TestGetGameState:
    def test_get_state(self):
        create_resp = _create_game()
        game_id = create_resp.json()["game_id"]

        resp = client.get(f"/api/games/{game_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == game_id
        # AI players should have already bid (easy + medium), Alice's turn
        assert data["phase"] in ("bidding", "playing", "round_over")

    def test_get_nonexistent_game(self):
        resp = client.get("/api/games/nonexistent")
        assert resp.status_code == 404


class TestGetPlayerHand:
    def test_get_hand(self):
        create_resp = _create_game()
        data = create_resp.json()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        resp = client.get(f"/api/games/{game_id}/hand/{alice_id}")
        assert resp.status_code == 200
        hand_data = resp.json()
        assert "hand" in hand_data
        assert len(hand_data["hand"]) == 10  # first round is 10 cards


class TestBidAndPlay:
    def test_full_human_turn(self):
        create_resp = _create_game()
        data = create_resp.json()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        # Get state to see if it's Alice's turn to bid
        state = client.get(f"/api/games/{game_id}").json()

        if state["phase"] == "bidding" and state["current_player_id"] == alice_id:
            # Get valid bids
            hand_resp = client.get(f"/api/games/{game_id}/hand/{alice_id}").json()
            valid_bids = hand_resp["valid_bids"]
            assert len(valid_bids) > 0

            # Place bid
            bid_resp = client.post(f"/api/games/{game_id}/bid", json={
                "player_id": alice_id,
                "amount": valid_bids[0],
            })
            assert bid_resp.json()["success"] is True

        # After bidding, check if it's playing phase and Alice's turn
        state = client.get(f"/api/games/{game_id}").json()
        if state["phase"] == "playing" and state["current_player_id"] == alice_id:
            hand_resp = client.get(f"/api/games/{game_id}/hand/{alice_id}").json()
            valid_cards = hand_resp["valid_cards"]
            assert len(valid_cards) > 0

            card = valid_cards[0]
            play_resp = client.post(f"/api/games/{game_id}/play", json={
                "player_id": alice_id,
                "suit": card["suit"],
                "rank": card["rank"],
            })
            assert play_resp.json()["success"] is True

    def test_invalid_bid(self):
        create_resp = _create_game()
        data = create_resp.json()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        # Try bidding out of turn or invalid amount
        resp = client.post(f"/api/games/{game_id}/bid", json={
            "player_id": "nonexistent",
            "amount": 99,
        })
        assert resp.json()["success"] is False


class TestSessionLog:
    def test_session_log_exists(self):
        create_resp = _create_game()
        game_id = create_resp.json()["game_id"]

        resp = client.get(f"/api/games/{game_id}/session-log")
        assert resp.status_code == 200
        log = resp.json()
        assert log["game_id"] == game_id
        assert len(log["players"]) == 3


class TestAIAutoPlay:
    def test_ai_plays_automatically(self):
        """When game starts with AI players, they bid/play on their own turns."""
        create_resp = _create_game()
        data = create_resp.json()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        state = client.get(f"/api/games/{game_id}").json()
        # AI should have already taken their turns, so either it's Alice's turn
        # or AI has played through everything
        if state["current_player_id"] == alice_id:
            # Good — AI played, now waiting for human
            assert state["phase"] in ("bidding", "playing")
        else:
            # AI might still be going in a later phase
            assert state["phase"] in ("bidding", "playing", "round_over", "game_over")


# --- Phase 1: Join / Start / Lobby ---


def _create_lobby_game(players=None, variant="10_to_1"):
    """Create a game with auto_start=False (stays in LOBBY phase)."""
    if players is None:
        players = [{"name": "Alice", "is_ai": False}]
    return client.post("/api/games", json={
        "variant": variant,
        "must_lose_mode": False,
        "players": players,
        "auto_start": False,
    })


class TestCreateGameNoAutoStart:
    def test_create_stays_in_lobby(self):
        resp = _create_lobby_game()
        assert resp.status_code == 200
        data = resp.json()
        game_id = data["game_id"]

        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] == "lobby"

    def test_auto_start_default_true(self):
        """Default auto_start=True still works (backwards compat)."""
        resp = _create_game()
        assert resp.status_code == 200
        game_id = resp.json()["game_id"]
        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] in ("bidding", "playing", "round_over")

    def test_create_with_ai_auto_start(self):
        """Mixed human+AI with auto_start=True starts immediately."""
        resp = _create_game()
        assert resp.status_code == 200
        game_id = resp.json()["game_id"]
        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] != "lobby"


class TestJoinGame:
    def test_join_game(self):
        create_resp = _create_lobby_game()
        game_id = create_resp.json()["game_id"]

        resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})
        assert resp.status_code == 200
        data = resp.json()
        assert "player_id" in data
        assert data["game_id"] == game_id

        # Bob should appear in game state
        state = client.get(f"/api/games/{game_id}").json()
        player_names = [p["name"] for p in state["players"]]
        assert "Bob" in player_names


class TestStartGame:
    def test_start_game(self):
        create_resp = _create_lobby_game()
        data = create_resp.json()
        game_id = data["game_id"]
        host_id = data["player_ids"]["Alice"]

        # Join a second player
        client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})

        # Host starts
        resp = client.post(f"/api/games/{game_id}/start?player_id={host_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] == "bidding"

    def test_start_game_not_host(self):
        create_resp = _create_lobby_game()
        game_id = create_resp.json()["game_id"]

        join_resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})
        bob_id = join_resp.json()["player_id"]

        resp = client.post(f"/api/games/{game_id}/start?player_id={bob_id}")
        assert resp.status_code == 403

    def test_start_game_not_enough_players(self):
        create_resp = _create_lobby_game()
        data = create_resp.json()
        game_id = data["game_id"]
        host_id = data["player_ids"]["Alice"]

        resp = client.post(f"/api/games/{game_id}/start?player_id={host_id}")
        assert resp.status_code == 400
        assert "at least 2" in resp.json()["detail"].lower()

    def test_start_game_already_started(self):
        create_resp = _create_game()
        data = create_resp.json()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        resp = client.post(f"/api/games/{game_id}/start?player_id={alice_id}")
        assert resp.status_code == 400
        assert "already started" in resp.json()["detail"].lower()


class TestGetLobbyState:
    def test_get_lobby(self):
        create_resp = _create_lobby_game()
        data = create_resp.json()
        game_id = data["game_id"]

        resp = client.get(f"/api/games/{game_id}/lobby")
        assert resp.status_code == 200
        lobby = resp.json()
        assert lobby["game_id"] == game_id
        assert lobby["phase"] == "lobby"
        assert lobby["variant"] == "10_to_1"
        assert len(lobby["players"]) == 1
        assert lobby["max_players"] == 5

    def test_lobby_shows_joined_player(self):
        create_resp = _create_lobby_game()
        game_id = create_resp.json()["game_id"]

        client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})

        lobby = client.get(f"/api/games/{game_id}/lobby").json()
        player_names = [p["name"] for p in lobby["players"]]
        assert "Alice" in player_names
        assert "Bob" in player_names
        assert len(lobby["players"]) == 2

    def test_lobby_has_host_id(self):
        create_resp = _create_lobby_game()
        data = create_resp.json()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        lobby = client.get(f"/api/games/{game_id}/lobby").json()
        assert lobby["host_player_id"] == alice_id


# --- Phase 3: Lobby listing / Quick-join ---


def _create_public_lobby(player_name="Alice", variant="10_to_1"):
    """Create a public lobby game."""
    resp = client.post("/api/games", json={
        "variant": variant,
        "must_lose_mode": False,
        "players": [{"name": player_name, "is_ai": False}],
        "auto_start": False,
        "is_public": True,
    })
    assert resp.status_code == 200
    return resp.json()


class TestLobbyList:
    def test_lobby_list_empty(self):
        resp = client.get("/api/lobby")
        assert resp.status_code == 200
        assert resp.json()["games"] == []

    def test_lobby_list_public_games(self):
        _create_public_lobby()
        resp = client.get("/api/lobby")
        games = resp.json()["games"]
        assert len(games) == 1
        assert games[0]["host_name"] == "Alice"
        assert games[0]["variant"] == "10_to_1"
        assert games[0]["player_count"] == 1

    def test_lobby_list_excludes_private(self):
        _create_lobby_game()  # private by default
        resp = client.get("/api/lobby")
        assert len(resp.json()["games"]) == 0

    def test_lobby_list_excludes_started(self):
        data = _create_public_lobby()
        game_id = data["game_id"]
        alice_id = data["player_ids"]["Alice"]

        # Join and start
        client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})
        client.post(f"/api/games/{game_id}/start?player_id={alice_id}")

        resp = client.get("/api/lobby")
        assert len(resp.json()["games"]) == 0

    def test_lobby_list_game_info(self):
        _create_public_lobby(variant="8_down_up")
        resp = client.get("/api/lobby")
        game = resp.json()["games"][0]
        assert game["variant"] == "8_down_up"
        assert game["max_players"] == 6
        assert game["must_lose_mode"] is False


class TestQuickJoin:
    def test_quick_join_auto_play_starts_immediately(self):
        """Default quick-join fills with AI and starts — player can play right away."""
        resp = client.post("/api/lobby/quick-join", json={"player_name": "Alice"})
        assert resp.status_code == 200
        data = resp.json()
        assert "player_id" in data
        assert "game_id" in data

        # Game should be started (bidding/playing), not in lobby
        state = client.get(f"/api/games/{data['game_id']}").json()
        assert state["phase"] in ("bidding", "playing")
        assert len(state["players"]) >= 3  # human + AI backfill

    def test_quick_join_no_auto_play_stays_in_lobby(self):
        """With auto_play=False, creates a lobby and waits."""
        resp = client.post("/api/lobby/quick-join", json={
            "player_name": "Alice", "auto_play": False,
        })
        assert resp.status_code == 200

        # Should appear in lobby list (not started)
        lobby = client.get("/api/lobby").json()
        assert len(lobby["games"]) == 1

    def test_quick_join_finds_existing(self):
        _create_public_lobby(player_name="Alice")

        resp = client.post("/api/lobby/quick-join", json={"player_name": "Bob"})
        assert resp.status_code == 200

        # Should have joined the existing game, not created a new one
        lobby = client.get("/api/lobby").json()
        assert len(lobby["games"]) == 1
        assert lobby["games"][0]["player_count"] == 2

    def test_quick_join_prefers_fullest(self):
        # Create two public lobbies
        data1 = _create_public_lobby(player_name="Alice")
        data2 = _create_public_lobby(player_name="Charlie")

        # Add a second player to game 2
        client.post(f"/api/games/{data2['game_id']}/join", json={"player_name": "Dave"})

        # Quick-join should pick game 2 (has more players)
        resp = client.post("/api/lobby/quick-join", json={"player_name": "Eve"})
        assert resp.status_code == 200
        assert resp.json()["game_id"] == data2["game_id"]

    def test_quick_join_variant_filter(self):
        _create_public_lobby(player_name="Alice", variant="10_to_1")

        # Quick-join for 8_down_up — should NOT match, creates new lobby
        resp = client.post("/api/lobby/quick-join", json={
            "player_name": "Bob", "variant": "8_down_up", "auto_play": False,
        })
        assert resp.status_code == 200
        # Created a new game since no 8_down_up lobby exists
        lobby = client.get("/api/lobby").json()
        assert len(lobby["games"]) == 2

    def test_quick_join_duplicate_name_skips(self):
        data = _create_public_lobby(player_name="Alice")

        # Quick-join with same name — should create new game, not fail
        resp = client.post("/api/lobby/quick-join", json={
            "player_name": "Alice", "auto_play": False,
        })
        assert resp.status_code == 200
        assert resp.json()["game_id"] != data["game_id"]


class TestSinglePlayerLobbyCreation:
    """Verify that creating a multiplayer room with 1 player works when auto_start=False."""

    def test_single_player_lobby_succeeds(self):
        """A single human can create a lobby (auto_start=False) — no 2-player minimum."""
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": False,
            "players": [{"name": "Host", "is_ai": False}],
            "auto_start": False,
        })
        assert resp.status_code == 200
        assert "game_id" in resp.json()

    def test_single_player_auto_start_fails(self):
        """A single player with auto_start=True (default) is rejected — needs 2+ to start."""
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": False,
            "players": [{"name": "Solo", "is_ai": False}],
        })
        assert resp.status_code == 400

    def test_lobby_create_join_start_flow(self):
        """Full multiplayer flow: host creates lobby → friend joins → host starts."""
        # Host creates room
        create_resp = client.post("/api/games", json={
            "variant": "8_down_up",
            "must_lose_mode": False,
            "players": [{"name": "Host", "is_ai": False}],
            "auto_start": False,
        })
        assert create_resp.status_code == 200
        data = create_resp.json()
        game_id = data["game_id"]
        host_id = data["player_ids"]["Host"]

        # Verify lobby phase
        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] == "lobby"

        # Friend joins
        join_resp = client.post(f"/api/games/{game_id}/join", json={"player_name": "Friend"})
        assert join_resp.status_code == 200

        # Host starts the game
        start_resp = client.post(f"/api/games/{game_id}/start?player_id={host_id}")
        assert start_resp.status_code == 200

        # Game should now be in bidding phase
        state = client.get(f"/api/games/{game_id}").json()
        assert state["phase"] == "bidding"
        player_names = [p["name"] for p in state["players"]]
        assert "Host" in player_names
        assert "Friend" in player_names

    def test_lobby_with_must_lose_mode(self):
        """Lobby creation preserves must_lose_mode setting."""
        resp = client.post("/api/games", json={
            "variant": "10_to_1",
            "must_lose_mode": True,
            "players": [{"name": "Host", "is_ai": False}],
            "auto_start": False,
        })
        assert resp.status_code == 200
        game_id = resp.json()["game_id"]

        lobby = client.get(f"/api/games/{game_id}/lobby").json()
        assert lobby["must_lose_mode"] is True


class TestFillWithAI:
    def test_fill_with_ai(self, fresh_manager):
        data = _create_public_lobby()
        game_id = data["game_id"]

        # Join one more human
        client.post(f"/api/games/{game_id}/join", json={"player_name": "Bob"})

        # Fill remaining slots with AI
        fresh_manager.fill_with_ai(game_id)

        state = client.get(f"/api/games/{game_id}").json()
        assert len(state["players"]) == 5  # max for 10_to_1
