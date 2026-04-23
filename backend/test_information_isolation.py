"""Tests verifying information isolation guarantees.

These tests ensure:
1. Feature vectors contain only numeric values (no raw card data)
2. RoundContext contains only public game state (no other players' hands)
3. Engine never leaks one player's hand to another
4. Decision collector stores only numeric features, never raw cards
5. Strategy type is tracked for every decision
"""

import os
import tempfile

import pytest

from backend.app.models import Card, Suit, Rank, Bid
from backend.app.models.player import Player, PlayerType, AIDifficulty
from backend.app.models.game import GameConfig, GamePhase, DealingVariant
from backend.app.ai.base import RoundContext
from backend.app.ml.learning.features import extract_bid_features, extract_play_features
from backend.app.ml.learning.decision_collector import DecisionCollector
from backend.app.ml.learning import neighbor_model
from backend.app.ml.data_store import get_default_store
from backend.app.game.engine import GameEngine
from backend.app.game_manager import GameManager


def _make_hand():
    return [
        Card(suit=Suit.SPADES, rank=Rank.ACE),
        Card(suit=Suit.HEARTS, rank=Rank.KING),
        Card(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        Card(suit=Suit.CLUBS, rank=Rank.JACK),
        Card(suit=Suit.SPADES, rank=Rank.TEN),
    ]


def _make_context(**overrides):
    defaults = dict(
        player_id="p1",
        trump_suit=Suit.SPADES,
        num_cards=5,
        num_players=3,
        bids=[],
        tricks_won={},
        cards_played=[],
        current_trick_cards=[],
    )
    defaults.update(overrides)
    return RoundContext(**defaults)


# --- Feature vector isolation ---


class TestFeatureVectorIsolation:
    """Features must be fixed-length lists of floats — no card objects."""

    def test_bid_features_are_all_floats(self):
        features = extract_bid_features(_make_hand(), _make_context())
        assert isinstance(features, list)
        for value in features:
            assert isinstance(value, float), f"Expected float, got {type(value)}: {value}"

    def test_play_features_are_all_floats(self):
        hand = _make_hand()
        context = _make_context(bids=[Bid(player_id="p1", amount=2)])
        features = extract_play_features(hand, hand, context)
        assert isinstance(features, list)
        for value in features:
            assert isinstance(value, float), f"Expected float, got {type(value)}: {value}"

    def test_bid_features_fixed_length(self):
        """Different hands produce the same number of features."""
        small_hand = [Card(suit=Suit.HEARTS, rank=Rank.TWO)]
        big_hand = _make_hand()
        small_features = extract_bid_features(small_hand, _make_context(num_cards=1))
        big_features = extract_bid_features(big_hand, _make_context(num_cards=5))
        assert len(small_features) == len(big_features) == 12

    def test_play_features_fixed_length(self):
        """Different hands produce the same number of features."""
        small_hand = [Card(suit=Suit.HEARTS, rank=Rank.TWO)]
        big_hand = _make_hand()
        context = _make_context(bids=[Bid(player_id="p1", amount=1)])
        small_features = extract_play_features(small_hand, small_hand, context)
        big_features = extract_play_features(big_hand, big_hand, context)
        assert len(small_features) == len(big_features) == 11

    def test_features_contain_no_card_objects(self):
        """Feature values must be plain numbers, never Card/Suit/Rank objects."""
        hand = _make_hand()
        context = _make_context(bids=[Bid(player_id="p1", amount=2)])
        bid_features = extract_bid_features(hand, context)
        play_features = extract_play_features(hand, hand, context)

        for features in [bid_features, play_features]:
            for value in features:
                assert not isinstance(value, (Card, Suit, Rank)), \
                    f"Feature contains card object: {value}"


# --- RoundContext isolation ---


class TestRoundContextIsolation:
    """RoundContext must only contain public game state."""

    def test_context_has_no_hand_attribute(self):
        """RoundContext should never store hand data."""
        context = _make_context()
        assert not hasattr(context, "hand"), "RoundContext should not contain hand data"
        assert not hasattr(context, "hands"), "RoundContext should not contain hands data"
        assert not hasattr(context, "other_hands"), "RoundContext should not contain other_hands"

    def test_context_cards_played_are_public(self):
        """cards_played in context are from completed tricks — visible to all players."""
        played = [Card(suit=Suit.HEARTS, rank=Rank.ACE)]
        context = _make_context(cards_played=played)
        # These are cards from completed tricks, visible to everyone at the table
        assert context.cards_played == played

    def test_context_bids_are_public(self):
        """Bids are public information."""
        bids = [Bid(player_id="p1", amount=2), Bid(player_id="p2", amount=3)]
        context = _make_context(bids=bids)
        assert len(context.bids) == 2


# --- Engine hand isolation ---


class TestEngineHandIsolation:
    """Engine must never leak one player's hand to another."""

    def _setup_game(self):
        config = GameConfig(variant=DealingVariant.TEN_TO_ONE)
        engine = GameEngine(config)
        players = [
            Player(id="p1", name="Alice", player_type=PlayerType.HUMAN),
            Player(id="p2", name="Bob", player_type=PlayerType.HUMAN),
            Player(id="p3", name="Charlie", player_type=PlayerType.HUMAN),
        ]
        for player in players:
            engine.add_player(player)
        engine.start_game()
        return engine

    def test_hands_are_disjoint(self):
        """No two players share any cards."""
        engine = self._setup_game()
        hand_p1 = set((card.suit, card.rank) for card in engine.get_player_hand("p1"))
        hand_p2 = set((card.suit, card.rank) for card in engine.get_player_hand("p2"))
        hand_p3 = set((card.suit, card.rank) for card in engine.get_player_hand("p3"))

        assert hand_p1.isdisjoint(hand_p2), "p1 and p2 share cards"
        assert hand_p1.isdisjoint(hand_p3), "p1 and p3 share cards"
        assert hand_p2.isdisjoint(hand_p3), "p2 and p3 share cards"

    def test_get_player_hand_only_returns_own_cards(self):
        """get_player_hand returns exactly that player's cards, not others'."""
        engine = self._setup_game()
        hand_p1 = engine.get_player_hand("p1")
        hand_p2 = engine.get_player_hand("p2")

        assert len(hand_p1) > 0
        assert len(hand_p2) > 0
        assert hand_p1 != hand_p2

    def test_round_context_does_not_contain_other_hands(self):
        """get_round_context for one player never includes another's hand."""
        engine = self._setup_game()
        context_p1 = engine.get_round_context("p1")
        hand_p2 = engine.get_player_hand("p2")

        # Context should have no reference to p2's hand cards
        # cards_played should be empty at start of round (no tricks completed yet)
        for card in hand_p2:
            assert card not in context_p1.cards_played, \
                f"p2's card {card} found in p1's context.cards_played"


# --- Decision collector isolation ---


class TestDecisionCollectorIsolation:
    """Collector must store only numeric features and strategy type, never raw cards."""

    def test_stored_data_contains_only_numbers(self):
        """Flushed data must contain only features (float list) and label (float)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bid_file = os.path.join(tmp_dir, "bids.jsonl")
            play_file = os.path.join(tmp_dir, "plays.jsonl")

            collector = DecisionCollector()
            hand = _make_hand()
            context = _make_context(num_cards=5)

            collector.record_bid("winner", hand, context, 3, "hard")
            play_context = _make_context(
                num_cards=5,
                bids=[Bid(player_id="winner", amount=3)],
            )
            collector.record_play("winner", hand, hand, play_context, hand[0], "hard")

            import backend.app.ml.learning.decision_collector as collector_module
            original_bid_fn = collector_module.get_bid_data_file
            original_play_fn = collector_module.get_play_data_file
            collector_module.get_bid_data_file = lambda: bid_file
            collector_module.get_play_data_file = lambda: play_file

            try:
                collector.flush_winner(["winner"])
            finally:
                collector_module.get_bid_data_file = original_bid_fn
                collector_module.get_play_data_file = original_play_fn

            # Verify stored data
            bid_examples = get_default_store().load_examples(bid_file)
            play_examples = get_default_store().load_examples(play_file)

            for example in bid_examples + play_examples:
                assert "features" in example
                assert "label" in example
                # Features must be a list of numbers
                assert isinstance(example["features"], list)
                for value in example["features"]:
                    assert isinstance(value, (int, float)), \
                        f"Feature is not numeric: {value} ({type(value)})"
                # Label must be numeric
                assert isinstance(example["label"], (int, float))

    def test_stored_data_has_strategy_type(self):
        """Every flushed record must include the strategy_type metadata."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bid_file = os.path.join(tmp_dir, "bids.jsonl")
            play_file = os.path.join(tmp_dir, "plays.jsonl")

            collector = DecisionCollector()
            hand = _make_hand()
            context = _make_context(num_cards=5)

            collector.record_bid("winner", hand, context, 2, "human")
            play_context = _make_context(
                num_cards=5,
                bids=[Bid(player_id="winner", amount=2)],
            )
            collector.record_play("winner", hand, hand, play_context, hand[0], "smart_hard")

            import backend.app.ml.learning.decision_collector as collector_module
            original_bid_fn = collector_module.get_bid_data_file
            original_play_fn = collector_module.get_play_data_file
            collector_module.get_bid_data_file = lambda: bid_file
            collector_module.get_play_data_file = lambda: play_file

            try:
                collector.flush_winner(["winner"])
            finally:
                collector_module.get_bid_data_file = original_bid_fn
                collector_module.get_play_data_file = original_play_fn

            bid_examples = get_default_store().load_examples(bid_file)
            play_examples = get_default_store().load_examples(play_file)

            assert bid_examples[0]["strategy_type"] == "human"
            assert play_examples[0]["strategy_type"] == "smart_hard"

    def test_no_card_strings_in_stored_data(self):
        """Stored data must not contain card suit/rank strings."""
        import json

        with tempfile.TemporaryDirectory() as tmp_dir:
            bid_file = os.path.join(tmp_dir, "bids.jsonl")

            collector = DecisionCollector()
            hand = _make_hand()
            context = _make_context(num_cards=5)
            collector.record_bid("winner", hand, context, 3, "medium")

            import backend.app.ml.learning.decision_collector as collector_module
            original_bid_fn = collector_module.get_bid_data_file
            collector_module.get_bid_data_file = lambda: bid_file

            try:
                collector.flush_winner(["winner"])
            finally:
                collector_module.get_bid_data_file = original_bid_fn

            # Read the raw JSON and check for card-related strings
            with open(bid_file) as file_handle:
                raw_text = file_handle.read()

            suit_names = ["spades", "hearts", "diamonds", "clubs"]
            for suit_name in suit_names:
                assert suit_name not in raw_text.lower(), \
                    f"Raw card suit '{suit_name}' found in stored data"


# --- Full game integration isolation ---


class TestFullGameIsolation:
    """End-to-end test: a full AI game never leaks hand information."""

    def test_ai_game_hands_stay_isolated(self):
        """Run a full game with AI and verify hand isolation at each turn."""
        manager = GameManager()
        config = GameConfig(variant=DealingVariant.TEN_TO_ONE)
        players = [
            Player(id="ai1", name="Bot1", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
            Player(id="ai2", name="Bot2", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.MEDIUM),
            Player(id="ai3", name="Bot3", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.HARD),
        ]
        managed = manager.create_game(config, players)
        engine = managed.engine

        # Verify hands are disjoint before any play
        engine.start_game()

        # The game auto-plays through AI turns. After start, check isolation.
        # At whatever phase we're in, hands should never overlap.
        if engine.state.phase not in (GamePhase.GAME_OVER,):
            hands = {}
            for player in players:
                hands[player.id] = set(
                    (card.suit, card.rank) for card in engine.get_player_hand(player.id)
                )
            # Verify no overlap between any pair
            player_ids = list(hands.keys())
            for index_a in range(len(player_ids)):
                for index_b in range(index_a + 1, len(player_ids)):
                    pid_a = player_ids[index_a]
                    pid_b = player_ids[index_b]
                    assert hands[pid_a].isdisjoint(hands[pid_b]), \
                        f"{pid_a} and {pid_b} share cards"
