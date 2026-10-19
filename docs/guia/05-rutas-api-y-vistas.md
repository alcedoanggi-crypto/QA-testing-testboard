# 5. Rutas: API JSON y pantallas

## Blueprints

Un *Blueprint* es un grupo de rutas que luego se registra en la aplicación. Hay dos:

```python
api = Blueprint("api", __name__, url_prefix="/api")    # app/routes/api.py   → JSON
views = Blueprint("views", __name__)                    # app/routes/views.py → HTML
```

Con `url_prefix="/api"`, una ruta declarada como `/projects` queda en `/api/projects`. El nombre del blueprint
también sirve para construir URLs: `url_for("views.cases")` devuelve `/cases`.

## La API REST (CRUD)

REST usa el **método HTTP** para decir qué hacer y la **URL** para decir sobre qué:

| Acción CRUD | Método | Ejemplo | Respuesta |
|---|---|---|---|
| Create | `POST` | `/api/projects` | 201 + el objeto creado |
| Read | `GET` | `/api/projects/1` | 200 + el objeto |
| Update | `PUT` | `/api/projects/1` | 200 + el objeto actualizado |
| Delete | `DELETE` | `/api/projects/1` | 200 + `{"deleted": 1}` |

Las rutas son **delgadas**: leen, llaman al servicio y responden.

```python
@api.post("/projects")
def create_project():
    return jsonify(save_project(payload()).to_dict()), 201

@api.put("/projects/<int:project_id>")
def update_project(project_id):
    project = get_or_404(Project, project_id)
    return jsonify(save_project({**project.to_dict(), **payload()}, project).to_dict())
```

- `<int:project_id>` solo acepta números. `/api/projects/abc` ni siquiera entra a la función y da 404.
- `{**project.to_dict(), **payload()}` combina dos diccionarios y gana el segundo. Así un PUT puede enviar **solo** el
  campo que cambia (`{"name": "Web 2"}`) y el resto conserva su valor actual.
- `payload()` exige JSON:

  ```python
  def payload():
      data = request.get_json(silent=True)
      if not isinstance(data, dict):
          raise ValidationError("El cuerpo de la petición debe ser JSON")
      return data
  ```

  `silent=True` hace que un cuerpo mal formado devuelva `None` en vez de lanzar un error, y entonces respondemos
  nuestro propio 400 con un mensaje claro.

### Recursos anidados

Las secciones, casos y ejecuciones pertenecen a un proyecto. Por eso se **crean y listan** bajo el proyecto, pero se
**editan y borran** por su propio id:

```
GET  /api/projects/1/cases?priority=High&q=login     ← listar con filtros (query string)
POST /api/projects/1/cases                           ← crear dentro del proyecto 1
PUT  /api/cases/7                                    ← el id 7 ya identifica el caso
```

## Las pantallas: formulario → POST → redirección

Las pantallas usan formularios HTML normales. El patrón es siempre el mismo, y se llama **Post/Redirect/Get**:

```python
@views.post("/projects")
def projects_create():
    project = save_project(request.form)                      # 1. POST: guardar
    flash(f"Proyecto «{project.name}» creado", "success")     # 2. mensaje para la próxima página
    return redirect(url_for("views.projects"))                # 3. redirigir a un GET
```

**¿Por qué redirigir en vez de mostrar la página directamente?** Si después de un POST el usuario pulsa F5, el
navegador repetiría el POST y crearía el proyecto **dos veces**. Al redirigir, F5 solo repite el GET.

`flash()` guarda un mensaje en la sesión, que la plantilla `base.html` muestra una sola vez en la página siguiente.

## El proyecto activo

El selector "Proyecto" del encabezado decide qué proyecto se ve en Casos y Ejecuciones:

```python
def current_project(projects=None):
    """Proyecto activo: el de ?project=, el guardado en la sesión o el más antiguo."""
    wanted = request.args.get("project", type=int) or session.get("project_id")
    project = next((p for p in projects if p.id == wanted), None) or min(projects, key=lambda p: p.id, default=None)
    if project:
        session["project_id"] = project.id
    return project
```

El orden de prioridad es:

1. Lo que pide la URL (`?project=2`).
2. Lo que quedó guardado en la sesión.
3. El proyecto más antiguo.

La sesión es una cookie firmada con `SECRET_KEY`, así que el usuario no puede alterarla. Las páginas de detalle
(`/cases/5`, `/runs/2`) llaman a `remember_project(...)` para que el selector coincida con lo que se está viendo.

> **Error encontrado en el desarrollo:** al principio el valor por defecto era "el primero por orden alfabético".
> Como "App Móvil Clientes" va antes que "Portal de Facturación", la aplicación abría en el proyecto vacío. Se cambió
> a "el más antiguo" (`min(... key=id)`).

## El *context processor*

Hay variables que **todas** las plantillas necesitan: la lista de proyectos para el selector, el proyecto actual y
las listas de estados y prioridades. En vez de pasarlas en cada `render_template`, se registran una vez:

```python
@views.app_context_processor
def common_context():
    projects = db.session.scalars(db.select(Project).order_by(Project.name)).all()
    return {"all_projects": projects, "current_project": current_project(projects), "STATUSES": STATUSES, ...}
```

## Errores 404

```python
@app.errorhandler(404)
def not_found(_exc):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Recurso no encontrado"}), 404
    return render_template("404.html"), 404
```

La misma idea que con `ValidationError`: la API recibe JSON y el navegador una página bonita.
`db.get_or_404(Modelo, id)` lanza el 404 automáticamente si el id no existe.

## Tabla de rutas de pantalla

| Ruta | Pantalla |
|---|---|
| `/` | Dashboard |
| `/projects`, `/projects/<id>/edit` | Proyectos |
| `/cases?section=&priority=&q=` | Casos (carpetas + tabla) |
| `/cases/new`, `/cases/<id>`, `/cases/<id>/edit` | Crear, ver y editar caso |
| `/runs`, `/runs/new`, `/runs/<id>?status=` | Ejecuciones |
| `POST /results/<id>` | Registrar el resultado de un caso |

➡️ Siguiente: [6. Plantillas, Tailwind y JavaScript](06-plantillas-tailwind-js.md)
