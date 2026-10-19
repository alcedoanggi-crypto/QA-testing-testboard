"""Datos de demostración: se cargan solo si la base está vacía (SEED_DEMO=0 lo desactiva)."""
from datetime import timedelta

from app import db
from app.models import Project, Section, TestCase, TestResult, TestRun, now

DEMO = {
    "Autenticación": {
        "Login": [
            ("Login con credenciales válidas", "High", "Smoke", "JIRA-101",
             [("Abrir /login", "Se muestra el formulario"), ("Ingresar usuario y contraseña válidos", ""),
              ("Pulsar «Ingresar»", "Se abre el dashboard")]),
            ("Login con contraseña incorrecta", "High", "Functional", "JIRA-101",
             [("Ingresar una contraseña incorrecta", ""), ("Pulsar «Ingresar»", "Mensaje «Credenciales inválidas»")]),
            ("Bloqueo tras 5 intentos fallidos", "Critical", "Functional", "JIRA-102",
             [("Fallar el login 5 veces", "La cuenta se bloquea 15 minutos")]),
        ],
        "Recuperar contraseña": [
            ("Enviar enlace de recuperación", "Medium", "Functional", "JIRA-103",
             [("Pulsar «Olvidé mi contraseña» e ingresar el correo", "Llega un correo con el enlace")]),
        ],
    },
    "Facturación": {
        "Emitir factura": [
            ("Emitir factura con datos válidos", "Critical", "Smoke", "JIRA-201",
             [("Completar cliente y productos", "Se calcula el total"), ("Pulsar «Emitir»", "Se muestra el número")]),
            ("Emitir factura con IVA 0 %", "High", "Functional", "JIRA-202",
             [("Agregar un producto exento", "IVA = 0"), ("Pulsar «Emitir»", "La factura se emite")]),
        ],
        "Anular factura": [
            ("Anular factura del mismo día", "High", "Regression", "JIRA-210",
             [("Abrir una factura de hoy y pulsar «Anular»", "Estado «Anulada»")]),
            ("Dashboard carga en menos de 2 s", "Medium", "Performance", "JIRA-300",
             [("Medir la carga con 1000 facturas", "Tiempo < 2 s")]),
        ],
    },
}
# Resultados fijos de la ejecución de demostración (en el orden de los casos)
DEMO_RESULTS = [("passed", ""), ("passed", ""), ("failed", "El bloqueo no se activa al quinto intento (BUG-41)"),
                ("blocked", "El servidor de correo de QA está caído"), ("passed", ""), ("untested", ""),
                ("passed", ""), ("untested", "")]


def seed_if_empty():
    if db.session.scalar(db.select(db.func.count(Project.id))):
        return False
    project = Project(name="Portal de Facturación", description="Sistema web de facturación electrónica")
    position = 0
    for top_name, subs in DEMO.items():
        position += 1
        top = Section(project=project, name=top_name, position=position)
        for sub_name, cases in subs.items():
            position += 1
            sub = Section(project=project, parent=top, name=sub_name, position=position)
            for title, priority, ctype, refs, steps in cases:
                TestCase(project=project, section=sub, title=title, priority=priority, type=ctype, refs=refs,
                         preconditions="Usuario con sesión iniciada" if top_name != "Autenticación" else "",
                         steps=[{"action": a, "expected": e} for a, e in steps])
    db.session.add(project)
    db.session.flush()

    run = TestRun(project=project, name="Regresión Sprint 14", description="Build 1.4.2 · ambiente QA")
    cases = sorted(project.cases, key=lambda c: (c.section.path, c.id))
    for i, (case, (status, comment)) in enumerate(zip(cases, DEMO_RESULTS)):
        run.results.append(TestResult(case=case, case_title=case.title, section_path=case.section.path,
                                      priority=case.priority, status=status, comment=comment,
                                      executed_by="Ana Torres" if status != "untested" else "",
                                      executed_at=now() - timedelta(hours=8 - i) if status != "untested" else None))
    db.session.add(run)
    db.session.add(Project(name="App Móvil Clientes", description="Aplicación Android/iOS"))
    db.session.commit()
    return True
