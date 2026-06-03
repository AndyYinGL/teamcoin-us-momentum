"""Figure: long-short cumulative NAV. US team-coin is flat/declining;
the A-share factor compounded dramatically (we annotate, not reconstruct, since
we don't have the A-share monthly series)."""
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.factors import build_panels, make_factor_funcs
from teamcoin.backtest import backtest_factor

FIG = Path.home() / "teamcoin-us-momentum" / "notebooks" / "figures"

adj, rd, ri, ro, turnover, fund = build_panels()
f = make_factor_funcs(rd, ri, ro, turnover)
_, ls, nav = backtest_factor(f["team_coin"], adj, fund)

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(nav.index, nav.values, color="#2980b9", lw=1.8,
        label="US S&P 500 team-coin long-short")
ax.axhline(1.0, color="black", lw=0.8, ls="--")
ax.set_ylabel("cumulative NAV (start = 1.0)")
ax.set_xlabel("date")
ax.set_title("US team-coin long-short NAV: no compounding\n"
             f"final NAV {nav.iloc[-1]:.3f} (annualized {ls.mean()*12:+.1%}, "
             f"IR {ls.mean()/ls.std():+.2f}) — vs A-share IR 3.95")
ax.grid(alpha=0.3)
ax.legend(loc="upper left")
# annotate the contrast
ax.text(0.98, 0.05,
        "A-share factor compounded to many multiples over 2010-2022;\n"
        "the same factor is flat-to-negative in US large caps.",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=9,
        style="italic", color="#555")
plt.tight_layout()
fig.savefig(FIG / "nav_comparison.png", dpi=150, bbox_inches="tight")
print(f"saved {FIG / 'nav_comparison.png'}")
print(f"final NAV: {nav.iloc[-1]:.3f}, months: {len(ls)}")