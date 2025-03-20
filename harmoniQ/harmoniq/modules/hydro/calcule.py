import pandas as pd
import numpy as np
import HydroGenerate as hg

from HydroGenerate.hydropower_potential import calculate_hp_potential

def reservoir_infill(Type_barrage, nb_turbines, Debit_nom, Volume_remplie, nom_barrage, besoin_puissance, info_puissance, pourcentage_reservoir, debit_entrant, nbr_turb_maintenance): #Ajouter débit entrant pour les réservoirs

    # La fonction reservoir_infill permet de calculer le pourcentage de remplissage du réservoir associé à un barrage 
    # en fonction du nombre turbines actives, du débit entrant dans le réservoir et du 
    # pourcentage de remplissage du réservoir actuel.
    # Variable en entrée :
    #   - info_barrage : Dataframe contenant les informations des barrages extraite du csv Info_Barrages.csv. Les colonnes du dataframe utilisées dans la fonction sont les suivantes
    #       - Nom : Nom du barrage [string]
    #       - Type : Type du barrage ["Fil de l'eau" vs "Reservoir" (string)]
    #       - Debits_nom : Debit d'équipement des turbines en m^3/s [float]
    #       - Nb_turbines : Nombre de turbines installée dans le barrage [float]
    #       - Volume_reservoir : Volume du réservoir associé au barrage à réservoir en m^3 [float]
    #   - nom_barrage : Nom du barrage étudié [string]
    #   - besoin_puissanve : Besoin en puissance demandé pour le barrage étudié en MW [float]
    #   - info_puissance : Dataframe contenant une simulation de la puissance produite pour chaque barrage à réservoir en 
    #                      fonction du débits turbinés et du nombre de turbines actives. Les colonnes du dataframe sont les suivantes :
    #       - Nom : Nom du barrage [string]. Doit être la même nomenclature que pour info_barrage
    #       - Actives turbines : Nombre de turbines activées dans le barrage [int]
    #       - FLow (m3/s) : Débits turbinés pour toute les turbines actives en m3/s [float]
    #       - Power (MW) : Puissance générés par les turbines actives en MW [float]
    #   - pourcentage_reservoir : Pourcentage de remplissage actuel du réservoir associé au barrage [float] 
    #   - debit_entrant : débit entrant dans le réservoir (calculé à l'aide de xhydro)
    # Variable en sortie : 
    #   - pourcentage_réservoir : Pourcentage de remplissage du réservoir après une heure de production [float]
    #   - nbr_turb_maintenance : Nombre de turbines en maintenance pour le barrage [int] 

    if Type_barrage == "Fil de l'eau":
        print("Erreur : Le barrage entré n'est pas un barrage à réservoir")
    else:
        p = []
        d = []
        nb_turbines_a = []
        Volume_reel = Volume_remplie*pourcentage_reservoir + debit_entrant*3600
        
        for i in range(1, nb_turbines+1-nbr_turb_maintenance):
        # Filter for Dam A and 1 active turbine
            df_dam_a = info_puissance[(info_puissance["Nom"] == nom_barrage) & (info_puissance["Active Turbines"] == i)]
        # Loop through each row and access values
            for index, row in df_dam_a.iterrows():
                debit = row["Flow (m3/s)"]
                puissance = row["Power (MW)"]
                if abs(puissance/(besoin_puissance+0.01) - 1) < 0.05 and puissance>besoin_puissance: # Erreur de 0.01 fonctionne mais pas avec 0.001 pour 100 variables par nombre de turbines actives dans le csv
                    # Le +0.01 est la pour empecher la division par 0 au cas ou la demande est nulle
                    p.append(puissance)
                    d.append(debit)
                    nb_turbines_a.append(i)
                    variable_debits = 10^6
                    for k in range(0,len(p)):
                        if abs(d[k]/nb_turbines_a[k]-Debit_nom)<abs(variable_debits/nb_turbines_a[k]-Debit_nom):
                            variable_debits = d[k]
                            nb_turb_actif = nb_turbines_a[k]
                elif i == 1 and besoin_puissance < df_dam_a["Power (MW)"].iloc[0]:
                    variable_debits = Debit_nom
                    nb_turb_actif = 1
        if Volume_reel + variable_debits*nb_turb_actif*3600 > Volume_remplie:
            pourcentage_reservoir = 1
            Volume_evacue = Volume_reel + variable_debits*nb_turb_actif*3600 - Volume_remplie
        else:
            pourcentage_reservoir = (Volume_reel-(variable_debits*nb_turb_actif*3600))/Volume_remplie

    return pourcentage_reservoir, Volume_evacue # Possible d'ajouter une fonctionnalité permettant de calculer l'énergie perdue après l'utilisation d'un évacuateur de crue pour l'analyse de résultat

def get_run_of_river_dam_power(Type_barrage, nom_barrage,type_turb, nb_turbines, head, Debits_nom, flow, nb_turbine_maintenance):

    if Type_barrage == "Reservoir":
        print("Erreur : Le barrage entré n'est pas un barrage au fil de l'eau")
    else:
        Units = "IS"
        hp_type = 'Diversion'
        flow[nom_barrage] /= nb_turbines

        hp = calculate_hp_potential(flow = flow, flow_column = flow[nom_barrage], design_flow = Debits_nom, head = head, units = Units, 
                hydropower_type= hp_type, turbine_type = type_turb, annual_caclulation=True, annual_maintenance_flag = False
            )
        
        hp.dataframe_output["power_MW"] = (hp.dataframe_output["power_kW"] * (nb_turbines - nb_turbine_maintenance)) / 1000
        
        return hp.dataframe_output["power_MW"]
    
def energy_loss(Volume_evacue, Debits_nom, type_turb, nb_turbines, head, nb_turbine_maintenance):

    # Fonction permettant de calculer la perte d'énergie causé par l'activation d'un évacuateur de crue en MWh
    # Variable en entrée :
    #   - info_barrage : Dataframe contenant les informations des barrages extraite du csv Info_Barrages.csv. Les colonnes du dataframe utilisées dans la fonction sont les suivantes
    #       - Nom : Nom du barrage [string]
    #       - Type : Type du barrage ["Fil de l'eau" vs "Reservoir" (string)]
    #       - Debits_nom : Debit d'équipement des turbines en m^3/s [float]
    #       - Nb_turbines : Nombre de turbines installée dans le barrage [float]
    #       - Type_turbine : Type de turbine installée dans les barrages [string]
    #   - nom_barrage : Nom du barrage étudié [string]
    #   - Volume_evacue : Volume d'eau évacué sur une heure par l'évacuateur de crue en m^3/h  [float]
    #   - nb_turbine_maintenance : Nombre de turbine en maintenance dans le barrage [int]
    # Variable en sortie : 
    #   - energy_loss : Énergie perdue par l'utilisation de l'évacuateur de crue

    Units = "IS"
    hp_type = 'Diversion'
    Debit = Volume_evacue/(3600*nb_turbines) #Conversion du débit évacué de m^3/h en m^3/s pour le calcul de puissance

    hp = calculate_hp_potential(flow = Debit, design_flow = Debits_nom, head = head, units = Units, 
                hydropower_type= hp_type, turbine_type = type_turb, annual_maintenance_flag = False
    )

    energy_loss = hp.power[-1]*(nb_turbines-nb_turbine_maintenance) / 1000

    return energy_loss
