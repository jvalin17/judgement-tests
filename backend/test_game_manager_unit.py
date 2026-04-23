"""Unit tests for game_manager.py and _get_event_delay from websocket.py."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from backend.app.game_manager import (
    GameManager,
    GameSpeed,
    ManagedGame,
    _should_nerf_ai,
    _load_game_count,
    _increment_game_count,
)
from backend.app.models.player import Player, PlayerType, AIDifficulty
from backend.app.models.game import GameConfig, DealingVariant
from backend.app.models.events import EventType
from backend.app.game.engine import GameEngine
from backend.app.ai.easy import EasyAI
from backend.app.ai.medium import MediumAI
from backend.app.ai.hard import HardAI
from backend.app.api.websocket import _get_event_delay


# ---------------------------------------------------------------------------
# GameSpeed
# ---------------------------------------------------------------------------

class TestGameSpeed:
    def test_default_values(self):
        speed = GameSpeed()
        assert speed.after_card_played == 2.0
        assert speed.after_trick_complete == 3.0
        assert speed.after_round_complete == 1.5
        assert speed.after_bidding_complete == 1.5

    def test_custom_values(self):
        speed = GameSpeed(after_card=1.0, after_trick=2.0, after_round=0.5, after_bidding=0.8)
        assert speed.after_card_played == 1.0
        assert speed.after_trick_complete == 2.0
        assert speed.after_round_complete == 0.5
        assert speed.after_bidding_complete == 0.8


# ---------------------------------------------------------------------------
# GameManager.remove_game
# ---------------------------------------------------------------------------

class TestRemoveGame:
    def test_removes_existing_game(self):
        manager = GameManager()
        config = GameConfig(variant=DealingVariant.TEN_TO_ONE)
        players = [
            Player(id="p1", name="Alice", player_type=PlayerType.HUMAN),
            Player(id="ai1", name="Bot", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
            Player(id="ai2", name="Bot2", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
        ]
        managed = manager.create_game(config, players)
        game_id = managed.engine.state.game_id
        assert game_id in manager.list_games()

        manager.remove_game(game_id)
        assert game_id not in manager.list_games()

    def test_noop_for_nonexistent_game(self):
        manager = GameManager()
        # Should not raise
        manager.remove_game("nonexistent-id")
        assert manager.list_games() == []


# ---------------------------------------------------------------------------
# GameManager.list_games
# ---------------------------------------------------------------------------

class TestListGames:
    def test_empty_list(self):
        manager = GameManager()
        assert manager.list_games() == []

    def test_after_creating_games(self):
        manager = GameManager()
        config = GameConfig(variant=DealingVariant.TEN_TO_ONE)
        players = [
            Player(id="p1", name="Alice", player_type=PlayerType.HUMAN),
            Player(id="ai1", name="Bot", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
            Player(id="ai2", name="Bot2", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
        ]
        managed1 = manager.create_game(config, players)
        players2 = [
            Player(id="p2", name="Bob", player_type=PlayerType.HUMAN),
            Player(id="ai3", name="Bot3", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
            Player(id="ai4", name="Bot4", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
        ]
        managed2 = manager.create_game(config, players2)

        ids = manager.list_games()
        assert len(ids) == 2
        assert managed1.engine.state.game_id in ids
        assert managed2.engine.state.game_id in ids


# ---------------------------------------------------------------------------
# GameManager.record_persona
# ---------------------------------------------------------------------------

class TestRecordPersona:
    def test_appends_persona_id(self):
        manager = GameManager()
        manager.record_persona("persona-1")
        assert manager._recent_persona_ids == ["persona-1"]

    def test_stays_under_max(self):
        manager = GameManager()
        for index in range(15):
            manager.record_persona(f"p-{index}")
        assert len(manager._recent_persona_ids) == 15
        assert manager._recent_persona_ids[0] == "p-0"
        assert manager._recent_persona_ids[14] == "p-14"

    def test_trims_when_over_max(self):
        manager = GameManager()
        for index in range(15):
            manager.record_persona(f"p-{index}")
        # Adding one more should trim to the last 15
        manager.record_persona("p-15")
        assert len(manager._recent_persona_ids) == 15
        assert manager._recent_persona_ids[0] == "p-1"
        assert manager._recent_persona_ids[14] == "p-15"


# ---------------------------------------------------------------------------
# _should_nerf_ai
# ---------------------------------------------------------------------------

class TestShouldNerfAI:
    def test_returns_false_for_game_1(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"game_count": 0}, tmp)
            tmp_path = tmp.name
        try:
            with patch("backend.app.game_manager._STATS_FILE", tmp_path):
                result = _should_nerf_ai()
                assert result is False
        finally:
            os.unlink(tmp_path)

    def test_returns_false_for_game_2(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"game_count": 1}, tmp)
            tmp_path = tmp.name
        try:
            with patch("backend.app.game_manager._STATS_FILE", tmp_path):
                result = _should_nerf_ai()
                assert result is False
        finally:
            os.unlink(tmp_path)

    def test_returns_true_for_game_3_when_random_low(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"game_count": 2}, tmp)
            tmp_path = tmp.name
        try:
            with patch("backend.app.game_manager._STATS_FILE", tmp_path):
                with patch("backend.app.game_manager.random.random", return_value=0.1):
                    result = _should_nerf_ai()
                    assert result is True
        finally:
            os.unlink(tmp_path)

    def test_returns_false_for_game_3_when_random_high(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"game_count": 2}, tmp)
            tmp_path = tmp.name
        try:
            with patch("backend.app.game_manager._STATS_FILE", tmp_path):
                with patch("backend.app.game_manager.random.random", return_value=0.5):
                    result = _should_nerf_ai()
                    assert result is False
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# _load_game_count / _increment_game_count
# ---------------------------------------------------------------------------

class TestGameCountIO:
    def test_load_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"game_count": 7}, tmp)
            tmp_path = tmp.name
        try:
            with patch("backend.app.game_manager._STATS_FILE", tmp_path):
                assert _load_game_count() == 7
        finally:
            os.unlink(tmp_path)

    def test_file_not_found_returns_0(self):
        with patch("backend.app.game_manager._STATS_FILE", "/tmp/nonexistent_stats_abc123.json"):
            assert _load_game_count() == 0

    def test_increment_writes_and_reads(self):
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "data", "player_stats.json")
        try:
            with patch("backend.app.game_manager._STATS_FILE", tmp_path):
                count = _increment_game_count()
                assert count == 1
                count = _increment_game_count()
                assert count == 2
                assert _load_game_count() == 2
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            # Clean up dirs
            data_dir = os.path.dirname(tmp_path)
            if os.path.isdir(data_dir):
                os.rmdir(data_dir)
            if os.path.isdir(tmp_dir):
                os.rmdir(tmp_dir)


# ---------------------------------------------------------------------------
# ManagedGame._get_max_ai_difficulty
# ---------------------------------------------------------------------------

class TestGetMaxAIDifficulty:
    def _make_managed(self):
        config = GameConfig(variant=DealingVariant.TEN_TO_ONE)
        engine = GameEngine(config)
        return ManagedGame(engine)

    def test_no_strategies_returns_easy(self):
        managed = self._make_managed()
        assert managed._get_max_ai_difficulty() == "easy"

    def test_single_strategy(self):
        managed = self._make_managed()
        managed.ai_strategies["ai1"] = MediumAI()
        assert managed._get_max_ai_difficulty() == "medium"

    def test_mixed_difficulties_returns_highest(self):
        managed = self._make_managed()
        managed.ai_strategies["ai1"] = EasyAI()
        managed.ai_strategies["ai2"] = HardAI()
        managed.ai_strategies["ai3"] = MediumAI()
        assert managed._get_max_ai_difficulty() == "hard"


# ---------------------------------------------------------------------------
# _get_event_delay (from websocket.py)
# ---------------------------------------------------------------------------

class TestGetEventDelay:
    def _make_managed(self, speed=None):
        config = GameConfig(variant=DealingVariant.TEN_TO_ONE)
        engine = GameEngine(config)
        return ManagedGame(engine, speed=speed)

    def test_card_played_returns_after_card(self):
        managed = self._make_managed()
        assert _get_event_delay(EventType.CARD_PLAYED, managed) == 2.0

    def test_trick_complete_returns_after_trick(self):
        managed = self._make_managed()
        assert _get_event_delay(EventType.TRICK_COMPLETE, managed) == 3.0

    def test_round_complete_returns_after_round(self):
        managed = self._make_managed()
        assert _get_event_delay(EventType.ROUND_COMPLETE, managed) == 1.5

    def test_bidding_complete_returns_after_bidding(self):
        managed = self._make_managed()
        assert _get_event_delay(EventType.BIDDING_COMPLETE, managed) == 1.5

    def test_unknown_event_returns_zero(self):
        managed = self._make_managed()
        assert _get_event_delay(EventType.TURN_CHANGED, managed) == 0
        assert _get_event_delay(EventType.GAME_STARTED, managed) == 0
        assert _get_event_delay(EventType.BID_PLACED, managed) == 0
        assert _get_event_delay(EventType.GAME_OVER, managed) == 0

    def test_custom_speed_values(self):
        speed = GameSpeed(after_card=0.5, after_trick=1.0, after_round=0.3, after_bidding=0.4)
        managed = self._make_managed(speed=speed)
        assert _get_event_delay(EventType.CARD_PLAYED, managed) == 0.5
        assert _get_event_delay(EventType.TRICK_COMPLETE, managed) == 1.0
        assert _get_event_delay(EventType.ROUND_COMPLETE, managed) == 0.3
        assert _get_event_delay(EventType.BIDDING_COMPLETE, managed) == 0.4
