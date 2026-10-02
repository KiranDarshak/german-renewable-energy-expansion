# German Renewable Energy Grid Expansion, 2010-2024

How did Germany actually build out 186 GW of wind, solar, biomass and hydropower capacity, and where did it go? This project reconstructs the full installation and decommissioning history of every registered renewable generation unit in Germany from the Marktstammdatenregister (MaStR) - Bundesnetzagentur's official energy market registry - to track cumulative capacity by technology and by state, year by year.

## Data Source

- **Marktstammdatenregister (MaStR)**, the Bundesnetzagentur's unit-level registry of every power-generating installation in Germany. Snapshot dated **2025-02-09**, distributed as structured CSVs by the Open Energy Family's [open-MaStR](https://github.com/OpenEnergyPlatform/open-MaStR) project via Zenodo ([doi.org/10.5281/zenodo.14843222](https://doi.org/10.5281/zenodo.14843222)), itself built from Bundesnetzagentur's public bulk export under the Data Licence Germany (DL-DE-BY-2.0).
- **~5.02 million unit records** across four technologies: solar (4.95M units, almost all small rooftop systems), wind (38K units, onshore + offshore), biomass (23K units), and hydropower (8.7K units).
- Each unit carries a commissioning date (`Inbetriebnahmedatum`), and where applicable a decommissioning date, nominal capacity, and state (`Bundesland`).

This is official German government open data - no figures in this project are estimated, modeled, or simulated.

## Pipeline

Bronze -> Silver -> Gold, in Python/pandas (DuckDB/BigQuery-equivalent logic, run locally for cost reasons - the groupby/aggregation steps below map directly to dbt models over a BigQuery warehouse):

- **Bronze:** raw ingestion of all four technology tables. The solar file decompresses to ~3.9 GB - too large to extract and keep on disk for a reproducible pipeline - so it's streamed directly out of its zip archive in 300K-row chunks and reduced immediately rather than materialized whole.
- **Silver:** type-cleaning (dates, capacity units kW->MW), technology labeling (wind is split into onshore/offshore using the unit's `Lage` field), then each technology is reduced to two small tables: capacity **added** by (state, commissioning year) and capacity **removed** by (state, decommissioning year). Keeping both means capacity is tracked net of repowering and retirements, not just assumed permanent once built.
- **Gold:** cumulative net capacity by year and technology (additions minus removals, running total), state-level latest totals joined against population estimates for per-capita normalization, and annual gross new-build capacity by technology.

Offshore wind sited in federal waters beyond the 12-nautical-mile limit is registered against Germany's Exclusive Economic Zone rather than any Bundesland - it's included in all national totals but excluded from the state-level charts, where it cannot meaningfully be attributed (8.7 GW as of the snapshot).

## Key Findings

**Germany's renewable fleet nearly quadrupled in 14 years:** from 51 GW installed at the end of 2010 to 186 GW at the end of 2024 - a 3.7x increase - with growth accelerating sharply in the final two years rather than leveling off.

**Solar had a boom-bust-boom decade.** Rooftop PV added 7-8 GW/year during the 2010-2012 feed-in-tariff boom, then collapsed to under 2 GW/year for most of 2013-2019 after tariffs were cut, before a historic resurgence: 15.4 GW added in 2023 and a record **21.0 GW in 2024 alone** - more than the entire 2013-2019 period combined. Solar overtook wind onshore as Germany's single largest renewable source around 2022 and now accounts for 54% of all installed renewable capacity (99.8 GW).

**Offshore wind's buildout has stalled.** 85% of today's 9.2 GW offshore fleet was installed in just five years (2013-2019, peaking at 2.3 GW in 2015 alone). Since 2020, annual additions have collapsed to a few hundred MW a year - 2021 saw literally zero new offshore capacity registered - well short of the pace needed to hit Germany's stated offshore targets.

**Renewable density is a story of land, not ambition.** The four states with the most installed capacity per capita - Brandenburg (679 MW/100k residents), Mecklenburg-Vorpommern (542), Sachsen-Anhalt (498) and Schleswig-Holstein (451) - are exactly the sparsely populated states with the most available land for wind and solar farms. The city-states sit at the opposite extreme: Berlin has just 12 MW per 100k residents (almost entirely rooftop solar) and Hamburg 19.

**A clear north-south technology divide.** Wind dominates the coastal/northern states (Schleswig-Holstein: 67% wind, 28% solar), while the southern states run on solar (Bayern: 79% solar, 8% wind; Baden-Württemberg: 77% solar, 12% wind) - a direct reflection of wind resource vs. solar irradiance geography.

## Charts

- `chart_capacity_growth_stacked.png` - cumulative installed capacity by technology, 2010-2024 (stacked area)
- `chart_annual_additions.png` - new capacity commissioned each year by technology, showing the boom/bust/boom cycle
- `chart_capacity_per_capita_by_state.png` - installed renewable capacity per 100,000 residents, ranked by state
- `chart_tech_mix_by_state.png` - wind share vs. solar share of each state's renewable mix
- `dashboard_preview.png` - combined summary dashboard

## Caveats

- The MaStR snapshot is dated 2025-02-09, so "2024" figures are complete calendar-year totals, while any 2025 reference is a ~6-week partial year and is called out separately rather than blended into the trend.
- MaStR self-reporting means a small share of records (particularly older or very small installations) have incomplete or unverified data; rows missing a commissioning date, state, or valid capacity were excluded in the Silver layer rather than imputed.
- "Capacity" throughout is nominal/gross nameplate capacity (`Bruttoleistung`), the standard unit in MaStR; actual generation output depends on capacity factors that vary by technology and location and isn't addressed by this registry.
- Offshore wind in the Exclusive Economic Zone (8.7 GW) is excluded from all state-level views since it isn't attributable to a Bundesland - see Pipeline notes above.
- Population figures for per-capita normalization are the same estimates derived in the [EV charging infrastructure project](https://github.com/KiranDarshak/german-ev-charging-infrastructure-analysis), reused here for consistency across the project series.

## Tools

Python, pandas, matplotlib. Structured as a Bronze/Silver/Gold pipeline consistent with dbt/BigQuery modeling conventions, matching the approach used in the [German Motorcycle Market Analysis](https://github.com/KiranDarshak/germany-motorcycle-market-analysis) project.
