"""Tests for the narrative meta-model: TraitSet / Trait / Action.

Frontier reminder: Suddenly never evaluates traits or actions. These tests
assert storage and display (__str__) only — there is deliberately no
resolution logic to exercise.
"""

from __future__ import annotations

import pytest

from suddenly.characters.models import Action, Trait, TraitSet
from tests.factories import CharacterFactory


@pytest.mark.django_db
class TestTraitSet:
    def test_create_set_with_traits_and_actions(self) -> None:
        character = CharacterFactory()
        trait_set = TraitSet.objects.create(character=character, label="Aspects")

        casse_cou = Trait.objects.create(trait_set=trait_set, name="Casse-cou", value=3)
        prudent = Trait.objects.create(trait_set=trait_set, name="Prudent", value=-1)

        action = Action.objects.create(
            trait_set=trait_set,
            name="Foncer dans le tas",
            condition="Quand tu ignores le danger",
            outcome="Tu avances mais tu t'exposes",
        )
        action.traits.set([casse_cou, prudent])

        # related_name wiring (DoD)
        assert list(character.trait_sets.all()) == [trait_set]
        assert set(trait_set.traits.all()) == {casse_cou, prudent}
        assert list(trait_set.actions.all()) == [action]
        assert set(casse_cou.actions.all()) == {action}

    def test_str(self) -> None:
        character = CharacterFactory(name="Ariane")
        trait_set = TraitSet.objects.create(character=character, label="Thèmes")
        assert str(trait_set) == "Thèmes — Ariane"

    def test_default_label(self) -> None:
        character = CharacterFactory()
        trait_set = TraitSet.objects.create(character=character)
        assert trait_set.label == "Traits"


@pytest.mark.django_db
class TestTrait:
    def test_str_with_positive_value(self) -> None:
        ts = TraitSet.objects.create(character=CharacterFactory())
        trait = Trait.objects.create(trait_set=ts, name="Casse-cou", value=3)
        assert str(trait) == "Casse-cou (+3)"

    def test_str_with_negative_value(self) -> None:
        ts = TraitSet.objects.create(character=CharacterFactory())
        trait = Trait.objects.create(trait_set=ts, name="Fragile", value=-2)
        assert str(trait) == "Fragile (-2)"

    def test_str_with_zero_value(self) -> None:
        ts = TraitSet.objects.create(character=CharacterFactory())
        trait = Trait.objects.create(trait_set=ts, name="Neutre", value=0)
        assert str(trait) == "Neutre (+0)"

    def test_valueless_tag(self) -> None:
        """Mist-style tag: no numeric value, str is the name alone."""
        ts = TraitSet.objects.create(character=CharacterFactory())
        trait = Trait.objects.create(trait_set=ts, name="Sworn to the crown")
        assert trait.value is None
        assert str(trait) == "Sworn to the crown"

    def test_value_is_unbounded(self) -> None:
        """No Min/MaxValueValidator: out-of-UI-range values persist as-is."""
        ts = TraitSet.objects.create(character=CharacterFactory())
        trait = Trait.objects.create(trait_set=ts, name="Épique", value=42)
        trait.full_clean()  # would raise if a range validator existed
        assert trait.value == 42


@pytest.mark.django_db
class TestAction:
    def test_str(self) -> None:
        ts = TraitSet.objects.create(character=CharacterFactory(), label="Moves")
        action = Action.objects.create(trait_set=ts, name="Convaincre")
        assert str(action) == "Convaincre → Moves"

    def test_multi_trait_action(self) -> None:
        ts = TraitSet.objects.create(character=CharacterFactory())
        a = Trait.objects.create(trait_set=ts, name="A", value=1)
        b = Trait.objects.create(trait_set=ts, name="B")
        action = Action.objects.create(trait_set=ts, name="Combo")
        action.traits.set([a, b])
        assert action.traits.count() == 2

    def test_action_without_traits_is_allowed(self) -> None:
        ts = TraitSet.objects.create(character=CharacterFactory())
        action = Action.objects.create(trait_set=ts, name="Solo")
        assert action.traits.count() == 0

    def test_cascade_delete_from_character(self) -> None:
        character = CharacterFactory()
        ts = TraitSet.objects.create(character=character)
        Trait.objects.create(trait_set=ts, name="X")
        Action.objects.create(trait_set=ts, name="Y")
        character.delete()
        assert TraitSet.objects.count() == 0
        assert Trait.objects.count() == 0
        assert Action.objects.count() == 0
