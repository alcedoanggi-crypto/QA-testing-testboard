# 8. VS Code y práctica

## `.vscode/settings.json`

```jsonc
{
    "python.testing.pytestEnabled": true,          // usar pytest…
    "python.testing.unittestEnabled": false,       // …y no unittest
    "python.testing.pytestArgs": ["tests"],        // buscar pruebas en la carpeta tests/
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
    "task.allowAutomaticTasks": "on",              // permitir la tarea automática al abrir la carpeta
    "files.associations": { "*.html": "jinja-html" }
}
```

Con esto, la pestaña **Testing** (ícono del matraz 🧪) de VS Code muestra las 64 pruebas en árbol. Se pueden
ejecutar todas, una sola o depurarlas con puntos de interrupción. Se necesita la extensión **Python** de Microsoft.

`${workspaceFolder}` es una variable de VS Code que vale la carpeta abierta. Así la configuración funciona en
cualquier computador, sin rutas fijas.

## `.vscode/tasks.json`: el servidor arranca solo

```jsonc
{
    "label": "Iniciar servidor (Flask :5000)",
    "type": "shell",
    "command": "${workspaceFolder}/.venv/Scripts/python.exe",
    "args": ["app.py"],
    "isBackground": true,
    "runOptions": { "runOn": "folderOpen" },        // ← se ejecuta al abrir la carpeta
    "problemMatcher": {
        "owner": "flask",
        "pattern": { "regexp": "^__nunca_coincide__$" },
        "background": {
            "activeBegin": "Serving Flask app",
            "activeEnd": "Running on http://"
        }
    }
}
```

- `runOptions.runOn: "folderOpen"` es lo que pide el requisito: al abrir la carpeta, la tarea corre sola.
- Por seguridad, VS Code pregunta la primera vez si se permiten tareas automáticas, porque una carpeta descargada
  podría ejecutar cualquier cosa. El ajuste `task.allowAutomaticTasks` lo controla.
- `isBackground: true` + `problemMatcher.background` explica cuándo "terminó de arrancar" un proceso que nunca
  termina, como un servidor: cuando la salida muestra `Running on http://`. Sin esto VS Code se quedaría esperando
  para siempre. El `pattern` imposible indica que no buscamos errores de compilación en la salida.
- `linux` y `osx` cambian la ruta del intérprete (`.venv/bin/python`), así el mismo archivo sirve en otros sistemas.

También hay tareas para:

- instalar dependencias;
- correr pytest (es la tarea de prueba por defecto: *Run Test Task*);
- pytest con cobertura;
- compilar Tailwind y Tailwind en modo watch.

Se ejecutan con **Terminal → Run Task…**.

## Ejercicios para practicar

Ordenados de fácil a difícil. Después de cada uno, escribe su prueba en `tests/test_app.py` y corre `pytest`.

1. **Nuevo tipo de caso.** Agrega `"Security"` a `CASE_TYPES` en `models.py`. ¿Qué pantallas cambian solas?
   (Pista: el `<select>` del formulario se arma con un `for`.)
2. **Nuevo estado "Retest".**
   - Agrégalo a `STATUSES` con un color naranja en `tailwind.config.js`.
   - Escribe su clase `badge-retest` **completa** en el macro y en `input.css`.
   - Recompila Tailwind. ¿Qué pasa con `stats()` y con la barra de progreso?
3. **Estimación.** Agrega a `TestCase` una columna `estimate` (minutos, entero opcional).
   - Valídala en `save_case` (no negativa) y muéstrala en la tabla.
   - Borra `instance/testboard.db` para que `create_all()` cree la columna.
   - Pregunta: ¿por qué hace falta borrar la base?
4. **Copiar un caso.** Crea la ruta `POST /cases/<id>/copy` que duplique un caso con el título "Copia de …".
   Reutiliza `save_case`.
5. **Reabrir una ejecución cerrada.** Crea el servicio y la ruta `POST /api/runs/<id>/reopen`.
   Prueba que después se puedan volver a registrar resultados.
6. **Exportar a CSV.** Agrega `GET /runs/<id>/export.csv` con los resultados. Investiga el módulo `csv` y
   `Response(..., mimetype="text/csv")`.

## Resumen de lo aprendido

| Concepto | Dónde se ve |
|---|---|
| Fábrica de aplicaciones | `create_app()` |
| ORM, relaciones, cascadas, árbol recursivo | `models.py` |
| "Foto" de datos para el historial | `TestResult.case_title` |
| Validar primero, modificar después | `services.save_case` |
| Un error propio manejado en un solo lugar | `ValidationError` + `errorhandler` |
| API REST + Post/Redirect/Get | `routes/api.py`, `routes/views.py` |
| Herencia de plantillas y macros | `base.html`, `macros.html` |
| Tailwind compila solo las clases que ve escritas | `macros.html` (`status_badge`) |
| Fixtures, parametrize, cobertura | `tests/` |
| Automatizar el editor | `.vscode/` |

⬅️ Volver al [índice de la guía](README.md)
