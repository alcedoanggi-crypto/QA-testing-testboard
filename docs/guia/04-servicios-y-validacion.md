# 4. Servicios y validación

`app/services.py` contiene **todas las reglas de negocio**. Las rutas (API y pantallas) no validan nada por su
cuenta: reciben los datos, llaman a un servicio y muestran el resultado.

## Una excepción propia para "dato inválido"

```python
class ValidationError(ValueError):
    """Dato inválido: la API responde 400 y las pantallas muestran el mensaje."""
```

Cuando algo está mal, el servicio **lanza** `ValidationError("mensaje para el usuario")`. Quién lo atrapa y qué
hace con él se decide en un solo lugar (`create_app`):

```python
@app.errorhandler(ValidationError)
def validation_error(exc):
    if request.path.startswith("/api/"):
        return jsonify({"error": str(exc)}), 400        # API → JSON 400
    flash(str(exc), "error")                            # pantalla → mensaje rojo
    return redirect(request.referrer or "/")            #   y volver a donde estaba
```

Así el servicio no necesita saber si lo llamó la API o un formulario.

## Validadores pequeños y reutilizables

```python
def clean_text(data, key, label, max_len, required=False):
    value = str(data.get(key) or "").strip()
    if required and not value:
        raise ValidationError(f"El campo «{label}» es obligatorio")
    if len(value) > max_len:
        raise ValidationError(f"«{label}» admite máximo {max_len} caracteres")
    return value

def clean_choice(data, key, label, options, default):
    value = str(data.get(key) or default).strip()
    if value not in options:
        raise ValidationError(f"«{label}» inválido. Valores permitidos: {', '.join(options)}")
    return value

def to_id(value, label):
    if isinstance(value, int) or str(value).isdigit():
        return int(value)
    raise ValidationError(f"«{label}» debe ser un número")
```

- `data.get(...)` funciona igual con un diccionario JSON y con `request.form`. Por eso los mismos servicios sirven
  para la API y para los formularios.
- `to_id` existe porque `int("abc")` lanza un `ValueError` normal, que terminaría en un **error 500**. Un dato mal
  escrito debe ser un 400 con un mensaje claro, nunca un 500.

## La regla de oro: validar primero, modificar después

```python
def save_case(project, data, case=None):
    """Valida todo primero y solo después toca el objeto: un dato inválido no deja cambios a medias."""
    section = get_or_404(Section, to_id(data["section_id"], "Sección")) if data.get("section_id") else None
    if section is None:
        raise ValidationError("Elige la sección del caso")
    if section.project_id != project.id:
        raise ValidationError("La sección pertenece a otro proyecto")
    values = {
        "title": clean_text(data, "title", "Título", 250, required=True),
        "priority": clean_choice(data, "priority", "Prioridad", PRIORITIES, "Medium"),
        ...
        "steps": parse_steps(data.get("steps", [])),
    }
    case = case or TestCase()            # ← recién aquí se crea o modifica el objeto
    for key, value in values.items():
        setattr(case, key, value)
    case.section = section
    case.project = project
    db.session.add(case)
    db.session.commit()
    return case
```

**¿Por qué importa el orden?** Supón que primero se asigna `case.title = "Nuevo"` y después falla la prioridad. El
objeto ya quedó modificado en la sesión de SQLAlchemy, y cualquier `commit()` posterior lo guardaría a medias.
Durante el desarrollo esto apareció como una advertencia (`SAWarning: Object of type TestCase not in session`) y
se corrigió reordenando el código. La prueba `test_nombre_demasiado_largo_no_modifica` comprueba que un PUT
inválido no cambia nada.

## Reglas de las secciones

```python
def save_section(project, data, section=None):
    ...
    if parent_id:
        parent = get_or_404(Section, to_id(parent_id, "Sección padre"))
        if parent.project_id != project.id:
            raise ValidationError("La sección padre pertenece a otro proyecto")
        if section is not None and parent.id in section.descendant_ids():
            raise ValidationError("Una sección no puede moverse dentro de sí misma")
```

La segunda regla evita un **ciclo**. Si "Login" se mueve dentro de su propia subcarpeta "Errores", el árbol
quedaría A → B → A → B… y `path` entraría en un bucle infinito. `descendant_ids()` incluye a la propia sección, así
que también impide hacerla su propio padre.

## Pasos: dos formatos de entrada, uno de salida

La API recibe una lista JSON y el formulario recibe texto. `parse_steps` acepta ambos y siempre devuelve lo mismo:

```python
def parse_steps(value):
    if isinstance(value, str):                       # formulario: "acción | resultado" por línea
        steps = []
        for line in value.splitlines():
            if not line.strip():
                continue
            action, _, expected = line.partition("|")
            steps.append({"action": action.strip(), "expected": expected.strip()})
        value = steps
    if not isinstance(value, list):
        raise ValidationError("Los pasos deben ser una lista")
    ...
```

`str.partition("|")` divide en el **primer** `|` y siempre devuelve 3 partes, aunque no haya `|`. Por eso no falla
con líneas como "Pulsar Ingresar", que no tienen resultado esperado.

## Crear una ejecución

```python
def create_run(project, data):
    name = clean_text(data, "name", "Nombre", 150, required=True)
    if data.get("include_all", True) in (True, "1", "true", "on", 1):
        cases = list(project.cases)
    else:
        ids = {int(i) for i in data.get("case_ids") or []}       # (dentro de un try → ValidationError)
        cases = [c for c in project.cases if c.id in ids]
        if len(cases) != len(ids):
            raise ValidationError("Algunos casos no pertenecen al proyecto")
    if not cases:
        raise ValidationError("La ejecución necesita al menos un caso de prueba")
    snapshots = [dict(case=case, case_title=case.title, section_path=case.section.path, priority=case.priority)
                 for case in sorted(cases, key=lambda c: (c.section.path, c.id))]
    run = TestRun(name=name, description=description)
    db.session.add(run)
    run.results = [TestResult(status="untested", **snap) for snap in snapshots]
    run.project = project
    db.session.commit()
```

- `include_all` acepta `True` (JSON) y `"1"` (formulario).
- `len(cases) != len(ids)` detecta ids inexistentes **o de otro proyecto**. Sin esta comprobación se podría meter en
  una ejecución un caso de otro proyecto.
- Cada resultado nace "untested" con la **foto** del caso (capítulo 3).

## Registrar un resultado

```python
def record_result(result, data):
    if result.run.is_completed:
        raise ValidationError("La ejecución está cerrada; no admite resultados nuevos")
    status = clean_choice(data, "status", "Estado", STATUSES, "passed")
    comment = clean_text(data, "comment", "Comentario", 4000)
    if status in ("failed", "blocked") and not comment:
        raise ValidationError("Describe el problema en el comentario (obligatorio para Failed y Blocked)")
    result.status = status
    result.comment = comment
    result.executed_by = clean_text(data, "executed_by", "Ejecutado por", 80) or "QA"
    result.executed_at = now() if status != "untested" else None
```

Un Failed sin explicación no le sirve al programador que debe corregirlo, y por eso se exige el comentario. Además,
volver a "untested" borra la fecha de ejecución, ya que ese caso deja de estar ejecutado.

➡️ Siguiente: [5. Rutas: API JSON y pantallas](05-rutas-api-y-vistas.md)
