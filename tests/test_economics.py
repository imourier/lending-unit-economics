"""Checks on the arithmetic the notebook relies on."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from unit_economics import Params, Segment
from unit_economics import economics as E
from unit_economics import portfolio as P

p = Params()


def test_hazard_shape_spreads_one_year_of_defaults_over_the_first_twelve_months():
    assert P.hazard_shape(24)[:12].sum() == pytest.approx(1.0)


def test_expected_loss_is_pd_times_lgd_times_ead():
    el = E.expected_loss_by_segment(p)
    s = p.segments[0]
    assert el.loc[s.name, "el_per_line"] == pytest.approx(s.annual_pd * p.lgd * s.limit_mean * s.utilisation_mean)


def test_cost_stack_plus_margin_equals_price():
    stack = E.pricing_vs_loss(p)
    total = stack[["funding", "expected_loss", "opex", "margin"]].sum(axis=1)
    assert np.allclose(total, p.apr)


def test_contribution_is_the_sum_of_its_parts():
    cf = E.line_cashflows(p, p.segments[1])
    parts = cf[["revenue", "funding", "losses", "opex"]].sum(axis=1)
    assert np.allclose(parts, cf["contribution"])
    assert cf.loc[1, "opex"] < -p.acquisition_cost, "acquisition is paid in month 1"


def test_riskier_segment_pays_back_later():
    months = E.line_summary(p)["payback_month"]
    assert months["A"] <= months["B"] <= months["C"]


def test_no_payback_when_price_is_below_funding():
    cf = E.line_cashflows(replace(p, apr=0.05), Segment("x", 1.0, 0.05, 2500, 0.5))
    assert E.payback_month(cf) is None


def test_sensitivity_moves_the_right_way():
    s = E.sensitivity(p)
    assert s.loc[(0.02, 0.36), 2500.0] > s.loc[(0.12, 0.36), 2500.0], "more loss, less contribution"
    assert s.loc[(0.05, 0.48), 2500.0] > s.loc[(0.05, 0.24), 2500.0], "higher rate, more contribution"


def test_portfolio_is_reproducible_with_a_seed():
    assert P.originate(p, seed=5).equals(P.originate(p, seed=5))
