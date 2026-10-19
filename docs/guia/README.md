# Guía: cómo se construyó QA TestBoard

Esta guía explica, paso a paso y en el mismo orden en que se hizo, cómo se construyó la aplicación y **por qué**
se tomó cada decisión. La idea es que puedas leer el código entendiendo la lógica y luego rehacerlo por tu cuenta.

| # | Capítulo | Qué aprendes |
|---|---|---|
| 1 | [Visión general y plan](01-vision-y-plan.md) | Qué problema resuelve, cómo se dividió el trabajo, estructura de carpetas |
| 2 | [Entorno y arranque](02-entorno-y-arranque.md) | venv, requirements, `app.py`, la fábrica `create_app()` |
| 3 | [Base de datos con SQLAlchemy](03-base-de-datos.md) | Modelos, relaciones, árbol de secciones, cascadas, "foto" del caso |
| 4 | [Servicios y validación](04-servicios-y-validacion.md) | Por qué la lógica va en `services.py`, "validar primero, modificar después" |
| 5 | [Rutas: API JSON y pantallas](05-rutas-api-y-vistas.md) | Blueprints, CRUD REST, formularios POST → redirección, manejo de errores |
| 6 | [Plantillas, Tailwind y JavaScript](06-plantillas-tailwind-js.md) | Jinja, herencia, macros, compilar Tailwind, colores de estado |
| 7 | [Pruebas con pytest](07-pruebas-pytest.md) | `test_client`, fixtures, parametrize, cobertura |
| 8 | [VS Code y práctica](08-vscode-y-practica.md) | `tasks.json`, `settings.json`, ejercicios para practicar |

**Recomendación:** abre el código al lado de cada capítulo. Cada archivo nombrado aquí existe en la carpeta
`C:\Users\Pc\Downloads\qa-testboard`, y los fragmentos son copias reales del código.

También hay un video con la presentación y el recorrido de la aplicación: `docs/video/qa-testboard-presentacion.mp4`.
