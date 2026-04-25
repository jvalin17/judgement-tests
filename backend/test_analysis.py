"""Tests for the mascot analysis module: persona loader, fingerprint, and matcher."""
import random

import pytest

from backend.app.ml.analysis.persona_loader import load_personas, get_persona_by_id, DIMENSIONS
from backend.app.ml.analysis.fingerprint import compute_fingerprint, project_round
from backend.app.ml.analysis.persona_match import (
    score_persona, best_personas, pick_persona, _evaluate_trigger,
    compute_tier, TIER_ELITE, TIER_COMPETITIVE, TIER_STANDARD, TIER_CASUAL,
    TIERS_BY_LEVEL,
)
from backend.app.models.session import SessionLog, RoundLog
from backend.app.models.game import Bid


# ---- Persona loader tests ----

class TestPersonaLoader:
    def test_loads_without_errors(self):
        personas = load_personas()
        assert len(personas) > 0

    def test_persona_count(self):
        assert len(load_personas()) == 75

    def test_all_personas_have_11_traits(self):
        for persona in load_personas():
            assert len(persona.traits) == 11, f"{persona.id} has {len(persona.traits)} traits"
            for dim in DIMENSIONS:
                assert dim in persona.traits, f"{persona.id} missing {dim}"

    def test_all_personas_have_11_weights(self):
        for persona in load_personas():
            assert len(persona.weights) == 11, f"{persona.id} has {len(persona.weights)} weights"
            for dim in DIMENSIONS:
                assert dim in persona.weights, f"{persona.id} missing weight {dim}"

    def test_all_trait_values_in_unit_range(self):
        for persona in load_personas():
            for dim, value in persona.traits.items():
                assert 0.0 <= value <= 1.0, f"{persona.id}.{dim} = {value}"

    def test_all_weight_values_positive(self):
        for persona in load_personas():
            for dim, value in persona.weights.items():
                assert value >= 0.0, f"{persona.id}.weights.{dim} = {value}"

    def test_all_personas_have_required_fields(self):
        valid_categories = {"superhero", "animal", "cartoon", "pokemon", "mythology", "achievement"}
        for persona in load_personas():
            assert persona.id
            assert persona.name
            assert persona.tagline
            assert persona.category in valid_categories, f"{persona.id} has unknown category {persona.category}"

    def test_get_persona_by_id_found(self):
        persona = get_persona_by_id("batman")
        assert persona.name == "Batman"

    def test_get_persona_by_id_not_found(self):
        with pytest.raises(KeyError):
            get_persona_by_id("nonexistent")

    def test_categories_all_represented(self):
        categories = {persona.category for persona in load_personas()}
        assert categories == {"superhero", "animal", "cartoon", "pokemon", "mythology", "achievement"}

    def test_key_dims_returns_top_3(self):
        persona = get_persona_by_id("batman")
        key = persona.key_dims
        assert len(key) == 3
        # Batman's top weights are planning (2.0), precision (1.8), consistency (1.5)
        assert "planning" in key
        assert "precision" in key

    def test_achievement_personas_have_triggers(self):
        achievement = [p for p in load_personas() if p.category == "achievement"]
        assert len(achievement) == 10
        for persona in achievement:
            assert len(persona.triggers) > 0, f"{persona.id} has no triggers"


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


# ---- Score persona tests ----

class TestScorePersona:
    def test_exact_match_high_score(self):
        persona = get_persona_by_id("batman")
        # Player with traits very close to Batman's
        player_vec = dict(persona.traits)
        score = score_persona(player_vec, persona)
        assert score > 0.95

    def test_opposite_traits_low_score(self):
        persona = get_persona_by_id("batman")
        # Batman: low risk, high planning. Opposite: high risk, low planning
        player_vec = {dim: 1.0 - persona.traits.get(dim, 0.5) for dim in DIMENSIONS}
        score = score_persona(player_vec, persona)
        assert score < 0.6

    def test_weights_affect_scoring(self):
        # Batman has planning weight=2.0, risk weight=0.5
        persona = get_persona_by_id("batman")
        # Player A: matches planning, misses risk
        player_a = dict(persona.traits)
        player_a["risk"] = 1.0 - persona.traits["risk"]  # mismatch risk
        # Player B: matches risk, misses planning
        player_b = dict(persona.traits)
        player_b["planning"] = 1.0 - persona.traits["planning"]  # mismatch planning
        score_a = score_persona(player_a, persona)
        score_b = score_persona(player_b, persona)
        # Player A should score higher (risk has low weight for Batman)
        assert score_a > score_b

    def test_trigger_fires_bonus(self):
        persona = get_persona_by_id("sniper")
        # Player with precision >= 0.85 should trigger the bonus
        player_vec = {dim: 0.5 for dim in DIMENSIONS}
        player_vec["precision"] = 0.9
        score_with_trigger = score_persona(player_vec, persona)

        player_vec_low = dict(player_vec)
        player_vec_low["precision"] = 0.5
        score_without_trigger = score_persona(player_vec_low, persona)

        assert score_with_trigger > score_without_trigger

    def test_combo_trigger_requires_all_conditions(self):
        # wildcard: consistency <= 0.35 AND planning >= 0.55
        player_both = {dim: 0.5 for dim in DIMENSIONS}
        player_both["consistency"] = 0.2
        player_both["planning"] = 0.7
        assert _evaluate_trigger(
            {"type": "combo", "conditions": [
                {"type": "max", "dim": "consistency", "threshold": 0.35},
                {"type": "min", "dim": "planning", "threshold": 0.55},
            ]},
            player_both,
        ) is True

        # Only one condition met
        player_partial = dict(player_both)
        player_partial["planning"] = 0.3  # below threshold
        assert _evaluate_trigger(
            {"type": "combo", "conditions": [
                {"type": "max", "dim": "consistency", "threshold": 0.35},
                {"type": "min", "dim": "planning", "threshold": 0.55},
            ]},
            player_partial,
        ) is False

    def test_affinity_bonus_for_extreme_match(self):
        persona = get_persona_by_id("thor")
        # Thor has high aggression (0.95) with high weight
        # Player with high aggression should get affinity bonus
        player_exact = dict(persona.traits)
        score_exact = score_persona(player_exact, persona)

        # Player with moderate aggression (still close by distance but no affinity)
        player_mid = dict(persona.traits)
        player_mid["aggression"] = 0.65  # close by distance but not extreme
        score_mid = score_persona(player_mid, persona)

        assert score_exact > score_mid


# ---- Persona matching tests ----

class TestPersonaMatch:
    def test_batman_vector_matches_superhero(self):
        batman = get_persona_by_id("batman")
        top = best_personas(dict(batman.traits))
        top_ids = [pair[0] for pair in top]
        # Category-diverse selection ensures superhero category is represented
        personas = {p.id: p for p in load_personas()}
        top_categories = {personas[pid].category for pid in top_ids}
        assert "superhero" in top_categories

    def test_turtle_vector_matches_turtle_or_nit(self):
        turtle = get_persona_by_id("turtle")
        top = best_personas(dict(turtle.traits))
        top_ids = [pair[0] for pair in top]
        conservative = {"turtle", "nit", "snorlax", "ant", "elephant"}
        assert any(pid in conservative for pid in top_ids)

    def test_novelty_penalises_recent(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        without_recent = best_personas(vec, recent_ids=[])
        with_recent = best_personas(vec, recent_ids=[without_recent[0][0]])
        assert with_recent[0][1] <= without_recent[0][1]

    def test_pick_persona_deterministic_with_seed(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        result1 = pick_persona(vec, rng=random.Random(123))
        result2 = pick_persona(vec, rng=random.Random(123))
        assert result1.id == result2.id

    def test_variety_over_multiple_seeds(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        results = set()
        for seed in range(50):
            persona = pick_persona(vec, rng=random.Random(seed))
            results.add(persona.id)
        assert len(results) >= 2

    def test_pick_never_returns_unknown_id(self):
        known_ids = {persona.id for persona in load_personas()}
        rng = random.Random(42)
        for _ in range(100):
            vec = {dim: rng.random() for dim in DIMENSIONS}
            persona = pick_persona(vec, rng=rng)
            assert persona.id in known_ids

    def test_top_k_default_is_7(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        top = best_personas(vec)
        assert len(top) == 7

    def test_category_diversity(self):
        """The top results should include multiple categories, not just one."""
        vec = {dim: 0.5 for dim in DIMENSIONS}
        top = best_personas(vec)
        top_ids = [pair[0] for pair in top]
        personas = {p.id: p for p in load_personas()}
        categories = {personas[pid].category for pid in top_ids}
        assert len(categories) >= 3

    def test_casual_tier_only_returns_animals(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        top = best_personas(vec, allowed_categories=TIER_CASUAL)
        personas_map = {p.id: p for p in load_personas()}
        for pid, _ in top:
            assert personas_map[pid].category in TIER_CASUAL

    def test_elite_tier_includes_superheroes(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        elite_cats = TIER_ELITE | TIER_COMPETITIVE
        top = best_personas(vec, allowed_categories=elite_cats)
        personas_map = {p.id: p for p in load_personas()}
        categories = {personas_map[pid].category for pid, _ in top}
        assert "superhero" in categories

    def test_competitive_tier_excludes_animals(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        competitive_cats = TIER_COMPETITIVE | TIER_STANDARD
        top = best_personas(vec, allowed_categories=competitive_cats)
        personas_map = {p.id: p for p in load_personas()}
        for pid, _ in top:
            assert personas_map[pid].category not in TIER_CASUAL, (
                f"Animal persona {pid} should not appear at competitive tier"
            )

    def test_standard_tier_excludes_superheroes(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        allowed = TIER_STANDARD | TIER_CASUAL
        top = best_personas(vec, allowed_categories=allowed)
        personas_map = {p.id: p for p in load_personas()}
        for pid, _ in top:
            assert personas_map[pid].category not in TIER_ELITE

    def test_compute_tier_elite(self):
        assert compute_tier("hard", challenge_mode=True, must_lose_mode=True) == "elite"
        assert compute_tier("smart_hard", challenge_mode=True, must_lose_mode=True) == "elite"

    def test_compute_tier_competitive(self):
        assert compute_tier("hard", challenge_mode=False, must_lose_mode=False) == "competitive"
        assert compute_tier("easy", challenge_mode=True, must_lose_mode=False) == "competitive"

    def test_compute_tier_standard(self):
        assert compute_tier("medium", challenge_mode=False, must_lose_mode=False) == "standard"

    def test_compute_tier_casual(self):
        assert compute_tier("easy", challenge_mode=False, must_lose_mode=False) == "casual"

    def test_pick_persona_respects_tier(self):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        personas_map = {p.id: p for p in load_personas()}
        for seed in range(50):
            persona = pick_persona(vec, rng=random.Random(seed), tier="casual")
            assert personas_map[persona.id].category in TIER_CASUAL

    def test_achievement_persona_wins_with_trigger(self):
        # A player with precision = 0.95 should get Sniper in top results
        player_vec = {dim: 0.5 for dim in DIMENSIONS}
        player_vec["precision"] = 0.95
        player_vec["planning"] = 0.9
        player_vec["consistency"] = 0.85
        top = best_personas(player_vec)
        top_ids = [pair[0] for pair in top]
        assert "sniper" in top_ids


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


class TestAllPersonasByDifficulty:
    """Exhaustively verify all 75 personas are correctly gated by difficulty tier."""

    @classmethod
    def setup_class(cls):
        cls.all_personas = load_personas()
        cls.by_category = {}
        for p in cls.all_personas:
            cls.by_category.setdefault(p.category, []).append(p)

    def test_all_75_personas_loaded(self):
        assert len(self.all_personas) == 75, f"Expected 75 personas, got {len(self.all_personas)}"

    def test_every_persona_has_a_tier(self):
        """Every persona's category must belong to exactly one tier group."""
        tiered = TIER_ELITE | TIER_COMPETITIVE | TIER_STANDARD | TIER_CASUAL
        for persona in self.all_personas:
            assert persona.category in tiered, (
                f"Persona '{persona.name}' has category '{persona.category}' not in any tier"
            )

    def test_category_to_tier_mapping(self):
        """Verify which categories belong to which tier groups."""
        assert TIER_ELITE == {"superhero", "mythology"}
        assert TIER_COMPETITIVE == {"achievement"}
        assert TIER_STANDARD == {"cartoon", "pokemon"}
        assert TIER_CASUAL == {"animal"}

    def test_tier_levels_exclude_lower(self):
        """Each tier level should NOT include all lower categories."""
        assert "animal" not in TIERS_BY_LEVEL["elite"]
        assert "cartoon" not in TIERS_BY_LEVEL["elite"]
        assert "pokemon" not in TIERS_BY_LEVEL["elite"]
        assert "animal" not in TIERS_BY_LEVEL["competitive"]
        assert "superhero" not in TIERS_BY_LEVEL["standard"]
        assert "mythology" not in TIERS_BY_LEVEL["standard"]
        assert "superhero" not in TIERS_BY_LEVEL["casual"]
        assert "achievement" not in TIERS_BY_LEVEL["casual"]

    def test_elite_picks_from_all_75_never_leak(self):
        """Pick 75 times at elite tier — every result must be superhero/mythology/achievement."""
        allowed = TIERS_BY_LEVEL["elite"]
        self._pick_n_and_verify(75, "elite", allowed)

    def test_competitive_picks_from_all_75_never_leak(self):
        """Pick 75 times at competitive tier — every result must be achievement/cartoon/pokemon."""
        allowed = TIERS_BY_LEVEL["competitive"]
        self._pick_n_and_verify(75, "competitive", allowed)

    def test_standard_picks_from_all_75_never_leak(self):
        """Pick 75 times at standard tier — every result must be cartoon/pokemon/animal."""
        allowed = TIERS_BY_LEVEL["standard"]
        self._pick_n_and_verify(75, "standard", allowed)

    def test_casual_picks_from_all_75_never_leak(self):
        """Pick 75 times at casual tier — every result must be animal."""
        allowed = TIERS_BY_LEVEL["casual"]
        self._pick_n_and_verify(75, "casual", allowed)

    def test_hard_difficulty_maps_to_competitive(self):
        assert compute_tier("hard", challenge_mode=False, must_lose_mode=False) == "competitive"

    def test_hard_challenge_turbulence_maps_to_elite(self):
        assert compute_tier("hard", challenge_mode=True, must_lose_mode=True) == "elite"

    def test_medium_maps_to_standard(self):
        assert compute_tier("medium", challenge_mode=False, must_lose_mode=False) == "standard"

    def test_easy_maps_to_casual(self):
        assert compute_tier("easy", challenge_mode=False, must_lose_mode=False) == "casual"

    def test_every_superhero_reachable_at_elite(self):
        """Every superhero persona must be pickable at elite tier."""
        self._assert_category_reachable("superhero", "elite")

    def test_every_mythology_reachable_at_elite(self):
        self._assert_category_reachable("mythology", "elite")

    def test_every_achievement_reachable_at_competitive(self):
        self._assert_category_reachable("achievement", "competitive")

    def test_every_cartoon_reachable_at_competitive(self):
        self._assert_category_reachable("cartoon", "competitive")

    def test_every_cartoon_reachable_at_standard(self):
        self._assert_category_reachable("cartoon", "standard")

    def test_every_pokemon_reachable_at_standard(self):
        self._assert_category_reachable("pokemon", "standard")

    def test_every_animal_reachable_at_casual(self):
        self._assert_category_reachable("animal", "casual")

    def test_no_animal_in_500_hard_picks(self):
        """500 picks at hard difficulty with varied traits — zero animals."""
        vecs = [
            {dim: 0.5 for dim in DIMENSIONS},
            {dim: 0.9 for dim in DIMENSIONS},
            {dim: 0.1 for dim in DIMENSIONS},
            {dim: (0.1 if i % 2 == 0 else 0.9) for i, dim in enumerate(DIMENSIONS)},
            {dim: random.Random(99).random() for dim in DIMENSIONS},
        ]
        for vec_idx, vec in enumerate(vecs):
            recent = []
            for seed in range(100):
                persona = pick_persona(vec, recent_ids=list(recent),
                                       rng=random.Random(seed + vec_idx * 100), tier="competitive")
                cat = persona.category
                assert cat != "animal", (
                    f"Vec {vec_idx} seed {seed}: got animal '{persona.name}' at competitive tier"
                )
                recent.append(persona.id)

    def test_no_elite_persona_in_500_easy_picks(self):
        """500 picks at easy difficulty — zero superhero/mythology."""
        vecs = [
            {dim: 0.5 for dim in DIMENSIONS},
            {dim: 0.9 for dim in DIMENSIONS},
            {dim: 0.1 for dim in DIMENSIONS},
            {dim: (0.1 if i % 2 == 0 else 0.9) for i, dim in enumerate(DIMENSIONS)},
            {dim: random.Random(42).random() for dim in DIMENSIONS},
        ]
        for vec_idx, vec in enumerate(vecs):
            recent = []
            for seed in range(100):
                persona = pick_persona(vec, recent_ids=list(recent),
                                       rng=random.Random(seed + vec_idx * 100), tier="casual")
                cat = persona.category
                assert cat not in ("superhero", "mythology", "achievement", "cartoon", "pokemon"), (
                    f"Vec {vec_idx} seed {seed}: got '{cat}' persona '{persona.name}' at casual tier"
                )
                recent.append(persona.id)

    def test_25_picks_with_recency_produces_variety(self):
        """25 consecutive picks with recency tracking should produce at least 8 unique personas."""
        vec = {dim: 0.5 for dim in DIMENSIONS}
        recent = []
        seen = set()
        for seed in range(25):
            persona = pick_persona(vec, recent_ids=list(recent),
                                   rng=random.Random(seed), tier="competitive")
            seen.add(persona.id)
            recent.append(persona.id)
        assert len(seen) >= 8, f"Only {len(seen)} unique in 25 picks: {seen}"

    def _pick_n_and_verify(self, n, tier, allowed_cats):
        vec = {dim: 0.5 for dim in DIMENSIONS}
        recent = []
        for seed in range(n):
            persona = pick_persona(vec, recent_ids=list(recent),
                                   rng=random.Random(seed), tier=tier)
            assert persona.category in allowed_cats, (
                f"Tier '{tier}' seed {seed}: got '{persona.category}' persona "
                f"'{persona.name}' — allowed: {allowed_cats}"
            )
            recent.append(persona.id)

    def test_anchor_does_not_dominate_consistent_player(self):
        """A consistent player should not get The Anchor more than 15% of the time in 100 picks."""
        vec = {
            "risk": 0.4, "planning": 0.7, "patience": 0.7, "aggression": 0.4,
            "adaptability": 0.5, "consistency": 0.85, "boldness": 0.45,
            "precision": 0.75, "resilience": 0.6, "clutch": 0.7, "trajectory": 0.5,
        }
        anchor_count = 0
        recent = []
        for seed in range(100):
            persona = pick_persona(vec, recent_ids=list(recent),
                                   rng=random.Random(seed), tier="competitive")
            if persona.id == "anchor":
                anchor_count += 1
            recent.append(persona.id)
            if len(recent) > 15:
                recent = recent[-15:]
        assert anchor_count <= 15, (
            f"The Anchor selected {anchor_count}/100 times — should be <= 15 for variety"
        )

    def test_no_single_persona_exceeds_20_percent_in_100_picks(self):
        """No persona should dominate more than 20% of picks across varied player profiles."""
        profiles = [
            {dim: 0.5 for dim in DIMENSIONS},  # neutral
            {dim: 0.9 for dim in DIMENSIONS},  # maxed
            {dim: 0.1 for dim in DIMENSIONS},  # minimal
            {"risk": 0.8, "planning": 0.3, "patience": 0.2, "aggression": 0.9,
             "adaptability": 0.5, "consistency": 0.3, "boldness": 0.8,
             "precision": 0.3, "resilience": 0.5, "clutch": 0.5, "trajectory": 0.5},  # aggressive
        ]
        for profile_idx, vec in enumerate(profiles):
            counts = {}
            recent = []
            for seed in range(100):
                persona = pick_persona(vec, recent_ids=list(recent),
                                       rng=random.Random(seed), tier="competitive")
                counts[persona.id] = counts.get(persona.id, 0) + 1
                recent.append(persona.id)
                if len(recent) > 15:
                    recent = recent[-15:]
            for persona_id, count in counts.items():
                assert count <= 20, (
                    f"Profile {profile_idx}: '{persona_id}' picked {count}/100 times (max 20)"
                )

    def test_no_persona_weight_exceeds_1_5(self):
        """No persona should have any dimension weight above 1.5 to prevent single-dimension dominance."""
        for persona in load_personas():
            for dim, weight in persona.weights.items():
                assert weight <= 1.5, (
                    f"{persona.id}.weights.{dim} = {weight} — max 1.5 to prevent dominance"
                )

    def test_no_trigger_bonus_exceeds_0_08(self):
        """No persona trigger bonus should exceed 0.08 to prevent trigger-based dominance."""
        for persona in load_personas():
            for trigger in persona.triggers:
                bonus = trigger.get("bonus", 0)
                assert bonus <= 0.08, (
                    f"{persona.id} trigger bonus is {bonus} — max 0.08 to prevent dominance"
                )

    def test_zen_master_does_not_dominate_patient_player(self):
        """A patient player should not get Zen Master more than 15% of the time."""
        vec = {
            "risk": 0.3, "planning": 0.8, "patience": 0.9, "aggression": 0.3,
            "adaptability": 0.5, "consistency": 0.85, "boldness": 0.3,
            "precision": 0.8, "resilience": 0.6, "clutch": 0.75, "trajectory": 0.5,
        }
        zen_count = 0
        recent = []
        for seed in range(100):
            persona = pick_persona(vec, recent_ids=list(recent),
                                   rng=random.Random(seed), tier="competitive")
            if persona.id == "zen_master":
                zen_count += 1
            recent.append(persona.id)
            if len(recent) > 15:
                recent = recent[-15:]
        assert zen_count <= 15, (
            f"Zen Master selected {zen_count}/100 times — should be <= 15 for variety"
        )

    def test_recent_ids_penalty_prevents_immediate_repeat(self):
        """A persona just picked should almost never repeat on the next pick."""
        vec = {dim: 0.5 for dim in DIMENSIONS}
        repeat_count = 0
        for seed in range(100):
            rng = random.Random(seed)
            first = pick_persona(vec, recent_ids=[], rng=rng, tier="competitive")
            second = pick_persona(vec, recent_ids=[first.id], rng=random.Random(seed + 1000), tier="competitive")
            if first.id == second.id:
                repeat_count += 1
        assert repeat_count <= 10, (
            f"Immediate repeats: {repeat_count}/100 — penalty should prevent most repeats"
        )

    def _assert_category_reachable(self, category, tier):
        """Verify every persona in a category is in the allowed set for the tier."""
        personas_in_cat = self.by_category.get(category, [])
        assert len(personas_in_cat) > 0, f"No personas in category '{category}'"
        allowed = TIERS_BY_LEVEL[tier]
        for persona in personas_in_cat:
            assert persona.category in allowed, (
                f"Persona '{persona.name}' (category '{persona.category}') "
                f"not in allowed categories for tier '{tier}': {allowed}"
            )
