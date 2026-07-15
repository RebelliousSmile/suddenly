"""Tests for the suddenly:traitSet JSON-LD extension (issue F).

The extension carries the *shape* of a shared sheet, never value semantics:
Suddenly evaluates nothing, locally or in federation. These tests assert
serialization, omission, tolerant ingestion, and that peers ignoring the
vocabulary are never broken.
"""

from __future__ import annotations

from typing import Any

import pytest

from suddenly.activitypub.inbox import _ingest_trait_sets
from suddenly.activitypub.serializers import serialize_character
from suddenly.characters.models import Action, Character, Trait, TraitSet
from tests.factories import CharacterFactory


def _seed_sheet(character: Character) -> None:
    ts = TraitSet.objects.create(character=character, label="Aspects")
    casse = Trait.objects.create(trait_set=ts, name="Casse-cou", value=3)
    sworn = Trait.objects.create(trait_set=ts, name="Sworn", note="au trône")  # valueless
    action = Action.objects.create(
        trait_set=ts,
        character=character,
        name="Foncer",
        condition="Quand tu fonces",
        outcome="Tu t'exposes",
    )
    action.traits.set([casse, sworn])


@pytest.mark.django_db
class TestSerialize:
    def test_emits_traitset_when_present(self) -> None:
        character = CharacterFactory()
        _seed_sheet(character)

        data = serialize_character(character)
        assert "traitSet" in data
        [block] = data["traitSet"]
        assert block["type"] == "suddenly:TraitSet"
        assert block["label"] == "Aspects"

        names = {t["name"]: t for t in block["traits"]}
        assert names["Casse-cou"]["value"] == 3
        assert "value" not in names["Sworn"]  # valueless tag omits the key
        assert names["Sworn"]["note"] == "au trône"

        [action] = block["actions"]
        assert action["name"] == "Foncer"
        assert set(action["traits"]) == {"Casse-cou", "Sworn"}
        assert action["condition"] == "Quand tu fonces"

    def test_omits_traitset_when_absent(self) -> None:
        character = CharacterFactory()
        data = serialize_character(character)
        assert "traitSet" not in data

    def test_context_declares_vocabulary(self) -> None:
        character = CharacterFactory()
        data = serialize_character(character)
        vocab = next(c for c in data["@context"] if isinstance(c, dict))
        for term in ("traitSet", "traits", "actions", "value", "condition", "outcome"):
            assert vocab[term].startswith("suddenly:")


@pytest.mark.django_db
class TestIngest:
    def _remote_character(self) -> Character:
        return CharacterFactory(remote=True, ap_id="https://peer.example/characters/aria")

    def test_round_trip(self) -> None:
        source = CharacterFactory()
        _seed_sheet(source)
        obj = serialize_character(source)

        remote = self._remote_character()
        _ingest_trait_sets(remote, obj)

        [ts] = remote.trait_sets.all()
        assert ts.label == "Aspects"
        casse = ts.traits.get(name="Casse-cou")
        assert casse.value == 3
        assert ts.traits.get(name="Sworn").value is None
        [action] = ts.actions.all()
        assert set(action.traits.values_list("name", flat=True)) == {"Casse-cou", "Sworn"}

    def test_absent_block_is_noop(self) -> None:
        remote = self._remote_character()
        _ingest_trait_sets(remote, {"type": "Person", "name": "Aria"})
        assert remote.trait_sets.count() == 0

    def test_ingest_is_idempotent_replace(self) -> None:
        remote = self._remote_character()
        _ingest_trait_sets(remote, {"traitSet": [{"label": "V1", "traits": [{"name": "a"}]}]})
        _ingest_trait_sets(remote, {"traitSet": [{"label": "V2", "traits": [{"name": "b"}]}]})
        labels = list(remote.trait_sets.values_list("label", flat=True))
        assert labels == ["V2"]
        assert Trait.objects.filter(trait_set__character=remote).count() == 1

    def test_malformed_entries_are_skipped(self) -> None:
        remote = self._remote_character()
        obj = {
            "traitSet": [
                "not-a-dict",
                {"label": "Ok", "traits": ["nope", {"name": ""}, {"name": "Good", "value": "x"}]},
            ]
        }
        _ingest_trait_sets(remote, obj)
        [ts] = remote.trait_sets.all()
        assert ts.label == "Ok"
        # "" skipped, "nope" skipped; "Good" kept with value coerced to None.
        good = ts.traits.get(name="Good")
        assert good.value is None

    def test_non_list_traitset_ignored(self) -> None:
        remote = self._remote_character()
        _ingest_trait_sets(remote, {"traitSet": {"label": "oops"}})
        assert remote.trait_sets.count() == 0

    def test_third_party_actor_without_vocab_not_broken(self) -> None:
        """A plain Mastodon-style actor has no traitSet: ingestion is a no-op."""
        remote = self._remote_character()
        mastodon_actor: dict[str, Any] = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Person",
            "name": "Someone",
            "summary": "hello",
        }
        _ingest_trait_sets(remote, mastodon_actor)
        assert remote.trait_sets.count() == 0
