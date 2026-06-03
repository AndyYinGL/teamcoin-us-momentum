"""Figure: decile annualized returns, US S&P500 vs A-share report.
Shows the A-share monotone staircase vs the US noise."""
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.factors import build_panels, make_factor_funcs
from teamcoin.backtest import backtest_factor

FIG = Path.home() / "teamcoin-us-momentum" / "notebooks" / "figures"
FIG.mkdir(exist_ok=True)

# A-share decile annualized returns from the report (figure 32), decile 1..10
ashare = [22.71, 18.29, 15.35, 12.25, 9.75, 8.27, 5.87, 4.83, 0.70, -13.79]

# US: recompute team-coin deciles
adj, rd, ri, ro, turnover, fund = build_panels()
f = make_factor_funcs(rd, ri, ro, turnover)
decile_ann, ls, nav = backtest_factor(f["team_coin"], adj, fund)
us = [decile_ann[d] * 100 for d in range(10)]

x = np.arange(10)
w = 0.38
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.bar(x - w / 2, ashare, w, label="A-shares (Founder report)",
       color="#c0392b", edgecolor="black", linewidth=0.4)
ax.bar(x + w / 2, us, w, label="US S&P 500 (this study)",
       color="#2980b9", edgecolor="black", linewidth=0.4)
ax.axhline(0, color="black", lw=1)
ax.set_xticks(x)
ax.set_xticklabels([f"D{d+1}" for d in range(10)])
ax.set_xlabel("factor decile (D1 = lowest factor value = predicted highest return)")
ax.set_ylabel("annualized return (%)")
ax.set_title("Team-coin factor: monotone in A-shares, noise in US large caps\n"
             "A-share long-short IR 3.95 vs US IR -0.21")
ax.legend()
ax.grid(alpha=0.3, axis="y")
plt.tight_layout()
fig.savefig(FIG / "decile_comparison.png", dpi=150, bbox_inches="tight")
print(f"saved {FIG / 'decile_comparison.png'}")
print("US deciles:", [round(v, 1) for v in us])