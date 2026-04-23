from backend.app.models import (
    Player, PlayerType, GameConfig, DealingVariant, GamePhase, Card,
)
from backend.app.models.events import EventType, GameEvent
from backend.app.game.engine import GameEngine


def _make_players(n: int) -> list[Player]:
    return [Player(id=f"p{i+1}", name=f"Player {i+1}", player_type=PlayerType.HUMAN) for i in range(n)]


def _setup_game(num_players: int = 3, variant=DealingVariant.TEN_TO_ONE, must_lose=False) -> tuple[GameEngine, list[GameEvent]]:
    engine = GameEngine(GameConfig(variant=variant, must_lose_mode=must_lose))
    events: list[GameEvent] = []
    engine.add_observer(events.append)
    for p in _make_players(num_players):
        engine.add_player(p)
    engine.start_game()
    return engine, events


class TestGameSetup:
    def test_add_players(self):
        engine = GameEngine()
        players = _make_players(3)
        for p in players:
            assert engine.add_player(p)
        assert len(engine.state.players) == 3

    def test_cannot_add_duplicate(self):
        engine = GameEngine()
        p = _make_players(1)[0]
        assert engine.add_player(p)
        assert not engine.add_player(p)

    def test_cannot_exceed_max_players(self):
        engine = GameEngine(GameConfig(variant=DealingVariant.TEN_TO_ONE))
        for p in _make_players(5):
            assert engine.add_player(p)
        extra = Player(id="p6", name="Extra", player_type=PlayerType.HUMAN)
        assert not engine.add_player(extra)

    def test_need_min_two_players(self):
        engine = GameEngine()
        engine.add_player(_make_players(1)[0])
        assert not engine.start_game()

    def test_start_game_transitions_to_bidding(self):
        engine, events = _setup_game()
        assert engine.state.phase == GamePhase.BIDDING
        event_types = [e.event_type for e in events]
        assert EventType.GAME_STARTED in event_types
        assert EventType.ROUND_STARTED in event_types


class TestBidding:
    def test_bidding_order(self):
        engine, _ = _setup_game(3)
        # Dealer is p1 (index 0), so bid order is p2, p3, p1
        assert engine.state.current_player_id == "p2"

    def test_place_valid_bid(self):
        engine, events = _setup_game(3)
        assert engine.place_bid("p2", 2)
        bid_events = [e for e in events if e.event_type == EventType.BID_PLACED]
        assert len(bid_events) == 1

    def test_wrong_player_cannot_bid(self):
        engine, _ = _setup_game(3)
        assert not engine.place_bid("p1", 2)

    def test_bidding_completes(self):
        engine, events = _setup_game(3)
        # 10 cards, 3 players, bid order: p2, p3, p1 (dealer)
        engine.place_bid("p2", 3)
        engine.place_bid("p3", 2)
        # Dealer (p1) forbidden = 10 - 5 = 5
        assert engine.place_bid("p1", 4)
        assert engine.state.phase == GamePhase.PLAYING


class TestFullRound:
    def test_play_full_round(self):
        engine, events = _setup_game(3)

        # Complete bidding
        engine.place_bid("p2", 3)
        engine.place_bid("p3", 2)
        engine.place_bid("p1", 4)  # dealer can't bid 5

        assert engine.state.phase == GamePhase.PLAYING

        # Play all 10 tricks
        for _ in range(10):
            current = engine.state.current_player_id
            for _ in range(3):
                current = engine.state.current_player_id
                valid = engine.get_valid_cards(current)
                assert len(valid) > 0, f"No valid cards for {current}"
                assert engine.play_card(current, valid[0])

        # Round should be over, waiting for continue_game()
        assert engine.state.phase == GamePhase.ROUND_OVER
        round_complete = [e for e in events if e.event_type == EventType.ROUND_COMPLETE]
        assert len(round_complete) == 1

        # Advance to next round
        assert engine.continue_game()
        assert engine.state.phase == GamePhase.BIDDING


class TestTurnOrder:
    def test_trick_winner_leads_next(self):
        engine, events = _setup_game(3)
        engine.place_bid("p2", 3)
        engine.place_bid("p3", 2)
        engine.place_bid("p1", 4)

        # Play first trick
        for _ in range(3):
            current = engine.state.current_player_id
            valid = engine.get_valid_cards(current)
            engine.play_card(current, valid[0])

        # Check that the trick winner leads the next trick
        trick_events = [e for e in events if e.event_type == EventType.TRICK_COMPLETE]
        assert len(trick_events) == 1
        winner = trick_events[0].data["winner_id"]

        # The winner should be the current player for the next trick
        assert engine.state.current_player_id == winner


class TestValidActions:
    def test_get_valid_bids(self):
        engine, _ = _setup_game(3)
        bids = engine.get_valid_bids("p2")
        assert len(bids) > 0
        assert all(0 <= b <= 10 for b in bids)

    def test_get_valid_cards(self):
        engine, _ = _setup_game(3)
        engine.place_bid("p2", 3)
        engine.place_bid("p3", 2)
        engine.place_bid("p1", 4)
        current = engine.state.current_player_id
        valid = engine.get_valid_cards(current)
        assert len(valid) > 0


class TestRoundOverGating:
    """Engine must NOT auto-advance after a round. The client calls continue_game()."""

    def test_round_stays_in_round_over(self):
        engine, events = _setup_game(3)
        engine.place_bid("p2", 3)
        engine.place_bid("p3", 2)
        engine.place_bid("p1", 4)

        for _ in range(10):
            for _ in range(3):
                current = engine.state.current_player_id
                valid = engine.get_valid_cards(current)
                engine.play_card(current, valid[0])

        # Must be ROUND_OVER, not BIDDING
        assert engine.state.phase == GamePhase.ROUND_OVER

        # No ROUND_STARTED after ROUND_COMPLETE
        event_types = [e.event_type for e in events]
        round_complete_idx = next(
            i for i, t in enumerate(event_types) if t == EventType.ROUND_COMPLETE
        )
        events_after = event_types[round_complete_idx + 1:]
        assert EventType.ROUND_STARTED not in events_after
        assert EventType.CARDS_DEALT not in events_after

    def test_continue_game_advances_to_bidding(self):
        engine, events = _setup_game(3)
        engine.place_bid("p2", 3)
        engine.place_bid("p3", 2)
        engine.place_bid("p1", 4)

        for _ in range(10):
            for _ in range(3):
                current = engine.state.current_player_id
                valid = engine.get_valid_cards(current)
                engine.play_card(current, valid[0])

        assert engine.state.phase == GamePhase.ROUND_OVER
        events.clear()

        assert engine.continue_game()
        assert engine.state.phase == GamePhase.BIDDING
        event_types = [e.event_type for e in events]
        assert EventType.ROUND_STARTED in event_types
        assert EventType.CARDS_DEALT in event_types

    def test_continue_game_rejects_wrong_phase(self):
        engine, _ = _setup_game(3)
        assert engine.state.phase == GamePhase.BIDDING
        assert not engine.continue_game()


class TestDealerRotation:
    def test_dealer_rotates_each_round(self):
        engine, events = _setup_game(3)

        first_round_dealer = engine.state.current_round.dealer_id
        assert first_round_dealer == "p1"

        # Play through first round
        engine.place_bid("p2", 3)
        engine.place_bid("p3", 2)
        engine.place_bid("p1", 4)
        for _ in range(10):
            for _ in range(3):
                current = engine.state.current_player_id
                valid = engine.get_valid_cards(current)
                engine.play_card(current, valid[0])

        # Advance to next round
        assert engine.state.phase == GamePhase.ROUND_OVER
        engine.continue_game()

        # Second round should have p2 as dealer
        if engine.state.phase != GamePhase.GAME_OVER:
            assert engine.state.current_round.dealer_id == "p2"
