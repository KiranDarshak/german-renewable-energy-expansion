"""
GOLD layer: build national year x technology cumulative capacity, state-level latest totals,
per-capita normalization, and the chart set.
Palette: house single-series blue #2B6CB0 / diverging green #2F855A & red #C53030 for ranked
bar & scatter charts (matches prior projects); a separate validated categorical 5-hue set
(dataviz skill, light-mode, all adjacent-pair CVD checks pass) for the multi-technology stack:
  Solar #eda100 | Wind onshore #2a78d6 | Wind offshore #4a3aa7 | Biomass #008300 | Hydropower #1baf7a
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap

additions = pd.read_csv("data/silver/silver_capacity_additions.csv")
removals = pd.read_csv("data/silver/silver_capacity_removals.csv")
state_pop = pd.read_csv("data/silver/silver_state_pop.csv")

TECHS = ["Solar", "Wind onshore", "Wind offshore", "Biomass", "Hydropower"]
TECH_COLORS = {
    "Solar": "#eda100", "Wind onshore": "#2a78d6", "Wind offshore": "#4a3aa7",
    "Biomass": "#008300", "Hydropower": "#1baf7a",
}
YEARS = list(range(2010, 2025))  # through 2024; 2025 snapshot (Feb) is partial, reported separately

# ---------------------------------------------------------------------------
# National: cumulative net capacity by year x technology
# ---------------------------------------------------------------------------
nat_adds = additions.groupby(["technology", "year"])["capacity_added_mw"].sum().unstack(fill_value=0)
nat_rems = removals.groupby(["technology", "year"])["capacity_removed_mw"].sum().unstack(fill_value=0)

all_years = sorted(set(nat_adds.columns) | set(nat_rems.columns))
nat_adds = nat_adds.reindex(columns=all_years, fill_value=0)
nat_rems = nat_rems.reindex(index=nat_adds.index, columns=all_years, fill_value=0)
net = (nat_adds - nat_rems).reindex(TECHS, fill_value=0)
cumulative = net.cumsum(axis=1)

gold_national = cumulative[[y for y in all_years if y <= 2025]].T
gold_national.index.name = "year"
gold_national.to_csv("data/gold/gold_national_capacity_by_year.csv")
print("National cumulative capacity by technology (GW), selected years:")
print((gold_national.loc[[y for y in [2010, 2015, 2020, 2024] if y in gold_national.index]] / 1000).round(1))

snapshot_2025 = gold_national.loc[2025] if 2025 in gold_national.index else None
cum_2024 = gold_national.loc[2024]
print(f"\nTotal installed renewable capacity end of 2024: {cum_2024.sum()/1000:.1f} GW")
if snapshot_2025 is not None:
    print(f"Snapshot as of 2025-02-09 (partial year): {snapshot_2025.sum()/1000:.1f} GW")

# ---------------------------------------------------------------------------
# State level: latest cumulative totals (as of snapshot, early 2025) per technology
# ---------------------------------------------------------------------------
adds_st = additions.groupby(["Bundesland", "technology"])["capacity_added_mw"].sum()
rems_st = removals.groupby(["Bundesland", "technology"])["capacity_removed_mw"].sum()
combined_st = pd.DataFrame({"added": adds_st, "removed": rems_st}).fillna(0)
state_net = combined_st["added"] - combined_st["removed"]
state_wide = state_net.unstack(fill_value=0).reindex(columns=TECHS, fill_value=0)
# Offshore wind sited in federal waters (beyond the 12nm territorial limit) is registered
# against the EEZ, not a Bundesland - keep it in national totals but drop it from state views.
offshore_eez_mw = state_wide.loc["Ausschließliche Wirtschaftszone"].sum() if "Ausschließliche Wirtschaftszone" in state_wide.index else 0
state_wide = state_wide.drop(index="Ausschließliche Wirtschaftszone", errors="ignore")
print(f"Offshore wind capacity sited in federal waters (excluded from state views): {offshore_eez_mw/1000:.1f} GW")
state_wide["total_mw"] = state_wide.sum(axis=1)
state_wide = state_wide.reset_index().merge(state_pop, on="Bundesland", how="left")
state_wide["capacity_per_100k_mw"] = (state_wide["total_mw"] / state_wide["population_est"] * 100_000).round(2)
state_wide["solar_share_pct"] = (state_wide["Solar"] / state_wide["total_mw"] * 100).round(1)
state_wide["wind_share_pct"] = ((state_wide["Wind onshore"] + state_wide["Wind offshore"]) / state_wide["total_mw"] * 100).round(1)
state_wide = state_wide.sort_values("capacity_per_100k_mw", ascending=False)
state_wide.to_csv("data/gold/gold_state_summary.csv", index=False)
print("\nState summary (top 5 by capacity per 100k residents):")
print(state_wide[["Bundesland", "total_mw", "capacity_per_100k_mw", "solar_share_pct", "wind_share_pct"]].head(5).to_string(index=False))

# ---------------------------------------------------------------------------
# Gross annual additions (new capacity brought online each year, by technology)
# ---------------------------------------------------------------------------
annual_gross = nat_adds.reindex(TECHS, fill_value=0)[[y for y in all_years if 2010 <= y <= 2024]].T
annual_gross.index.name = "year"
annual_gross.to_csv("data/gold/gold_annual_additions_by_year.csv")

print("\nGold tables written to data/gold/")

# ===========================================================================
# CHARTS
# ===========================================================================

# --- CHART 1: Stacked area - cumulative installed capacity by technology, 2010-2024 ---
fig, ax = plt.subplots(figsize=(11, 7))
years_plot = gold_national.index[(gold_national.index >= 2010) & (gold_national.index <= 2024)]
stack_data = [gold_national.loc[years_plot, t] / 1000 for t in TECHS]  # GW
ax.stackplot(years_plot, stack_data, labels=TECHS, colors=[TECH_COLORS[t] for t in TECHS],
             edgecolor="white", linewidth=0.6)
ax.set_ylabel("Cumulative installed capacity (GW)")
ax.set_xlabel("Year")
ax.set_title("Germany's Renewable Generation Fleet, 2010-2024", fontsize=13, fontweight="bold")
ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
ax.set_xlim(2010, 2024)
ax.grid(alpha=0.25, axis="y")
plt.tight_layout()
plt.savefig("charts/chart_capacity_growth_stacked.png", dpi=150)
plt.close()

# --- CHART 2: Gross annual additions by technology (grouped/stacked bars - boom/bust cycles) ---
fig, ax = plt.subplots(figsize=(11, 6.5))
bottom = np.zeros(len(annual_gross))
for t in TECHS:
    vals = (annual_gross[t] / 1000).values
    ax.bar(annual_gross.index, vals, bottom=bottom, label=t, color=TECH_COLORS[t])
    bottom += vals
ax.set_ylabel("New capacity commissioned that year (GW)")
ax.set_xlabel("Year")
ax.set_title("Annual New-Build Renewable Capacity by Technology", fontsize=13, fontweight="bold")
ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
ax.grid(alpha=0.25, axis="y")
plt.tight_layout()
plt.savefig("charts/chart_annual_additions.png", dpi=150)
plt.close()

# --- CHART 3: Renewable capacity per 100k residents by state (house blue gradient) ---
blue_cmap = LinearSegmentedColormap.from_list("house_blue", ["#BBD3EA", "#2B6CB0", "#123A5E"])
def gradient_colors(values, cmap):
    v = np.asarray(values, dtype=float)
    norm = (v - v.min()) / (v.max() - v.min() + 1e-9)
    return [cmap(0.25 + 0.65 * n) for n in norm]

fig, ax = plt.subplots(figsize=(10, 7))
plot_df = state_wide.sort_values("capacity_per_100k_mw")
colors = gradient_colors(plot_df["capacity_per_100k_mw"], blue_cmap)
ax.barh(plot_df["Bundesland"], plot_df["capacity_per_100k_mw"], color=colors)
ax.set_xlabel("Installed renewable capacity (MW) per 100,000 residents")
ax.set_title("Renewable Capacity Density by State (as of early 2025)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("charts/chart_capacity_per_capita_by_state.png", dpi=150)
plt.close()

# --- CHART 4: Technology mix by state - solar share vs wind share (diverging-style scatter) ---
fig, ax = plt.subplots(figsize=(9.5, 7))
sc = ax.scatter(state_wide["wind_share_pct"], state_wide["solar_share_pct"], s=110,
                 c=state_wide["total_mw"] / 1000, cmap=blue_cmap, zorder=3,
                 edgecolors="white", linewidths=0.6)
for _, row in state_wide.iterrows():
    ax.annotate(row["Bundesland"], (row["wind_share_pct"], row["solar_share_pct"]),
                fontsize=8, xytext=(5, 5), textcoords="offset points")
cbar = plt.colorbar(sc, ax=ax)
cbar.set_label("Total installed renewable capacity (GW)", fontsize=9)
ax.set_xlabel("Wind share of state's renewable capacity (%)")
ax.set_ylabel("Solar share of state's renewable capacity (%)")
ax.set_title("Technology Mix: Wind-Heavy North vs. Solar-Heavy South", fontsize=13, fontweight="bold")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("charts/chart_tech_mix_by_state.png", dpi=150)
plt.close()

print("\nCharts written to charts/")
