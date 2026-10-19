"""Pruebas de QA TestBoard con el cliente de pruebas de Flask (app.test_client()).

Organización:
  1. Unitarias: funciones puras de app/services.py (no necesitan HTTP).
  2. API JSON: CRUD de cada recurso + validaciones (400) + inexistentes (404).
  3. Flujo completo: crear ejecución → registrar resultados → estadísticas → cerrar.
  4. Pantallas HTML: que cada página responda 200 y los formularios funcionen.

Ejecutar:  pytest            (o con cobertura:  pytest --cov=app --cov-report=term-missing)
"""
import pytest

from app import db
from app.models import TestResult
from app.seed import seed_if_empty
from app.services import ValidationError, parse_steps, steps_to_text


# ============================================================================= 1. unitarias
class TestParseSteps:
    def test_texto_un_paso_por_linea(self):
        steps = parse_steps("Abrir login | Se ve el formulario\n\nPulsar Ingresar")
        assert steps == [{"action": "Abrir login", "expected": "Se ve el formulario"},
                         {"action": "Pulsar Ingresar", "expected": ""}]

    def test_lista_desde_la_api(self):
        assert parse_steps([{"action": " A ", "expected": " B "}]) == [{"action": "A", "expected": "B"}]

    def test_ignora_pasos_vacios(self):
        assert parse_steps([{"action": "", "expected": ""}, {"action": "X"}]) == [{"action": "X", "expected": ""}]

    def test_resultado_sin_accion_es_error(self):
        with pytest.raises(ValidationError):
            parse_steps(" | solo resultado")

    @pytest.mark.parametrize("valor", [123, {"action": "x"}, ["texto suelto"]])
    def test_formato_invalido(self, valor):
        with pytest.raises(ValidationError):
            parse_steps(valor)

    def test_ida_y_vuelta_con_texto(self):
        texto = "Abrir | Ver\nPulsar"
        assert steps_to_text(parse_steps(texto)) == texto


# ============================================================================= 2. API JSON
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}


class TestProjectsApi:
    def test_crud_completo(self, client):
        r = client.post("/api/projects", json={"name": "Web", "description": "Sitio"})
        assert r.status_code == 201
        pid = r.get_json()["id"]

        assert client.get(f"/api/projects/{pid}").get_json()["name"] == "Web"
        assert [p["name"] for p in client.get("/api/projects").get_json()] == ["Web"]

        r = client.put(f"/api/projects/{pid}", json={"name": "Web 2"})
        assert r.get_json()["name"] == "Web 2"
        assert r.get_json()["description"] == "Sitio"          # PUT parcial: conserva lo no enviado

        assert client.delete(f"/api/projects/{pid}").get_json() == {"deleted": pid}
        assert client.get(f"/api/projects/{pid}").status_code == 404

    def test_nombre_obligatorio(self, client):
        r = client.post("/api/projects", json={"name": "   "})
        assert r.status_code == 400
        assert "obligatorio" in r.get_json()["error"]

    def test_cuerpo_no_json(self, client):
        assert client.post("/api/projects", data="hola").status_code == 400

    def test_nombre_demasiado_largo_no_modifica(self, client, project):
        pid = project["project"]["id"]
        r = client.put(f"/api/projects/{pid}", json={"name": "Nuevo", "description": "x" * 3000})
        assert r.status_code == 400
        assert client.get(f"/api/projects/{pid}").get_json()["name"] == "Demo"

    def test_borrar_proyecto_borra_en_cascada(self, client, project):
        pid = project["project"]["id"]
        client.delete(f"/api/projects/{pid}")
        assert client.get(f"/api/cases/{project['case']['id']}").status_code == 404


class TestSectionsApi:
    def test_arbol_con_subsecciones(self, client, project):
        pid, root = project["project"]["id"], project["section"]["id"]
        r = client.post(f"/api/projects/{pid}/sections", json={"name": "Errores", "parent_id": root})
        assert r.status_code == 201
        assert r.get_json()["path"] == "Login › Errores"

        tree = client.get(f"/api/projects/{pid}/sections").get_json()
        assert [(s["name"], s["depth"]) for s in tree] == [("Login", 0), ("Errores", 1)]
        assert tree[0]["total_cases"] == 1

    def test_no_puede_moverse_dentro_de_si_misma(self, client, project):
        pid, root = project["project"]["id"], project["section"]["id"]
        child = client.post(f"/api/projects/{pid}/sections", json={"name": "Hija", "parent_id": root}).get_json()
        r = client.put(f"/api/sections/{root}", json={"parent_id": child["id"]})
        assert r.status_code == 400

    def test_padre_no_numerico(self, client, project):
        r = client.post(f"/api/projects/{project['project']['id']}/sections", json={"name": "X", "parent_id": "abc"})
        assert r.status_code == 400

    def test_renombrar_y_eliminar(self, client, project):
        sid = project["section"]["id"]
        assert client.put(f"/api/sections/{sid}", json={"name": "Acceso"}).get_json()["name"] == "Acceso"
        r = client.delete(f"/api/sections/{sid}")
        assert r.get_json() == {"deleted": sid, "cases_deleted": 1}


class TestCasesApi:
    def test_crear_y_leer(self, client, project):
        case = project["case"]
        assert case["code"] == f"C{case['id']}"
        assert case["section"] == "Login"
        assert case["steps"][0]["action"] == "Abrir /login"
        assert case["last_status"] is None

    def test_actualizar(self, client, project):
        cid = project["case"]["id"]
        r = client.put(f"/api/cases/{cid}", json={"priority": "Critical", "steps": "Paso 1 | OK"})
        body = r.get_json()
        assert r.status_code == 200
        assert body["priority"] == "Critical" and body["title"] == "Ingresar con datos válidos"
        assert body["steps"] == [{"action": "Paso 1", "expected": "OK"}]

    @pytest.mark.parametrize("cambio", [{"priority": "Urgente"}, {"type": "Otro"}, {"title": ""}, {"section_id": 999}])
    def test_validaciones(self, client, project, cambio):
        status = client.put(f"/api/cases/{project['case']['id']}", json=cambio).status_code
        assert status in (400, 404)

    def test_seccion_de_otro_proyecto(self, client, project):
        otro = client.post("/api/projects", json={"name": "Otro"}).get_json()
        r = client.post(f"/api/projects/{otro['id']}/cases", json={"title": "X", "section_id": project["section"]["id"]})
        assert r.status_code == 400

    def test_filtros(self, client, project):
        pid, sid = project["project"]["id"], project["section"]["id"]
        client.post(f"/api/projects/{pid}/cases", json={"title": "Recuperar clave", "section_id": sid,
                                                        "priority": "Low", "refs": "JIRA-7"})
        url = f"/api/projects/{pid}/cases"
        assert len(client.get(url).get_json()) == 2
        assert [c["title"] for c in client.get(url + "?priority=Low").get_json()] == ["Recuperar clave"]
        assert len(client.get(url + "?q=jira-7").get_json()) == 1                     # busca en referencias
        assert len(client.get(url + f"?q=C{project['case']['id']}").get_json()) == 1  # busca por ID
        assert len(client.get(url + f"?section_id={sid}").get_json()) == 2
        assert client.get(url + "?section_id=abc").status_code == 400

    def test_eliminar(self, client, project):
        cid = project["case"]["id"]
        assert client.delete(f"/api/cases/{cid}").status_code == 200
        assert client.get(f"/api/cases/{cid}").status_code == 404


# ============================================================================= 3. flujo de ejecución
@pytest.fixture
def run(client, project):
    pid = project["project"]["id"]
    sid = project["section"]["id"]
    for title in ("Caso B", "Caso C", "Caso D"):
        client.post(f"/api/projects/{pid}/cases", json={"title": title, "section_id": sid})
    r = client.post(f"/api/projects/{pid}/runs", json={"name": "Regresión"})
    assert r.status_code == 201
    return r.get_json()


class TestRunsFlow:
    def test_nueva_ejecucion_todo_untested(self, run):
        assert run["code"] == f"R{run['id']}"
        assert run["stats"]["total"] == 4 and run["stats"]["untested"] == 4
        assert run["stats"]["progress"] == 0.0

    def test_elegir_casos_especificos(self, client, project):
        pid, cid = project["project"]["id"], project["case"]["id"]
        r = client.post(f"/api/projects/{pid}/runs", json={"name": "Smoke", "include_all": False, "case_ids": [cid]})
        assert r.get_json()["stats"]["total"] == 1

    @pytest.mark.parametrize("datos", [{"name": "X", "include_all": False, "case_ids": []},
                                       {"name": "X", "include_all": False, "case_ids": [999]},
                                       {"name": "X", "include_all": False, "case_ids": ["a"]},
                                       {"name": ""}])
    def test_ejecucion_invalida(self, client, project, datos):
        assert client.post(f"/api/projects/{project['project']['id']}/runs", json=datos).status_code == 400

    def test_registrar_resultados_y_estadisticas(self, client, run):
        ids = [r["id"] for r in run["results"]]
        client.put(f"/api/results/{ids[0]}", json={"status": "passed"})
        client.put(f"/api/results/{ids[1]}", json={"status": "passed"})
        client.put(f"/api/results/{ids[2]}", json={"status": "failed", "comment": "Error 500", "executed_by": "Ana"})

        stats = client.get(f"/api/runs/{run['id']}").get_json()["stats"]
        assert (stats["passed"], stats["failed"], stats["blocked"], stats["untested"]) == (2, 1, 0, 1)
        assert stats["progress"] == 75.0           # 3 de 4 ejecutados
        assert stats["pass_rate"] == 50.0          # 2 de 4 pasaron

        result = client.get(f"/api/runs/{run['id']}").get_json()["results"][2]
        assert result["executed_by"] == "Ana" and result["executed_at"] is not None

    @pytest.mark.parametrize("status", ["failed", "blocked"])
    def test_comentario_obligatorio(self, client, run, status):
        r = client.put(f"/api/results/{run['results'][0]['id']}", json={"status": status})
        assert r.status_code == 400

    def test_estado_invalido(self, client, run):
        assert client.put(f"/api/results/{run['results'][0]['id']}", json={"status": "ok"}).status_code == 400

    def test_ultimo_estado_del_caso(self, client, run, project):
        result = next(r for r in run["results"] if r["case_id"] == project["case"]["id"])
        client.put(f"/api/results/{result['id']}", json={"status": "passed"})
        assert client.get(f"/api/cases/{project['case']['id']}").get_json()["last_status"] == "passed"

    def test_ejecucion_cerrada_no_acepta_resultados(self, client, run):
        assert client.post(f"/api/runs/{run['id']}/close").get_json()["is_completed"] is True
        r = client.put(f"/api/results/{run['results'][0]['id']}", json={"status": "passed"})
        assert r.status_code == 400

    def test_borrar_caso_conserva_historial(self, client, app, run, project):
        """El resultado guarda una "foto" del caso: si el caso se borra, la ejecución no pierde datos."""
        client.delete(f"/api/cases/{project['case']['id']}")
        titles = [r["case_title"] for r in client.get(f"/api/runs/{run['id']}").get_json()["results"]]
        assert "Ingresar con datos válidos" in titles
        with app.app_context():
            assert db.session.scalar(db.select(TestResult).where(TestResult.case_title == "Ingresar con datos válidos")).case_id is None

    def test_eliminar_ejecucion(self, client, run):
        assert client.delete(f"/api/runs/{run['id']}").status_code == 200
        assert client.get(f"/api/runs/{run['id']}").status_code == 404

    def test_estadisticas_globales(self, client, run):
        stats = client.get("/api/stats").get_json()
        assert stats["projects"] == 1 and stats["cases"] == 4 and stats["active_runs"] == 1


def test_recurso_inexistente_devuelve_json(client):
    r = client.get("/api/cases/12345")
    assert r.status_code == 404 and "error" in r.get_json()


# ============================================================================= 4. pantallas HTML
@pytest.fixture
def demo(app):
    """Carga los datos de ejemplo (los mismos que ve el usuario al abrir la app por primera vez)."""
    with app.app_context():
        seed_if_empty()


@pytest.mark.parametrize("url", ["/", "/projects", "/projects/1/edit", "/cases", "/cases?section=1",
                                 "/cases?q=login&priority=High", "/cases/new", "/cases/1", "/cases/1/edit",
                                 "/runs", "/runs/new", "/runs/1", "/runs/1?status=failed"])
def test_paginas_responden(client, demo, url):
    r = client.get(url)
    assert r.status_code == 200
    assert "QA TestBoard" in r.get_data(as_text=True)


def test_dashboard_muestra_menu_y_estados(client, demo):
    html = client.get("/").get_data(as_text=True)
    for texto in ("Dashboard", "Proyectos", "Casos de Prueba", "Ejecuciones (Test Runs)", "Passed", "Failed"):
        assert texto in html


def test_pagina_inexistente(client):
    r = client.get("/no-existe")
    assert r.status_code == 404 and "no existe" in r.get_data(as_text=True).lower()


def test_sin_proyectos_redirige(client):
    assert client.get("/cases").status_code == 302


def test_formularios_crear_proyecto_seccion_y_caso(client):
    r = client.post("/projects", data={"name": "Tienda"}, follow_redirects=True)
    assert "Tienda" in r.get_data(as_text=True)

    r = client.post("/sections", data={"name": "Carrito"}, follow_redirects=True)
    assert "Carrito" in r.get_data(as_text=True)

    r = client.post("/cases/new", data={"title": "Agregar producto", "section_id": "1", "priority": "High",
                                        "type": "Smoke", "steps": "Abrir producto | Se ve el botón"},
                    follow_redirects=True)
    assert "Agregar producto" in r.get_data(as_text=True)


def test_formulario_invalido_muestra_mensaje(client, demo):
    r = client.post("/projects", data={"name": ""}, headers={"Referer": "/projects"}, follow_redirects=True)
    assert "obligatorio" in r.get_data(as_text=True)


def test_formulario_registrar_resultado(client, demo):
    r = client.post("/results/7", data={"status": "failed", "comment": ""}, follow_redirects=True)
    assert "obligatorio" in r.get_data(as_text=True)

    r = client.post("/results/7", data={"status": "passed", "executed_by": "QA Bot"})
    assert r.status_code == 302 and r.location.endswith("#t7")


def test_formulario_nueva_ejecucion_y_cerrar(client, demo):
    r = client.post("/runs/new", data={"name": "Smoke", "include_all": "0", "case_ids": ["1", "2"]})
    assert r.status_code == 302
    run_url = r.location
    assert "Smoke" in client.get(run_url).get_data(as_text=True)

    run_id = int(run_url.rstrip("/").split("/")[-1])
    client.post(f"/runs/{run_id}/close")
    assert "Cerrada" in client.get(run_url).get_data(as_text=True)


def test_formularios_editar_y_eliminar(client, demo):
    assert client.post("/projects/1/edit", data={"name": "Portal v2"}).status_code == 302
    assert "Portal v2" in client.get("/projects").get_data(as_text=True)

    r = client.post("/cases/1/edit", data={"title": "Login editado", "section_id": "2", "priority": "Low"})
    assert r.status_code == 302
    assert "Login editado" in client.get("/cases/1").get_data(as_text=True)

    assert client.post("/cases/1/delete").status_code == 302
    assert client.get("/cases/1").status_code == 404

    assert client.post("/sections/4/delete").status_code == 302
    assert client.post("/runs/1/delete").status_code == 302
    assert client.get("/runs/1").status_code == 404

    assert client.post("/projects/2/delete").status_code == 302
    assert 'data-project="2"' not in client.get("/projects").get_data(as_text=True)
