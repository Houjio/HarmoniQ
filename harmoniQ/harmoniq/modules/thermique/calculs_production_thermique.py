import pandas as pd
from datetime import datetime

def calculate_thermique_production(
        power_mw: float, 
        maintenance_week: int,
        date_start: datetime, 
        date_end: datetime
    ) -> pd.DataFrame:
    """
    Calcule la production annuelle d'une centrale thermique en mWh.

    Parameters
    ----------
    power_mw : float
        Puissance nominale de la centrale en kilowatts (kW).
    maintenance_week : int
        Semaine de l'année où la production est nulle (1-52).
    date_start : datetime
        Date de début de la période de calcul.
    date_end : datetime
        Date de fin de la période de calcul.

    Returns
    -------
    DataFrame
        DataFrame contenant la production horaire en kWh pour chaque heure de la période.
    """
    # Créer un DataFrame avec une colonne pour chaque heure de l'année
    date_range = pd.date_range(
        start=date_start, end=date_end, freq="h"
    )
    production_df = pd.DataFrame(index=date_range, columns=["production_mwh"])

    # Calculer la production horaire en kWh (constante)
    production_df["production_mwh"] = power_mw
    
    # Appliquer la maintenance
    maintenance_week_dt = datetime.strptime(
        f"{date_start.year}-W{maintenance_week}-1", "%Y-W%W-%w"
    )
    maintenance_start = maintenance_week_dt
    maintenance_end = maintenance_start + pd.DateOffset(weeks=1)
    production_df.loc[
        (production_df.index >= maintenance_start)
        & (production_df.index < maintenance_end), "production_mwh"
    ] = 0

    return production_df

if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # Paramètres de la centrale nucléaire
    power_kw = 400*1000  # Puissance nominale d'une centrale thermique moyenne en kW (400 MW)
    maintenance_week = 22  # Semaine de maintenance

    # Calculer la production annuelle et hebdomadaire
    production_df = calculate_thermal_production(power_kw, maintenance_week)
    weekly_production = production_df.groupby('week')['production_kwh'].sum()

    # Calculer la production annuelle totale en kWh
    annual_thermal_production = production_df['production_kwh'].sum()
    print(f"Production électrique thermique annuelle totale : {annual_thermal_production:.2f} kWh")

    # Tracer le graphique de la production hebdomadaire
    plt.figure(figsize=(10, 6))
    plt.plot(weekly_production.index, weekly_production.values, marker='o', linestyle='-', color='b')
    plt.title('Production électrique thermique Hebdomadaire')
    plt.xlabel('Semaine de l\'année')
    plt.ylabel('Production (kWh)')
    plt.grid(True)
    plt.xticks(range(1, 53))
    plt.show()