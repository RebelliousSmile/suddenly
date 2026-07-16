"""Fiction order — reading chain, chronology labels, invariants, reading, UI.

The fiction order is an explicit forest built on the self-FK ``previous_report``,
distinct from ``Meta.ordering``. These tests cover the model + XOR constraint,
the service invariants, ``fiction_thread`` (mainline-first DFS) and ``set_previous``,
and the opening/closing UI partials.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string

from suddenly.games.models import ReportTemporalKind
from suddenly.games.services import (
    fiction_continuations,
    fiction_thread,
    set_previous,
    validate_fiction_links,
)
from tests.factories import GameFactory, ReportFactory


# ---------------------------------------------------------------------------
# Model + constraint
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestModel:
    def test_model_previous_report_chains_two_scenes(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game, previous_report=a)
        b.refresh_from_db()
        assert b.previous_report_id == a.pk
        assert list(a.next_reports.all()) == [b]

    def test_model_defaults_are_unchained_and_normal(self) -> None:
        report = ReportFactory()
        assert report.previous_report_id is None
        assert not report.previous_report_iri
        assert report.branch_order == 0
        assert report.temporal_kind == ReportTemporalKind.NORMAL
        assert report.temporal_label == ""

    def test_constraint_rejects_previous_fk_and_iri_together(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ReportFactory(
                    game=game,
                    previous_report=a,
                    previous_report_iri="https://peer.example/reports/x",
                )

    def test_constraint_rejects_anchor_fk_and_iri_together(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ReportFactory(
                    game=game,
                    temporal_anchor=a,
                    temporal_anchor_iri="https://peer.example/reports/x",
                )


# ---------------------------------------------------------------------------
# Invariants (validate_fiction_links)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestInvariants:
    def test_invariant_self_previous_reference_rejected(self) -> None:
        report = ReportFactory()
        report.previous_report = report
        with pytest.raises(ValidationError):
            validate_fiction_links(report)

    def test_invariant_self_anchor_reference_rejected(self) -> None:
        report = ReportFactory(temporal_kind=ReportTemporalKind.FLASHBACK)
        report.temporal_anchor = report
        with pytest.raises(ValidationError):
            validate_fiction_links(report)

    def test_invariant_cycle_in_previous_chain_rejected(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game, previous_report=a)
        c = ReportFactory(game=game, previous_report=b)
        a.previous_report = c  # a -> c -> b -> a would cycle
        with pytest.raises(ValidationError):
            validate_fiction_links(a)

    def test_invariant_previous_different_game_rejected(self) -> None:
        a = ReportFactory(game=GameFactory())
        b = ReportFactory(game=GameFactory())
        b.previous_report = a
        with pytest.raises(ValidationError):
            validate_fiction_links(b)

    def test_invariant_anchor_different_game_rejected(self) -> None:
        a = ReportFactory(game=GameFactory())
        b = ReportFactory(game=GameFactory(), temporal_kind=ReportTemporalKind.FLASHBACK)
        b.temporal_anchor = a
        with pytest.raises(ValidationError):
            validate_fiction_links(b)

    def test_invariant_normal_kind_with_anchor_rejected(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game)  # temporal_kind NORMAL by default
        b.temporal_anchor = a
        with pytest.raises(ValidationError):
            validate_fiction_links(b)

    def test_invariant_normal_kind_with_label_rejected(self) -> None:
        report = ReportFactory(temporal_label="Ten years earlier")
        with pytest.raises(ValidationError):
            validate_fiction_links(report)

    def test_invariant_xor_previous_fk_and_iri_rejected(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game)
        b.previous_report = a
        b.previous_report_iri = "https://peer.example/reports/x"
        with pytest.raises(ValidationError):
            validate_fiction_links(b)

    def test_invariant_nominal_chain_passes(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game, previous_report=a)
        validate_fiction_links(b)  # must not raise

    def test_invariant_flashback_nominal_passes(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(
            game=game,
            previous_report=a,
            temporal_kind=ReportTemporalKind.FLASHBACK,
            temporal_anchor=a,
            temporal_label="Ten years earlier",
        )
        validate_fiction_links(b)  # must not raise


# ---------------------------------------------------------------------------
# Reading (fiction_thread) + mutation (set_previous)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestThread:
    def test_thread_mainline_first_on_branch(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game, previous_report=a, branch_order=0)
        c = ReportFactory(game=game, previous_report=a, branch_order=1)
        d = ReportFactory(game=game, previous_report=b)
        assert fiction_thread(game) == [a, b, d, c]

    def test_thread_flashback_appears_in_place(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(
            game=game,
            previous_report=a,
            temporal_kind=ReportTemporalKind.FLASHBACK,
            temporal_anchor=a,
            temporal_label="Before",
        )
        c = ReportFactory(game=game, previous_report=b)
        ordered = fiction_thread(game)
        assert ordered == [a, b, c]  # flashback at its chain position, not last
        assert ordered[1].temporal_kind == ReportTemporalKind.FLASHBACK

    def test_numqueries_thread_is_bounded(self, django_assert_max_num_queries: Any) -> None:
        game = GameFactory()
        prev = None
        for _ in range(6):
            prev = ReportFactory(game=game, previous_report=prev)
        with django_assert_max_num_queries(3):
            fiction_thread(game)

    def test_set_previous_rewrites_single_edge(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game)
        set_previous(b, a)
        b.refresh_from_db()
        assert b.previous_report_id == a.pk

    def test_set_previous_refuses_cycle_and_leaves_db_untouched(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game, previous_report=a)
        c = ReportFactory(game=game, previous_report=b)
        with pytest.raises(ValidationError):
            set_previous(a, c)
        a.refresh_from_db()
        assert a.previous_report_id is None

    def test_orphan_becomes_root_after_predecessor_deleted(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game, previous_report=a)
        a.delete()
        b.refresh_from_db()
        assert b.previous_report_id is None  # SET_NULL
        assert b in fiction_thread(game)  # reappears as a root


# ---------------------------------------------------------------------------
# UI partials — opening « Previously » / closing « Next → »
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestTemplateRender:
    def test_render_previously_present_with_predecessor(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game, title="Scene Alpha")
        b = ReportFactory(game=game, previous_report=a)
        html = render_to_string("games/_fiction_previously.html", {"report": b})
        assert 'data-fiction="previously"' in html
        assert "Scene Alpha" in html

    def test_render_previously_absent_without_predecessor(self) -> None:
        report = ReportFactory()
        html = render_to_string("games/_fiction_previously.html", {"report": report})
        assert 'data-fiction="previously"' not in html

    def test_render_previously_flashback_badge(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game, title="Anchor")
        b = ReportFactory(
            game=game,
            previous_report=a,
            temporal_kind=ReportTemporalKind.FLASHBACK,
            temporal_anchor=a,
            temporal_label="Ten years earlier",
        )
        html = render_to_string("games/_fiction_previously.html", {"report": b})
        assert 'data-fiction-temporal="flashback"' in html
        assert "Ten years earlier" in html

    def test_render_next_lists_mainline_before_branches(self) -> None:
        game = GameFactory()
        mainline = ReportFactory(game=game, title="Mainline scene", branch_order=0)
        branch = ReportFactory(game=game, title="Branch scene", branch_order=1)
        html = render_to_string("games/_fiction_next.html", {"fiction_next": [mainline, branch]})
        assert 'data-fiction="next"' in html
        assert "Mainline scene" in html and "Branch scene" in html
        assert html.index("mainline") < html.index("branch")

    def test_render_next_absent_without_continuations(self) -> None:
        html = render_to_string("games/_fiction_next.html", {"fiction_next": []})
        assert 'data-fiction="next"' not in html

    def test_render_continuations_service_orders_mainline_first(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        branch = ReportFactory(game=game, previous_report=a, branch_order=1)
        mainline = ReportFactory(game=game, previous_report=a, branch_order=0)
        assert fiction_continuations(a) == [mainline, branch]


def test_local_report_url_prefix_is_stable() -> None:
    """The local report IRI prefix used by the fiction partials is a settings.DOMAIN URL."""
    assert isinstance(settings.DOMAIN, str) and settings.DOMAIN
