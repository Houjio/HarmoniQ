"Liste de modèles de données de la base de données"

from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql.schema import ForeignKey

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


class EolienneBase(BaseModel):
    latitude: float
    longitude: float
    diametre_rotor: float
    hauteur_moyenne: float
    puissance_nominal: float
    modele_turbine: str
    project_name: str
    project_id: int
    annee_commission: Optional[int] = None
    surface_balayee: Optional[float] = None
    vitesse_vent_de_demarrage: Optional[float] = None
    vitesse_vent_de_coupure: Optional[float] = None
    materiau_pale: Optional[str] = None
    type_generateur: Optional[int] = None


class EolienneCreate(EolienneBase):
    pass


class EolienneResponse(EolienneBase):
    id: int

    class Config:
        from_attributes = True


class Eolienne(SQLBase):
    __tablename__ = "eoliennes"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    diametre_rotor = Column(Float)
    hauteur_moyenne = Column(Float)
    puissance_nominal = Column(Float)
    modele_turbine = Column(String)
    project_name = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    annee_commission = Column(Integer, nullable=True)
    surface_balayee = Column(Float, nullable=True)
    vitesse_vent_de_demarrage = Column(Float, nullable=True)
    vitesse_vent_de_coupure = Column(Float, nullable=True)
    materiau_pale = Column(String, nullable=True)
    type_generateur = Column(Integer, nullable=True)


class HydroelectriqueBase(InfrastructureBase):
    fils_de_l_eau: bool
    pass


class SolaireBase(InfrastructureBase):
    pass


class ThermiqueBase(InfrastructureBase):
    pass


class TransmissionBase(InfrastructureBase):
    pass
