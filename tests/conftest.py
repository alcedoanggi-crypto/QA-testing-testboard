"""Fixtures compartidas por las pruebas.

pytest carga este archivo automáticamente. Cada prueba recibe una aplicación NUEVA con su
propia base SQLite temporal, así las pruebas no dependen unas de otras ni tocan instance/testboard.db.
"""
import pytest

from app import create_app, db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "SEED_DEMO": False,          # base vacía: cada prueba crea lo que necesita
        "SECRET_KEY": "test",
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()          # libera el archivo .db (necesario en Windows)


@pytest.fixture
def client(app):
    """El cliente de pruebas de Flask: hace peticiones HTTP sin levantar un servidor."""
    return app.test_client()


@pytest.fixture
def project(client):
    """Un proyecto con una sección y un caso, creado a través de la API (como lo haría un usuario)."""
    p = client.post("/api/projects", json={"name": "Demo"}).get_json()
    s = client.post(f"/api/projects/{p['id']}/sections", json={"name": "Login"}).get_json()
    c = client.post(f"/api/projects/{p['id']}/cases", json={
        "title": "Ingresar con datos válidos", "section_id": s["id"], "priority": "High",
        "steps": [{"action": "Abrir /login", "expected": "Se ve el formulario"}],
    }).get_json()
    return {"project": p, "section": s, "case": c}
