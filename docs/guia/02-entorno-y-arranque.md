# 2. Entorno y arranque

## Entorno virtual y dependencias

Un **entorno virtual** (`.venv`) es una copia aislada de Python para este proyecto. Así las versiones de Flask de
este proyecto no chocan con las de otros.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

`requirements.txt` contiene:

```
flask>=3.0,<4.0          # el framework web
flask-sqlalchemy>=3.1,<4.0   # integra SQLAlchemy (el ORM) con Flask
pytest>=8.0              # pruebas
pytest-cov>=5.0          # medir cobertura de las pruebas
```

Los rangos (`>=3.0,<4.0`) aceptan correcciones y mejoras, pero no una versión mayor que podría romper el código.

## `app.py`: el punto de entrada

```python
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="localhost", port=int(os.environ.get("PORT", "5000")), debug=True)
```

- `if __name__ == "__main__"` solo se cumple al ejecutar `python app.py`. Si otro archivo importa `app.py`, el
  servidor no arranca.
- `debug=True` hace dos cosas:
  - **Recarga** el servidor al guardar un archivo `.py`.
  - Muestra una página de error detallada en el navegador.

  Nunca se usa en producción.
- El puerto sale de la variable `PORT` (5000 por defecto). Así se puede cambiar sin tocar el código.

## La fábrica `create_app()`

En lugar de crear un `app = Flask(...)` global, la aplicación se construye dentro de una función
(`app/__init__.py`). Esto se llama *application factory*:

```python
def create_app(config=None):
    app = Flask(__name__, template_folder=os.path.join(ROOT_DIR, "templates"),
                static_folder=os.path.join(ROOT_DIR, "static"))
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "qa-testboard-desarrollo"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///" + os.path.join(ROOT_DIR, "instance", "testboard.db")),
        SEED_DEMO=os.environ.get("SEED_DEMO", "1") == "1",
    )
    if config:
        app.config.update(config)          # ← las pruebas pasan aquí su propia base de datos
    ...
```

**¿Por qué una fábrica?** Por las pruebas. Cada prueba llama a `create_app({...})` con una base temporal distinta y
obtiene una aplicación nueva y limpia. Con una `app` global, todas las pruebas compartirían la misma base de datos.

- `template_folder` y `static_folder` apuntan a la raíz, porque la estructura pedida pone `templates/` y `static/`
  fuera del paquete `app/`. Por defecto Flask los buscaría dentro de `app/`.
- `SECRET_KEY` firma la cookie de sesión, que guarda el proyecto activo y los mensajes flash.

### El resto de `create_app()`

```python
    db.init_app(app)                       # conecta SQLAlchemy con esta app

    app.register_blueprint(api)            # rutas /api/...
    app.register_blueprint(views)          # pantallas HTML

    @app.errorhandler(ValidationError)     # dato inválido en cualquier parte → respuesta amable
    def validation_error(exc): ...

    with app.app_context():
        db.create_all()                    # crea las tablas si no existen
        if app.config["SEED_DEMO"]:
            seed_if_empty()                # datos de ejemplo la primera vez
```

`db.create_all()` crea las tablas que falten y no toca las existentes, así que es seguro llamarlo en cada arranque.
Para un proyecto que evoluciona en producción se usarían *migraciones* (Flask-Migrate); aquí basta con esto.

`app.app_context()` es necesario porque SQLAlchemy necesita saber a **qué** aplicación pertenece la base de datos.
Dentro de una petición HTTP Flask crea ese contexto solo; fuera de una petición, como al arrancar, hay que crearlo a mano.

## Datos de ejemplo (`seed.py`)

`seed_if_empty()` solo inserta datos si **no hay ningún proyecto**:

```python
def seed_if_empty():
    if db.session.scalar(db.select(db.func.count(Project.id))):
        return False
    ...
```

Así la primera vez la aplicación muestra el proyecto "Portal de Facturación", con secciones, 8 casos y una ejecución
a medias, y nunca duplica datos ni pisa los tuyos. Para empezar de cero, borra `instance/testboard.db`.

➡️ Siguiente: [3. Base de datos con SQLAlchemy](03-base-de-datos.md)
