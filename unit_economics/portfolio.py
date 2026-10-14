"""Synthetic portfolio and simulated defaults, cohort by cohort."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .params import SEASONING_PEAK_MONTH, SEASONING_SPREAD, Params


def hazard_shape(months: int) -> np.ndarray:
    """Share of 12-month defaults falling in each month on book (sums to 1 over 12)."""
    m = np.arange(1, months + 1)
    shape = np.exp(-0.5 * ((m - SEASONING_PEAK_MONTH) / SEASONING_SPREAD) ** 2)
    return shape / shape[:12].sum()


def monthly_default_rates(annual_pd: float, months: int) -> np.ndarray:
    """Unconditional default probability per month on book, seasoned."""
    return annual_pd * hazard_shape(months)


def originate(p: Params, seed: int = 3) -> pd.DataFrame:
    """One row per line: cohort, segment, limit, drawn balance, default month (0 = none)."""
    rng = np.random.default_rng(seed)
    rows = []
    names = [s.name for s in p.segments]
    shares = [s.share for s in p.segments]
    by_name = {s.name: s for s in p.segments}
    for cohort in range(p.cohorts):
        segs = rng.choice(names, size=p.lines_per_cohort, p=shares)
        observable = p.horizon_months - cohort      # younger cohorts have less history
        for seg in segs:
            s = by_name[seg]
            limit = float(np.clip(rng.normal(s.limit_mean, 0.25 * s.limit_mean), 500, 8000) // 100 * 100)
            util = float(np.clip(rng.normal(s.utilisation_mean, 0.15), 0.05, 1.0))
            rates = monthly_default_rates(s.annual_pd, p.horizon_months)
            draws = rng.random(p.horizon_months) < rates
            first = int(np.argmax(draws)) + 1 if draws.any() else 0
            rows.append(dict(cohort=cohort, segment=seg, limit=limit, balance=round(limit * util, 2),
                             default_month=first if 0 < first <= observable else 0,
                             months_observed=observable))
    return pd.DataFrame(rows)


def cohort_loss_curves(df: pd.DataFrame, lgd: float) -> pd.DataFrame:
    """Cumulative loss as a share of originated balance, by cohort and month on book."""
    out = {}
    for cohort, g in df.groupby("cohort"):
        orig = g["balance"].sum()
        horizon = int(g["months_observed"].max())
        lost = [(g.loc[(g.default_month > 0) & (g.default_month <= m), "balance"].sum() * lgd) / orig
                for m in range(1, horizon + 1)]
        out[cohort] = pd.Series(lost, index=range(1, horizon + 1))
    return pd.DataFrame(out)
