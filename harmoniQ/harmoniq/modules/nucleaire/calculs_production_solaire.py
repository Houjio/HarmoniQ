import pandas as pd
import matplotlib.pyplot as plt

def calculate_nuclear_production(power_kw, maintenance_week, maintenance_duration_days):
    """
    Calcule la production annuelle d'une centrale nucléaire en kWh, en tenant compte de la période de maintenance.

    Parameters
    ----------
    power_kw : float
        Puissance nominale de la centrale en kilowatts (kW).
    maintenance_week : int
        Semaine de l'année où la maintenance commence (1-52).
    maintenance_duration_days : int
        Durée de la maintenance en jours.

    Returns
    -------
    DataFrame
        DataFrame contenant la production horaire en kWh pour chaque heure de l'année.
    """
    # Créer un DataFrame avec une colonne pour chaque heure de l'année
    date_range = pd.date_range(start='2023-01-01', end='2023-12-31 23:00:00', freq='H')
    production_df = pd.DataFrame(index=date_range, columns=['production_kwh'])
    
    # Calculer la production horaire en kWh
    production_df['production_kwh'] = power_kw
    
    # Calculer les dates de début et de fin de la maintenance pour couvrir toute la semaine 20
    maintenance_start = pd.Timestamp('2023-01-01') + pd.Timedelta(weeks=maintenance_week - 1)
    maintenance_end = maintenance_start + pd.Timedelta(days=6)  # 7 jours de maintenance
    
    # Mettre la production à zéro pendant la période de maintenance
    production_df.loc[maintenance_start:maintenance_end, 'production_kwh'] = 0
    
    return production_df

# Paramètres de la centrale nucléaire
power_kw = 1000  # Puissance nominale en kW
maintenance_week = 20  # Semaine de maintenance
maintenance_duration_days = 7  # Durée de la maintenance en jours

# Calculer la production annuelle
production_df = calculate_nuclear_production(power_kw, maintenance_week, maintenance_duration_days)

# Calculer la production hebdomadaire
production_df['week'] = production_df.index.isocalendar().week
weekly_production = production_df.groupby('week')['production_kwh'].sum()

# Afficher les premières lignes du DataFrame
print(production_df.head(24 * 21))  # Afficher les premières 21 jours (504 heures)

# Calculer la production annuelle totale en kWh
annual_nuclear_production = production_df['production_kwh'].sum()
print(f"Production annuelle totale : {annual_nuclear_production:.2f} kWh")

# Tracer le graphique de la production hebdomadaire
plt.figure(figsize=(10, 6))
plt.plot(weekly_production.index, weekly_production.values, marker='o', linestyle='-', color='b')
plt.title('Production Nucléaire Hebdomadaire')
plt.xlabel('Semaine de l\'année')
plt.ylabel('Production (kWh)')
plt.grid(True)
plt.xticks(range(1, 53))
plt.show()