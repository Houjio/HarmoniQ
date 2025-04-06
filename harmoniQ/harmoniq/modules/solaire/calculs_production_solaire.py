import pvlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from data_solaire import coordinates_centrales, coordinates_residential, population_relative
from typing import List

def get_weather_data(coordinates_residential):
    tmys = []
    for location in coordinates_residential:
        latitude, longitude, name, altitude, timezone = location
        print(f"\nRécupération des données météo pour {name}...")
        weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude)[0]
        weather.index.name = "utc_time"
        tmys.append(weather)
    return tmys


def calculate_solar_parameters(
    weather,
    latitude,
    longitude,
    altitude,
    temperature_model_parameters,
    module,
    inverter,
    surface_tilt,
    surface_orientation,
):
    solpos = pvlib.solarposition.get_solarposition(
        time=weather.index,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        temperature=weather["temp_air"],
        pressure=pvlib.atmosphere.alt2pres(altitude),
    )
    dni_extra = pvlib.irradiance.get_extra_radiation(weather.index)
    airmass = pvlib.atmosphere.get_relative_airmass(solpos["apparent_zenith"])
    pressure = pvlib.atmosphere.alt2pres(altitude)
    am_abs = pvlib.atmosphere.get_absolute_airmass(airmass, pressure)
    aoi = pvlib.irradiance.aoi(
        surface_tilt,
        surface_orientation,
        solpos["apparent_zenith"],
        solpos["azimuth"],
    )
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt,
        surface_orientation,
        solpos["apparent_zenith"],
        solpos["azimuth"],
        weather["dni"],
        weather["ghi"],
        weather["dhi"],
        dni_extra=dni_extra,
        model="haydavies",
    )
    cell_temperature = pvlib.temperature.sapm_cell(
        total_irradiance["poa_global"],
        weather["temp_air"],
        weather["wind_speed"],
        **temperature_model_parameters,
    )
    effective_irradiance = pvlib.pvsystem.sapm_effective_irradiance(
        total_irradiance["poa_direct"],
        total_irradiance["poa_diffuse"],
        am_abs,
        aoi,
        module,
    )
    dc = pvlib.pvsystem.sapm(effective_irradiance, cell_temperature, module)
    ac = pvlib.inverter.sandia(dc["v_mp"], dc["p_mp"], inverter)
    return ac


def convert_solar(value, module, mode="surface_to_power"):
    panel_efficiency = module["Impo"] * module["Vmpo"] / (1000 * module["Area"])

    if mode == "surface_to_power":
        power_w = value * panel_efficiency * 1000
        power_kw = power_w / 1000
        return power_kw
    elif mode == "power_to_surface":
        surface_m2 = value * 1000 / (panel_efficiency * 1000)
        return surface_m2
    else:
        raise ValueError(
            "Mode invalide. Utilisez 'surface_to_power' ou 'power_to_surface'."
        )
start_time = time.time()


def calculate_energy_solar_plants(coordinates_centrales, surface_tilt=45, surface_orientation=180):

    # Initialisation des modèles
    sandia_modules = pvlib.pvsystem.retrieve_sam("SandiaMod")
    sapm_inverters = pvlib.pvsystem.retrieve_sam("cecinverter")

    module = sandia_modules["Canadian_Solar_CS5P_220M___2009_"]
    inverter = sapm_inverters["ABB__MICRO_0_25_I_OUTD_US_208__208V_"]
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS[
        "sapm"
    ]["open_rack_glass_glass"]

    resultats_centrales = {}
    results_list = []  # Liste pour stocker les résultats pour le DataFrame
    energie_totale = 0

    for centrale in coordinates_centrales:
        latitude, longitude, name, altitude, timezone, puissance_kw = centrale

        # Récupération des données météo
        weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude)[0]
        weather.index.name = "utc_time"

        # Calcul du nombre de modules nécessaires
        puissance_module_w = module["Impo"] * module["Vmpo"]
        nombre_modules = int(np.ceil((puissance_kw * 1000) / puissance_module_w))

        # Calcul de la production
        print(f"Calcul de la production pour {name} ({puissance_kw} kW)...")
        ac = calculate_solar_parameters(
            weather,
            latitude,
            longitude,
            altitude,
            temperature_model_parameters,
            module,
            inverter,
            surface_tilt,
            surface_orientation,
        )

        # Mise à l'échelle selon la puissance de la centrale
        ac_scaled = ac * nombre_modules
        annual_energy = ac_scaled.sum()
        energie_totale += annual_energy

        # Stockage des résultats pour cette centrale dans le dictionnaire
        resultats_centrales[name] = {
            "energie_annuelle_wh": annual_energy,
            "energie_horaire": ac_scaled,
            "nombre_modules": nombre_modules,
            "puissance_kw": puissance_kw,
        }

        # Stockage des résultats pour cette centrale dans la liste pour le DataFrame
        results_list.append({
            "nom_centrale": name,
            "latitude": latitude,
            "longitude": longitude,
            "puissance_kw": puissance_kw,
            "energie_annuelle_kwh": annual_energy / 1000,  # Conversion en kWh
            "nombre_modules": nombre_modules,
        })

    resultats_centrales["energie_totale_wh"] = energie_totale
    resultats_centrales_df = pd.DataFrame(results_list)

    return resultats_centrales, resultats_centrales_df

def calculate_regional_residential_solar(
    coordinates_residential: List[tuple],
    population_relative,
    total_clients,
    num_panels_per_client,
    surface_tilt,
    surface_orientation,
):

    # Initialisation des modèles
    sandia_modules = pvlib.pvsystem.retrieve_sam("SandiaMod")
    module = sandia_modules["Canadian_Solar_CS5P_220M___2009_"]

    resultats_regions = {}
    results_list = []  # Liste pour stocker les résultats pour le DataFrame

    for coordinates in coordinates_residential:
        latitude, longitude, nom_region, altitude, timezone = coordinates
        population_weight = population_relative.get(nom_region, 0)
        num_clients_region = total_clients * population_weight
        surface_panneau_region = (
            num_clients_region * num_panels_per_client * module["Area"]
        )

        # Conversion de la surface en puissance
        puissance_installee_kw = convert_solar(
            surface_panneau_region, module, mode="surface_to_power"
        )

        # Création du tuple de coordonnées avec la puissance
        coordinates_with_power = (
            latitude,
            longitude,
            nom_region,
            altitude,
            timezone,
            puissance_installee_kw,
        )

        # Calcul de la production d'énergie
        production_dict, production_df = calculate_energy_solar_plants(
            [coordinates_with_power],  # Liste avec un seul tuple de coordonnées
            surface_tilt=surface_tilt,
            surface_orientation=surface_orientation,
        )

        # Récupération des résultats pour cette région à partir du dictionnaire
        region_results = production_dict[nom_region]

        # Stockage des résultats dans le dictionnaire
        resultats_regions[nom_region] = {
            "energie_annuelle_kwh": region_results["energie_annuelle_wh"] / 1000,
            "puissance_installee_kw": puissance_installee_kw,
            "surface_installee_m2": surface_panneau_region,
            "latitude": latitude,
            "longitude": longitude,
        }

        # Stockage des résultats pour le DataFrame
        results_list.append({
            "nom_region": nom_region,
            "latitude": latitude,
            "longitude": longitude,
            "puissance_installee_kw": puissance_installee_kw,
            "surface_installee_m2": surface_panneau_region,
            "energie_annuelle_kwh": region_results["energie_annuelle_wh"] / 1000,
        })

    resultats_regions_df = pd.DataFrame(results_list)

    return resultats_regions, resultats_regions_df

def cost_solar_powerplant(coordinates_centrales, resultats_centrales):
    """
    Calcule le coût total pour chaque centrale solaire.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales
    resultats_centrales : dict
        Dictionnaire contenant l'énergie produite par chaque centrale

    Returns
    -------
    dict
        Dictionnaire contenant le coût total en dollars pour chaque centrale
    """
    couts = {}

    for centrale in coordinates_centrales:
        nom = centrale[2]
        puissance_mw = centrale[5] / 1000  # Conversion kW en MW

        # Coût de référence par MW pour le Québec
        cout_par_mw = 4_210_000  # Estimation moyenne des coûts actuels

        # Coût total prenant en compte les coûts indirects et opérationnels
        cout_total = puissance_mw * cout_par_mw

        couts[nom] = cout_total

    return couts


def calculate_installation_cost(coordinates_centrales):
    """
    Calcule le coût d'installation pour chaque centrale solaire avec une estimation plus précise.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales

    Returns
    -------
    dict
        Dictionnaire contenant le coût d'installation pour chaque centrale
    """
    couts_installation = {}

    for centrale in coordinates_centrales:
        nom = centrale[2]
        puissance_mw = centrale[5] / 1000  # Conversion kW en MW

        # Coûts de base par MW selon la taille de l'installation
        if puissance_mw < 1:
            cout_base = 4_500_000  # Plus cher pour petites installations
        elif 1 <= puissance_mw < 5:
            cout_base = 4_210_000  # Coût moyen
        else:
            cout_base = 3_900_000  # Économies d'échelle pour grandes installations

        # Facteurs d'ajustement
        facteur_echelle = 0.85  # Économies d'échelle
        facteur_complexite = 1.1  # Complexité du site et infrastructure

        # Calcul du coût d'installation avec facteurs
        cout_installation = (
            cout_base * (puissance_mw**facteur_echelle) * facteur_complexite
        )

        couts_installation[nom] = cout_installation

    return couts_installation


def calculate_lifetime(coordinates_centrales):
    """
    Estime la durée de vie des centrales solaires en fonction de leurs puissances installées.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales sous forme de tuples
        (latitude, longitude, nom, altitude, timezone, puissance_kw)

    Returns
    -------
    dict
        Dictionnaire contenant la durée de vie estimée pour chaque centrale
    """
    durees_vie = {}

    for centrale in coordinates_centrales:
        nom = centrale[2]
        puissance_mw = centrale[5] / 1000  # Conversion kW en MW

        if puissance_mw < 1:
            duree_vie = 25  # Petites installations
        elif 1 <= puissance_mw < 10:
            duree_vie = 30  # Installations moyennes
        else:
            duree_vie = 35  # Grandes installations

        durees_vie[nom] = duree_vie

    return durees_vie


def co2_emissions_solar(
    coordinates_centrales, resultats_centrales, facteur_emission=40
):
    """
    Calcule les émissions totales de CO₂ équivalent pour chaque centrale solaire sur toute sa durée de vie.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales
    resultats_centrales : dict
        Dictionnaire contenant l'énergie produite par chaque centrale
    facteur_emission : float, optional
        Facteur d'émission en g CO₂eq/kWh basé sur l'ACV

    Returns
    -------
    dict
        Dictionnaire contenant les émissions totales de CO₂ en kg pour chaque centrale
    """
    emissions = {}
    durees_vie = calculate_lifetime(coordinates_centrales)

    for centrale in coordinates_centrales:
        nom = centrale[2]
        energie_kwh = resultats_centrales[nom]["energie_annuelle_wh"] / 1000
        duree_vie = durees_vie[nom]

        # Calcul des émissions sur toute la durée de vie
        emissions_g = energie_kwh * facteur_emission * duree_vie
        emissions[nom] = emissions_g / 1000

    return emissions


# Exemple d'utilisation
if __name__ == "__main__":

        # Appel des fonction
    resultats_regions, resultats_regions_df = calculate_regional_residential_solar(
        coordinates_residential,
        population_relative,
        total_clients=125000,
        num_panels_per_client=4,
        surface_tilt=0,
        surface_orientation=180,
    )
    
    resultats_centrales, resultats_centrales_df = calculate_energy_solar_plants(coordinates_centrales)
    energie_centrales = resultats_centrales["energie_totale_wh"]
    couts = cost_solar_powerplant(coordinates_centrales, resultats_centrales)
    couts_installation = calculate_installation_cost(coordinates_centrales)
    durees_vie = calculate_lifetime(coordinates_centrales)
    emissions_co2 = co2_emissions_solar(coordinates_centrales, resultats_centrales)

    # # Affichage des résultats
    # print("\n=== RÉSULTATS PAR CENTRALE ===")
    # for centrale in coordinates_centrales:
    #     nom = centrale[2]
    #     duree_vie = durees_vie[nom]
    #     print(f"\n{nom}:")
    #     print(
    #         f"  Production annuelle : {resultats_centrales[nom]['energie_annuelle_wh']/1000:,.2f} kWh"
    #     )
    #     print(f"  Puissance installée : {centrale[5]:,.2f} kW")
    #     print(f"  Coût total : {couts[nom]:,.2f} $")
    #     print(f"  Coût d'installation : {couts_installation[nom]:,.2f} $")
    #     print(f"  Durée de vie estimée : {duree_vie} ans")
    #     print(
    #         f"  Émissions CO₂ totales : {emissions_co2[nom]:,.2f} kg CO₂eq sur {duree_vie} ans"
    #     )


    # print("\n=== RÉSUMÉ DES RÉSULTATS POUR TOUTES LES RÉGIONS ===")
    # energie_totale = 0
    # for nom_region, data in resultats_regions.items():
    #     energie_totale += data["energie_annuelle_kwh"]
    
    # print(f"\nProduction totale pour toutes les régions : {energie_totale:,.2f} kWh")

end_time = time.time()
print(f"\nTemps d'exécution : {end_time - start_time:.2f} secondes")



# # ------------   Validation avec données réelles Hydro-Québec ----------------------##
# def load_csv(file_path):
#     """
#     Charge le fichier CSV contenant les données de production solaire.

#     Parameters
#     ----------
#     file_path : str
#         Chemin vers le fichier CSV.

#     Returns
#     -------
#     DataFrame
#         DataFrame contenant les données de production solaire.
#     """
#     return pd.read_csv(file_path, sep=";")


# def plot_validation(resultats_centrales, real_data):
#     """
#     Superpose sur un graphique mensuel la production des centrales solaires simulée totale avec les données réelles.

#     Parameters
#     ----------
#     resultats_centrales : dict
#         Dictionnaire contenant les résultats des centrales solaires simulées.
#     real_data : DataFrame
#         DataFrame contenant les données de production solaire réelle.
#     """
#     # Combiner les données horaires de toutes les centrales simulées
#     simulated_data = pd.concat(
#         [
#             resultats_centrales[name]["energie_horaire"]
#             for name in resultats_centrales.keys()
#             if name != "energie_totale_wh"
#         ]
#     )
#     simulated_data = simulated_data.groupby(simulated_data.index).sum()

#     # Assurez-vous que simulated_data est un DataFrame et ajoutez la colonne 'production_kwh'
#     simulated_data = simulated_data.to_frame(name="production_kwh")
#     simulated_data["month"] = simulated_data.index.month

#     # Calculer la production mensuelle simulée
#     monthly_simulated = (
#         simulated_data.groupby("month")["production_kwh"].sum() / 1e6
#     )  # Conversion de Wh en MWh

#     real_data["Solaire"] = real_data["Solaire"]

#     # Calculer la production mensuelle réelle
#     real_data["month"] = pd.to_datetime(real_data["Date"]).dt.month
#     monthly_real = real_data.groupby("month")["Solaire"].sum()
#     # Tracer le graphique
#     plt.figure(figsize=(10, 6))
#     plt.plot(
#         monthly_simulated.index,
#         monthly_simulated.values,
#         marker="o",
#         linestyle="-",
#         color="b",
#         label="Production simulée",
#     )
#     plt.plot(
#         monthly_real.index,
#         monthly_real.values,
#         marker="o",
#         linestyle="-",
#         color="r",
#         label="Production réelle",
#     )
#     plt.title("Production Solaire Mensuelle")
#     plt.xlabel("Mois")
#     plt.ylabel("Production (MWh)")
#     plt.legend()
#     plt.grid(True)
#     plt.xticks(range(1, 13))
#     plt.show()


# # Charger les données réelles
# file_path = "2022-sources-electricite-quebec.csv"
# real_data = load_csv(file_path)

# # # Superposer les données simulées et réelles sur un graphique
# # plot_validation(resultats_centrales, real_data)
