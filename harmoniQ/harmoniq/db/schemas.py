"Liste de modèles de données de la base de données"

from sqlalchemy import Column, Integer, String, Float, Boolean, Table
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey

import pandera as pa
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum

SQLBase = declarative_base()


class MRC(SQLBase):
    __tablename__ = "mrc"

    id = Column(Integer, primary_key=True)  # CDUID
    nom = Column(String)
    longitude_centre = Column(Float)
    latitude_centre = Column(Float)

    instances_population = relationship("InstancePopulation", back_populates="mrc")


class MRCBase(BaseModel):
    id: int
    nom: str
    longitude_centre: float
    latitude_centre: float


class MRCCreate(MRCBase):
    pass


class MRCResponse(MRCBase):
    class Config:
        from_attributes = True


class InstancePopulation(SQLBase):
    __tablename__ = "instance_population"

    id = Column(Integer, primary_key=True)
    annee = Column(Integer)
    population = Column(Integer)
    mrc_id = Column(Integer, ForeignKey("mrc.id"))

    mrc = relationship("MRC", back_populates="instances_population")


class InstancePopulationBase(BaseModel):
    annee: int
    population: int
    mrc_id: int


class InstancePopulationCreate(InstancePopulationBase):
    pass


class InstancePopulationResponse(InstancePopulationBase):
    id: int

    class Config:
        from_attributes = True


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
    eolienne_nom: str
    diametre_rotor: float
    hauteur_moyenne: float
    puissance_nominal: float
    turbine_id: int
    modele_turbine: str
    project_name: str
    eolienne_parc_id: int
    annee_commission: Optional[int] = None
    surface_balayee: Optional[float] = None
    vitesse_vent_de_demarrage: Optional[float] = None
    vitesse_vent_de_coupure: Optional[float] = None
    materiau_pale: Optional[str] = None
    type_generateur: Optional[int] = None

    class Config:
        from_attributes = True


class EolienneCreate(EolienneBase):
    pass


class EolienneResponse(EolienneBase):
    id: int

    class Config:
        from_attributes = True


class Eolienne(SQLBase):
    __tablename__ = "eoliennes"

    id = Column(Integer, primary_key=True, index=True)
    eolienne_nom = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    diametre_rotor = Column(Float)
    hauteur_moyenne = Column(Float)
    turbine_id = Column(Integer)
    puissance_nominal = Column(Float)
    modele_turbine = Column(String)
    project_name = Column(String)
    annee_commission = Column(Integer, nullable=True)
    surface_balayee = Column(Float, nullable=True)
    vitesse_vent_de_demarrage = Column(Float, nullable=True)
    vitesse_vent_de_coupure = Column(Float, nullable=True)
    materiau_pale = Column(String, nullable=True)
    type_generateur = Column(Integer, nullable=True)
    eolienne_parc_id = Column(Integer, ForeignKey("eoliennes_parc.id"), nullable=True)

    eolienne_parc = relationship("EolienneParc", back_populates="eoliennes")


class EolienneParcBase(BaseModel):
    nom: str = Field(..., description="Nom du parc éolien")
    latitude: float = Field(..., description="Latitude moyenne des éoliennes (degrés)")
    longitude: float = Field(..., description="Longitude moyenne des éoliennes (degrés)")
    nombre_eoliennes: int = Field(..., description="Nombre d'éoliennes dans le parc")
    capacite_total: float = Field(..., description="Capacité totale du parc (MW)")


class EolienneParcCreate(EolienneParcBase):
    pass


class EolienneParcResponse(EolienneParcBase):
    id: int

    class Config:
        from_attributes = True


class EolienneParc(SQLBase):
    __tablename__ = "eoliennes_parc"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    nombre_eoliennes = Column(Integer)
    capacite_total = Column(Float)
    eoliennes = relationship("Eolienne", back_populates="eolienne_parc")


class HydroelectriqueBase(InfrastructureBase):
    fils_de_l_eau: bool
    pass


class SolaireBase(InfrastructureBase):
    pass


class ThermiqueBase(InfrastructureBase):
    pass


class TransmissionBase(InfrastructureBase):
    pass

weather_schema = pa.DataFrameSchema(
    columns={
        "longitude": pa.Column(pa.Float, checks=pa.Check.greater_than(-180), nullable=False),
        "latitude": pa.Column(pa.Float, checks=pa.Check.greater_than(-90), nullable=False),
        "temperature_C": pa.Column(pa.Float, nullable=False),
        "min_tempature_C": pa.Column(pa.Float, nullable=True), # Pour les données journalières
        "max_temperature_C": pa.Column(pa.Float, nullable=True), # Pour les données journalières
        "pluie_mm": pa.Column(pa.Float, nullable=True),
        "neige_cm": pa.Column(pa.Float, nullable=True),
        "precipitation_mm": pa.Column(pa.Float, nullable=False),
        "neige_accumulee_cm": pa.Column(pa.Float, nullable=True),
        "direction_vent": pa.Column(pa.Float, nullable=False),
        "vitesse_vent_kmh": pa.Column(pa.Float, nullable=False),
        "humidite": pa.Column(pa.Float, nullable=True),
        "pression": pa.Column(pa.Float, nullable=True),
        "point_de_rosee": pa.Column(pa.Float, nullable=True),
    },
    index=pa.Index(pa.DateTime, name="datetemps"),
    strict=True,
)
