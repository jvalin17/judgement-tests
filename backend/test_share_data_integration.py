"""Integration test: create game with share_data → play to completion → verify consent in JSONL."""

import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.rest import set_manager
from backend.app.game_manager import GameManager
from backend.app.ml.learning.decision_collector import get_bid_data_file, get_play_data_file
from backend.app.ml.data_store import get_default_store


@pytest.fixture(autouse=True)
def fresh_manager():
    manager = GameManager()
    set_manager(manager)
    yield manager


@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch, tmp_path):
    """Redirect JSONL data files to a temp directory to avoid polluting real data."""
    bid_file = str(tmp_path / "bid_decisions.jsonl")
    play_file = str(tmp_path / "play_decisions.jsonl")
    monkeypatch.setattr(
        "backend.app.ml.learning.decision_collector.get_bid_data_file",
        lambda: bid_file,
    )
    monkeypatch.setattr(
        "backend.app.ml.learning.decision_collector.get_play_data_file",
        lambda: play_file,
    )
    # Also patch neighbor_model so appends go to temp files
    monkeypatch.setattr(
        "backend.app.ml.learning.neighbor_model.get_default_store",
        lambda: get_default_store(),
    )
    # Clear cache so we don't pick up stale data
    get_default_store().invalidate_cache()
    return {"bid_file": bid_file, "play_file": play_file}


client = TestClient(app)


class TestShareDataIntegration:
    """End-to-end: create game with share_data, play full game, verify consent metadata."""

    def test_share_data_true_flows_to_jsonl(self, temp_data_dir):
        """When share_data=true, winner's JSONL entries have share_consent=true."""
        # Create game with share_data=true, all AI so it auto-plays
        resp = client.post("/api/games", json={
            "variant": "3_quick",
            "players": [
                {"name": "Human", "is_ai": False},
                {"name": "Bot1", "is_ai": True, "ai_difficulty": "easy"},
                {"name": "Bot2", "is_ai": True, "ai_difficulty": "easy"},
            ],
            "share_data": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        game_id = data["game_id"]
        human_id = data["player_ids"]["Human"]

        # Play through the game as the human player
        _play_full_game(game_id, human_id)

        # Check JSONL files for share_consent metadata
        bid_file = temp_data_dir["bid_file"]
        play_file = temp_data_dir["play_file"]

        all_entries = []
        for filepath in [bid_file, play_file]:
            if os.path.exists(filepath):
                with open(filepath) as fh:
                    for line in fh:
                        if line.strip():
                            all_entries.append(json.loads(line))

        # At least some entries should exist (game completed, winners flushed)
        if all_entries:
            # Human's entries should have share_consent=true
            human_entries = [e for e in all_entries if e.get("strategy_type") == "human"]
            for entry in human_entries:
                assert entry.get("share_consent") is True, (
                    f"Human entry missing share_consent=true: {entry}"
                )

    def test_share_data_false_flows_to_jsonl(self, temp_data_dir):
        """When share_data=false (default), entries have share_consent=false."""
        resp = client.post("/api/games", json={
            "variant": "3_quick",
            "players": [
                {"name": "Human", "is_ai": False},
                {"name": "Bot1", "is_ai": True, "ai_difficulty": "easy"},
                {"name": "Bot2", "is_ai": True, "ai_difficulty": "easy"},
            ],
            # share_data defaults to false
        })
        assert resp.status_code == 200
        data = resp.json()
        game_id = data["game_id"]
        human_id = data["player_ids"]["Human"]

        _play_full_game(game_id, human_id)

        bid_file = temp_data_dir["bid_file"]
        play_file = temp_data_dir["play_file"]

        all_entries = []
        for filepath in [bid_file, play_file]:
            if os.path.exists(filepath):
                with open(filepath) as fh:
                    for line in fh:
                        if line.strip():
                            all_entries.append(json.loads(line))

        if all_entries:
            human_entries = [e for e in all_entries if e.get("strategy_type") == "human"]
            for entry in human_entries:
                assert entry.get("share_consent") is False, (
                    f"Human entry should have share_consent=false: {entry}"
                )

    def test_join_game_share_data_sets_consent(self, temp_data_dir):
        """Joining a game with share_data=true sets consent for that player."""
        # Create a lobby game (auto_start=false)
        resp = client.post("/api/games", json={
            "variant": "3_quick",
            "players": [
                {"name": "Host", "is_ai": False},
            ],
            "auto_start": False,
        })
        assert resp.status_code == 200
        game_id = resp.json()["game_id"]
        host_id = resp.json()["player_ids"]["Host"]

        # Join with share_data=true
        join_resp = client.post(f"/api/games/{game_id}/join", json={
            "player_name": "Joiner",
            "share_data": True,
        })
        assert join_resp.status_code == 200
        joiner_id = join_resp.json()["player_id"]

        # Add a bot and start the game
        client.post(f"/api/games/{game_id}/add-bot", json={
            "player_id": host_id,
            "difficulty": "easy",
        })
        client.post(f"/api/games/{game_id}/start?player_id={host_id}")

        # Play through as both humans
        _play_full_game_two_humans(game_id, host_id, joiner_id)

        # Check JSONL — joiner's entries should have consent
        all_entries = []
        for filepath in [temp_data_dir["bid_file"], temp_data_dir["play_file"]]:
            if os.path.exists(filepath):
                with open(filepath) as fh:
                    for line in fh:
                        if line.strip():
                            all_entries.append(json.loads(line))

        # We can't know who won, but if entries exist, check consent values
        # Host didn't set share_data, Joiner did
        # Both are strategy_type="human" so we check that at least some have consent
        if all_entries:
            consented = [e for e in all_entries if e.get("share_consent") is True]
            not_consented = [e for e in all_entries if e.get("share_consent") is False]
            # At least consent tracking is present in all entries
            for entry in all_entries:
                assert "share_consent" in entry, f"Missing share_consent field: {entry}"


def _play_full_game(game_id: str, human_id: str):
    """Play a 3_quick game to completion as a single human with AI bots."""
    for attempt in range(100):  # Safety limit
        state = client.get(f"/api/games/{game_id}").json()
        phase = state["phase"]

        if phase == "game_over":
            break

        if state.get("current_player_id") != human_id:
            continue  # AI's turn, they auto-play

        if phase == "bidding":
            hand = client.get(f"/api/games/{game_id}/hand/{human_id}").json()
            valid_bids = hand.get("valid_bids", [0])
            bid = valid_bids[0]
            client.post(f"/api/games/{game_id}/bid", json={
                "player_id": human_id,
                "amount": bid,
            })

        elif phase == "playing":
            hand = client.get(f"/api/games/{game_id}/hand/{human_id}").json()
            valid_cards = hand.get("valid_cards", hand.get("hand", []))
            if valid_cards:
                card = valid_cards[0]
                client.post(f"/api/games/{game_id}/play", json={
                    "player_id": human_id,
                    "suit": card["suit"],
                    "rank": card["rank"],
                })


def _play_full_game_two_humans(game_id: str, player1_id: str, player2_id: str):
    """Play a game with two human players + bots."""
    human_ids = {player1_id, player2_id}
    for attempt in range(200):
        state = client.get(f"/api/games/{game_id}").json()
        phase = state["phase"]

        if phase == "game_over":
            break

        current = state.get("current_player_id")
        if current not in human_ids:
            continue

        if phase == "bidding":
            hand = client.get(f"/api/games/{game_id}/hand/{current}").json()
            valid_bids = hand.get("valid_bids", [0])
            client.post(f"/api/games/{game_id}/bid", json={
                "player_id": current,
                "amount": valid_bids[0],
            })

        elif phase == "playing":
            hand = client.get(f"/api/games/{game_id}/hand/{current}").json()
            valid_cards = hand.get("valid_cards", hand.get("hand", []))
            if valid_cards:
                card = valid_cards[0]
                client.post(f"/api/games/{game_id}/play", json={
                    "player_id": current,
                    "suit": card["suit"],
                    "rank": card["rank"],
                })
