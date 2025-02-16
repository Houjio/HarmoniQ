import pytest
from sqlalchemy.orm import Session
from harmoniq.db.engine import engine, get_db, create_eolienne, create_eolienne_parc, read_eoliennes, read_eolienne, update_eolienne, delete_eolienne, read_eolienne_parcs, read_eolienne_parc, update_eolienne_parc, delete_eolienne_parc
from harmoniq.db.shemas import SQLBase, EolienneCreate, EolienneParcCreate

@pytest.fixture(scope="module")
def db():
    SQLBase.metadata.create_all(bind=engine)
    db = next(get_db())
    yield db
    SQLBase.metadata.drop_all(bind=engine)
    db.close()

def test_create_eolienne_parc(db: Session):
    eolienne_parc = EolienneParcCreate(
        latitude=45.5017,
        longitude=-73.5673,
        nombre_eoliennes=10,
        capacite_total=50.0,
        nom="Parc A"
    )
    result = create_eolienne_parc(db, eolienne_parc)
    assert result.id is not None
    assert result.latitude == 45.5017
    assert result.longitude == -73.5673

def test_create_eolienne(db: Session):
    eolienne = EolienneCreate(
        latitude=45.5017,
        longitude=-73.5673,
        eolienne_nom="Eolienne 1",
        diametre_rotor=100.0,
        hauteur_moyenne=80.0,
        puissance_nominal=2.0,
        turbine_id=1,
        modele_turbine="Model X",
        project_name="Project A",
        eolienne_parc_id=1
    )
    result = create_eolienne(db, eolienne)
    assert result.id is not None
    assert result.eolienne_nom == "Eolienne 1"

def test_read_eoliennes(db: Session):
    result = read_eoliennes(db)
    assert len(result) > 0

def test_read_eolienne(db: Session):
    result = read_eolienne(db, 1)
    assert result is not None
    assert result.id == 1
    def test_update_eolienne(db: Session):
        eolienne = EolienneCreate(
            latitude=45.5017,
            longitude=-73.5673,
            eolienne_nom="Eolienne Updated",
            diametre_rotor=100.0,
            hauteur_moyenne=80.0,
            puissance_nominal=2.0,
            turbine_id=1,
            modele_turbine="Model X",
            project_name="Project A",
            eolienne_parc_id=1
        )
        result = update_eolienne(db, 1, eolienne)
        assert result.eolienne_nom == "Eolienne Updated"

def test_delete_eolienne(db: Session):
    result = delete_eolienne(db, 1)
    assert result["message"] == "Eolienne deleted successfully"

def test_read_eolienne_parcs(db: Session):
    result = read_eolienne_parcs(db)
    assert len(result) > 0

def test_read_eolienne_parc(db: Session):
    result = read_eolienne_parc(db, 1)
    assert result is not None
    assert result.id == 1

def test_update_eolienne_parc(db: Session):
    eolienne_parc = EolienneParcCreate(
        latitude=45.5017,
        longitude=-73.5673,
        nombre_eoliennes=10,
        capacite_total=50.0,
        nom="Parc Updated"
    )
    result = update_eolienne_parc(db, 1, eolienne_parc)
    assert result.nom == "Parc Updated"

def test_delete_eolienne_parc(db: Session):
    result = delete_eolienne_parc(db, 1)
    assert result["message"] == "EolienneParc deleted successfully"
