"""Tests for fingerprinting and mascot integration flows."""
import random


from backend.app.ml.analysis.persona_loader import load_personas, DIMENSIONS
from backend.app.ml.analysis.fingerprint import compute_fingerprint, project_round
from backend.app.ml.analysis.persona_match import best_personas
from backend.app.models.session import SessionLog, RoundLog
from backend.app.models.game import Bid


# ---- Fingerprint tests ----

def _make_session_with_rounds(rounds_data):
    """Helper: create a SessionLog with given round data.
    Each round_data is (num_cards, bids_dict, tricks_won_dict).
    """
    session = SessionLog(game_id="test")
    for index, (num_cards, bids_dict, tricks_won) in enumerate(rounds_data):
        bids = [Bid(player_id=pid, amount=amt) for pid, amt in bids_dict.items()]
        session.rounds.append(RoundLog(
            round_number=index + 1,
            num_cards=num_cards,
            trump_suit="spades",
            dealer_id="p1",
            bids=bids,
            tricks_won=tricks_won,
            scores={},
        ))
    return session


class TestFingerprint:
    def test_high_bid_scores_high_risk(self):
        session = _make_session_with_rounds([
            (7, {"p1": 6, "p2": 2}, {"p1": 6, "p2": 1}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["risk"] > 0.8

    def test_exact_hit_scores_high_planning(self):
        session = _make_session_with_rounds([
            (5, {"p1": 3, "p2": 2}, {"p1": 3, "p2": 2}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["planning"] >= 0.9

    def test_low_bid_scores_low_risk(self):
        session = _make_session_with_rounds([
            (7, {"p1": 1, "p2": 3}, {"p1": 1, "p2": 3}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["risk"] < 0.3

    def test_missed_bid_scores_low_planning(self):
        session = _make_session_with_rounds([
            (10, {"p1": 0, "p2": 5}, {"p1": 5, "p2": 5}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["planning"] < 0.6

    def test_all_values_in_unit_range(self):
        rng = random.Random(42)
        for _ in range(50):
            num_cards = rng.randint(1, 10)
            bids = {"p1": rng.randint(0, num_cards), "p2": rng.randint(0, num_cards)}
            tricks = {"p1": rng.randint(0, num_cards), "p2": num_cards - rng.randint(0, num_cards)}
            session = _make_session_with_rounds([(num_cards, bids, tricks)])
            vec = compute_fingerprint(session, "p1")
            for dim, value in vec.items():
                assert 0.0 <= value <= 1.0, f"{dim} = {value}"

    def test_empty_session_returns_neutral(self):
        session = SessionLog(game_id="test")
        vec = compute_fingerprint(session, "p1")
        for dim in DIMENSIONS:
            assert vec[dim] == 0.5

    def test_fingerprint_returns_all_11_dimensions(self):
        session = _make_session_with_rounds([
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert len(vec) == 11
        for dim in DIMENSIONS:
            assert dim in vec

    def test_multi_round_consistency(self):
        session = _make_session_with_rounds([
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),
            (4, {"p1": 1, "p2": 3}, {"p1": 1, "p2": 3}),
            (3, {"p1": 1, "p2": 2}, {"p1": 1, "p2": 2}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["consistency"] > 0.8

    def test_inconsistent_player_lower_consistency(self):
        consistent_session = _make_session_with_rounds([
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),
            (5, {"p1": 3, "p2": 2}, {"p1": 3, "p2": 2}),
            (5, {"p1": 1, "p2": 4}, {"p1": 1, "p2": 4}),
        ])
        inconsistent_session = _make_session_with_rounds([
            (5, {"p1": 0, "p2": 3}, {"p1": 4, "p2": 1}),
            (5, {"p1": 5, "p2": 3}, {"p1": 0, "p2": 5}),
            (5, {"p1": 0, "p2": 3}, {"p1": 3, "p2": 2}),
        ])
        consistent_vec = compute_fingerprint(consistent_session, "p1")
        inconsistent_vec = compute_fingerprint(inconsistent_session, "p1")
        assert consistent_vec["consistency"] > inconsistent_vec["consistency"]


# ---- New dimension tests ----

class TestBoldness:
    def test_bold_bidder_high_boldness(self):
        # Bid 5 out of 7 and make all 5 → bold
        session = _make_session_with_rounds([
            (7, {"p1": 5, "p2": 2}, {"p1": 5, "p2": 2}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["boldness"] > 0.65

    def test_reckless_bidder_low_boldness(self):
        # Bid 5 out of 7 but only make 1 → reckless, low boldness
        session = _make_session_with_rounds([
            (7, {"p1": 5, "p2": 2}, {"p1": 1, "p2": 6}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["boldness"] < 0.25

    def test_commendable_effort_mid_boldness(self):
        # Bid 5 out of 7 and make 4 → commendable effort
        session = _make_session_with_rounds([
            (7, {"p1": 5, "p2": 2}, {"p1": 4, "p2": 3}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert 0.35 < vec["boldness"] < 0.65

    def test_zero_bid_zero_boldness(self):
        session = _make_session_with_rounds([
            (5, {"p1": 0, "p2": 3}, {"p1": 0, "p2": 5}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["boldness"] == 0.0


class TestPrecision:
    def test_exact_hits_high_precision(self):
        session = _make_session_with_rounds([
            (8, {"p1": 3, "p2": 5}, {"p1": 3, "p2": 5}),
            (6, {"p1": 2, "p2": 4}, {"p1": 2, "p2": 4}),
            (4, {"p1": 1, "p2": 3}, {"p1": 1, "p2": 3}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["precision"] > 0.8

    def test_all_misses_low_precision(self):
        session = _make_session_with_rounds([
            (8, {"p1": 3, "p2": 5}, {"p1": 1, "p2": 7}),
            (6, {"p1": 4, "p2": 2}, {"p1": 1, "p2": 5}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["precision"] < 0.2


class TestResilience:
    def test_recovery_high_resilience(self):
        # miss, hit, miss, hit → 100% recovery rate
        session = _make_session_with_rounds([
            (5, {"p1": 3, "p2": 2}, {"p1": 1, "p2": 4}),  # miss
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),  # hit (recovery)
            (5, {"p1": 4, "p2": 1}, {"p1": 2, "p2": 3}),  # miss
            (5, {"p1": 1, "p2": 4}, {"p1": 1, "p2": 4}),  # hit (recovery)
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["resilience"] >= 0.9

    def test_no_recovery_low_resilience(self):
        # miss, miss, miss, hit → only 1/3 recovery
        session = _make_session_with_rounds([
            (5, {"p1": 3, "p2": 2}, {"p1": 1, "p2": 4}),  # miss
            (5, {"p1": 3, "p2": 2}, {"p1": 0, "p2": 5}),  # miss
            (5, {"p1": 4, "p2": 1}, {"p1": 2, "p2": 3}),  # miss
            (5, {"p1": 1, "p2": 4}, {"p1": 1, "p2": 4}),  # hit
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["resilience"] < 0.5

    def test_never_missed_neutral_resilience(self):
        session = _make_session_with_rounds([
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),
            (5, {"p1": 3, "p2": 2}, {"p1": 3, "p2": 2}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["resilience"] == 0.5


class TestClutch:
    def test_late_game_dominance_high_clutch(self):
        # Miss early rounds, nail late rounds
        session = _make_session_with_rounds([
            (5, {"p1": 3, "p2": 2}, {"p1": 0, "p2": 5}),  # miss
            (5, {"p1": 3, "p2": 2}, {"p1": 0, "p2": 5}),  # miss
            (5, {"p1": 3, "p2": 2}, {"p1": 0, "p2": 5}),  # miss
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),  # hit (late)
            (5, {"p1": 1, "p2": 4}, {"p1": 1, "p2": 4}),  # hit (late)
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["clutch"] > 0.7

    def test_early_strong_late_weak_low_clutch(self):
        session = _make_session_with_rounds([
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),  # hit
            (5, {"p1": 3, "p2": 2}, {"p1": 3, "p2": 2}),  # hit
            (5, {"p1": 1, "p2": 4}, {"p1": 1, "p2": 4}),  # hit
            (5, {"p1": 3, "p2": 2}, {"p1": 0, "p2": 5}),  # miss (late)
            (5, {"p1": 4, "p2": 1}, {"p1": 1, "p2": 4}),  # miss (late)
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["clutch"] < 0.4


class TestTrajectory:
    def test_improving_player_high_trajectory(self):
        # Bad first half, good second half
        session = _make_session_with_rounds([
            (5, {"p1": 4, "p2": 1}, {"p1": 1, "p2": 4}),  # big miss
            (5, {"p1": 3, "p2": 2}, {"p1": 0, "p2": 5}),  # big miss
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),  # exact hit
            (5, {"p1": 3, "p2": 2}, {"p1": 3, "p2": 2}),  # exact hit
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["trajectory"] > 0.7

    def test_declining_player_low_trajectory(self):
        session = _make_session_with_rounds([
            (5, {"p1": 2, "p2": 3}, {"p1": 2, "p2": 3}),  # exact
            (5, {"p1": 3, "p2": 2}, {"p1": 3, "p2": 2}),  # exact
            (5, {"p1": 4, "p2": 1}, {"p1": 1, "p2": 4}),  # big miss
            (5, {"p1": 3, "p2": 2}, {"p1": 0, "p2": 5}),  # big miss
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["trajectory"] < 0.3



# ---- Integration: fingerprint → match ----

class TestFingerprintToMatch:
    def test_aggressive_player_gets_high_risk_persona(self):
        session = _make_session_with_rounds([
            (7, {"p1": 6, "p2": 2}, {"p1": 3, "p2": 4}),
            (5, {"p1": 5, "p2": 1}, {"p1": 2, "p2": 3}),
            (8, {"p1": 7, "p2": 3}, {"p1": 4, "p2": 4}),
        ])
        vec = compute_fingerprint(session, "p1")
        assert vec["risk"] > 0.7
        assert vec["aggression"] > 0.5
        top = best_personas(vec)
        assert len(top) == 7
        known_ids = {p.id for p in load_personas()}
        assert all(pid in known_ids for pid, _ in top)

    def test_conservative_player_gets_conservative_persona(self):
        session = _make_session_with_rounds([
            (7, {"p1": 1, "p2": 4}, {"p1": 1, "p2": 3}),
            (5, {"p1": 0, "p2": 3}, {"p1": 0, "p2": 2}),
            (8, {"p1": 1, "p2": 5}, {"p1": 1, "p2": 3}),
        ])
        vec = compute_fingerprint(session, "p1")
        top = best_personas(vec)
        top_ids = [pair[0] for pair in top]
        conservative_personas = {
            "turtle", "nit", "elephant", "snorlax", "ant", "owl",
            "shaktimaan", "rock", "zen_master",
        }
        assert any(pid in conservative_personas for pid in top_ids)

    def test_game_over_event_includes_persona(self):
        from backend.app.models.events import game_over_event, PersonaAward
        persona = PersonaAward(
            persona_id="fox",
            persona_name="The Fox",
            persona_category="animal",
            persona_tagline="Cunning",
            traits={"risk": 0.6},
            player_traits={"risk": 0.5},
        )
        event = game_over_event(
            final_scores={"p1": 20},
            winners=["p1"],
            persona=persona,
        )
        assert event.event_type.value == "game_over"
        assert event.data["persona"]["persona_id"] == "fox"
        assert event.data["persona"]["persona_name"] == "The Fox"
        assert event.data["persona"]["player_traits"]["risk"] == 0.5

    def test_game_over_event_without_persona(self):
        from backend.app.models.events import game_over_event
        event = game_over_event(final_scores={"p1": 20}, winners=["p1"])
        assert event.data["persona"] is None


class TestMascotIntegration:
    """Integration test: play a full game and verify persona is in GAME_OVER event."""

    def test_full_game_emits_persona_in_game_over(self):
        import random as stdlib_random
        from backend.app.models import Player, PlayerType, AIDifficulty, GameConfig, DealingVariant
        from backend.app.models.events import EventType
        from backend.app.game_manager import GameManager

        manager = GameManager()
        config = GameConfig(variant=DealingVariant.THREE_QUICK)
        players = [
            Player(id="human1", name="Alice", player_type=PlayerType.HUMAN),
            Player(id="ai1", name="Bot", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
        ]

        collected_events = []
        managed = manager.create_game(config, players)
        managed.add_event_callback(lambda e: collected_events.append(e))
        managed.engine.start_game()

        rng = stdlib_random.Random(42)
        max_iterations = 500
        iteration = 0
        while managed.engine.state.phase.value != "game_over" and iteration < max_iterations:
            iteration += 1
            phase = managed.engine.state.phase.value
            pid = managed.engine.state.current_player_id
            if phase == "round_over":
                managed.engine.continue_game()
                continue
            if not pid or pid.startswith("ai"):
                continue
            if phase == "bidding":
                valid = managed.engine.get_valid_bids(pid)
                managed.engine.place_bid(pid, rng.choice(valid))
            elif phase == "playing":
                valid = managed.engine.get_valid_cards(pid)
                managed.engine.play_card(pid, rng.choice(valid))

        game_over_events = [
            e for e in collected_events
            if e.event_type == EventType.GAME_OVER and e.player_id == "human1"
        ]
        assert len(game_over_events) == 1, f"Expected 1 GAME_OVER for human, got {len(game_over_events)}"

        event = game_over_events[0]
        persona = event.data.get("persona")
        assert persona is not None, "Persona should be included in GAME_OVER event"
        assert "persona_name" in persona
        assert "persona_tagline" in persona
        assert "traits" in persona
        assert "player_traits" in persona
        assert len(persona["player_traits"]) == 11

    def test_ai_only_game_has_no_persona(self):
        from backend.app.models import Player, PlayerType, AIDifficulty, GameConfig, DealingVariant
        from backend.app.models.events import EventType
        from backend.app.game_manager import GameManager

        manager = GameManager()
        config = GameConfig(variant=DealingVariant.THREE_QUICK)
        players = [
            Player(id="ai1", name="Bot1", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
            Player(id="ai2", name="Bot2", player_type=PlayerType.AI, ai_difficulty=AIDifficulty.EASY),
        ]

        collected_events = []
        managed = manager.create_game(config, players)
        managed.add_event_callback(lambda e: collected_events.append(e))
        managed.engine.start_game()

        max_iterations = 500
        iteration = 0
        while managed.engine.state.phase.value != "game_over" and iteration < max_iterations:
            iteration += 1
            if managed.engine.state.phase.value == "round_over":
                managed.engine.continue_game()

        game_over_events = [e for e in collected_events if e.event_type == EventType.GAME_OVER]
        assert len(game_over_events) == 2
        for event in game_over_events:
            assert event.data.get("persona") is None


