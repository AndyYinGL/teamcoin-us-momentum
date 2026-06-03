"""Figure: the team-coin factor across three markets of increasing efficiency.
A-shares (inefficient) -> US small caps -> US large caps (efficient)."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

FIG = Path.home() / "teamcoin-us-momentum" / "notebooks" / "figures"
FIG.mkdir(exist_ok=True)

markets = ["A-shares", "US small cap\n(R2000)", "US large cap\n(S&P500)"]
trad_ic = [-6.53, -1.40, -0.20]      # traditional daily reversal Rank IC (%)
team_ic = [-9.67, -0.52, -1.61]      # final team-coin Rank IC (%)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))

# panel 1: traditional reversal IC
colors = ["#c0392b", "#e67e22", "#2980b9"]
ax1.bar(markets, trad_ic, color=colors, edgecolor="black", linewidth=0.5)
ax1.axhline(0, color="black", lw=1)
ax1.set_ylabel("Rank IC (%)")
ax1.set_title("Traditional reversal factor\n(the raw inefficiency)")
ax1.grid(alpha=0.3, axis="y")
for i, v in enumerate(trad_ic):
    ax1.text(i, v - 0.3, f"{v:.2f}%", ha="center", va="top", fontweight="bold")

# panel 2: team-coin IC
ax2.bar(markets, team_ic, color=colors, edgecolor="black", linewidth=0.5)
ax2.axhline(0, color="black", lw=1)
ax2.set_ylabel("Rank IC (%)")
ax2.set_title("Team-coin composite factor\n(A-share L/S +39.7%; US L/S ~0 or negative)")
ax2.grid(alpha=0.3, axis="y")
for i, v in enumerate(team_ic):
    ax2.text(i, v - 0.2, f"{v:.2f}%", ha="center", va="top", fontweight="bold")

fig.suptitle("Team-coin factor decays with market efficiency: strong in A-shares, "
             "gone in US equities", fontsize=13, fontweight="bold")
plt.tight_layout()
fig.savefig(FIG / "three_tier_comparison.png", dpi=150, bbox_inches="tight")
print(f"saved {FIG / 'three_tier_comparison.png'}")