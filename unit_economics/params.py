"""Illustrative parameters for a synthetic revolving credit line portfolio.

None of these numbers describe a real product or lender. They are chosen so the
mechanics are visible: segments with different risk, a loss curve that seasons
over the first year, and a price that covers loss in some segments and not in
others. Amounts are in generic currency units; rates are annual unless noted.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    name: str
    share: float              # share of originated lines
    annual_pd: float          # 12-month probability of default
    limit_mean: float
    utilisation_mean: float   # drawn balance / limit


@dataclass(frozen=True)
class Params:
    apr: float = 0.36                 # interest rate charged on drawn balance
    funding_rate: float = 0.12        # cost of funds on drawn balance
    lgd: float = 0.85                 # loss given default, share of balance
    acquisition_cost: float = 60.0    # per line, upfront
    servicing_cost: float = 2.0       # per active line, per month
    horizon_months: int = 24
    cohorts: int = 12                 # monthly origination vintages
    lines_per_cohort: int = 400
    segments: tuple[Segment, ...] = field(default_factory=lambda: (
        Segment("A", 0.35, 0.02, 4000.0, 0.45),
        Segment("B", 0.45, 0.06, 2500.0, 0.55),
        Segment("C", 0.20, 0.14, 1200.0, 0.70),
    ))


# Shape of default timing over months on book: little in the first months,
# a peak around months 4-9, a long tail. Normalised in `curves.hazard_shape`.
SEASONING_PEAK_MONTH = 6
SEASONING_SPREAD = 4.0
