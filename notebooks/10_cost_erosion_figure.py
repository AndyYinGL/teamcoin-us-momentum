"""Figure: the 'strongest' OOS factor (R2000 overnight reversal) is not
tradeable. Long-short annualized return collapses as realistic small-cap
transaction costs are applied -- and it's already negative gross."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

FIG = Path.home() / "teamcoin-us-momentum" / "notebooks" / "figures"

# from 08_cost_robustness.py output (R2000 overnight reversal long-short)
costs = [0.0, 0.1, 0.2, 0.3, 0.5]          # round-trip cost per side (%)
ann_ret = [-13.46, -17.21, -20.97, -24.73, -32.24]  # annualized return (%)

fig, ax = plt.subplots(figsize=(9, 5.2))
colors = ["#e67e22" if c < 0.2 else "#c0392b" for c in costs]
bars = ax.bar([f"{c:.1f}%" for c in costs], ann_ret, color=colors,
              edgecolor="black", linewidth=0.5, width=0.6)
ax.axhline(0, color="black", lw=1)
for b, v in zip(bars, ann_ret):
    ax.text(b.get_x() + b.get_width() / 2, v - 0.8, f"{v:.1f}%",
            ha="center", va="top", fontsize=10, fontweight="bold")

ax.set_xlabel("round-trip transaction cost per side")
ax.set_ylabel("long-short annualized return (%)")
ax.set_title("The 'strongest' OOS factor is not tradeable\n"
             "R2000 overnight reversal: negative gross, 157% monthly turnover, "
             "buried by small-cap spreads")
ax.grid(alpha=0.3, axis="y")
# shade the realistic small-cap cost zone
ax.axvspan(1.5, 4.5, color="red", alpha=0.06)
ax.text(3.0, -5, "realistic small-cap\ncost range", ha="center",
        fontsize=9, color="#c0392b", style="italic")
plt.tight_layout()
fig.savefig(FIG / "cost_erosion.png", dpi=150, bbox_inches="tight")
print(f"saved {FIG / 'cost_erosion.png'}")