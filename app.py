"""Punto de entrada de QA TestBoard.

    python app.py      ->   http://localhost:5000   (debug=True: se recarga solo al guardar cambios)

Variables opcionales: PORT, DATABASE_URL, SECRET_KEY, SEED_DEMO=0 (empezar sin datos de demostración).
"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="localhost", port=int(os.environ.get("PORT", "5000")), debug=True)
