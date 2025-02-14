"Liste de modèles de données de la base de données"

from sqlalchemy import Column, Integer, String, Float, Boolean, Table
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
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


# eolienne_parc_association = Table(
#     'eolienne_parc_association',
#     SQLBase.metadata,
#     Column('parc_id', Integer, ForeignKey('eoliennes_parc.id')),
#     Column('eolienne_id', Integer, ForeignKey('eoliennes.id'))
# )

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
        orm_mode = True


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
    nom: str
    latitude: float
    longitude: float
    nombre_eoliennes: int
    capacite_total: float
    

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
