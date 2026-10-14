"""Expected loss, pricing against loss, per-line P&L, payback and sensitivity.

All figures are expected values on one line held for the horizon; no
prepayment, no limit changes, balance constant until default.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .params import Params, Segment
from .portfolio import monthly_default_rates


def expected_loss_by_segment(p: Params) -> pd.DataFrame:
    """EL = PD x LGD x EAD, annual, per line and as a rate on balance."""
    rows = []
    for s in p.segments:
        ead = s.limit_mean * s.utilisation_mean
        rows.append(dict(segment=s.name, pd_12m=s.annual_pd, lgd=p.lgd, ead=ead,
                         el_per_line=s.annual_pd * p.lgd * ead, el_rate=s.annual_pd * p.lgd))
    return pd.DataFrame(rows).set_index("segment")


def pricing_vs_loss(p: Params) -> pd.DataFrame:
    """Annual yield against the cost stack, as rates on drawn balance."""
    rows = []
    for s in p.segments:
        balance = s.limit_mean * s.utilisation_mean
        opex_rate = (p.servicing_cost * 12 + p.acquisition_cost * 12 / p.horizon_months) / balance
        el = s.annual_pd * p.lgd
        rows.append(dict(segment=s.name, apr=p.apr, funding=p.funding_rate, expected_loss=el,
                         opex=opex_rate, margin=p.apr - p.funding_rate - el - opex_rate))
    return pd.DataFrame(rows).set_index("segment")


def line_cashflows(p: Params, s: Segment, limit: float | None = None) -> pd.DataFrame:
    """Monthly expected cash flows for one line of segment `s`."""
    balance = (limit or s.limit_mean) * s.utilisation_mean
    pd_m = monthly_default_rates(s.annual_pd, p.horizon_months)
    alive = np.concatenate([[1.0], np.cumprod(1 - pd_m)[:-1]])   # survival at start of month
    months = np.arange(1, p.horizon_months + 1)
    df = pd.DataFrame(index=pd.Index(months, name="month"))
    df["revenue"] = alive * balance * p.apr / 12
    df["funding"] = -alive * balance * p.funding_rate / 12
    df["losses"] = -alive * pd_m * balance * p.lgd
    df["opex"] = -alive * p.servicing_cost
    df.loc[1, "opex"] -= p.acquisition_cost
    df["contribution"] = df[["revenue", "funding", "losses", "opex"]].sum(axis=1)
    df["cumulative"] = df["contribution"].cumsum()
    return df


def payback_month(cf: pd.DataFrame) -> int | None:
    """First month in which cumulative contribution turns non-negative."""
    hit = cf.index[cf["cumulative"] >= 0]
    return int(hit[0]) if len(hit) else None


def line_summary(p: Params) -> pd.DataFrame:
    rows = []
    for s in p.segments:
        cf = line_cashflows(p, s)
        totals = cf[["revenue", "funding", "losses", "opex", "contribution"]].sum()
        rows.append(dict(segment=s.name, **totals.round(2).to_dict(), payback_month=payback_month(cf)))
    return pd.DataFrame(rows).set_index("segment")


def sensitivity(p: Params, loss_rates=(0.02, 0.05, 0.08, 0.12), aprs=(0.24, 0.36, 0.48),
                limits=(1000.0, 2500.0, 5000.0), utilisation: float = 0.55) -> pd.DataFrame:
    """Horizon contribution per line over annual loss rate x APR x limit.

    The loss rate is net of recoveries (PD x LGD); the PD used is loss / LGD.
    """
    rows = []
    for loss in loss_rates:
        for apr in aprs:
            for lim in limits:
                s = Segment("x", 1.0, loss / p.lgd, lim, utilisation)
                cf = line_cashflows(replace(p, apr=apr), s, lim)
                rows.append(dict(annual_loss_rate=loss, apr=apr, limit=lim,
                                 contribution=round(cf["contribution"].sum(), 0)))
    return pd.DataFrame(rows).pivot_table(index=["annual_loss_rate", "apr"], columns="limit",
                                          values="contribution")
