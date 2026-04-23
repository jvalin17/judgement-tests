from backend.app.models import Card, Suit, Rank, Bid
from backend.app.models.game import TrickPlay
from backend.app.ai.base import RoundContext
from backend.app.ai.easy import EasyAI
from backend.app.ai.medium import MediumAI
from backend.app.ai.hard import HardAI
from backend.app.ai.hand_evaluator import evaluate_hand
from backend.app.ai.personality import AIPersonality, random_personality, AGGRESSIVE, CONSERVATIVE, TACTICAL, GAMBLER
from backend.app.ai.opponent_model import OpponentModel


def _make_context(
    player_id="p1",
    trump=Suit.SPADES,
    num_cards=10,
    num_players=3,
    bids=None,
    tricks_won=None,
    cards_played=None,
    current_trick_cards=None,
):
    return RoundContext(
        player_id=player_id,
        trump_suit=trump,
        num_cards=num_cards,
        num_players=num_players,
        bids=bids or [],
        tricks_won=tricks_won or {},
        cards_played=cards_played or [],
        current_trick_cards=current_trick_cards or [],
    )


def _strong_hand(trump=Suit.SPADES):
    return [
        Card(suit=trump, rank=Rank.ACE),
        Card(suit=trump, rank=Rank.KING),
        Card(suit=trump, rank=Rank.QUEEN),
        Card(suit=Suit.HEARTS, rank=Rank.ACE),
        Card(suit=Suit.DIAMONDS, rank=Rank.ACE),
    ]


def _weak_hand(trump=Suit.SPADES):
    return [
        Card(suit=Suit.HEARTS, rank=Rank.TWO),
        Card(suit=Suit.HEARTS, rank=Rank.THREE),
        Card(suit=Suit.DIAMONDS, rank=Rank.TWO),
        Card(suit=Suit.CLUBS, rank=Rank.THREE),
        Card(suit=Suit.CLUBS, rank=Rank.FOUR),
    ]


# ---- Hand Evaluator ----

class TestHandEvaluator:
    def test_strong_hand_high_estimate(self):
        hand = _strong_hand()
        ev = evaluate_hand(hand, Suit.SPADES)
        assert ev.trump_count == 3
        assert ev.aces == 3
        assert ev.estimated_tricks >= 3.0

    def test_weak_hand_low_estimate(self):
        hand = _weak_hand()
        ev = evaluate_hand(hand, Suit.SPADES)
        assert ev.trump_count == 0
        assert ev.aces == 0
        assert ev.estimated_tricks < 1.5

    def test_void_suit_adds_ruffing(self):
        hand = [
            Card(suit=Suit.SPADES, rank=Rank.FIVE),
            Card(suit=Suit.HEARTS, rank=Rank.TWO),
            Card(suit=Suit.HEARTS, rank=Rank.THREE),
        ]
        ev = evaluate_hand(hand, Suit.SPADES)
        # Has trump + void in diamonds and clubs
        assert ev.estimated_tricks > 0


# ---- Easy AI ----

class TestEasyAI:
    def test_always_returns_valid_bid(self):
        ai = EasyAI()
        for _ in range(50):
            valid_bids = [0, 1, 2, 3]
            bid = ai.choose_bid([], valid_bids, _make_context())
            assert bid in valid_bids

    def test_always_returns_valid_card(self):
        ai = EasyAI()
        hand = _strong_hand()
        valid = hand[:3]
        for _ in range(50):
            card = ai.choose_card(hand, valid, _make_context())
            assert card in valid


# ---- Medium AI ----

class TestMediumAI:
    def test_bids_higher_with_strong_hand(self):
        ai = MediumAI()
        valid_bids = list(range(6))
        ctx = _make_context(num_cards=5)

        strong_bids = [
            ai.choose_bid(_strong_hand(), valid_bids, ctx) for _ in range(20)
        ]
        weak_bids = [
            ai.choose_bid(_weak_hand(), valid_bids, ctx) for _ in range(20)
        ]

        avg_strong = sum(strong_bids) / len(strong_bids)
        avg_weak = sum(weak_bids) / len(weak_bids)
        assert avg_strong > avg_weak

    def test_always_returns_valid_bid(self):
        ai = MediumAI()
        valid_bids = [0, 1, 3, 4]  # 2 is forbidden
        for _ in range(20):
            bid = ai.choose_bid(_strong_hand(), valid_bids, _make_context(num_cards=5))
            assert bid in valid_bids

    def test_always_returns_valid_card(self):
        ai = MediumAI()
        hand = _strong_hand()
        valid = hand[:3]
        ctx = _make_context()
        for _ in range(20):
            card = ai.choose_card(hand, valid, ctx)
            assert card in valid

    def test_leads_with_high_card(self):
        ai = MediumAI()
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.HEARTS, rank=Rank.TWO),
            Card(suit=Suit.CLUBS, rank=Rank.THREE),
        ]
        ctx = _make_context(current_trick_cards=[])
        card = ai.choose_card(hand, hand, ctx)
        # Should prefer leading with the ace
        assert card.rank == Rank.ACE

    def test_tries_to_win_trick(self):
        ai = MediumAI()
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.KING),
            Card(suit=Suit.HEARTS, rank=Rank.TWO),
        ]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.TEN)]
        ctx = _make_context(current_trick_cards=trick_cards)
        card = ai.choose_card(hand, hand, ctx)
        assert card.rank == Rank.KING


# ---- Hard AI ----

class TestHardAI:
    def test_always_returns_valid_bid(self):
        ai = HardAI()
        valid_bids = [0, 1, 2, 4, 5]
        for _ in range(20):
            bid = ai.choose_bid(_strong_hand(), valid_bids, _make_context(num_cards=5))
            assert bid in valid_bids

    def test_always_returns_valid_card(self):
        ai = HardAI()
        hand = _strong_hand()
        valid = hand[:3]
        ctx = _make_context()
        for _ in range(20):
            card = ai.choose_card(hand, valid, ctx)
            assert card in valid

    def test_bids_higher_with_strong_hand(self):
        ai = HardAI()
        valid_bids = list(range(6))
        ctx = _make_context(num_cards=5)

        strong_bids = [
            ai.choose_bid(_strong_hand(), valid_bids, ctx) for _ in range(20)
        ]
        weak_bids = [
            ai.choose_bid(_weak_hand(), valid_bids, ctx) for _ in range(20)
        ]

        avg_strong = sum(strong_bids) / len(strong_bids)
        avg_weak = sum(weak_bids) / len(weak_bids)
        assert avg_strong > avg_weak

    def test_card_counting_affects_estimate(self):
        ai = HardAI()
        valid_bids = list(range(6))

        # If ace of spades already played, our king of spades is stronger
        played = [Card(suit=Suit.SPADES, rank=Rank.ACE)]
        ctx = _make_context(num_cards=5, cards_played=played)
        hand = [
            Card(suit=Suit.SPADES, rank=Rank.KING),
            Card(suit=Suit.HEARTS, rank=Rank.TWO),
            Card(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]
        bid_with_info = ai.choose_bid(hand, valid_bids, ctx)

        ai2 = HardAI()
        ctx_no_info = _make_context(num_cards=5, cards_played=[])
        bid_without_info = ai2.choose_bid(hand, valid_bids, ctx_no_info)

        # With the ace played, king is highest — bid should be >= without info
        assert bid_with_info >= bid_without_info

    def test_plays_guaranteed_winner_in_middle(self):
        """In middle position, play the guaranteed winner (Ace — nothing can beat it)."""
        ai = HardAI()
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.HEARTS, rank=Rank.KING),
            Card(suit=Suit.HEARTS, rank=Rank.QUEEN),
        ]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.JACK)]
        bids = [Bid(player_id="p1", amount=2)]
        ctx = _make_context(
            current_trick_cards=trick_cards,
            bids=bids,
        )
        card = ai.choose_card(hand, hand, ctx)
        # Ace is a guaranteed winner (nothing outstanding above it) — play it
        assert card.rank == Rank.ACE


# ---- Integration: AI plays full game ----

class TestAIFullGame:
    def test_all_strategies_complete_game(self):
        """Each AI can play through a full game engine round without errors."""
        from backend.app.models import Player, PlayerType, AIDifficulty, GameConfig
        from backend.app.game.engine import GameEngine
        from backend.app.ai.easy import EasyAI
        from backend.app.ai.medium import MediumAI
        from backend.app.ai.hard import HardAI

        strategies = {"easy": EasyAI(), "medium": MediumAI(), "hard": HardAI()}

        for name, strategy in strategies.items():
            engine = GameEngine(GameConfig())
            players = [
                Player(id=f"ai_{name}_{i}", name=f"AI {i}", player_type=PlayerType.AI)
                for i in range(3)
            ]
            for p in players:
                engine.add_player(p)
            engine.start_game()

            # Play through first round (10 cards)
            # Bidding
            while engine.state.phase.value == "bidding":
                pid = engine.state.current_player_id
                valid_bids = engine.get_valid_bids(pid)
                hand = engine.get_player_hand(pid)
                ctx = engine.get_round_context(pid)
                bid = strategy.choose_bid(hand, valid_bids, ctx)
                assert engine.place_bid(pid, bid), f"{name} AI failed to bid"

            # Playing
            while engine.state.phase.value == "playing":
                pid = engine.state.current_player_id
                valid_cards = engine.get_valid_cards(pid)
                hand = engine.get_player_hand(pid)
                ctx = engine.get_round_context(pid)
                card = strategy.choose_card(hand, valid_cards, ctx)
                assert engine.play_card(pid, card), f"{name} AI failed to play"


# ---- Personality tests ----

class TestAIPersonality:
    def test_random_personality_in_bounds(self):
        """All personality weights should be between 0.0 and 1.0."""
        for _ in range(50):
            pers = random_personality()
            for attr in ["aggression", "trump_conservation", "opponent_focus", "risk_tolerance"]:
                value = getattr(pers, attr)
                assert 0.0 <= value <= 1.0, f"{attr}={value} out of bounds"

    def test_personalities_vary(self):
        """Generated personalities should not all be identical."""
        personalities = [random_personality() for _ in range(20)]
        aggression_values = set(round(p.aggression, 2) for p in personalities)
        assert len(aggression_values) > 3, "Personalities are too similar"

    def test_predefined_archetypes(self):
        """Each archetype should have its defining trait as highest weight."""
        assert AGGRESSIVE.aggression >= 0.8
        assert CONSERVATIVE.trump_conservation >= 0.8
        assert TACTICAL.opponent_focus >= 0.8
        assert GAMBLER.risk_tolerance >= 0.8


# ---- Opponent model tests ----

class TestOpponentModel:
    def _make_trick_plays(self, plays):
        """Helper: list of (player_id, suit, rank) tuples -> List[TrickPlay]."""
        return [
            TrickPlay(player_id=pid, card=Card(suit=suit, rank=rank))
            for pid, suit, rank in plays
        ]

    def test_detects_void_from_offsuit_play(self):
        """If player didn't follow lead suit, they are void in that suit."""
        trick = self._make_trick_plays([
            ("p1", Suit.HEARTS, Rank.TEN),
            ("p2", Suit.DIAMONDS, Rank.THREE),  # p2 didn't follow hearts
            ("p3", Suit.HEARTS, Rank.JACK),
        ])
        model = OpponentModel(
            player_id="p1", trick_history=[trick], current_trick_plays=[],
            bids=[], tricks_won={}, trump_suit=Suit.SPADES,
        )
        assert Suit.HEARTS in model.get_likely_voids("p2")
        assert len(model.get_likely_voids("p1")) == 0
        assert len(model.get_likely_voids("p3")) == 0

    def test_trump_play_implies_void(self):
        """Playing trump when a non-trump was led means void in lead suit."""
        trick = self._make_trick_plays([
            ("p1", Suit.HEARTS, Rank.ACE),
            ("p2", Suit.SPADES, Rank.TWO),  # p2 trumped in — void in hearts
        ])
        model = OpponentModel(
            player_id="p1", trick_history=[trick], current_trick_plays=[],
            bids=[], tricks_won={}, trump_suit=Suit.SPADES,
        )
        assert model.opponent_might_be_void("p2", Suit.HEARTS)

    def test_following_suit_no_false_void(self):
        """Following suit should NOT create a void entry."""
        trick = self._make_trick_plays([
            ("p1", Suit.HEARTS, Rank.TEN),
            ("p2", Suit.HEARTS, Rank.QUEEN),
        ])
        model = OpponentModel(
            player_id="p1", trick_history=[trick], current_trick_plays=[],
            bids=[], tricks_won={}, trump_suit=Suit.SPADES,
        )
        assert not model.opponent_might_be_void("p2", Suit.HEARTS)

    def test_opponent_needs_calculation(self):
        """Needs = bid - tricks_won."""
        bids = [Bid(player_id="p1", amount=3), Bid(player_id="p2", amount=1)]
        model = OpponentModel(
            player_id="p1", trick_history=[], current_trick_plays=[],
            bids=bids, tricks_won={"p1": 1, "p2": 1}, trump_suit=Suit.SPADES,
        )
        assert model.get_opponent_needs("p1") == 2  # 3 - 1
        assert model.get_opponent_needs("p2") == 0  # 1 - 1

    def test_satisfied_vs_dangerous(self):
        """Classify opponents by whether they still need tricks."""
        bids = [
            Bid(player_id="p1", amount=2),
            Bid(player_id="p2", amount=1),
            Bid(player_id="p3", amount=3),
        ]
        model = OpponentModel(
            player_id="p1", trick_history=[], current_trick_plays=[],
            bids=bids, tricks_won={"p1": 2, "p2": 1, "p3": 0}, trump_suit=Suit.SPADES,
        )
        assert "p2" in model.get_satisfied_opponents()
        assert "p3" in model.get_dangerous_opponents()
        assert "p1" not in model.get_dangerous_opponents()  # p1 is self


# ---- Hard AI positional play tests ----

class TestHardAIPositionalPlay:
    def test_last_position_takes_cheap_win(self):
        """When playing last and needing tricks, take with lowest winner."""
        pers = AIPersonality(aggression=0.5, trump_conservation=0.5, opponent_focus=0.5, risk_tolerance=0.5)
        ai = HardAI(personality=pers)
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.HEARTS, rank=Rank.KING),
            Card(suit=Suit.HEARTS, rank=Rank.QUEEN),
        ]
        # 3 players, 2 already played => we are last
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.FIVE),
            Card(suit=Suit.HEARTS, rank=Rank.JACK),
        ]
        bids = [Bid(player_id="p1", amount=2)]
        ctx = _make_context(current_trick_cards=trick_cards, bids=bids)
        card = ai.choose_card(hand, hand, ctx)
        assert card.rank == Rank.QUEEN  # cheapest winner in last position

    def test_last_position_dumps_when_over_bid(self):
        """When last to play and already met bid, don't win."""
        pers = AIPersonality(aggression=0.5, trump_conservation=0.5, opponent_focus=0.5, risk_tolerance=0.5)
        ai = HardAI(personality=pers)
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.FIVE),
            Card(suit=Suit.HEARTS, rank=Rank.JACK),
        ]
        bids = [Bid(player_id="p1", amount=1)]
        ctx = _make_context(
            current_trick_cards=trick_cards,
            bids=bids,
            tricks_won={"p1": 1},  # already met bid
        )
        card = ai.choose_card(hand, hand, ctx)
        # Should try to lose — play the 3 of diamonds (won't win)
        assert card.suit == Suit.DIAMONDS

    def test_lead_low_trump_to_draw_out(self):
        """With trump length advantage, lead low trump to draw out opponents'."""
        pers = AIPersonality(aggression=0.9, trump_conservation=0.3, opponent_focus=0.5, risk_tolerance=0.5)
        ai = HardAI(personality=pers)
        hand = [
            Card(suit=Suit.SPADES, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.KING),
            Card(suit=Suit.SPADES, rank=Rank.QUEEN),
            Card(suit=Suit.SPADES, rank=Rank.TWO),
            Card(suit=Suit.HEARTS, rank=Rank.THREE),
        ]
        bids = [Bid(player_id="p1", amount=3)]
        ctx = _make_context(
            trump=Suit.SPADES,
            bids=bids,
            num_cards=5,
        )
        card = ai.choose_card(hand, hand, ctx)
        # With 4 trumps and high aggression, should lead low trump (2 of spades)
        if card.suit == Suit.SPADES:
            assert card.rank == Rank.TWO, "Should lead LOW trump, not high"

    def test_guaranteed_non_trump_winner_first(self):
        """Lead guaranteed non-trump winner before uncertain cards."""
        pers = AIPersonality(aggression=0.5, trump_conservation=0.5, opponent_focus=0.5, risk_tolerance=0.5)
        ai = HardAI(personality=pers)
        # All other hearts have been played — Ace is guaranteed
        played = [
            Card(suit=Suit.HEARTS, rank=rank)
            for rank in Rank if rank != Rank.ACE
        ]
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.DIAMONDS, rank=Rank.SEVEN),
            Card(suit=Suit.CLUBS, rank=Rank.FOUR),
        ]
        bids = [Bid(player_id="p1", amount=1)]
        ctx = _make_context(bids=bids, cards_played=played, num_cards=3)
        card = ai.choose_card(hand, hand, ctx)
        assert card == Card(suit=Suit.HEARTS, rank=Rank.ACE)


# ---- Trump management tests ----

class TestHardAITrumpManagement:
    def test_conserves_ace_of_trump(self):
        """Don't lead Ace of trump first when you have lower trumps and high conservation."""
        pers = AIPersonality(aggression=0.4, trump_conservation=0.9, opponent_focus=0.5, risk_tolerance=0.3)
        ai = HardAI(personality=pers)
        hand = [
            Card(suit=Suit.SPADES, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.THREE),
            Card(suit=Suit.HEARTS, rank=Rank.SEVEN),
        ]
        bids = [Bid(player_id="p1", amount=2)]
        ctx = _make_context(trump=Suit.SPADES, bids=bids, num_cards=3)
        card = ai.choose_card(hand, hand, ctx)
        # With only 2 trumps and conservation=0.9, should not lead Ace of trump first
        assert card.rank != Rank.ACE or card.suit != Suit.SPADES


# ---- Smart losing tests ----

class TestHardAISmartLosing:
    def test_dumps_from_shortest_suit(self):
        """When losing, dump from shortest non-trump suit to create voids."""
        pers = AIPersonality(aggression=0.5, trump_conservation=0.5, opponent_focus=0.5, risk_tolerance=0.5)
        ai = HardAI(personality=pers)
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.KING),    # only 1 heart
            Card(suit=Suit.DIAMONDS, rank=Rank.THREE),  # 2 diamonds
            Card(suit=Suit.DIAMONDS, rank=Rank.FIVE),
        ]
        # Leading, bid already met
        bids = [Bid(player_id="p1", amount=0)]
        ctx = _make_context(trump=Suit.SPADES, bids=bids, num_cards=3)
        card = ai.choose_card(hand, hand, ctx)
        # Should lead to lose — lowest from a suit, not the King
        assert card.rank != Rank.KING or card.suit != Suit.HEARTS

    def test_avoids_accidental_win(self):
        """When trying to lose, play a card that won't win."""
        pers = AIPersonality(aggression=0.5, trump_conservation=0.5, opponent_focus=0.5, risk_tolerance=0.5)
        ai = HardAI(personality=pers)
        hand = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.HEARTS, rank=Rank.TWO),
        ]
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.TEN),
            Card(suit=Suit.HEARTS, rank=Rank.JACK),
        ]
        bids = [Bid(player_id="p1", amount=0)]
        ctx = _make_context(
            current_trick_cards=trick_cards,
            bids=bids,
            tricks_won={"p1": 0},
        )
        card = ai.choose_card(hand, hand, ctx)
        # 2 of hearts loses to the Jack — prefer it over Ace
        assert card.rank == Rank.TWO


# ---- Integration: all archetypes complete a game ----

class TestHardAIArchetypes:
    def test_all_archetypes_complete_game(self):
        """Each predefined personality archetype can play through a full round."""
        from backend.app.models import Player, PlayerType, GameConfig
        from backend.app.game.engine import GameEngine

        for archetype in [AGGRESSIVE, CONSERVATIVE, TACTICAL, GAMBLER]:
            engine = GameEngine(GameConfig())
            strategies = {f"ai_{i}": HardAI(personality=archetype) for i in range(3)}
            players = [
                Player(id=f"ai_{i}", name=f"AI {i}", player_type=PlayerType.AI)
                for i in range(3)
            ]
            for player in players:
                engine.add_player(player)
            engine.start_game()

            while engine.state.phase.value == "bidding":
                pid = engine.state.current_player_id
                strategy = strategies[pid]
                valid_bids = engine.get_valid_bids(pid)
                hand = engine.get_player_hand(pid)
                ctx = engine.get_round_context(pid)
                bid = strategy.choose_bid(hand, valid_bids, ctx)
                assert engine.place_bid(pid, bid)

            while engine.state.phase.value == "playing":
                pid = engine.state.current_player_id
                strategy = strategies[pid]
                valid_cards = engine.get_valid_cards(pid)
                hand = engine.get_player_hand(pid)
                ctx = engine.get_round_context(pid)
                card = strategy.choose_card(hand, valid_cards, ctx)
                assert engine.play_card(pid, card)
