import pandas as pd
from datetime import datetime


def calculate_nuclear_production(
        power_mw: float, 
        maintenance_week: int,
        date_start: datetime, 
        date_end: datetime
    ) -> pd.DataFrame:
    """
    Calcule la production annuelle d'une centrale nucléaire en mWh.

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


def co2_emissions_nuclear(annual_nuclear_production, facteur_emission=8):
    """
    Calcule les émissions totales de CO₂ équivalent pour une centrale nucléaire.

    Parameters
    ----------
    annual_nuclear_production : float
        Production annuelle totale de la centrale en kWh.
    facteur_emission : float
        Facteur d'émission en g CO₂eq/kWh basé sur l'ACV. Par défaut 8 g CO₂eq/kWh.

    Returns
    -------
    float
        Émissions totales de CO₂ en kg
    """
    # Calcul des émissions en grammes
    emissions_g = annual_nuclear_production * facteur_emission

    # Conversion en kilogrammes
    emissions_kg = emissions_g / 1000

    return emissions_kg


def cost_nuclear_powerplant(power_mw):
    """
    Estime le coût de construction d'une centrale nucléaire au Québec.

    Parameters
    ----------
    power_mw : float
        Puissance nominale de la centrale en kilowatts (kW)

    Returns
    -------
    float
        Coût total estimé en dollars canadiens
    """

    # Coûts de référence basés sur des projets récents
    cout_base_par_mw = 4_000_000  # 4M$ par MW

    # Facteurs d'ajustement
    facteur_echelle = 0.85  # Économies d'échelle
    facteur_region = (
        1.1  # Ajustement pour le Québec (conditions climatiques, normes, etc.)
    )

    # Calcul du coût total
    cout_total = cout_base_par_mw * (power_mw**facteur_echelle) * facteur_region

    return cout_total


# ---------------- APPEL DES FONCTIONS ----------------

if __name__ == "__main__":
    import matplotlib.pyplot as plt

    power_mw = 300  # Puissance nominale en MW (
    maintenance_week = 20  # Semaine de maintenance

    # Calculer la production annuelle et hebdomadaire
    production_df = calculate_nuclear_production(power_mw, maintenance_week)
    weekly_production = production_df.groupby("week")["production_mwh"].sum()

    # Calculer la production annuelle totale en kWh
    annual_nuclear_production = production_df["production_mwh"].sum()
    # Déplacer tous les calculs et affichages ensemble
    annual_nuclear_production = production_df["production_mwh"].sum()
    Total_emission = co2_emissions_nuclear(annual_nuclear_production)
    cout_construction = cost_nuclear_powerplant(power_mw)

    print("\n=== RÉSULTATS DE LA CENTRALE NUCLÉAIRE ===")
    print(f"Production nucléaire hebdomadaire : {weekly_production}")
    print(f"Production nucléaire annuelle totale : {annual_nuclear_production:.2f} kWh")
    print(f"Total des émissions de CO2 : {Total_emission:.2f} kg CO2eq")
    print(f"Coût de construction estimé : {cout_construction:,.2f} $")
    print("\n")  # Ligne vide pour séparer les résultats du graphique

    # Tracer le graphique de la production hebdomadaire
    plt.figure(figsize=(10, 6))
    plt.plot(
        weekly_production.index,
        weekly_production.values,
        marker="o",
        linestyle="-",
        color="b",
    )
    plt.title("Production Nucléaire Hebdomadaire")
    plt.xlabel("Semaine de l'année")
    plt.ylabel("Production (kWh)")
    plt.grid(True)
    plt.xticks(range(1, 53))
    plt.show()
