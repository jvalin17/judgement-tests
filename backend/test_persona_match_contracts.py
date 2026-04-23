"""Persona matching contract tests.

Focused, deterministic tests for persona loader, scoring, ranking, and tier gating.
"""
import random

import pytest

from backend.app.ml.analysis.persona_loader import DIMENSIONS, get_persona_by_id, load_personas
from backend.app.ml.analysis.persona_match import (
    _evaluate_trigger,
    best_personas,
    compute_tier,
    pick_persona,
    score_persona,
    TIER_CASUAL,
    TIERS_BY_LEVEL,
)


def _neutral_vec():
    return {dim: 0.5 for dim in DIMENSIONS}


def _vec(**overrides):
    vec = _neutral_vec()
    vec.update(overrides)
    return vec


class TestPersonaLoaderContracts:
    def test_load_personas_returns_nonempty_tuple(self):
        personas = load_personas()
        assert isinstance(personas, tuple)
        assert len(personas) > 0

    def test_persona_schema_has_required_fields(self):
        valid_categories = {"superhero", "animal", "poker", "cartoon", "pokemon", "mythology", "achievement"}
        for persona in load_personas():
            assert persona.id
            assert persona.name
            assert persona.tagline
            assert persona.category in valid_categories

    def test_trait_and_weight_dimensions_match_dimensions_constant(self):
        for persona in load_personas():
            assert set(persona.traits.keys()) == set(DIMENSIONS)
            assert set(persona.weights.keys()) == set(DIMENSIONS)

    def test_trait_values_are_in_unit_range(self):
        for persona in load_personas():
            for value in persona.traits.values():
                assert 0.0 <= value <= 1.0

    def test_weight_values_are_non_negative(self):
        for persona in load_personas():
            for value in persona.weights.values():
                assert value >= 0.0

    def test_get_persona_by_id_unknown_raises(self):
        with pytest.raises(KeyError):
            get_persona_by_id("persona-does-not-exist")


class TestTriggerContracts:
    @pytest.mark.parametrize(
        "trigger,vec,expected",
        [
            ({"type": "min", "dim": "precision", "threshold": 0.8}, _vec(precision=0.8), True),
            ({"type": "min", "dim": "precision", "threshold": 0.8}, _vec(precision=0.79), False),
            ({"type": "max", "dim": "risk", "threshold": 0.3}, _vec(risk=0.3), True),
            ({"type": "max", "dim": "risk", "threshold": 0.3}, _vec(risk=0.31), False),
            ({"type": "range", "dim": "planning", "lo": 0.4, "hi": 0.6}, _vec(planning=0.4), True),
            ({"type": "range", "dim": "planning", "lo": 0.4, "hi": 0.6}, _vec(planning=0.61), False),
        ],
    )
    def test_trigger_primitives(self, trigger, vec, expected):
        assert _evaluate_trigger(trigger, vec) is expected

    def test_combo_trigger_requires_all_conditions(self):
        trigger = {
            "type": "combo",
            "conditions": [
                {"type": "max", "dim": "consistency", "threshold": 0.35},
                {"type": "min", "dim": "planning", "threshold": 0.55},
            ],
        }
        assert _evaluate_trigger(trigger, _vec(consistency=0.2, planning=0.7)) is True
        assert _evaluate_trigger(trigger, _vec(consistency=0.2, planning=0.3)) is False


class TestScoreContracts:
    def test_exact_trait_match_scores_higher_than_inverted_traits(self):
        persona = get_persona_by_id("batman")
        exact = dict(persona.traits)
        inverted = {dim: 1.0 - persona.traits[dim] for dim in DIMENSIONS}

        assert score_persona(exact, persona) > score_persona(inverted, persona)

    def test_high_weight_mismatch_penalized_more_than_low_weight_mismatch(self):
        persona = get_persona_by_id("batman")
        match_all = dict(persona.traits)

        mismatch_low_weight = dict(match_all)
        mismatch_low_weight["risk"] = 1.0 - persona.traits["risk"]

        mismatch_high_weight = dict(match_all)
        mismatch_high_weight["planning"] = 1.0 - persona.traits["planning"]

        low_penalty_score = score_persona(mismatch_low_weight, persona)
        high_penalty_score = score_persona(mismatch_high_weight, persona)
        assert low_penalty_score > high_penalty_score

    def test_trigger_bonus_increases_score(self):
        persona = get_persona_by_id("sniper")
        with_trigger = _vec(precision=0.9)
        without_trigger = _vec(precision=0.5)

        assert score_persona(with_trigger, persona) > score_persona(without_trigger, persona)


class TestBestPersonasContracts:
    def test_returns_top_k_sorted_and_unique(self):
        top = best_personas(_neutral_vec(), top_k=7)

        assert len(top) == 7
        ids = [pid for pid, _ in top]
        scores = [score for _, score in top]
        assert len(set(ids)) == len(ids)
        assert scores == sorted(scores, reverse=True)

    def test_respects_allowed_categories(self):
        allowed = TIER_CASUAL
        personas_map = {p.id: p for p in load_personas()}
        top = best_personas(_neutral_vec(), allowed_categories=allowed)

        assert len(top) > 0
        for pid, _ in top:
            assert personas_map[pid].category in allowed

    def test_recent_persona_is_penalized(self):
        vec = _neutral_vec()
        without_recent = best_personas(vec, recent_ids=[])
        with_recent = best_personas(vec, recent_ids=[without_recent[0][0]])

        assert with_recent[0][1] <= without_recent[0][1]


class TestPickPersonaContracts:
    @pytest.mark.parametrize(
        "difficulty,challenge,must_lose,expected",
        [
            ("hard", True, True, "elite"),
            ("smart_hard", True, True, "elite"),
            ("hard", False, False, "competitive"),
            ("easy", True, False, "competitive"),
            ("medium", False, False, "standard"),
            ("easy", False, False, "casual"),
        ],
    )
    def test_compute_tier_mapping(self, difficulty, challenge, must_lose, expected):
        assert compute_tier(difficulty, challenge_mode=challenge, must_lose_mode=must_lose) == expected

    @pytest.mark.parametrize(
        "tier,allowed",
        [
            ("elite", TIERS_BY_LEVEL["elite"]),
            ("competitive", TIERS_BY_LEVEL["competitive"]),
            ("standard", TIERS_BY_LEVEL["standard"]),
            ("casual", TIERS_BY_LEVEL["casual"]),
        ],
    )
    def test_pick_persona_respects_tier_categories(self, tier, allowed):
        personas_map = {p.id: p for p in load_personas()}
        vec = _neutral_vec()

        for seed in range(40):
            persona = pick_persona(vec, rng=random.Random(seed), tier=tier)
            assert personas_map[persona.id].category in allowed

    def test_pick_persona_is_deterministic_with_seed(self):
        vec = _neutral_vec()
        a = pick_persona(vec, rng=random.Random(123), tier="competitive")
        b = pick_persona(vec, rng=random.Random(123), tier="competitive")
        assert a.id == b.id
