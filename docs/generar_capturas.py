"""Toma las capturas de docs/capturas/*.png con Selenium (Chrome sin ventana) y revisa la consola del navegador.

Uso (con el servidor ya corriendo):
    pip install selenium            # solo hace falta para este script, no para la app
    python docs/generar_capturas.py                         # usa http://localhost:5000
    python docs/generar_capturas.py http://localhost:5055   # otra URL

Recomendado sobre una base recién creada (borra instance/testboard.db y reinicia el servidor)
para que las imágenes muestren los datos de demostración.
"""
import html
import os
import pathlib
import subprocess
import sys
import tempfile
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "capturas")
PYTHON = os.path.join(ROOT, ".venv", "Scripts" if os.name == "nt" else "bin", "python")
os.makedirs(OUT, exist_ok=True)


def pick_cases(driver):
    """En 'Nueva ejecución' elige 'casos específicos' y marca algunos, para que se vea el selector."""
    driver.find_element(By.CSS_SELECTOR, "[data-case-picker-toggle][value='0']").click()
    for box in driver.find_elements(By.NAME, "case_ids")[:3]:
        box.click()


def failed_without_comment(driver):
    """Intenta guardar Failed sin comentario: muestra la validación del lado del cliente."""
    form = driver.find_elements(By.CSS_SELECTOR, "form[data-result-form]")[-1]
    form.find_element(By.NAME, "status").send_keys("Failed")
    form.find_element(By.CSS_SELECTOR, "button[type=submit]").click()


# (archivo, ruta, acción opcional antes de la foto)
SCREENS = [
    ("01-dashboard", "/", None),
    ("02-proyectos", "/projects", None),
    ("03-casos-de-prueba", "/cases?project=1", None),
    ("04-casos-seccion", "/cases?section=1", None),
    ("05-caso-detalle", "/cases/1", None),
    ("06-caso-formulario", "/cases/1/edit", None),
    ("07-ejecuciones", "/runs", None),
    ("08-nueva-ejecucion", "/runs/new", pick_cases),
    ("09-ejecucion-detalle", "/runs/1", None),
    ("10-ejecucion-filtro-failed", "/runs/1?status=failed", None),
    ("11-validacion-comentario", "/runs/1?status=untested", failed_without_comment),
]


def pytest_report_page():
    """Corre pytest con cobertura y guarda la salida como una página tipo terminal (para la imagen del reporte)."""
    run = subprocess.run([PYTHON, "-m", "pytest", "-o", "addopts=", "-v", "--cov=app", "--cov-report=term", "--cov-report=html",
                          "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    lines = []
    for line in run.stdout.splitlines():
        color = "#4ade80" if "PASSED" in line or " passed" in line else "#f87171" if "FAILED" in line else "#e2e8f0"
        lines.append(f'<div style="color:{color}">{html.escape(line) or "&nbsp;"}</div>')
    page = pathlib.Path(tempfile.mkdtemp()) / "pytest.html"
    page.write_text(f"""<html><body style="margin:0;background:#192734;font:13px/1.45 Consolas,monospace;padding:20px 24px;white-space:pre">
        <div style="color:#94a3b8;margin-bottom:8px">$ pytest -v --cov=app</div>{''.join(lines)}</body></html>""",
                    encoding="utf-8")
    return page.as_uri()


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver = webdriver.Chrome(options=options)
    errors = []
    try:
        for name, route, action in SCREENS:
            driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                                   {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
            driver.get(BASE + route)
            time.sleep(0.6)
            if action:
                action(driver)
                time.sleep(0.4)
            height = driver.execute_script("return Math.max(document.body.scrollHeight, 900)")
            driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                                   {"width": 1440, "height": height, "deviceScaleFactor": 1, "mobile": False})
            driver.save_screenshot(os.path.join(OUT, f"{name}.png"))
            for entry in driver.get_log("browser"):
                if entry["level"] == "SEVERE":
                    errors.append(f"{route}: {entry['message']}")
            print("✓", name)

        # Imágenes de reportes: salida de pytest y reporte HTML de cobertura (htmlcov/).
        reports = [("12-reporte-pytest", pytest_report_page()),
                   ("13-reporte-cobertura", pathlib.Path(ROOT, "htmlcov", "index.html").as_uri())]
        for name, url in reports:
            driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                                   {"width": 1100, "height": 800, "deviceScaleFactor": 1, "mobile": False})
            driver.get(url)
            time.sleep(0.5)
            height = driver.execute_script("return Math.max(document.body.scrollHeight + 40, 600)")
            driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                                   {"width": 1100, "height": height, "deviceScaleFactor": 1, "mobile": False})
            driver.save_screenshot(os.path.join(OUT, f"{name}.png"))
            print("✓", name)
    finally:
        driver.quit()
    print("Errores de consola:", errors or "ninguno")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
