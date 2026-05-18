"""Tests for consent tracking in DecisionCollector and kNN subsampling."""

import json
import os
import random
import tempfile

import pytest

from backend.app.models import Card, Suit, Rank
from backend.app.ai.base import RoundContext
from backend.app.ml.data_store import JsonlFileStore, get_default_store
from backend.app.ml.learning.decision_collector import DecisionCollector
from backend.app.ml.learning import neighbor_model
from backend.app.ml.learning.neighbor_model import (
    _find_neighbors,
    MAX_KNN_EXAMPLES,
    predict_bid,
    predict_card_index,
)


def _make_context(player_id="p1", trump_suit=Suit.SPADES, num_cards=5, num_players=3):
    return RoundContext(
        player_id=player_id,
        trump_suit=trump_suit,
        num_cards=num_cards,
        num_players=num_players,
        bids=[],
        tricks_won={},
        cards_played=[],
        current_trick_cards=[],
    )


def _sample_hand():
    return [
        Card(suit=Suit.SPADES, rank=Rank.ACE),
        Card(suit=Suit.HEARTS, rank=Rank.QUEEN),
        Card(suit=Suit.DIAMONDS, rank=Rank.JACK),
        Card(suit=Suit.CLUBS, rank=Rank.TEN),
        Card(suit=Suit.CLUBS, rank=Rank.FIVE),
    ]


# --- Consent tracking ---


class TestConsentTracking:
    def test_default_consent_is_false(self, tmp_path):
        """Winners without explicit consent get share_consent=False."""
        collector = DecisionCollector()
        hand = _sample_hand()
        context = _make_context()

        collector.record_bid("winner1", hand, context, 2, "human")

        bid_file = str(tmp_path / "bid_decisions.jsonl")
        play_file = str(tmp_path / "play_decisions.jsonl")

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_bid_data_file",
                lambda: bid_file,
            )
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_play_data_file",
                lambda: play_file,
            )
            count = collector.flush_winner(["winner1"])

        assert count == 1
        with open(bid_file) as fh:
            entry = json.loads(fh.readline())
        assert entry["share_consent"] is False

    def test_consented_player_gets_true(self, tmp_path):
        """Player who opted in gets share_consent=True in metadata."""
        collector = DecisionCollector()
        hand = _sample_hand()
        context = _make_context()

        collector.set_share_consent("winner1", True)
        collector.record_bid("winner1", hand, context, 3, "human")

        bid_file = str(tmp_path / "bid_decisions.jsonl")
        play_file = str(tmp_path / "play_decisions.jsonl")

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_bid_data_file",
                lambda: bid_file,
            )
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_play_data_file",
                lambda: play_file,
            )
            collector.flush_winner(["winner1"])

        with open(bid_file) as fh:
            entry = json.loads(fh.readline())
        assert entry["share_consent"] is True
        assert entry["strategy_type"] == "human"

    def test_mixed_consent_multiple_winners(self, tmp_path):
        """Two winners: one consented, one not. Each gets correct metadata."""
        collector = DecisionCollector()
        hand = _sample_hand()
        context_p1 = _make_context(player_id="p1")
        context_p2 = _make_context(player_id="p2")

        collector.set_share_consent("p1", True)
        # p2 has no consent set (defaults to False)
        collector.record_bid("p1", hand, context_p1, 2, "human")
        collector.record_bid("p2", hand, context_p2, 1, "medium")

        bid_file = str(tmp_path / "bid_decisions.jsonl")
        play_file = str(tmp_path / "play_decisions.jsonl")

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_bid_data_file",
                lambda: bid_file,
            )
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_play_data_file",
                lambda: play_file,
            )
            count = collector.flush_winner(["p1", "p2"])

        assert count == 2
        with open(bid_file) as fh:
            entries = [json.loads(line) for line in fh if line.strip()]
        consents = {e["strategy_type"]: e["share_consent"] for e in entries}
        assert consents["human"] is True
        assert consents["medium"] is False

    def test_set_consent_after_recording(self, tmp_path):
        """Consent can be set after decisions are recorded (before flush)."""
        collector = DecisionCollector()
        hand = _sample_hand()
        context = _make_context()

        collector.record_bid("p1", hand, context, 1, "human")
        collector.set_share_consent("p1", True)  # Set AFTER recording

        bid_file = str(tmp_path / "bid_decisions.jsonl")
        play_file = str(tmp_path / "play_decisions.jsonl")

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_bid_data_file",
                lambda: bid_file,
            )
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_play_data_file",
                lambda: play_file,
            )
            collector.flush_winner(["p1"])

        with open(bid_file) as fh:
            entry = json.loads(fh.readline())
        assert entry["share_consent"] is True

    def test_loser_decisions_not_flushed(self, tmp_path):
        """Non-winner decisions are discarded, regardless of consent."""
        collector = DecisionCollector()
        hand = _sample_hand()
        context_w = _make_context(player_id="winner")
        context_l = _make_context(player_id="loser")

        collector.set_share_consent("loser", True)
        collector.record_bid("winner", hand, context_w, 2, "human")
        collector.record_bid("loser", hand, context_l, 0, "human")

        bid_file = str(tmp_path / "bid_decisions.jsonl")
        play_file = str(tmp_path / "play_decisions.jsonl")

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_bid_data_file",
                lambda: bid_file,
            )
            monkeypatch.setattr(
                "backend.app.ml.learning.decision_collector.get_play_data_file",
                lambda: play_file,
            )
            count = collector.flush_winner(["winner"])

        assert count == 1  # Only winner's decision


# --- kNN subsampling ---


class TestKnnSubsampling:
    def test_find_neighbors_small_dataset(self):
        """Datasets under MAX_KNN_EXAMPLES are not subsampled."""
        examples = [{"features": [float(i)], "label": float(i)} for i in range(100)]
        query = [50.0]
        neighbors = _find_neighbors(query, examples, k=5)
        assert len(neighbors) == 5
        # Nearest should be exactly 50
        assert neighbors[0][0]["label"] == 50.0

    def test_find_neighbors_large_dataset_subsamples(self):
        """Datasets over MAX_KNN_EXAMPLES are subsampled to MAX_KNN_EXAMPLES."""
        large_count = MAX_KNN_EXAMPLES + 1000
        examples = [{"features": [float(i)], "label": float(i)} for i in range(large_count)]
        query = [0.0]

        # With random sampling, nearest neighbor might not be exactly 0
        # but we should still get k results
        random.seed(42)
        neighbors = _find_neighbors(query, examples, k=5)
        assert len(neighbors) == 5
        # All results should be valid examples
        for example, distance in neighbors:
            assert "features" in example
            assert "label" in example
            assert distance >= 0.0

    def test_subsampling_cap_is_respected(self):
        """Verify the subsample size is exactly MAX_KNN_EXAMPLES."""
        large_count = MAX_KNN_EXAMPLES * 2
        examples = [{"features": [float(i)], "label": float(i)} for i in range(large_count)]
        query = [0.0]

        # Patch random.sample to verify it's called with correct size
        original_sample = random.sample
        captured_args = []

        def tracking_sample(population, k):
            captured_args.append(k)
            return original_sample(population, k)

        random.seed(42)
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(random, "sample", tracking_sample)
            _find_neighbors(query, examples, k=5)

        assert captured_args[0] == MAX_KNN_EXAMPLES

    def test_predict_bid_below_min_examples(self, tmp_path):
        """Prediction returns None when examples < MIN_EXAMPLES."""
        data_file = str(tmp_path / "sparse.jsonl")
        store = JsonlFileStore()
        for i in range(5):  # Less than MIN_EXAMPLES (10)
            store.append_example(data_file, [float(i)], float(i))

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.neighbor_model.get_default_store",
                lambda: store,
            )
            result = predict_bid([3.0], data_file)

        assert result is None

    def test_predict_bid_with_enough_examples(self, tmp_path):
        """Prediction returns an integer when examples >= MIN_EXAMPLES."""
        data_file = str(tmp_path / "sufficient.jsonl")
        store = JsonlFileStore()
        # Create 15 examples all bidding 3
        for i in range(15):
            store.append_example(data_file, [float(i)], 3.0)

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.neighbor_model.get_default_store",
                lambda: store,
            )
            result = predict_bid([7.0], data_file)

        assert result is not None
        assert isinstance(result, int)
        assert result == 3  # All neighbors bid 3

    def test_predict_card_index_clamped(self, tmp_path):
        """Card index prediction is clamped to [0, num_valid_cards - 1]."""
        data_file = str(tmp_path / "play.jsonl")
        store = JsonlFileStore()
        # All examples predict index 99 (way out of range)
        for i in range(15):
            store.append_example(data_file, [float(i)], 99.0)

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "backend.app.ml.learning.neighbor_model.get_default_store",
                lambda: store,
            )
            result = predict_card_index([7.0], num_valid_cards=5, data_file=data_file)

        assert result is not None
        assert 0 <= result <= 4  # Clamped to valid range


# --- share_data in API schemas ---


class TestShareDataSchema:
    def test_create_game_share_data_defaults_false(self):
        from backend.app.api.schemas import CreateGameRequest
        request = CreateGameRequest(players=[{"name": "Alice", "is_ai": False}])
        assert request.share_data is False

    def test_create_game_share_data_true(self):
        from backend.app.api.schemas import CreateGameRequest
        request = CreateGameRequest(
            players=[{"name": "Alice", "is_ai": False}],
            share_data=True,
        )
        assert request.share_data is True

    def test_join_game_share_data_defaults_false(self):
        from backend.app.api.schemas import JoinGameRequest
        request = JoinGameRequest(player_name="Bob")
        assert request.share_data is False

    def test_join_game_share_data_true(self):
        from backend.app.api.schemas import JoinGameRequest
        request = JoinGameRequest(player_name="Bob", share_data=True)
        assert request.share_data is True
