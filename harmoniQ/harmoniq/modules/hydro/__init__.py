from harmoniq.core.base import Infrastructure
from harmoniq.core.meteo import Granularity
from harmoniq.db.schemas import HydroBase, ScenarioBase
from harmoniq.modules.hydro.calcule import (
    get_run_of_river_dam_power,
    estimation_cout_barrage,
    estimer_qualite_ecosysteme_futur,
    estimer_daly_futur,
    calculer_emissions_et_ressources,
    get_facteur_de_charge,
    get_energy,
    reservoir_infill,
)
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from typing import List

CURRENT_DIR = Path(__file__).parent
DEBIT_DIR = CURRENT_DIR / "debits"
APPORT_DIR = CURRENT_DIR / "apport_naturel"


class InfraHydro:

    def __init__(self, donnees: List[HydroBase]):
        # super().__init__(donnees)
        self.donnees = donnees
        self.debit = None
        self.apport = None
        self.cout = None
        self.qualite_ecosysteme = None
        self.daly = None
        self.production = None
    @necessite_scenario
    def _charger_debit(self):  # Seulement pour les barrages au fil de l'Eau
        filename_debit = str(self.donnees.nom) + ".csv"
        self.scenario
        start_date = self.date_de_debut
        end_date = self.date_de_fin

        if self.donnees.nom == "Beauharnois_Francis":
            debit = pd.read_csv(filepath_or_buffer=DEBIT_DIR / "Beauharnois.csv")
            debit["dateTime"] = pd.to_datetime(debit["dateTime"])
            debit = debit[
            (debit["dateTime"] >= start_date) & (debit["dateTime"] <= end_date)
            ]
            debit = debit.set_index("dateTime")
            self.debit = debit[["Beauharnois"]] * (26 / 36)
        elif self.donnees.nom == "Beauharnois_Kaplan":
            debit = pd.read_csv(filepath_or_buffer=DEBIT_DIR / "Beauharnois.csv")
            debit["dateTime"] = pd.to_datetime(debit["dateTime"])
            debit = debit[
            (debit["dateTime"] >= start_date) & (debit["dateTime"] <= end_date)
            ]
            debit = debit.set_index("dateTime")            
            self.debit = debit[["Beauharnois"]] * (10 / 36)
        else:
            debit = pd.read_csv(filepath_or_buffer=DEBIT_DIR / filename_debit)
            debit["dateTime"] = pd.to_datetime(debit["dateTime"])
            debit = debit[
            (debit["dateTime"] >= start_date) & (debit["dateTime"] <= end_date)
            ]
            debit = debit.set_index("dateTime")
            # debit = debit.resample("D").mean()
            self.debit = debit[[self.donnees.nom]]

    def charger_scenario(self, scenario):
        # Ajouter un debit pour
        # scenario: ScenarioBase = self.scenario

        # date_debut = scenario.date_de_debut
        # date_fin = scenario.date_fin
        # granularite = (
        #     Granularity.HOURLY if scenario.pas_de_temps.days == 0 else Granularity.DAILY
        # )
        self.scenario: ScenarioBase = scenario
        # granularite = 1
        # if self.donnees.type_barrage == "Fil de l'eau":
        #     if (
        #         granularite == 2
        #     ):  # Daily il va falloir faire une moyenne des 24 heures de débit
        #         self.debit: pd.DataFrame = self._charger_debit()
        #         self.debit = self.debit.resample("D").mean()
        #         self.apport: pd.DataFrame = self._charger_apport()
        #     else:
        #         self.debit: pd.DataFrame = self._charger_debit()
        #         self.apport: pd.DataFrame = self._charger_apport()
        #         self.apport["time"] = np.repeat(self.apport["time"].values, 24)
        #         offset = np.tile(
        #             pd.to_timedelta(np.arange(24), unit="h"), len(self.apport) // 24
        #         )
        #         self.apport["time"] += offset
        #         self.apport["streamflow"] = np.repeat(
        #             self.apport["streamflow"].values, 24
        #         )

    def calculer_production(self) -> pd.DataFrame:  # Fonctionne

        if self.donnees.type_barrage == "Fil de l'eau":
            return get_run_of_river_dam_power(self)
  
    def calculer_energie(self, production):
        return get_energy(production)

    def calculer_facteur_charge(self, production):  # Fonctionne
        return get_facteur_de_charge(self, production)

    def calculer_cout_construction(puissance):  # Fonctionne
        return estimation_cout_barrage(puissance)

    def PDF_environnement(self, facteur_charge):  # Fonctionne
        return estimer_qualite_ecosysteme_futur(facteur_charge)

    def daly_futur(self, facteur_charge):  # Fonctionne
        return estimer_daly_futur(facteur_charge)

    def emission(self, energie, facteur_charge):  # Fonctionne
        return calculer_emissions_et_ressources(self, energie, facteur_charge)


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_hydro, read_all_scenario
    from harmoniq.db.engine import get_db
    from datetime import datetime, timedelta


    db = next(get_db())
    production = pd.DataFrame({"hydro" : [0 for _ in range(0,366)]})
    barrage = read_all_hydro(db) #La-grande-1
    print("f")
    for i in range(0,len(barrage)):
        if barrage[i].nom != "Gull-Island" and barrage[i].type_barrage == "Fil de l'eau":

            infraHydro = InfraHydro(barrage[i])
            infraHydro._charger_debit()
        # # date_repetee = np.repeat(infraHydro.apport["time"].values,24)
        # # offset = np.tile(pd.to_timedelta(np.arange(24), unit="h"), len(infraHydro.apport))
        # # temps = date_repetee + offset
        # apport_repete = np.repeat(infraHydro.apport["streamflow"].values, 24)
        # apport_df = pd.DataFrame({"dateTime":temps, "streamflow" : apport_repete})
        # # Get the last recorded inflow
        # last_inflow = apport_df.iloc[-1]["streamflow"]  # Adjust column name if necessary
        # # Create the new row with the inflow from the last hour
        # new_entry = pd.DataFrame({
        # "dateTime": [pd.Timestamp("2026-01-01 00:00:00")],
        # "streamflow": [last_inflow]
        # })
        # # Append the new row to the DataFrame
        # apport_df = pd.concat([apport_df, new_entry], ignore_index=True)
        # infraHydro.apport = apport_df
            production["hydro"] += infraHydro.calculer_production().values
            cout = infraHydro.calculer_cout_construction()
            facteur_charge = infraHydro.calculer_facteur_charge(production)
            facteur_env = infraHydro.PDF_environnement(facteur_charge)
            daly = infraHydro.daly_futur(facteur_charge)
            energie = infraHydro.calculer_energie(production)
            emissions = infraHydro.emission(energie, facteur_charge)

        # elif barrage[i].type_barrage == "Reservoir":

        #     infraHydro = InfraHydro(barrage[i])
        #     production["hydro"] += demande[barrage[i].donnees.nom]

            # plt.plot(production.index, production.values)
            # plt.show()
    print(max(production["hydro"]))        
    print(production)
