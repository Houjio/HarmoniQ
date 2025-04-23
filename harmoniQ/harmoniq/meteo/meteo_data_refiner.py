#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

def main():
    raw_folder = Path("raw")
    refined_folder = Path("refined")
    refined_folder.mkdir(exist_ok=True)

    # remove any existing output
    final_csv = refined_folder / "meteo_data.csv"
    if final_csv.exists():
        final_csv.unlink()

    # column order
    ordered_columns = [
        "LOCAL_DATE", "x", "y", "CLIMATE_IDENTIFIER",
        "DEW_POINT_TEMP", "DEW_POINT_TEMP_FLAG", "HUMIDEX", "HUMIDEX_FLAG",
        "ID", "LOCAL_DAY", "LOCAL_HOUR", "LOCAL_MONTH", "LOCAL_YEAR",
        "PRECIP_AMOUNT", "PRECIP_AMOUNT_FLAG", "PROVINCE_CODE",
        "RELATIVE_HUMIDITY", "RELATIVE_HUMIDITY_FLAG",
        "STATION_NAME", "STATION_PRESSURE", "STATION_PRESSURE_FLAG",
        "TEMP", "TEMP_FLAG",
        "UTC_DATE", "UTC_DAY", "UTC_MONTH", "UTC_YEAR",
        "VISIBILITY", "VISIBILITY_FLAG",
        "WEATHER_ENG_DESC", "WEATHER_FRE_DESC",
        "WINDCHILL", "WINDCHILL_FLAG",
        "WIND_DIRECTION", "WIND_DIRECTION_FLAG",
        "WIND_SPEED", "WIND_SPEED_FLAG"
    ]
    export_cols = ordered_columns + ["ORIGINAL_DATA"]

    # === Step 1: Lecture et concaténation des CSV ===
    csv_files = sorted(raw_folder.glob("*.csv"))
    if not csv_files:
        print("❌ Aucun CSV trouvé dans", raw_folder)
        return
    print("=== Step 1: Lecture et concaténation des CSV ===")
    dfs = []
    total_files = len(csv_files)
    for idx, fp in enumerate(csv_files, start=1):
        print(f"  [1/{total_files}] Lecture de {fp.name}")
        df_part = pd.read_csv(fp)
        df_part.columns = df_part.columns.str.strip()
        df_part = df_part.reindex(columns=ordered_columns)
        dfs.append(df_part)
    df = pd.concat(dfs, ignore_index=True)
    print(f"  ✅ Concaténation terminée: {len(df)} lignes")

    # === Step 2: Création de l'index horaire global ===
    print("=== Step 2: Création de l'index horaire global ===")
    df["LOCAL_DATE"] = pd.to_datetime(df["LOCAL_DATE"])
    start_time = df["LOCAL_DATE"].min().floor('h')
    end_time = df["LOCAL_DATE"].max().ceil('h')
    full_idx = pd.date_range(start_time, end_time, freq='h')
    print(f"  🔧 Index de {start_time} à {end_time} ({len(full_idx)} créneaux)")

    # === Step 3: Nettoyage des types et déduplication ===
    print("=== Step 3: Nettoyage des types et déduplication ===")
    df[["x","y"]] = df[["x","y"]].round(5)
    df["CLIMATE_IDENTIFIER"] = df["CLIMATE_IDENTIFIER"].astype(str)
    before = len(df)
    df = df.drop_duplicates(["CLIMATE_IDENTIFIER","LOCAL_DATE"]).reset_index(drop=True)
    after = len(df)
    print(f"  ❇ Supprimé {before-after} doublons, restant {after} lignes")

    # === Step 4: Construction des DataFrames par station ===
    print("=== Step 4: Construction des DataFrames par station ===")
    static_cols = ['x','y','CLIMATE_IDENTIFIER','ID','STATION_NAME','PROVINCE_CODE']
    dyn_cols = [c for c in ordered_columns if c not in static_cols + ['LOCAL_DATE']]
    stations = sorted(df['CLIMATE_IDENTIFIER'].unique())
    station_tables = {}
    for i, sid in enumerate(stations, start=1):
        print(f"  [4/{len(stations)}] Station {sid}")
        base = pd.DataFrame(index=full_idx)
        info = df[df['CLIMATE_IDENTIFIER']==sid].iloc[0]
        for c in static_cols:
            base[c] = info[c]
        dyn = df[df['CLIMATE_IDENTIFIER']==sid].set_index('LOCAL_DATE')[dyn_cols]
        sdf = base.join(dyn)
        sdf['ORIGINAL_DATA'] = sdf[dyn_cols].notna().any(axis=1)
        sdf['CLIMATE_IDENTIFIER'] = sid
        station_tables[sid] = sdf
    print(f"  ✅ {len(stations)} DataFrames créés")

    # === Step 5: Interpolation linéaire par station ===
    print("=== Step 5: Interpolation linéaire par station ===")
    for i, sid in enumerate(stations, start=1):
        print(f"  [5/{len(stations)}] Station {sid}")
        sdf = station_tables[sid]
        # identify numeric vs non-numeric dyn_cols
        num_cols = [c for c in dyn_cols if pd.api.types.is_numeric_dtype(sdf[c])]
        str_cols = [c for c in dyn_cols if c not in num_cols]
        # linear interpolation over time for numeric columns
        sdf[num_cols] = sdf[num_cols].interpolate(method='time', limit_direction='both')
        # forward fill for strings, then infer objects to avoid downcasting warning
        sdf[str_cols] = sdf[str_cols].ffill().infer_objects(copy=False)
        station_tables[sid] = sdf
    print("  ✅ Interpolation linéaire terminée")

    # === Step 6: Concaténation finale et export ===
    print("=== Step 6: Concaténation finale et export ===")
    out = pd.concat(station_tables.values())
    out = out.reset_index().rename(columns={'index':'LOCAL_DATE'})
    out = out.sort_values(['CLIMATE_IDENTIFIER','LOCAL_DATE']).reset_index(drop=True)
    out = out.reindex(columns=export_cols)
    out.to_csv(final_csv, index=False, float_format="%.5f")
    print(f"✅ Terminé: {final_csv} généré avec interpolation linéaire.")

if __name__ == "__main__":
    main()