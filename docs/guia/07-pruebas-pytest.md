# 7. Pruebas con pytest

## `test_client`: peticiones HTTP sin servidor

Flask trae un cliente de pruebas que simula el navegador o Postman **sin levantar un servidor**:

```python
client = app.test_client()
r = client.post("/api/projects", json={"name": "Web"})
assert r.status_code == 201
assert r.get_json()["name"] == "Web"
```

Corre en milisegundos y prueba todo el camino real: ruta → servicio → base de datos → respuesta.

## Fixtures (`tests/conftest.py`)

Una *fixture* es una función que prepara algo que las pruebas necesitan. pytest la ejecuta automáticamente cuando
una prueba la pide **por su nombre de parámetro**:

```python
@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "SEED_DEMO": False,
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()          # libera el archivo .db (necesario en Windows)

@pytest.fixture
def client(app):
    return app.test_client()
```

- `tmp_path` es una fixture de pytest que da una carpeta temporal **distinta para cada prueba**. Cada prueba tiene
  su propia base vacía, así que el orden de las pruebas no importa y nunca se toca `instance/testboard.db`.
- Todo lo que va después de `yield` se ejecuta al terminar la prueba (limpieza). En Windows un archivo abierto no se
  puede borrar, y por eso se cierra la conexión con `dispose()`.
- Las fixtures se encadenan: `client` pide `app`, y `project` pide `client`.

```python
@pytest.fixture
def project(client):
    """Un proyecto con una sección y un caso, creado a través de la API (como lo haría un usuario)."""
    p = client.post("/api/projects", json={"name": "Demo"}).get_json()
    s = client.post(f"/api/projects/{p['id']}/sections", json={"name": "Login"}).get_json()
    c = client.post(f"/api/projects/{p['id']}/cases", json={...}).get_json()
    return {"project": p, "section": s, "case": c}
```

Una prueba que necesita datos solo los pide:

```python
def test_crear_y_leer(self, client, project):
    assert project["case"]["code"] == f"C{project['case']['id']}"
```

## Qué se prueba (64 pruebas)

| Grupo | Ejemplos |
|---|---|
| **Unitarias** (`parse_steps`) | texto "a \| b", lista JSON, pasos vacíos ignorados, resultado sin acción = error |
| **API: proyectos** | CRUD completo, nombre obligatorio, cuerpo no JSON, PUT inválido no modifica, borrado en cascada |
| **API: secciones** | árbol con profundidad, no moverse dentro de sí misma, padre no numérico |
| **API: casos** | crear/actualizar, prioridad o tipo inválidos, sección de otro proyecto, filtros, buscar por `C12` |
| **Flujo de ejecución** | todo nace Untested, estadísticas (75 % progreso, 50 % pass rate), comentario obligatorio, ejecución cerrada, historial al borrar el caso |
| **Pantallas** | cada página responde 200, menú y estados presentes, 404, formularios crear/editar/eliminar, mensaje de error visible |

## Probar los casos "malos"

En QA, la mitad del valor está en verificar que **lo incorrecto se rechaza bien**:

```python
@pytest.mark.parametrize("status", ["failed", "blocked"])
def test_comentario_obligatorio(self, client, run, status):
    r = client.put(f"/api/results/{run['results'][0]['id']}", json={"status": status})
    assert r.status_code == 400
```

`@pytest.mark.parametrize` ejecuta la misma prueba con varios valores. Aquí corre dos veces, una con "failed" y otra
con "blocked", y cada una cuenta como una prueba aparte en el reporte.

Escribir estas pruebas sirvió de algo: al probar entradas raras se encontraron tres casos que daban **error 500**
en vez de 400. Eran un `section_id` no numérico, un paso que no era objeto y un `case_ids` con letras. Se corrigieron
con `to_id()` y validaciones explícitas.

## Probar las pantallas

```python
def test_formulario_invalido_muestra_mensaje(client, demo):
    r = client.post("/projects", data={"name": ""}, headers={"Referer": "/projects"}, follow_redirects=True)
    assert "obligatorio" in r.get_data(as_text=True)
```

- `data=` envía un formulario (como el navegador) y `json=` envía JSON (como Postman).
- `follow_redirects=True` sigue la redirección del patrón Post/Redirect/Get, de modo que `r` es la página final con
  el mensaje flash.
- `get_data(as_text=True)` devuelve el HTML como texto para buscar en él.

> **Detalle aprendido:** una prueba fallaba porque comprobaba que "App Móvil" **no** aparecía tras eliminar el
> proyecto, pero el mensaje flash decía "Proyecto «App Móvil Clientes» eliminado". La prueba se corrigió para buscar
> la fila de la tabla (`data-project="2"`). Los atributos `data-*` también sirven para que las pruebas encuentren
> los elementos.

## Ejecutar y medir cobertura

```powershell
.venv\Scripts\python -m pytest                           # todas las pruebas
.venv\Scripts\python -m pytest -k ejecucion -v           # solo las que contienen "ejecucion" en su nombre
.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

**Cobertura** = qué porcentaje de las líneas del código se ejecutó durante las pruebas. Está en **98 %**, y la
columna `Missing` dice qué líneas quedaron sin probar. El reporte HTML (`htmlcov/index.html`) las marca en rojo.

Ojo: 100 % de cobertura no significa "sin errores". Solo dice que cada línea se ejecutó al menos una vez, no que se
probaron todos los valores posibles. La cobertura sirve para encontrar código **sin** pruebas, no para demostrar que
algo es correcto.

`pytest.ini` le dice a pytest dónde buscar:

```ini
[pytest]
testpaths = tests
addopts = -q
```

➡️ Siguiente: [8. VS Code y práctica](08-vscode-y-practica.md)
