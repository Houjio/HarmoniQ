"Liste de modèles de données de la base de données"

from sqlalchemy import Column, Integer, String, Float, Boolean, Table, Enum
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator
from sqlalchemy.sql.schema import ForeignKey

import pandera as pa
from pydantic import BaseModel, TypeAdapter, Field, field_validator, validator
from typing import List, Optional
from datetime import datetime, timedelta
import isodate
from enum import Enum as PyEnum

SQLBase = declarative_base()


class PositionBase(BaseModel):
    """Pydantic modèle de base pour les positions"""

    latitude: float
    longitude: float

    def __repr__(self):
        return f"({self.latitude}, {self.longitude})"


class Optimisme(PyEnum):
    pessimiste = 1
    moyen = 2
    optimiste = 3

class Weather(PyEnum):
    warm = 1
    typical = 2
    cold = 3

class Consomation(PyEnum):
    PV = 1 # Typique
    UB = 2 # Conservateur

class DateTimeString(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            return value.isoformat()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return datetime.fromisoformat(value)
        return value


class TimeDeltaString(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            return isodate.duration_isoformat(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return isodate.parse_duration(value)
        return value


class Scenario(SQLBase):
    __tablename__ = "scenario"

    id = Column(Integer, primary_key=True)
    nom = Column(String)
    description = Column(String)
    date_de_debut = Column(DateTimeString)
    date_de_fin = Column(DateTimeString)
    pas_de_temps = Column(TimeDeltaString)
    weather = Column(Enum(Weather))
    consomation = Column(Enum(Consomation))
    optimisme_social = Column(Enum(Optimisme))
    optimisme_ecologique = Column(Enum(Optimisme))


class ScenarioBase(BaseModel):
    nom: str
    description: Optional[str] = None
    date_de_debut: datetime = Field(
        ..., description="Date de début de la simulation (YYYY-MM-DD)"
    )
    date_de_fin: datetime = Field(
        ..., description="Date de fin de la simulation (YYYY-MM-DD)"
    )
    pas_de_temps: timedelta = Field(
        ..., description="Pas de temps de la simulation (HH:MM:SS)"
    )
    weather: Weather = Weather.typical
    consomation: Consomation = Consomation.PV
    optimisme_social: Optimisme = Optimisme.moyen
    optimisme_ecologique: Optimisme = Optimisme.moyen

    @validator("date_de_debut", "date_de_fin", pre=True)
    def parse_datetime(cls, value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                raise ValueError(f"Invalid datetime format: {value}")
        return value

    @validator("pas_de_temps", pre=True)
    def parse_timedelta(cls, value):
        if isinstance(value, str):
            try:
                return isodate.parse_duration(value)
            except ValueError:
                raise ValueError(f"Invalid timedelta format: {value}")
        return value


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioResponse(ScenarioBase):
    id: int

    class Config:
        from_attributes = True


class ListeInfrastructures(SQLBase):
    __tablename__ = "liste_infrastructures"

    id = Column(Integer, primary_key=True)
    nom = Column(String)
    parc_eoliens = Column(String, nullable=True)
    parc_solaires = Column(String, nullable=True)
    central_hydroelectriques = Column(String, nullable=True)
    central_thermique = Column(String, nullable=True)

    @property
    def parc_eolien_list(self):
        return self.parc_eolien.split(",") if self.parc_eolien else []

    @property
    def parc_solaire_list(self):
        return self.parc_solaire.split(",") if self.parc_solaire else []

    @property
    def central_hydroelectriques_list(self):
        return (
            self.central_hydroelectriques.split(",")
            if self.central_hydroelectriques
            else []
        )

    @property
    def central_thermique_list(self):
        return self.central_thermique.split(",") if self.central_thermique else []


class ListeInfrastructuresBase(BaseModel):
    nom: str
    parc_eoliens: Optional[str] = None
    parc_solaires: Optional[str] = None
    central_hydroelectriques: Optional[str] = None
    central_thermique: Optional[str] = None


class ListeInfrastructuresCreate(ListeInfrastructuresBase):
    pass


class ListeInfrastructuresResponse(ListeInfrastructuresBase):
    id: int

    class Config:
        from_attributes = True


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
    longitude: float = Field(
        ..., description="Longitude moyenne des éoliennes (degrés)"
    )
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


class Solaire(SQLBase):
    __tablename__ = "solaire"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    angle_panneau = Column(Integer)
    orientation_panneau = Column(Integer)
    nombre_panneau = Column(Integer)
    puissance_nominal = Column(Float)
    annee_commission = Column(Integer, nullable=True)
    panneau_type = Column(String, nullable=True)
    materiau_panneau = Column(String, nullable=True)


class SolaireBase(BaseModel):
    nom: str
    latitude: float
    longitude: float
    angle_panneau: int
    orientation_panneau: int
    puissance_nominal: float
    nombre_panneau: int
    annee_commission: Optional[int] = None
    panneau_type: Optional[str] = None
    materiau_panneau: Optional[str] = None

    class Config:
        from_attributes = True


class SolaireCreate(SolaireBase):
    pass


class HydroBase(BaseModel):
    barrage_nom: str
    longitude: float
    latitude: float
    type_barrage: str
    puissance_nominal: float
    hauteur_chute: float
    nb_turbines: int
    debits_nominal: float
    modele_turbine: str
    volume_reservoir: int
    nb_turbines_maintenance: int
    annee_commission: Optional[int] = None
    materiau_conduite: Optional[str] = None

    class Config:
        from_attributes = True


class HydroCreate(HydroBase):
    pass


class HydroResponse(HydroBase):
    id: int

    class Config:
        from_attributes = True


class Hydro(SQLBase):
    __tablename__ = "hydro"

    id = Column(Integer, primary_key=True, index=True)
    barrage_nom = Column(String)
    longitude = Column(Float)
    latitude = Column(Float)
    type_barrage = Column(String)
    puissance_nominal = Column(Float)
    hauteur_chute = Column(Float)
    nb_turbines = Column(Integer)
    debits_nominal = Column(Float)
    modele_turbine = Column(String)
    volume_reservoir = Column(Integer)
    nb_turbines_maintenance = Column(Integer)
    annee_commission = Column(Integer, nullable=True)
    materiau_conduite = Column(String, nullable=True)


class SolaireResponse(SolaireBase):
    id: int

    class Config:
        from_attributes = True


class ThermiqueBase(BaseModel):
    latitude: float
    longitude: float
    nom: str
    puissance_nominal: float
    type_intrant: str
    semaine_maintenance: int
    annee_commission: Optional[int] = None
    type_generateur: Optional[str] = None

    class Config:
        from_attributes = True


class ThermiqueCreate(ThermiqueBase):
    pass


class ThermiqueResponse(ThermiqueBase):
    id: int

    class Config:
        from_attributes = True


class Thermique(SQLBase):
    __tablename__ = "thermique"

    id = Column(Integer, primary_key=True, index=True)

    nom = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    puissance_nominal = Column(Float)
    type_intrant = Column(String)
    semaine_maintenance = Column(Integer)
    annee_commission = Column(Integer, nullable=True)
    type_generateur = Column(Integer, nullable=True)


class NucleaireBase(BaseModel):
    latitude: float
    longitude: float
    centrale_nucleaire_nom: str
    puissance_nominal: float
    type_intrant: str
    semaine_maintenance: int
    annee_commission: Optional[int] = None
    type_generateur: Optional[str] = None

    class Config:
        from_attributes = True


class NucleaireCreate(NucleaireBase):
    pass


class NucleaireResponse(NucleaireBase):
    id: int

    class Config:
        from_attributes = True


class Nucleaire(SQLBase):
    __tablename__ = "nucleaire"

    id = Column(Integer, primary_key=True, index=True)

    centrale_nucleaire_nom = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    puissance_nominal = Column(Float)
    type_intrant = Column(String)
    semaine_maintenance = Column(Integer)
    annee_commission = Column(Integer, nullable=True)
    type_generateur = Column(Integer, nullable=True)


class BusControlType(str, PyEnum):
    """Enumération des types de contrôle de bus"""

    PV = "PV"
    PQ = "PQ"
    slack = "slack"


class BusType(str, PyEnum):
    """Enumération des types de bus"""

    prod = "prod"
    conso = "conso"
    line = "ligne"


class Bus(SQLBase):
    __tablename__ = "bus"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    v_nom = Column(Integer)
    type = Column(Enum(BusType))
    x = Column(Float)
    y = Column(Float)
    control = Column(Enum(BusControlType))

    lines_from = relationship(
        "Line", back_populates="bus_from", foreign_keys="Line.bus0"
    )
    lines_to = relationship("Line", back_populates="bus_to", foreign_keys="Line.bus1")


class BusBase(BaseModel):
    name: str
    v_nom: int
    type: BusType
    x: float
    y: float
    control: BusControlType

    class Config:
        from_attributes = True


class BusCreate(BusBase):
    pass


class BusResponse(BusBase):
    id: int

    class Config:
        from_attributes = True


class LineType(SQLBase):
    __tablename__ = "line_type"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    f_nom = Column(Integer)
    r_per_length = Column(Float)
    x_per_length = Column(Float)

    lines = relationship("Line", back_populates="line_type")


class LineTypeBase(BaseModel):
    name: str
    f_nom: int
    r_per_length: float
    x_per_length: float

    class Config:
        from_attributes = True


class LineTypeCreate(LineTypeBase):
    pass


class LineTypeResponse(LineTypeBase):
    id: int

    class Config:
        from_attributes = True


class Line(SQLBase):
    __tablename__ = "line"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    bus0 = Column(Integer, ForeignKey("bus.name"))
    bus1 = Column(Integer, ForeignKey("bus.name"))
    type = Column(Integer, ForeignKey("line_type.name"))
    capital_cost = Column(Float)
    length = Column(Float)
    s_nom = Column(Float)

    bus_from = relationship("Bus", back_populates="lines_from", foreign_keys=[bus0])
    bus_to = relationship("Bus", back_populates="lines_to", foreign_keys=[bus1])
    line_type = relationship("LineType", back_populates="lines")


class LineBase(BaseModel):
    name: str
    bus0: str
    bus1: str
    type: str
    capital_cost: float
    length: float
    s_nom: float

    class Config:
        from_attributes = True


class LineCreate(LineBase):
    pass


class LineResponse(LineBase):
    id: int

    class Config:
        from_attributes = True


weather_schema = pa.DataFrameSchema(
    columns={
        "longitude": pa.Column(
            pa.Float, checks=pa.Check.greater_than(-180), nullable=False
        ),
        "latitude": pa.Column(
            pa.Float, checks=pa.Check.greater_than(-90), nullable=False
        ),
        "temperature_C": pa.Column(pa.Float, nullable=False),
        "min_tempature_C": pa.Column(
            pa.Float, nullable=True
        ),  # Pour les données journalières
        "max_temperature_C": pa.Column(
            pa.Float, nullable=True
        ),  # Pour les données journalières
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
