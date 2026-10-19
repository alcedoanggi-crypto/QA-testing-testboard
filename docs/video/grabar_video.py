"""Genera docs/video/qa-testboard-presentacion.mp4: presentación (diapositivas) + recorrido paso a paso con subtítulos.

Levanta su propio servidor con una base TEMPORAL (no toca instance/testboard.db).
Requisitos extra (solo para grabar):  pip install selenium imageio imageio-ffmpeg pillow numpy
Ejecutar desde la raíz del proyecto:    python docs/video/grabar_video.py
"""
import io
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.request

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa-testboard-presentacion.mp4")
VENV_PY = os.path.join(ROOT, ".venv", "Scripts" if os.name == "nt" else "bin", "python")
SHOTS = os.path.join(ROOT, "docs", "capturas")

FPS = 2
W, SHOT_H, BAND_H = 1280, 800, 160
H = SHOT_H + BAND_H
NAVY, NAVY7, MINT, BG, INK, MUTED = (30, 45, 64), (42, 61, 85), (46, 204, 113), (245, 247, 250), (31, 42, 55), (100, 116, 139)
STATUS = [("Passed", "✓", (26, 127, 75)), ("Failed", "✕", (217, 45, 69)), ("Blocked", "⊘", (240, 190, 44)),
          ("Untested", "○", (174, 184, 198))]


def font(size, bold=False):
    for name in ("segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"):
        try:
            return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", name), size)
        except OSError:
            continue
    return ImageFont.load_default()


F = {"step": font(20, True), "title": font(28, True), "text": font(22), "h1": font(58, True), "h2": font(40, True),
     "body": font(27), "bodyb": font(27, True), "small": font(21), "mono": font(22)}
SYMBOL_FONT = os.path.join(r"C:\Windows\Fonts", "seguisym.ttf")   # Segoe UI no trae ✓ ✕ ⊘ ○
F["sym"] = ImageFont.truetype(SYMBOL_FONT, 28) if os.path.isfile(SYMBOL_FONT) else F["body"]
try:
    F["mono"] = ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", "consola.ttf"), 22)
except OSError:
    pass


class Video:
    def __init__(self):
        self.frames = []
        self.step = 0

    def add(self, img, seconds):
        self.frames.extend([np.asarray(img.convert("RGB"))] * max(1, int(seconds * FPS)))

    # ------------------------------------------------------------------ diapositivas
    def slide_base(self, title, kicker="Presentación"):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, W, 86), fill=NAVY)
        d.rounded_rectangle((40, 22, 82, 64), 8, fill=MINT)
        d.text((61, 43), "TB", font=F["step"], fill=NAVY, anchor="mm")
        d.text((98, 43), "QA TestBoard", font=F["title"], fill="white", anchor="lm")
        d.text((W - 40, 43), kicker, font=F["small"], fill=(159, 176, 196), anchor="rm")
        d.text((70, 130), title, font=F["h2"], fill=INK)
        d.rectangle((70, 188, 170, 194), fill=MINT)
        return img, d

    def bullets(self, d, items, x=70, y=225, gap=62):
        for item in items:
            head, _, rest = item.partition(" — ")
            d.ellipse((x, y + 12, x + 12, y + 24), fill=MINT)
            d.text((x + 30, y), head, font=F["bodyb"], fill=INK)
            if rest:
                d.text((x + 30 + d.textlength(head, font=F["bodyb"]), y), " — " + rest, font=F["body"], fill=MUTED)
            y += gap
        return y

    def title_slide(self):
        img = Image.new("RGB", (W, H), NAVY)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((80, 120, 200, 240), 22, fill=MINT)
        d.text((140, 180), "TB", font=F["h2"], fill=NAVY, anchor="mm")
        d.text((80, 300), "QA TestBoard", font=F["h1"], fill="white")
        d.text((80, 385), "Flask + SQLAlchemy + Tailwind CSS + pytest, listo para VS Code", font=F["body"], fill=(199, 211, 224))
        d.text((80, 425), "Presentación y recorrido paso a paso", font=F["body"], fill=MINT)
        y = 540
        for label, value in (("Dirección", "http://localhost:5000"), ("Acceso", "sin usuario ni contraseña"),
                             ("Carpeta", r"C:\Users\Pc\Downloads\qa-testboard"), ("Iniciar", "python app.py")):
            d.text((80, y), label, font=F["small"], fill=(159, 176, 196))
            d.text((260, y), value, font=F["bodyb"], fill="white")
            y += 48
        self.add(img, 7)

    def slides(self):
        img, d = self.slide_base("¿Qué es QA TestBoard?")
        self.bullets(d, ["Proyectos — cada uno con sus carpetas, casos y ejecuciones",
                         "Secciones — carpetas y subcarpetas para ordenar los casos",
                         "Casos de prueba — título, prioridad, tipo, referencias y pasos",
                         "Ejecuciones (Test Runs) — rondas de prueba con un resultado por caso",
                         "Dashboard — avance, pass rate y últimos resultados",
                         "API REST JSON — el mismo CRUD para integrarlo con otras herramientas"])
        self.add(img, 8)

        img, d = self.slide_base("Estructura de la carpeta")
        tree = ["qa-testboard/", "├── app/                 ← paquete Python (modelos, servicios, rutas)",
                "│   ├── models.py        ← tablas SQLAlchemy", "│   ├── services.py      ← reglas y validaciones",
                "│   └── routes/          ← api.py (JSON) y views.py (HTML)", "├── templates/           ← Jinja + Tailwind",
                "├── static/              ← css (Tailwind compilado) y js", "├── tests/               ← pytest con test_client",
                "├── .vscode/             ← tasks.json y settings.json", "├── app.py               ← arranca en :5000 (debug)",
                "└── requirements.txt"]
        for i, line in enumerate(tree):
            d.text((90, 230 + i * 44), line, font=F["mono"], fill=INK if "←" not in line else NAVY7)
        self.add(img, 9)

        img, d = self.slide_base("Arquitectura en capas")
        layers = [("Navegador", "Plantillas Jinja + Tailwind CSS + un poco de JavaScript", NAVY7),
                  ("Rutas Flask", "views.py devuelve HTML · api.py devuelve JSON (los dos usan services.py)", NAVY),
                  ("Servicios", "Validan los datos y aplican las reglas (un solo lugar para la lógica)", (45, 70, 100)),
                  ("SQLAlchemy + SQLite", "Project · Section · TestCase · TestRun · TestResult", (17, 96, 58))]
        for i, (name, desc, color) in enumerate(layers):
            y = 230 + i * 140
            d.rounded_rectangle((70, y, W - 70, y + 110), 14, fill=color)
            d.text((110, y + 26), name, font=F["bodyb"], fill="white")
            d.text((110, y + 66), desc, font=F["small"], fill=(220, 230, 240))
        self.add(img, 8)

        img, d = self.slide_base("Colores de estado")
        for i, (name, color) in enumerate((("Encabezado #1E2D40", NAVY), ("Acciones", MINT), ("Fondo", BG), ("Tarjetas", (255, 255, 255)))):
            x = 70 + i * 290
            d.rounded_rectangle((x, 230, x + 260, 300), 10, fill=color, outline=(203, 213, 225), width=2)
            d.text((x, 312), name, font=F["small"], fill=MUTED)
        d.text((70, 400), "Cada estado lleva color, ícono y texto (no solo color):", font=F["body"], fill=INK)
        for i, (name, icon, color) in enumerate(STATUS):
            x = 70 + i * 290
            d.rounded_rectangle((x, 470, x + 260, 540), 35, fill=color)
            ink = (60, 45, 0) if name in ("Blocked", "Untested") else "white"
            label_w, icon_w = d.textlength(name, font=F["bodyb"]), d.textlength(icon, font=F["sym"])
            start = x + 130 - (icon_w + 10 + label_w) / 2
            d.text((start, 505), icon, font=F["sym"], fill=ink, anchor="lm")
            d.text((start + icon_w + 10, 505), name, font=F["bodyb"], fill=ink, anchor="lm")
        d.text((70, 600), "Passed verde · Failed rojo · Blocked amarillo · Untested gris", font=F["body"], fill=MUTED)
        self.add(img, 8)

        img, d = self.slide_base("Flujo de trabajo")
        boxes = ["1. Crear proyecto", "2. Crear secciones", "3. Escribir casos",
                 "4. Crear ejecución", "5. Marcar resultados", "6. Revisar dashboard"]
        for i, label in enumerate(boxes):
            x, y = 70 + (i % 3) * 395, 250 + (i // 3) * 220
            d.rounded_rectangle((x, y, x + 340, y + 120), 14, fill=NAVY if i % 2 else NAVY7)
            d.text((x + 170, y + 60), label, font=F["bodyb"], fill="white", anchor="mm")
            if i % 3 != 2:
                d.text((x + 367, y + 60), "→", font=F["h2"], fill=MINT, anchor="mm")
        d.text((70, 740), "Ahora, el recorrido paso a paso en la aplicación real.", font=F["body"], fill=INK)
        self.add(img, 8)

    # ------------------------------------------------------------------ capturas con subtítulo
    def frame(self, screen, title, text, seconds):
        self.step += 1
        screen = screen.convert("RGB").resize((W, SHOT_H), Image.LANCZOS)
        img = Image.new("RGB", (W, H), (15, 23, 42))
        img.paste(screen, (0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle((0, SHOT_H, W, SHOT_H + 6), fill=MINT)
        d.rounded_rectangle((30, SHOT_H + 26, 142, SHOT_H + 60), 8, fill=MINT)
        d.text((86, SHOT_H + 43), f"Paso {self.step}", font=F["step"], fill=NAVY, anchor="mm")
        d.text((162, SHOT_H + 22), title, font=F["title"], fill="white")
        for i, line in enumerate(textwrap.wrap(text, 104)[:3]):
            d.text((32, SHOT_H + 74 + i * 28), line, font=F["text"], fill=(203, 213, 225))
        self.add(img, seconds)

    def shot(self, driver, title, text, seconds=5):
        self.frame(Image.open(io.BytesIO(driver.get_screenshot_as_png())), title, text, seconds)

    def image(self, path, title, text, seconds=6):
        """Paso a partir de una imagen ya generada (los reportes de pytest/cobertura), recortada a 16:10."""
        src = Image.open(path).convert("RGB")
        canvas = Image.new("RGB", (src.width, int(src.width * SHOT_H / W)), (25, 39, 52))
        canvas.paste(src.crop((0, 0, src.width, min(src.height, canvas.height))), (0, 0))
        self.frame(canvas, title, text, seconds)

    def end_slide(self):
        img = Image.new("RGB", (W, H), NAVY)
        d = ImageDraw.Draw(img)
        d.text((80, 220), "¡Listo!", font=F["h1"], fill="white")
        lines = [("Iniciar", "python app.py  (o abrir la carpeta en VS Code)"), ("Dirección", "http://localhost:5000"),
                 ("Pruebas", "pytest --cov=app"), ("Guía", r"docs\guia\README.md"),
                 ("Carpeta", r"C:\Users\Pc\Downloads\qa-testboard")]
        for i, (k, v) in enumerate(lines):
            d.text((80, 340 + i * 56), k, font=F["small"], fill=(159, 176, 196))
            d.text((260, 336 + i * 56), v, font=F["bodyb"], fill="white")
        self.add(img, 7)

    def save(self):
        writer = imageio.get_writer(OUTPUT, fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p", macro_block_size=16)
        for frame in self.frames:
            writer.append_data(frame)
        writer.close()


def start_server():
    """Arranca la app (sin el recargador de debug) en un puerto libre con una base temporal."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    db = os.path.join(tempfile.mkdtemp(prefix="testboard_video_"), "video.db").replace("\\", "/")
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{db}")
    proc = subprocess.Popen([VENV_PY, "-c", f"from app import create_app; create_app().run(port={port})"],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/api/health", timeout=1)
            return proc, base
        except OSError:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("El servidor no arrancó")


def main():
    proc, base = start_server()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    v = Video()
    by = lambda sel: driver.find_element(By.CSS_SELECTOR, sel)  # noqa: E731

    def go(path):
        driver.get(base + path)
        time.sleep(0.8)

    def mark(el):
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});arguments[0].style.outline='4px solid #F0BE2C';"
                              "arguments[0].style.outlineOffset='3px';", el)
        time.sleep(0.2)
        return el

    def fill(sel, text):
        el = by(sel)
        el.clear()
        el.send_keys(text)

    try:
        v.title_slide()
        v.slides()

        go("/")
        v.shot(driver, "Dashboard", "Al abrir http://localhost:5000 se ve el resumen: proyectos, casos, ejecuciones activas y "
               "pass rate. La barra apilada muestra Passed, Failed, Blocked y Untested; a la derecha, los últimos resultados.", 7)

        go("/projects")
        v.shot(driver, "Proyectos", "Crea, edita y elimina proyectos. Cada uno cuenta sus secciones, casos y ejecuciones. "
               "El selector «Proyecto» del encabezado cambia el proyecto activo en todas las pantallas.", 6)
        fill("#p-name", "Tienda Online")
        fill("#p-desc", "Pruebas del carrito y del checkout")
        mark(by("#form-project button"))
        v.shot(driver, "Nuevo proyecto", "Escribe el nombre (obligatorio) y la descripción, y pulsa «Crear proyecto».", 5)
        by("#form-project button").click()
        time.sleep(1)
        v.shot(driver, "Proyecto creado", "Aparece el mensaje de confirmación y el proyecto en la tabla. Su nombre lleva a "
               "sus casos de prueba.", 5)

        go("/cases?project=1")
        v.shot(driver, "Casos de prueba", "A la izquierda, las secciones (carpetas y subcarpetas) con su cantidad de casos. "
               "A la derecha, la tabla con ID, título, sección, prioridad, tipo, referencias y último estado.", 7)
        by("#section-tree a[data-section='2']").click()
        time.sleep(0.8)
        v.shot(driver, "Filtrar por carpeta", "Al pulsar una carpeta se ven sus casos y los de sus subcarpetas. También se "
               "busca por título, referencia o ID (C3) y se filtra por prioridad.", 6)

        fill("#s-name", "Errores de login")
        Select(by("#form-section select")).select_by_index(2)
        mark(by("#form-section button"))
        v.shot(driver, "Nueva sección", "Escribe el nombre y elige la carpeta padre (o «En la raíz»). Al pasar el mouse "
               "por una carpeta aparece ✕ para eliminarla junto con sus casos.", 6)
        by("#form-section button").click()
        time.sleep(1)

        by("#btn-new-case").click()
        time.sleep(0.8)
        fill("#c-title", "Usuario bloqueado ve un mensaje claro")
        Select(by("#c-priority")).select_by_visible_text("High")
        Select(by("#c-type")).select_by_visible_text("Functional")
        fill("#c-refs", "JIRA-150")
        fill("#c-pre", "Usuario con la cuenta bloqueada")
        fill("#c-steps", "Abrir /login | Se ve el formulario\nIngresar las credenciales | \n"
                         "Pulsar Ingresar | Mensaje «Tu cuenta está bloqueada»")
        mark(by("#btn-save-case"))
        v.shot(driver, "Crear un caso de prueba", "Título, sección, prioridad (Low a Critical), tipo, referencias y "
               "precondiciones. Los pasos se escriben uno por línea: «acción | resultado esperado».", 8)
        by("#btn-save-case").click()
        time.sleep(1)
        v.shot(driver, "Caso creado", "El caso aparece en su sección con su ID (C…). Sin ejecuciones, su último estado es «—».", 5)
        by("#cases-table tr[data-case] a").click()
        time.sleep(0.8)
        v.shot(driver, "Detalle del caso", "Pasos numerados y el historial de resultados en todas las ejecuciones. Desde "
               "aquí se edita o se elimina.", 5)

        go("/runs")
        v.shot(driver, "Ejecuciones (Test Runs)", "Cada ejecución es una ronda de pruebas: muestra su progreso, el pass rate "
               "y si está activa o cerrada.", 5)
        by("#btn-new-run").click()
        time.sleep(0.8)
        fill("#r-name", "Smoke Login")
        by("[data-case-picker-toggle][value='0']").click()
        for box in driver.find_elements(By.NAME, "case_ids")[:4]:
            box.click()
        mark(by("#btn-create-run"))
        v.shot(driver, "Nueva ejecución", "Ponle nombre e incluye todos los casos o solo algunos, marcados por carpeta. Cada "
               "caso se copia como un resultado «Untested».", 7)
        by("#btn-create-run").click()
        time.sleep(1)
        v.shot(driver, "Ejecución creada", "Todo empieza en Untested (gris). Arriba, el pass rate, el progreso y el conteo "
               "de cada estado; las pestañas filtran por estado.", 6)

        rows = driver.find_elements(By.CSS_SELECTOR, "form[data-result-form]")
        Select(rows[0].find_element(By.NAME, "status")).select_by_value("passed")
        rows[0].find_element(By.NAME, "executed_by").send_keys("Ana Torres")
        rows[0].find_element(By.CSS_SELECTOR, "button").click()
        time.sleep(1)
        form = driver.find_elements(By.CSS_SELECTOR, "form[data-result-form]")[1]
        Select(form.find_element(By.NAME, "status")).select_by_value("failed")
        form.find_element(By.CSS_SELECTOR, "button").click()
        time.sleep(0.5)
        driver.execute_script("window.scrollTo(0,0)")
        v.shot(driver, "Comentario obligatorio", "Un resultado Failed o Blocked sin comentario no se guarda: el campo se marca "
               "en rojo. El servidor también lo valida (la API responde 400).", 7)
        form = driver.find_elements(By.CSS_SELECTOR, "form[data-result-form]")[1]
        form.find_element(By.NAME, "comment").send_keys("El mensaje dice «Error» sin más detalle (BUG-77)")
        form.find_element(By.NAME, "executed_by").send_keys("Ana Torres")
        form.find_element(By.CSS_SELECTOR, "button").click()
        time.sleep(1)
        driver.execute_script("window.scrollTo(0,0)")
        time.sleep(0.3)
        v.shot(driver, "Resultados registrados", "Passed en verde y Failed en rojo, con quién y cuándo. La barra y el pass rate "
               "se recalculan solos.", 7)
        mark(by("#btn-close-run"))
        v.shot(driver, "Cerrar la ejecución", "Al terminar la ronda se cierra: los resultados quedan fijos y ya no se pueden "
               "cambiar.", 5)

        go("/")
        v.shot(driver, "Dashboard actualizado", "El dashboard suma los resultados de todas las ejecuciones activas.", 5)

        for name, title, text in (("12-reporte-pytest.png", "Pruebas automáticas (pytest)",
                                   "64 pruebas con el test_client de Flask: API, validaciones, flujo de ejecución y pantallas. "
                                   "En VS Code aparecen en la pestaña Testing."),
                                  ("13-reporte-cobertura.png", "Reporte de cobertura (pytest-cov)",
                                   "pytest --cov=app mide qué líneas del código ejecutaron las pruebas: 98 %. "
                                   "El reporte HTML queda en htmlcov/index.html.")):
            path = os.path.join(SHOTS, name)
            if os.path.isfile(path):
                v.image(path, title, text, 7)
        v.end_slide()
    finally:
        driver.quit()
        proc.kill()
    v.save()
    print(f"Video: {OUTPUT} · {len(v.frames) / FPS:.0f} s · {v.step} pasos")


if __name__ == "__main__":
    sys.exit(main())
