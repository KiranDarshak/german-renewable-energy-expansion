import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

gold_national = pd.read_csv("data/gold/gold_national_capacity_by_year.csv", index_col="year")
gold_state = pd.read_csv("data/gold/gold_state_summary.csv")
annual = pd.read_csv("data/gold/gold_annual_additions_by_year.csv", index_col="year")

TECHS = ["Solar", "Wind onshore", "Wind offshore", "Biomass", "Hydropower"]
TECH_COLORS = {
    "Solar": "#eda100", "Wind onshore": "#2a78d6", "Wind offshore": "#4a3aa7",
    "Biomass": "#008300", "Hydropower": "#1baf7a",
}
blue_cmap = LinearSegmentedColormap.from_list("house_blue", ["#BBD3EA", "#2B6CB0", "#123A5E"])

def gradient_colors(values, cmap):
    v = np.asarray(values, dtype=float)
    norm = (v - v.min()) / (v.max() - v.min() + 1e-9)
    return [cmap(0.25 + 0.65 * n) for n in norm]

cap_2010 = gold_national.loc[2010].sum() / 1000
cap_2024 = gold_national.loc[2024].sum() / 1000
multiple = cap_2024 / cap_2010
top_state = gold_state.sort_values("capacity_per_100k_mw", ascending=False).iloc[0]
new_build_2024 = annual.loc[2024].sum() / 1000

fig = plt.figure(figsize=(13, 8.2))
fig.patch.set_facecolor("white")

fig.text(0.045, 0.955, "German Renewable Energy Grid Expansion, 2010-2024", fontsize=17, fontweight="bold", color="#1a1a1a")
fig.text(0.045, 0.925, "Capacity Buildout Dashboard  •  Marktstammdatenregister (Bundesnetzagentur), snapshot 2025-02-09", fontsize=10, color="#666666")

kpi_ax = fig.add_axes([0.045, 0.76, 0.91, 0.13])
kpi_ax.axis("off")
kpis = [
    (f"{cap_2024:.0f} GW", "INSTALLED RENEWABLE CAPACITY, END OF 2024", f"up from {cap_2010:.0f} GW in 2010", "#2F855A"),
    (f"{multiple:.1f}×", "GROWTH SINCE 2010", "national cumulative capacity", "#2B6CB0"),
    (f"{new_build_2024:.1f} GW", "NEW CAPACITY BUILT IN 2024", "highest single year on record", "#eda100"),
    (top_state["Bundesland"], "LEADING STATE PER CAPITA", f"{top_state['capacity_per_100k_mw']:.0f} MW / 100k residents", "#4a3aa7"),
]
n = len(kpis)
w = 1.0 / n
for i, (value, label, sub, color) in enumerate(kpis):
    x0 = i * w
    kpi_ax.add_patch(plt.Rectangle((x0 + 0.01, 0), w - 0.02, 1, transform=kpi_ax.transAxes,
                                    facecolor="#FAFAFA", edgecolor="#E5E5E5", linewidth=1))
    kpi_ax.add_patch(plt.Rectangle((x0 + 0.01, 0), 0.012, 1, transform=kpi_ax.transAxes, facecolor=color))
    kpi_ax.text(x0 + 0.05, 0.62, value, transform=kpi_ax.transAxes, fontsize=18, fontweight="bold", color="#1a1a1a", va="center")
    kpi_ax.text(x0 + 0.05, 0.32, label, transform=kpi_ax.transAxes, fontsize=7, color="#555555", va="center", fontweight="bold")
    kpi_ax.text(x0 + 0.05, 0.14, sub, transform=kpi_ax.transAxes, fontsize=7, color="#888888", va="center")
kpi_ax.set_xlim(0, 1)
kpi_ax.set_ylim(0, 1)

# Chart 1: stacked area, compact
ax1 = fig.add_axes([0.055, 0.06, 0.32, 0.62])
years_plot = [y for y in gold_national.index if 2010 <= y <= 2024]
stack_data = [gold_national.loc[years_plot, t] / 1000 for t in TECHS]
ax1.stackplot(years_plot, stack_data, colors=[TECH_COLORS[t] for t in TECHS], edgecolor="white", linewidth=0.4)
ax1.set_title("Cumulative Capacity by Technology (GW)", fontsize=9.5, fontweight="bold", loc="left")
ax1.tick_params(labelsize=7)
ax1.set_xlim(2010, 2024)

# Chart 2: annual additions, compact
ax2 = fig.add_axes([0.405, 0.06, 0.29, 0.62])
bottom = np.zeros(len(annual))
for t in TECHS:
    vals = (annual[t] / 1000).values
    ax2.bar(annual.index, vals, bottom=bottom, color=TECH_COLORS[t])
    bottom += vals
ax2.set_title("Annual New-Build Capacity (GW)", fontsize=9.5, fontweight="bold", loc="left")
ax2.tick_params(labelsize=7)

# Chart 3: per-capita state bar, compact (top 8)
ax3 = fig.add_axes([0.735, 0.06, 0.23, 0.62])
plot_df = gold_state.sort_values("capacity_per_100k_mw").tail(8)
colors = gradient_colors(plot_df["capacity_per_100k_mw"], blue_cmap)
ax3.barh(plot_df["Bundesland"], plot_df["capacity_per_100k_mw"], color=colors)
ax3.set_title("Top States: MW per 100k Residents", fontsize=9.5, fontweight="bold", loc="left")
ax3.tick_params(axis="y", labelsize=6.5)
ax3.tick_params(axis="x", labelsize=7)

# Shared legend for technology colors
handles = [plt.Rectangle((0, 0), 1, 1, color=TECH_COLORS[t]) for t in TECHS]
fig.legend(handles, TECHS, loc="lower center", ncol=5, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 0.0))

plt.savefig("charts/dashboard_preview.png", dpi=160, facecolor="white")
print("done")
