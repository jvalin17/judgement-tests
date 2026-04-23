"""Engine correctness tests: phase validation, score persistence, tied winners.

These tests verify that the engine rejects actions in wrong phases,
accumulates scores across rounds, and handles edge cases like ties.
"""

from backend.app.models import (
    Player, PlayerType, GameConfig, DealingVariant, GamePhase, Card, Suit, Rank,
)
from backend.app.models.events import EventType, GameEvent
from backend.app.game.engine import GameEngine


def _make_players(n: int) -> list:
    return [
        Player(id=f"p{i+1}", name=f"Player {i+1}", player_type=PlayerType.HUMAN)
        for i in range(n)
    ]


def _setup_game(num_players=3, variant=DealingVariant.TEN_TO_ONE) -> tuple:
    engine = GameEngine(GameConfig(variant=variant))
    events = []
    engine.add_observer(events.append)
    for player in _make_players(num_players):
        engine.add_player(player)
    engine.start_game()
    return engine, events


def _complete_bidding(engine):
    """Place valid bids for all players in order."""
    while engine.state.phase == GamePhase.BIDDING:
        pid = engine.state.current_player_id
        valid_bids = engine.get_valid_bids(pid)
        engine.place_bid(pid, valid_bids[0])


def _play_one_trick(engine):
    """Play one full trick (all players play one card)."""
    num_players = len(engine.state.players)
    for _ in range(num_players):
        pid = engine.state.current_player_id
        valid = engine.get_valid_cards(pid)
        engine.play_card(pid, valid[0])


def _play_full_round(engine):
    """Complete bidding + all tricks for one round."""
    _complete_bidding(engine)
    num_cards = engine.state.current_round.num_cards
    for _ in range(num_cards):
        if engine.state.phase != GamePhase.PLAYING:
            break
        _play_one_trick(engine)


class TestPhaseValidation:
    """Engine must reject actions in wrong phases."""

    def test_cannot_bid_during_playing(self):
        engine, _ = _setup_game()
        _complete_bidding(engine)
        assert engine.state.phase == GamePhase.PLAYING
        pid = engine.state.current_player_id
        assert not engine.place_bid(pid, 1)

    def test_cannot_play_during_bidding(self):
        engine, _ = _setup_game()
        assert engine.state.phase == GamePhase.BIDDING
        pid = engine.state.current_player_id
        hand = engine.get_player_hand(pid)
        assert len(hand) > 0
        assert not engine.play_card(pid, hand[0])

    def test_cannot_bid_in_lobby(self):
        engine = GameEngine()
        for player in _make_players(3):
            engine.add_player(player)
        assert engine.state.phase == GamePhase.LOBBY
        assert not engine.place_bid("p1", 1)

    def test_cannot_play_in_lobby(self):
        engine = GameEngine()
        for player in _make_players(3):
            engine.add_player(player)
        card = Card(suit=Suit.SPADES, rank=Rank.ACE)
        assert not engine.play_card("p1", card)

    def test_cannot_start_twice(self):
        engine, _ = _setup_game()
        assert not engine.start_game()

    def test_cannot_add_player_after_start(self):
        engine, _ = _setup_game()
        extra = Player(id="extra", name="Extra", player_type=PlayerType.HUMAN)
        assert not engine.add_player(extra)


class TestScorePersistence:
    """Scores must accumulate across rounds."""

    def test_scores_persist_across_rounds(self):
        engine, events = _setup_game()
        _play_full_round(engine)

        # Gather scores after round 1
        round_complete_events = [
            evt for evt in events if evt.event_type == EventType.ROUND_COMPLETE
        ]
        assert len(round_complete_events) >= 1
        first_round_scores = round_complete_events[0].data["cumulative_scores"]

        # All players should have a score (could be positive or negative)
        for pid in ["p1", "p2", "p3"]:
            assert pid in first_round_scores

        # Cumulative scores on engine should match
        for pid in ["p1", "p2", "p3"]:
            assert engine.state.cumulative_scores[pid] == first_round_scores[pid]

    def test_second_round_adds_to_first(self):
        engine, events = _setup_game()
        _play_full_round(engine)

        scores_after_r1 = dict(engine.state.cumulative_scores)

        if engine.state.phase == GamePhase.GAME_OVER:
            return  # Game ended after 1 round (shouldn't happen with 10_to_1 but guard)

        engine.continue_game()
        _play_full_round(engine)

        # Scores should have changed (extremely unlikely all 3 players score 0 twice)
        scores_after_r2 = dict(engine.state.cumulative_scores)
        changed = any(
            scores_after_r2[pid] != scores_after_r1[pid]
            for pid in ["p1", "p2", "p3"]
        )
        assert changed, "Scores didn't change after second round"


class TestQueryEdgeCases:
    """Query methods should be safe to call in any state."""

    def test_get_hand_before_start(self):
        engine = GameEngine()
        for player in _make_players(3):
            engine.add_player(player)
        assert engine.get_player_hand("p1") == []

    def test_get_valid_bids_wrong_player(self):
        engine, _ = _setup_game()
        # p2 bids first (left of dealer), so p1 shouldn't get valid bids
        assert engine.get_valid_bids("p1") == []

    def test_get_valid_cards_during_bidding(self):
        engine, _ = _setup_game()
        assert engine.state.phase == GamePhase.BIDDING
        assert engine.get_valid_cards("p2") == []

    def test_get_round_context_before_start(self):
        engine = GameEngine()
        for player in _make_players(3):
            engine.add_player(player)
        ctx = engine.get_round_context("p1")
        assert ctx.player_id == "p1"
        assert ctx.trump_suit is None
        assert ctx.num_cards == 0

    def test_get_round_summary_before_start(self):
        engine = GameEngine()
        for player in _make_players(3):
            engine.add_player(player)
        summary = engine.get_round_summary()
        assert summary == {}

    def test_get_hand_unknown_player(self):
        engine, _ = _setup_game()
        assert engine.get_player_hand("unknown") == []


class TestTiedWinners:
    """Game with tied final scores should list all tied players as winners."""

    def test_tied_scores_both_win(self):
        engine = GameEngine(GameConfig())
        events = []
        engine.add_observer(events.append)
        players = _make_players(3)
        for player in players:
            engine.add_player(player)

        # Manually set scores so they'll tie after the game
        engine.state.cumulative_scores["p1"] = 100
        engine.state.cumulative_scores["p2"] = 100
        engine.state.cumulative_scores["p3"] = 50

        # Use _determine_winners directly
        winners = engine._determine_winners()
        assert set(winners) == {"p1", "p2"}


class TestAllVariantsPlayable:
    """Every dealing variant can be started and played through at least one round."""

    def test_ten_to_one(self):
        engine, _ = _setup_game(3, DealingVariant.TEN_TO_ONE)
        _play_full_round(engine)
        assert engine.state.phase == GamePhase.ROUND_OVER
        engine.continue_game()
        assert engine.state.phase in (GamePhase.BIDDING, GamePhase.GAME_OVER)

    def test_eight_down_up(self):
        engine, _ = _setup_game(3, DealingVariant.EIGHT_DOWN_UP)
        _play_full_round(engine)
        assert engine.state.phase == GamePhase.ROUND_OVER
        engine.continue_game()
        assert engine.state.phase in (GamePhase.BIDDING, GamePhase.GAME_OVER)

    def test_ten_down_up(self):
        engine, _ = _setup_game(3, DealingVariant.TEN_DOWN_UP)
        _play_full_round(engine)
        assert engine.state.phase == GamePhase.ROUND_OVER
        engine.continue_game()
        assert engine.state.phase in (GamePhase.BIDDING, GamePhase.GAME_OVER)
