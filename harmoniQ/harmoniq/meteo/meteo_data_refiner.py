#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

def main():
    # Répertoires
    raw_folder     = Path("raw")
    refined_folder = Path("refined")
    refined_folder.mkdir(exist_ok=True)

    # Ordre des colonnes : LOCAL_DATE, x, y, puis le reste alphabétique
    ordered_columns = [
        "LOCAL_DATE", "x", "y",
        "CLIMATE_IDENTIFIER", "DEW_POINT_TEMP", "DEW_POINT_TEMP_FLAG", "HUMIDEX", "HUMIDEX_FLAG",
        "ID", "LOCAL_DAY", "LOCAL_HOUR", "LOCAL_MONTH", "LOCAL_YEAR", "PRECIP_AMOUNT",
        "PRECIP_AMOUNT_FLAG", "PROVINCE_CODE", "RELATIVE_HUMIDITY", "RELATIVE_HUMIDITY_FLAG",
        "STATION_NAME", "STATION_PRESSURE", "STATION_PRESSURE_FLAG", "TEMP", "TEMP_FLAG",
        "UTC_DATE", "UTC_DAY", "UTC_MONTH", "UTC_YEAR", "VISIBILITY", "VISIBILITY_FLAG",
        "WEATHER_ENG_DESC", "WEATHER_FRE_DESC", "WINDCHILL", "WINDCHILL_FLAG", "WIND_DIRECTION",
        "WIND_DIRECTION_FLAG", "WIND_SPEED", "WIND_SPEED_FLAG"
    ]

    # Lire et concaténer tous les CSV
    all_dataframes = []
    for file_path in sorted(raw_folder.glob("*.csv")):
        try:
            df = pd.read_csv(file_path)
            df = df.reindex(columns=ordered_columns)
            all_dataframes.append(df)
        except Exception as e:
            print(f"Erreur avec {file_path.name} : {e}")

    if not all_dataframes:
        print("Aucun fichier traité.")
        return

    # Concaténation
    combined_df = pd.concat(all_dataframes, ignore_index=True)

    # Arrondi x et y à 5 décimales
    combined_df[['x', 'y']] = combined_df[['x', 'y']].round(5)

    # Conversion en datetime
    combined_df['LOCAL_DATE'] = pd.to_datetime(combined_df['LOCAL_DATE'])

    # Déterminer la plage annuelle à couvrir
    year_min = combined_df['LOCAL_DATE'].dt.year.min()
    year_max = combined_df['LOCAL_DATE'].dt.year.max()
    start = pd.Timestamp(f"{year_min}-01-01 00:00:00")
    end   = pd.Timestamp(f"{year_max}-01-01 00:00:00")

    # Index horaire continu
    full_idx = pd.date_range(start=start, end=end, freq='h')

    # Colonnes statiques à conserver même en l'absence de donnée
    static_cols = ['x', 'y', 'CLIMATE_IDENTIFIER', 'ID', 'STATION_NAME', 'PROVINCE_CODE']
    # Colonnes dynamiques à remplir ou NaN
    dynamic_cols = [c for c in ordered_columns if c not in (static_cols + ['LOCAL_DATE'])]

    station_frames = []
    for station, grp in combined_df.groupby('CLIMATE_IDENTIFIER'):
        # Extraction des infos statiques (première occurrence)
        info = grp.iloc[0]
        # Créer DataFrame vide indexé sur toutes les heures
        df_stat = pd.DataFrame(index=full_idx)
        # Remplir colonnes statiques
        for col in static_cols:
            df_stat[col] = info.get(col)
        # Récupérer les données dynamiques existantes
        grp_dyn = grp.set_index('LOCAL_DATE')[dynamic_cols]
        # Combiner : les heures manquantes restent NaN
        df_full = df_stat.join(grp_dyn)
        # Replacer l'index en colonne
        df_full = df_full.reset_index().rename(columns={'index': 'LOCAL_DATE'})
        station_frames.append(df_full)

    # Concaténer toutes les stations et trier
    final_df = pd.concat(station_frames, ignore_index=True)
    final_df = final_df.sort_values(['CLIMATE_IDENTIFIER', 'LOCAL_DATE'])

    # Réordonner les colonnes
    final_df = final_df.reindex(columns=ordered_columns)

    # Export
    final_df.to_csv(
        refined_folder / "meteo_data.csv",
        index=False,
        float_format="%.5f"
    )
    print("Fusion et remplissage terminés dans Refined/meteo_data.csv")

if __name__ == "__main__":
    main()
