"""Paquete de la aplicación QA TestBoard.

`create_app()` es una fábrica: construye una aplicación Flask nueva con la configuración indicada.
El servidor usa la configuración normal y cada prueba una base SQLite temporal propia (tests/conftest.py).
"""
import os

from flask import Flask, flash, jsonify, redirect, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def create_app(config=None):
    app = Flask(__name__, template_folder=os.path.join(ROOT_DIR, "templates"),
                static_folder=os.path.join(ROOT_DIR, "static"))
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "qa-testboard-desarrollo"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///" + os.path.join(ROOT_DIR, "instance", "testboard.db")),
        SEED_DEMO=os.environ.get("SEED_DEMO", "1") == "1",
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    os.makedirs(os.path.join(ROOT_DIR, "instance"), exist_ok=True)
    app.json.ensure_ascii = False

    db.init_app(app)

    from app.routes.api import api
    from app.routes.views import views
    app.register_blueprint(api)
    app.register_blueprint(views)

    from app.services import ValidationError

    @app.errorhandler(ValidationError)
    def validation_error(exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": str(exc)}), 400
        flash(str(exc), "error")
        return redirect(request.referrer or "/")

    @app.errorhandler(404)
    def not_found(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado"}), 404
        return render_template("404.html"), 404

    with app.app_context():
        db.create_all()
        if app.config["SEED_DEMO"]:
            from app.seed import seed_if_empty
            seed_if_empty()

    return app
