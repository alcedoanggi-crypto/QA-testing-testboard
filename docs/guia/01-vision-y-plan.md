# 1. Visión general y plan

## El problema

Un equipo de QA necesita:

1. **Guardar casos de prueba** ordenados en carpetas: "Autenticación › Login › Contraseña incorrecta".
2. **Ejecutarlos por rondas**: "Regresión Sprint 14" incluye 8 casos y cada uno termina en Passed, Failed, Blocked o Untested.
3. **Ver el avance**: cuánto falta por ejecutar y qué porcentaje pasó.

Eso es lo que hace TestRail, y QA TestBoard es una versión pequeña y entendible del mismo concepto.

## Vocabulario (igual que en TestRail)

| Término | Significado | En el código |
|---|---|---|
| Proyecto | El producto que se prueba | `Project` |
| Sección | Carpeta de casos; puede tener subcarpetas | `Section` (con `parent_id`) |
| Caso de prueba | Qué probar y cómo (pasos + resultado esperado) | `TestCase`, se muestra como `C12` |
| Ejecución (Test Run) | Una ronda de pruebas con un conjunto de casos | `TestRun`, `R3` |
| Resultado (Test) | El estado de **un** caso dentro de **una** ejecución | `TestResult`, `T45` |

La distinción clave es **caso vs. resultado**. Un mismo caso (C1 "Login válido") se ejecuta en muchas rondas.
En cada ronda tiene su propio resultado, así que el caso no tiene un estado fijo: tiene un *historial*.

## Requisitos que se pidieron

- Flask en `localhost:5000` con `debug=True`.
- SQLite + SQLAlchemy con las tablas Proyectos, Secciones, Casos y Resultados, y endpoints CRUD.
- La interfaz:
  - Encabezado `#1E2D40` con el menú Dashboard / Proyectos / Casos de Prueba / Ejecuciones.
  - Vista de casos con carpetas a la izquierda y tabla a la derecha.
  - Colores: Passed verde, Failed rojo, Blocked amarillo, Untested gris.
- Pruebas pytest con `test_client`.
- VS Code: pytest habilitado y una tarea que arranque el servidor al abrir la carpeta.

## El plan (el orden en que se construyó)

1. **Estructura y arranque**: carpetas, `requirements.txt`, `app.py`, `create_app()`.
2. **Modelos**: primero los datos, porque todo lo demás depende de ellos.
3. **Servicios**: las reglas, como "Failed exige comentario" o "una sección no puede moverse dentro de sí misma".
4. **API JSON**: el CRUD expuesto como REST, que es fácil de probar.
5. **Pantallas HTML**: plantillas Jinja + Tailwind que usan **los mismos servicios**.
6. **Pruebas**: pytest sobre la API y las pantallas.
7. **VS Code**: `tasks.json` y `settings.json`.
8. **Documentación**: README, capturas, video y esta guía.

> ¿Por qué modelos → servicios → rutas? Cada capa solo depende de la anterior. Si los servicios están bien probados,
> las rutas son delgadas y casi no pueden fallar.

## Estructura de carpetas

```
qa-testboard/
├── app/              ← el paquete Python (toda la lógica)
│   ├── __init__.py   ← create_app()
│   ├── models.py     ← tablas
│   ├── services.py   ← reglas
│   ├── seed.py       ← datos de ejemplo
│   └── routes/       ← api.py (JSON) y views.py (HTML)
├── templates/        ← HTML con Jinja
├── static/           ← CSS (Tailwind) y JS
├── tests/            ← pytest
├── .vscode/          ← tareas y configuración del editor
├── app.py            ← punto de entrada
└── requirements.txt
```

**Detalle curioso:** existe `app.py` (archivo) y `app/` (paquete). Cuando escribes `from app import create_app`,
Python elige el **paquete** porque los paquetes tienen prioridad sobre los módulos con el mismo nombre en la misma
carpeta. Por eso `app.py` puede importar desde `app/` sin conflicto.

## Arquitectura en capas

```
Navegador ──HTML──> views.py ─┐
                              ├──> services.py ──> models.py ──> SQLite
Postman/curl ─JSON─> api.py ──┘
```

Las dos puertas de entrada (pantallas y API) comparten una sola implementación de las reglas.
Si mañana cambias la regla "Failed exige comentario", la cambias en un solo lugar.

➡️ Siguiente: [2. Entorno y arranque](02-entorno-y-arranque.md)
