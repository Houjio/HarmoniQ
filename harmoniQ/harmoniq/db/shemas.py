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


class EolienneBase(InfrastructureBase):
    pass


class HydroelectriqueBase(InfrastructureBase):
    fils_de_l_eau: bool
    pass


class SolaireBase(InfrastructureBase):
    pass


class ThermiqueBase(InfrastructureBase):
    pass


class TransmissionBase(InfrastructureBase):
    pass


# Station Météo
class StationMeteoBase(PositionBase):
    """Pydanctic modèle de base pour les stations météo"""

    nom: str
    IATA_ID: str
    WMO_ID: Optional[int] = None
    MSC_ID: str
    elevation_m: float
    fournisseur_de_donnees: Optional[str] = None
    reseau: Optional[str] = None
    automatic: Optional[bool] = None


class StationMeteoCreate(StationMeteoBase):
    """Pydanctic modèle pour créer une station météo"""

    pass


class StationMeteoRead(StationMeteoBase):
    """Pydanctic modèle pour lire une station météo"""

    id: int

    model_config = ConfigDict(from_attributes=True)


class StationMeteo(SQLBase):
    """Modèle SQLAlchemy pour les stations météo"""

    __tablename__ = "stations_meteo"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    IATA_ID = Column(String, index=True)
    WMO_ID = Column(Integer, index=True, nullable=True)
    MSC_ID = Column(String, index=True)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)
    elevation_m = Column(Float, index=True)
    fournisseur_de_donnees = Column(String, index=True, nullable=True)
    reseau = Column(String, index=True, nullable=True)
    automatic = Column(Boolean, index=True, nullable=True)
