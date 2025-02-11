"Liste de modèles de données de la base de données"

from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum

SQLBase = declarative_base()


class TypeInfrastructures(str, Enum):
    """Enumération des types d'infrastructures"""

    eolienne = "éolienne"
    solaire = "solaire"
    hydro = "hydro"
    thermique = "thermique"
    transmission = "transmission"
    stockage = "stockage"


class PositionBase(BaseModel):
    """Pydantic modèle de base pour les positions"""

    latitude: float
    longitude: float

    def __repr__(self):
        return f"({self.latitude}, {self.longitude})"


class CasBase(BaseModel):
    nom: str
    description: Optional[str] = None
    date_de_debut: datetime
    date_de_fin: datetime
    pas_de_temps: timedelta


class InfrastructureBase(PositionBase):
    nom: str
    type: TypeInfrastructures
    cout_de_construction: Optional[float] = None
    cout_de_maintenance_annuel: Optional[float] = None
    # TODO: Ajouter plus de champs


class TypeGenerateur(Enum):
    A = 1
    B = 2
    C = 3

class EolienneBase(InfrastructureBase):
    diametre_rotor: float
    hauteur_moyenne: float
    puissance_nominal: float
    modele_turbine : str
    project_name : str
    project_id : int
    annee_commission: Optional[int] = None
    surface_balayee: Optional[float] = None
    vitesse_vent_de_demarrage: Optional[float] = None
    Vitesse_vent_de_coupure: Optional[float] = None
    materiau_pale: Optional[str] = None
    type_generateur : Optional[TypeGenerateur] = None


class HydroelectriqueBase(InfrastructureBase):
    fils_de_l_eau: bool
    pass


class SolaireBase(InfrastructureBase):
    pass


class ThermiqueBase(InfrastructureBase):
    pass


class TransmissionBase(InfrastructureBase):
    pass
