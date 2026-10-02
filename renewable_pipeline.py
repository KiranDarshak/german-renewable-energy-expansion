"""
Bronze -> Silver pipeline
German Renewable Energy Grid Expansion 2010-2025
Data: Marktstammdatenregister (MaStR) unit-level registry, Bundesnetzagentur.
Snapshot via Open Energy Family's open-MaStR Zenodo archive (2025-02-09), doi.org/10.5281/zenodo.14843222.

Solar is read directly out of its zip in chunks (4.95M rows) rather than extracted to disk,
since the decompressed file is ~3.9GB - too large to keep around, and not needed once aggregated.
Each technology is reduced, during ingestion, to two small tables: capacity ADDED by
(Bundesland, commission_year) and capacity REMOVED by (Bundesland, decommission_year).
Summing additions minus removals, cumulatively by year, gives net installed capacity -
this correctly accounts for decommissioned/repowered units instead of just assuming
everything ever commissioned is still standing.
"""
import pandas as pd
import numpy as np

RAW = "data/raw"
COLS = ["Bundesland", "Inbetriebnahmedatum", "DatumEndgueltigeStilllegung",
        "Bruttoleistung", "EinheitBetriebsstatus", "Energietraeger"]

TECH_MAP = {
    "Biomasse": "Biomass",
    "Wasser": "Hydropower",
    "Solare Strahlungsenergie": "Solar",
}

def technology_label(energietraeger, lage):
    if energietraeger == "Wind":
        if isinstance(lage, str) and "See" in lage:
            return "Wind offshore"
        return "Wind onshore"
    return TECH_MAP.get(energietraeger, energietraeger)

def clean_chunk(df):
    """Shared cleaning: types, date bounds, technology label. Returns cleaned rows."""
    if "Lage" not in df.columns:
        df["Lage"] = np.nan
    df["Inbetriebnahmedatum"] = pd.to_datetime(df["Inbetriebnahmedatum"], errors="coerce")
    df["DatumEndgueltigeStilllegung"] = pd.to_datetime(df["DatumEndgueltigeStilllegung"], errors="coerce")
    df["capacity_mw"] = pd.to_numeric(df["Bruttoleistung"], errors="coerce") / 1000.0
    df = df.dropna(subset=["Inbetriebnahmedatum", "capacity_mw", "Bundesland"])
    df = df[df["Bundesland"].str.strip() != ""]
    df = df[(df["Inbetriebnahmedatum"].dt.year >= 1900) & (df["Inbetriebnahmedatum"].dt.year <= 2025)]  # keep pre-2000 plants so cumulative totals from 2010 onward include the existing (often century-old) hydro fleet
    df = df[df["capacity_mw"] > 0]
    df["technology"] = [technology_label(e, l) for e, l in zip(df["Energietraeger"], df["Lage"])]
    df["commission_year"] = df["Inbetriebnahmedatum"].dt.year
    df["decommission_year"] = df["DatumEndgueltigeStilllegung"].dt.year
    return df

def aggregate(df):
    adds = df.groupby(["Bundesland", "technology", "commission_year"])["capacity_mw"].sum().reset_index()
    adds.columns = ["Bundesland", "technology", "year", "capacity_added_mw"]
    rem_rows = df.dropna(subset=["decommission_year"])
    rems = rem_rows.groupby(["Bundesland", "technology", "decommission_year"])["capacity_mw"].sum().reset_index()
    rems.columns = ["Bundesland", "technology", "year", "capacity_removed_mw"]
    return adds, rems

SOURCES = {
    "wind": f"{RAW}/bnetza_mastr_wind_raw.csv.zip",
    "biomass": f"{RAW}/bnetza_mastr_biomass_raw.csv.zip",
    "hydro": f"{RAW}/bnetza_mastr_hydro_raw.csv.zip",
}

all_adds, all_rems = [], []
total_bronze_rows = 0

for tech, path in SOURCES.items():
    print(f"Loading {tech} from {path} ...")
    cols = COLS + (["Lage"] if tech == "wind" else [])
    df = pd.read_csv(path, compression="zip", usecols=lambda c: c in cols, encoding="utf-8", low_memory=False)
    total_bronze_rows += len(df)
    print(f"  bronze rows: {len(df):,}")
    df = clean_chunk(df)
    adds, rems = aggregate(df)
    all_adds.append(adds)
    all_rems.append(rems)

# Solar: stream in chunks directly from the zip (4.95M rows, ~722.9MB compressed / ~3.9GB raw)
print("Loading solar from data/raw/bnetza_mastr_solar_raw.csv.zip (chunked, streamed from zip)...")
solar_rows = 0
for i, chunk in enumerate(pd.read_csv(f"{RAW}/bnetza_mastr_solar_raw.csv.zip", compression="zip",
                                       usecols=lambda c: c in COLS, chunksize=300000, low_memory=False)):
    solar_rows += len(chunk)
    chunk = clean_chunk(chunk)
    adds, rems = aggregate(chunk)
    all_adds.append(adds)
    all_rems.append(rems)
    if i % 4 == 0:
        print(f"  ...processed {solar_rows:,} solar rows so far")
total_bronze_rows += solar_rows
print(f"  bronze rows (solar): {solar_rows:,}")
print(f"\nTotal bronze rows (all technologies): {total_bronze_rows:,}")

# ---------------------------------------------------------------------------
# SILVER: combine partial aggregates from every chunk/technology
# ---------------------------------------------------------------------------
additions = pd.concat(all_adds, ignore_index=True).groupby(
    ["Bundesland", "technology", "year"])["capacity_added_mw"].sum().reset_index()
removals = pd.concat(all_rems, ignore_index=True).groupby(
    ["Bundesland", "technology", "year"])["capacity_removed_mw"].sum().reset_index()

print("\nTotal capacity added by technology (MW), all years:")
print(additions.groupby("technology")["capacity_added_mw"].sum().sort_values(ascending=False))
print("\nTotal capacity removed/decommissioned by technology (MW), all years:")
print(removals.groupby("technology")["capacity_removed_mw"].sum().sort_values(ascending=False))

additions.to_csv("data/silver/silver_capacity_additions.csv", index=False)
removals.to_csv("data/silver/silver_capacity_removals.csv", index=False)
print(f"\nSilver tables written: {len(additions):,} addition rows, {len(removals):,} removal rows")
