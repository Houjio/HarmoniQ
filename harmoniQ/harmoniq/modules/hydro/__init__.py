from harmoniq.core.base import Infrastructure
from harmoniq.core.meteo import Granularity
from harmoniq.db.schemas import HydroBase, ScenarioBase
from harmoniq.modules.hydro.calcule import get_run_of_river_dam_power,estimation_cout_barrage,estimer_qualite_ecosysteme_futur,estimer_daly_futur,calculer_emissions_et_ressources
import pandas as pd

from typing import List

class InfraHydro():

    def __init__(self, donnees: List[HydroBase]):
        # super().__init__(donnees)
        self.donnees = donnees
        self.debit = None
        self.apport = None
        self.cout = None
        self.qualite_ecosysteme = None
        self.daly = None

    def _charger_debit(self): #Seulement pour les barrages au fil de l'Eau
        filename_debit = "C:/Users/olivi/Desktop/Git/HarmoniQ/harmoniQ/harmoniq/modules/hydro/debits/Debits.csv"
        debit = pd.read_csv(filepath_or_buffer=filename_debit)
        debit['dateTime'] = pd.to_datetime(debit["dateTime"])
        debit = debit.set_index('dateTime')
        if self.donnees.barrage_nom == "Beauharnois_Francis":
            self.debit = debit["Beauharnois"]/20
        elif self.donnees.barrage_nom == "Beauharnois_Kaplan":
            self.debit = debit["Beauharnois"]/16
        else:
            self.debit = debit

    def _charger_apport(self, scenario: ScenarioBase): #Seulement pour les barrages à réservoir
        id_HQ = self.donnees.id_HQ
        filename_apport = id_HQ + ".csv"
        self.apport = pd.read_csv(filepath_or_buffer=filename_apport)


    def _charger_scenario(self):
        # Ajouter un debit pour
        # scenario: ScenarioBase = self.scenario

        # date_debut = scenario.date_de_debut
        # date_fin = scenario.date_fin
        # granularite = (
        #     Granularity.HOURLY if scenario.pas_de_temps.days == 0 else Granularity.DAILY
        # )
        granularite = 1
        if self.donnees.type_barrage == "Fil de l'eau":
            if granularite == 2: #Hourly il va falloir faire une moyenne des 24 heures de débit
                self.debit : pd.DataFrame = self._charger_debit()
            else:
                self.debit : pd.DataFrame = self._charger_debit()

    

    def calculer_production(self) -> pd.DataFrame:

        if self.donnees.type_barrage == "Fil de l'eau":
            return get_run_of_river_dam_power(self)
        
    def calculer_cout_construction(puissance):
        return estimation_cout_barrage(puissance)
    
    def PDF_environnement(facteur_charge):
        return estimer_qualite_ecosysteme_futur(facteur_charge)
    
    def daly_futur(facteur_charge):
        return estimer_daly_futur(facteur_charge)
    
    def emission(self):
        return calculer_emissions_et_ressources(self)
    

if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_hydro, read_all_scenario
    from harmoniq.db.engine import get_db
    from datetime import datetime, timedelta

    db = next(get_db())
    barrage = read_all_hydro(db)[7] #La-grande-1
    infraHydro = InfraHydro(barrage)

    # scenario = read_all_scenario(db)[0]

    infraHydro._charger_debit()

    production = infraHydro.calculer_production()

    print(production)